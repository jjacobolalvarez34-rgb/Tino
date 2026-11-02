# -*- coding: utf-8 -*-
"""
Reglas de nivel 3 (con Bancolombia). Solo corren si lo cargado del banco cubre
el día revisado.

R30 Transferencias: la lista "Transferencias" del punto contra lo que llegó al
    banco, contando cuántas veces aparece cada monto en cada lado. Lo que no
    aparece se busca en el día anterior y el siguiente antes de reportarlo.
R31 Referencias: pagos sin código reconocible el mismo día en que un punto queda
    con transferencias que no llegaron → posible cambio de código de QR.
R32 Consignaciones: consignación del Excel contra las consignaciones del extracto.
R33 Tarjetas (Bold/Redeban): listas T + U del punto contra lo cobrado en el
    datáfono, con la misma comparación monto por monto que R30. Solo corre si
    el reporte cargado cubre ese punto y día.
"""
import datetime as dt

from .modelo import Evidencia
from .reglas_n1 import _h, _ev, _mismo_signo
from .texto import norm, pesos
from .banco import MovBanco

UN_DIA = dt.timedelta(days=1)


def _clave(v):
    return int(round(v))


def _restar(a, b):
    """a, b: listas de (monto, cosa). Empareja monto por monto (multiconjunto).
    Devuelve lo que sobra de a y lo que sobra de b."""
    pendientes = {}
    for v, x in b:
        pendientes.setdefault(_clave(v), []).append((v, x))
    sobran_a = []
    for v, x in a:
        lista = pendientes.get(_clave(v))
        if lista:
            lista.pop()
        else:
            sobran_a.append((v, x))
    sobran_b = [par for lista in pendientes.values() for par in lista]
    return sobran_a, sobran_b


def _parecidos(a, b):
    """¿Pudo ser un error de digitación? 35.900 vs 39.500 (dígitos cambiados de
    lugar), 35.900 vs 36.900 (un dígito distinto), 3.590 vs 35.900 (un cero)."""
    sa, sb = str(_clave(a)), str(_clave(b))
    if sa == sb:
        return False
    if len(sa) == len(sb):
        if sorted(sa) == sorted(sb):
            return True
        return sum(1 for x, y in zip(sa, sb) if x != y) == 1
    return _clave(a) * 10 == _clave(b) or _clave(b) * 10 == _clave(a)


COL_DEFECTO = {"col.pago_transferencias": "S", "col.pago_debito": "T", "col.pago_credito": "U"}


def _excel_de(dia, rol="transferencias"):
    """Lista S, T o U del Excel como [(monto, ("excel", hoja, fila, columna))]."""
    if not dia:
        return []
    return [(v, ("excel", dia.hoja, fila, f"col.pago_{rol}")) for fila, v in getattr(dia.pagos, rol)]


def _ext(movs):
    return [(m.valor, ("ext", m)) for m in movs]


def _ev_par(cx, cosa, nota=""):
    if cosa[0] == "excel":
        _, hoja, fila, rol_col = cosa
        col = cx.dia.celdas.get(rol_col, COL_DEFECTO.get(rol_col, "S"))
        celda = f"{col}{fila}"
        if hoja == cx.dia.hoja:
            return _ev(cx.dia, celda, nota)
        return Evidencia(hoja, celda, None, "", nota)
    m = cosa[1]
    partes = [nota, f"ref. {m.referencia}" if m.referencia else "",
              m.descripcion if m.fuente != "Banco" else "", f"({m.fecha:%d/%m})"]
    return Evidencia(m.fuente, m.origen, m.valor, "", " ".join(x for x in partes if x))


