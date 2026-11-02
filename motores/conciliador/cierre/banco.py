# -*- coding: utf-8 -*-
"""
Bancolombia — lo que llegó al banco, en una estructura neutral (DatosBanco).

Dos fuentes, cualquiera sirve (y se pueden sumar):
  leer_pdf      PDF de movimientos. Reutiliza transferencias_core.extraer_transacciones
                (PAGO QR / PAGO LLAVE; el punto sale de los últimos 4 dígitos de la
                referencia) y además busca líneas de consignación (R32).
  leer_sheet    el Sheet de control "N. Transferencias <mes>" descargado como .xlsx:
                una hoja por día, una fila por punto con cada transferencia del banco
                a partir de la columna TRANSACCIONES, y la fila "Datos Sin origen".

Una sola cuenta para todos los puntos; el extracto trae fecha pero no hora.
"""
import datetime as dt
import os
import re
from dataclasses import dataclass, field

import openpyxl

from .texto import norm

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


@dataclass
class MovBanco:
    fecha: dt.date
    valor: float
    punto: str = None          # id del punto; None = sin identificar
    referencia: str = ""
    descripcion: str = ""
    origen: str = ""           # dónde está: "extracto.pdf" o "Transferencias septiembre!05 fila 4"
    fuente: str = "Banco"      # "Banco", "Bold" o "Redeban" (para la evidencia)


@dataclass
class DatosBanco:
    transferencias: dict = field(default_factory=dict)   # (fecha, punto) -> [MovBanco]
    sin_identificar: dict = field(default_factory=dict)  # fecha -> [MovBanco]
    consignaciones: dict = field(default_factory=dict)   # fecha -> [MovBanco]
    fechas: set = field(default_factory=set)             # días que la fuente cubre
    fechas_consignaciones: set = field(default_factory=set)
    archivos: list = field(default_factory=list)
    avisos: list = field(default_factory=list)

    def agregar(self, otro):
        """Suma otra fuente. Si un mismo día viene de dos fuentes (PDF y Sheet),
        gana la que se cargó primero para no duplicar transferencias."""
        nuevos = otro.fechas - self.fechas
        for (f, p), movs in otro.transferencias.items():
            if f in nuevos:
                self.transferencias.setdefault((f, p), []).extend(movs)
        for f, movs in otro.sin_identificar.items():
            if f in nuevos:
                self.sin_identificar.setdefault(f, []).extend(movs)
        for f, movs in otro.consignaciones.items():
            if f not in self.fechas_consignaciones:
                self.consignaciones.setdefault(f, []).extend(movs)
        self.fechas_consignaciones |= otro.fechas_consignaciones
        self.fechas |= otro.fechas
        self.archivos += otro.archivos
        self.avisos += otro.avisos
        repetidos = otro.fechas - nuevos
        if repetidos:
            self.avisos.append(f"{', '.join(otro.archivos)}: los días "
                               f"{', '.join(f'{d:%d/%m}' for d in sorted(repetidos))} ya venían de otra "
                               f"fuente; se usó la primera.")


def _fecha_iso_banco(s):
    return dt.date.fromisoformat(s.replace("/", "-"))


VALOR_RE = re.compile(r"(-?[\d.]*\d,\d{3}(?:,\d{3})*\.\d{2}|-?\d+\.\d{2})\s*$")
LINEA_FECHA_RE = re.compile(r"^(\d{4}/\d{2}/\d{2})\s+(.*)$")


# Pagos de clientes que no traen código de punto (no son PAGO QR / PAGO LLAVE).
SIN_CODIGO_RE = re.compile(r"^(TRANSFERENCIA DESDE|TRANSFERENCIA CTA)\b")


def leer_zip(ruta, carpeta_destino):
    """Bancolombia descarga el extracto como .zip con el PDF adentro."""
    import zipfile
    with zipfile.ZipFile(ruta) as z:
        pdfs = [n for n in z.namelist() if n.lower().endswith(".pdf")]
        if not pdfs:
            raise ValueError(f"{os.path.basename(ruta)} no trae ningún PDF adentro.")
        os.makedirs(carpeta_destino, exist_ok=True)
        return [z.extract(n, carpeta_destino) for n in pdfs]


def leer_pdf(ruta, ids_validos, palabras_consignacion):
    """Una sola pasada por el PDF. Las transferencias se interpretan con las
    mismas reglas de transferencias_core (PATRON_LINEA, PATRON_VALOR,
    PATRON_REFERENCIA, LAST4_TO_PUNTO), sin modificarlo; leerlo dos veces
    (una para transferencias y otra para consignaciones) tardaba el doble."""
    import pdfplumber
    import transferencias_core as tc

    nombre = os.path.basename(ruta)
    datos = DatosBanco(archivos=[nombre])
    claves = [norm(p) for p in palabras_consignacion]

    def sin_id(f, valor, ref, linea):
        datos.sin_identificar.setdefault(f, []).append(MovBanco(f, valor, None, ref, linea, nombre))

    with pdfplumber.open(ruta) as pdf:
        for page in pdf.pages:
            for linea in (page.extract_text() or "").split("\n"):
                linea = linea.strip()
                m = LINEA_FECHA_RE.match(linea)
                if not m:
                    continue
                f = _fecha_iso_banco(m.group(1))
                datos.fechas.add(f)
                datos.fechas_consignaciones.add(f)
                resto = m.group(2)
                mt = tc.PATRON_LINEA.match(linea)
                if mt:   # PAGO QR / PAGO LLAVE: igual que transferencias_core.extraer_transacciones
                    mv = tc.PATRON_VALOR.search(mt.group("resto"))
                    if not mv:
                        continue
                    try:
                        valor = float(mv.group(1).replace(",", ""))
                    except ValueError:
                        continue
                    refs = tc.PATRON_REFERENCIA.findall(mt.group("resto")[: mv.start()])
                    if not refs:
                        sin_id(f, valor, "", linea)
                        continue
                    info = tc.LAST4_TO_PUNTO.get(refs[0][-4:])
                    if info and info[0] in ids_validos:
                        datos.transferencias.setdefault((f, info[0]), []).append(
                            MovBanco(f, valor, info[0], refs[0], "", nombre))
                    else:
                        sin_id(f, valor, refs[0], linea)
                    continue
                mv = VALOR_RE.search(resto)
                if not mv:
                    continue
                valor = float(mv.group(1).replace(",", ""))
                if valor <= 0:
                    continue
                if SIN_CODIGO_RE.match(resto):     # p. ej. TRANSFERENCIA DESDE NEQUI
                    sin_id(f, valor, "", linea)
                elif any(c in norm(resto) for c in claves):
                    datos.consignaciones.setdefault(f, []).append(MovBanco(f, valor, None, "", linea, nombre))
    if not datos.fechas:
        datos.avisos.append(f"{nombre}: no encontré movimientos con fecha. ¿Es el PDF de movimientos de Bancolombia?")
    return datos


