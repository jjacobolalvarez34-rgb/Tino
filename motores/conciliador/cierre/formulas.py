# -*- coding: utf-8 -*-
"""
Normaliza fórmulas a una "forma" independiente de letras y filas, para
comparar contra la plantilla aunque haya columnas insertadas (hoja 17) o el
día anterior cambie de nombre.

  ='09'!E8           -> ={PREV:inv_final@0}
  =F57+L59           -> ={salidas_siigo@0}+{efectivo_cant@2}
  ='04'!B189+H179    -> ={PREV:caja.efectivo_contado}+{caja.sencillo_recibido}
  =SUM(H7:H167)      -> =SUM({valor[7:167]})

Y al revés: `renderizar` convierte una forma a A1 en el contexto de una hoja.
"""
import re

from openpyxl.formula.tokenizer import Tokenizer, Token

REF_RE = re.compile(
    r"^(?:(?:'(?P<hq>[^']+)'|(?P<h>[A-Za-z0-9_ ]+))!)?"
    r"\$?(?P<c1>[A-Z]{1,3})\$?(?P<r1>\d+)"
    r"(?::\$?(?P<c2>[A-Z]{1,3})\$?(?P<r2>\d+))?$")
CELDA_RE = re.compile(r"^([A-Z]{1,3})(\d+)$")


class Contexto:
    """Mapa de roles de una hoja (DiaPunto.celdas) listo para traducir refs."""

    def __init__(self, dia):
        self.hoja = dia.hoja
        self.fila_enc = dia.celdas.get("fila_encabezado", 0)
        self.fila_tot = dia.fila_totales or 0
        self.col_a_rol = {}
        self.rol_a_col = {}
        self.celda_a_rol = {}
        self.rol_a_celda = {}
        for k, v in dia.celdas.items():
            if k.startswith("col."):
                self.col_a_rol[v] = k[4:]
                self.rol_a_col[k[4:]] = v
            elif k.startswith(("caja.", "tot.")) and isinstance(v, str):
                # tot.valor y caja.valor_teorico son la misma celda: gana tot.
                if v not in self.celda_a_rol or k.startswith("tot."):
                    self.celda_a_rol[v] = k
                self.rol_a_celda[k] = v
        self.rol_a_celda.setdefault("caja.valor_teorico", self.rol_a_celda.get("tot.valor"))


def _es_producto(ctx, fila):
    return ctx.fila_enc < fila < ctx.fila_tot


def _ref_a_forma(texto, fila_formula, ctx, ctx_prev, nombre_prev):
    m = REF_RE.match(texto.replace("$", ""))
    if not m:
        return texto.upper()
    hoja = m.group("hq") or m.group("h")
    if hoja is None or hoja == ctx.hoja:
        destino, prefijo = ctx, ""
    elif nombre_prev is not None and hoja == nombre_prev and ctx_prev is not None:
        destino, prefijo = ctx_prev, "PREV:"
    else:
        return "{HOJA:" + hoja + "!" + texto.split("!")[-1].replace("$", "") + "}"

    c1, r1 = m.group("c1"), int(m.group("r1"))
    if m.group("c2"):
        c2, r2 = m.group("c2"), int(m.group("r2"))
        rol = destino.col_a_rol.get(c1)
        # Solo es "rango de un rol" si toca filas de productos; C179:C185 (los
        # billetes, debajo de los totales) es un rango literal aunque C sea INV. INICIAL.
        toca_productos = r1 < destino.fila_tot and r2 > destino.fila_enc
        if rol and c1 == c2 and toca_productos:
            return "{" + prefijo + f"{rol}[{r1}:{r2}]" + "}"
        return "{" + prefijo + f"{c1}{r1}:{c2}{r2}" + "}"

    celda = f"{c1}{r1}"
    if celda in destino.celda_a_rol:
        return "{" + prefijo + destino.celda_a_rol[celda] + "}"
    rol = destino.col_a_rol.get(c1)
    if rol and _es_producto(destino, r1):
        if fila_formula is not None and _es_producto(ctx, fila_formula):
            return "{" + prefijo + f"{rol}@{r1 - fila_formula}" + "}"
        return "{" + prefijo + f"{rol}#{r1}" + "}"
    return "{" + prefijo + celda + "}"


