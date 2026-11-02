# -*- coding: utf-8 -*-
"""Exige que Python y TypeScript den exactamente lo mismo.

Genera entradas al azar, las corre en los dos lenguajes y compara las salidas. Una
sola diferencia es un error: ver CONTRATO.md.

Uso, desde la raíz del repositorio: python motores/comparar_lenguajes.py [cantidad]
"""
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "motores"))

from nucleo.logica import ejecutar  # noqa: E402

MONTOS = [1000, 5000, 3590, 35900, 36900, 39500, 72800, 85000, 100000, 200000, 350000]
LOTE = RAIZ / "motores" / "nucleo_ts" / "lote.ts"


def monto(r):
    return r.choice(MONTOS) if r.random() < 0.7 else r.randint(0, 9_000_000)


def items(r, prefijo, tope=8):
    return [{"monto": monto(r), "id": f"{prefijo}{i}"} for i in range(r.randint(0, tope))]


def fecha(r):
    anio, mes = r.randint(2024, 2028), r.randint(1, 12)
    return f"{anio}-{mes:02d}-{r.randint(1, 28):02d}"


def fecha_o_imposible(r):
    return r.choice([fecha(r)] * 40 + ["2026-02-30", "2026-13-01", "2028-02-29"])


# Entradas raras a propósito: aquí es donde dos lenguajes suelen separarse.
TEXTOS_RAROS = ["-0.4", "-0", "0.5", "-0.5", "123\n", " 12", "12 ", ",5", "1,,2", "1.234,567.00",
                "90,000,000,000,000.00", "90,000,000,000,000.50", "90,000,000,000,001.00",
                "-90,000,000,000,001.00", "99999999999999999999999999.99", "١٢٣", "１２", "", "-",
                ".5", "1.", "1.2.3", "$100", "١,٢٣٤.٠٠"]
FINALES_RAROS = ["", "", "", " ", " ", "\t", "\n", " ", "\r", "﻿"]


def texto_valor(r):
    if r.random() < 0.2:
        return r.choice(TEXTOS_RAROS)
    entero = r.randint(0, 99_000_000)
    con_comas = f"{entero:,}" if r.random() < 0.7 else str(entero)
    decimales = r.choice(["", ".00", ".49", ".5", ".50", ".99", ".5000"])
    return r.choice(["", "-"]) + con_comas + decimales


def linea_banco(r):
    tipo = r.choice(["PAGO QR", "PAGO LLAVE", "ABONO NEQUI", "PAGO PSE"])
    medio = r.choice(["COMPRA", "", "SIN CODIGO", "REF", "Ñ", "a b", "x y", "x\ry"])
    ref = r.choice(["", str(r.randint(1000000, 9999999999)), str(r.randint(100, 999999)),
                    f"Ñ{r.randint(1000000, 99999999)}", f"{r.randint(1000000, 99999999)}Ñ",
                    "١٢٣٤٥٦٧٨"])
    valor = r.choice([f"{r.randint(1, 3000000):,}.00", f"{r.randint(1, 900)}.{r.randint(0, 99):02d}", "SIN VALOR",
                      "1.234,567.00", "99,000,000,000,000.00", "-5,000.00"])
    return (f"{r.choice(['', '  ', chr(0xa0)])}{fecha(r).replace('-', '/')} {tipo} {medio} {ref} {valor}"
            f"{r.choice(FINALES_RAROS)}")


