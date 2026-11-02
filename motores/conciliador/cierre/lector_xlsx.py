# -*- coding: utf-8 -*-
"""
Lector .xlsx -> DiaPunto. Respaldo y pruebas (el lector principal será Google
Sheets). Todo se ubica por TEXTO: encabezados de la fila de "PRODUCTO" para las
columnas, etiquetas de la columna A para el bloque de caja. Nunca por letra.
"""
import datetime as dt
import os
import re

import openpyxl
from openpyxl.utils import get_column_letter as col_letra

from .modelo import DiaPunto, Producto, Pagos, Caja, FilaDescFact
from .texto import norm, num, num_o_none

MAX_FILAS = 400
MAX_COLS = 60

# encabezado normalizado -> rol (columnas de productos y listas de pago)
COLUMNAS = {
    "producto": "nombre",
    "precio": "precio",
    "inv inicial": "inv_inicial",
    "entradas": "entradas",
    "inv final": "inv_final",
    "salidas siigo": "salidas_siigo",
    "salidas totales": "salidas_tot",
    "valor venta": "valor",
    "regalos entregados": "regalos_cant",
    "total regalos": "regalos_valor",
    "descuentos": "descuento",
    "cantidad": "efectivo_cant",
    "descuento": "efectivo_desc_unit",
    "total": "efectivo_total",
    "transferencias": "pago_transferencias",
    "tarjeta debito": "pago_debito",
    "tarjeta credito": "pago_credito",
}

# etiqueta de caja (columna A) -> rol. Orden importa: se prueba de arriba abajo
# y gana la primera coincidencia ("regalos idunn" antes que "regalos").
ETIQUETAS_CAJA = [
    (lambda t: t == "efectivo", "efectivo_contado"),
    (lambda t: t.startswith("venta en efectivo"), "venta_efectivo"),
    (lambda t: t == "addi", "addi"),
    (lambda t: t.startswith("consignacion"), "consignacion"),
    (lambda t: t.startswith("tarjetas"), "tarjetas"),
    (lambda t: t.startswith("transferencias"), "transferencias"),
    (lambda t: t.startswith("gastos"), "gastos"),
    (lambda t: t.startswith("descuent") and "idunn" in t, "descuentos_idunn"),
    (lambda t: t.startswith("descuent"), "descuentos"),
    (lambda t: t.startswith("regalos") and "idunn" in t, "regalos_idunn"),
    (lambda t: t.startswith("regalos"), "regalos"),
    (lambda t: t.startswith("danados"), "danados"),
    (lambda t: t.startswith("devoluciones"), "devoluciones"),
    (lambda t: t.startswith("cambios"), "cambios"),
    # "Efectivo Apartido" (sic) en la hoja 01 de agosto.
    (lambda t: t.startswith("efectivo apar"), "efectivo_apartado"),
    (lambda t: t.startswith("base"), "base"),
    (lambda t: t == "total", "total"),
    (lambda t: t.startswith("descuadre"), "descuadre"),
    (lambda t: t.startswith("cantidad facturas"), "cantidad_facturas"),
]

DESC_FACT_COLS = {
    "fecha": "dia",
    "asesor": "asesor",
    "vr descuadre": "descuadre",
    "venta dia": "venta",
    "facturas": "facturas",
    "efectivo sin facturar": "efectivo_sin_facturar",
    "saldo": "saldo",
    "dinero entregado": "entregado",
}

HOJA_DIA_RE = re.compile(r"^\d{1,2}$")
SEPARADORES_ASESORAS = re.compile(r"\s+y\s+|\s*[-/,&+]\s*", re.IGNORECASE)


class ErrorLectura(Exception):
    pass


def _es_formula(v):
    return isinstance(v, str) and v.startswith("=")


def _grilla(ws):
    """Lee la hoja una sola vez a un dict (fila, col) -> valor."""
    g = {}
    for r, fila in enumerate(ws.iter_rows(min_row=1, max_row=MAX_FILAS,
                                          max_col=MAX_COLS, values_only=True), 1):
        for c, v in enumerate(fila, 1):
            if v is not None:
                g[(r, c)] = v
    return g


