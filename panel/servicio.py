# -*- coding: utf-8 -*-
"""Lo que hacen las pantallas del programa conectado, sin ventana: se puede probar solo.

Cada método recibe y devuelve datos simples (texto, números, listas), listos para la
pantalla. Toda consulta va con la sesión del usuario: RLS decide qué ve y qué cambia.
"""
import datetime as dt
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(RAIZ / "motores" / "conciliador")]

from ingesta.tarjetas import unir_reportes  # noqa: E402
from panel.datos import cargar  # noqa: E402
from panel.datos import revisar as rdb  # noqa: E402
from panel.datos.cliente import ErrorBase  # noqa: E402
from panel.datos.empresa import Empresa  # noqa: E402
from revision import revisar  # noqa: E402

DECISIONES = {"confirmada", "rechazada"}
CIERRES = {"explicado", "resuelto", "aceptado"}


class Servicio:
    def __init__(self, cliente):
        self.c = cliente
        self.emp = None
        self.preparados = {}

    # Sesión ------------------------------------------------------------------
    def entrar(self, correo=None, clave=None):
        if correo:
            self.c.iniciar_sesion(correo, clave)
        yo = self.c.leer("usuario", columnas="id,nombre,rol,empresa_id", orden="id")
        empresa = self.c.leer("empresa", columnas="id,nombre", orden="id")
        if not empresa:
            raise ErrorBase("Este usuario no tiene empresa asignada.")
        self.emp = Empresa(self.c)
        mio = next((u for u in yo if u["id"] == self.c.usuario), yo[0] if len(yo) == 1 else {})
        return {"empresa": empresa[0]["nombre"], "nombre": mio.get("nombre", ""), "rol": mio.get("rol", "")}

    def _nombre(self, punto_id):
        return self.emp.etiqueta.get(punto_id, "Sin punto")

    # Archivos ----------------------------------------------------------------
    def preparar(self, rutas):
        """Lee cada archivo y dice qué trae, sin subir nada."""
        salida = []
        for ruta in rutas:
            try:
                carga, avisos = cargar.preparar(ruta, self.emp)
                clave = carga["hash"]
                self.preparados[clave] = carga
                salida.append({"clave": clave, "nombre": Path(ruta).name, "fuente": carga["fuente"],
                               "resumen": cargar.resumen(carga), "avisos": avisos[:20]})
            except Exception as e:  # noqa: BLE001 - se muestra junto al archivo
                salida.append({"clave": None, "nombre": Path(ruta).name, "error": str(e) or e.__class__.__name__})
        return salida

    def subir(self, clave):
        """Sube un archivo ya leído y revisa los días que trae."""
        carga = self.preparados.get(clave)
        if carga is None:
            raise ErrorBase("Ese archivo ya no está listo: elíjalo otra vez.")
        archivo = cargar.subir(self.c, carga)
        self.preparados.pop(clave, None)
        dias = self.revisar_rango(carga["desde"], carga["hasta"]) if carga.get("desde") else 0
        return {"archivo": archivo, "dias_revisados": dias}

    def archivos(self):
        filas = self.c.leer("archivo_importado", columnas="id,fuente,nombre,desde,hasta,filas,estado,creado_en,deshecho_en",
                            orden="creado_en.desc")
        return filas[:200]

    def deshacer(self, archivo_id):
        self.c.rpc("deshacer_archivo", {"p_archivo": archivo_id})
        return True

    def errores(self):
        return self.c.leer("error_importacion", [("resuelto", "eq", "false")], "id,tipo,texto,fila_origen,archivo_id",
                           "creado_en.desc")

    # Revisión ----------------------------------------------------------------
    def revisar_rango(self, desde, hasta):
        """Corre la revisión de cada día y la guarda. Devuelve cuántos días revisó."""
        excel, banco, tarj = rdb.leer(self.c, self.emp, desde, hasta)
        n = 0
        for fecha in rdb._dias(desde, hasta):
            r = revisar(fecha, excel, banco, tarj, self.emp.lectores["config"])
            if any(not p.get("sin_excel") for p in r["puntos"]):
                self.c.rpc("guardar_revision", {"p": rdb.para_guardar(r, excel)})
                n += 1
        return n

    def revision_dia(self, fecha):
        """La revisión de un día, para la pantalla de siempre. También la guarda."""
        excel, banco, tarj = rdb.leer(self.c, self.emp, fecha, fecha)
        r = revisar(fecha, excel, banco, tarj, self.emp.lectores["config"])
        r["puntos"] = [p for p in r["puntos"] if not p.get("sin_excel")]
        if r["puntos"]:
            self.c.rpc("guardar_revision", {"p": rdb.para_guardar(r, excel)})
        con_excel = {p["punto"] for p in r["puntos"]}
        r["puntos"] += [{"punto": n, "sin_excel": True} for n in self.emp.etiqueta.values() if n not in con_excel]
        r["avisos"] = [f"Falta configurar «{c}»: esa causa no se revisó." for c in r["sin_configurar"]]
        r["fuentes"] = {"excel": len(con_excel), "banco": int(fecha in banco["fechas"]),
                        "tarjetas": sum(1 for f in tarj["cubre"].values() if fecha in f)}
        return r

    # Transferencias ----------------------------------------------------------
    def transferencias(self, desde, hasta):
        filas = self.c.leer("v_transferencia", [("fecha", "gte", desde), ("fecha", "lte", hasta)],
                            "pago_id,punto_id,fecha,monto,fila_origen,estado,fecha_banco,referencia,nota", "fecha")
        orden = {"sospechosa": 0, "propuesta": 1, "pendiente": 2, "confirmada": 3, "rechazada": 4}
        for f in filas:
            f["punto"] = self._nombre(f["punto_id"])
        return sorted(filas, key=lambda f: (orden.get(f["estado"], 9), f["fecha"], f["punto"]))

    def decidir_transferencia(self, pago_id, estado, nota):
        if estado not in DECISIONES or not (nota or "").strip():
            raise ErrorBase("Para decidir hace falta una nota.")
        existe = self.c.leer("verificacion_transferencia", [("pago_id", "eq", pago_id)], "id,extracto_id")
        if not existe:
            self.c.crear("verificacion_transferencia", [{"empresa_id": self.emp.config_base["empresa_id"],
                                                         "pago_id": pago_id, "estado": "pendiente"}])
            existe = [{"extracto_id": None}]
        if estado == "confirmada" and not existe[0]["extracto_id"]:
            raise ErrorBase("Nada se confirma sin el extracto: use «No es» o espere el extracto (D-007).")
        self.c.cambiar("verificacion_transferencia", [("pago_id", "eq", pago_id)], {"estado": estado, "nota": nota})
        return True

    # Por confirmar -----------------------------------------------------------
    def por_confirmar(self):
        filas = self.c.leer("v_cruce", [("estado", "eq", "propuesta")],
                            "id,tipo,punto_id,fecha_anotada,monto_anotado,medio_tipo,fila_origen,fuente,fecha_externa,"
                            "monto_externo,referencia", "fecha_anotada")
        for f in filas:
            f["punto"] = self._nombre(f["punto_id"])
        return filas

    def decidir_cruce(self, cruce_id, estado, nota):
        if estado not in DECISIONES or not (nota or "").strip():
            raise ErrorBase("Para decidir hace falta una nota.")
        self.c.cambiar("conciliacion", [("id", "eq", cruce_id)], {"estado": estado, "nota": nota})
        return True

    # Descuadres --------------------------------------------------------------
    def descuadres(self, desde, hasta):
        filas = self.c.leer("v_jornada", [("fecha", "gte", desde), ("fecha", "lte", hasta)],
                            "id,punto_id,fecha,descuadre_id,descuadre,explicado,sin_explicar,estado_motor,causa_codigo,"
                            "descuadre_estado,descuadre_nota,asesoras_texto,venta_teorica", "fecha")
        causas = {c["codigo"]: c["nombre"] for c in self.c.leer("causa_descuadre", columnas="codigo,nombre", orden="codigo")}
        salida = []
        for f in filas:
            if f["descuadre_id"] is None:
                continue
            f["punto"] = self._nombre(f["punto_id"])
            f["causa"] = causas.get(f["causa_codigo"], "")
            salida.append(f)
        orden = {"sin_explicar": 0, "explicado": 1, "cuadra": 2}
        return sorted(salida, key=lambda f: (f["descuadre_estado"] != "abierto", orden.get(f["estado_motor"], 9),
                                             f["fecha"], f["punto"]))

    def pruebas(self, descuadre_id):
        filas = self.c.leer("descuadre_evidencia", [("descuadre_id", "eq", descuadre_id), ("vigente", "eq", "true")],
                            "causa_codigo,tipo,monto,total,detalle", "tipo")
        causas = {c["codigo"]: c["nombre"] for c in self.c.leer("causa_descuadre", columnas="codigo,nombre", orden="codigo")}
        for f in filas:
            f["causa"] = causas.get(f["causa_codigo"], f["causa_codigo"])
        return filas

    def cerrar_descuadre(self, descuadre_id, estado, nota):
        if estado not in CIERRES or not (nota or "").strip():
            raise ErrorBase("Para cerrar un descuadre hace falta una nota.")
        self.c.cambiar("descuadre", [("id", "eq", descuadre_id)], {"estado": estado, "nota": nota})
        return True

    # Ventas con tarjeta ------------------------------------------------------
    def cobros(self, desde, hasta):
        """Cobros de Bold y Redeban de la base, un reporte por proveedor y día (D-038)."""
        movs = self.c.leer("v_movimiento_vigente", [("fecha", "gte", desde), ("fecha", "lte", hasta)],
                           "id,archivo_id,fuente,fecha,hora,punto_id,franquicia,bruto,comision,retenciones,prestamo,neto",
                           "fecha")
        lotes = {}
        for m in movs:
            if m["fuente"] in ("bold", "redeban"):
                lotes.setdefault(m["archivo_id"], []).append({
                    "fecha": m["fecha"], "hora": int(m["hora"][:2]) if m["hora"] else None,
                    "punto": self._nombre(m["punto_id"]), "proveedor": m["fuente"], "franquicia": m["franquicia"],
                    "bruto": m["bruto"], "comision": m["comision"], "retenciones": m["retenciones"],
                    "prestamo": m["prestamo"], "neto": m["neto"]})
        return unir_reportes(list(lotes.values()))


def ayer():
    return (dt.date.today() - dt.timedelta(days=1)).isoformat()
