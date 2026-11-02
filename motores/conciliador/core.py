# -*- coding: utf-8 -*-
"""
Motor de procesamiento Bold / Redeban.
Genera un archivo con DOS hojas:
  1) Datos crudos limpios, ordenados y coloreados (equivalente al "post macro").
  2) Tabla resumen en las posiciones EXACTAS de PLANTILLAS_TRABAJO_IRINA,
     con tamaño dinámico según la cantidad real de días de cada bloque.
"""
import datetime as dt
import openpyxl
from openpyxl.utils import get_column_letter
from openpyxl.styles import PatternFill, Font

# ---------------------------------------------------------------------------
# Config fija (sacada de PLANTILLAS_TRABAJO_IRINA.xlsx)
# ---------------------------------------------------------------------------
BOLD_STORES = [
    "ALTAVISTA", "BANDERAS", "KENNEDY", "PLAZA IMPERIAL",
    "PORTAL AMERICAS", "PORTAL DORADO", "PORTAL SUBA",
]
REDEBAN_STORES = {
    "85": "PLAZA CLARO",
    "93": "PORTAL SUR",
    "19": "SALITRE",
    "35": "SANTAFÉ",
}
REDEBAN_STORE_ORDER = ["85", "93", "19", "35"]
FRANCHISE_ORDER = ["MASTERCARD", "VISA", "AMEX"]

MONEY_FMT = '"$"#,##0.00'
COMMISSION_RATE = 0.10

BOLD_FONT = Font(bold=True)
GREEN_FILL = PatternFill("solid", fgColor="92D050")

BOLD_STORE_COLORS = {
    "ALTAVISTA": "9DC3E6",
    "BANDERAS": "0070C0",
    "KENNEDY": "FFC000",
    "PLAZA IMPERIAL": "FF66FF",
    "PORTAL AMERICAS": "ED7D31",
    "PORTAL DORADO": "FF0000",
    "PORTAL SUBA": "A6A6A6",
}
REDEBAN_STORE_COLORS = {
    "PLAZA CLARO": "00B0F0",
    "PORTAL SUR": "ED7D31",
    "SALITRE": "7030A0",
    "SANTAFÉ": "FF66CC",
}

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _norm(s):
    if s is None:
        return ""
    return str(s).strip().upper().rstrip(".").strip()


# ---------------------------------------------------------------------------
# Detección / errores de formato
# ---------------------------------------------------------------------------
class FormatoNoReconocido(Exception):
    pass


