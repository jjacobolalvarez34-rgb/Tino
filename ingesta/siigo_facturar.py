# -*- coding: utf-8 -*-
"""Facturar desde Tino a través de Siigo (D-063). La factura la emite Siigo, con la cuenta, la
numeración y los impuestos que el cliente tiene configurados allá: Tino no calcula impuestos, manda
los ids de impuesto de cada producto tal como están en Siigo.

Cada venta de Tino tiene un id único creado donde se registró (también en el celular sin internet).
De ese id sale la `Idempotency-Key` de Siigo: si la misma venta se manda dos veces (se cortó el
internet a mitad, se reintenta), Siigo devuelve la factura que ya creó y no hace otra.

Una factura electrónica no puede llevar fecha anterior a hoy (regla de Siigo): una venta hecha sin
conexión se factura con la fecha del día en que se manda, y su fecha y hora reales van en las
observaciones. Qué entregarle al cliente mientras tanto (contingencia DIAN) lo confirma el contador.

Perfil de la empresa (perfil_fuente "siigo", clave "facturar"):
    {"documento": 26, "enviar_dian": false, "enviar_correo": false,
     "cliente_por_defecto": "222222222222",
     "vendedor": {"P01": 629}, "centro_costo": {"P01": 66},
     "pagos": {"efectivo": 5636, "debito": 5637, "credito": 5638, "transferencia": 5639},
     "impuestos": {"M001": [13156]}}
Por seguridad, enviar_dian empieza en false: la factura queda creada en Siigo sin mandarse a la
DIAN hasta que la empresa lo active.
"""
import re

from ingesta.siigo import ErrorSiigo


class FacturaInvalida(Exception):
    """La venta no se puede facturar así: falta algo del perfil o no cuadra."""


def llave_idempotencia(venta_id):
    """Hasta 30 letras o números, siempre la misma para la misma venta."""
    limpio = re.sub(r"[^A-Za-z0-9]", "", str(venta_id))
    if len(limpio) < 8:
        raise FacturaInvalida("La venta no tiene un id único válido.")
    return ("tino" + limpio)[:30]


def armar(venta, perfil, hoy):
    """El cuerpo de POST /v1/invoices para una venta de Tino.

    venta = {"id", "fecha", "hora"?, "punto": "P01", "cliente": "123" o None, "observaciones"?,
             "items": [{"codigo", "cantidad", "precio", "descuento"?}], "pagos": [{"medio", "valor"}]}
    Montos en pesos enteros, precios como los tiene Siigo (con o sin IVA según el producto allá).
    """
    faltan = [k for k in ("documento", "pagos") if not perfil.get(k)]
    if faltan:
        raise FacturaInvalida(f"El perfil de facturación no dice: {', '.join(faltan)}.")
    punto = venta.get("punto")
    vendedor = (perfil.get("vendedor") or {}).get(punto)
    if vendedor is None:
        raise FacturaInvalida(f"El perfil no dice qué vendedor de Siigo factura en el punto {punto}.")
    if not venta.get("items"):
        raise FacturaInvalida("La venta no tiene productos.")
    if not venta.get("pagos"):
        raise FacturaInvalida("La venta no tiene medio de pago.")

    items = []
    for it in venta["items"]:
        if not it.get("codigo") or int(it.get("cantidad") or 0) <= 0:
            raise FacturaInvalida("Cada producto necesita su código de Siigo y una cantidad mayor que cero.")
        linea = {"code": str(it["codigo"]), "quantity": int(it["cantidad"]), "price": int(it["precio"])}
        if it.get("descuento"):
            linea["discount"] = int(it["descuento"])
        impuestos = (perfil.get("impuestos") or {}).get(str(it["codigo"]))
        if impuestos:
            linea["taxes"] = [{"id": int(i)} for i in impuestos]
        items.append(linea)

    pagos = []
    for p in venta["pagos"]:
        id_pago = (perfil.get("pagos") or {}).get(p["medio"])
        if id_pago is None:
            raise FacturaInvalida(f"El perfil no dice qué forma de pago de Siigo es «{p['medio']}».")
        pagos.append({"id": int(id_pago), "value": int(p["valor"])})

    nota = venta.get("observaciones") or ""
    if venta.get("fecha") and venta["fecha"] != hoy:
        nota = (f"Venta del {venta['fecha']}{(' ' + venta['hora']) if venta.get('hora') else ''}, "
                f"registrada sin conexión en Tino. " + nota).strip()
    cuerpo = {
        "document": {"id": int(perfil["documento"])},
        "date": hoy,
        "customer": {"identification": str(venta.get("cliente") or perfil.get("cliente_por_defecto") or ""),
                     "branch_office": 0},
        "seller": int(vendedor),
        "items": items,
        "payments": pagos,
        "observations": (nota + f" · Tino {venta['id']}").strip(" ·")[:4000],
        "stamp": {"send": bool(perfil.get("enviar_dian", False))},
        "mail": {"send": bool(perfil.get("enviar_correo", False))},
    }
    if not cuerpo["customer"]["identification"]:
        raise FacturaInvalida("La venta no tiene cliente y el perfil no tiene cliente por defecto.")
    centro = (perfil.get("centro_costo") or {}).get(punto)
    if centro is not None:
        cuerpo["cost_center"] = int(centro)
    return cuerpo


def facturar(siigo, venta, perfil, hoy):
    """Crea la factura en Siigo. Se puede llamar las veces que haga falta con la misma venta: la
    llave de idempotencia evita duplicados. Devuelve {"id", "nombre", "total", "dian"}."""
    cuerpo = armar(venta, perfil, hoy)
    r = siigo.crear("/v1/invoices", cuerpo, llave_idempotencia(venta["id"]))
    if not r or not r.get("id"):
        raise ErrorSiigo("Siigo no devolvió la factura creada.")
    return {"id": r["id"], "nombre": r.get("name"), "total": r.get("total"),
            "dian": ((r.get("stamp") or {}).get("status"))}
