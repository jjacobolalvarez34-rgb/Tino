# -*- coding: utf-8 -*-
"""
Reglas de nivel 2 (con Siigo). Solo corren si se cargó el reporte de Siigo
del día revisado.

R20 Unidades: por producto, salidas Siigo (F) del Excel contra las unidades
facturadas en Siigo. Se descuentan las unidades de dañados/devoluciones/
préstamos que se lean en las observaciones (salen en F pero no se facturan).
Revisa también los días que cuadran: una venta facturada en Siigo que no está en
el Excel, y cuya plata tampoco está, deja el descuadre en 0.
"""
from .modelo import Evidencia
from .reglas_n1 import _h, _ev, _mismo_signo, _tiene_palabra, productos_mencionados
from .texto import norm, pesos


def _lista(items, n=8):
    txt = ", ".join(items[:n])
    return txt + (f" y {len(items) - n} más" if len(items) > n else "")


def r20(cx):
    if cx.siigo is None or cx.mapeo is None:
        return []
    d, m, u = cx.dia, cx.mapeo, cx.siigo
    tol = cx.config.get("siigo", {}).get("tolerancia_unidades", 0)

    excel = {}          # clave -> {"u": unidades F, "prods": [...]}
    sin_mapeo_excel = []
    for p in d.productos:
        clave = m.clave_excel(p.nombre)
        if clave is None:
            if p.salidas_siigo:
                sin_mapeo_excel.append(p)
            continue
        e = excel.setdefault(clave, {"u": 0.0, "prods": []})
        e["u"] += p.salidas_siigo
        e["prods"].append(p)

    # Dañados, devoluciones y préstamos salen en F pero no se facturan.
    palabras = cx.config["R07_observaciones"]["palabras_ajuste"]
    ajustes, notas_ajuste = {}, {}
    for celda, texto in d.observaciones:
        if not _tiene_palabra(texto, palabras):
            continue
        for p, cantidad in productos_mencionados(texto, d.productos):
            clave = m.clave_excel(p.nombre)
            if clave and cantidad:
                ajustes[clave] = ajustes.get(clave, 0) + cantidad
                notas_ajuste.setdefault(clave, []).append(f"{celda}: {texto}")

    a_eleccion = dict(u.a_eleccion)   # "Shampoo (a elección)" de los kits
    solo_siigo, solo_excel = [], []   # (clave, diferencia de unidades, precio, prods)
    for clave in sorted(set(excel) | set(u.por_clave)):
        ex = excel.get(clave, {"u": 0.0, "prods": []})
        unidades_excel = ex["u"] - ajustes.get(clave, 0)
        diff = unidades_excel - u.por_clave.get(clave, 0)
        if diff > tol and a_eleccion:
            # Un kit con "shampoo a elección" explica un shampoo de más en el Excel.
            for cat in list(a_eleccion):
                if any(norm(p.nombre).startswith(cat) for p in ex["prods"]):
                    usar = min(diff, a_eleccion[cat])
                    diff -= usar
                    a_eleccion[cat] -= usar
                    if a_eleccion[cat] <= 0:
                        del a_eleccion[cat]
        if abs(diff) <= tol:
            continue
        precio = max((p.precio for p in ex["prods"]), default=0.0)
        (solo_excel if diff > 0 else solo_siigo).append((clave, diff, precio, ex["prods"]))

    out = []
    col_f = d.celdas.get("col.salidas_siigo", "F")

    def evidencia(items):
        ev = []
        for clave, diff, precio, prods in items[:6]:
            nombre = m.nombre_clave.get(clave, clave)
            for p in prods[:3]:
                ev.append(_ev(d, f"{col_f}{p.fila}", f"{p.nombre}: {p.salidas_siigo:g} en el Excel"))
            lineas = u.lineas_por_clave.get(clave, [])
            ev.append(Evidencia("Siigo", ", ".join(f"fila {ln.fila}" for ln in lineas[:4]) or "—",
                                u.por_clave.get(clave, 0), "",
                                f"{nombre}: {u.por_clave.get(clave, 0):g} facturadas en Siigo"
                                + (f" ({cx.siigo_archivo})" if cx.siigo_archivo else "")))
            for nota in notas_ajuste.get(clave, [])[:2]:
                ev.append(Evidencia(d.hoja, nota.split(":")[0], None, "",
                                    "Se descontó del Excel por ser ajuste: " + nota.split(":", 1)[1].strip()))
        return ev

    def describir(items):
        return _lista([f"{m.nombre_clave.get(c, c)} ({abs(df):g} u)" for c, df, _, _ in items])

    if solo_siigo:
        valor = sum(abs(df) * pr for _, df, pr, _ in solo_siigo)
        unidades = sum(abs(df) for _, df, _, _ in solo_siigo)
        explica = valor if cx.descuadre > 0 else 0.0
        if explica:
            texto = (f"Hay {unidades:g} unidad(es) facturadas en Siigo que no están en el Excel "
                     f"({describir(solo_siigo)}), por {pesos(valor)}. Si la plata está en la caja, "
                     f"explican el sobrante: la venta se facturó pero no se anotó en la planilla.")
        else:
            texto = (f"Hay {unidades:g} unidad(es) facturadas en Siigo que no están en el Excel "
                     f"({describir(solo_siigo)}), por {pesos(valor)}. "
                     + ("La caja cuadra, así que esa plata tampoco entró a caja. Revisar."
                        if abs(cx.descuadre) <= cx.config["estado"]["tolerancia_cuadra"]
                        else "Revisar."))
        out.append(_h(cx, "R20", "causa" if explica else "señal", "alta", texto,
                      explica if _mismo_signo(explica, cx.descuadre) else 0.0, evidencia(solo_siigo)))

    if solo_excel:
        valor = sum(df * pr for _, df, pr, _ in solo_excel)
        unidades = sum(df for _, df, _, _ in solo_excel)
        explica = -valor if cx.descuadre < 0 else 0.0
        if explica:
            texto = (f"El Excel tiene {unidades:g} salida(s) más que lo facturado en Siigo "
                     f"({describir(solo_excel)}), por {pesos(valor)}. Si esas unidades no se vendieron "
                     f"(error al anotar), inflan la venta teórica y explican el faltante.")
        else:
            texto = (f"El Excel tiene {unidades:g} salida(s) anotadas como facturadas que no aparecen en "
                     f"Siigo ({describir(solo_excel)}), por {pesos(valor)}. Revisar si falta la factura.")
        out.append(_h(cx, "R20", "causa" if explica else "señal", "media", texto,
                      explica if _mismo_signo(explica, cx.descuadre) else 0.0, evidencia(solo_excel)))

    if sin_mapeo_excel:
        out.append(_h(cx, "R20", "integridad", "baja",
                      "Productos del Excel con salidas que no están en el mapeo de Siigo, así que no se "
                      f"pudieron comparar: {_lista([p.nombre for p in sin_mapeo_excel])}. Agrégalos al mapeo.",
                      0.0, [_ev(d, f"{col_f}{p.fila}", p.nombre) for p in sin_mapeo_excel[:6]]))
    if u.sin_mapeo:
        out.append(_h(cx, "R20", "integridad", "baja",
                      "Productos de Siigo que no están en el mapeo, así que no se pudieron comparar: "
                      f"{_lista([ln.nombre or ln.codigo for ln in u.sin_mapeo])}. Agrégalos al mapeo.",
                      0.0, [Evidencia("Siigo", f"fila {ln.fila}", ln.unidades, "", f"{ln.codigo} {ln.nombre}")
                            for ln in u.sin_mapeo[:6]]))
    return out


REGLAS_N2 = [r20]
