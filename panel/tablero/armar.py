# -*- coding: utf-8 -*-
"""Arma el tablero de ventas con tarjeta en un solo archivo HTML.

Uso, desde la raíz del repositorio:
    python panel/tablero/armar.py --puntos puntos.json --salida tablero.html reporte1.xlsx ...

puntos.json dice qué datáfono es de qué punto; ver ingesta/tarjetas.py. El HTML
lleva datos del cliente: guárdalo fuera del repositorio. Los cálculos los hace el
núcleo; la pantalla solo los muestra.
"""
import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores")]

from ingesta import tarjetas  # noqa: E402
from nucleo.logica import estadisticas_ventas  # noqa: E402

PLANTILLA = Path(__file__).with_name("plantilla.html")
TODOS = "Todos los puntos"


def armar_datos(cobros, avisos):
    """Una vista por punto y una con todos, ya calculadas: la pantalla no calcula."""
    puntos = sorted({c["punto"] for c in cobros})
    vistas = {TODOS: estadisticas_ventas(cobros)}
    for punto in puntos:
        vistas[punto] = estadisticas_ventas([c for c in cobros if c["punto"] == punto])
    fechas = sorted(c["fecha"] for c in cobros)
    return {"todos": TODOS, "puntos": puntos, "vistas": vistas, "avisos": avisos,
            "desde": fechas[0] if fechas else None, "hasta": fechas[-1] if fechas else None}


def escribir(datos, salida):
    # Sin </ dentro del JSON: un nombre raro no debe poder cerrar la etiqueta script.
    incrustado = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    html = PLANTILLA.read_text(encoding="utf-8").replace("/*DATOS*/null", incrustado)
    Path(salida).write_text(html, encoding="utf-8")


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--puntos", required=True, help="JSON con el punto de cada datáfono")
    args.add_argument("--salida", required=True, help="HTML de salida, fuera del repositorio")
    args.add_argument("archivos", nargs="+", help="Reportes de Bold o Redeban (.xlsx)")
    a = args.parse_args()

    puntos = json.loads(Path(a.puntos).read_text(encoding="utf-8"))
    cobros, avisos = [], []
    for archivo in a.archivos:
        leidos, sus_avisos = tarjetas.leer(archivo, puntos)
        cobros += leidos
        avisos += [f"{Path(archivo).name}: {x}" for x in sus_avisos]

    escribir(armar_datos(cobros, avisos), a.salida)
    print(f"{len(cobros)} cobros de {len(a.archivos)} archivo(s). Tablero en {a.salida}")
    for aviso in avisos:
        print(f"  Aviso: {aviso}")


if __name__ == "__main__":
    main()
