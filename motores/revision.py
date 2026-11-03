# -*- coding: utf-8 -*-
"""Revisión de la mañana: lo anotado en cada punto contra el banco y los datáfonos.

Arma los cruces con las funciones del núcleo, que existen en Python y TypeScript. Aquí
solo se ordenan los datos y se juntan los resultados. Sigue `docs/REGLAS/`.
"""
import datetime as dt

from nucleo.logica import (causa_billete, causa_compensacion, causa_precios, causas_de_cruce, cruzar,
                           estado_dia, sobrantes_vecinos)

UN_DIA = dt.timedelta(days=1)
# Lo que cada causa del descuadre necesita de la configuración de la empresa (⚑ D4 a D6).
CONFIG_CAUSAS = ("compensacion", "billete", "precios")


def _vecinas(fecha):
    f = dt.date.fromisoformat(fecha)
    return [(f + UN_DIA).isoformat(), (f - UN_DIA).isoformat()]


def _cruce(fecha, dias_punto, rol, externo_de, cubre):
    """Lo anotado de un rol (transferencias o tarjetas) contra lo externo, con días vecinos."""
    vecinos = [{"cubre": cubre(f), "tiene_excel": f in dias_punto,
                "anotado": dias_punto.get(f, {}).get(rol, []), "externo": externo_de(f)} for f in _vecinas(fecha)]
    sobra = sobrantes_vecinos(vecinos)
    return cruzar(dias_punto[fecha][rol], externo_de(fecha), sobra["ext_sobra"], sobra["excel_sobra"])


def _causas_del_descuadre(fecha, dias_punto, config):
    """Compensación con el día vecino, error de billete y suma de precios."""
    dia, descuadre = dias_punto[fecha], dias_punto[fecha]["descuadre"]
    causas = []
    if "compensacion" in config:
        # Vecinos son la hoja anterior y la siguiente del libro, como en el conciliador: si
        # el domingo no abrió, el lunes se compara con el sábado.
        fechas = sorted(dias_punto)
        i = fechas.index(fecha)
        vecinos = [(c, fechas[j]) for c, j in (("anterior", i - 1), ("siguiente", i + 1)) if 0 <= j < len(fechas)]
        cuando = dict(vecinos)
        for c in causa_compensacion(descuadre, [{"cual": c, "descuadre": dias_punto[f]["descuadre"]} for c, f in vecinos],
                                    **config["compensacion"]):
            causas.append({**c, "fecha": cuando[c["cual"]]})
    if "billete" in config:
        causas += causa_billete(descuadre, **config["billete"])
    if "precios" in config:
        productos = dia.get("productos", [])
        for c in causa_precios(descuadre, [{"precio": p["precio"], "movimiento": p["movimiento"]} for p in productos],
                               **config["precios"]):
            # Nombres de ejemplo para cada precio, primero los que se movieron ese día.
            nombres = {}
            for p in sorted(productos, key=lambda p: -p["movimiento"]):
                nombres.setdefault(p["precio"], []).append(p["nombre"])
            c["productos"] = [[{"precio": q, "nombres": nombres.get(q, [])[:2]} for q in combo]
                              for combo in c["combinaciones"]]
            causas.append(c)
    return causas


def revisar(fecha, excel, banco, tarjetas, config):
    """Revisión de un día para todos los puntos con Excel.

    excel:    {punto: {fecha: día}}, de ingesta.excel_diario.
    banco:    {"por_dia": {(fecha, punto): [ítems]}, "fechas": set, "sin_origen": [...]}.
    tarjetas: {"por_dia": {(fecha, punto): [ítems]}, "cubre": {punto: set de fechas}}.
    config:   tolerancia_cuadra, porcentaje_explicado, reglas_sin_peso y los valores de
              compensacion, billete y precios, de la empresa.
    """
    puntos = []
    for punto, dias_punto in sorted(excel.items()):
        dia = dias_punto.get(fecha)
        if dia is None:
            puntos.append({"punto": punto, "sin_excel": True})
            continue
        resultado = {"punto": punto, "asesoras": dia["asesoras"], "venta": dia["venta"],
                     "descuadre": dia["descuadre"], "cruces": {}, "causas": [], "sin_datos": []}
        descuadre = dia["descuadre"] or 0

        if fecha in banco["fechas"]:
            c = _cruce(fecha, dias_punto, "transferencias",
                       lambda f: banco["por_dia"].get((f, punto), []), lambda f: f in banco["fechas"])
            resultado["cruces"]["transferencias"] = c
            resultado["causas"] += causas_de_cruce("R30", c, descuadre)
        else:
            resultado["sin_datos"].append("extracto del banco")

        cubre = tarjetas["cubre"].get(punto, set())
        if fecha in cubre:
            c = _cruce(fecha, dias_punto, "tarjetas",
                       lambda f: tarjetas["por_dia"].get((f, punto), []), lambda f: f in cubre)
            resultado["cruces"]["tarjetas"] = c
            resultado["causas"] += causas_de_cruce("R33", c, descuadre)
        else:
            resultado["sin_datos"].append("reporte de Bold o Redeban")

        if dia["descuadre"] is None:
            resultado["estado"] = {"estado": "sin_dato", "explicado": 0, "sin_explicar": 0}
        else:
            resultado["causas"] += _causas_del_descuadre(fecha, dias_punto, config)
            # Una regla sin peso (como la suma de precios) es una pista: se muestra, no explica.
            for c in resultado["causas"]:
                if c["tipo"] == "causa" and c["regla"] in config["reglas_sin_peso"]:
                    c["tipo"] = "pista"
            causas = [{"regla": c["regla"], "monto": c["monto"]} for c in resultado["causas"] if c["tipo"] == "causa"]
            resultado["estado"] = estado_dia(dia["descuadre"], causas, config["tolerancia_cuadra"],
                                             config["porcentaje_explicado"], config["reglas_sin_peso"])
        puntos.append(resultado)
    sin_origen = [s for s in banco.get("sin_origen", []) if s["fecha"] == fecha]
    sin_configurar = [c for c in CONFIG_CAUSAS if c not in config]
    return {"fecha": fecha, "puntos": puntos, "sin_origen": sin_origen, "sin_configurar": sin_configurar}
