# -*- coding: utf-8 -*-
"""
Siigo — reporte "Ventas por vendedor por producto" y mapeo producto Excel ↔ Siigo.

Siigo solo sirve para comparar UNIDADES (no registra descuentos). Un solo
reporte trae los 11 puntos ("Nombre vendedor" = punto).

Piezas:
  Mapeo         mapeo_siigo.xlsx: nombre en el Excel -> código/nombre en Siigo,
                grupos (varios productos del Excel = un código de Siigo) y kits.
  ReporteSiigo  el reporte leído: rango de fechas y unidades por punto y clave.
  leer_reporte  lector del .xlsx de Siigo. PROVISIONAL: armado con la
                descripción de CIERRE_DEL_DIA.md; se ajusta con un reporte real.
"""
import datetime as dt
import re
from dataclasses import dataclass, field

import openpyxl

from .texto import norm, num


# ---------------------------------------------------------------------------
# Mapeo
# ---------------------------------------------------------------------------
@dataclass
class Componente:
    excel: str            # nombre del producto en el Excel ("" si es "a elección")
    cantidad: float
    es_regalo: bool
    a_eleccion: str = ""  # "shampoo" para "Shampoo (a elección)"


@dataclass
class Mapeo:
    clave_de_excel: dict = field(default_factory=dict)   # norm(nombre excel) -> clave siigo
    nombre_clave: dict = field(default_factory=dict)     # clave -> nombre legible en Siigo
    clave_de_codigo: dict = field(default_factory=dict)  # norm(código) -> clave
    clave_de_nombre: dict = field(default_factory=dict)  # norm(nombre siigo) -> clave
    kits: dict = field(default_factory=dict)             # norm(nombre kit) -> [Componente]
    nombre_kit: dict = field(default_factory=dict)
    avisos: list = field(default_factory=list)

    def clave_excel(self, nombre_excel):
        return self.clave_de_excel.get(norm(nombre_excel))

    def clave_componente(self, nombre):
        """Los componentes de kit vienen a veces con el nombre de Siigo
        ('Doypack Biorepolarizador') y a veces con el del Excel."""
        return self.clave_de_excel.get(norm(nombre)) or self.clave_de_nombre.get(norm(nombre))

    def clave_linea(self, codigo, nombre):
        """Clave para una línea del reporte de Siigo (por código y, si no, por
        nombre). None si no está en el mapeo."""
        if codigo and norm(codigo) in self.clave_de_codigo:
            return self.clave_de_codigo[norm(codigo)]
        n = norm(nombre)
        if n in self.clave_de_nombre:
            return self.clave_de_nombre[n]
        # Grupos tipo "Sachet Obsequio ...": el nombre de la línea empieza por el
        # nombre del grupo.
        for nombre_grupo, clave in self.clave_de_nombre.items():
            if clave.startswith("GRUPO:") and n.startswith(nombre_grupo):
                return clave
        return None


def _bool(v):
    if isinstance(v, (bool, int, float)):
        return bool(v)
    return norm(v) in ("1", "si", "true", "x", "verdadero")