def detect_file_type(path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    for ws in wb.worksheets:
        for r in range(1, min(8, ws.max_row) + 1):
            vals = [str(c.value).upper() if c.value else "" for c in ws[r]]
            joined = " ".join(vals)
            if "NOMBRE DEL DAT" in joined and "FECHA" in joined:
                return "bold"
            if "CODIGO ESTABLECIMIENTO" in joined and "FRANQUICIA" in joined:
                return "redeban"
    raise FormatoNoReconocido(
        "No se pudo identificar el archivo como Bold ni Redeban. "
        "Revisa que sea un reporte virgen sin modificar, o avísame si "
        "cambiaron otra vez el formato para actualizar el programa.")


def _header_row_and_map(ws, required_any):
    for r in range(1, min(10, ws.max_row) + 1):
        headers = {}
        for c in range(1, ws.max_column + 1):
            v = ws.cell(r, c).value
            if v is not None:
                headers[str(v).strip().upper()] = c
        if any(k in headers for k in required_any):
            return r, headers
    raise FormatoNoReconocido("No se encontró la fila de encabezados esperada.")


# ---------------------------------------------------------------------------
# Carga BOLD (soporta formato viejo y nuevo)
# ---------------------------------------------------------------------------
def load_bold_multi(paths):
    """Carga y combina varios archivos vírgenes de Bold (por ejemplo cuando
    un mes termina en fin de semana y el acumulado cae en el mes siguiente)."""
    all_rows, formatos, omitidas_total = [], set(), 0
    for path in paths:
        rows, formato, omitidas = load_bold(path)
        all_rows.extend(rows)
        formatos.add(formato)
        omitidas_total += omitidas
    return all_rows, " + ".join(sorted(formatos)), omitidas_total


def load_redeban_multi(paths):
    all_rows = []
    for path in paths:
        all_rows.extend(load_redeban(path))
    return all_rows


def load_bold(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    header_row, hmap = _header_row_and_map(ws, {"NOMBRE DEL DATÁFONO", "FECHA"})

    def col(*names):
        for n in names:
            if n in hmap:
                return hmap[n]
        return None

    needed = {
        "datafono": col("NOMBRE DEL DATÁFONO"),
        "fecha": col("FECHA"),
        "operacion": col("OPERACIÓN"),  # solo en el formato nuevo
        "compra": col("VALOR DE LA COMPRA"),
        "iva": col("IVA"),
        "total": col("VALOR TOTAL"),
        "retefuente": col("VALOR RETE FUENTE"),
        "reteiva": col("VALOR RETE IVA"),
        "reteica": col("VALOR RETE ICA"),
        "pct_comision": col("% COMISIÓN BOLD"),
        "comision_fija": col("COMISIÓN BOLD FIJA"),
        "total_deduccion": col("TOTAL DEDUCCIÓN"),
        "deposito": col("DEPOSITO EN CUENTA BOLD", "DEPOSITO EN SALDO DE VENTAS"),
    }
    required = ["datafono", "fecha", "compra", "iva", "total", "retefuente",
                "reteiva", "reteica", "pct_comision", "comision_fija",
                "total_deduccion", "deposito"]
    missing = [k for k in required if needed[k] is None]
    if missing:
        raise FormatoNoReconocido(
            "El archivo de Bold no tiene las columnas esperadas: "
            f"{', '.join(missing)}. Puede que Bold haya cambiado el formato "
            "de nuevo — avísame para actualizar el programa.")

    formato = "nuevo (con OPERACIÓN)" if needed["operacion"] else "clásico"

    rows = []
    omitidas = 0
    for r in range(header_row + 1, ws.max_row + 1):
        datafono = ws.cell(r, needed["datafono"]).value
        fecha_raw = ws.cell(r, needed["fecha"]).value
        if datafono is None or fecha_raw is None:
            continue
        if needed["operacion"]:
            op = ws.cell(r, needed["operacion"]).value
            if op is not None and str(op).strip().upper() != "COBRO EXITOSO":
                omitidas += 1
                continue
        if isinstance(fecha_raw, dt.datetime):
            fecha_completa = fecha_raw
        else:
            fecha_completa = dt.datetime.fromisoformat(str(fecha_raw)[:19])
        fecha = fecha_completa.date()
        rows.append({
            "NOMBRE DEL DATÁFONO": str(datafono).strip(),
            "NOMBRE DEL DATÁFONO_NORM": _norm(datafono),
            "FECHA": fecha,
            "Fecha antigua": fecha_completa,
            "VALOR DE LA COMPRA": ws.cell(r, needed["compra"]).value or 0,
            "IVA": ws.cell(r, needed["iva"]).value or 0,
            "VALOR TOTAL": ws.cell(r, needed["total"]).value or 0,
            "VALOR RETE FUENTE": ws.cell(r, needed["retefuente"]).value or 0,
            "VALOR RETE IVA": ws.cell(r, needed["reteiva"]).value or 0,
            "VALOR RETE ICA": ws.cell(r, needed["reteica"]).value or 0,
            "% COMISIÓN BOLD": ws.cell(r, needed["pct_comision"]).value or 0,
            "COMISIÓN BOLD FIJA": ws.cell(r, needed["comision_fija"]).value or 0,
            "TOTAL DEDUCCIÓN": ws.cell(r, needed["total_deduccion"]).value or 0,
            "DEPOSITO EN CUENTA BOLD": ws.cell(r, needed["deposito"]).value or 0,
        })
    return rows, formato, omitidas


# ---------------------------------------------------------------------------
# Carga REDEBAN
# ---------------------------------------------------------------------------
def _parse_redeban_date(v):
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    s = str(v).strip()
    if len(s) == 8 and s.isdigit():
        return dt.date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return dt.datetime.fromisoformat(s).date()


def load_redeban(path):
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    header_row, hmap = _header_row_and_map(ws, {"CODIGO ESTABLECIMIENTO", "FRANQUICIA"})

    def col(name):
        return hmap.get(name)

    needed = {
        "estab": col("CODIGO ESTABLECIMIENTO"),
        "franquicia": col("FRANQUICIA"),
        "f_trans": col("FECHA DE TRANSACCION"),
        "f_canje": col("FECHA DE CANJE"),
        "compra": col("VALOR COMPRA"),
        "iva": col("VALOR IVA"),
        "total": col("VALOR TOTAL"),
        "comision": col("VALOR COMISION"),
        "retefuente": col("VALOR RETEFUENTE"),
        "reteiva": col("VALOR RETE IVA"),
        "reteica": col("VALOR RTE ICA"),
        "neto": col("VALOR NETO"),
    }
    missing = [k for k, v in needed.items() if v is None]
    if missing:
        raise FormatoNoReconocido(
            f"El archivo de Redeban no tiene las columnas esperadas: {missing}. "
            "Puede que hayan cambiado el formato — avísame para actualizarlo.")

    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        estab = ws.cell(r, needed["estab"]).value
        franq = ws.cell(r, needed["franquicia"]).value
        if estab is None or franq is None:
            continue
        estab_code = str(estab).strip()[-2:]
        rows.append({
            "CODIGO ESTABLECIMIENTO": estab_code,
            "FRANQUICIA": str(franq).strip().upper(),
            "FECHA DE TRANSACCION": _parse_redeban_date(ws.cell(r, needed["f_trans"]).value),
            "FECHA DE CANJE": _parse_redeban_date(ws.cell(r, needed["f_canje"]).value),
            "VALOR COMPRA": ws.cell(r, needed["compra"]).value or 0,
            "VALOR IVA": ws.cell(r, needed["iva"]).value or 0,
            "VALOR TOTAL": ws.cell(r, needed["total"]).value or 0,
            "VALOR COMISION": abs(ws.cell(r, needed["comision"]).value or 0),
            "VALOR RETEFUENTE": abs(ws.cell(r, needed["retefuente"]).value or 0),
            "VALOR RETE IVA": abs(ws.cell(r, needed["reteiva"]).value or 0),
            "VALOR RTE ICA": abs(ws.cell(r, needed["reteica"]).value or 0),
            "VALOR NETO": ws.cell(r, needed["neto"]).value or 0,
        })
    return rows


# ---------------------------------------------------------------------------
# Fechas / bloques
# ---------------------------------------------------------------------------
def get_available_dates(rows, kind):
    key = "FECHA" if kind == "bold" else "FECHA DE CANJE"
    return sorted({r[key] for r in rows})


def is_special(date_, holidays):
    # weekday(): lunes=0 ... sábado=5, domingo=6. El viernes (4) SÍ es día
    # hábil de consignación — solo sábado/domingo (y festivos marcados a
    # mano) no lo son. Antes incluía el viernes por error, lo que hacía que
    # el jueves se "colara" en el bloque del fin de semana (jueves-domingo
    # en vez de solo viernes-sábado-domingo).
    return date_.weekday() in (5, 6) or date_ in holidays


def next_business_day(date_, holidays):
    d = date_ + dt.timedelta(days=1)
    while is_special(d, holidays):
        d += dt.timedelta(days=1)
    return d


def build_date_blocks(all_dates, holidays):
    """Agrupa las fechas de transacción de Bold por su fecha real de
    consignación (próximo día hábil, saltando fines de semana/festivos).
    Todas las fechas que consignan el mismo día quedan en el mismo bloque
    ('grande' si son más de una, 'chico'/diario si es solo una)."""
    by_settlement = {}
    for d in all_dates:
        settlement = next_business_day(d, holidays)
        by_settlement.setdefault(settlement, []).append(d)
    blocks = []
    for settlement in sorted(by_settlement):
        days = sorted(by_settlement[settlement])
        blocks.append({"settlement": settlement, "days": days,
                        "is_big": len(days) > 1})
    return blocks


def redeban_blocks(rows):
    """Cada valor de FECHA DE CANJE ya es un bloque natural (el banco salta
    fines de semana). Si dentro de un bloque hay >1 fecha de transacción,
    es un bloque grande (fin de semana/festivo)."""
    by_canje = {}
    for r in rows:
        by_canje.setdefault(r["FECHA DE CANJE"], []).append(r)
    blocks = []
    for canje_date in sorted(by_canje):
        brows = by_canje[canje_date]
        tdays = sorted({r["FECHA DE TRANSACCION"] for r in brows})
        blocks.append({"canje": canje_date, "rows": brows, "days": tdays,
                        "is_big": len(tdays) > 1})
    return blocks


# ---------------------------------------------------------------------------
# Nombre de archivo
# ---------------------------------------------------------------------------
def build_filename(kind, date_start, date_end):
    """date_start/date_end deben ser las fechas de SALIDA (fecha de entrada
    en Bold, fecha de canje en Redeban), no las fechas de la transacción."""
    if date_start == date_end:
        rango = f"{date_start.day} {MESES_ES[date_start.month-1]}"
    elif date_start.month == date_end.month:
        rango = f"{date_start.day} a {date_end.day} {MESES_ES[date_start.month-1]}"
    else:
        rango = (f"{date_start.day} {MESES_ES[date_start.month-1]} a "
                  f"{date_end.day} {MESES_ES[date_end.month-1]}")
    label = "BOLD-REDEBAN" if kind == "bold_redeban" else kind.upper()
    return f"{label} {rango}.xlsx"


# ---------------------------------------------------------------------------
# Utilidades de escritura
# ---------------------------------------------------------------------------
def _row_ranges(rows_list):
    rows_list = sorted(rows_list)
    ranges = []
    start = prev = rows_list[0]
    for r in rows_list[1:]:
        if r == prev + 1:
            prev = r
        else:
            ranges.append((start, prev))
            start = prev = r
    ranges.append((start, prev))
    return ranges


def _sumformula(sheet_name, src_col, ranges):
    parts = []
    for a, b in ranges:
        cl = get_column_letter(src_col)
        if a == b:
            parts.append(f"'{sheet_name}'!{cl}{a}")
        else:
            parts.append(f"SUM('{sheet_name}'!{cl}{a}:{cl}{b})")
    return "=+" + "+".join(parts)


def _autosize(ws, width=16):
    for c in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(c)].width = width


# ---------------------------------------------------------------------------
# Hoja de datos crudos - BOLD
# ---------------------------------------------------------------------------
RAW_SHEET_BOLD = "TRANSACCIONES"
RAW_SHEET_REDEBAN = "Reporte Conciliar"
AGG_SHEET_BOLD = "BOLD"
AGG_SHEET_REDEBAN = "REDEBAN"


def write_bold_raw_sheet(wb, rows, date_start, date_end):
    ws = wb.create_sheet(RAW_SHEET_BOLD)
    headers = ["NOMBRE DEL DATÁFONO", "FECHA", "Fecha antigua", "VALOR DE LA COMPRA",
               "IVA", "VALOR TOTAL", "VALOR RETE FUENTE", "VALOR RETE IVA",
               "VALOR RETE ICA", "% COMISIÓN BOLD", "COMISIÓN BOLD FIJA",
               "TOTAL DEDUCCIÓN", "DEPOSITO EN CUENTA BOLD"]
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h).font = BOLD_FONT

    rows_sorted = sorted(rows, key=lambda x: (x["FECHA"], x["NOMBRE DEL DATÁFONO"]))
    money_cols = [4, 5, 6, 7, 8, 9, 11, 12, 13]
    r = 2
    for row in rows_sorted:
        c1 = ws.cell(r, 1, row["NOMBRE DEL DATÁFONO"])
        color = BOLD_STORE_COLORS.get(row["NOMBRE DEL DATÁFONO_NORM"])
        if color:
            c1.fill = PatternFill("solid", fgColor=color)
        ws.cell(r, 2, row["FECHA"].isoformat())
        ws.cell(r, 3, row["Fecha antigua"])
        ws.cell(r, 4, row["VALOR DE LA COMPRA"])
        ws.cell(r, 5, row["IVA"])
        ws.cell(r, 6, row["VALOR TOTAL"])
        ws.cell(r, 7, row["VALOR RETE FUENTE"])
        ws.cell(r, 8, row["VALOR RETE IVA"])
        ws.cell(r, 9, row["VALOR RETE ICA"])
        ws.cell(r, 10, row["% COMISIÓN BOLD"])
        ws.cell(r, 11, row["COMISIÓN BOLD FIJA"])
        ws.cell(r, 12, row["TOTAL DEDUCCIÓN"])
        ws.cell(r, 13, row["DEPOSITO EN CUENTA BOLD"])
        for mc in money_cols:
            ws.cell(r, mc).number_format = MONEY_FMT
        if not (date_start <= row["FECHA"] <= date_end):
            ws.row_dimensions[r].hidden = True
        r += 1
    _autosize(ws)
    return ws, rows_sorted


