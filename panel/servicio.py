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

from ingesta import archivos  # noqa: E402
from ingesta.tarjetas import unir_reportes  # noqa: E402
from panel.datos import cargar, exportar  # noqa: E402
from panel.datos import revisar as rdb  # noqa: E402
from panel.datos.cliente import ErrorBase  # noqa: E402
from panel.datos.empresa import Empresa  # noqa: E402
from revision import revisar  # noqa: E402

DECISIONES = {"confirmada", "rechazada"}
CIERRES = {"explicado", "resuelto", "aceptado"}


class Servicio:
    def __init__(self, cliente, carpeta=None):
        self.c = cliente
        self.carpeta = carpeta  # carpeta de datos de la empresa, para copias y exportaciones
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
        """Lee cada archivo y dice qué trae, sin subir nada. Un .zip se abre solo."""
        salida = []
        try:
            lista = archivos.expandir(rutas)
        except archivos.ArchivoNoValido as e:
            return [{"clave": None, "nombre": "", "error": str(e)}]
        for ruta, nombre in lista:
            try:
                carga, avisos = cargar.preparar(ruta, self.emp, nombre=Path(ruta).name)
                clave = carga["hash"]
                self.preparados[clave] = (carga, ruta)
                salida.append({"clave": clave, "nombre": nombre, "fuente": carga["fuente"],
                               "resumen": cargar.resumen(carga), "avisos": avisos[:20]})
            except Exception as e:  # noqa: BLE001 - se muestra junto al archivo
                salida.append({"clave": None, "nombre": nombre, "error": str(e) or e.__class__.__name__})
        return salida

    def subir(self, clave):
        """Sube un archivo ya leído y revisa los días que trae. Del extracto deja una copia
        con nombre claro en la carpeta de la empresa."""
        if clave not in self.preparados:
            raise ErrorBase("Ese archivo ya no está listo: elíjalo otra vez.")
        carga, ruta = self.preparados[clave]
        archivo = cargar.subir(self.c, carga)
        self.preparados.pop(clave, None)
        copia = None
        if carga["fuente"] == "banco" and self.carpeta:
            fechas = list(rdb._dias(carga["desde"], carga["hasta"]))
            copia = str(archivos.guardar_copia(ruta, Path(self.carpeta) / "extractos",
                                               archivos.nombre_extracto(carga.get("banco", "Banco"), fechas)))
        dias = self.revisar_rango(carga["desde"], carga["hasta"]) if carga.get("desde") else 0
        return {"archivo": archivo, "dias_revisados": dias, "copia": copia}

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

    # Sin origen ------------------------------------------------------------
    def _transferencias_banco(self, desde, hasta):
        """Transferencias del extracto vigente (una sola vez cada fecha, D-038)."""
        archivos_banco = self.c.leer("archivo_importado", [("fuente", "eq", "banco"), ("estado", "eq", "cargado")],
                                     "id,fuente,desde,hasta,creado_en", "creado_en")
        duenio = rdb.extractos_por_fecha(archivos_banco)
        movs = self.c.leer("v_movimiento_vigente", [("fecha", "gte", desde), ("fecha", "lte", hasta),
                                                    ("tipo", "eq", "transferencia"), ("fuente", "eq", "banco")],
                           "id,archivo_id,fecha,punto_id,referencia,descripcion,etiqueta,bruto,nota", "fecha")
        fechas = sorted(f for f in duenio if desde <= f <= hasta)
        return [m for m in movs if duenio.get(m["fecha"]) == m["archivo_id"]], fechas

    def sin_origen(self, desde, hasta):
        """Pagos sin punto, con su posible pareja (sin confirmarla) y la señal de QR cambiado (T2 y T3)."""
        d0 = (dt.date.fromisoformat(desde) - dt.timedelta(days=1)).isoformat()
        d1 = (dt.date.fromisoformat(hasta) + dt.timedelta(days=1)).isoformat()
        movs, _ = self._transferencias_banco(desde, hasta)
        anotadas = self.c.leer("v_transferencia", [("fecha", "gte", d0), ("fecha", "lte", d1)],
                               "pago_id,punto_id,fecha,monto,estado", "fecha")

        def cerca(a, b):
            return abs((dt.date.fromisoformat(a) - dt.date.fromisoformat(b)).days) <= 1

        pendientes, asignados = [], []
        for m in movs:
            fila = {"id": m["id"], "fecha": m["fecha"], "descripcion": m["descripcion"], "etiqueta": m["etiqueta"],
                    "valor": m["bruto"], "punto": self._nombre(m["punto_id"]) if m["punto_id"] else None,
                    "punto_id": m["punto_id"], "nota": m["nota"]}
            if m["punto_id"] is None:
                fila["sugerencias"] = [{"punto": self._nombre(t["punto_id"]), "punto_id": t["punto_id"],
                                        "fecha": t["fecha"]}
                                       for t in anotadas if t["estado"] == "sospechosa" and t["monto"] == m["bruto"]
                                       and cerca(t["fecha"], m["fecha"])]
                pendientes.append(fila)
            elif m["nota"]:
                asignados.append(fila)
        # T3: un punto anotó transferencias, ninguna llegó con su código y ese día hay pagos sin punto.
        senales = []
        for fecha in sorted({p["fecha"] for p in pendientes}):
            del_dia = [t for t in anotadas if t["fecha"] == fecha]
            for punto_id in sorted({t["punto_id"] for t in del_dia}):
                suyas = [t for t in del_dia if t["punto_id"] == punto_id]
                if suyas and all(t["estado"] in ("sospechosa", "pendiente") for t in suyas):
                    senales.append({"fecha": fecha, "punto": self._nombre(punto_id), "anotadas": len(suyas)})
        puntos = sorted(({"id": k, "nombre": v} for k, v in self.emp.etiqueta.items()), key=lambda p: p["nombre"])
        return {"pendientes": pendientes, "asignados": asignados, "senales": senales, "puntos": puntos}

    def asignar(self, movimiento_id, punto_id, nota):
        """Asigna (o quita) el punto de un pago, con nota, y revisa otra vez esos días."""
        if not (nota or "").strip():
            raise ErrorBase("Para asignar un pago hace falta una nota.")
        filas = self.c.cambiar("movimiento_externo", [("id", "eq", movimiento_id)],
                               {"punto_id": punto_id or None, "nota": nota})
        if not filas:
            raise ErrorBase("No se encontró ese pago, o su usuario no puede cambiarlo.")
        f = dt.date.fromisoformat(filas[0]["fecha"][:10])
        self.revisar_rango((f - dt.timedelta(days=1)).isoformat(), (f + dt.timedelta(days=1)).isoformat())
        return True

    def exportar_transferencias(self, desde, hasta):
        """El Excel de transferencias del banco, en la carpeta de la empresa."""
        movs, fechas = self._transferencias_banco(desde, hasta)
        codigos = self.emp.lectores["codigos"]
        puntos = [(self.emp.etiqueta[p["id"]], codigos.get(self.emp.etiqueta[p["id"]]))
                  for p in sorted(self.emp.puntos, key=lambda p: p["codigo"])]
        por_dia, sin = {}, []
        for m in movs:
            if m["punto_id"]:
                por_dia.setdefault((m["fecha"], self._nombre(m["punto_id"])), []).append(m["bruto"])
            # Lo asignado a mano cuenta en su punto y también queda en la lista de sin origen.
            if m["punto_id"] is None or m["nota"]:
                sin.append({"fecha": m["fecha"], "descripcion": m["descripcion"], "etiqueta": m["etiqueta"],
                            "valor": m["bruto"], "punto": self._nombre(m["punto_id"]) if m["punto_id"] else ""})
        carpeta = Path(self.carpeta or ".") / "transferencias"
        base = exportar.nombre(fechas)
        salida, n = carpeta / f"{base}.xlsx", 2
        while salida.exists():
            salida, n = carpeta / f"{base} ({n}).xlsx", n + 1
        return str(exportar.escribir(salida, fechas, puntos, por_dia, sin))

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