def forma(formula, celda, ctx, ctx_prev=None, nombre_prev=None):
    """Forma normalizada de una fórmula. None si no es fórmula."""
    if not isinstance(formula, str) or not formula.startswith("="):
        return None
    m = CELDA_RE.match(celda)
    fila = int(m.group(2)) if m else None
    try:
        tok = Tokenizer(formula)
    except Exception:
        return formula.replace(" ", "").replace("$", "").upper()
    partes = []
    for t in tok.items:
        if t.type == Token.WSPACE:
            continue
        if t.type == Token.OPERAND and t.subtype == Token.RANGE:
            partes.append(_ref_a_forma(t.value, fila, ctx, ctx_prev, nombre_prev))
        else:
            partes.append(t.value.upper())
    return "=" + "".join(partes)


_RANGO_LITERAL_RE = re.compile(r"^([A-Z]{1,3})(\d+):([A-Z]{1,3})(\d+)$")


def _terminos_suma(f):
    """Si la forma es solo una suma (con o sin SUM(), paréntesis) devuelve la
    lista ordenada de términos, expandiendo rangos literales de una columna.
    None si tiene otra cosa (restas, productos, funciones distintas)."""
    if not f:
        return None
    s = f.replace("SUMA(", "(").replace("SUM(", "(")   # SUMA: Sheets en español
    sin_ph = PLACEHOLDER_RE.sub("", s)
    if any(ch not in "=()+" for ch in sin_ph):
        return None
    terminos = []
    for ph in PLACEHOLDER_RE.findall(s):
        m = _RANGO_LITERAL_RE.match(ph)
        if m and m.group(1) == m.group(3):
            terminos += [f"{m.group(1)}{r}" for r in range(int(m.group(2)), int(m.group(4)) + 1)]
        else:
            terminos.append(ph)
    return sorted(terminos)


def equivalentes(a, b):
    """Igualdad de formas tolerando sumas escritas distinto
    (=SUM(C179:C185) equivale a =C179+C180+...+C185)."""
    if a == b:
        return True
    ta, tb = _terminos_suma(a), _terminos_suma(b)
    return ta is not None and ta == tb


def sin_desplazamientos(f):
    """Forma con los @n reemplazados, para reconocer 'referencias corridas'."""
    return re.sub(r"@-?\d+", "@*", f or "")


def desplazamientos(f):
    return [int(x) for x in re.findall(r"@(-?\d+)", f or "")]


PLACEHOLDER_RE = re.compile(r"\{([^}]*)\}")


def renderizar(forma_txt, celda, ctx, ctx_prev=None, nombre_prev=None):
    """Forma -> fórmula A1 en la hoja de `ctx`, celda `celda`."""
    if not forma_txt:
        return ""
    m = CELDA_RE.match(celda)
    fila = int(m.group(2)) if m else 0

    def sub(mm):
        x = mm.group(1)
        prefijo = ""
        destino = ctx
        if x.startswith("PREV:"):
            x = x[5:]
            destino = ctx_prev or ctx
            prefijo = f"'{nombre_prev}'!" if nombre_prev else ""
        if x.startswith("HOJA:"):
            hoja, ref = x[5:].rsplit("!", 1)
            return f"'{hoja}'!{ref}"
        if x.startswith(("caja.", "tot.")):
            return prefijo + (destino.rol_a_celda.get(x) or x)
        mm2 = re.match(r"^(\w+)@(-?\d+)$", x)
        if mm2:
            col = destino.rol_a_col.get(mm2.group(1), "?")
            return f"{prefijo}{col}{fila + int(mm2.group(2))}"
        mm2 = re.match(r"^(\w+)#(\d+)$", x)
        if mm2:
            return f"{prefijo}{destino.rol_a_col.get(mm2.group(1), '?')}{mm2.group(2)}"
        mm2 = re.match(r"^(\w+)\[(\d+):(\d+)\]$", x)
        if mm2:
            col = destino.rol_a_col.get(mm2.group(1), "?")
            return f"{prefijo}{col}{mm2.group(2)}:{col}{mm2.group(3)}"
        return prefijo + x

    return PLACEHOLDER_RE.sub(sub, forma_txt)


def rango_suma(formula):
    """=SUM(H7:H167) -> (7, 167). None si no es una suma simple de un rango."""
    if not isinstance(formula, str):
        return None
    m = re.match(r"^=\s*SUMA?\(\s*\$?[A-Z]{1,3}\$?(\d+)\s*:\s*\$?[A-Z]{1,3}\$?(\d+)\s*\)\s*$",
                 formula, re.IGNORECASE)
    return (int(m.group(1)), int(m.group(2))) if m else None
