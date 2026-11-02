# -*- coding: utf-8 -*-
"""
Reglas de nivel 1 (solo el Excel). Cada regla recibe un ContextoRegla y
devuelve una lista de Hallazgo. Ninguna regla sabe de letras de columna: usan
DiaPunto y, para citar evidencia, DiaPunto.celdas.

Convención de montos: `monto` es la parte del descuadre que el hallazgo
explicaría, con el mismo signo del descuadre (negativo = falta plata).
"""
import itertools
import re
from dataclasses import dataclass
from typing import Optional

from .modelo import DiaPunto, Hallazgo, Evidencia
from .formulas import (Contexto, forma, renderizar, sin_desplazamientos, desplazamientos,
                       rango_suma, equivalentes)
from .plantilla import MANUALES_DIA_1, ROLES_PRODUCTO
from .texto import norm, pesos

NOMBRE_ROL = {
    "inv_inicial": "INV. INICIAL", "entradas": "ENTRADAS", "inv_final": "INV. FINAL",
    "salidas_siigo": "SALIDAS SIIGO", "salidas_tot": "SALIDAS TOTALES",
    "valor": "VALOR VENTA", "regalos_cant": "REGALOS ENTREGADOS",
    "regalos_valor": "TOTAL REGALOS", "descuento": "DESCUENTOS",
    "efectivo_cant": "CANTIDAD (efectivo)", "efectivo_desc_unit": "DESCUENTO (efectivo)",
    "efectivo_total": "TOTAL (efectivo apartado)",
    "pago_transferencias": "Transferencias", "pago_debito": "Tarjeta Débito",
    "pago_credito": "Tarjeta Crédito",
    "caja.efectivo_contado": "Efectivo", "caja.venta_efectivo": "Venta en efectivo del día",
    "caja.addi": "ADDI", "caja.consignacion": "Consignación", "caja.tarjetas": "Tarjetas",
    "caja.transferencias": "Transferencias", "caja.gastos": "Gastos",
    "caja.descuentos": "Descuentos", "caja.descuentos_idunn": "Descuentos Idunn",
    "caja.regalos": "Regalos", "caja.regalos_idunn": "Regalos Idunn",
    "caja.danados": "Dañados", "caja.devoluciones": "Devoluciones", "caja.cambios": "Cambios",
    "caja.efectivo_apartado": "Efectivo apartado", "caja.base": "Base",
    "caja.sencillo_recibido": "Sencillo recibido", "caja.total": "TOTAL",
    "caja.descuadre": "Descuadre", "caja.cantidad_facturas": "Cantidad facturas",
    "tot.valor": "VENTA DEL DIA (valor teórico)", "tot.regalos_valor": "total TOTAL REGALOS",
    "tot.descuento": "total DESCUENTOS", "tot.efectivo_total": "total efectivo apartado",
    "tot.pago_transferencias": "total Transferencias", "tot.pago_debito": "total Tarjeta Débito",
    "tot.pago_credito": "total Tarjeta Crédito",
}


@dataclass
class ContextoRegla:
    dia: DiaPunto
    anterior: Optional[DiaPunto]
    siguiente: Optional[DiaPunto]
    desc_fact: list
    plantilla: dict
    config: dict
    es_primer_dia: bool
    punto: str
    anterior2: Optional[DiaPunto] = None   # el día antes del anterior (para R01)
    # Fuentes externas opcionales (nivel 2 y 3). None = no se cargaron.
    siigo: object = None    # cierre.siigo.UnidadesSiigo del punto y día
    mapeo: object = None    # cierre.siigo.Mapeo
    siigo_archivo: str = ""
    siigo_dias: dict = None  # fecha -> ReporteSiigo (para R21 y los días vecinos)
    banco: object = None    # cierre.banco.DatosBanco (todo lo cargado, todos los puntos)
    tarjetas: object = None  # cierre.tarjetas.DatosTarjetas (Bold/Redeban)

    @property
    def descuadre(self):
        return self.dia.caja.descuadre or 0.0


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------
def _ev(dia, rol_o_celda, nota=""):
    celda = dia.celdas.get(rol_o_celda, rol_o_celda)
    if not isinstance(celda, str):
        celda = str(celda)
    return Evidencia(hoja=dia.hoja, celda=celda, valor=dia.valores.get(celda),
                     formula=dia.formulas.get(celda, ""), nota=nota)


def _h(cx, regla, tipo, severidad, texto, monto=0.0, evidencia=None):
    return Hallazgo(punto=cx.punto, fecha=cx.dia.fecha_hoja, regla=regla, tipo=tipo,
                    severidad=severidad, texto=texto, monto=round(monto, 2),
                    evidencia=evidencia or [])


