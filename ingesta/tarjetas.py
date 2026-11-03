# -*- coding: utf-8 -*-
"""Lee los reportes de Bold y Redeban y los deja como cobros en pesos enteros.

Los encabezados son de Bold y Redeban, no de un cliente. Lo propio de cada empresa,
qué datáfono es de qué punto, llega en `puntos`:
    {"bold": {"NOMBRE DEL DATAFONO": "Punto 1"}, "redeban": {"85": "Punto 2"}}
Por ahora sale de un archivo local. Con la base, saldrá de terminal_datafono.

Solo lee: no escribe Excel. Las hojas que arma el conciliador con su plantilla no
pasan a Tino.
"""
import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "motores"))

from nucleo.logica import a_pesos  # noqa: E402


class FormatoNoReconocido(Exception):
    pass


COLUMNAS_BOLD = {
    "datafono": ("NOMBRE DEL DATÁFONO",),
    "fecha": ("FECHA",),
    # El formato anterior la llama ESTADO ACTUAL. Sin leerla, un cobro no realizado
    # contaría como venta.
    "operacion": ("OPERACIÓN", "ESTADO ACTUAL"),
    "total": ("VALOR TOTAL",),
    "retefuente": ("VALOR RETE FUENTE",),
    "reteiva": ("VALOR RETE IVA",),
    "reteica": ("VALOR RETE ICA",),
    "comision_pct": ("% COMISIÓN BOLD",),
    "comision_fija": ("COMISIÓN BOLD FIJA",),
    "deposito": ("DEPOSITO EN CUENTA BOLD", "DEPOSITO EN SALDO DE VENTAS"),
    "prestamo": ("DEDUCCIÓN DEL PRÉSTAMO",),
    "franquicia": ("FRANQUICIA",),
}
COLUMNAS_REDEBAN = {
    "establecimiento": ("CODIGO ESTABLECIMIENTO",),
    "franquicia": ("FRANQUICIA",),
    "fecha": ("FECHA DE TRANSACCION",),
    "total": ("VALOR TOTAL",),
    "comision": ("VALOR COMISION",),
    "retefuente": ("VALOR RETEFUENTE",),
    "reteiva": ("VALOR RETE IVA",),
    "reteica": ("VALOR RTE ICA",),
    "neto": ("VALOR NETO",),
}
# Bold cambia de formato: estas columnas no siempre vienen. Solo se leen las de plata;
# el nombre y el documento de quien paga se quedan en el archivo.
OPCIONALES_BOLD = {"operacion", "prestamo", "franquicia"}


def _pesos(valor):
    """Celda -> pesos enteros, o None si no se entiende. Decimal evita el float."""
    if valor is None or valor == "":
        return 0
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return a_pesos(format(Decimal(str(valor)), "f"))
    return a_pesos(str(valor).strip().replace("$", "").replace(" ", ""))


def _encabezados(hoja, buscadas):
    for fila in range(1, min(10, hoja.max_row) + 1):
        mapa = {}
        for col in range(1, hoja.max_column + 1):
            valor = hoja.cell(fila, col).value
            if valor is not None:
                # El primero gana: los archivos procesados traen a la derecha otra
                # tabla con los mismos títulos.
                mapa.setdefault(str(valor).strip().upper(), col)
        if any(nombre in mapa for nombre in buscadas):
            return fila, mapa
    return None, {}


def _hoja_del_reporte(ruta, buscadas):
    """Los datos no siempre están en la primera hoja de un archivo ya trabajado."""
    libro = openpyxl.load_workbook(ruta, data_only=True)
    for hoja in libro.worksheets:
        inicio, mapa = _encabezados(hoja, buscadas)
        if inicio is not None:
            return hoja, inicio, mapa
    raise FormatoNoReconocido("No se encontró la fila de encabezados.")


def _columnas(mapa, esperadas, fuente, opcionales=()):
    columnas, faltan = {}, []
    for campo, nombres in esperadas.items():
        columnas[campo] = next((mapa[n] for n in nombres if n in mapa), None)
        if columnas[campo] is None and campo not in opcionales:
            faltan.append(campo)
    if faltan:
        raise FormatoNoReconocido(f"El archivo de {fuente} no trae las columnas: {', '.join(faltan)}.")
    return columnas


