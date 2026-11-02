# -*- coding: utf-8 -*-
"""
Unifica los nombres de asesoras. En la celda NOMBRE ASESORA aparece a veces el
nombre completo ("Ana Pérez") y a veces solo el primero ("Ana",
"Ana Y Luisa"). Sin unificar, la pantalla Asesora vería dos personas.

Regla: un nombre de una sola palabra se une al nombre completo del MISMO punto
que empiece igual, si hay exactamente uno. Si hay dos "Ana ..." distintas en
el punto, no se adivina. El alias de la configuración siempre gana.
"""
from .texto import norm


def _bonito(nombre):
    return " ".join(w.capitalize() for w in str(nombre).split())


def construir_mapa(nombres_por_punto, alias=None):
    """nombres_por_punto: {punto: {nombre crudo, ...}}.
    alias: {"ana": "Ana Pérez", ...} (claves sin tildes ni mayúsculas).
    Devuelve {(punto, nombre crudo): nombre canónico}."""
    alias = {norm(k): v for k, v in (alias or {}).items() if not k.startswith("_")}
    mapa = {}
    for punto, nombres in nombres_por_punto.items():
        completos = {}
        for n in nombres:
            partes = norm(n).split()
            if len(partes) >= 2:
                completos.setdefault(partes[0], set()).add(_bonito(n))
        for n in nombres:
            clave = norm(n)
            if clave in alias:
                mapa[(punto, n)] = alias[clave]
                continue
            partes = clave.split()
            candidatos = completos.get(partes[0], set()) if len(partes) == 1 else set()
            mapa[(punto, n)] = next(iter(candidatos)) if len(candidatos) == 1 else _bonito(n)
    return mapa
