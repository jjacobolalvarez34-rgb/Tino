# -*- coding: utf-8 -*-
"""Pruebas del conector de Siigo con respuestas inventadas que siguen la documentación.

Desde la raíz: python -m unittest ingesta.test_siigo
"""
import unittest

from ingesta import siigo


def factura(i, centro=10, anulada=False, total=71800.0, fecha="2026-10-02"):
    return {"id": f"uuid-{i}", "prefix": "FV-1", "number": 100 + i, "name": f"FV-1-{100 + i}", "date": fecha,
            "document": {"id": 5}, "cost_center": centro, "seller": 629, "total": total, "annulled": anulada,
            "items": [{"code": "M001", "description": "Producto inventado", "quantity": 2, "price": 35900.0,
                       "total": total, "discount": {"value": 0}, "warehouse": {"id": 7, "name": "Bodega"}}],
            "payments": [{"id": 1, "name": "Efectivo", "value": total}]}


class Falso:
    """Siigo inventado: dos páginas de facturas, y un 429 la primera vez."""

    def __init__(self, facturas, clave="buena"):
        self.facturas, self.clave, self.llamadas, self.esperar = facturas, clave, [], True

    def __call__(self, metodo, url, cab, cuerpo=None):
        self.llamadas.append((metodo, url, cab.get("Partner-Id")))
        if url.endswith("/auth"):
            if cuerpo["access_key"] != self.clave:
                return 401, {"Errors": [{"Code": "invalid_credentials"}]}
            return 200, {"access_token": "token", "expires_in": 86400}
        if "/v1/invoices" in url:
            if self.esperar:
                self.esperar = False
                return 429, {}
            pagina = int(url.split("page=")[1].split("&")[0])
            return 200, {"pagination": {"page": pagina, "page_size": 2, "total_results": len(self.facturas)},
                         "results": self.facturas[(pagina - 1) * 2:pagina * 2]}
        return 404, {}


class Conector(unittest.TestCase):
    def setUp(self):
        siigo.time.sleep = lambda s: None  # sin esperas en las pruebas

    def test_trae_todas_las_paginas_y_reintenta_si_pide_esperar(self):
        t = Falso([factura(i) for i in range(5)])
        s = siigo.Siigo("u", "buena", "Tino", transporte=t)
        self.assertEqual(len(s.facturas("2026-10-01", "2026-10-31")), 5)
        self.assertTrue(all(p == "Tino" for _, _, p in t.llamadas), "Cada petición lleva el Partner-Id")

    def test_el_ultimo_dia_del_rango_si_entra(self):
        # En Siigo date_end no incluye ese día: se pide hasta el siguiente y se filtra aquí.
        facturas = [dict(factura(i), date=f"2026-10-{d:02d}") for i, d in enumerate([6, 7, 7, 8])]
        t = Falso(facturas)
        s = siigo.Siigo("u", "buena", "Tino", transporte=t)
        leidas = s.facturas("2026-10-01", "2026-10-07")
        self.assertEqual(sorted(f["date"] for f in leidas), ["2026-10-06", "2026-10-07", "2026-10-07"])
        self.assertTrue(any("date_end=2026-10-08" in url for _, url, _ in t.llamadas))

    def test_clave_mala_dice_que_revisar(self):
        s = siigo.Siigo("u", "mala", "Tino", transporte=Falso([]))
        with self.assertRaisesRegex(siigo.ErrorSiigo, "credencial API"):
            s.probar()

    def test_sin_credenciales_no_intenta(self):
        with self.assertRaises(siigo.ErrorSiigo):
            siigo.Siigo("", "x", "Tino")

    def test_normaliza_en_pesos_y_ubica_el_punto_por_el_perfil(self):
        perfil = {"campo": "cost_center", "puntos": {"10": "P01"}}
        carga = siigo.normalizar([factura(1), factura(2, centro=99)], perfil, {"P01": "id-p01"}, {"M001": "id-m001"},
                                 "2026-10-01", "2026-10-31")
        f = carga["facturas"][0]
        self.assertEqual((f["punto_id"], f["total"], f["items"][0]["producto_id"], f["pagos"][0]["valor"]),
                         ("id-p01", 71800, "id-m001", 71800))
        self.assertEqual(len(carga["errores"]), 1, "La factura sin punto no se inventa: queda como error")
        self.assertIn("99", carga["errores"][0]["texto"])

    def test_el_punto_puede_salir_de_la_bodega_o_del_prefijo(self):
        self.assertEqual(siigo.valor_de(factura(1), "warehouse"), "7")
        self.assertEqual(siigo.valor_de(factura(1), "prefix"), "FV-1")
        self.assertEqual(siigo.valores_encontrados([factura(1), factura(2), factura(3, centro=11)], "cost_center"),
                         {"10": 2, "11": 1})

    def test_decimales_sin_float(self):
        self.assertEqual((siigo.pesos(35900.5), siigo.pesos("1234.49"), siigo.pesos(None)), (35901, 1234, 0))

    def test_misma_respuesta_misma_huella(self):
        p = {"campo": "cost_center", "puntos": {"10": "P01"}}
        a = siigo.normalizar([factura(1)], p, {"P01": "x"}, {}, "2026-10-01", "2026-10-31")
        b = siigo.normalizar([factura(1)], p, {"P01": "x"}, {}, "2026-10-01", "2026-10-31")
        c = siigo.normalizar([factura(1, anulada=True)], p, {"P01": "x"}, {}, "2026-10-01", "2026-10-31")
        self.assertEqual(a["hash"], b["hash"])
        self.assertNotEqual(a["hash"], c["hash"], "Si cambió algo en Siigo, se puede traer otra vez")


if __name__ == "__main__":
    unittest.main()
