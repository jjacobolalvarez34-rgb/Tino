# -*- coding: utf-8 -*-
"""Utilidades de texto compartidas por lectores y reglas."""
import re
import unicodedata


def norm(s):
    """Minúsculas, sin tildes, sin puntuación, espacios colapsados."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9%$]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def num(v):
    """Valor de celda -> float. Vacío, texto o error (#REF!) -> 0.0."""
    if v is None or isinstance(v, bool):
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(" ", "")
    if not s or s.startswith("#"):
        return 0.0
    try:
        return float(s.replace(",", ""))
    except ValueError:
        return 0.0


def num_o_none(v):
    """Como num(), pero distingue 'celda vacía' (None) de 0."""
    if v is None:
        return None
    if isinstance(v, str) and not v.strip():
        return None
    return num(v)


def pesos(x):
    """Formato $1.234.567 (estilo Colombia), con signo."""
    if x is None:
        return "—"
    signo = "-" if x < 0 else ""
    return f"{signo}${abs(round(x)):,.0f}".replace(",", ".")
