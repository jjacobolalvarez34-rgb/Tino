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

# Empacado como .exe, la plantilla viaja dentro del programa.
PLANTILLA = (Path(sys._MEIPASS) / "tablero" if getattr(sys, "frozen", False) else Path(__file__).parent) / "plantilla.html"
TODOS = "Todos los puntos"
TODO_EL_PERIODO = "todo"


def armar_datos(cobros, avisos):
    """Una vista por periodo y punto, ya calculada: la pantalla no calcula."""
    puntos = sorted({c["punto"] for c in cobros})
    meses = sorted({c["fecha"][:7] for c in cobros})
    vistas, por_mes = {}, {}
    for punto in [TODOS] + puntos:
        del_punto = [c for c in cobros if punto == TODOS or c["punto"] == punto]
        vistas[f"{TODO_EL_PERIODO}|{punto}"] = estadisticas_ventas(del_punto)
        por_mes[punto] = []
        for mes in meses:
            del_mes = [c for c in del_punto if c["fecha"].startswith(mes)]
            v = estadisticas_ventas(del_mes)
            vistas[f"{mes}|{punto}"] = v
            por_mes[punto].append({"clave": mes, **v["totales"]})
    return {"todos": TODOS, "todo_el_periodo": TODO_EL_PERIODO, "puntos": puntos, "meses": meses,
            "vistas": vistas, "por_mes": por_mes, "avisos": avisos}


def escribir(datos, salida):
    # Sin </ dentro del JSON: un nombre raro no debe poder cerrar la etiqueta script.
    incrustado = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
    html = PLANTILLA.read_text(encoding="utf-8").replace("/*DATOS*/null", incrustado)
    Path(salida).write_text(html, encoding="utf-8")


def generar(ruta_puntos, salida, archivos):
    """Arma el tablero y lo guarda en `salida`. Devuelve (cobros, avisos)."""
    puntos = json.loads(Path(ruta_puntos).read_text(encoding="utf-8"))
    lotes, avisos = [], []
    for archivo in archivos:
        leidos, sus_avisos = tarjetas.leer(archivo, puntos)
        lotes.append(leidos)
        avisos += [f"{Path(archivo).name}: {x}" for x in sus_avisos]
    # El mismo mes puede venir en varios archivos: no se cuenta dos veces.
    cobros = tarjetas.unir_reportes(lotes)
    escribir(armar_datos(cobros, avisos), salida)
    return cobros, avisos


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--puntos", required=True, help="JSON con el punto de cada datáfono")
    args.add_argument("--salida", required=True, help="HTML de salida, fuera del repositorio")
    args.add_argument("archivos", nargs="+", help="Reportes de Bold o Redeban (.xlsx)")
    a = args.parse_args()

    cobros, avisos = generar(a.puntos, a.salida, a.archivos)
    print(f"{len(cobros)} cobros de {len(a.archivos)} archivo(s). Tablero en {a.salida}")
    for aviso in avisos:
        print(f"  Aviso: {aviso}")


if __name__ == "__main__":
    main()
