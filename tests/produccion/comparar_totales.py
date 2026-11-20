# -*- coding: utf-8 -*-
"""Compara, punto por punto, la venta por persona de un mes entre dos bases (pruebas y
producción), con el usuario de la empresa en cada una. Solo lee. Imprime totales, no nombres
de personas.

Uso: python tests/produccion/comparar_totales.py <conexión A.json> <usuario A.json> <conexión B.json> <usuario B.json> <AAAA-MM>
     Cada conexión es un JSON con "url" y "llave_publica"; cada usuario, con "correo" y "clave".
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from panel.datos.cliente import Cliente  # noqa: E402


def leer(conexion, usuario, mes):
    c = json.loads(Path(conexion).read_text(encoding="utf-8"))
    u = json.loads(Path(usuario).read_text(encoding="utf-8"))
    cli = Cliente(c["url"], c["llave_publica"])
    cli.iniciar_sesion(u["correo"], u["clave"])
    nombres = {p["id"]: p["nombre"] for p in cli.leer("punto_venta", columnas="id,nombre")}
    desde, hasta = f"{mes}-01", f"{mes}-31"
    filas = cli.leer("v_venta_asesora", [("fecha", "gte", desde), ("fecha", "lte", hasta)], "punto_id,venta,asesora_id", "fecha")
    suma = defaultdict(int)
    for f in filas:
        suma[nombres.get(f["punto_id"], "?")] += f["venta"]
    sin = sum(f["venta"] for f in filas if not f["asesora_id"])
    metas = sum(m["monto"] for m in cli.leer("meta_periodo", [("activo", "eq", "true"), ("desde", "lte", hasta),
                                                              ("hasta", "gte", desde), ("asesora_id", "is", "null")], "monto", "desde"))
    return dict(suma), sin, metas


def main():
    a, sin_a, metas_a = leer(sys.argv[1], sys.argv[2], sys.argv[5])
    b, sin_b, metas_b = leer(sys.argv[3], sys.argv[4], sys.argv[5])
    iguales = True
    print(f"{'Punto':28} {'A':>14} {'B':>14}")
    for p in sorted(set(a) | set(b)):
        marca = "" if a.get(p) == b.get(p) else "  ■ distinto"
        iguales &= not marca
        print(f"{p[:28]:28} {a.get(p, 0):>14,} {b.get(p, 0):>14,}{marca}".replace(",", "."))
    print(f"{'TOTAL':28} {sum(a.values()):>14,} {sum(b.values()):>14,}".replace(",", "."))
    print(f"{'Sin persona':28} {sin_a:>14,} {sin_b:>14,}".replace(",", "."))
    print(f"{'Metas de los puntos':28} {metas_a:>14,} {metas_b:>14,}".replace(",", "."))
    print("\nCuadran punto por punto." if iguales else "\nHay puntos distintos.")
    sys.exit(0 if iguales else 1)


if __name__ == "__main__":
    main()
