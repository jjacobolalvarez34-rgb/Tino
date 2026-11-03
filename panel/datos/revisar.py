# -*- coding: utf-8 -*-
"""La revisión de la mañana con lo que está en la base, y lo que se guarda de ella.

Lee lo vigente de unos días (y sus vecinos), lo ordena como lo espera motores/revision.py,
corre el mismo motor y arma lo que recibe guardar_revision: el descuadre de cada jornada
con sus pruebas, los cruces entre lo anotado y lo que llegó, y la verificación de cada
transferencia.

Cuando la misma plata llega en dos archivos, cuenta uno solo:
  * Excel: los pagos del archivo cuyo reporte de caja está vigente en esa jornada.
  * Extracto: para cada fecha, el último extracto cargado que la cubre.
  * Bold y Redeban: por proveedor y día, el reporte que trae el préstamo y, entre esos,
    el que más cobros trae (tarjetas.unir_reportes, igual que con archivos sueltos).
"""
import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores")]

from ingesta.tarjetas import unir_reportes  # noqa: E402
from nucleo.logica import emparejar  # noqa: E402
from revision import revisar  # noqa: E402

UN_DIA = dt.timedelta(days=1)
CODIGO = {("R30", "no_llego"): "transferencia_no_llego", ("R30", "sin_anotar"): "transferencia_sin_anotar",
          ("R30", "mal_digitado"): "transferencia_mal_digitada", ("R33", "no_llego"): "tarjeta_no_aparece",
          ("R33", "sin_anotar"): "tarjeta_sin_anotar", ("R33", "mal_digitado"): "tarjeta_mal_digitada"}


def _dias(desde, hasta):
    d, fin = dt.date.fromisoformat(desde), dt.date.fromisoformat(hasta)
    while d <= fin:
        yield d.isoformat()
        d += UN_DIA


def _rango(c, tabla, desde, hasta, columnas):
    return c.leer(tabla, [("fecha", "gte", desde), ("fecha", "lte", hasta)], columnas)


def leer(c, emp, desde, hasta):
    """Lo vigente entre desde y hasta, con un margen de días para los vecinos."""
    d0 = (dt.date.fromisoformat(desde) - 7 * UN_DIA).isoformat()
    d1 = (dt.date.fromisoformat(hasta) + 7 * UN_DIA).isoformat()
    nombre = {p["id"]: p["nombre"] for p in emp.puntos}

    jornadas = _rango(c, "v_jornada", d0, d1, "id,punto_id,fecha,reporte_id,venta_teorica,descuadre_reportado,"
                                              "asesoras_texto")
    reportes = {r["jornada_id"]: r["archivo_id"]
                for r in c.leer("v_reporte_vigente", columnas="jornada_id,archivo_id", orden="jornada_id")}
    pagos = _rango(c, "v_pago_vigente", d0, d1, "id,jornada_id,medio_tipo,monto,archivo_id,fila_origen")
    detalle = _rango(c, "v_detalle_vigente", d0, d1, "id,jornada_id,texto_producto,cantidad,precio_lista,archivo_id")
    movs = _rango(c, "v_movimiento_vigente", d0, d1, "id,archivo_id,fuente,tipo,fecha,punto_id,bruto,prestamo,"
                                                     "referencia,fila_origen")
    archivos = {a["id"]: a for a in c.leer("archivo_importado", [("estado", "eq", "cargado")],
                                           "id,fuente,desde,hasta,creado_en")}

    # Excel: lo de cada jornada sale del archivo de su reporte vigente.
    excel, clave = {}, {}
    for j in jornadas:
        if j["punto_id"] not in nombre:
            continue
        dia = {"transferencias": [], "tarjetas": [], "descuadre": j["descuadre_reportado"],
               "venta": j["venta_teorica"], "asesoras": j["asesoras_texto"] or "", "productos": [],
               "jornada_id": j["id"], "reporte_id": j["reporte_id"]}
        excel.setdefault(nombre[j["punto_id"]], {})[j["fecha"]] = dia
        clave[j["id"]] = dia
    for p in pagos:
        dia = clave.get(p["jornada_id"])
        if dia is None or (p["archivo_id"] and p["archivo_id"] != reportes.get(p["jornada_id"])):
            continue
        rol = {"transferencia": "transferencias", "tarjeta": "tarjetas"}.get(p["medio_tipo"])
        if rol:
            dia[rol].append({"monto": p["monto"], "id": f"{p['id']}|fila {p['fila_origen'] or 0}"})
    for d in detalle:
        dia = clave.get(d["jornada_id"])
        if dia is not None and (not d["archivo_id"] or d["archivo_id"] == reportes.get(d["jornada_id"])):
            dia["productos"].append({"precio": d["precio_lista"], "nombre": d["texto_producto"],
                                     "movimiento": 1 if d["cantidad"] else 0})

    # Extracto: cada fecha, del último extracto cargado que la cubre.
    extractos = sorted((a for a in archivos.values() if a["fuente"] == "banco" and a["desde"]),
                       key=lambda a: a["creado_en"])
    duenio = {}
    for a in extractos:
        for f in _dias(a["desde"], a["hasta"]):
            duenio[f] = a["id"]
    banco = {"por_dia": {}, "fechas": set(duenio), "sin_origen": []}
    lotes = {}
    for m in movs:
        if m["fuente"] == "banco":
            if duenio.get(m["fecha"]) != m["archivo_id"]:
                continue
            if m["punto_id"] in nombre:
                banco["por_dia"].setdefault((m["fecha"], nombre[m["punto_id"]]), []).append(
                    {"monto": m["bruto"], "id": m["id"]})
            elif m["punto_id"] is None:
                banco["sin_origen"].append({"fecha": m["fecha"], "valor": m["bruto"], "referencia": m["referencia"],
                                            "id": m["id"]})
        elif m["fuente"] in ("bold", "redeban") and m["punto_id"] in nombre:
            lotes.setdefault(m["archivo_id"], []).append(
                {"proveedor": m["fuente"], "fecha": m["fecha"], "punto": nombre[m["punto_id"]], "bruto": m["bruto"],
                 "prestamo": m["prestamo"], "id": m["id"]})

    # Bold y Redeban: un reporte por proveedor y día. Las reversiones no se cruzan.
    tarj = {"por_dia": {}, "cubre": {}}
    for co in unir_reportes(list(lotes.values())):
        tarj["cubre"].setdefault(co["punto"], set()).add(co["fecha"])
        if co["bruto"] >= 0:
            tarj["por_dia"].setdefault((co["fecha"], co["punto"]), []).append({"monto": co["bruto"], "id": co["id"]})
    for punto, fechas in tarj["cubre"].items():
        a0, a1 = min(fechas), max(fechas)
        tarj["cubre"][punto] = set(_dias(a0, a1))
    return excel, banco, tarj