def _rangos(filas):
    filas = sorted(set(filas))
    out, ini, prev = [], None, None
    for f in filas:
        if ini is None:
            ini = prev = f
        elif f == prev + 1:
            prev = f
        else:
            out.append((ini, prev))
            ini = prev = f
    if ini is not None:
        out.append((ini, prev))
    return ", ".join(f"{a}" if a == b else f"{a}–{b}" for a, b in out)


def _mismo_signo(a, b):
    return (a > 0 and b > 0) or (a < 0 and b < 0)


STOP = {"de", "la", "el", "los", "las", "con", "sin", "x", "y", "en", "del", "para",
        "por", "a", "al", "se", "le", "un", "una"}


def _raiz(w):
    if len(w) > 5 and w.endswith("es") and w[-3] in "lrndz":
        return w[:-2]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def _tokens(texto):
    return [_raiz(t) for t in norm(texto).split() if t not in STOP]


def productos_mencionados(texto, productos):
    """Productos cuyo nombre aparece completo en el texto (plurales y
    abreviaturas como 'perf.' incluidos). Devuelve [(producto, cantidad|None)]."""
    tk = _tokens(texto)
    if not tk:
        return []
    encontrados = []
    for p in productos:
        nombre_tk = _tokens(p.nombre)
        if not nombre_tk:
            continue

        def esta(t):
            return any(x == t or (len(x) >= 4 and t.startswith(x)) or
                       (len(t) >= 4 and x.startswith(t)) for x in tk)

        if all(esta(t) for t in nombre_tk):
            cantidad = None
            m = re.search(r"(\d+)\s+(?:\w+\s+){0,1}" + re.escape(norm(p.nombre).split()[0][:4]),
                          norm(texto))
            if m:
                cantidad = int(m.group(1))
            encontrados.append((p, cantidad))
    # Si "Shampoo Cebolla" y "Shampoo Mini Cebolla" coinciden, gana el más largo.
    encontrados.sort(key=lambda pc: -len(_tokens(pc[0].nombre)))
    finales = []
    for p, c in encontrados:
        if not any(set(_tokens(p.nombre)) < set(_tokens(q.nombre)) for q, _ in finales):
            finales.append((p, c))
    return finales


def _tiene_palabra(texto, palabras):
    t = " " + norm(texto) + " "
    return any(norm(pal) in t if not pal.endswith(" ") else (" " + norm(pal) + " ") in t
               for pal in palabras)


# ---------------------------------------------------------------------------
# R01 Integridad de fórmulas
# ---------------------------------------------------------------------------
ROLES_DINERO = {"salidas_tot", "valor", "efectivo_total"}


def _desvios(dia, prev, plantilla, es_primer_dia):
    """Celdas de un día cuya fórmula no coincide con la plantilla.
    prod: {(rol, nombre_norm): (producto, tipo, extra)}; caja: {rol: forma}."""
    ctx = Contexto(dia)
    ctxp = Contexto(prev) if prev else None
    nprev = prev.hoja if prev else None
    prev_por_fila = {q.fila: q for q in prev.productos} if prev else {}
    prod, caja = {}, {}
    for p in dia.productos:
        for rol, canon in plantilla["producto"].items():
            if es_primer_dia and rol in MANUALES_DIA_1:
                continue
            if "PREV:" in canon and prev is None:
                continue
            col = ctx.rol_a_col.get(rol)
            if not col:
                continue
            celda = f"{col}{p.fila}"
            fo = forma(dia.formulas.get(celda), celda, ctx, ctxp, nprev)
            if equivalentes(fo, canon):
                continue
            if fo is None:
                tipo = "a_mano" if dia.valores.get(celda) not in (None, "") else "faltante"
                extra = ""
            elif "{HOJA:" in fo:
                tipo, extra = "otra_hoja", re.search(r"\{HOJA:([^!]+)!", fo).group(1)
            elif sin_desplazamientos(fo) == sin_desplazamientos(canon):
                desp = sorted({x for x in desplazamientos(fo) if x != 0})
                if "PREV:" in fo and len(desp) == 1:
                    # Se insertó una fila: la referencia se corrió, pero si apunta
                    # al MISMO producto del día anterior está bien.
                    q = prev_por_fila.get(p.fila + desp[0])
                    if q is not None and norm(q.nombre) == norm(p.nombre):
                        continue
                tipo, extra = "corrida", (desp[0] if desp else 0)
            else:
                tipo, extra = "distinta", ""
            prod[(rol, norm(p.nombre))] = (p, tipo, extra)
    for rol, canon in plantilla["caja"].items():
        if es_primer_dia and rol in MANUALES_DIA_1:
            continue
        if "PREV:" in canon and prev is None:
            continue
        celda = ctx.rol_a_celda.get(rol)
        if not celda:
            continue
        fo = forma(dia.formulas.get(celda), celda, ctx, ctxp, nprev)
        if not equivalentes(fo, canon):
            caja[rol] = fo
    return prod, caja