FRASES = {
    "R30": {"que": "transferencia(s)", "lista": "transferencias", "Lista": "Transferencias",
            "ext": "el banco", "llegaron": "llegaron al banco", "no_llegaron": "no llegaron al banco",
            "como": "como transferencia", "nota_ext": "llegó al banco", "ext_otro_dia": "llegó otro día",
            "vecino": " (normal en pagos de la noche)"},
    "R33": {"que": "venta(s) con tarjeta", "lista": "tarjetas", "Lista": "Ventas con tarjeta",
            "ext": "el datáfono", "llegaron": "se cobraron en el datáfono",
            "no_llegaron": "no aparecen en el datáfono", "como": "con tarjeta",
            "nota_ext": "cobrado en el datáfono", "ext_otro_dia": "se cobró otro día", "vecino": ""},
    # R21: Siigo (lo facturado) en vez de banco/datáfono. Una forma de pago mal
    # elegida al facturar es común, así que lo anotado y no facturado es "media".
    "R21T": {"que": "transferencia(s)", "lista": "transferencias", "Lista": "Transferencias",
             "ext": "Siigo", "llegaron": "se facturaron en Siigo como transferencia",
             "no_llegaron": "no están facturadas en Siigo como transferencia", "como": "como transferencia",
             "nota_ext": "facturado en Siigo", "ext_otro_dia": "se facturó otro día", "vecino": "",
             "sev_no": "media"},
    "R21C": {"que": "venta(s) con tarjeta", "lista": "tarjetas", "Lista": "Ventas con tarjeta",
             "ext": "Siigo", "llegaron": "se facturaron en Siigo con tarjeta",
             "no_llegaron": "no están facturadas en Siigo con tarjeta", "como": "con tarjeta",
             "nota_ext": "facturado en Siigo", "ext_otro_dia": "se facturó otro día", "vecino": "",
             "sev_no": "media"},
}


def _sobrantes_vecinos(cx, excel_de, ext_de, cubre):
    """Lo que le SOBRA al día anterior y al siguiente: cobros externos que no
    cuadran con el Excel de ese día, y anotaciones del Excel que no cuadran con
    lo externo. Usar todo el día vecino daría falsos "llegó otro día" con montos
    que se repiten a diario (un $72.800 del día siguiente ya tiene su venta)."""
    f = cx.dia.fecha_hoja
    ext_sobra, excel_sobra = [], []
    for fecha in (f + UN_DIA, f - UN_DIA):
        d = next((x for x in (cx.siguiente, cx.anterior) if x and x.fecha_hoja == fecha), None)
        if not cubre(fecha):          # sin datos externos de ese día: no se sabe qué le sobra
            excel_sobra += excel_de(d) if d else []
            continue
        if d is None:                 # día de otro mes: no hay Excel para descontar
            ext_sobra += ext_de(fecha)
            continue
        sobra_x, sobra_e = _restar(excel_de(d), ext_de(fecha))
        ext_sobra += sobra_e
        excel_sobra += sobra_x
    return ext_sobra, excel_sobra