def _fecha_y_hora(valor):
    """Bold trae fecha y hora. La medianoche exacta significa que no trae hora."""
    if isinstance(valor, dt.datetime):
        momento = valor
    elif isinstance(valor, dt.date):
        momento = dt.datetime(valor.year, valor.month, valor.day)
    else:
        momento = dt.datetime.fromisoformat(str(valor).strip()[:19])
    hora = momento.hour if (momento.hour or momento.minute) else None
    return momento.date().isoformat(), hora


def _fecha_redeban(valor):
    if isinstance(valor, dt.datetime):
        return valor.date().isoformat()
    if isinstance(valor, dt.date):
        return valor.isoformat()
    texto = str(valor).strip()
    if len(texto) == 8 and texto.isdigit():
        return f"{texto[:4]}-{texto[4:6]}-{texto[6:8]}"
    return dt.date.fromisoformat(texto[:10]).isoformat()


def _cobro(fila, avisos, **campos):
    """Arma el cobro, o avisa y lo deja por fuera. Nada se descarta en silencio."""
    montos = {k: campos[k] for k in ("bruto", "comision", "retenciones", "prestamo", "neto")}
    if any(v is None for v in montos.values()):
        avisos.append(f"Fila {fila}: valores que no se entienden; no se cuenta.")
        return None
    return campos


def leer_bold(ruta, puntos):
    """Devuelve (cobros, avisos). Solo cuentan los COBRO EXITOSO."""
    hoja, inicio, mapa = _hoja_del_reporte(ruta, {"NOMBRE DEL DATÁFONO"})
    col = _columnas(mapa, COLUMNAS_BOLD, "Bold", OPCIONALES_BOLD)
    por_nombre = {str(k).strip().upper(): v for k, v in puntos.get("bold", {}).items()}

    cobros, avisos, omitidas, desconocidos, raras = [], [], 0, set(), 0
    for f in range(inicio + 1, hoja.max_row + 1):
        celda = lambda campo: hoja.cell(f, col[campo]).value  # noqa: E731
        datafono, fecha = celda("datafono"), celda("fecha")
        if datafono is None or fecha is None:
            continue
        if col["operacion"]:
            operacion = celda("operacion")
            if operacion is not None and str(operacion).strip().upper() != "COBRO EXITOSO":
                omitidas += 1
                continue
        # Un archivo ya trabajado puede traer totales o encabezados repetidos en medio.
        try:
            dia, hora = _fecha_y_hora(fecha)
        except ValueError:
            raras += 1
            continue
        nombre = str(datafono).strip().upper().rstrip(".").strip()
        punto = por_nombre.get(nombre)
        if punto is None:
            desconocidos.add(str(datafono).strip())
            continue
        partes = [_pesos(celda(c)) for c in ("retefuente", "reteiva", "reteica")]
        comisiones = [_pesos(celda(c)) for c in ("comision_pct", "comision_fija")]
        franquicia = celda("franquicia") if col["franquicia"] else None
        cobro = _cobro(f, avisos, fecha=dia, hora=hora, punto=punto, proveedor="bold",
                       franquicia=str(franquicia).strip().upper() if franquicia else None,
                       bruto=_pesos(celda("total")),
                       comision=None if None in comisiones else sum(comisiones),
                       retenciones=None if None in partes else sum(partes),
                       prestamo=_pesos(celda("prestamo")) if col["prestamo"] else 0,
                       neto=_pesos(celda("deposito")))
        if cobro:
            cobros.append(cobro)
    if omitidas:
        avisos.append(f"{omitidas} operación(es) que no son COBRO EXITOSO no se cuentan.")
    if desconocidos:
        avisos.append("Datáfonos sin punto asignado, no se cuentan: " + ", ".join(sorted(desconocidos)) + ".")
    if raras:
        avisos.append(f"{raras} fila(s) sin fecha válida, como totales, no se cuentan.")
    return cobros, avisos