def _describir(rol, tipo, extra, ctx, nprev):
    nom = f"{NOMBRE_ROL.get(rol, rol)} ({ctx.rol_a_col.get(rol, '?')})"
    if tipo == "faltante":
        return f"{nom} está vacía (sin fórmula)"
    if tipo == "a_mano":
        return f"{nom} tiene un valor escrito a mano"
    if tipo == "otra_hoja":
        return f"{nom} toma datos de la hoja '{extra}' en vez del día anterior ('{nprev}')"
    if tipo == "corrida":
        return f"{nom} toma una celda {abs(extra)} fila(s) más {'abajo' if extra > 0 else 'arriba'}"
    return f"{nom} tiene una fórmula distinta a la plantilla"


def _impacto(prods):
    """Parte del descuadre que cambiaría con las fórmulas de plantilla en G/H/N."""
    monto = 0.0
    for p in prods:
        h_esp = p.precio * (p.salidas_siigo + p.efectivo_cant)
        n_esp = p.efectivo_cant * (p.precio - p.efectivo_desc_unit)
        monto += (p.efectivo_total - n_esp) - (p.valor - h_esp)
    return monto


def _agrupar(prod):
    """{(rol, nombre): (p, tipo, extra)} -> [(firma, [productos])] por fila."""
    por_fila = {}
    for (rol, _), (p, tipo, extra) in prod.items():
        por_fila.setdefault(p.fila, (p, []))[1].append((rol, tipo, extra))
    orden = {r: i for i, r in enumerate(ROLES_PRODUCTO)}
    grupos = {}
    for p, firma in por_fila.values():
        grupos.setdefault(tuple(sorted(firma, key=lambda x: orden.get(x[0], 99))), []).append(p)
    return [(firma, sorted(ps, key=lambda p: p.fila)) for firma, ps in grupos.items()]


def _quien(prods):
    return (f"{prods[0].nombre} (fila {prods[0].fila})" if len(prods) == 1
            else f"filas {_rangos([p.fila for p in prods])} ({len(prods)} productos)")


def r01(cx):
    d, prev = cx.dia, cx.anterior
    ctx = Contexto(d)
    ctxp = Contexto(prev) if prev else None
    nprev = prev.hoja if prev else None
    pl = cx.plantilla
    prod, caja = _desvios(d, prev, pl, cx.es_primer_dia)
    if prev is not None:
        prod_ant, caja_ant = _desvios(prev, cx.anterior2, pl, prev.fecha_hoja and prev.fecha_hoja.day == 1)
    else:
        prod_ant, caja_ant = {}, {}

    # Lo que ya estaba igual de mal ayer no es un error de HOY: se junta en un
    # solo aviso para que no tape lo nuevo.
    arr_prod = {k: v for k, v in prod.items() if k in prod_ant and prod_ant[k][1:] == v[1:]}
    nue_prod = {k: v for k, v in prod.items() if k not in arr_prod}
    arr_caja = {r: f for r, f in caja.items() if r in caja_ant and equivalentes(caja_ant[r], f)}
    nue_caja = {r: f for r, f in caja.items() if r not in arr_caja}

    out = []
    for firma, prods in _agrupar(nue_prod):
        partes = [_describir(rol, tipo, extra, ctx, nprev) for rol, tipo, extra in firma]
        dinero = {r for r, _, _ in firma} & ROLES_DINERO
        monto = _impacto(prods) if dinero else 0.0
        texto = f"Fórmulas fuera de plantilla en {_quien(prods)}: " + "; ".join(partes) + "."
        if dinero:
            texto += (f" Con la fórmula correcta el descuadre cambiaría en {pesos(-monto)}."
                      if abs(monto) >= 1 else " Hoy no cambia el descuadre, pero hay que corregirla.")
        ev = []
        for p in prods[:4]:
            for rol, _, _ in firma:
                col = ctx.rol_a_col.get(rol)
                if col:
                    celda = f"{col}{p.fila}"
                    esperada = renderizar(pl["producto"][rol], celda, ctx, ctxp, nprev)
                    ev.append(_ev(d, celda, f"{p.nombre}. Esperada: {esperada}"))
        hay_monto = abs(monto) >= 1
        out.append(_h(cx, "R01", "causa" if hay_monto else "integridad", "alta" if hay_monto else "media",
                      texto, monto if _mismo_signo(monto, cx.descuadre) else 0.0, ev))

    for rol, fo in nue_caja.items():
        celda = ctx.rol_a_celda[rol]
        canon = pl["caja"][rol]
        esperada = renderizar(canon, celda, ctx, ctxp, nprev)
        nom = f"{NOMBRE_ROL.get(rol, rol)} ({celda})"
        if fo is None:
            texto = f"{nom} no tiene fórmula (debería ser {esperada})."
        else:
            texto = (f"{nom} tiene una fórmula distinta a la plantilla. Esperada: {esperada} · "
                     f"Encontrada: {d.formulas.get(celda)}.")
        if rol == "caja.base" and "{caja.sencillo_recibido}" in canon and \
                "{caja.sencillo_recibido}" not in (fo or ""):
            s = d.caja.sencillo_recibido or 0
            texto += (" Le falta sumar el sencillo recibido; hoy no afecta porque no hubo sencillo."
                      if not s else f" Le falta sumar el sencillo recibido ({pesos(s)}).")
        out.append(_h(cx, "R01", "integridad", "media", texto, 0.0,
                      [_ev(d, celda, f"Esperada: {esperada}")]))

    if arr_prod or arr_caja:
        partes, ev, prods_dinero = [], [], []
        for firma, prods in _agrupar(arr_prod):
            partes.append(f"{_quien(prods)}: " +
                          "; ".join(_describir(r, t, e, ctx, nprev) for r, t, e in firma))
            if {r for r, _, _ in firma} & ROLES_DINERO:
                prods_dinero += prods
            col = ctx.rol_a_col.get(firma[0][0])
            if col:
                ev.append(_ev(d, f"{col}{prods[0].fila}", prods[0].nombre))
        for rol in arr_caja:
            celda = ctx.rol_a_celda[rol]
            partes.append(f"{NOMBRE_ROL.get(rol, rol)} ({celda}) con fórmula distinta a la plantilla")
            ev.append(_ev(d, celda, "Esperada: " + renderizar(pl["caja"][rol], celda, ctx, ctxp, nprev)))
        monto = _impacto(prods_dinero)
        texto = ("Siguen sin corregir errores de fórmula que ya venían del día anterior: "
                 + " · ".join(partes) + ".")
        if abs(monto) >= 1:
            texto += f" Hoy mueven el descuadre en {pesos(monto)}."
        out.append(_h(cx, "R01", "causa" if abs(monto) >= 1 else "integridad", "baja", texto,
                      monto if _mismo_signo(monto, cx.descuadre) else 0.0, ev))
    return out