def _pago(item_id):
    return item_id.split("|", 1)[0]


def para_guardar(resultado, excel):
    """Lo que calculó la revisión de un día, en la forma de guardar_revision."""
    descuadres, cruces, verificaciones = [], [], []
    for p in resultado["puntos"]:
        if p.get("sin_excel"):
            continue
        dia = excel[p["punto"]][resultado["fecha"]]
        if p["descuadre"] is not None:
            causas = [c for c in p["causas"] if c["tipo"] == "causa"]
            principal = max(causas, key=lambda c: abs(c["monto"]), default=None)
            estado = p["estado"]["estado"]
            codigo = (None if estado == "cuadra" else "sin_causa_clara" if estado == "sin_explicar"
                      else CODIGO.get((principal["regla"], principal["que"]), principal["que"]))
            evidencias = []
            for c in p["causas"]:
                detalle = {k: v for k, v in c.items() if k not in ("regla", "que", "tipo", "monto", "total")}
                if c["regla"] in ("R30", "R33"):
                    cruce = p["cruces"]["transferencias" if c["regla"] == "R30" else "tarjetas"]
                    campo = {"no_llego": "no_llegaron", "sin_anotar": "no_anotadas", "mal_digitado": "mal_digitadas"}
                    detalle["items"] = cruce[campo[c["que"]]]
                evidencias.append({"causa_codigo": CODIGO.get((c["regla"], c["que"]), c["que"]), "tipo": c["tipo"],
                                   "monto": c["monto"] if c["tipo"] == "causa" else 0, "total": c["total"],
                                   "detalle": detalle})
            descuadres.append({"jornada_id": dia["jornada_id"], "reporte_id": dia["reporte_id"], "monto": p["descuadre"],
                               "explicado": p["estado"]["explicado"], "sin_explicar": p["estado"]["sin_explicar"],
                               "estado_motor": estado, "causa_codigo": codigo, "evidencias": evidencias})

        _cruces_del_punto(p, dia, cruces, verificaciones)
    return {"descuadres": descuadres, "cruces": cruces, "verificaciones": verificaciones}


def _cruces_del_punto(p, dia, cruces, verificaciones):
    """Parejas entre lo anotado y lo que llegó: el mismo día, otro día y mal digitadas."""
    for rol in ("transferencias", "tarjetas"):
        cruce = p["cruces"].get(rol)
        if cruce is None:
            continue
        # Las mismas parejas que hizo cruzar en su primer paso (restar).
        mismo = emparejar(dia[rol], cruce["externo_dia"])["parejas"]
        vecinos = emparejar([{"monto": x["monto"], "id": x["id"]} for x in cruce["otro_dia"]
                             if x["donde"] == "externo_otro_dia"], cruce["ext_vecinos"])["parejas"]
        mal = [(m["anotado"], m["externo"]) for m in cruce["mal_digitadas"]]
        parejas = ([(x["a"], x["b"], "mismo_dia") for x in mismo] + [(x["a"], x["b"], "otro_dia") for x in vecinos]
                   + [(a, b, "mal_digitado") for a, b in mal])
        for a, b, tipo in parejas:
            cruces.append({"pago_id": _pago(a["id"]), "movimiento_id": b["id"], "tipo": tipo})
        if rol == "transferencias":
            for a, b, tipo in parejas:
                verificaciones.append({"pago_id": _pago(a["id"]), "extracto_id": b["id"],
                                       "estado": "confirmada" if tipo == "mismo_dia" else "propuesta"})
            for a in cruce["no_llegaron"]:
                verificaciones.append({"pago_id": _pago(a["id"]), "extracto_id": None, "estado": "sospechosa"})