def generar(r):
    vecino = lambda p: {"cubre": r.random() < 0.7, "tiene_excel": r.random() < 0.7,  # noqa: E731
                        "anotado": items(r, p + "a", 5), "externo": items(r, p + "e", 5)}
    fila = lambda i: {"codigo": r.choice(["11", "22"]), "franquicia": r.choice(["VISA", "AMEX"]),  # noqa: E731
                      "fecha": f"2026-10-{i + 1:02d}", "esperado": r.choice([0, 40000, 60000, 100000, 100030]),
                      "banco": r.choice([0, 40000, 60000, 100000, 100030])}
    fes = [fecha(r) for _ in range(r.randint(0, 20))]
    return r.choice([
        ("a_pesos", {"texto": texto_valor(r)}),
        ("restar", {"a": items(r, "a"), "b": items(r, "b")}),
        ("parecidos", {"a": monto(r), "b": monto(r)}),
        ("sobrantes_vecinos", {"vecinos": [vecino(f"v{i}") for i in range(r.randint(0, 3))]}),
        ("cruzar", {"anotado": items(r, "a"), "externo": items(r, "e"),
                    "ext_vecinos": items(r, "v"), "excel_vecinos": items(r, "x")}),
        ("dia_habil_siguiente", {"fecha": fecha_o_imposible(r), "festivos": fes}),
        ("bloques_deposito", {"fechas": [r.choice(["2026-10-29", fecha_o_imposible(r)])
                                         for _ in range(r.randint(0, 15))], "festivos": fes}),
        ("coincide_deposito", {"banco": monto(r), "esperado": monto(r), "tolerancia": r.choice([0, 50, 1000]),
                               "porcentajes": r.choice([[100], [100, 90]])}),
        ("cruces_redeban", {"filas": [fila(i) for i in range(r.randint(0, 8))],
                            "tolerancia": r.choice([0, 50]), "max_cruce": r.choice([2, 3])}),
        ("estado_dia", {"descuadre": r.randint(-200000, 200000),
                        "causas": [{"regla": r.choice(["R05", "R30", "R33"]), "monto": r.randint(-200000, 200000)}
                                   for _ in range(r.randint(0, 4))],
                        "tolerancia_cuadra": r.choice([0, 100, 1000]),
                        "porcentaje_explicado": r.choice([50, 80, 100]), "reglas_sin_peso": ["R05"]}),
        ("leer_linea_transferencia", {"linea": linea_banco(r)}),
        ("punto_por_referencia", {"referencia": str(r.randint(0, 99999999)),
                                  "puntos": [{"punto": f"P{i}", "codigo": str(r.randint(10000000, 99999999))}
                                             for i in range(r.randint(0, 5))]}),
    ])


def correr_python(funcion, entrada):
    # Los mensajes de error pueden variar entre lenguajes; que falle, no.
    try:
        return ejecutar(funcion, entrada)
    except Exception:
        return {"error": True}


def main():
    cantidad = int(sys.argv[1]) if len(sys.argv) > 1 else 50000
    r = random.Random(20261102)
    pruebas = [generar(r) for _ in range(cantidad)]
    python = [correr_python(f, e) for f, e in pruebas]

    with tempfile.TemporaryDirectory() as carpeta:
        entrada, salida = Path(carpeta) / "entrada.json", Path(carpeta) / "salida.json"
        entrada.write_text(json.dumps([{"funcion": f, "entrada": e} for f, e in pruebas]), encoding="utf-8")
        subprocess.run(["node", "--experimental-strip-types", "--no-warnings", str(LOTE), str(entrada), str(salida)],
                       check=True)
        typescript = [{"error": True} if isinstance(x, dict) and "error" in x else x
                      for x in json.loads(salida.read_text(encoding="utf-8"))]

    distintos = [(p, a, b) for p, a, b in zip(pruebas, python, typescript) if a != b]
    por_funcion = {}
    for (f, _), a, b in zip(pruebas, python, typescript):
        total, malos = por_funcion.get(f, (0, 0))
        por_funcion[f] = (total + 1, malos + (a != b))
    for f, (total, malos) in sorted(por_funcion.items()):
        print(f"{f:28} {total:6} comparaciones, {malos} distintas")
    print(f"Total: {len(pruebas)} comparaciones, {len(distintos)} distintas")
    for (f, e), a, b in distintos[:5]:
        print(f"\n{f} {json.dumps(e, ensure_ascii=False)}\n  Python:     {a}\n  TypeScript: {b}")
    sys.exit(1 if distintos or len(typescript) != len(python) else 0)


if __name__ == "__main__":
    main()