# ---------------------------------------------------------------------------
# R02 Continuidad
# ---------------------------------------------------------------------------
def r02(cx):
    d, prev = cx.dia, cx.anterior
    out = []
    if d.fecha and d.fecha_hoja and d.fecha != d.fecha_hoja:
        out.append(_h(cx, "R02", "integridad", "media",
                      f"La hoja '{d.hoja}' dice fecha {d.fecha:%d/%m/%Y}, pero corresponde al "
                      f"{d.fecha_hoja:%d/%m/%Y}. Puede ser una hoja copiada sin actualizar.",
                      0.0, [_ev(d, "fecha")]))
    if cx.es_primer_dia:
        out.append(_h(cx, "R02", "integridad", "info",
                      "Primer día del mes: la base y el inventario inicial se escriben a mano. "
                      "Revisar contra el cierre del mes anterior.",
                      0.0, [_ev(d, "caja.base"), _ev(d, f"{d.celdas.get('col.inv_inicial', 'C')}"
                                                         f"{d.productos[0].fila if d.productos else 8}")]))
        return out
    if prev is None:
        return out

    finales = {}
    for p in prev.productos:
        finales.setdefault(norm(p.nombre), p)
    distintos = []
    for p in d.productos:
        q = finales.get(norm(p.nombre))
        if q is not None and abs(p.inv_inicial - q.inv_final) > 1e-6:
            distintos.append((p, q))
    if distintos:
        col_c = d.celdas.get("col.inv_inicial", "C")
        col_e = prev.celdas.get("col.inv_final", "E")
        lista = ", ".join(f"{p.nombre} ({q.inv_final:g} → {p.inv_inicial:g})" for p, q in distintos[:6])
        mas = f" y {len(distintos) - 6} más" if len(distintos) > 6 else ""
        out.append(_h(cx, "R02", "integridad", "media",
                      f"{len(distintos)} producto(s) arrancan con un inventario distinto al que cerró "
                      f"el día anterior: {lista}{mas}.", 0.0,
                      [_ev(d, f"{col_c}{p.fila}", f"{p.nombre}: el día anterior cerró en {q.inv_final:g} "
                                                  f"('{prev.hoja}'!{col_e}{q.fila})")
                       for p, q in distintos[:8]]))

    if d.caja.base is not None and prev.caja.efectivo_contado is not None:
        esperado = (prev.caja.efectivo_contado or 0) + (d.caja.sencillo_recibido or 0)
        real = d.caja.base or 0
        if abs(real - esperado) > 1:
            monto = esperado - real
            out.append(_h(cx, "R02", "causa", "alta",
                          f"La base ({pesos(real)}) no es el efectivo contado del día anterior "
                          f"({pesos(prev.caja.efectivo_contado)}) más el sencillo recibido "
                          f"({pesos(d.caja.sencillo_recibido or 0)}). Eso mueve el descuadre en {pesos(monto)}.",
                          monto if _mismo_signo(monto, cx.descuadre) else 0.0,
                          [_ev(d, "caja.base"), _ev(d, "caja.sencillo_recibido"),
                           Evidencia(prev.hoja, prev.celdas.get("caja.efectivo_contado", ""),
                                     prev.caja.efectivo_contado, "", "Efectivo contado del día anterior")]))
    return out