def leer_redeban(ruta, puntos):
    """Devuelve (cobros, avisos). Redeban trae fecha pero no hora."""
    hoja, inicio, mapa = _hoja_del_reporte(ruta, {"CODIGO ESTABLECIMIENTO"})
    col = _columnas(mapa, COLUMNAS_REDEBAN, "Redeban")
    por_codigo = {str(k)[-2:]: v for k, v in puntos.get("redeban", {}).items()}

    cobros, avisos, desconocidos, raras = [], [], set(), 0
    for f in range(inicio + 1, hoja.max_row + 1):
        celda = lambda campo: hoja.cell(f, col[campo]).value  # noqa: E731
        establecimiento, franquicia = celda("establecimiento"), celda("franquicia")
        if establecimiento is None or franquicia is None:
            continue
        codigo = str(establecimiento).strip()[-2:]
        punto = por_codigo.get(codigo)
        if punto is None:
            desconocidos.add(codigo)
            continue
        try:
            fecha = _fecha_redeban(celda("fecha"))
        except ValueError:
            raras += 1
            continue
        # Redeban trae comisión y retenciones en negativo. En una reversión vienen en
        # positivo porque las devuelve: para Tino restan, igual que la venta.
        bruto = _pesos(celda("total"))
        signo = -1 if bruto is not None and bruto < 0 else 1
        comision = _pesos(celda("comision"))
        partes = [_pesos(celda(c)) for c in ("retefuente", "reteiva", "reteica")]
        cobro = _cobro(f, avisos, fecha=fecha, hora=None, punto=punto,
                       proveedor="redeban", franquicia=str(franquicia).strip().upper(),
                       bruto=bruto,
                       comision=None if comision is None else signo * abs(comision),
                       retenciones=None if None in partes else signo * sum(abs(p) for p in partes),
                       prestamo=0, neto=_pesos(celda("neto")))
        if cobro:
            cobros.append(cobro)
    if desconocidos:
        avisos.append("Establecimientos sin punto asignado, no se cuentan: "
                      + ", ".join(sorted(desconocidos)) + ".")
    if raras:
        avisos.append(f"{raras} fila(s) sin fecha válida, como totales, no se cuentan.")
    return cobros, avisos


def leer(ruta, puntos):
    """Reconoce si es Bold o Redeban por sus encabezados."""
    # read_only deja el archivo abierto, y en Windows eso lo bloquea: hay que cerrarlo.
    libro = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    try:
        filas = [fila for hoja in libro.worksheets
                 for fila in hoja.iter_rows(min_row=1, max_row=8, values_only=True)]
    finally:
        libro.close()
    for fila in filas:
        texto = " ".join(str(v).upper() for v in fila if v is not None)
        if "NOMBRE DEL DAT" in texto and "FECHA" in texto:
            return leer_bold(ruta, puntos)
        if "CODIGO ESTABLECIMIENTO" in texto and "FRANQUICIA" in texto:
            return leer_redeban(ruta, puntos)
    raise FormatoNoReconocido("El archivo no parece un reporte de Bold ni de Redeban.")


def unir_reportes(lotes):
    """Une reportes que se traslapan sin contar dos veces.

    El mismo mes suele estar descargado varias veces, a veces incompleto. Para cada día
    de cada proveedor se queda con el reporte que más cobros trae de ese día. Si empatan,
    gana el que trae el préstamo: una versión vieja del archivo puede no tener esa columna.
    """
    def valor(cobros_del_dia):
        return len(cobros_del_dia), sum(c.get("prestamo", 0) for c in cobros_del_dia)

    mejor = {}
    for cobros in lotes:
        por_dia = {}
        for c in cobros:
            por_dia.setdefault((c["proveedor"], c["fecha"]), []).append(c)
        for clave, del_dia in por_dia.items():
            if clave not in mejor or valor(del_dia) > valor(mejor[clave]):
                mejor[clave] = del_dia
    return [c for clave in sorted(mejor) for c in mejor[clave]]
