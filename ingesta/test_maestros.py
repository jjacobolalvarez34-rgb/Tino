# -*- coding: utf-8 -*-
"""Pruebas del cargador de maestros, sin red y con datos inventados.

Desde la raíz: python -m unittest ingesta.test_maestros
"""
import unittest

from ingesta.maestros import norm_alias, plan

EMPRESA = "e0000000-0000-4000-8000-000000000001"


def datos():
    return {
        "empresa": {"id": EMPRESA, "nombre": "Inventada"},
        "puntos": [{"id": "p1", "codigo": "P01", "nombre": "Uno"}, {"id": "p2", "codigo": "P02", "nombre": "Dos"}],
        "medios_pago": [{"codigo": "EF", "nombre": "Efectivo", "tipo": "efectivo"}],
        "tipos_venta": [{"codigo": "DET", "nombre": "Detal"}],
        "asesoras": [{"id": "a1", "nombre_completo": "Ana Uno"}, {"id": "a2", "nombre_completo": "Ana Dos"}],
        "alias": [{"punto": "P01", "asesora": "Ana Uno", "texto": "Ana"},
                  {"punto": "P02", "asesora": "Ana Dos", "texto": "Ana"},
                  {"punto": "P01", "asesora": "Ana Uno", "texto": "ANA."}],
        "productos": [{"id": "x1", "codigo": "X1", "nombre": "Crema"}, {"id": "x2", "codigo": "X2", "nombre": "Jabón"}],
        "producto_alias": [{"producto": "X1", "texto": "Crema"}, {"producto": "X2", "texto": "crema"},
                           {"producto": "X2", "texto": "Jabón"}],
        "datafonos": [{"punto": "P01", "proveedor": "bold", "codigo_terminal": "T1", "activo_desde": "2026-01-01"}],
        "codigos_recaudo": [{"punto": "P01", "codigo": "11110001", "activo_desde": "2026-01-01"},
                            {"punto": "P02", "codigo": "22220001", "activo_desde": "2026-01-01"}],
    }


class Plan(unittest.TestCase):
    def test_base_vacia_crea_todo_con_su_empresa(self):
        faltan, _ = plan(datos(), {})
        self.assertEqual(len(faltan["punto_venta"]), 2)
        self.assertTrue(all(f["empresa_id"] == EMPRESA for f in faltan["asesora"]))

    def test_mismo_nombre_en_dos_puntos_son_dos_alias(self):
        faltan, _ = plan(datos(), {})
        self.assertEqual(len(faltan["asesora_alias"]), 2)

    def test_correr_dos_veces_no_crea_nada(self):
        d = datos()
        ya = {"empresa": [EMPRESA], "punto_venta": ["P01", "P02"], "medio_pago": ["EF"], "tipo_venta": ["DET"],
              "asesora": ["Ana Uno", "Ana Dos"], "asesora_alias": [("p1", "ana"), ("p2", "ana")],
              "producto": ["X1", "X2"], "producto_alias": ["crema", "jabon"], "terminal_datafono": ["T1"],
              "codigo_recaudo": ["11110001", "22220001"]}
        faltan, _ = plan(d, ya)
        self.assertEqual({k: v for k, v in faltan.items() if v}, {})

    def test_nombre_de_producto_ambiguo_avisa_y_no_se_carga(self):
        faltan, avisos = plan(datos(), {})
        self.assertEqual(len(faltan["producto_alias"]), 2)
        self.assertTrue(any("dos productos" in a for a in avisos))

    def test_dos_puntos_con_los_mismos_cuatro_digitos_avisa(self):
        _, avisos = plan(datos(), {})
        self.assertTrue(any("0001" in a for a in avisos))

    def test_alias_con_punto_desconocido_avisa(self):
        d = datos()
        d["alias"].append({"punto": "P99", "asesora": "Ana Uno", "texto": "Otra"})
        _, avisos = plan(d, {})
        self.assertTrue(any("Otra" in a for a in avisos))

    def test_normaliza_igual_que_la_base(self):
        self.assertEqual(norm_alias("Ánge-la  MUÑOZ."), "ange la munoz")


if __name__ == "__main__":
    unittest.main()