# ---------------------------------------------------------------------------
# R03 Compensación entre días seguidos
# ---------------------------------------------------------------------------
def r03(cx):
    cfg = cx.config["R03_compensacion"]
    x = cx.descuadre
    if abs(x) < cfg["monto_minimo"]:
        return []
    out = []
    for vecino, cual in ((cx.anterior, "anterior"), (cx.siguiente, "siguiente")):
        if vecino is None or vecino.caja.descuadre is None:
            continue
        y = vecino.caja.descuadre
        if abs(y) < cfg["monto_minimo"] or _mismo_signo(x, y):
            continue
        dif = abs(x + y)
        if dif <= max(cfg["tolerancia_abs"], cfg["tolerancia_pct"] * max(abs(x), abs(y))):
            explicado = min(abs(x), abs(y)) * (1 if x > 0 else -1)
            out.append(_h(cx, "R03", "causa", "media",
                          f"Se compensa con el día {cual} ({vecino.fecha_hoja:%d/%m}): ese día quedó "
                          f"{pesos(y)} y hoy {pesos(x)} (quedan {pesos(x + y)} sin compensar). Típico de un "
                          f"error de conteo o de base que se arrastra de un día al otro.",
                          explicado,
                          [_ev(cx.dia, "caja.descuadre"),
                           Evidencia(vecino.hoja, vecino.celdas.get("caja.descuadre", ""), y, "",
                                     f"Descuadre del día {cual}")]))
    return out


# ---------------------------------------------------------------------------
# R04 Billete
# ---------------------------------------------------------------------------
def r04(cx):
    cfg = cx.config["R04_billete"]
    x = cx.descuadre
    if abs(x) < min(cfg["denominaciones"]):
        return []
    for den in sorted(cfg["denominaciones"], reverse=True):
        k = round(abs(x) / den)
        if 1 <= k <= cfg["max_billetes"] and abs(abs(x) - k * den) <= cfg["tolerancia"]:
            que = "sobra" if x > 0 else "falta"
            billetes = f"un billete de {pesos(den)}" if k == 1 else f"{k} billetes de {pesos(den)}"
            return [_h(cx, "R04", "causa", "baja",
                       f"El descuadre es exactamente {billetes} ({que} plata): posible error al contar "
                       f"el efectivo o un billete que quedó fuera/dentro de la caja.",
                       x, [_ev(cx.dia, "caja.descuadre"), _ev(cx.dia, "caja.efectivo_contado")])]
    return []


# ---------------------------------------------------------------------------
# R05 Combinación de precios
# ---------------------------------------------------------------------------
def r05(cx):
    cfg = cx.config["R05_precios"]
    x = cx.descuadre
    objetivo = abs(x)
    if objetivo < cfg["monto_minimo"]:
        return []
    por_precio = {}
    for p in cx.dia.productos:
        if p.precio > 0:
            por_precio.setdefault(round(p.precio), []).append(p)
    precios = sorted(por_precio)
    tol = cfg["tolerancia"]
    combos = []
    conjunto = set(precios)
    for n in range(1, cfg["max_productos"] + 1):
        for combo in itertools.combinations_with_replacement(precios, n - 1):
            resto = objetivo - sum(combo)
            if combo and resto < combo[-1] - tol:
                continue
            candidatos = [resto] if tol == 0 else [q for q in precios if abs(q - resto) <= tol]
            for q in candidatos:
                if q in conjunto and (not combo or q >= combo[-1]):
                    combos.append(tuple(combo) + (q,))
        if combos:
            break   # preferir la explicación con menos productos
    if not combos:
        return []

    def movimiento(precio):
        return sum(1 for p in por_precio[precio] if p.salidas_tot or p.efectivo_cant)

    combos.sort(key=lambda c: -sum(movimiento(q) for q in c))
    mostrar = combos[:cfg["max_combinaciones_mostradas"]]

    def describir(combo):
        partes = []
        for q in combo:
            ps = sorted(por_precio[q], key=lambda p: -(p.salidas_tot + p.efectivo_cant))
            nombres = ", ".join(p.nombre for p in ps[:2]) + (f" u otro de {pesos(q)}" if len(ps) > 2 else "")
            partes.append(f"{nombres} ({pesos(q)})")
        return " + ".join(partes)

    alternativas = " · o bien: ".join(describir(c) for c in mostrar)
    if x > 0:
        sentido = ("Sobra justo lo que valen estos productos: posible venta en efectivo que no se "
                   "anotó (efectivo apartado sin registrar).")
    else:
        sentido = ("Falta justo lo que valen estos productos: posibles unidades facturadas/entregadas "
                   "que no se cobraron, o un regalo que no se anotó.")
    extra = f" Hay {len(combos)} combinaciones posibles." if len(combos) > len(mostrar) else ""
    return [_h(cx, "R05", "causa", "baja", f"{sentido} {alternativas}.{extra}", x,
               [_ev(cx.dia, "caja.descuadre")] +
               [_ev(cx.dia, f"{cx.dia.celdas.get('col.precio', 'B')}{por_precio[q][0].fila}",
                    por_precio[q][0].nombre) for q in sorted(set(mostrar[0]))])]


