# -*- coding: utf-8 -*-
"""Pruebas de la revisión de la mañana, con datos inventados y sin archivos.

Desde motores/: python -m unittest test_revision
"""
import unittest

from revision import revisar

CONFIG = {"tolerancia_cuadra": 100, "porcentaje_explicado": 80, "reglas_sin_peso": ["R05"],
          "compensacion": {"monto_minimo": 1000, "tolerancia": 500, "porcentaje": 25},
          "billete": {"denominaciones": [2000, 5000, 10000, 20000, 50000, 100000], "max_billetes": 3},
          "precios": {"monto_minimo": 1000, "max_productos": 3, "max_mostradas": 3}}
F, ANTES, DESPUES = "2026-09-16", "2026-09-15", "2026-09-17"


def item(monto, i):
    return {"monto": monto, "id": i}


def dia(transferencias=(), tarjetas=(), descuadre=0):
    return {"transferencias": list(transferencias), "tarjetas": list(tarjetas), "descuadre": descuadre,
            "venta": 1000000, "asesoras": "Ana"}


def banco(por_dia, fechas=(ANTES, F, DESPUES)):
    return {"por_dia": por_dia, "fechas": set(fechas), "sin_origen": []}


SIN_TARJETAS = {"por_dia": {}, "cubre": {}}


class Revision(unittest.TestCase):
    def test_todo_llego_y_cuadra(self):
        r = revisar(F, {"P1": {F: dia([item(50000, "a")])}}, banco({(F, "P1"): [item(50000, "b")]}), SIN_TARJETAS, CONFIG)
        p = r["puntos"][0]
        self.assertEqual(p["estado"]["estado"], "cuadra")
        self.assertEqual(p["cruces"]["transferencias"]["no_llegaron"], [])

    def test_transferencia_que_no_llego_se_muestra(self):
        r = revisar(F, {"P1": {F: dia([item(85000, "a")], descuadre=-85000)}}, banco({}), SIN_TARJETAS, CONFIG)
        p = r["puntos"][0]
        self.assertEqual(p["cruces"]["transferencias"]["no_llegaron"], [item(85000, "a")])
        self.assertEqual(p["estado"]["estado"], "sin_explicar")

    def test_la_que_llego_al_dia_siguiente_no_es_faltante(self):
        r = revisar(F, {"P1": {F: dia([item(85000, "a")])}}, banco({(DESPUES, "P1"): [item(85000, "b")]}),
                    SIN_TARJETAS, CONFIG)
        c = r["puntos"][0]["cruces"]["transferencias"]
        self.assertEqual((c["no_llegaron"], c["otro_dia"][0]["donde"]), ([], "externo_otro_dia"))

    def test_cobro_con_tarjeta_sin_anotar_explica_el_faltante(self):
        tarjetas = {"por_dia": {(F, "P1"): [item(40000, "t")]}, "cubre": {"P1": {ANTES, F, DESPUES}}}
        r = revisar(F, {"P1": {F: dia(descuadre=-40000)}}, banco({}), tarjetas, CONFIG)
        p = r["puntos"][0]
        self.assertEqual(p["estado"], {"estado": "explicado", "explicado": -40000, "sin_explicar": 0})

    def test_sin_extracto_no_se_inventa_nada(self):
        r = revisar(F, {"P1": {F: dia([item(85000, "a")], descuadre=-85000)}}, banco({}, fechas=()), SIN_TARJETAS, CONFIG)
        p = r["puntos"][0]
        self.assertNotIn("transferencias", p["cruces"])
        self.assertIn("extracto del banco", p["sin_datos"])

    def test_cada_punto_solo_cruza_lo_suyo(self):
        excel = {"P1": {F: dia([item(85000, "a")])}, "P2": {F: dia()}}
        r = revisar(F, excel, banco({(F, "P2"): [item(85000, "b")]}), SIN_TARJETAS, CONFIG)
        p1, p2 = r["puntos"]
        self.assertEqual(len(p1["cruces"]["transferencias"]["no_llegaron"]), 1)
        self.assertEqual(len(p2["cruces"]["transferencias"]["no_anotadas"]), 1)

    def test_punto_sin_excel_ese_dia(self):
        r = revisar(F, {"P1": {ANTES: dia()}}, banco({}), SIN_TARJETAS, CONFIG)
        self.assertTrue(r["puntos"][0]["sin_excel"])

    def test_falta_hoy_lo_que_sobro_ayer_se_explica(self):
        excel = {"P1": {ANTES: dia(descuadre=37000), F: dia(descuadre=-37300)}}
        p = revisar(F, excel, banco({}), SIN_TARJETAS, CONFIG)["puntos"][0]
        comp = [c for c in p["causas"] if c["que"] == "compensacion"]
        self.assertEqual((comp[0]["fecha"], comp[0]["monto"]), (ANTES, -37000))
        self.assertEqual(p["estado"]["estado"], "explicado")

    def test_el_vecino_es_la_hoja_anterior_aunque_no_sea_ayer(self):
        sabado, lunes = "2026-09-12", "2026-09-14"
        excel = {"P1": {sabado: dia(descuadre=20000), lunes: dia(descuadre=-20000)}}
        p = revisar(lunes, excel, banco({}), SIN_TARJETAS, CONFIG)["puntos"][0]
        self.assertEqual([c["fecha"] for c in p["causas"] if c["que"] == "compensacion"], [sabado])

    def test_billete_explica_y_precios_es_solo_pista(self):
        d = dia(descuadre=-50000)
        d["productos"] = [{"precio": 25000, "nombre": "Crema", "movimiento": 1}]
        p = revisar(F, {"P1": {F: d}}, banco({}), SIN_TARJETAS, CONFIG)["puntos"][0]
        tipos = {c["que"]: c["tipo"] for c in p["causas"]}
        self.assertEqual((tipos["billete"], tipos["precios"]), ("causa", "pista"))
        self.assertEqual(p["causas"][-1]["productos"], [[{"precio": 25000, "nombres": ["Crema"]}] * 2])
        self.assertEqual(p["estado"]["estado"], "explicado")

    def test_solo_la_pista_no_explica(self):
        d = dia(descuadre=-35900)
        d["productos"] = [{"precio": 35900, "nombre": "Kit", "movimiento": 0}]
        p = revisar(F, {"P1": {F: d}}, banco({}), SIN_TARJETAS, CONFIG)["puntos"][0]
        self.assertEqual(p["estado"]["estado"], "sin_explicar")

    def test_sin_configuracion_no_se_inventan_valores(self):
        base = {k: CONFIG[k] for k in ("tolerancia_cuadra", "porcentaje_explicado", "reglas_sin_peso")}
        r = revisar(F, {"P1": {F: dia(descuadre=-50000)}}, banco({}), SIN_TARJETAS, base)
        self.assertEqual(r["puntos"][0]["estado"]["estado"], "sin_explicar")
        self.assertEqual(r["sin_configurar"], ["compensacion", "billete", "precios"])


if __name__ == "__main__":
    unittest.main()