def _cruzar(cx, regla, excel_de, ext_de, cubre, frases=None):
    """Lista del Excel contra la fuente externa (banco o datáfono), monto por
    monto. excel_de(dia) y ext_de(fecha) dan [(monto, cosa)]; cubre(fecha) dice
    si hay datos externos de ese día.
    Devuelve (hallazgos, anotadas que no aparecen, lista Excel del día, externa del día)."""
    fr = FRASES[frases or regla]
    f = cx.dia.fecha_hoja
    excel_hoy, ext_hoy = excel_de(cx.dia), ext_de(f)
    no_llegaron, no_anotadas = _restar(excel_hoy, ext_hoy)

    # Antes de reportar: ¿apareció el día anterior o el siguiente? ¿se anotó otro día?
    otro_dia = []
    ext_vecinos, excel_vecinos = _sobrantes_vecinos(cx, excel_de, ext_de, cubre)
    if no_llegaron:
        sigue, _ = _restar(no_llegaron, ext_vecinos)
        encontrados, _ = _restar(no_llegaron, sigue)
        otro_dia += [(fr["ext_otro_dia"], v, x) for v, x in encontrados]
        no_llegaron = sigue
    if no_anotadas:
        sigue, _ = _restar(no_anotadas, excel_vecinos)
        encontrados, _ = _restar(no_anotadas, sigue)
        otro_dia += [("se anotó otro día", v, x) for v, x in encontrados]
        no_anotadas = sigue

    # Parejas que parecen el mismo pago mal digitado.
    mal_digitadas = []
    for v_ex, x_ex in list(no_llegaron):
        par = next(((v_b, x_b) for v_b, x_b in no_anotadas if _parecidos(v_ex, v_b)), None)
        if par:
            mal_digitadas.append(((v_ex, x_ex), par))
            no_llegaron.remove((v_ex, x_ex))
            no_anotadas.remove(par)

    out = []
    desc = cx.descuadre
    if mal_digitadas:
        efecto = sum(a - bb for (a, _), (bb, _) in mal_digitadas)
        lista = ", ".join(f"{pesos(a)} anotado / {pesos(bb)} en {fr['ext']}" for (a, _), (bb, _) in mal_digitadas)
        ev = []
        for (a, xa), (bb, xb) in mal_digitadas:
            ev += [_ev_par(cx, xa, "anotado en el Excel"), _ev_par(cx, xb, fr["nota_ext"])]
        out.append(_h(cx, regla, "causa" if _mismo_signo(efecto, desc) else "señal", "media",
                      f"Posible monto mal digitado en {fr['lista']}: {lista}. "
                      f"Con el valor correcto la caja cambiaría en {pesos(-efecto)}.",
                      efecto if _mismo_signo(efecto, desc) else 0.0, ev))
    if no_anotadas:
        total = sum(v for v, _ in no_anotadas)
        explica = -total if desc < 0 else 0.0
        texto = (f"{len(no_anotadas)} {fr['que']} {fr['llegaron']} y no están anotadas en el Excel "
                 f"({', '.join(pesos(v) for v, _ in no_anotadas[:8])}; total {pesos(total)}).")
        texto += (f" Si se cobraron {fr['como']} pero no se anotaron, explican el faltante."
                  if explica else " Revisar a qué venta corresponden.")
        out.append(_h(cx, regla, "causa" if explica else "señal", "media", texto,
                      explica if _mismo_signo(explica, desc) else 0.0,
                      [_ev_par(cx, x, fr["nota_ext"]) for _, x in no_anotadas[:8]]))
    if no_llegaron:
        total = sum(v for v, _ in no_llegaron)
        explica = total if desc > 0 else 0.0
        texto = (f"{len(no_llegaron)} {fr['que']} anotadas en el Excel {fr['no_llegaron']} "
                 f"(ni ese día ni el anterior o el siguiente): {', '.join(pesos(v) for v, _ in no_llegaron[:8])}; "
                 f"total {pesos(total)}.")
        texto += (" Si se anotaron dos veces o por error, explican el sobrante." if explica
                  else f" Revisar: la plata anotada {fr['como']} no aparece en {fr['ext']}.")
        out.append(_h(cx, regla, "causa" if explica else "señal", fr.get("sev_no", "alta"), texto,
                      explica if _mismo_signo(explica, desc) else 0.0,
                      [_ev_par(cx, x, "anotado en el Excel") for _, x in no_llegaron[:8]]))
    if otro_dia:
        out.append(_h(cx, regla, "integridad", "info",
                      f"{fr['Lista']} que no cuadran el mismo día pero sí con el día vecino{fr['vecino']}: "
                      + ", ".join(f"{pesos(v)} ({que})" for que, v, _ in otro_dia[:8]) + ".",
                      0.0, [_ev_par(cx, x, que) for que, _, x in otro_dia[:6]]))
    return out, no_llegaron, excel_hoy, ext_hoy


def r30_r31(cx):
    b = cx.banco
    f = cx.dia.fecha_hoja
    if b is None or f not in b.fechas:
        return []
    punto = cx.punto
    out, no_llegaron, excel_hoy, banco_hoy = _cruzar(
        cx, "R30", _excel_de, lambda fecha: _ext(b.transferencias.get((fecha, punto), [])),
        lambda fecha: fecha in b.fechas)

    # R31: pagos sin código el mismo día en que este punto quedó con transferencias sin llegar.
    sin_codigo = b.sin_identificar.get(f, [])
    if no_llegaron and sin_codigo:
        sin_par, _ = _restar(list(no_llegaron), _ext(sin_codigo))
        coinciden = [par for par in no_llegaron if par not in sin_par]
        sin_transf_banco = not banco_hoy and len(excel_hoy) >= 2
        if coinciden or sin_transf_banco:
            texto = (f"Ese día llegaron {len(sin_codigo)} pago(s) sin código de punto reconocible"
                     + (f", y {len(coinciden)} coinciden en monto con transferencias de este punto que no "
                        f"aparecen ({', '.join(pesos(v) for v, _ in coinciden[:6])})" if coinciden else "")
                     + (". Además el punto no tiene NINGUNA transferencia en el banco ese día" if sin_transf_banco else "")
                     + ". Posible cambio del código del QR del punto: revisar la referencia en el extracto.")
            out.append(_h(cx, "R31", "señal", "alta" if coinciden else "media", texto, 0.0,
                          [Evidencia("Banco", m.origen, m.valor, "",
                                     f"sin identificar {m.referencia or ''} {m.descripcion or ''}".strip())
                           for m in sin_codigo[:6]]))
    return out


