# -*- coding: utf-8 -*-
"""Arma docs/pantallas/tablero_ventas.html con datos inventados.

Crea reportes falsos con el formato de Bold y Redeban y los pasa por el lector real,
así la demo prueba el camino completo. Uso, desde la raíz: python panel/tablero/demo.py
"""
import datetime as dt
import random
import sys
import tempfile
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(Path(__file__).parent)]

from armar import armar_datos, escribir  # noqa: E402
from ingesta import tarjetas  # noqa: E402

PUNTOS = {"bold": {"Datafono A": "Punto 1", "Datafono B": "Punto 2", "Datafono C": "Punto 3"},
          "redeban": {"11": "Punto 4", "22": "Punto 5"}}
INICIO = dt.date(2026, 10, 1)
DIAS = 31
HORAS = [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 18, 19, 19, 19, 20, 20]
VALORES = [18000, 25000, 32900, 35900, 39500, 42000, 54000, 68000, 72800, 85000, 120000, 240000]
PESO_SEMANA = [0.7, 0.75, 0.8, 0.85, 1.1, 1.5, 1.2]


def reporte_bold(ruta, r):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["NOMBRE DEL DATÁFONO", "FECHA", "OPERACIÓN", "VALOR TOTAL", "VALOR RETE FUENTE", "VALOR RETE IVA",
               "VALOR RETE ICA", "% COMISIÓN BOLD", "COMISIÓN BOLD FIJA", "DEPOSITO EN CUENTA BOLD",
               "DEDUCCIÓN DEL PRÉSTAMO", "FRANQUICIA"])
    for dia in range(DIAS):
        fecha = INICIO + dt.timedelta(days=dia)
        for datafono, fuerza in (("Datafono A", 26), ("Datafono B", 18), ("Datafono C", 13)):
            for _ in range(int(fuerza * PESO_SEMANA[fecha.weekday()] * r.uniform(0.75, 1.25))):
                valor = r.choice(VALORES)
                comision, rf, ri, rc = valor * 299 // 10000, valor * 15 // 1000, valor * 3 // 1000, valor * 4 // 1000
                # Algunos días, un préstamo inventado descuenta parte de cada depósito.
                prestamo = valor // 10 if 16 <= fecha.day <= 21 else 0
                ws.append([datafono, dt.datetime.combine(fecha, dt.time(r.choice(HORAS), r.randint(0, 59))),
                           "COBRO EXITOSO", valor, rf, ri, rc, comision, 0,
                           valor - comision - rf - ri - rc - prestamo, prestamo,
                           r.choice(["VISA", "MASTERCARD"])])
    wb.save(ruta)


def reporte_redeban(ruta, r):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["CODIGO ESTABLECIMIENTO", "FRANQUICIA", "FECHA DE TRANSACCION", "VALOR TOTAL", "VALOR COMISION",
               "VALOR RETEFUENTE", "VALOR RETE IVA", "VALOR RTE ICA", "VALOR NETO"])
    for dia in range(DIAS):
        fecha = INICIO + dt.timedelta(days=dia)
        for codigo, fuerza in (("0000011", 14), ("0000022", 9)):
            for _ in range(int(fuerza * PESO_SEMANA[fecha.weekday()] * r.uniform(0.75, 1.25))):
                valor = r.choice(VALORES)
                comision, rf, ri, rc = valor * 25 // 1000, valor * 15 // 1000, valor * 3 // 1000, valor * 4 // 1000
                ws.append([codigo, r.choice(["VISA", "VISA", "MASTERCARD", "AMEX"]), fecha.strftime("%Y%m%d"), valor,
                           -comision, -rf, -ri, -rc, valor - comision - rf - ri - rc])
    wb.save(ruta)


def main():
    r = random.Random(20261102)
    with tempfile.TemporaryDirectory() as carpeta:
        bold, redeban = Path(carpeta) / "bold.xlsx", Path(carpeta) / "redeban.xlsx"
        reporte_bold(bold, r)
        reporte_redeban(redeban, r)
        c1, a1 = tarjetas.leer(bold, PUNTOS)
        c2, a2 = tarjetas.leer(redeban, PUNTOS)
    salida = RAIZ / "docs" / "pantallas" / "tablero_ventas.html"
    escribir(armar_datos(c1 + c2, a1 + a2), salida)
    print(f"{len(c1) + len(c2)} cobros inventados. Tablero en {salida}")


if __name__ == "__main__":
    main()