# ---------------------------------------------------------------------------
# R06 Regalos
# ---------------------------------------------------------------------------
def r06(cx):
    malos = [p for p in cx.dia.productos if p.regalos_cant > p.salidas_siigo + 1e-6]
    if not malos:
        return []
    col_i = cx.dia.celdas.get("col.regalos_cant", "I")
    col_f = cx.dia.celdas.get("col.salidas_siigo", "F")
    lista = ", ".join(f"{p.nombre} ({p.regalos_cant:g} regalados, {p.salidas_siigo:g} facturados)"
                      for p in malos[:5])
    return [_h(cx, "R06", "señal", "media",
               f"Regalos entregados mayores que las salidas facturadas en Siigo (los regalos se "
               f"facturan a $1, así que deberían estar incluidos en F): {lista}.", 0.0,
               [_ev(cx.dia, f"{col_i}{p.fila}", f"{p.nombre}; salidas Siigo en {col_f}{p.fila}")
                for p in malos[:6]])]


# ---------------------------------------------------------------------------
# R07 Observaciones vs. valores de ajustes
# ---------------------------------------------------------------------------
AJUSTES = ("caja.danados", "caja.devoluciones", "caja.cambios")


def _valores_ajustes(d):
    return {rol: getattr(d.caja, rol.split(".")[1]) or 0 for rol in AJUSTES}


def _estimar_ajuste(texto, productos):
    m = re.search(r"\$\s*([\d.,]+)", texto)
    if m:
        v = float(m.group(1).replace(".", "").replace(",", ""))
        if v > 0:
            return v
    for p, cantidad in productos_mencionados(texto, productos):
        if p.precio > 0:
            return p.precio * (cantidad or 1)
    return None


def r07(cx):
    d = cx.dia
    palabras = cx.config["R07_observaciones"]["palabras_ajuste"]
    obs_aj = [(c, t) for c, t in d.observaciones if _tiene_palabra(t, palabras)]
    vals = _valores_ajustes(d)
    con_valor = {r: v for r, v in vals.items() if v}
    out = []
    if obs_aj and not con_valor:
        est = sum(filter(None, (_estimar_ajuste(t, d.productos) for _, t in obs_aj)))
        monto = 0.0
        if est and cx.descuadre < 0:
            monto = max(cx.descuadre, -est)
        txt = ("Las observaciones hablan de productos dañados, devueltos, prestados o enviados a "
               "bodega, pero Dañados, Devoluciones y Cambios están vacíos.")
        if est:
            txt += f" Por lo que dicen, el valor sería de unos {pesos(est)}."
        out.append(_h(cx, "R07", "causa" if monto else "señal", "media", txt, monto,
                      [Evidencia(d.hoja, c, t, "", "Observación") for c, t in obs_aj[:4]] +
                      [_ev(d, r, "vacío") for r in AJUSTES]))
    if con_valor and not obs_aj:
        lista = ", ".join(f"{NOMBRE_ROL[r]} {pesos(v)}" for r, v in con_valor.items())
        out.append(_h(cx, "R07", "señal", "media",
                      f"Hay valores de ajustes ({lista}) pero ninguna observación dice qué producto "
                      f"salió ni por qué.", 0.0,
                      [_ev(d, r) for r in con_valor] +
                      [Evidencia(d.hoja, c, t, "", "Observación") for c, t in d.observaciones[:3]]))
    return out


# ---------------------------------------------------------------------------
# R08 Valores de ajustes vs. precios de los productos mencionados
# ---------------------------------------------------------------------------
def r08(cx):
    d = cx.dia
    palabras = cx.config["R07_observaciones"]["palabras_ajuste"]
    textos = [t for _, t in d.observaciones if _tiene_palabra(t, palabras)]
    mencionados = {}
    for t in textos:
        for p, _ in productos_mencionados(t, d.productos):
            mencionados[p.fila] = p
    precios = sorted({p.precio for p in mencionados.values() if p.precio > 0})
    if not precios:
        return []
    out = []
    for rol, v in _valores_ajustes(d).items():
        if not v:
            continue
        if any(abs(v / q - round(v / q)) < 1e-6 for q in precios):
            continue
        nombres = ", ".join(f"{p.nombre} ({pesos(p.precio)})" for p in mencionados.values())
        out.append(_h(cx, "R08", "señal", "media",
                      f"{NOMBRE_ROL[rol]} por {pesos(v)} no corresponde a un número exacto de unidades "
                      f"de lo que dicen las observaciones: {nombres}.", 0.0,
                      [_ev(d, rol)] + [Evidencia(d.hoja, c, t, "", "Observación")
                                       for c, t in d.observaciones if t in textos][:3]))
    return out


