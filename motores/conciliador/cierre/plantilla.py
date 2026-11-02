# -*- coding: utf-8 -*-
"""
La "plantilla" se deduce del propio mes: para cada rol se toma la forma de
fórmula más común entre todas las hojas de día. Así no hay que escribir a mano
las fórmulas de cada punto (cada libro puede tener más o menos productos y
filas distintas), y un error aislado nunca se vuelve "la plantilla".
"""
from collections import Counter

from .formulas import Contexto, forma

ROLES_PRODUCTO = ["inv_inicial", "salidas_tot", "inv_final", "valor",
                  "regalos_valor", "efectivo_total"]

ROLES_CAJA = ["caja.efectivo_contado", "caja.venta_efectivo", "caja.tarjetas",
              "caja.transferencias", "caja.descuentos", "caja.descuentos_idunn",
              "caja.regalos", "caja.regalos_idunn", "caja.efectivo_apartado",
              "caja.base", "caja.total", "caja.descuadre",
              "tot.valor", "tot.regalos_valor", "tot.descuento", "tot.efectivo_total",
              "tot.pago_transferencias", "tot.pago_debito", "tot.pago_credito"]

# Roles que en el primer día del mes se escriben a mano por diseño.
MANUALES_DIA_1 = {"inv_inicial", "caja.base"}

VALOR = "<valor a mano>"
VACIO = "<vacía>"


def _forma_celda(dia, celda, ctx, ctx_prev, nombre_prev):
    f = dia.formulas.get(celda)
    if f is not None:
        return forma(f, celda, ctx, ctx_prev, nombre_prev)
    v = dia.valores.get(celda)
    return VACIO if v in (None, "") else VALOR


def construir(dias_ordenados):
    """dias_ordenados: lista de DiaPunto en orden de hoja. Devuelve
    {"producto": {rol: forma}, "caja": {rol: forma}} con solo los roles cuya
    forma mayoritaria es realmente una fórmula."""
    votos_p = {r: Counter() for r in ROLES_PRODUCTO}
    votos_c = {r: Counter() for r in ROLES_CAJA}
    for i, dia in enumerate(dias_ordenados):
        prev = dias_ordenados[i - 1] if i > 0 else None
        ctx = Contexto(dia)
        ctxp = Contexto(prev) if prev else None
        nprev = prev.hoja if prev else None
        for p in dia.productos:
            for rol in ROLES_PRODUCTO:
                if i == 0 and rol in MANUALES_DIA_1:
                    continue
                col = ctx.rol_a_col.get(rol)
                if col:
                    votos_p[rol][_forma_celda(dia, f"{col}{p.fila}", ctx, ctxp, nprev)] += 1
        for rol in ROLES_CAJA:
            if i == 0 and rol in MANUALES_DIA_1:
                continue
            celda = ctx.rol_a_celda.get(rol)
            if celda:
                votos_c[rol][_forma_celda(dia, celda, ctx, ctxp, nprev)] += 1

    def ganadoras(votos):
        out = {}
        for rol, c in votos.items():
            if not c:
                continue
            f, n = c.most_common(1)[0]
            if f not in (VALOR, VACIO):
                out[rol] = f
        return out

    return {"producto": ganadoras(votos_p), "caja": ganadoras(votos_c)}