def _write_bold_agg_table(ws, start_row, store_map, settlement_date):
    """store_map: {store: [(day, [row_indices_in_raw_sheet])...]}.
    Todas las filas del bloque comparten la MISMA fecha de entrada
    (settlement_date), porque el banco consigna todo el bloque junto."""
    header_r = start_row
    headers = ["NOMBRE DEL DATÁFONO", "FECHA VENTA", "FECHA ENTRADA", "VALOR TOTAL",
               "VALOR RETE FUENTE", "VALOR RETE IVA", "VALOR RETE ICA",
               "% COMISIÓN BOLD", "COMISIÓN BOLD FIJA", "TOTAL DEDUCCIÓN",
               "DEPOSITO EN CUENTA BOLD", "DEDUCIDO"]
    for c, h in enumerate(headers, 1):
        ws.cell(header_r, c, h).font = BOLD_FONT
    ws.cell(header_r, 13, COMMISSION_RATE)

    row = header_r + 1
    first_data_row = row
    for store in BOLD_STORES:
        color = BOLD_STORE_COLORS.get(store)
        for day, src_rows in store_map.get(store, []):
            lc = ws.cell(row, 1, store)
            if color:
                lc.fill = PatternFill("solid", fgColor=color)
            ws.cell(row, 2, day.isoformat())
            ws.cell(row, 3, settlement_date.isoformat())
            if src_rows:
                ranges = _row_ranges(src_rows)
                for offset, src_col in zip(range(4, 10), [6, 7, 8, 9, 10, 11]):
                    ws.cell(row, offset, _sumformula(RAW_SHEET_BOLD, src_col, ranges))
            J = 10  # TOTAL DEDUCCIÓN
            K = 11  # DEPOSITO
            ws.cell(row, J, f"=SUM(E{row}:I{row})")
            ws.cell(row, K, f"=D{row}-J{row}")
            for mc in range(4, 12):
                ws.cell(row, mc).number_format = MONEY_FMT
            row += 1
    last_data_row = row - 1

    total_row = row
    ws.cell(total_row, 2, "TOTALES").font = BOLD_FONT
    for col_idx in range(4, 12):
        cl = get_column_letter(col_idx)
        ws.cell(total_row, col_idx, f"=SUM({cl}{first_data_row}:{cl}{last_data_row})")
        ws.cell(total_row, col_idx).number_format = MONEY_FMT
    ws.cell(total_row, 12, f"=K{total_row}*M{header_r}")
    ws.cell(total_row, 12).number_format = MONEY_FMT

    total_row2 = total_row + 1
    ws.cell(total_row2, 7, f"=SUM(E{total_row}:G{total_row})").number_format = MONEY_FMT
    ws.cell(total_row2, 9, f"=SUM(H{total_row}:I{total_row})").number_format = MONEY_FMT
    ws.cell(total_row2, 11, f"=K{total_row}-L{total_row}").number_format = MONEY_FMT

    return total_row2, total_row  # última fila usada, fila de TOTALES (col K = depósito)


