# -*- coding: utf-8 -*-
"""Corre tests/casos/motor/casos.json. Desde motores/: python -m unittest nucleo.test_casos"""
import json
import unittest
from pathlib import Path

from nucleo.logica import ejecutar

CASOS = Path(__file__).resolve().parents[2] / "tests" / "casos" / "motor" / "casos.json"


class Casos(unittest.TestCase):
    def test_casos(self):
        casos = json.loads(CASOS.read_text(encoding="utf-8"))
        self.assertTrue(casos)
        for caso in casos:
            with self.subTest(funcion=caso["funcion"], nombre=caso["nombre"]):
                self.assertEqual(ejecutar(caso["funcion"], caso["entrada"]), caso["esperado"])


if __name__ == "__main__":
    unittest.main()
