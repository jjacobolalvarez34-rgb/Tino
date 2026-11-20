# -*- coding: utf-8 -*-
"""Pruebas de facturar a través de Siigo con un Siigo inventado (sin red, sin facturas reales).

Uso, desde la raíz del repositorio: python -m unittest ingesta.test_siigo_facturar
"""
import unittest

from ingesta import siigo
from ingesta import siigo_facturar as sf

PERFIL = {"documento": 26, "cliente_por_defecto": "222222222222", "vendedor": {"P01": 629},
          "centro_costo": {"P01": 66}, "pagos": {"efectivo": 5636, "debito": 5637},
          "impuestos": {"M001": [13156]}}
VENTA = {"id": "9f1c2b7e-3a44-4c1d-9f00-1a2b3c4d5e6f", "fecha": "2026-11-20", "punto": "P01", "cliente": None,
         "items": [{"codigo": "M001", "cantidad": 2, "precio": 35900, "descuento": 0}],
         "pagos": [{"medio": "efectivo", "valor": 71800}]}


class SiigoFalso:
    """Guarda lo creado por llave de idempotencia, como hace Siigo. Puede cortarse una vez."""

    def __init__(self, cortar=0, pedir_esperar=0):
        self.creadas, self.llamadas, self.cortar, self.esperar = {}, [], cortar, pedir_esperar

    def __call__(self, metodo, url, cab, cuerpo=None):
        if url.endswith("/auth"):
            return 200, {"access_token": "t", "expires_in": 86400}
        self.llamadas.append((metodo, cab.get("Idempotency-Key")))
        llave = cab["Idempotency-Key"]
        if llave not in self.creadas:
            self.creadas[llave] = {"id": f"uuid-{len(self.creadas) + 1}", "name": f"FV-2-{len(self.creadas) + 1}",
                                   "total": sum(p["value"] for p in cuerpo["payments"]), "stamp": {"status": "Draft"}}
        if self.cortar:  # se crea en Siigo pero la respuesta no llega
            self.cortar -= 1
            raise siigo.ErrorSiigo("No hay conexión con Siigo: se cortó")
        if self.esperar:
            self.esperar -= 1
            return 429, {}
        return 201, self.creadas[llave]


class Facturar(unittest.TestCase):
    def setUp(self):
        siigo.time.sleep = lambda s: None

    def test_arma_la_factura_con_lo_que_dice_el_perfil(self):
        c = sf.armar(VENTA, PERFIL, "2026-11-20")
        self.assertEqual(c["document"], {"id": 26})
        self.assertEqual(c["customer"]["identification"], "222222222222")
        self.assertEqual((c["seller"], c["cost_center"]), (629, 66))
        self.assertEqual(c["items"], [{"code": "M001", "quantity": 2, "price": 35900, "taxes": [{"id": 13156}]}])
        self.assertEqual(c["payments"], [{"id": 5636, "value": 71800}])
        self.assertFalse(c["stamp"]["send"], "Por seguridad no se manda a la DIAN hasta que la empresa lo active")
        self.assertIn(VENTA["id"], c["observations"])

    def test_venta_sin_conexion_va_con_la_fecha_de_hoy_y_su_hora_real_en_la_nota(self):
        c = sf.armar(dict(VENTA, fecha="2026-11-18", hora="15:40"), PERFIL, "2026-11-20")
        self.assertEqual(c["date"], "2026-11-20")
        self.assertIn("Venta del 2026-11-18 15:40, registrada sin conexión", c["observations"])

    def test_lo_que_falta_se_dice_y_no_se_inventa(self):
        with self.assertRaisesRegex(sf.FacturaInvalida, "vendedor"):
            sf.armar(dict(VENTA, punto="P09"), PERFIL, "2026-11-20")
        with self.assertRaisesRegex(sf.FacturaInvalida, "forma de pago"):
            sf.armar(dict(VENTA, pagos=[{"medio": "addi", "valor": 71800}]), PERFIL, "2026-11-20")
        with self.assertRaisesRegex(sf.FacturaInvalida, "documento"):
            sf.armar(VENTA, {k: v for k, v in PERFIL.items() if k != "documento"}, "2026-11-20")

    def test_llave_de_idempotencia_estable_y_valida(self):
        llave = sf.llave_idempotencia(VENTA["id"])
        self.assertEqual(llave, sf.llave_idempotencia(VENTA["id"]))
        self.assertLessEqual(len(llave), 30)
        self.assertRegex(llave, r"^[A-Za-z0-9]+$")
        self.assertNotEqual(llave, sf.llave_idempotencia("0a1c2b7e-3a44-4c1d-9f00-1a2b3c4d5e6f"))

    def test_si_se_corta_al_mandar_no_queda_duplicada(self):
        falso = SiigoFalso(cortar=1, pedir_esperar=1)
        s = siigo.Siigo("u", "k", "Tino", transporte=falso)
        r = sf.facturar(s, VENTA, PERFIL, "2026-11-20")
        self.assertEqual(r["nombre"], "FV-2-1")
        self.assertEqual(len(falso.creadas), 1, "Una sola factura aunque se mandó tres veces")
        self.assertEqual({k for _, k in falso.llamadas}, {sf.llave_idempotencia(VENTA["id"])})
        # Mandarla otra vez después (por ejemplo, el celular reintenta) devuelve la misma.
        self.assertEqual(sf.facturar(s, VENTA, PERFIL, "2026-11-20")["id"], r["id"])
        self.assertEqual(len(falso.creadas), 1)


if __name__ == "__main__":
    unittest.main()
