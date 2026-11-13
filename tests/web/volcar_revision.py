# -*- coding: utf-8 -*-
"""Guarda filas reales de una base local y lo que calcula Python con ellas, para exigir que la
revisión en TypeScript (web/lib/revision.ts) dé exactamente lo mismo.

Uso: python tests/web/volcar_revision.py <url de Postgres local> <usuario> <desde> <hasta> <salida.json fuera del repo>
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(RAIZ / "tests" / "local")]
from cliente_psql import ClientePsql  # noqa: E402
from panel.datos import revisar as rdb  # noqa: E402
from panel.datos.empresa import Empresa  # noqa: E402
from revision import revisar  # noqa: E402

url, usuario, desde, hasta, salida = sys.argv[1:6]
c = ClientePsql(url, usuario)
emp = Empresa(c)
filas = {}
leer_original = c.leer


def leer_y_guardar(tabla, filtros=(), columnas="*", orden="id"):
    r = leer_original(tabla, filtros, columnas, orden)
    nombre = {"v_jornada": "jornadas", "v_reporte_vigente": "reportes", "v_pago_vigente": "pagos",
              "v_detalle_vigente": "detalle", "v_movimiento_vigente": "movs", "archivo_importado": "archivos"}[tabla]
    filas[nombre] = r
    return r


c.leer = leer_y_guardar
excel, banco, tarj = rdb.leer(c, emp, desde, hasta)
dias = []
for f in rdb._dias(desde, hasta):
    r = revisar(f, excel, banco, tarj, emp.lectores["config"])
    dias.append({"fecha": f, "revision": r, "guardar": rdb.para_guardar(r, excel)})
Path(salida).write_text(json.dumps({"filas": filas, "nombre": emp.etiqueta, "config": emp.lectores["config"],
                                    "desde": desde, "hasta": hasta, "dias": dias}, ensure_ascii=False, default=list),
                        encoding="utf-8")
print(f"{len(dias)} días guardados en {salida}")
