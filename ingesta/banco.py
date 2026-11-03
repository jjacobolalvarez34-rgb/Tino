# -*- coding: utf-8 -*-
"""Lee el PDF de movimientos de Bancolombia: transferencias por punto y pagos sin origen.

El punto sale de los últimos 4 dígitos de la referencia del QR o la llave (D-026). Los
códigos de cada punto llegan en `puntos["codigos"]`: punto -> código.
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "motores"))

from nucleo.logica import leer_linea_transferencia, punto_por_referencia  # noqa: E402

FECHA = re.compile(r"^\s*([0-9]{4})/([0-9]{2})/([0-9]{2})\s")


def leer(ruta, puntos):
    """Devuelve {'transferencias', 'sin_origen', 'fechas', 'avisos'}."""
    import pdfplumber

    codigos = [{"punto": p, "codigo": c} for p, c in puntos.get("codigos", {}).items()]
    transferencias, sin_origen, fechas, avisos = [], [], set(), []
    with pdfplumber.open(str(ruta)) as pdf:
        for pagina, hoja in enumerate(pdf.pages, start=1):
            for numero, linea in enumerate((hoja.extract_text() or "").split("\n"), start=1):
                m = FECHA.match(linea)
                if m:
                    fechas.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
                pago = leer_linea_transferencia(linea)
                if pago is None or pago["valor"] <= 0:
                    continue
                pago["id"] = f"{Path(ruta).name}|p{pagina}|l{numero}"
                punto = punto_por_referencia(pago["referencia"], codigos) if pago["referencia"] else None
                (transferencias if punto else sin_origen).append({**pago, "punto": punto})
    if not fechas:
        avisos.append(f"{Path(ruta).name}: no se encontraron movimientos con fecha.")
    return {"transferencias": transferencias, "sin_origen": sin_origen, "fechas": fechas, "avisos": avisos}
