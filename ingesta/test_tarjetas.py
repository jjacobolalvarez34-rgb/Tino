# -*- coding: utf-8 -*-
"""Pruebas del lector de Bold y Redeban, con archivos inventados.

Desde la raíz: python -m unittest ingesta.test_tarjetas
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import openpyxl

from ingesta import tarjetas

PUNTOS = {"bold": {"Tienda Uno": "Punto 1", "Tienda Dos": "Punto 2"}, "redeban": {"11": "Punto 3"}}
BOLD = ["NOMBRE DEL DATÁFONO", "FECHA", "OPERACIÓN", "VALOR DE LA COMPRA", "IVA", "VALOR TOTAL",
        "VALOR RETE FUENTE", "VALOR RETE IVA", "VALOR RETE ICA", "% COMISIÓN BOLD",
        "COMISIÓN BOLD FIJA", "TOTAL DEDUCCIÓN", "DEPOSITO EN CUENTA BOLD"]
REDEBAN = ["CODIGO ESTABLECIMIENTO", "FRANQUICIA", "FECHA DE TRANSACCION", "FECHA DE CANJE",
           "VALOR COMPRA", "VALOR IVA", "VALOR TOTAL", "VALOR COMISION", "VALOR RETEFUENTE",
           "VALOR RETE IVA", "VALOR RTE ICA", "VALOR NETO"]


def libro(ruta, encabezado, filas, titulo=None):
    wb = openpyxl.Workbook()
    ws = wb.active
    if titulo:
        ws.append([titulo])
    ws.append(encabezado)
    for fila in filas:
        ws.append(fila)
    wb.save(ruta)
    return ruta


class Lector(unittest.TestCase):
    def setUp(self):
        self._carpeta = tempfile.TemporaryDirectory()
        self.carpeta = Path(self._carpeta.name)

    def tearDown(self):
        self._carpeta.cleanup()

    def test_bold_con_hora_y_solo_cobros_exitosos(self):
        ruta = libro(self.carpeta / "b.xlsx", BOLD, [
            ["Tienda Uno", dt.datetime(2026, 10, 30, 14, 32), "COBRO EXITOSO", 84000, 16000, 100000,
             1500, 285.5, 41.4, 2990, 0, 4816.9, 95183.1],
            ["Tienda Uno", dt.datetime(2026, 10, 30, 15, 0), "COBRO FALLIDO", 0, 0, 50000, 0, 0, 0, 0, 0, 0, 0],
            ["Tienda Sin Punto", dt.datetime(2026, 10, 30, 16, 0), "COBRO EXITOSO", 0, 0, 7000, 0, 0, 0, 0, 0, 0, 0],
        ], titulo="Reporte de transacciones")
        cobros, avisos = tarjetas.leer(ruta, PUNTOS)
        self.assertEqual(cobros, [{"fecha": "2026-10-30", "hora": 14, "punto": "Punto 1", "proveedor": "bold",
                                   "franquicia": None, "bruto": 100000, "comision": 2990,
                                   "retenciones": 1827, "prestamo": 0, "neto": 95183}])
        self.assertEqual(len(avisos), 2)

    def test_bold_formato_clasico_sin_operacion(self):
        encabezado = [c for c in BOLD if c != "OPERACIÓN"]
        encabezado[-1] = "DEPOSITO EN SALDO DE VENTAS"
        ruta = libro(self.carpeta / "c.xlsx", encabezado, [
            ["Tienda Dos.", "2026-10-31 09:05:00", 0, 0, 20000, 0, 0, 0, 600, 0, 600, 19400]])
        cobros, _ = tarjetas.leer(ruta, PUNTOS)
        self.assertEqual((cobros[0]["punto"], cobros[0]["hora"], cobros[0]["neto"]), ("Punto 2", 9, 19400))

    def test_bold_con_prestamo_y_franquicia(self):
        encabezado = BOLD + ["DEDUCCIÓN DEL PRÉSTAMO", "FRANQUICIA", "NOMBRE DEL PAGADOR"]
        ruta = libro(self.carpeta / "p.xlsx", encabezado, [
            ["Tienda Uno", dt.datetime(2026, 9, 16, 12, 0), "COBRO EXITOSO", 0, 0, 100000, 1000, 0, 0, 3000, 0,
             13600, 86400, 9600, "visa", "Persona Inventada"]])
        cobros, _ = tarjetas.leer(ruta, PUNTOS)
        self.assertEqual((cobros[0]["prestamo"], cobros[0]["franquicia"], cobros[0]["neto"]), (9600, "VISA", 86400))
        self.assertNotIn("Persona Inventada", str(cobros))

    def test_redeban_sin_hora_y_con_negativos(self):
        ruta = libro(self.carpeta / "r.xlsx", REDEBAN, [
            ["0000011", "visa", "20261030", "20261102", 84000, 16000, 100000, -2500, -1500, -285, -41, 95674],
            ["0000099", "AMEX", "20261030", "20261102", 0, 0, 5000, 0, 0, 0, 0, 5000],
        ])
        cobros, avisos = tarjetas.leer(ruta, PUNTOS)
        self.assertEqual(cobros, [{"fecha": "2026-10-30", "hora": None, "punto": "Punto 3", "proveedor": "redeban",
                                   "franquicia": "VISA", "bruto": 100000, "comision": 2500,
                                   "retenciones": 1826, "prestamo": 0, "neto": 95674}])
        self.assertIn("99", avisos[0])

    def test_valor_que_no_se_entiende_no_se_cuenta_y_avisa(self):
        ruta = libro(self.carpeta / "b.xlsx", BOLD, [
            ["Tienda Uno", dt.datetime(2026, 10, 30, 14, 32), "COBRO EXITOSO", 0, 0, "#REF!",
             0, 0, 0, 0, 0, 0, 0]])
        cobros, avisos = tarjetas.leer(ruta, PUNTOS)
        self.assertEqual(cobros, [])
        self.assertIn("no se cuenta", avisos[0])

    def test_falta_una_columna(self):
        ruta = libro(self.carpeta / "b.xlsx", [c for c in BOLD if c != "VALOR TOTAL"], [])
        with self.assertRaises(tarjetas.FormatoNoReconocido):
            tarjetas.leer(ruta, PUNTOS)

    def test_archivo_que_no_es_de_tarjetas(self):
        ruta = libro(self.carpeta / "x.xlsx", ["Nombre", "Edad"], [["a", 1]])
        with self.assertRaises(tarjetas.FormatoNoReconocido):
            tarjetas.leer(ruta, PUNTOS)


if __name__ == "__main__":
    unittest.main()
