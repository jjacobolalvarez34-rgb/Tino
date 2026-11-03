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


def _fila(celdas, rol):
    """La fila de una celda como "B204", para guardar de dónde salió el dato."""
    m = re.search(r"([0-9]+)$", str(celdas.get(rol) or ""))
    return int(m.group(1)) if m else None


def _caja(dia):
    """Lo que el punto reportó de su caja, con la fila de cada dato."""
    c, celdas = dia.caja, dia.celdas
    movimientos = [{"tipo": tipo, "monto": _pesos(getattr(c, campo)), "fila": _fila(celdas, f"caja.{campo}")}
                   for tipo, campo in (("consignacion", "consignacion"), ("gasto", "gastos"), ("base", "base"))]
    return {"hoja": dia.hoja, "fila": _fila(celdas, "caja.descuadre"), "efectivo": _pesos(c.efectivo_contado),
            "fila_asesoras": _fila(celdas, "asesoras"), "fila_venta": _fila(celdas, "caja.valor_teorico"),
            "movimientos": [m for m in movimientos if m["monto"] and m["fila"]]}


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
            # Para la pista de "suma de precios": se movió si salió por Siigo o en efectivo.
            "productos": [{"precio": _pesos(p.precio) or 0, "nombre": p.nombre,
                           "movimiento": 1 if (p.salidas_tot or p.efectivo_cant) else 0,
                           # Para guardarlo en la base: cuánto salió, por cuánto y de qué fila.
                           "fila": p.fila, "cantidad": int(p.salidas_tot or 0), "valor": _pesos(p.valor) or 0,
                           "descuento": abs(_pesos(p.descuento) or 0), "regalos": int(p.regalos_cant or 0)}
                          for p in dia.productos],
            "lista_asesoras": list(dia.asesoras),
            "caja": _caja(dia),
        }
    return punto, dias, avisos
