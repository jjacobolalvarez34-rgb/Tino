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

    # Ajustes: puntos de venta ----------------------------------------------
    def _recargar(self):
        self.emp = Empresa(self.c)
        return True

    def _perfil(self, fuente):
        filas = self.c.leer("perfil_fuente", [("fuente", "eq", fuente), ("activo", "eq", "true")],
                            "id,nombre,mapeo_columnas", "creado_en")
        return filas[0] if filas else None

    def _guardar_perfil(self, fuente, nombre, mapeo):
        perfil = self._perfil(fuente)
        if perfil:
            self.c.cambiar("perfil_fuente", [("id", "eq", perfil["id"])], {"mapeo_columnas": mapeo})
        else:
            self.c.crear("perfil_fuente", [{"empresa_id": self.emp.config_base["empresa_id"], "fuente": fuente,
                                            "nombre": nombre, "mapeo_columnas": mapeo}])

    def puntos(self):
        """Cada punto con su código de pago, sus datáfonos y cómo se llama en el Excel."""
        puntos = self.c.leer("punto_venta", columnas="id,codigo,nombre,tipo,activo", orden="codigo")
        codigos = self.c.leer("codigo_recaudo", [("activo_hasta", "is", "null")], "punto_id,codigo", "codigo")
        terminales = self.c.leer("terminal_datafono", [("activo_hasta", "is", "null")],
                                 "id,punto_id,proveedor,codigo_terminal", "codigo_terminal")
        nombres = ((self._perfil("excel_dia") or {}).get("mapeo_columnas") or {}).get("puntos", {})
        for p in puntos:
            p["codigo_pago"] = next((c["codigo"] for c in codigos if c["punto_id"] == p["id"]), "")
            p["datafonos"] = [t for t in terminales if t["punto_id"] == p["id"]]
            p["nombres_excel"] = sorted(t for t, cod in nombres.items() if cod == p["codigo"])
        return puntos

    def guardar_punto(self, datos):
        """Crea un punto o cambia su nombre, tipo o si está activo. El código no cambia."""
        nombre, tipo = (datos.get("nombre") or "").strip(), datos.get("tipo") or "detal"
        if not nombre:
            raise ErrorBase("Escriba el nombre del punto.")
        if datos.get("id"):
            self.c.cambiar("punto_venta", [("id", "eq", datos["id"])],
                           {"nombre": nombre, "tipo": tipo, "activo": bool(datos.get("activo", True))})
        else:
            codigo = (datos.get("codigo") or "").strip().upper()
            if not codigo:
                raise ErrorBase("Escriba un código corto para el punto, como P12.")
            self.c.crear("punto_venta", [{"empresa_id": self.emp.config_base["empresa_id"], "codigo": codigo,
                                          "nombre": nombre, "tipo": tipo}])
        return self._recargar()

    def poner_codigo_pago(self, punto_id, codigo):
        """El código del QR o la llave del punto. El anterior se cierra, no se borra."""
        codigo = "".join(ch for ch in (codigo or "") if ch.isdigit())
        if len(codigo) < 4:
            raise ErrorBase("El código de pago tiene al menos 4 dígitos.")
        hoy = dt.date.today().isoformat()
        self.c.cambiar("codigo_recaudo", [("punto_id", "eq", punto_id), ("activo_hasta", "is", "null")],
                       {"activo_hasta": hoy})
        self.c.crear("codigo_recaudo", [{"empresa_id": self.emp.config_base["empresa_id"], "punto_id": punto_id,
                                         "codigo": codigo, "activo_desde": hoy}])
        return self._recargar()

    def agregar_datafono(self, punto_id, proveedor, codigo):
        codigo = (codigo or "").strip()
        if proveedor not in ("bold", "redeban", "otro") or not codigo:
            raise ErrorBase("Elija el proveedor y escriba cómo aparece el datáfono en su reporte.")
        self.c.crear("terminal_datafono", [{"empresa_id": self.emp.config_base["empresa_id"], "punto_id": punto_id,
                                            "proveedor": proveedor, "codigo_terminal": codigo,
                                            "activo_desde": dt.date.today().isoformat()}])
        return self._recargar()

    def quitar_datafono(self, terminal_id):
        """El datáfono deja de estar en el punto desde hoy; queda en el historial."""
        self.c.cambiar("terminal_datafono", [("id", "eq", terminal_id)], {"activo_hasta": dt.date.today().isoformat()})
        return self._recargar()

    def nombre_excel(self, codigo_punto, texto, quitar=False):
        """Cómo se llama el punto en su Excel del día (perfil de la empresa, no código)."""
        texto = " ".join((texto or "").lower().split())
        if not texto:
            raise ErrorBase("Escriba el nombre como aparece en el Excel.")
        perfil = self._perfil("excel_dia")
        mapeo = dict((perfil or {}).get("mapeo_columnas") or {})
        puntos = dict(mapeo.get("puntos", {}))
        if quitar:
            puntos.pop(texto, None)
        else:
            puntos[texto] = codigo_punto
        mapeo["puntos"] = puntos
        self._guardar_perfil("excel_dia", "Excel diario de cada punto", mapeo)
        return self._recargar()

    # Ajustes: Siigo --------------------------------------------------------
    def _archivo_siigo(self):
        return Path(self.carpeta or ".") / "siigo.json"

    def _siigo(self):
        import json
        from ingesta import siigo
        a = self._archivo_siigo()
        if not a.exists():
            raise ErrorBase("Primero guarde el usuario, la llave y el Partner-Id de Siigo.")
        d = json.loads(a.read_text(encoding="utf-8"))
        return siigo.Siigo(d.get("usuario"), d.get("llave"), d.get("partner_id"))

    def siigo_estado(self):
        import json
        from ingesta import siigo
        a = self._archivo_siigo()
        d = json.loads(a.read_text(encoding="utf-8")) if a.exists() else {}
        perfil = ((self._perfil("siigo") or {}).get("mapeo_columnas") or {})
        return {"configurado": bool(d.get("llave")), "usuario": d.get("usuario", ""),
                "partner_id": d.get("partner_id", ""), "campo": perfil.get("campo", "cost_center"),
                "puntos": perfil.get("puntos", {}), "campos": siigo.CAMPOS}

    def siigo_guardar(self, usuario, llave, partner_id):
        """Guarda las credenciales en la carpeta de la empresa (nunca en la base ni en el
        repositorio) y prueba que Siigo las acepte."""
        import json
        from ingesta import siigo
        a = self._archivo_siigo()
        viejo = json.loads(a.read_text(encoding="utf-8")) if a.exists() else {}
        datos = {"usuario": (usuario or "").strip(), "llave": (llave or "").strip() or viejo.get("llave", ""),
                 "partner_id": "".join(ch for ch in (partner_id or "") if ch.isalnum())}
        try:
            siigo.Siigo(datos["usuario"], datos["llave"], datos["partner_id"]).probar()
        except siigo.ErrorSiigo as e:
            raise ErrorBase(str(e)) from None
        a.parent.mkdir(parents=True, exist_ok=True)
        a.write_text(json.dumps(datos, indent=2), encoding="utf-8")
        return True

    def siigo_valores(self, desde, hasta, campo):
        """Trae las facturas y dice qué valores tiene el campo elegido, para asignarles punto."""
        from ingesta import siigo
        try:
            s = self._siigo()
            self._facturas_siigo = (desde, hasta, s.facturas(desde, hasta))
            nombres = s.catalogo(campo)
        except siigo.ErrorSiigo as e:
            raise ErrorBase(str(e)) from None
        cuenta = siigo.valores_encontrados(self._facturas_siigo[2], campo)
        return {"facturas": len(self._facturas_siigo[2]),
                "valores": [{"valor": v, "nombre": nombres.get(v, ""), "facturas": n}
                            for v, n in sorted(cuenta.items(), key=lambda x: -x[1])]}

    def siigo_guardar_perfil(self, campo, puntos):
        from ingesta import siigo
        if campo not in siigo.CAMPOS:
            raise ErrorBase("Elija de dónde sale el punto de cada factura.")
        self._guardar_perfil("siigo", "Siigo", {"campo": campo, "puntos": {k: v for k, v in puntos.items() if v}})
        return True

    def siigo_traer(self, desde, hasta):
        """Trae las facturas del rango y las guarda sin repetir las que ya estaban."""
        from ingesta import siigo
        perfil = (self._perfil("siigo") or {}).get("mapeo_columnas") or {}
        if not perfil.get("puntos"):
            raise ErrorBase("Primero diga de qué punto es cada factura (paso 2).")
        cache = getattr(self, "_facturas_siigo", None)
        try:
            facturas = cache[2] if cache and cache[:2] == (desde, hasta) else self._siigo().facturas(desde, hasta)
        except siigo.ErrorSiigo as e:
            raise ErrorBase(str(e)) from None
        productos = self.c.leer("producto", columnas="id,codigo_siigo", orden="id")
        por_codigo = {p["codigo"]: p["id"] for p in self.emp.puntos}
        carga = siigo.normalizar(facturas, perfil, por_codigo,
                                 {p["codigo_siigo"]: p["id"] for p in productos if p["codigo_siigo"]}, desde, hasta)
        try:
            r = self.c.rpc("importar_facturas", {"p": carga})
        except ErrorBase as e:
            if e.codigo == "23505":
                return {"nuevas": 0, "repetidas": len(carga["facturas"]), "anuladas": 0,
                        "sin_punto": len(carga["errores"]), "nota": "Nada cambió en Siigo desde la última vez."}
            raise
        return {**r, "sin_punto": len(carga["errores"])}

    def facturas(self, desde, hasta):
        """Resumen por punto y día de las facturas traídas."""
        filas = self.c.leer("v_factura", [("fecha", "gte", desde), ("fecha", "lte", hasta)],
                            "punto_id,fecha,total,anulada", "fecha")
        resumen = {}
        for f in filas:
            r = resumen.setdefault((f["fecha"], f["punto_id"]), {"fecha": f["fecha"], "punto": self._nombre(f["punto_id"]),
                                                                 "facturas": 0, "total": 0, "anuladas": 0})
            if f["anulada"]:
                r["anuladas"] += 1
            else:
                r["facturas"] += 1
                r["total"] += f["total"]
        return sorted(resumen.values(), key=lambda r: (r["fecha"], r["punto"]))

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
