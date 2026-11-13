# -*- coding: utf-8 -*-
"""Lee el extracto del banco completo y ordena cada línea por tipo (D-040).

Qué es cada línea lo deciden reglas: primero las del perfil del banco de la empresa
(`puntos["banco"]["reglas"]`, desde perfil_fuente) y después las del formato del banco.
Las del formato solo describen lo que escribe el banco en su extracto; nada de un
cliente va aquí. El punto de una transferencia con código sale de los últimos 4 dígitos
de la referencia (D-026), con los códigos de `puntos["codigos"]`.

Categorías que entiende Tino:
  transferencia  pago de un cliente con código de punto
  sin_codigo     pago de un cliente sin código (Nequi, otro banco): queda sin punto
  deposito       abono de un datáfono (Bold, Redeban)
  consignacion   plata que el punto lleva al banco
  abono, cargo   cualquier otra entrada o salida
"""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "motores"))

from nucleo.logica import clasificar_linea_banco, punto_por_referencia  # noqa: E402

FECHA = re.compile(r"^\s*([0-9]{4})/([0-9]{2})/([0-9]{2})\s")


def _regla(prefijo, categoria, etiqueta=None, con_codigo=False):
    return {"prefijo": prefijo, "categoria": categoria, "etiqueta": etiqueta, "con_codigo": con_codigo}


# Lo que escribe cada banco en su extracto. Se agrega un banco nuevo aquí, una vez, y
# sirve para todas las empresas que lo usen.
FORMATOS = {
    "bancolombia": {
        "banco": "Bancolombia",
        "reglas": [
            _regla("PAGO QR", "transferencia", "QR", True),
            _regla("PAGO LLAVE", "transferencia", "Llave", True),
            _regla("TRANSFERENCIA DESDE", "sin_codigo", "Nequi u otro banco"),
            _regla("TRANSFERENCIA CTA", "sin_codigo", "Transferencia de cuenta"),
            _regla("PAGO INTERBANC BOLD", "deposito", "Bold"),
            _regla("PAGO INTERBANC", "sin_codigo", "Interbancaria"),
            _regla("ABONO NETO", "deposito", "Redeban"),
            _regla("CONSIG", "consignacion", "Consignación"),
        ],
    },
}
TIPO = {"transferencia": "transferencia", "sin_codigo": "transferencia", "deposito": "deposito",
        "consignacion": "consignacion", "abono": "otro", "cargo": "cargo"}


def configuracion(puntos):
    """Formato y reglas de la empresa: las suyas primero, luego las del formato."""
    perfil = puntos.get("banco") or {}
    formato = FORMATOS.get(perfil.get("formato") or "bancolombia", FORMATOS["bancolombia"])
    return formato["banco"], list(perfil.get("reglas", [])) + formato["reglas"]


def leer(ruta, puntos):
    """Devuelve {'transferencias', 'sin_origen', 'otros', 'fechas', 'avisos', 'banco'}."""
    import pdfplumber

    banco, reglas = configuracion(puntos)
    codigos = [{"punto": p, "codigo": c} for p, c in puntos.get("codigos", {}).items()]
    transferencias, sin_origen, otros, fechas, avisos = [], [], [], set(), []
    fila = 0  # línea del PDF contada de corrido, para guardar de dónde salió cada movimiento
    with pdfplumber.open(str(ruta)) as pdf:
        for pagina, hoja in enumerate(pdf.pages, start=1):
            for numero, linea in enumerate((hoja.extract_text() or "").split("\n"), start=1):
                fila += 1
                m = FECHA.match(linea)
                if m:
                    fechas.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
                mov = clasificar_linea_banco(linea, reglas)
                if mov is None or mov["valor"] == 0:
                    continue
                # Lo que sale de la cuenta es un cargo, aunque se llame "transferencia".
                tipo = TIPO.get(mov["categoria"], "otro") if mov["valor"] > 0 else "cargo"
                mov.update({"id": f"{Path(ruta).name}|p{pagina}|l{numero}", "fila_origen": fila,
                            "tipo": tipo, "punto": None})
                if mov["categoria"] in ("transferencia", "sin_codigo") and mov["valor"] > 0:
                    if mov["referencia"]:
                        mov["punto"] = punto_por_referencia(mov["referencia"], codigos)
                    (transferencias if mov["punto"] else sin_origen).append(mov)
                else:
                    otros.append(mov)
    if not fechas:
        avisos.append(f"{Path(ruta).name}: no se encontraron movimientos con fecha. ¿Es el extracto del banco?")
    return {"transferencias": transferencias, "sin_origen": sin_origen, "otros": otros, "fechas": fechas,
            "avisos": avisos, "banco": banco}