def write_bold_agg_sheet(wb, rows_sorted, date_start, date_end, holidays):
    """date_start/date_end filtran por FECHA DE TRANSACCIÓN (lo que el
    usuario elige). Devuelve (ws, settlement_dates, verificacion) donde
    verificacion es una lista de dicts para la conciliación bancaria."""
    ws = wb.create_sheet(AGG_SHEET_BOLD)

    sel_rows = [row for row in rows_sorted if date_start <= row["FECHA"] <= date_end]
    dates = sorted({row["FECHA"] for row in sel_rows})
    blocks = build_date_blocks(dates, holidays)

    row_index = {id(row): i + 2 for i, row in enumerate(rows_sorted)}

    settlement_dates = []
    verificacion = []

    def _write_block(block):
        store_map = {}
        store_breakdown = {}
        computed_total = 0.0
        for store in BOLD_STORES:
            entries = []
            store_total = 0.0
            for day in block["days"]:
                matching = [r for r in sel_rows if r["FECHA"] == day
                            and r["NOMBRE DEL DATÁFONO_NORM"] == store]
                src_rows = [row_index[id(r)] for r in matching]
                day_total = sum(r["DEPOSITO EN CUENTA BOLD"] for r in matching)
                computed_total += day_total
                store_total += day_total
                entries.append((day, src_rows))
            store_map[store] = entries
            if store_total:
                store_breakdown[store] = store_total
        last, total_row = _write_bold_agg_table(ws, cursor[0], store_map, block["settlement"])
        settlement_dates.append(block["settlement"])
        verificacion.append({
            "settlement_date": block["settlement"],
            "computed_total": computed_total,
            "cell": f"K{total_row}",
            # store_breakdown: {tienda: monto} de ese bloque, solo tiendas con
            # movimiento — el depósito de Bold llega consolidado (una sola
            # línea en el banco por bloque), así que no hay un "bank_total"
            # por tienda; se usa para prorratear cuando el bloque no cuadra.
            "store_breakdown": store_breakdown,
        })
        cursor[0] = last + 2

    cursor = [1]
    for block in sorted(blocks, key=lambda b: b["settlement"]):
        _write_block(block)

    _autosize(ws)
    return ws, settlement_dates, verificacion