# ---------------------------------------------------------------------------
# R09 Descuentos
# ---------------------------------------------------------------------------
def r09(cx):
    d = cx.dia
    out = []
    total_k = sum(p.descuento for p in d.productos)
    palabras = cx.config["R09_descuentos"]["palabras_descuento"]
    if total_k > 0 and not any(_tiene_palabra(t, palabras) for _, t in d.observaciones):
        col = d.celdas.get("col.descuento", "K")
        out.append(_h(cx, "R09", "señal", "media",
                      f"Hay descuentos por {pesos(total_k)} sin ninguna observación que diga a qué "
                      f"factura o promoción corresponden.", 0.0,
                      [_ev(d, "tot.descuento")] +
                      [_ev(d, f"{col}{p.fila}", p.nombre) for p in d.productos if p.descuento][:5]))
    con_m = [p for p in d.productos if p.efectivo_cant and p.efectivo_desc_unit]
    if con_m:
        impacto = -sum(p.efectivo_cant * p.efectivo_desc_unit for p in con_m)
        col = d.celdas.get("col.efectivo_desc_unit", "M")
        out.append(_h(cx, "R09", "causa", "alta",
                      f"Se usó el descuento por unidad del bloque de efectivo ({len(con_m)} producto(s)). "
                      f"La plantilla no lo suma a caja como descuento, así que genera un descuadre de "
                      f"{pesos(impacto)}. Debe anotarse en la columna DESCUENTOS.",
                      impacto if _mismo_signo(impacto, cx.descuadre) else 0.0,
                      [_ev(d, f"{col}{p.fila}", f"{p.nombre}: {p.efectivo_cant:g} × {pesos(p.efectivo_desc_unit)}")
                       for p in con_m[:6]]))
    return out


# ---------------------------------------------------------------------------
# R10 Errores conocidos de plantilla
# ---------------------------------------------------------------------------
def r10(cx):
    d = cx.dia
    ctx = Contexto(d)
    out = []

    # (a) Doble conteo Idunn: el principal suma TODO el total y el Idunn vuelve a
    # sumar un pedazo de ese mismo rango.
    for principal, idunn, total in (("caja.regalos", "caja.regalos_idunn", "tot.regalos_valor"),
                                    ("caja.descuentos", "caja.descuentos_idunn", "tot.descuento")):
        cp, ci, ct = (ctx.rol_a_celda.get(r) for r in (principal, idunn, total))
        if not (cp and ci and ct):
            continue
        fp = forma(d.formulas.get(cp), cp, ctx)
        fi = forma(d.formulas.get(ci), ci, ctx)
        rt = rango_suma(d.formulas.get(ct))
        mi = re.match(r"^=SUMA?\(\{\w+\[(\d+):(\d+)\]\}\)$", fi or "")
        if fp == "={" + total + "}" and mi and rt and rt[0] <= int(mi.group(1)) and int(mi.group(2)) <= rt[1]:
            v = getattr(d.caja, idunn.split(".")[1]) or 0
            base_txt = (f"Error de plantilla: {NOMBRE_ROL[principal]} ({cp}: {d.formulas.get(cp)}) ya incluye "
                        f"las filas {mi.group(1)}–{mi.group(2)}, y {NOMBRE_ROL[idunn]} ({ci}) las vuelve a sumar.")
            if v:
                out.append(_h(cx, "R10", "causa", "alta",
                              base_txt + f" Hoy eso infla la caja en {pesos(v)}.",
                              v if _mismo_signo(v, cx.descuadre) else 0.0, [_ev(d, cp), _ev(d, ci)]))
            else:
                out.append(_h(cx, "R10", "integridad", "info",
                              base_txt + " Hoy no afecta porque ese valor es 0; el día que haya "
                                         "movimiento Idunn el descuadre saldrá inflado en ese valor.",
                              0.0, [_ev(d, cp), _ev(d, ci)]))

    # (b) Filas con datos fuera del rango de las sumas de totales.
    signo = {"valor": 1, "efectivo_total": -1, "regalos_valor": -1, "descuento": -1,
             "pago_transferencias": -1, "pago_debito": -1, "pago_credito": -1}
    filas_datos = {p.fila: p for p in d.productos}
    pagos = {"pago_transferencias": d.pagos.transferencias, "pago_debito": d.pagos.debito,
             "pago_credito": d.pagos.credito}
    for rol, s in signo.items():
        celda_tot = ctx.rol_a_celda.get(f"tot.{rol}")
        rango = rango_suma(d.formulas.get(celda_tot)) if celda_tot else None
        if not rango:
            continue
        lo, hi = rango
        if rol in pagos:
            fuera = [(f, v) for f, v in pagos[rol] if not lo <= f <= hi]
        else:
            fuera = [(p.fila, getattr(p, rol)) for p in filas_datos.values()
                     if not lo <= p.fila <= hi and getattr(p, rol)]
        if not fuera:
            continue
        suma = sum(v for _, v in fuera)
        monto = s * suma
        col = ctx.rol_a_col.get(rol, "?")
        out.append(_h(cx, "R10", "causa", "alta",
                      f"La suma {celda_tot} ({d.formulas.get(celda_tot)}) no incluye las filas "
                      f"{_rangos([f for f, _ in fuera])} de {NOMBRE_ROL[rol]}, que suman {pesos(suma)}. "
                      f"Eso mueve el descuadre en {pesos(monto)}.",
                      monto if _mismo_signo(monto, cx.descuadre) else 0.0,
                      [_ev(d, celda_tot)] + [_ev(d, f"{col}{f}") for f, _ in fuera[:5]]))
    return out


