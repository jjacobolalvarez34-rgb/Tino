# -*- coding: utf-8 -*-
"""Arma la revisión de la mañana de un día en un solo archivo HTML.

Uso, desde la raíz del repositorio:
    python panel/revision/armar.py --fecha 2026-09-16 --puntos puntos.json --salida revision.html
        --excel libro1.xlsx ... --banco extracto.pdf ... --tarjetas bold.xlsx redeban.xlsx ...

puntos.json trae lo propio de la empresa: qué datáfono, Excel y código de pago es de cada
punto, y su configuración (tolerancia_cuadra, porcentaje_explicado, reglas_sin_peso). El
HTML lleva datos del cliente: se guarda fuera del repositorio.
"""
import argparse
import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores")]

from ingesta import banco as lector_banco  # noqa: E402
from ingesta import excel_diario, tarjetas  # noqa: E402
from revision import revisar  # noqa: E402

# Empacado como .exe, la plantilla viaja dentro del programa.
PLANTILLA = (Path(sys._MEIPASS) / "revision" if getattr(sys, "frozen", False) else Path(__file__).parent) / "plantilla.html"


def leer_todo(a, puntos):
    avisos, excel = [], {}
    for ruta in a.excel:
        punto, dias, sus = excel_diario.leer(ruta, puntos)
        avisos += [f"{Path(ruta).name}: {x}" for x in sus]
        if punto:
            excel.setdefault(punto, {}).update(dias)

    banco = {"por_dia": {}, "fechas": set(), "sin_origen": []}
    for ruta in a.banco:
        b = lector_banco.leer(ruta, puntos)
        avisos += b["avisos"]
        banco["fechas"] |= b["fechas"]
        banco["sin_origen"] += b["sin_origen"]
        for t in b["transferencias"]:
            banco["por_dia"].setdefault((t["fecha"], t["punto"]), []).append({"monto": t["valor"], "id": t["id"]})

    lotes = []
    for ruta in a.tarjetas:
        cobros, sus = tarjetas.leer(ruta, puntos)
        lotes.append(cobros)
        avisos += [f"{Path(ruta).name}: {x}" for x in sus]
    tarj = {"por_dia": {}, "cubre": {}}
    for i, c in enumerate(tarjetas.unir_reportes(lotes)):
        # Una reversión no está en el Excel: se muestra aparte, no se cruza.
        if c["bruto"] < 0:
            avisos.append(f"Reversión de {c['proveedor']} en {c['punto']} el {c['fecha']}: {-c['bruto']} pesos.")
            continue
        tarj["por_dia"].setdefault((c["fecha"], c["punto"]), []).append(
            {"monto": c["bruto"], "id": f"{c['proveedor']}|{c['fecha']}|{i}"})
        tarj["cubre"].setdefault(c["punto"], set()).add(c["fecha"])
    # Un reporte cubre todos los días entre el primero y el último de cada punto.
    for punto, fechas in tarj["cubre"].items():
        a0, a1 = dt.date.fromisoformat(min(fechas)), dt.date.fromisoformat(max(fechas))
        tarj["cubre"][punto] = {(a0 + dt.timedelta(days=k)).isoformat() for k in range((a1 - a0).days + 1)}
    return excel, banco, tarj, avisos


def generar(fecha, ruta_puntos, salida, excel=(), banco=(), tarjetas=()):
    """Arma la revisión y la guarda en `salida`. Devuelve (resultado, avisos)."""
    a = argparse.Namespace(excel=list(excel), banco=list(banco), tarjetas=list(tarjetas))
    puntos = json.loads(Path(ruta_puntos).read_text(encoding="utf-8"))
    excel_dias, banco_dias, tarj, avisos = leer_todo(a, puntos)
    resultado = revisar(fecha, excel_dias, banco_dias, tarj, puntos["config"])
    avisos += [f"Falta configurar «{c}» en puntos.json: esa causa no se revisó." for c in resultado["sin_configurar"]]
    resultado["avisos"] = avisos
    resultado["fuentes"] = {"excel": len(a.excel), "banco": len(a.banco), "tarjetas": len(a.tarjetas)}
    datos = json.dumps(resultado, ensure_ascii=False).replace("</", "<\\/")
    Path(salida).write_text(PLANTILLA.read_text(encoding="utf-8").replace("/*DATOS*/null", datos), encoding="utf-8")
    return resultado, avisos


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fecha", required=True)
    p.add_argument("--puntos", required=True)
    p.add_argument("--salida", required=True)
    p.add_argument("--excel", nargs="*", default=[])
    p.add_argument("--banco", nargs="*", default=[])
    p.add_argument("--tarjetas", nargs="*", default=[])
    a = p.parse_args()
    resultado, avisos = generar(a.fecha, a.puntos, a.salida, a.excel, a.banco, a.tarjetas)
    print(f"Revisión del {a.fecha}: {len(resultado['puntos'])} punto(s). Archivo: {a.salida}")
    for aviso in avisos:
        print("  Aviso:", aviso)


if __name__ == "__main__":
    main()