def cargar_mapeo(ruta, grupos):
    """grupos (de cierre_config.json): [{"siigo": "Sachet Obsequio",
    "excel_empieza_por": ["Sachet"]}, ...]."""
    m = Mapeo()
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    hoja = next((wb[n] for n in wb.sheetnames if norm(n) not in ("kits siigo",)), wb.worksheets[0])
    filas = list(hoja.iter_rows(values_only=True))
    enc = [norm(x) for x in filas[0]] if filas else []

    def col(*nombres):
        return next((i for i, h in enumerate(enc) if h in nombres), None)

    c_excel, c_antiguo = col("nombre excel"), col("nombre excel antiguo")
    c_siigo, c_codigo = col("nombre siigo"), col("codigo siigo")
    if c_excel is None or c_siigo is None:
        raise ValueError("El mapeo de Siigo debe tener las columnas 'nombre excel' y 'nombre siigo'.")

    reglas_grupo = [(norm(g["siigo"]), [norm(p) for p in g.get("excel_empieza_por", [])],
                     [norm(p) for p in g.get("excel", [])]) for g in grupos]

    for fila in filas[1:]:
        fila = list(fila) + [None] * 6
        excel, siigo, codigo = fila[c_excel], fila[c_siigo], fila[c_codigo] if c_codigo is not None else None
        antiguo = fila[c_antiguo] if c_antiguo is not None else None
        if not siigo and not excel:
            continue
        grupo = None
        for nombre_grupo, prefijos, exactos in reglas_grupo:
            ne = norm(excel)
            if ne and (ne in exactos or any(ne.startswith(p) for p in prefijos)):
                grupo = nombre_grupo
                break
        if grupo:
            clave = "GRUPO:" + grupo
            m.nombre_clave[clave] = next(g["siigo"] for g in grupos if norm(g["siigo"]) == grupo)
            m.clave_de_nombre[grupo] = clave
        elif codigo:
            clave = "COD:" + norm(codigo)
            m.clave_de_codigo[norm(codigo)] = clave
        elif siigo:
            clave = "NOM:" + norm(siigo)
        else:
            continue   # producto del Excel que no se factura en Siigo
        if siigo and not grupo:
            m.clave_de_nombre[norm(siigo)] = clave
            m.nombre_clave.setdefault(clave, str(siigo).strip())
        for nombre in (excel, antiguo):
            if nombre:
                m.clave_de_excel[norm(nombre)] = clave

    # El código de un grupo (p. ej. "Empaque Milagros" = JACC017) también lleva al grupo.
    for fila in filas[1:]:
        fila = list(fila) + [None] * 6
        siigo, codigo = fila[c_siigo], fila[c_codigo] if c_codigo is not None else None
        if siigo and codigo and norm(siigo) in m.clave_de_nombre and \
                m.clave_de_nombre[norm(siigo)].startswith("GRUPO:"):
            m.clave_de_codigo[norm(codigo)] = m.clave_de_nombre[norm(siigo)]

    hoja_kits = next((wb[n] for n in wb.sheetnames if norm(n) == "kits siigo"), None)
    if hoja_kits is not None:
        kf = list(hoja_kits.iter_rows(values_only=True))
        ke = [norm(x) for x in kf[0]] if kf else []
        ik, ip, ic, ir = (ke.index(x) if x in ke else None for x in
                          ("nombre kit", "producto componente", "cantidad por kit", "es regalo"))
        for fila in kf[1:]:
            fila = list(fila) + [None] * 6   # read_only recorta las celdas vacías del final
            if ik is None or ip is None or not fila[ik] or not fila[ip]:
                continue
            comp = str(fila[ip]).strip()
            cant = num(fila[ic]) if ic is not None and fila[ic] is not None else 1.0
            m_el = re.match(r"^(.*?)\s*\(a elecci[oó]n\)\s*$", comp, re.IGNORECASE)
            c = Componente(excel="" if m_el else comp, cantidad=cant or 1.0,
                           es_regalo=_bool(fila[ir]) if ir is not None else False,
                           a_eleccion=norm(m_el.group(1)) if m_el else "")
            m.kits.setdefault(norm(fila[ik]), []).append(c)
            m.nombre_kit[norm(fila[ik])] = str(fila[ik]).strip()
            if c.excel and not m.clave_componente(c.excel):
                m.avisos.append(f"Kit '{fila[ik]}': el componente '{comp}' no está en el mapeo.")
    wb.close()
    return m


# ---------------------------------------------------------------------------
# Reporte de Siigo (estructura neutral)
# ---------------------------------------------------------------------------
@dataclass
class LineaSiigo:
    punto: str
    codigo: str
    nombre: str
    unidades: float
    fila: int


@dataclass
class ReporteSiigo:
    archivo: str
    desde: dt.date = None
    hasta: dt.date = None
    lineas: list = field(default_factory=list)          # [LineaSiigo]
    vendedores_sin_punto: dict = field(default_factory=dict)   # nombre -> unidades
    avisos: list = field(default_factory=list)
    # Solo con el reporte "Movimiento ventas y compras":
    puntos: set = None              # puntos que trae el reporte (None = los de las líneas)
    pagos: list = field(default_factory=list)            # [PagoSiigo]
    fechas_cambiadas: list = field(default_factory=list)  # [(factura, punto, creada datetime)]

    def cubre(self, fecha):
        return self.desde is not None and self.desde <= fecha <= (self.hasta or self.desde)

    def trae_punto(self, punto):
        return punto in (self.puntos if self.puntos is not None else {ln.punto for ln in self.lineas})


