# -*- coding: utf-8 -*-
"""Lee la venta por persona y día de una hoja resumen del Excel, según el perfil de la empresa.

El perfil va en perfil_fuente (fuente excel_dia), dentro de mapeo_columnas:

    "venta_persona": {
        "hoja": "DESC FACT",
        "columnas": {"fecha": ["FECHA", "v"], "persona": "ASESOR", "venta": "VENTA DIA", "facturas": "FACTURAS"},
        "separadores": "\\s+y\\s+|/|&|,|\\+|\\s-\\s",
        "dia_sin_venta": ["No abrió"]
    }

Cada columna acepta un nombre o una lista de nombres posibles: los Excel del cliente no se
corrigen, Tino tolera sus variaciones desde el perfil. "dia_sin_venta" son los textos que el
punto escribe cuando no abrió: ese día no tiene persona.

La meta del mes, si el libro la trae, también va en el perfil:

    "meta_mes": {"hoja": "METAS", "celda": "K2"}

"fecha" puede traer la fecha completa o solo el número del día: en ese caso el mes sale de
los días que trae el resto del libro. Un día con varias personas se reparte con la regla de
la empresa (empresa_config.equipo_reparto, ⚑). Montos en pesos enteros.
"""
import datetime as dt
import re
import unicodedata

SEPARADORES = r"\s+y\s+|/|&|,|\+|\s-\s"


