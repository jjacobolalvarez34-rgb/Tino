# -*- coding: utf-8 -*-
"""Lee el Excel diario de un punto y lo deja en pesos enteros, día por día.

El formato de la plantilla es de Milagros: por eso se usa el lector del conciliador
(`motores/conciliador/cierre/lector_xlsx.py`), que ya lo conoce. Se usa la clase directa
y no `leer_libro`, que guarda caché en C:. Otro cliente tendrá su propio lector, que
entregue lo mismo.

Qué punto es cada libro llega en `puntos["excel"]`: texto del Excel -> nombre del punto.
"""
import re
import sys
import unicodedata
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "motores"), str(RAIZ / "motores" / "conciliador")]

from nucleo.logica import a_pesos  # noqa: E402


def _norm(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def _pesos(valor):
    if valor is None:
        return None
    return a_pesos(format(Decimal(str(valor)), "f"))


def _items(lista, punto, fecha, rol):
    return [{"monto": _pesos(monto), "id": f"{punto}|{fecha}|{rol}|fila {fila}"}
            for fila, monto in lista if _pesos(monto)]


def leer(ruta, puntos):
    """Devuelve (punto, {fecha: día}, avisos). Montos en pesos enteros."""
    from cierre.lector_xlsx import LibroXlsx

    libro = LibroXlsx(str(ruta))
    nombres = {_norm(k): v for k, v in puntos.get("excel", {}).items()}
    punto = nombres.get(_norm(libro.punto_texto)) or nombres.get(_norm(Path(ruta).stem))
    avisos = list(libro.avisos)
    if punto is None:
        avisos.append(f"No se sabe de qué punto es este libro: {libro.punto_texto!r}.")
        return None, {}, avisos

    dias = {}
    for fecha, dia in libro.dias.items():
        f = fecha.isoformat()
        dias[f] = {
            "transferencias": _items(dia.pagos.transferencias, punto, f, "transferencia"),
            "tarjetas": _items(dia.pagos.debito, punto, f, "debito") + _items(dia.pagos.credito, punto, f, "credito"),
            "descuadre": _pesos(dia.caja.descuadre),
            "venta": _pesos(dia.caja.valor_teorico),
            "asesoras": dia.asesoras_texto,
        }
    return punto, dias, avisos
