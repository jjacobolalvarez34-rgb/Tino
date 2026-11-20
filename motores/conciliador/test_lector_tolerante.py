# -*- coding: utf-8 -*-
"""Prueba del lector de días cuando una hoja tiene un encabezado borrado (D-055).

Libro inventado en memoria, con la forma de la plantilla del Excel del día: no usa datos de
ningún cliente. Uso, desde motores/conciliador: python -m unittest test_lector_tolerante
"""
import datetime as dt
import unittest

from cierre.lector_xlsx import LibroMensual

ENCABEZADO = ["PRODUCTO", "PRECIO", "INV. INICIAL", "ENTRADAS", "INV. FINAL", "SALIDAS SIIGO",
              "SALIDAS TOTALES", "VALOR VENTA"]


def hoja(dia, venta, encabezado=ENCABEZADO, columna_extra=False):
    """Una hoja de día mínima: fecha, encabezados en la fila 7, un producto y el total."""
    enc = list(encabezado)
    if columna_extra:  # otra versión de la plantilla: una columna más antes de ENTRADAS
        enc.insert(3, "OTRA")
    g = {(1, 1): "FECHA", (1, 2): dt.datetime(2026, 10, dia), (2, 1): "PUNTO DE VENTA", (2, 2): "Punto Inventado"}
    for c, t in enumerate(enc, 1):
        if t is not None:
            g[(7, c)] = t
    col = {t: c for c, t in enumerate(enc, 1)}
    g[(8, 1)] = "Producto Uno"
    g[(8, col.get("VALOR VENTA", 8))] = venta
    g[(10, 1)] = "VENTA DEL DIA"
    g[(10, col.get("VALOR VENTA", 8))] = venta
    return g


def libro(hojas):
    return LibroMensual("prueba.xlsx", "prueba.xlsx", list(hojas), {n: {} for n in hojas}, hojas)


class LectorTolerante(unittest.TestCase):
    def test_encabezado_borrado_usa_el_diseno_del_libro(self):
        roto = list(ENCABEZADO)
        roto[1], roto[2] = 9.0, 0.0          # escribieron números encima de PRECIO e INV. INICIAL
        vacio = list(ENCABEZADO)
        vacio[1] = None                      # el de PRECIO quedó vacío
        l = libro({"01": hoja(1, 1000), "02": hoja(2, 2000), "05": hoja(5, 5000, roto), "30": hoja(30, 3000, vacio)})
        self.assertEqual(sorted(d.day for d in l.dias), [1, 2, 5, 30])
        self.assertEqual(round(sum(d.caja.valor_teorico for d in l.dias.values())), 11000)
        avisos = " ".join(l.avisos)
        self.assertIn("Hoja 05", avisos)
        self.assertIn("Hoja 30", avisos)
        self.assertIn("mismas columnas", avisos)

    def test_toma_el_diseno_que_coincide_aunque_no_sea_el_primero(self):
        roto = list(ENCABEZADO)
        roto[1] = "9"
        l = libro({"01": hoja(1, 1000, columna_extra=True), "02": hoja(2, 2000), "05": hoja(5, 5000, roto)})
        self.assertIn(dt.date(2026, 10, 5), l.dias)
        self.assertEqual(round(l.dias[dt.date(2026, 10, 5)].caja.valor_teorico), 5000)

    def test_si_no_hay_diseno_igual_no_adivina(self):
        roto = list(ENCABEZADO)
        roto[1] = None
        roto[3], roto[4] = roto[4], roto[3]  # además movieron columnas: no coincide con nada
        l = libro({"01": hoja(1, 1000), "05": hoja(5, 5000, roto)})
        self.assertNotIn(dt.date(2026, 10, 5), l.dias)
        self.assertIn("faltan columnas", " ".join(l.avisos))


if __name__ == "__main__":
    unittest.main()