# ---------------------------------------------------------------------------
# R11 DESC FACT
# ---------------------------------------------------------------------------
HOJA_EN_FORMULA = re.compile(r"(?:'([^']+)'|([A-Za-z0-9_]+))!")


def r11(cx):
    d = cx.dia
    dia_n = d.fecha_hoja.day if d.fecha_hoja else None
    fila = next((f for f in cx.desc_fact if f.dia == dia_n), None)
    hoja_df = "DESC  FACT"
    if fila is None:
        return [_h(cx, "R11", "integridad", "baja",
                   f"DESC FACT no tiene la fila del día {dia_n}.", 0.0)]
    out = []
    malas = []
    for rol, (celda, f) in fila.formulas.items():
        hojas = {a or b for a, b in HOJA_EN_FORMULA.findall(f)}
        otras = [h for h in hojas if h != d.hoja]
        if otras:
            malas.append((rol, celda, f, otras))
    if malas:
        nombres = {"asesor": "ASESOR", "descuadre": "VR DESCUADRE", "venta": "VENTA DIA",
                   "facturas": "FACTURAS", "efectivo_sin_facturar": "EFECTIVO SIN FACTURAR",
                   "saldo": "SALDO", "entregado": "DINERO ENTREGADO"}
        hojas_txt = ", ".join(sorted({f"'{h}'" for _, _, _, hs in malas for h in hs}))
        cols = ", ".join(nombres.get(r, r) for r, _, _, _ in malas)
        ev = []
        for rol, celda, f, _ in malas:
            nota = "Debería leer la hoja '" + d.hoja + "'"
            if rol == "venta":
                nota += f" (ahí la venta es {pesos(d.caja.valor_teorico)}, aquí dice {pesos(fila.venta)})"
            ev.append(Evidencia(hoja_df, celda, getattr(fila, rol, None), f, nota))
        out.append(_h(cx, "R11", "integridad", "media",
                      f"En DESC FACT la fila del día {dia_n} lee {cols} de {hojas_txt} en vez de la "
                      f"hoja '{d.hoja}'. El resumen del mes queda con datos de otra hoja.", 0.0, ev))
    if not fila.facturas:
        out.append(_h(cx, "R11", "señal", "baja",
                      f"Falta la cantidad de facturas del día (DESC FACT y la hoja '{d.hoja}').", 0.0,
                      [_ev(d, "caja.cantidad_facturas")]))

    cfg = cx.config["R11_desc_fact"]
    previas = sorted((f for f in cx.desc_fact if f.dia is not None and f.dia <= dia_n), key=lambda f: f.dia)
    racha, anterior = 0, None
    for f in previas:
        if (f.entregado or 0) == 0 and f.saldo is not None and anterior is not None and f.saldo > anterior:
            racha += 1
        elif (f.entregado or 0) != 0:
            racha = 0
        anterior = f.saldo if f.saldo is not None else anterior
    if fila.saldo and fila.saldo >= cfg["saldo_minimo"] and racha >= cfg["dias_sin_entrega"]:
        out.append(_h(cx, "R11", "señal", "media",
                      f"El efectivo sin facturar acumulado va en {pesos(fila.saldo)} y lleva {racha} días "
                      f"creciendo sin entregas anotadas en DINERO ENTREGADO. Revisar que las entregas "
                      f"(p. ej. 'efectivo jefe') se estén registrando.", 0.0,
                      [Evidencia(hoja_df, fila.formulas.get("saldo", ("", ""))[0], fila.saldo, "",
                                 "SALDO")]))
    return out


REGLAS = [r01, r02, r03, r04, r05, r06, r07, r08, r09, r10, r11]