def _ref(r, c):
    return f"{col_letra(c)}{r}"


def _a_fecha(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    # Google Sheets (UNFORMATTED_VALUE + SERIAL_NUMBER) entrega las fechas como
    # número de días desde el 30/12/1899, igual que Excel por dentro.
    if isinstance(v, (int, float)) and not isinstance(v, bool) and 30000 < v < 80000:
        return dt.date(1899, 12, 30) + dt.timedelta(days=int(v))
    return None


def es_hoja_util(nombre):
    """Hojas que se leen: las de día ('01'…'31'), DESC FACT, y las tipo
    '04 antiguo' (no son de día, pero DESC FACT las puede referenciar)."""
    return bool(HOJA_DIA_RE.match(nombre) or norm(nombre) == "desc fact"
                or re.match(r"^\d{1,2}\s+\S", nombre))


def separar_asesoras(texto):
    if not texto:
        return []
    partes = [p.strip() for p in SEPARADORES_ASESORAS.split(str(texto)) if p and p.strip()]
    return [" ".join(w.capitalize() for w in p.split()) for p in partes]


class LibroMensual:
    """Un libro mensual de un punto de venta, ya leído y normalizado.

    No sabe de dónde vienen las celdas: recibe las cuadrículas ya armadas
    ({hoja: {(fila, col): valor}}, una de fórmulas y otra de valores). Las
    arman LibroXlsx (archivo descargado) y cierre.lector_sheets (Google Sheets)."""

    def __init__(self, origen, nombre, nombres_hojas, grillas_formulas, grillas_valores):
        self.path = origen        # ruta del archivo, o enlace del Google Sheet
        self.nombre = nombre      # nombre para mostrar
        self.avisos = []
        self.nombres_hojas = list(nombres_hojas)
        self._f, self._v = grillas_formulas, grillas_valores
        self._interpretar()

    def _interpretar(self):
        self.hojas_dia = sorted((n for n in self.nombres_hojas if HOJA_DIA_RE.match(n)), key=int)
        self.anio, self.mes = self._detectar_mes()
        self.punto_texto = self._detectar_punto()
        self.dias = {}           # fecha (según nombre de hoja) -> DiaPunto
        for nombre in self.hojas_dia:
            try:
                dia = self._leer_dia(nombre)
            except ErrorLectura as e:
                self.avisos.append(f"Hoja {nombre}: {e}")
                continue
            if dia.fecha_hoja:
                self.dias[dia.fecha_hoja] = dia
        self.hoja_desc_fact = next((n for n in self.nombres_hojas if norm(n) == "desc fact"), None)
        self.desc_fact = self._leer_desc_fact() if self.hoja_desc_fact else []
        if not self.hoja_desc_fact:
            self.avisos.append("No se encontró la hoja 'DESC  FACT'.")

    # ------------------------------------------------------------------
    def _detectar_mes(self):
        conteo = {}
        for nombre in self.hojas_dia:
            g = self._v[nombre]
            for r in range(1, 8):
                if norm(g.get((r, 1))) == "fecha":
                    f = _a_fecha(g.get((r, 2)))
                    if f:
                        conteo[(f.year, f.month)] = conteo.get((f.year, f.month), 0) + 1
        if not conteo:
            raise ErrorLectura("Ninguna hoja de día trae la FECHA en el encabezado.")
        return max(conteo, key=conteo.get)

    def _detectar_punto(self):
        for nombre in self.hojas_dia:
            g = self._v[nombre]
            for r in range(1, 8):
                if norm(g.get((r, 1))) == "punto de venta":
                    v = g.get((r, 2))
                    if v:
                        return str(v).strip()
        return os.path.splitext(self.nombre)[0]

    def fecha_de_hoja(self, nombre):
        try:
            return dt.date(self.anio, self.mes, int(nombre))
        except ValueError:
            return None

    def hoja_anterior(self, nombre):
        i = self.hojas_dia.index(nombre)
        return self.hojas_dia[i - 1] if i > 0 else None

    # ------------------------------------------------------------------
    def _leer_dia(self, nombre):
        g, gf = self._v[nombre], self._f[nombre]
        dia = DiaPunto(fecha=None, fecha_hoja=self.fecha_de_hoja(nombre),
                       punto=self.punto_texto, hoja=nombre)

        for r in range(1, 8):
            et = norm(g.get((r, 1)))
            if et == "fecha":
                dia.fecha = _a_fecha(g.get((r, 2)))
                dia.celdas["fecha"] = _ref(r, 2)
            elif et == "nombre asesora":
                dia.asesoras_texto = str(g.get((r, 2)) or "").strip()
                dia.asesoras = separar_asesoras(dia.asesoras_texto)
                dia.celdas["asesoras"] = _ref(r, 2)

        fila_enc = next((r for r in range(1, 20) if norm(g.get((r, 1))) == "producto"), None)
        if fila_enc is None:
            raise ErrorLectura("no se encontró la fila de encabezados (PRODUCTO).")
        cols = {}
        for c in range(1, MAX_COLS + 1):
            rol = COLUMNAS.get(norm(g.get((fila_enc, c))))
            if rol and rol not in cols:
                cols[rol] = c
        faltan = [r for r in ("precio", "inv_inicial", "inv_final", "salidas_siigo",
                              "salidas_tot", "valor") if r not in cols]
        if faltan:
            raise ErrorLectura(f"faltan columnas: {', '.join(faltan)}.")
        for rol, c in cols.items():
            dia.celdas[f"col.{rol}"] = col_letra(c)

        fila_tot = next((r for r in range(fila_enc + 1, MAX_FILAS)
                         if norm(g.get((r, 1))) == "venta del dia"), None)
        if fila_tot is None:
            raise ErrorLectura("no se encontró la fila 'VENTA DEL DIA'.")
        dia.fila_totales = fila_tot
        dia.celdas["fila_encabezado"] = fila_enc

        def val(r, rol):
            c = cols.get(rol)
            return num(g.get((r, c))) if c else 0.0

        for r in range(fila_enc + 1, fila_tot):
            nombre_p = g.get((r, cols["nombre"])) if "nombre" in cols else None
            if isinstance(nombre_p, str) and nombre_p.strip():
                dia.productos.append(Producto(
                    fila=r, nombre=nombre_p.strip(),
                    precio=val(r, "precio"), inv_inicial=val(r, "inv_inicial"),
                    entradas=val(r, "entradas"), salidas_siigo=val(r, "salidas_siigo"),
                    efectivo_cant=val(r, "efectivo_cant"),
                    efectivo_desc_unit=val(r, "efectivo_desc_unit"),
                    salidas_tot=val(r, "salidas_tot"), inv_final=val(r, "inv_final"),
                    valor=val(r, "valor"), regalos_cant=val(r, "regalos_cant"),
                    regalos_valor=val(r, "regalos_valor"), descuento=val(r, "descuento"),
                    efectivo_total=val(r, "efectivo_total")))
            for rol, destino in (("pago_transferencias", dia.pagos.transferencias),
                                 ("pago_debito", dia.pagos.debito),
                                 ("pago_credito", dia.pagos.credito)):
                c = cols.get(rol)
                if c:
                    v = g.get((r, c))
                    if isinstance(v, (int, float)) and v:
                        destino.append((r, float(v)))

        for rol in ("valor", "regalos_valor", "descuento", "efectivo_total",
                    "pago_transferencias", "pago_debito", "pago_credito"):
            if rol in cols:
                dia.celdas[f"tot.{rol}"] = _ref(fila_tot, cols[rol])
        dia.caja.valor_teorico = num(g.get((fila_tot, cols["valor"])))

        self._leer_caja(dia, g, fila_tot)

        for (r, c), v in gf.items():
            if _es_formula(v):
                dia.formulas[_ref(r, c)] = v
        for (r, c), v in g.items():
            dia.valores[_ref(r, c)] = v
        return dia

    def _leer_caja(self, dia, g, fila_tot):
        hasta = min(fila_tot + 60, MAX_FILAS)
        ultima = fila_tot
        for r in range(fila_tot + 1, hasta):
            et = norm(g.get((r, 1)))
            if not et:
                continue
            for prueba, rol in ETIQUETAS_CAJA:
                if prueba(et):
                    clave = f"caja.{rol}"
                    if clave not in dia.celdas:
                        dia.celdas[clave] = _ref(r, 2)
                        if hasattr(dia.caja, rol):
                            setattr(dia.caja, rol, num_o_none(g.get((r, 2))))
                        ultima = max(ultima, r)
                    break
        dia.celdas["fila_fin_caja"] = ultima
        dia.celdas["caja.valor_teorico"] = dia.celdas.get("tot.valor")

        for r in range(fila_tot + 1, fila_tot + 20):
            for c in range(1, MAX_COLS):
                if "sencillo recibido" in norm(g.get((r, c))):
                    dia.celdas["caja.sencillo_recibido"] = _ref(r, c + 1)
                    dia.caja.sencillo_recibido = num_o_none(g.get((r, c + 1)))
                    break
            if "caja.sencillo_recibido" in dia.celdas:
                break

        fila_obs = col_obs = None
        for r in range(fila_tot + 1, fila_tot + 25):
            for c in range(1, MAX_COLS):
                if norm(g.get((r, c))) == "observaciones":
                    fila_obs, col_obs = r, c
                    break
            if fila_obs:
                break
        if fila_obs:
            for r in range(fila_obs + 1, ultima + 6):
                for c in range(col_obs, MAX_COLS):
                    v = g.get((r, c))
                    if isinstance(v, str) and v.strip():
                        dia.observaciones.append((_ref(r, c), v.strip()))

    # ------------------------------------------------------------------
    def _leer_desc_fact(self):
        g, gf = self._v[self.hoja_desc_fact], self._f[self.hoja_desc_fact]
        fila_enc = next((r for r in range(1, 10) if norm(g.get((r, 1))) == "fecha"), None)
        if fila_enc is None:
            self.avisos.append("DESC FACT: no se encontró el encabezado FECHA.")
            return []
        cols = {}
        for c in range(1, MAX_COLS + 1):
            rol = DESC_FACT_COLS.get(norm(g.get((fila_enc, c))))
            if rol and rol not in cols:
                cols[rol] = c
        filas = []
        for r in range(fila_enc + 1, MAX_FILAS):
            d = g.get((r, cols.get("dia", 1)))
            if not isinstance(d, (int, float)):
                continue
            f = FilaDescFact(fila=r, dia=int(d))
            f.asesor = str(g.get((r, cols["asesor"])) or "").strip() if "asesor" in cols else ""
            for rol in ("descuadre", "venta", "facturas", "efectivo_sin_facturar", "saldo", "entregado"):
                if rol in cols:
                    setattr(f, rol, num_o_none(g.get((r, cols[rol]))))
            for rol, c in cols.items():
                fv = gf.get((r, c))
                if _es_formula(fv):
                    f.formulas[rol] = (_ref(r, c), fv)
            filas.append(f)
        return filas


class LibroXlsx(LibroMensual):
    """El libro mensual de un punto leído desde un .xlsx descargado."""

    def __init__(self, path):
        try:
            wb_f = openpyxl.load_workbook(path, data_only=False, read_only=True)
            wb_v = openpyxl.load_workbook(path, data_only=True, read_only=True)
        except Exception as e:
            raise ErrorLectura(f"No se pudo abrir {os.path.basename(path)}: {e}")
        nombres = list(wb_v.sheetnames)
        grillas_f, grillas_v = {}, {}
        for nombre in nombres:
            if es_hoja_util(nombre):
                grillas_f[nombre] = _grilla(wb_f[nombre])
                grillas_v[nombre] = _grilla(wb_v[nombre])
        wb_f.close()
        wb_v.close()
        super().__init__(path, os.path.basename(path), nombres, grillas_f, grillas_v)