def _norm(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def _numero(v):
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return v
    t = re.sub(r"[^0-9,.\-]", "", str(v))
    if not t:
        return None
    try:
        return float(t.replace(".", "").replace(",", ".")) if "," in t else float(t)
    except ValueError:
        return None


def es_dia_sin_venta(texto, perfil):
    """¿El texto dice que el punto no abrió (según el perfil de la empresa)?"""
    return _norm(texto) in {_norm(x) for x in (perfil or {}).get("dia_sin_venta", [])}


def personas(texto, separadores=SEPARADORES):
    """Los nombres de una celda: "Ana y Luisa" -> ["Ana", "Luisa"]."""
    partes = re.split(separadores, str(texto or "").strip(), flags=re.IGNORECASE)
    return [p.strip() for p in partes if p and p.strip()]


def repartir(venta, facturas, n, regla="partes_iguales"):
    """Reparte la venta (pesos enteros) y las facturas de un día entre n personas.
    Partes iguales: lo que sobra de dividir va de a un peso a las primeras, así la suma
    siempre da la venta del día."""
    if regla != "partes_iguales":
        raise ValueError(f"Regla de reparto desconocida: {regla}")
    base, sobra = divmod(venta, n)
    ventas = [base + (1 if i < sobra else 0) for i in range(n)]
    fact = None if facturas is None else round(facturas / n, 2)
    return [(v, fact) for v in ventas]


def leer(libro, perfil, fechas_libro, regla="partes_iguales"):
    """libro: openpyxl abierto (read_only, data_only). fechas_libro: fechas ISO que trae el
    resto del libro, para completar el mes cuando la hoja solo trae el número del día.
    Devuelve (filas, avisos). Cada fila: fecha, texto, venta, facturas, venta_dia,
    facturas_dia, personas_dia, fila_origen."""
    avisos = []
    hoja = next((n for n in libro.sheetnames if _norm(n) == _norm(perfil.get("hoja"))), None)
    if hoja is None:
        return [], [f"No está la hoja «{perfil.get('hoja')}» de la venta por persona."]
    # Cada columna puede tener varios nombres aceptados: los Excel del cliente no se corrigen,
    # Tino tolera sus variaciones (por ejemplo, un encabezado mal escrito en un punto).
    columnas = {k: [_norm(x) for x in (v if isinstance(v, list) else [v])]
                for k, v in (perfil.get("columnas") or {}).items()}
    faltan = [k for k in ("fecha", "persona", "venta") if k not in columnas]
    if faltan:
        return [], [f"El perfil de venta por persona no dice qué columna es: {', '.join(faltan)}."]

    ws = libro[hoja]
    filas = list(ws.iter_rows(min_row=1, max_row=600, max_col=40, values_only=True))
    enc, pos = None, {}
    for i, fila in enumerate(filas[:15]):
        textos = [_norm(v) for v in fila]
        if any(n in textos for n in columnas["fecha"]) and any(n in textos for n in columnas["persona"]):
            enc = i
            for campo, nombres_col in columnas.items():
                pos_campo = next((textos.index(n) for n in nombres_col if n in textos), None)
                if pos_campo is not None:
                    pos[campo] = pos_campo
            break
    if enc is None:
        return [], [f"Hoja «{hoja}»: no se encontró el encabezado de la fecha ({', '.join(columnas['fecha'])})."]

    meses = sorted({f[:7] for f in fechas_libro})
    mes = meses[0] if len(meses) == 1 else None
    separadores = perfil.get("separadores") or SEPARADORES
    salida = []
    for i, fila in enumerate(filas[enc + 1:], start=enc + 2):
        def celda(campo):
            return fila[pos[campo]] if campo in pos and pos[campo] < len(fila) else None
        bruto = celda("fecha")
        if isinstance(bruto, dt.datetime):
            fecha = bruto.date().isoformat()
        elif isinstance(bruto, dt.date):
            fecha = bruto.isoformat()
        elif isinstance(bruto, (int, float)) and 1 <= bruto <= 31 and float(bruto).is_integer():
            if mes is None:
                avisos.append(f"Hoja «{hoja}» fila {i}: trae solo el día y el libro no dice de qué mes es.")
                continue
            try:
                fecha = dt.date.fromisoformat(f"{mes}-{int(bruto):02d}").isoformat()
            except ValueError:
                continue
        else:
            continue
        venta = _numero(celda("venta"))
        if not venta:
            continue
        venta = int(round(venta))
        fact = _numero(celda("facturas"))
        fact = int(round(fact)) if fact is not None else None
        nombres = personas(celda("persona"), separadores)
        if es_dia_sin_venta(celda("persona"), perfil):
            avisos.append(f"Hoja «{hoja}» fila {i}: dice que el punto no abrió pero trae venta; queda sin persona.")
            nombres = ["(sin nombre)"]
        if not nombres:
            avisos.append(f"Hoja «{hoja}» fila {i}: hay venta pero no dice quién vendió.")
            nombres = ["(sin nombre)"]
        for nombre, (parte, fact_parte) in zip(nombres, repartir(venta, fact, len(nombres), regla)):
            salida.append({"fecha": fecha, "texto": nombre, "venta": parte, "facturas": fact_parte,
                           "venta_dia": venta, "facturas_dia": fact, "personas_dia": len(nombres),
                           "fila_origen": i})
    return salida, avisos


def _celda(ref):
    m = re.fullmatch(r"([A-Za-z]{1,3})([0-9]+)", str(ref or "").strip())
    if not m:
        return None
    col = 0
    for ch in m.group(1).upper():
        col = col * 26 + ord(ch) - 64
    return int(m.group(2)), col


def leer_meta(libro, perfil, fechas_libro):
    """La meta del mes del punto: (meta, avisos). meta = {desde, hasta, monto, fila_origen}
    o None. El período es el mes de los días que trae el libro."""
    if not perfil:
        return None, []
    hoja = next((n for n in libro.sheetnames if _norm(n) == _norm(perfil.get("hoja"))), None)
    pos = _celda(perfil.get("celda"))
    if hoja is None or pos is None:
        return None, [f"No está la meta del mes en «{perfil.get('hoja')}» {perfil.get('celda') or ''}."]
    fila, col = pos
    valor = None
    for f in libro[hoja].iter_rows(min_row=fila, max_row=fila, min_col=col, max_col=col, values_only=True):
        valor = _numero(f[0])
    meses = sorted({f[:7] for f in fechas_libro})
    if not valor or valor <= 0 or len(meses) != 1:
        return None, [] if not valor else ["La meta del mes no se guardó: el libro trae días de varios meses."]
    desde = dt.date.fromisoformat(meses[0] + "-01")
    hasta = (desde.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return {"desde": desde.isoformat(), "hasta": hasta.isoformat(), "monto": int(round(valor)), "fila_origen": fila}, []