# ---------------------------------------------------------------------------
# Hoja de datos crudos - REDEBAN
# ---------------------------------------------------------------------------
def write_redeban_raw_sheet(wb, rows, date_start, date_end):
    ws = wb.create_sheet(RAW_SHEET_REDEBAN)
    headers = ["CODIGO ESTABLECIMIENTO", "FRANQUICIA", "FECHA DE TRANSACCION",
               "FECHA DE CANJE", "VALOR COMPRA", "VALOR IVA", "VALOR TOTAL",
               "VALOR COMISION", "VALOR RETEFUENTE", "VALOR RETE IVA",
               "VALOR RTE ICA", "VALOR NETO"]
    for c, h in enumerate(headers, 1):
        ws.cell(1, c, h).font = BOLD_FONT

    franq_rank = {f: i for i, f in enumerate(FRANCHISE_ORDER)}
    rows_sorted = sorted(rows, key=lambda x: (
        x["FECHA DE CANJE"], x["CODIGO ESTABLECIMIENTO"],
        franq_rank.get(x["FRANQUICIA"], 99), x["FECHA DE TRANSACCION"]))

    money_cols = [5, 6, 7, 8, 9, 10, 11, 12]
    r = 2
    for row in rows_sorted:
        c1 = ws.cell(r, 1, row["CODIGO ESTABLECIMIENTO"])
        store = REDEBAN_STORES.get(row["CODIGO ESTABLECIMIENTO"])
        color = REDEBAN_STORE_COLORS.get(store)
        if color:
            c1.fill = PatternFill("solid", fgColor=color)
        ws.cell(r, 2, row["FRANQUICIA"])
        ws.cell(r, 3, row["FECHA DE TRANSACCION"])
        ws.cell(r, 4, row["FECHA DE CANJE"])
        ws.cell(r, 5, row["VALOR COMPRA"])
        ws.cell(r, 6, row["VALOR IVA"])
        ws.cell(r, 7, row["VALOR TOTAL"])
        ws.cell(r, 8, row["VALOR COMISION"])
        ws.cell(r, 9, row["VALOR RETEFUENTE"])
        ws.cell(r, 10, row["VALOR RETE IVA"])
        ws.cell(r, 11, row["VALOR RTE ICA"])
        ws.cell(r, 12, row["VALOR NETO"])
        for mc in money_cols:
            ws.cell(r, mc).number_format = MONEY_FMT
        if not (date_start <= row["FECHA DE CANJE"] <= date_end):
            ws.row_dimensions[r].hidden = True
        r += 1
    _autosize(ws)
    return ws, rows_sorted


