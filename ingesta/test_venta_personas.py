# -*- coding: utf-8 -*-
"""Pruebas del lector de venta por persona, con un libro inventado (sin datos reales).

Uso, desde la raíz del repositorio: python -m unittest ingesta.test_venta_personas
"""
import datetime as dt
import os
import tempfile
import unittest

import openpyxl

from ingesta import venta_personas as vp

PERFIL = {"hoja": "DESC FACT",
          "columnas": {"fecha": "FECHA", "persona": "ASESOR", "venta": "VENTA DIA", "facturas": "FACTURAS"}}


def libro(filas, encabezado=("FECHA", "ASESOR", "VR DESCUADRE", "VENTA DIA", "FACTURAS"), fila_enc=2):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DESC FACT"
    ws.cell(1, 1, "RESUMEN DEL MES")
    for c, t in enumerate(encabezado, 1):
        ws.cell(fila_enc, c, t)
    for r, fila in enumerate(filas, fila_enc + 1):
        for c, v in enumerate(fila, 1):
            ws.cell(r, c, v)
    d = tempfile.mkdtemp(dir=os.environ.get("TEMP"))
    ruta = os.path.join(d, "libro.xlsx")
    wb.save(ruta)
    return openpyxl.load_workbook(ruta, read_only=True, data_only=True)


class Repartir(unittest.TestCase):
    def test_partes_iguales_suman_el_dia(self):
        partes = vp.repartir(7554201, 88, 2)
        self.assertEqual(sum(v for v, _ in partes), 7554201)
        self.assertEqual(partes, [(3777101, 44.0), (3777100, 44.0)])

    def test_facturas_impares_y_vacias(self):
        self.assertEqual(vp.repartir(100, 15, 2), [(50, 7.5), (50, 7.5)])
        self.assertEqual(vp.repartir(100, None, 3), [(34, None), (33, None), (33, None)])

    def test_regla_desconocida(self):
        with self.assertRaises(ValueError):
            vp.repartir(100, 1, 2, "por_horas")

    def test_separar_nombres(self):
        self.assertEqual(vp.personas("Ana Ruiz Y Luisa Gil"), ["Ana Ruiz", "Luisa Gil"])
        self.assertEqual(vp.personas("Ana / Luisa"), ["Ana", "Luisa"])
        self.assertEqual(vp.personas("Ana-María Gil"), ["Ana-María Gil"])
        self.assertEqual(vp.personas("Yolanda"), ["Yolanda"])


class Leer(unittest.TestCase):
    def test_dia_con_numero_y_dos_personas(self):
        wb = libro([(1, "Ana Ruiz", 0, 1000000, 10), (2, "Ana Ruiz y Luisa Gil", 0, 501, None),
                    (3, "Luisa Gil", 0, None, None), ("TOTAL", "", 0, 1000501, 10)])
        filas, avisos = vp.leer(wb, PERFIL, ["2026-10-01", "2026-10-02"])
        self.assertEqual(avisos, [])
        self.assertEqual([(f["fecha"], f["texto"], f["venta"], f["facturas"], f["personas_dia"], f["fila_origen"])
                          for f in filas],
                         [("2026-10-01", "Ana Ruiz", 1000000, 10.0, 1, 3),
                          ("2026-10-02", "Ana Ruiz", 251, None, 2, 4),
                          ("2026-10-02", "Luisa Gil", 250, None, 2, 4)])
        self.assertEqual(sum(f["venta"] for f in filas), 1000501)

    def test_fecha_completa(self):
        wb = libro([(dt.datetime(2026, 10, 5), "Ana Ruiz", 0, 20000, 2)])
        filas, _ = vp.leer(wb, PERFIL, [])
        self.assertEqual(filas[0]["fecha"], "2026-10-05")

    def test_sin_encabezado_avisa(self):
        wb = libro([(1, "Ana", 0, 100, 1)], encabezado=("DIA", "QUIEN", "X", "VENTA DIA", "FACTURAS"))
        filas, avisos = vp.leer(wb, PERFIL, ["2026-10-01"])
        self.assertEqual(filas, [])
        self.assertIn("encabezado", avisos[0])

    def test_venta_sin_nombre_avisa(self):
        wb = libro([(4, None, 0, 9000, 1)])
        filas, avisos = vp.leer(wb, PERFIL, ["2026-10-04"])
        self.assertEqual(filas[0]["texto"], "(sin nombre)")
        self.assertIn("no dice quién", avisos[0])

    def test_hoja_que_no_esta(self):
        wb = libro([])
        filas, avisos = vp.leer(wb, dict(PERFIL, hoja="VENTAS"), [])
        self.assertEqual(filas, [])
        self.assertIn("VENTAS", avisos[0])


class Meta(unittest.TestCase):
    def test_meta_del_mes(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "METAS"
        ws["K1"], ws["K2"] = "META", 53000000.0
        d = tempfile.mkdtemp(dir=os.environ.get("TEMP"))
        wb.save(os.path.join(d, "m.xlsx"))
        libro_m = openpyxl.load_workbook(os.path.join(d, "m.xlsx"), read_only=True, data_only=True)
        meta, avisos = vp.leer_meta(libro_m, {"hoja": "METAS", "celda": "K2"}, ["2026-02-01", "2026-02-28"])
        self.assertEqual(meta, {"desde": "2026-02-01", "hasta": "2026-02-28", "monto": 53000000, "fila_origen": 2})
        self.assertEqual(avisos, [])
        meta, _ = vp.leer_meta(libro_m, {"hoja": "METAS", "celda": "K3"}, ["2026-02-01"])
        self.assertIsNone(meta)


if __name__ == "__main__":
    unittest.main()
