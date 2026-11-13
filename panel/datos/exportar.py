# -*- coding: utf-8 -*-
"""El Excel de transferencias del banco, ordenado por día y por punto.

Una hoja por día: cada punto con su código, el total y cada transferencia en su columna;
el total general; y abajo los pagos sin punto, con el punto si ya se asignó. Una hoja
"Sin origen" junta los de todos los días. Los montos van como números enteros, para que
Excel los pueda sumar. Los puntos y sus códigos salen de la empresa, no de una lista fija.
"""
import datetime as dt
from pathlib import Path

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
FORMATO = "#,##0"


def nombre(fechas):
    """'Transferencias {2026-09-01 a 2026-09-30}': los días seguidos se juntan."""
    dias = sorted({dt.date.fromisoformat(f) for f in fechas})
    if not dias:
        return "Transferencias (sin datos)"
    tramos = [[dias[0], dias[0]]]
    for d in dias[1:]:
        if (d - tramos[-1][1]).days == 1:
            tramos[-1][1] = d
        else:
            tramos.append([d, d])
    texto = ", ".join(a.isoformat() if a == b else f"{a.isoformat()} a {b.isoformat()}" for a, b in tramos)
    if len(texto) > 150:  # Windows no deja nombres muy largos
        texto = f"{dias[0].isoformat()} a {dias[-1].isoformat()}, {len(dias)} días"
    return f"Transferencias {{{texto}}}"


def escribir(salida, fechas, puntos, por_dia, sin_origen):
    """puntos: [(nombre, código)] en orden. por_dia: {(fecha, nombre): [montos]}.
    sin_origen: [{fecha, descripcion, etiqueta, valor, punto}]."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    from openpyxl.utils import get_column_letter

    negrita, titulo = Font(bold=True), Font(bold=True, size=12)
    encabezado = PatternFill("solid", fgColor="F3E4EE")
    suave = Font(italic=True, color="5E5862")
    wb = Workbook()
    wb.remove(wb.active)
    sin_por_dia = {}
    for s in sin_origen:
        sin_por_dia.setdefault(s["fecha"], []).append(s)

    for fecha in sorted(fechas):
        d = dt.date.fromisoformat(fecha)
        ws = wb.create_sheet(fecha)
        ws.cell(1, 1, f"Transferencias del {DIAS[d.weekday()]} {d.day}/{d.month}/{d.year}").font = titulo
        for col, texto in enumerate(["Punto", "Código", "Total"], start=1):
            c = ws.cell(3, col, texto)
            c.font, c.fill = negrita, encabezado
        fila, ancho = 4, 0
        for punto, codigo in puntos:
            montos = por_dia.get((fecha, punto), [])
            ancho = max(ancho, len(montos))
            ws.cell(fila, 1, punto)
            ws.cell(fila, 2, codigo or "")
            ws.cell(fila, 3, sum(montos)).number_format = FORMATO
            for i, m in enumerate(montos):
                ws.cell(fila, 4 + i, m).number_format = FORMATO
            fila += 1
        ws.cell(fila, 1, "Total").font = negrita
        total = ws.cell(fila, 3, f"=SUM(C4:C{fila - 1})" if fila > 4 else 0)
        total.font, total.number_format = negrita, FORMATO

        fila += 2
        ws.cell(fila, 1, "Pagos sin punto").font = negrita
        fila += 1
        for col, texto in enumerate(["Descripción", "Tipo", "Punto asignado", "Valor"], start=1):
            c = ws.cell(fila, col, texto)
            c.font, c.fill = negrita, encabezado
        fila += 1
        del_dia = sin_por_dia.get(fecha, [])
        for s in del_dia:
            ws.cell(fila, 1, s["descripcion"])
            ws.cell(fila, 2, s.get("etiqueta") or "")
            ws.cell(fila, 3, s.get("punto") or "")
            ws.cell(fila, 4, s["valor"]).number_format = FORMATO
            fila += 1
        if not del_dia:
            ws.cell(fila, 1, "Ninguno este día").font = suave
        ws.column_dimensions["A"].width = 34
        ws.column_dimensions["B"].width = 16
        ws.column_dimensions["C"].width = 18
        for col in range(4, 5 + ancho):
            ws.column_dimensions[get_column_letter(col)].width = 12

    ws = wb.create_sheet("Sin origen")
    ws.append(["Fecha", "Descripción", "Tipo", "Punto asignado", "Valor"])
    for c in ws[1]:
        c.font, c.fill = negrita, encabezado
    for s in sorted(sin_origen, key=lambda s: s["fecha"]):
        ws.append([s["fecha"], s["descripcion"], s.get("etiqueta") or "", s.get("punto") or "", s["valor"]])
        ws.cell(ws.max_row, 5).number_format = FORMATO
    if not sin_origen:
        ws.append(["Ninguno"])
    for letra, w in zip("ABCDE", (12, 40, 22, 20, 14)):
        ws.column_dimensions[letra].width = w
    if not fechas:
        wb.move_sheet("Sin origen", 0)
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    wb.save(salida)
    return salida