@dataclass
class PagoSiigo:
    fecha: dt.date
    punto: str
    factura: str
    forma: str
    valor: float
    fila: int


FECHA_RE = re.compile(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})|(\d{4})-(\d{2})-(\d{2})")
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
         "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
_M = "|".join(MESES)
# Siigo escribe el encabezado como "De Septiembre 1 2026 a Septiembre 30 2026";
# también se acepta "1 de septiembre de 2026".
FECHA_MES_RE = re.compile(rf"\b({_M})\s+(\d{{1,2}})\s*,?\s+(\d{{4}})\b|\b(\d{{1,2}})\s+de\s+({_M})\s+(?:de\s+)?(\d{{4}})\b")


def _fechas_en(texto):
    out = []
    for m in FECHA_RE.finditer(str(texto)):
        try:
            if m.group(1):
                out.append(dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            else:
                out.append(dt.date(int(m.group(4)), int(m.group(5)), int(m.group(6))))
        except ValueError:
            pass
    if not out:
        for m in FECHA_MES_RE.finditer(norm(texto)):
            try:
                if m.group(1):
                    out.append(dt.date(int(m.group(3)), MESES[m.group(1)], int(m.group(2))))
                else:
                    out.append(dt.date(int(m.group(6)), MESES[m.group(5)], int(m.group(4))))
            except ValueError:
                pass
    return out


def leer_reporte(ruta, identificar_punto, ignorar):
    """identificar_punto(texto) -> id de punto o None.
    ignorar: textos de vendedor a saltar (p. ej. 'CATALIMA MOU S.A.S')."""
    import os
    rep = ReporteSiigo(archivo=os.path.basename(ruta))
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    ws = wb.worksheets[0]
    filas = list(ws.iter_rows(values_only=True))
    wb.close()

    fila_enc = next((i for i, f in enumerate(filas[:40])
                     if any(norm(v) == "nombre vendedor" for v in f)), None)
    if fila_enc is None:
        raise ValueError("No encontré la fila de encabezados con 'Nombre vendedor'. ¿Es el reporte "
                         "'Ventas por vendedor por producto' de Siigo?")
    enc = [norm(v) for v in filas[fila_enc]]

    def col(prueba):
        return next((i for i, h in enumerate(enc) if h and prueba(h)), None)

    c_vend = enc.index("nombre vendedor")
    c_cant = col(lambda h: h.startswith("cantidad vendida")) or col(lambda h: h.startswith("cantidad"))
    c_cod = col(lambda h: h.startswith(("codigo producto", "codigo", "referencia")))
    c_nom = col(lambda h: "producto" in h and not h.startswith("codigo")) or \
        col(lambda h: h.startswith(("nombre", "descripcion")) and h != "nombre vendedor")
    if c_cant is None or (c_cod is None and c_nom is None):
        raise ValueError("El reporte de Siigo no trae las columnas esperadas (cantidad vendida y "
                         "producto/código).")

    fechas = [f for fila in filas[:fila_enc] for v in fila if v for f in
              (_fechas_en(v) if not isinstance(v, (dt.date, dt.datetime))
               else [v.date() if isinstance(v, dt.datetime) else v])]
    if fechas:
        rep.desde, rep.hasta = min(fechas), max(fechas)
    else:
        rep.avisos.append("No encontré el rango de fechas en el encabezado del reporte de Siigo.")

    ignorar_n = [norm(x) for x in ignorar]
    vendedor = None
    for i, fila in enumerate(filas[fila_enc + 1:], start=fila_enc + 2):
        fila = list(fila) + [None] * (len(enc) - len(fila))
        textos = " ".join(norm(v) for v in fila if isinstance(v, str))
        if "procesado en" in textos or textos.startswith("total"):
            continue
        if fila[c_vend]:
            vendedor = str(fila[c_vend]).strip()
        if not vendedor or any(x and x in norm(vendedor) for x in ignorar_n):
            continue
        cant = fila[c_cant]
        if not isinstance(cant, (int, float)):
            continue
        codigo = str(fila[c_cod]).strip() if c_cod is not None and fila[c_cod] is not None else ""
        nombre = str(fila[c_nom]).strip() if c_nom is not None and fila[c_nom] is not None else ""
        if "total" in norm(nombre) or "total" in norm(codigo):
            continue
        punto = identificar_punto(vendedor)
        if punto is None:
            rep.vendedores_sin_punto[vendedor] = rep.vendedores_sin_punto.get(vendedor, 0) + cant
            continue
        rep.lineas.append(LineaSiigo(punto, codigo, nombre, float(cant), i))
    if rep.vendedores_sin_punto:
        rep.avisos.append("Vendedores de Siigo que no reconozco como punto: "
                          + ", ".join(rep.vendedores_sin_punto) + ". Agrégalos como alias del punto.")
    return rep


# ---------------------------------------------------------------------------
# Reporte "Movimiento ventas y compras": factura por factura, de cualquier rango
# ---------------------------------------------------------------------------
def es_movimiento(ruta):
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    try:
        for fila in wb.worksheets[0].iter_rows(max_row=40, values_only=True):
            enc = {norm(v) for v in fila if v}
            if "tipo transaccion" in enc and "fecha elaboracion" in enc:
                return True
        return False
    finally:
        wb.close()


def leer_movimiento(ruta, identificar_punto, ignorar):
    """Devuelve {fecha: ReporteSiigo} con un reporte por día (para R20, igual que
    el reporte de un día) que además trae los pagos de cada factura (R21).

    - La fecha de cada factura es la FECHA ELABORACIÓN (la de la factura). Si la
      FECHA CREACIÓN es de otro día, se avisa: alguien le cambió la fecha.
    - El punto de una línea de producto es su vendedor (como en "Ventas por
      vendedor"); el de un pago, el centro de costo de la factura.
    - Solo cuentan las facturas de venta."""
    import os
    archivo = os.path.basename(ruta)
    wb = openpyxl.load_workbook(ruta, data_only=True, read_only=True)
    filas = list(wb.worksheets[0].iter_rows(values_only=True))
    wb.close()
    fila_enc = next((i for i, f in enumerate(filas[:40])
                     if {"tipo transaccion", "fecha elaboracion"} <= {norm(v) for v in f if v}), None)
    if fila_enc is None:
        raise ValueError("No es el reporte 'Movimiento ventas y compras' de Siigo.")
    enc = [norm(v) for v in filas[fila_enc]]

    def col(*nombres):
        return next((enc.index(n) for n in nombres if n in enc), None)

    c = {k: col(*v) for k, v in {
        "tipo": ("tipo transaccion",), "factura": ("consecutivo", "numero comprobante"),
        "comprobante": ("numero comprobante",), "centro": ("centro costo",),
        "creada": ("fecha creacion",), "fecha": ("fecha elaboracion",), "registro": ("tipo de registro",),
        "codigo": ("codigo",), "nombre": ("nombre",), "vendedor": ("nombre vendedor",),
        "cantidad": ("cantidad",), "total": ("total",), "forma": ("forma pago",)}.items()}
    faltan = [k for k in ("tipo", "factura", "fecha", "registro", "cantidad", "total", "forma") if c[k] is None]
    if faltan:
        raise ValueError("El reporte de movimiento de Siigo no trae las columnas: " + ", ".join(faltan) + ".")

    def v(fila, k):
        return fila[c[k]] if c[k] is not None and c[k] < len(fila) else None

    def fecha_de(x):
        if isinstance(x, dt.datetime):
            return x.date()
        return x if isinstance(x, dt.date) else None

    ignorar_n = [norm(x) for x in ignorar]
    dias, otros_tipos, sin_punto, cruzadas = {}, {}, {}, {}
    movidas = set()
    puntos = set()
    for i, fila in enumerate(filas[fila_enc + 1:], start=fila_enc + 2):
        fila = list(fila)
        tipo = norm(v(fila, "tipo"))
        if not tipo or "procesado en" in tipo:
            continue
        if tipo != "factura de venta":
            otros_tipos[str(v(fila, "tipo"))] = otros_tipos.get(str(v(fila, "tipo")), 0) + 1
            continue
        fecha = fecha_de(v(fila, "fecha"))
        if fecha is None:
            continue
        rep = dias.get(fecha)
        if rep is None:
            rep = dias[fecha] = ReporteSiigo(archivo=archivo, desde=fecha, hasta=fecha, puntos=puntos)
        factura = f"{v(fila, 'comprobante') or ''} {v(fila, 'factura') or ''}".strip()
        centro = str(v(fila, "centro") or "")
        registro = norm(v(fila, "registro"))
        if registro.startswith("formas de pago"):
            punto = identificar_punto(centro) if centro else None
            total = v(fila, "total")
            if punto and isinstance(total, (int, float)) and total:
                puntos.add(punto)
                rep.pagos.append(PagoSiigo(fecha, punto, factura, str(v(fila, "forma") or "").strip(),
                                           float(total), i))
            creada = v(fila, "creada")
            if punto and isinstance(creada, dt.datetime) and creada.date() != fecha and factura not in movidas:
                movidas.add(factura)
                rep.fechas_cambiadas.append((factura, punto, creada))
            continue
        cant = v(fila, "cantidad")
        if not isinstance(cant, (int, float)) or not cant:
            continue
        vendedor = str(v(fila, "vendedor") or centro).strip()
        if any(x and x in norm(vendedor) for x in ignorar_n):
            continue
        punto = identificar_punto(vendedor) or (identificar_punto(centro) if centro else None)
        if punto is None:
            sin_punto[vendedor] = sin_punto.get(vendedor, 0) + cant
            continue
        # Los puntos "incluidos" salen de las facturas (centro de costo), no de un
        # vendedor suelto: un producto de Salitre en una factura de Plaza Imperial
        # no quiere decir que el reporte traiga las ventas de Salitre.
        p_centro = identificar_punto(centro) if centro else None
        if p_centro and p_centro != punto:
            clave = (vendedor, centro)
            cruzadas[clave] = cruzadas.get(clave, 0) + cant
        rep.lineas.append(LineaSiigo(punto, str(v(fila, "codigo") or "").strip(),
                                     str(v(fila, "nombre") or "").strip(), float(cant), i))
    avisos = []
    if otros_tipos:
        avisos.append("No se cuentan (no son facturas de venta): "
                      + ", ".join(f"{k} ({n} filas)" for k, n in otros_tipos.items()) + ".")
    for (vend, centro), n in cruzadas.items():
        avisos.append(f"{n:g} unidad(es) con vendedor '{vend}' en facturas de '{centro}': se cuentan para "
                      f"el punto del vendedor.")
    if sin_punto:
        avisos.append("Vendedores de Siigo que no reconozco como punto: " + ", ".join(sin_punto)
                      + ". Agrégalos como alias del punto.")
    if not dias:
        avisos.append("El reporte no trae facturas de venta.")
    return dias, avisos


# ---------------------------------------------------------------------------
# Unidades por clave para un punto (kits desarmados)
# ---------------------------------------------------------------------------
@dataclass
class UnidadesSiigo:
    por_clave: dict = field(default_factory=dict)      # clave -> unidades
    lineas_por_clave: dict = field(default_factory=dict)  # clave -> [LineaSiigo]
    a_eleccion: dict = field(default_factory=dict)     # "shampoo" -> unidades sin producto definido
    sin_mapeo: list = field(default_factory=list)      # [LineaSiigo]


def unidades_punto(reporte, punto, mapeo):
    u = UnidadesSiigo()
    for ln in reporte.lineas:
        if ln.punto != punto:
            continue
        kit = mapeo.kits.get(norm(ln.nombre))
        if kit:
            for c in kit:
                if c.a_eleccion:
                    u.a_eleccion[c.a_eleccion] = u.a_eleccion.get(c.a_eleccion, 0) + ln.unidades * c.cantidad
                    continue
                clave = mapeo.clave_componente(c.excel)
                if clave:
                    u.por_clave[clave] = u.por_clave.get(clave, 0) + ln.unidades * c.cantidad
                    u.lineas_por_clave.setdefault(clave, []).append(ln)
            continue
        clave = mapeo.clave_linea(ln.codigo, ln.nombre)
        if clave is None:
            u.sin_mapeo.append(ln)
            continue
        u.por_clave[clave] = u.por_clave.get(clave, 0) + ln.unidades
        u.lineas_por_clave.setdefault(clave, []).append(ln)
    return u
