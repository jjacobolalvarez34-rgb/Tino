# -*- coding: utf-8 -*-
"""Convierte un archivo en lo que recibe importar_archivo, y lo sube entero.

Lee con los mismos lectores de siempre (ingesta/) y resuelve cada nombre contra la
empresa: punto, medio de pago, producto y asesora. Lo que no se reconoce no se
inventa ni se descarta: entra como error por resolver, con su archivo y su fila.
"""
import hashlib
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(RAIZ / "motores" / "conciliador")]

from ingesta import banco as lector_banco  # noqa: E402
from ingesta import excel_diario, tarjetas  # noqa: E402

FUENTES = {"excel_dia": "Excel del día", "banco": "Extracto del banco", "tarjetas": "Reporte de Bold o Redeban"}


class ArchivoNoValido(Exception):
    pass


def huella(ruta):
    """sha256 del contenido: el mismo archivo con otro nombre es el mismo archivo."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def detectar(ruta):
    """Qué clase de archivo es, por su extensión y sus encabezados."""
    if Path(ruta).suffix.lower() == ".pdf":
        return "banco"
    import openpyxl
    libro = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    try:
        filas = [f for hoja in libro.worksheets for f in hoja.iter_rows(min_row=1, max_row=8, values_only=True)]
    finally:
        libro.close()
    texto = " ".join(str(v).upper() for f in filas for v in f if v is not None)
    if ("NOMBRE DEL DAT" in texto and "FECHA" in texto) or ("CODIGO ESTABLECIMIENTO" in texto and "FRANQUICIA" in texto):
        return "tarjetas"
    return "excel_dia"


def _fila_de(id_item):
    m = re.search(r"fila ([0-9]+)$", id_item)
    return int(m.group(1)) if m else None


def _excel(ruta, emp):
    punto, dias, avisos = excel_diario.leer(ruta, emp.lectores)
    if punto is None:
        raise ArchivoNoValido("No se sabe de qué punto es este Excel. " + " ".join(avisos[-1:]))
    punto_id = emp.id_por_nombre[punto]
    jornadas, errores = [], []
    for fecha, dia in sorted(dias.items()):
        caja = dia["caja"]
        j = {"punto_id": punto_id, "fecha": fecha, "pagos": [], "turnos": []}
        if caja["fila"]:
            j["reporte"] = {"hoja": caja["hoja"], "fila_origen": caja["fila"], "efectivo_contado": caja["efectivo"],
                            "venta_teorica": dia["venta"], "descuadre": dia["descuadre"],
                            "asesoras_texto": dia["asesoras"]}
        else:
            avisos.append(f"Hoja {caja['hoja']}: no se encontró la celda del descuadre; ese día no trae caja.")
        for item in dia["transferencias"]:
            j["pagos"].append({"medio_pago_id": emp.medio("transferencia"), "monto": item["monto"],
                               "fila_origen": _fila_de(item["id"])})
        for item in dia["tarjetas"]:
            j["pagos"].append({"medio_pago_id": emp.medio("tarjeta", punto_id), "monto": item["monto"],
                               "detalle_medio": "credito" if "|credito|" in item["id"] else "debito",
                               "fila_origen": _fila_de(item["id"])})
        fila_asesoras = caja["fila_asesoras"]
        for texto in dia["lista_asesoras"] if fila_asesoras else []:
            asesora = emp.asesora(punto_id, texto)
            j["turnos"].append({"asesora_id": asesora, "texto_original": texto, "fila_origen": fila_asesoras})
            if asesora is None:
                errores.append({"fila_origen": fila_asesoras, "tipo": "nombre_sin_reconocer",
                                "texto": f"{texto} ({caja['hoja']})"})
        # Todas las filas con precio, aunque no se movieran: la hoja es la lista de precios del
        # día, y la pista de "suma de precios" la necesita completa (D-037).
        detalle = []
        for p in dia["productos"]:
            if not p["fila"] or (p["precio"] <= 0 and not (p["cantidad"] or p["valor"])):
                continue
            producto = emp.producto(p["nombre"])
            detalle.append({"producto_id": producto, "texto_producto": p["nombre"], "cantidad": p["cantidad"],
                            "precio_lista": max(p["precio"], 0), "valor": p["valor"], "descuento": p["descuento"],
                            "regalos": p["regalos"], "fila_origen": p["fila"]})
            if producto is None:
                errores.append({"fila_origen": p["fila"], "tipo": "producto_sin_reconocer",
                                "texto": f"{p['nombre']} ({caja['hoja']})"})
        if dia["venta"] is not None and caja["fila_venta"]:
            j["venta"] = {"total": dia["venta"], "fila_origen": caja["fila_venta"], "detalle": detalle}
        jornadas.append(j)
    if not jornadas:
        raise ArchivoNoValido("El Excel no trae ningún día que se pueda leer.")
    fechas = [j["fecha"] for j in jornadas]
    # Un producto sin reconocer se repite cada día: basta un error por nombre.
    unicos = {(e["tipo"], e["texto"].rsplit(" (", 1)[0]): e for e in errores}
    return {"jornadas": jornadas, "errores": list(unicos.values()), "desde": min(fechas), "hasta": max(fechas)}, avisos


def _banco(ruta, emp):
    b = lector_banco.leer(ruta, emp.lectores)
    if not b["fechas"]:
        raise ArchivoNoValido("El PDF no trae movimientos con fecha: ¿es el extracto de Bancolombia?")
    movimientos = [{"fila_origen": t["fila_origen"], "fuente": "banco", "tipo": "transferencia", "fecha": t["fecha"],
                    "punto_id": emp.id_por_nombre.get(t["punto"]) if t["punto"] else None,
                    "referencia": t["referencia"], "descripcion": t["tipo"], "bruto": t["valor"]}
                   for t in b["transferencias"] + b["sin_origen"]]
    return {"movimientos": movimientos, "desde": min(b["fechas"]), "hasta": max(b["fechas"])}, b["avisos"]


def _tarjetas(ruta, emp):
    cobros, avisos = tarjetas.leer(ruta, emp.lectores)
    if not cobros:
        raise ArchivoNoValido("El reporte no trae cobros de los datáfonos de la empresa.")
    movimientos = []
    for c in cobros:
        movimientos.append({
            "fila_origen": c["fila_origen"], "fuente": c["proveedor"], "tipo": "reversion" if c["bruto"] < 0 else "cobro",
            "fecha": c["fecha"], "hora": f"{c['hora']:02d}:00" if c["hora"] is not None else None,
            "punto_id": emp.id_por_nombre[c["punto"]],
            "terminal_id": emp.terminal_id.get((c["proveedor"], str(c["terminal"]).strip().upper())),
            "franquicia": c["franquicia"], "bruto": c["bruto"], "comision": c["comision"],
            "retenciones": c["retenciones"], "prestamo": c["prestamo"]})
    fechas = [c["fecha"] for c in cobros]
    return {"movimientos": movimientos, "desde": min(fechas), "hasta": max(fechas)}, avisos


def preparar(ruta, emp, fuente=None):
    """Lee el archivo y devuelve (carga, avisos). No escribe nada."""
    fuente = fuente or detectar(ruta)
    leer = {"excel_dia": _excel, "banco": _banco, "tarjetas": _tarjetas}[fuente]
    carga, avisos = leer(ruta, emp)
    if fuente == "tarjetas":
        proveedores = {m["fuente"] for m in carga["movimientos"]}
        fuente = proveedores.pop() if len(proveedores) == 1 else "bold"
    carga.update({"fuente": fuente, "nombre": Path(ruta).name, "hash": huella(ruta)})
    return carga, avisos


def subir(cliente, carga):
    """Sube el archivo entero. Si ya estaba cargado, la base lo rechaza (23505)."""
    return cliente.rpc("importar_archivo", {"p": carga})


def resumen(carga):
    """Qué trae, en palabras, para mostrarlo antes y después de subir."""
    jornadas = carga.get("jornadas", [])
    pagos = sum(len(j["pagos"]) for j in jornadas)
    return {"dias": len(jornadas), "pagos": pagos, "movimientos": len(carga.get("movimientos", [])),
            "errores": len(carga.get("errores", [])), "desde": carga.get("desde"), "hasta": carga.get("hasta")}