def mes_de_nombre(nombre):
    """'13. Transferencias septiembre_26.xlsx' -> (2026, 9)."""
    n = norm(os.path.splitext(nombre)[0])
    mes = next((v for k, v in MESES.items() if re.search(rf"\b{k}\b", n)), None)
    m_anio = re.search(r"\b(20\d{2})\b", n) or re.search(r"(?:^|\s)(\d{2})$", n)
    if not mes or not m_anio:
        return None
    anio = int(m_anio.group(1))
    return (anio + 2000 if anio < 100 else anio), mes


def es_hoja_de_dia(titulo):
    return bool(re.fullmatch(r"\d{1,2}", titulo.strip()))   # no 'URL' ni '19 bancolombia'


def leer_sheet(ruta, identificar_punto, mes_por_defecto=None):
    """Sheet de control de transferencias descargado como .xlsx."""
    nombre = os.path.basename(ruta)
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    hojas = {h: list(wb[h].iter_rows(min_row=1, max_row=60, max_col=80, values_only=True))
             for h in wb.sheetnames if es_hoja_de_dia(h)}
    wb.close()
    return procesar_sheet(nombre, hojas, identificar_punto, mes_de_nombre(nombre) or mes_por_defecto)


def procesar_sheet(nombre, hojas, identificar_punto, anio_mes):
    """hojas: {título de la hoja: [filas como tuplas]}. Lo usan el .xlsx y el
    lector de Google Sheets."""
    datos = DatosBanco(archivos=[nombre])
    if anio_mes is None:
        raise ValueError(f"No sé de qué mes es '{nombre}'. El nombre debe decir el mes y el año, "
                         f"por ejemplo '13. Transferencias septiembre_26.xlsx'.")
    anio, mes = anio_mes
    for hoja, filas in hojas.items():
        if not es_hoja_de_dia(hoja):
            continue
        try:
            fecha = dt.date(anio, mes, int(hoja))
        except ValueError:
            continue
        enc = next((i for i, f in enumerate(filas) if f and norm(f[0]) == "puntos"), None)
        if enc is None:
            datos.avisos.append(f"{nombre}, hoja {hoja}: no encontré el encabezado 'PUNTOS'.")
            continue
        cab = [norm(v) for v in filas[enc]]
        c_trans = next((i for i, h in enumerate(cab) if h.startswith("transacciones")), None)
        if c_trans is None:
            datos.avisos.append(f"{nombre}, hoja {hoja}: no encontré la columna 'TRANSACCIONES'.")
            continue
        hubo_datos = False
        for i in range(enc + 1, len(filas)):
            fila = list(filas[i] or ())
            etiqueta = fila[0] if fila else None
            if etiqueta is None or isinstance(etiqueta, (int, float)):
                continue
            et = norm(etiqueta)
            if et.startswith("transferencias en movimientos") or et == "puntos":
                break     # termina el bloque de puntos (abajo viene el bloque de ADDI)
            if et.startswith("domicilios"):
                continue
            punto = identificar_punto(str(etiqueta))
            if punto is None:
                datos.avisos.append(f"{nombre}, hoja {hoja}: no reconozco el punto '{etiqueta}'.")
                continue
            for j in range(c_trans, len(fila)):
                v = fila[j]
                if isinstance(v, (int, float)) and v:
                    hubo_datos = True
                    datos.transferencias.setdefault((fecha, punto), []).append(
                        MovBanco(fecha, float(v), punto, "", "",
                                 f"{nombre} hoja {hoja}, fila {i + 1}, col {j + 1}"))
        for i in range(enc + 1, len(filas)):
            fila = list(filas[i] or ())
            if fila and norm(fila[0]).startswith("datos sin origen"):
                for j in range(1, len(fila)):
                    v = fila[j]
                    if isinstance(v, (int, float)) and v:
                        datos.sin_identificar.setdefault(fecha, []).append(
                            MovBanco(fecha, float(v), None, "", "Datos sin origen",
                                     f"{nombre} hoja {hoja}, fila {i + 1}"))
                break
        if hubo_datos:
            datos.fechas.add(fecha)
    if not datos.fechas:
        datos.avisos.append(f"{nombre}: ninguna hoja de día trae transferencias.")
    return datos