def _write_redeban_agg_table(ws, start_row, block, row_index_lookup):
    """block: {'canje':date,'rows':[...],'days':[...],'is_big':bool}.
    Devuelve (total_row, verif_entries) donde verif_entries es una lista de
    dicts {code,franquicia,canje_date,computed_total,rows:[filas escritas]}
    para la conciliación bancaria."""
    header_r = start_row
    headers = ["PUNTO DE VENTA", "FECHA", "FRANQUICIA", None, "Valor venta",
               "VALOR COMISION", "VALOR RETEFUENTE", "VALOR RETE IVA",
               "VALOR RTE ICA", "TOTAL DESCUENTOS", "TOTAL A TRANSFERIR",
               "Fecha transferencia"]
    for c, h in enumerate(headers, 1):
        if h is not None:
            ws.cell(header_r, c, h).font = BOLD_FONT

    days_for_breakdown = block["days"] if block["is_big"] else [block["days"][0]]
    canje_date = block["canje"]

    row = header_r + 1
    first_row = row
    verif_entries = []
    for code in REDEBAN_STORE_ORDER:
        store_name = REDEBAN_STORES[code]
        color = REDEBAN_STORE_COLORS.get(store_name)
        store_first_row = row
        for fi, franq in enumerate(FRANCHISE_ORDER):
            franq_rows = []
            computed_total = 0.0
            for day in days_for_breakdown:
                key = (code, franq, day)
                src_rows = row_index_lookup.get(key, [])
                if fi == 0 and day == days_for_breakdown[0]:
                    lc = ws.cell(row, 1, store_name)
                    if color:
                        lc.fill = PatternFill("solid", fgColor=color)
                if fi == 1 and day == days_for_breakdown[0]:
                    ws.cell(row, 1, int(code))
                ws.cell(row, 2, day)
                ws.cell(row, 3, franq)
                if src_rows:
                    ranges = _row_ranges(src_rows)
                    for offset, src_col in zip(range(5, 10), [7, 8, 9, 10, 11]):
                        ws.cell(row, offset, _sumformula(RAW_SHEET_REDEBAN, src_col, ranges))
                ws.cell(row, 10, f"=SUM(F{row}:I{row})")
                ws.cell(row, 11, f"=E{row}-J{row}")
                ws.cell(row, 12, canje_date)
                for mc in range(5, 12):
                    if mc != 12:
                        ws.cell(row, mc).number_format = MONEY_FMT
                matching = [r for r in block["rows"]
                            if r["CODIGO ESTABLECIMIENTO"] == code
                            and r["FRANQUICIA"] == franq
                            and r["FECHA DE TRANSACCION"] == day]
                venta = sum(r["VALOR TOTAL"] for r in matching)
                desc = sum(r["VALOR COMISION"] + r["VALOR RETEFUENTE"] +
                           r["VALOR RETE IVA"] + r["VALOR RTE ICA"] for r in matching)
                computed_total += venta - desc
                franq_rows.append(row)
                row += 1
            verif_entries.append({
                "code": code, "franquicia": franq, "canje_date": canje_date,
                "computed_total": computed_total, "rows": franq_rows,
            })
        store_last_row = row - 1
        if not block["is_big"]:
            ws.cell(store_last_row, 4, f"=SUM(E{store_first_row}:E{store_last_row})")
            ws.cell(store_last_row, 4).number_format = MONEY_FMT
    last_row = row - 1

    total_row = row
    ws.cell(total_row, 11, f"=SUM(K{first_row}:K{last_row})").number_format = MONEY_FMT
    return total_row, verif_entries


