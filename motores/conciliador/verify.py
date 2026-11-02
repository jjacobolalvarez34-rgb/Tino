# -*- coding: utf-8 -*-
"""
Verificación contra los movimientos de Bancolombia.
Lee el PDF de movimientos, ubica las líneas de "PAGO INTERBANC" (Bold) y
"ABONO NETO MASTER/VISA/AMEX EST. AFILIADOS <código>" (Redeban), las compara
contra lo calculado por el motor, y:
  - colorea en el Excel la celda del total (verde = coincide, rojo = no).
  - dibuja una línea verde/roja debajo del valor correspondiente en el PDF.
"""
import re
import datetime as dt

import pdfplumber
import pymupdf as fitz  # PyMuPDF (alias 'fitz' por costumbre, sin el warning de deprecación)
import openpyxl
from openpyxl.styles import PatternFill

from itertools import combinations

GREEN_FILL = PatternFill("solid", fgColor="C6EFCE")
RED_FILL = PatternFill("solid", fgColor="FFC7CE")
AMBER_FILL = PatternFill("solid", fgColor="FFEB9C")
TOLERANCE = 50  # pesos de margen por redondeos
MAX_CRUCE = 3    # hasta cuántas filas se combinan buscando que cuadren juntas

DATE_RE = re.compile(r"^\d{4}/\d{2}/\d{2}$")
CODE_RE = re.compile(r"^\d{8}$")


def _to_float(txt):
    return float(txt.replace(",", ""))


def _cluster_rows(words, tol=4):
    words_sorted = sorted(words, key=lambda w: w["top"])
    rows, cur, cur_top = [], [], None
    for w in words_sorted:
        if cur_top is None or w["top"] - cur_top <= tol:
            cur.append(w)
            cur_top = cur_top if cur_top is not None else w["top"]
        else:
            rows.append(cur)
            cur, cur_top = [w], w["top"]
    if cur:
        rows.append(cur)
    return rows


def parse_bancolombia_pdf(path):
    """Devuelve una lista de dicts:
    {page, date, tipo:'bold'|'redeban', code, franquicia, amount, bbox}
    bbox = (x0, top, x1, bottom) del texto del VALOR en esa línea, para
    poder dibujar la marca en el PDF."""
    entries = []
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages):
            words = page.extract_words()
            rows = _cluster_rows(words)
            for row in rows:
                row_sorted = sorted(row, key=lambda w: w["x0"])
                texts = [w["text"] for w in row_sorted]
                if not texts or not DATE_RE.match(texts[0]):
                    continue
                date = dt.date.fromisoformat(texts[0].replace("/", "-"))
                line = " ".join(texts)
                amount_word = row_sorted[-1]
                try:
                    amount = _to_float(amount_word["text"])
                except ValueError:
                    continue
                bbox = (amount_word["x0"], amount_word["top"],
                        amount_word["x1"], amount_word["bottom"])

                if "PAGO INTERBANC" in line and "BOLD" in line.upper():
                    entries.append({"page": pno, "date": date, "tipo": "bold",
                                     "code": None, "franquicia": None,
                                     "amount": amount, "bbox": bbox, "line": line})
                    continue

                m = re.search(r"ABONO NETO (MASTER|VISA|AMEX).*?(\d{8})", line)
                if m and "EST" in line.upper():
                    franquicia = m.group(1)
                    if franquicia == "MASTER":
                        franquicia = "MASTERCARD"
                    code = m.group(2)[-2:]
                    entries.append({"page": pno, "date": date, "tipo": "redeban",
                                     "code": code, "franquicia": franquicia,
                                     "amount": amount, "bbox": bbox, "line": line})
    return entries


def match_bold(bank_entries, verificacion):
    """verificacion: lista de dicts de core.write_bold_agg_sheet
    ({settlement_date, computed_total, cell}). Devuelve la misma lista con
    'matched' (bool) y 'bank_entries_used' añadidos."""
    by_date = {}
    for e in bank_entries:
        if e["tipo"] == "bold":
            by_date.setdefault(e["date"], []).append(e)

    results = []
    for v in verificacion:
        candidates = by_date.get(v["settlement_date"], [])
        bank_total = sum(c["amount"] for c in candidates)
        target_full = v["computed_total"]
        target_90 = v["computed_total"] * 0.9
        matched = (abs(bank_total - target_full) <= TOLERANCE or
                   abs(bank_total - target_90) <= TOLERANCE)
        results.append({**v, "matched": matched, "bank_total": bank_total,
                         "bank_entries_used": candidates})
    return results