def r32(cx):
    b = cx.banco
    f = cx.dia.fecha_hoja
    cons = cx.dia.caja.consignacion or 0
    if b is None or not cons or f not in b.fechas_consignaciones:
        return []
    tol = cx.config.get("banco", {}).get("tolerancia_consignacion", 0)
    candidatos = b.consignaciones.get(f, []) + b.consignaciones.get(f + UN_DIA, [])
    if any(abs(m.valor - cons) <= tol for m in candidatos):
        return []
    parecidas = [m for m in candidatos if abs(m.valor - cons) <= max(1000, 0.02 * cons)]
    texto = (f"La consignación anotada en el Excel ({pesos(cons)}) no aparece en el extracto de ese día "
             f"ni del siguiente.")
    if parecidas:
        texto += " Hay consignaciones parecidas: " + ", ".join(pesos(m.valor) for m in parecidas[:4]) + "."
    else:
        texto += " Revisar el soporte de la consignación."
    return [_h(cx, "R32", "señal", "alta", texto, 0.0,
               [_ev(cx.dia, "caja.consignacion")] +
               [Evidencia("Banco", m.origen, m.valor, "", m.descripcion) for m in parecidas[:4]])]


def r33(cx):
    """Tarjetas: listas T (débito) + U (crédito) contra lo cobrado en Bold/Redeban."""
    t = cx.tarjetas
    f = cx.dia.fecha_hoja
    if t is None or not t.cubre(f, cx.punto):
        return []
    out, *_ = _cruzar(cx, "R33",
                      lambda d: _excel_de(d, "debito") + _excel_de(d, "credito"),
                      lambda fecha: _ext(t.de(fecha, cx.punto)),
                      lambda fecha: t.cubre(fecha, cx.punto))
    return out


def _formas(cx, clave):
    return [norm(x) for x in cx.config.get("siigo", {}).get("formas_pago", {}).get(clave, [])]


def r21(cx):
    """Formas de pago facturadas en Siigo (reporte "Movimiento ventas y compras")
    contra el Excel: transferencias contra la lista S, tarjetas contra T + U,
    ADDI contra el total de la caja, y facturas a las que les cambiaron la fecha."""
    dias = cx.siigo_dias or {}
    f = cx.dia.fecha_hoja
    punto = cx.punto

    def rep_de(fecha):
        r = dias.get(fecha)
        return r if r is not None and r.puntos is not None and r.trae_punto(punto) else None

    if rep_de(f) is None:
        return []

    def pagos(fecha, clave):
        r = rep_de(fecha)
        if r is None:
            return []
        formas = _formas(cx, clave)
        return _ext([MovBanco(fecha, pg.valor, punto, "", f"factura {pg.factura} · {pg.forma}",
                              f"{r.archivo} fila {pg.fila}", fuente="Siigo")
                     for pg in r.pagos if pg.punto == punto and any(norm(pg.forma).startswith(x) for x in formas)])

    cubre = lambda fecha: rep_de(fecha) is not None
    out, *_ = _cruzar(cx, "R21", _excel_de, lambda fecha: pagos(fecha, "transferencias"), cubre, "R21T")
    o2, *_ = _cruzar(cx, "R21", lambda d: _excel_de(d, "debito") + _excel_de(d, "credito"),
                     lambda fecha: pagos(fecha, "tarjetas"), cubre, "R21C")
    out += o2

    addi_siigo = sum(v for v, _ in pagos(f, "addi"))
    addi_excel = cx.dia.caja.addi or 0.0
    if abs(addi_siigo - addi_excel) > 1:
        out.append(_h(cx, "R21", "señal", "media",
                      f"ADDI facturado en Siigo: {pesos(addi_siigo)}; en el Excel: {pesos(addi_excel)} "
                      f"(diferencia {pesos(addi_siigo - addi_excel)}).", 0.0,
                      [_ev(cx.dia, "caja.addi")] + [_ev_par(cx, x, "facturado en Siigo") for _, x in pagos(f, "addi")[:4]]))

    movidas = [x for x in rep_de(f).fechas_cambiadas if x[1] == punto]
    if movidas:
        out.append(_h(cx, "R21", "señal", "media",
                      f"{len(movidas)} factura(s) de este día se crearon en Siigo otro día y les cambiaron la fecha: "
                      + ", ".join(f"{fac} (creada el {cr:%d/%m a las %H:%M})" for fac, _, cr in movidas[:6])
                      + ". Revisar por qué.", 0.0,
                      [Evidencia("Siigo", rep_de(f).archivo, None, "", f"factura {fac}") for fac, _, _ in movidas[:6]]))
    return out


REGLAS_N3 = [r30_r31, r32]
REGLAS_SIIGO_PAGOS = [r21]
REGLAS_TARJETAS = [r33]