def write_redeban_agg_sheet(wb, rows_sorted, date_start, date_end):
    ws = wb.create_sheet(AGG_SHEET_REDEBAN)

    sel_rows = [row for row in rows_sorted if date_start <= row["FECHA DE CANJE"] <= date_end]
    row_index = {id(row): i + 2 for i, row in enumerate(rows_sorted)}

    by_canje = {}
    for r in sel_rows:
        by_canje.setdefault(r["FECHA DE CANJE"], []).append(r)
    blocks = []
    for canje_date in sorted(by_canje):
        brows = by_canje[canje_date]
        tdays = sorted({r["FECHA DE TRANSACCION"] for r in brows})
        blocks.append({"canje": canje_date, "rows": brows, "days": tdays,
                        "is_big": len(tdays) > 1})

    canje_dates = []
    verificacion = []
    cursor = 1
    # bloques en orden cronológico de fecha de canje (ya vienen ordenados así)
    for block in blocks:
        lookup = {}
        for r in block["rows"]:
            key = (r["CODIGO ESTABLECIMIENTO"], r["FRANQUICIA"], r["FECHA DE TRANSACCION"])
            lookup.setdefault(key, []).append(row_index[id(r)])
        last, verif = _write_redeban_agg_table(ws, cursor, block, lookup)
        canje_dates.append(block["canje"])
        verificacion.extend(verif)
        cursor = last + 2

    _autosize(ws)
    return ws, canje_dates, verificacion