def match_redeban(bank_entries, verificacion):
    """verificacion: lista de dicts de core.write_redeban_agg_sheet
    ({code, franquicia, canje_date, computed_total, rows}).

    Primera pasada: match exacto por (código, franquicia, fecha de canje).
    Segunda pasada ('cruce'): a veces el banco reparte el abono de una
    franquicia en dos consignaciones con fecha distinta (por corte de
    horario), así que 2-3 filas individualmente no cuadran pero SU SUMA sí.
    Cuando eso pasa, se marcan como 'cruzado' (ámbar) en vez de rojo, y se
    anota con cuáles otras fechas cuadra."""
    by_key = {}
    for e in bank_entries:
        if e["tipo"] == "redeban":
            key = (e["code"], e["franquicia"], e["date"])
            by_key.setdefault(key, []).append(e)

    results = []
    for v in verificacion:
        key = (v["code"], v["franquicia"], v["canje_date"])
        candidates = by_key.get(key, [])
        bank_total = sum(c["amount"] for c in candidates)
        matched = abs(bank_total - v["computed_total"]) <= TOLERANCE
        no_data = bank_total == 0 and v["computed_total"] == 0
        results.append({**v, "matched": matched, "bank_total": bank_total,
                         "bank_entries_used": list(candidates), "no_data": no_data,
                         "cruzado": False, "nota": None})

    # --- segunda pasada: buscar cruces entre filas de la MISMA franquicia y
    # el MISMO código de establecimiento que individualmente no cuadraron ---
    groups = {}
    for i, r in enumerate(results):
        if r["matched"] or r["no_data"]:
            continue
        groups.setdefault((r["code"], r["franquicia"]), []).append(i)

    for (code, franq), idxs in groups.items():
        if len(idxs) < 2:
            continue
        for n in range(2, min(MAX_CRUCE, len(idxs)) + 1):
            found = False
            for combo in combinations(idxs, n):
                if any(results[i]["cruzado"] for i in combo):
                    continue  # ya resuelto por una combinación más chica
                bank_sum = sum(results[i]["bank_total"] for i in combo)
                comp_sum = sum(results[i]["computed_total"] for i in combo)
                if abs(bank_sum - comp_sum) <= TOLERANCE:
                    fechas = ", ".join(results[i]["canje_date"].isoformat() for i in combo)
                    for i in combo:
                        results[i]["cruzado"] = True
                        results[i]["nota"] = f"Cuadra junto con: {fechas}"
                        results[i]["bank_entries_used"] = [
                            e for j in combo for e in results[j]["bank_entries_used"]]
                    found = True
            if found:
                continue
    return results


def color_excel_bold(xlsx_path, sheet_name, results):
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[sheet_name]
    for r in results:
        cell = ws[r["cell"]]
        cell.fill = GREEN_FILL if r["matched"] else RED_FILL
    wb.save(xlsx_path)


def color_excel_redeban(xlsx_path, sheet_name, results):
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb[sheet_name]
    for r in results:
        if r.get("no_data"):
            continue
        if r.get("cruzado"):
            fill = AMBER_FILL
        else:
            fill = GREEN_FILL if r["matched"] else RED_FILL
        for row_num in r["rows"]:
            ws.cell(row_num, 11).fill = fill  # columna K = TOTAL A TRANSFERIR
            if r.get("nota"):
                ws.cell(row_num, 13, r["nota"])  # columna M, libre, al ladito
    wb.save(xlsx_path)


def annotate_pdf(pdf_path, all_results, out_pdf_path):
    """Dibuja una línea de color bajo el valor de cada movimiento bancario
    que participó en la verificación: verde = coincide, ámbar = coincide
    en conjunto con otra fecha (cruce), rojo = no coincide."""
    doc = fitz.open(pdf_path)
    green = (0.024, 0.541, 0.110)
    amber = (0.855, 0.647, 0.125)
    red = (0.859, 0.204, 0.145)
    for r in all_results:
        if r.get("cruzado"):
            color = amber
        elif r["matched"]:
            color = green
        else:
            color = red
        for e in r.get("bank_entries_used", []):
            x0, top, x1, bottom = e["bbox"]
            page = doc[e["page"]]
            y = bottom + 1
            page.draw_line((x0, y), (x1, y), color=color, width=1.6)
    doc.save(out_pdf_path)
    doc.close()


def run_verification(kind, xlsx_path, sheet_name, verificacion, bank_pdf_path, out_pdf_path):
    """Punto de entrada para un solo tipo (compatibilidad). Para reportes
    combinados usa run_verification_multi."""
    jobs = [(kind, sheet_name, verificacion)]
    return run_verification_multi(jobs, xlsx_path, bank_pdf_path, out_pdf_path)


def run_verification_multi(jobs, xlsx_path, bank_pdf_path, out_pdf_path):
    """jobs: lista de (kind, sheet_name, verificacion). Permite verificar
    en una sola pasada un reporte que tiene hojas de Bold Y Redeban a la
    vez. Devuelve un resumen combinado (conteos)."""
    bank_entries = parse_bancolombia_pdf(bank_pdf_path)
    all_results = []
    for kind, sheet_name, verificacion in jobs:
        if not verificacion:
            continue
        if kind == "bold":
            results = match_bold(bank_entries, verificacion)
            color_excel_bold(xlsx_path, sheet_name, results)
        else:
            results = match_redeban(bank_entries, verificacion)
            color_excel_redeban(xlsx_path, sheet_name, results)
        all_results.extend(results)

    annotate_pdf(bank_pdf_path, all_results, out_pdf_path)

    checked = [r for r in all_results if not r.get("no_data")]
    cruzados = sum(1 for r in checked if r.get("cruzado"))
    ok = sum(1 for r in checked if r["matched"] and not r.get("cruzado"))
    bad = len(checked) - ok - cruzados
    return {"total": len(checked), "coinciden": ok, "cruzados": cruzados, "difieren": bad}
