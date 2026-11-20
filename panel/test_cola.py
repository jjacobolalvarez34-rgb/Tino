# -*- coding: utf-8 -*-
"""Prueba del procesador de la cola (D-057) sin red: un cliente falso en memoria.

Uso, desde la raíz del repositorio: python -m unittest panel.test_cola
"""
import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("TEMP", tempfile.gettempdir())

from panel.datos.cliente import ErrorBase  # noqa: E402
from panel.servicio import Servicio  # noqa: E402


class ClienteFalso:
    def __init__(self, cola, datos):
        self.cola, self.datos, self.cambios = cola, datos, []

    def leer(self, tabla, filtros=(), columnas="*", orden="id"):
        assert tabla == "archivo_en_cola"
        return [dict(f) for f in self.cola if all(str(f.get(c)) == str(v) for c, _, v in filtros)]

    def cambiar(self, tabla, filtros, valores):
        filas = [f for f in self.cola if all(str(f.get(c)) == str(v) for c, _, v in filtros)]
        for f in filas:
            f.update(valores)
        self.cambios.append(valores)
        return filas

    def bajar(self, carpeta, ruta):
        if ruta not in self.datos:
            raise ErrorBase("No se pudo bajar el archivo de la cola (error 404).", "404")
        return self.datos[ruta]


class Cola(unittest.TestCase):
    def servicio(self, cola, datos, preparar, subir):
        s = Servicio(ClienteFalso(cola, datos))
        s.preparar, s.subir = preparar, subir
        return s

    def test_cargado_repetido_y_error(self):
        cola = [{"id": "1", "ruta": "e/h1/dia.xlsx", "nombre": "dia.xlsx", "estado": "en_cola"},
                {"id": "2", "ruta": "e/h2/viejo.xlsx", "nombre": "viejo.xlsx", "estado": "en_cola"},
                {"id": "3", "ruta": "e/h3/raro.csv", "nombre": "raro.csv", "estado": "en_cola"},
                {"id": "4", "ruta": "e/h4/falta.xlsx", "nombre": "falta.xlsx", "estado": "en_cola"},
                {"id": "5", "ruta": "e/h5/otro.xlsx", "nombre": "otro.xlsx", "estado": "cargado"}]
        datos = {"e/h1/dia.xlsx": b"1", "e/h2/viejo.xlsx": b"2", "e/h3/raro.csv": b"3"}

        def preparar(rutas):
            nombre = Path(rutas[0]).name
            self.assertTrue(Path(rutas[0]).exists())  # se bajó a una carpeta temporal antes de leerlo
            if nombre == "raro.csv":
                return [{"clave": None, "nombre": nombre, "error": "No se sabe de qué punto es este Excel."}]
            return [{"clave": nombre, "nombre": nombre}]

        def subir(clave):
            if clave == "viejo.xlsx":
                raise ErrorBase("Eso ya estaba: no se repite.", "23505")
            return {"archivo": "arch-" + clave}

        s = self.servicio(cola, datos, preparar, subir)
        self.assertEqual(s.procesar_cola(), {"cargados": 1, "repetidos": 1, "errores": 2})
        estado = {f["id"]: (f["estado"], f.get("archivo_id"), f.get("mensaje")) for f in cola}
        self.assertEqual(estado["1"], ("cargado", "arch-dia.xlsx", None))
        self.assertEqual(estado["2"][0], "repetido")
        self.assertEqual(estado["3"][0], "error")
        self.assertIn("No se sabe de qué punto", estado["3"][2])
        self.assertEqual(estado["4"][0], "error")
        self.assertIn("404", estado["4"][2])
        self.assertEqual(estado["5"][0], "cargado")  # lo que no estaba en cola no se toca

    def test_lo_que_otro_tomo_no_se_procesa(self):
        cola = [{"id": "1", "ruta": "e/h1/dia.xlsx", "nombre": "dia.xlsx", "estado": "en_cola"}]
        s = self.servicio(cola, {"e/h1/dia.xlsx": b"1"}, lambda r: self.fail("no debía leerlo"), None)
        s.c.cambiar = lambda tabla, filtros, valores: []  # otro programa lo tomó primero
        self.assertEqual(s.procesar_cola(), {"cargados": 0, "repetidos": 0, "errores": 0})


if __name__ == "__main__":
    unittest.main()