# ---------------------------------------------------------------------------
# API de alto nivel
# ---------------------------------------------------------------------------
def process_range(paths, date_start, date_end, out_path, holidays=None):
    """Compatibilidad con la versión anterior: un solo tipo de archivo(s)."""
    if isinstance(paths, str):
        paths = [paths]
    kinds = {detect_file_type(p) for p in paths}
    if len(kinds) > 1:
        raise FormatoNoReconocido(
            "Estás mezclando archivos de Bold y Redeban con la función antigua. "
            "Usa process_combined en su lugar.")
    kind = kinds.pop()
    bold_paths = paths if kind == "bold" else []
    redeban_paths = paths if kind == "redeban" else []
    return process_combined(bold_paths, redeban_paths, date_start, date_end, out_path, holidays)


def process_combined(bold_paths, redeban_paths, date_start, date_end, out_path, holidays=None):
    """Genera UN SOLO archivo con las hojas de Bold y/o Redeban que apliquen,
    según qué listas de archivos vengan con contenido. Al menos una de las
    dos listas debe tener archivos.
    Devuelve (kind, info):
      kind = 'bold', 'redeban' o 'bold_redeban'
      info incluye 'settlement_start'/'settlement_end' (rango combinado de
      fechas de salida) y, por separado, 'verificacion_bold' y
      'verificacion_redeban' (cada una vacía si ese tipo no se incluyó),
      listas para la conciliación bancaria."""
    holidays = holidays or set()
    if not bold_paths and not redeban_paths:
        raise FormatoNoReconocido("No se recibió ningún archivo para procesar.")

    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    info = {
        "formato": None, "omitidas": 0,
        "verificacion_bold": [], "verificacion_redeban": [],
        "rows_sorted_bold": None, "rows_sorted_redeban": None,
    }
    settlements = []

    if bold_paths:
        rows, formato, omitidas = load_bold_multi(bold_paths)
        raw_ws, rows_sorted = write_bold_raw_sheet(wb, rows, date_start, date_end)
        _, settlement_dates, verificacion = write_bold_agg_sheet(
            wb, rows_sorted, date_start, date_end, holidays)
        info["formato"] = formato
        info["omitidas"] = omitidas
        info["verificacion_bold"] = verificacion
        info["rows_sorted_bold"] = rows_sorted
        settlements.extend(settlement_dates)

    if redeban_paths:
        rows = load_redeban_multi(redeban_paths)
        raw_ws, rows_sorted = write_redeban_raw_sheet(wb, rows, date_start, date_end)
        _, canje_dates, verificacion = write_redeban_agg_sheet(wb, rows_sorted, date_start, date_end)
        info["verificacion_redeban"] = verificacion
        info["rows_sorted_redeban"] = rows_sorted
        settlements.extend(canje_dates)

    info["settlement_start"] = min(settlements) if settlements else date_start
    info["settlement_end"] = max(settlements) if settlements else date_end

    if bold_paths and redeban_paths:
        kind = "bold_redeban"
    elif bold_paths:
        kind = "bold"
    else:
        kind = "redeban"

    wb.save(out_path)
    return kind, info
