# -*- coding: utf-8 -*-
"""
Cierre del día — fachada del motor (paquete `cierre/`).

  sesion = SesionCierre()
  sesion.cargar_xlsx([ruta1, ruta2, ...])   # un libro mensual por punto
  sesion.fechas_disponibles()
  sesion.revisar(fecha)                      # -> dict listo para la interfaz

No modifica core.py, verify.py ni transferencias_core.py.
"""
import datetime as dt
import hashlib
import json
import os
import pickle

from cierre.lector_xlsx import LibroXlsx, ErrorLectura
from cierre import plantilla as plantilla_mod
from cierre.reglas_n1 import REGLAS, ContextoRegla
from cierre.texto import norm, pesos
from cierre.db import HistorialCierre
from cierre.asesoras import construir_mapa
from cierre import siigo as siigo_mod
from cierre.reglas_n2 import REGLAS_N2
from cierre import banco as banco_mod
from cierre.reglas_n3 import REGLAS_N3, REGLAS_TARJETAS, REGLAS_SIIGO_PAGOS
from cierre import tarjetas as tarjetas_mod
from cierre import lector_sheets as gs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DEFECTO = os.path.join(BASE_DIR, "cierre_config.json")
APPDATA = os.getenv("APPDATA") or os.path.expanduser("~")
DATOS_DIR = os.path.join(APPDATA, "SuiteIrina")
CONFIG_USUARIO = os.path.join(DATOS_DIR, "cierre_config.json")
CACHE_DIR = os.path.join(DATOS_DIR, "cache_cierre")
CACHE_VERSION = 3   # subir cuando cambie el lector, para no usar lecturas viejas
MAPEO_DEFECTO = os.path.join(BASE_DIR, "mapeo_siigo.xlsx")
MAPEO_USUARIO = os.path.join(DATOS_DIR, "mapeo_siigo.xlsx")
ASIGNACION_SHEETS = os.path.join(DATOS_DIR, "asignacion_sheets.json")


def _mezclar(base, encima):
    out = dict(base)
    for k, v in encima.items():
        out[k] = _mezclar(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


PLANTILLA_USUARIO = {
    "_nota": ("Escribe aquí SOLO lo que quieras cambiar; todo lo demás sale de la configuración "
              "del programa (cierre_config.json en la carpeta del programa, con todas las opciones). "
              "Ejemplo: {\"estado\": {\"tolerancia_cuadra\": 200}}")
}


def cargar_config():
    """Configuración del programa + los cambios del usuario en
    %APPDATA%\\SuiteIrina\\cierre_config.json, que ganan. El archivo del usuario
    guarda solo sus cambios (no una copia completa), así los valores nuevos de
    cada versión llegan aunque él ya haya editado algo."""
    with open(CONFIG_DEFECTO, encoding="utf-8") as f:
        config = json.load(f)
    try:
        if not os.path.exists(CONFIG_USUARIO):
            os.makedirs(DATOS_DIR, exist_ok=True)
            with open(CONFIG_USUARIO, "w", encoding="utf-8") as f:
                json.dump(PLANTILLA_USUARIO, f, ensure_ascii=False, indent=2)
        else:
            with open(CONFIG_USUARIO, encoding="utf-8") as f:
                config = _mezclar(config, json.load(f))
    except (OSError, ValueError):
        pass   # archivo ilegible o sin permisos: se usa la del programa
    return config


def identificar_punto(texto, config):
    """Texto libre (celda 'PUNTO DE VENTA' o nombre de archivo) -> id de punto."""
    t = " " + norm(texto) + " "
    mejor, largo = None, 0
    for p in config["puntos"]:
        for alias in p["alias"] + [p["id"], p["nombre"]]:
            a = norm(alias)
            if a and (" " + a + " ") in t and len(a) > largo:
                mejor, largo = p["id"], len(a)
    return mejor


def _clave_cache(path):
    st = os.stat(path)
    base = f"{CACHE_VERSION}|{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


CACHE_DIAS_MAX = 45


def _limpiar_cache():
    """Borra lecturas en caché que nadie usa hace más de CACHE_DIAS_MAX días
    (meses viejos, versiones anteriores del lector)."""
    limite = dt.datetime.now().timestamp() - CACHE_DIAS_MAX * 86400
    rutas = []
    for nombre in os.listdir(CACHE_DIR):
        ruta = os.path.join(CACHE_DIR, nombre)
        if os.path.isdir(ruta):   # extractos/: PDFs sacados de los .zip del banco
            rutas += [os.path.join(ruta, n) for n in os.listdir(ruta)]
        else:
            rutas.append(ruta)
    for ruta in rutas:
        try:
            if os.path.getmtime(ruta) < limite or os.path.getsize(ruta) == 0:
                os.remove(ruta)
        except OSError:
            pass


def leer_libro(path, log=print):
    """LibroXlsx con caché en disco (la lectura de un libro tarda ~40 s)."""
    return _con_cache(_clave_cache(path), lambda: LibroXlsx(path), log,
                      f"Leyendo {os.path.basename(path)} (la primera vez tarda ~40 s)...")


def _con_cache(clave, cargar, log, mensaje):
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache = os.path.join(CACHE_DIR, clave + ".pkl")
    if os.path.exists(cache):
        try:
            with open(cache, "rb") as f:
                libro = pickle.load(f)
            os.utime(cache)   # "usado hoy": que la limpieza no lo borre
            return libro
        except Exception:
            pass   # caché dañada: se vuelve a leer
    log(mensaje)
    libro = cargar()
    # Se escribe a un temporal y se renombra al final: si el programa se cierra
    # a mitad, nunca queda una caché a medias.
    tmp = cache + ".tmp"
    try:
        with open(tmp, "wb") as f:
            pickle.dump(libro, f)
        os.replace(tmp, cache)
    except Exception as e:
        log(f"Aviso: no se pudo guardar la lectura en caché ({type(e).__name__}: {e}); "
            f"la próxima vez volverá a tardar ~40 s.")
        try:
            os.remove(tmp)
        except OSError:
            pass
    _limpiar_cache()
    return libro


class SesionCierre:
    def __init__(self, ruta_db=None):
        self.config = cargar_config()
        self.libros = {}       # id punto -> LibroXlsx
        self.archivos = {}     # id punto -> ruta
        self.no_asignados = []  # [(ruta, motivo)]
        self.db = HistorialCierre(ruta_db or os.path.join(DATOS_DIR, "cierre.db"))
        self.siigo = {}         # fecha -> ReporteSiigo (solo reportes de un único día)
        self._mapeo = None
        self.banco = banco_mod.DatosBanco()   # todo lo cargado del banco (PDF y/o Sheet)
        self.tarjetas = tarjetas_mod.DatosTarjetas()   # Bold/Redeban
        self.google = gs.Google(DATOS_DIR)

    # ------------------------------------------------------------------
    # Bold / Redeban (opcional)
    # ------------------------------------------------------------------
    def cargar_tarjetas(self, rutas):
        """Reportes vírgenes de Bold o Redeban (.xlsx); se detecta cuál es cada uno."""
        resultado = []
        for ruta in rutas:
            nombre = os.path.basename(ruta)
            try:
                tipo, datos, puntos = tarjetas_mod.leer(ruta, lambda t: identificar_punto(t, self.config))
            except Exception as e:
                resultado.append({"archivo": nombre, "error": str(e)})
                continue
            self.tarjetas.agregar(datos, puntos)
            f = sorted(datos.fechas())
            resultado.append({"archivo": nombre, "error": None, "tipo": "Bold" if tipo == "bold" else "Redeban",
                              "cobros": sum(len(v) for v in datos.cobros.values()), "puntos": len(puntos),
                              "desde": f[0].isoformat() if f else None, "hasta": f[-1].isoformat() if f else None,
                              "avisos": datos.avisos})
        return resultado

    def estado_tarjetas(self):
        f = sorted(self.tarjetas.fechas())
        return {"archivos": self.tarjetas.archivos, "puntos": len(self.tarjetas.cobertura),
                "desde": f[0].isoformat() if f else None, "hasta": f[-1].isoformat() if f else None}

    # ------------------------------------------------------------------
    # Google Sheets (fase 5)
    # ------------------------------------------------------------------
    def google_estado(self):
        conectado = self.google.conectado()
        return {"credenciales": self.google.tiene_credenciales(), "conectado": conectado,
                "cuenta": self.google.cuenta() if conectado else ""}

    def _asignaciones(self):
        try:
            with open(ASIGNACION_SHEETS, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def google_buscar(self, mes):
        """Busca la carpeta del mes y propone qué Sheet es de cada punto. Lo que
        ya se confirmó antes para ese mes gana sobre la propuesta."""
        anio, m = map(int, mes.split("-"))
        ids = [p["id"] for p in self.config["puntos"]]
        carpeta_anio = self.google.carpeta_del_anio(anio)
        carpeta_mes = self.google.carpeta_del_mes(carpeta_anio["id"], m)
        sheets = self.google.sheets_de(carpeta_mes["id"])
        prop = gs.proponer_asignacion(sheets, lambda t: identificar_punto(t, self.config), set(ids))
        asignacion = {pid: (s["id"], "nombre") for pid, s in prop["puntos"].items()}
        por_id = {s["id"]: s for s in sheets}

        transf = prop["transferencias"]
        if transf:   # la hoja URL del Sheet de transferencias trae los enlaces de los 11 puntos
            try:
                filas = self.google.leer_filas(transf["id"], lambda t: norm(t) == "url", "A1:C30")
                for pid, sid in gs.ids_desde_hoja_url(next(iter(filas.values()), []),
                                                      lambda t: identificar_punto(t, self.config)).items():
                    if pid not in asignacion:
                        asignacion[pid] = (sid, "hoja URL de transferencias")
            except Exception:
                pass
        guardada = self._asignaciones().get(mes, {})
        for pid, sid in guardada.get("puntos", {}).items():
            if sid:
                asignacion[pid] = (sid, "confirmada antes")
        transf_id = guardada.get("transferencias") or (transf["id"] if transf else None)

        # Sheets asignados que no están en la carpeta del mes (vienen de la hoja URL
        # o de una confirmación anterior): se buscan por id para mostrarlos con nombre.
        for sid in {s for s, _ in asignacion.values()} | ({transf_id} if transf_id else set()):
            if sid not in por_id:
                try:
                    meta = self.google.archivo(sid)
                    por_id[sid] = {"id": sid, "name": meta["name"] + " (fuera de la carpeta del mes)"}
                except Exception:
                    por_id[sid] = {"id": sid, "name": f"(no se pudo abrir el Sheet {sid[:10]}…)"}
                sheets.append(por_id[sid])

        avisos = []
        faltan = [self.nombre_punto(p) for p in ids if p not in asignacion]
        if faltan:
            avisos.append("Sin Sheet: " + ", ".join(faltan) + ". Elígelo a mano o revisa la carpeta.")
        for pid, lista in prop["repetidos"].items():
            avisos.append(f"{self.nombre_punto(pid)}: hay {len(lista)} Sheets que parecen de este punto ("
                          + ", ".join(s["name"] for s in lista) + "). Confirma cuál es.")
        if prop["sin_asignar"]:
            avisos.append("No reconozco de qué punto son: " + ", ".join(s["name"] for s in prop["sin_asignar"]) + ".")
        if not transf_id:
            avisos.append("No encontré el Sheet de transferencias (uno que empiece por un número y diga "
                          "'transferencias').")
        return {
            "mes": mes, "carpeta": f"{carpeta_anio['name']} / {carpeta_mes['name']}",
            "sheets": [{"id": s["id"], "nombre": s["name"]} for s in sorted(sheets, key=lambda s: s["name"])],
            "puntos": [{"id": p["id"], "nombre": p["nombre"],
                        "sheet": asignacion.get(p["id"], (None, ""))[0],
                        "sheet_nombre": por_id.get(asignacion.get(p["id"], (None,))[0], {}).get("name", ""),
                        "origen": asignacion.get(p["id"], (None, ""))[1]} for p in self.config["puntos"]],
            "transferencias": transf_id,
            "avisos": avisos,
        }

    def google_guardar_asignacion(self, mes, puntos, transferencias):
        """puntos: {id_punto: id_sheet o None}."""
        todas = self._asignaciones()
        todas[mes] = {"puntos": {k: v for k, v in puntos.items() if v}, "transferencias": transferencias or None}
        os.makedirs(DATOS_DIR, exist_ok=True)
        tmp = ASIGNACION_SHEETS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(todas, f, ensure_ascii=False, indent=2)
        os.replace(tmp, ASIGNACION_SHEETS)

    def google_cargar(self, mes, log=print):
        """Lee de Google los Sheets confirmados para el mes (con caché por fecha
        de modificación: un Sheet que no cambió no se vuelve a descargar)."""
        self.config = cargar_config()
        guardada = self._asignaciones().get(mes)
        if not guardada:
            raise gs.ErrorGoogle("Primero busca y confirma los Sheets de ese mes.")
        resultado = []
        for pid, sid in guardada.get("puntos", {}).items():
            nombre_p = self.nombre_punto(pid)
            try:
                meta = self.google.archivo(sid)
                clave = hashlib.sha1(f"{CACHE_VERSION}|gs|{sid}|{meta['modifiedTime']}".encode()).hexdigest()
                libro = _con_cache(clave, lambda: self.google.leer_libro(sid, meta["name"]), log,
                                   f"Leyendo de Google: {meta['name']}…")
            except Exception as e:
                resultado.append({"punto": pid, "nombre": nombre_p, "error": str(e)})
                continue
            self.libros[pid] = libro
            self.archivos[pid] = gs.url_sheet(sid)
            resultado.append({"punto": pid, "nombre": nombre_p, "error": None, "sheet": libro.nombre,
                              "dias": len(libro.dias), "avisos": libro.avisos})
            log(f"✓ {nombre_p}: {libro.nombre} ({len(libro.dias)} días)")
        tid = guardada.get("transferencias")
        if tid:
            try:
                meta = self.google.archivo(tid)
                log(f"Leyendo de Google: {meta['name']}…")
                hojas = self.google.leer_filas(tid, banco_mod.es_hoja_de_dia, "A1:CB60")
                anio, m = map(int, mes.split("-"))
                datos = banco_mod.procesar_sheet(meta["name"], hojas,
                                                 lambda t: identificar_punto(t, self.config), (anio, m))
                self.banco.agregar(datos)
                resultado.append({"punto": None, "nombre": "Transferencias", "error": None,
                                  "sheet": meta["name"], "dias": len(datos.fechas), "avisos": datos.avisos})
            except Exception as e:
                resultado.append({"punto": None, "nombre": "Transferencias", "error": str(e)})
        return resultado

    # ------------------------------------------------------------------
    # Bancolombia (opcional)
    # ------------------------------------------------------------------
    def cargar_banco(self, rutas):
        """PDF de movimientos (o el .zip en que lo descarga Bancolombia) o Sheet
        de control de transferencias (.xlsx)."""
        resultado = []
        ids = {p["id"] for p in self.config["puntos"]}
        palabras = self.config["banco"]["palabras_consignacion"]
        expandidas = []
        for ruta in rutas:
            if ruta.lower().endswith(".zip"):
                try:
                    expandidas += banco_mod.leer_zip(ruta, os.path.join(CACHE_DIR, "extractos"))
                except Exception as e:
                    resultado.append({"archivo": os.path.basename(ruta), "error": str(e)})
            else:
                expandidas.append(ruta)
        for ruta in expandidas:
            nombre = os.path.basename(ruta)
            try:
                if ruta.lower().endswith(".pdf"):
                    datos = banco_mod.leer_pdf(ruta, ids, palabras)
                else:
                    defecto = None
                    if self.libros:
                        libro = next(iter(self.libros.values()))
                        defecto = (libro.anio, libro.mes)
                    datos = banco_mod.leer_sheet(ruta, lambda t: identificar_punto(t, self.config), defecto)
            except Exception as e:
                resultado.append({"archivo": nombre, "error": str(e)})
                continue
            n_transf = sum(len(v) for v in datos.transferencias.values())
            self.banco.agregar(datos)
            resultado.append({"archivo": nombre, "error": None, "transferencias": n_transf,
                              "dias": len(datos.fechas),
                              "desde": min(datos.fechas).isoformat() if datos.fechas else None,
                              "hasta": max(datos.fechas).isoformat() if datos.fechas else None,
                              "avisos": datos.avisos})
        return resultado

    def estado_banco(self):
        f = sorted(self.banco.fechas)
        return {"archivos": self.banco.archivos,
                "desde": f[0].isoformat() if f else None, "hasta": f[-1].isoformat() if f else None,
                "dias": len(f)}

    # ------------------------------------------------------------------
    # Siigo (opcional)
    # ------------------------------------------------------------------
    def ruta_mapeo(self):
        return MAPEO_USUARIO if os.path.exists(MAPEO_USUARIO) else MAPEO_DEFECTO

    def mapeo(self):
        if self._mapeo is None:
            self._mapeo = siigo_mod.cargar_mapeo(self.ruta_mapeo(), self.config["siigo"]["grupos"])
        return self._mapeo

    def cargar_mapeo_siigo(self, ruta):
        """Reemplaza el mapeo producto Excel ↔ Siigo por uno nuevo (se valida
        antes de copiarlo a la carpeta de datos)."""
        nuevo = siigo_mod.cargar_mapeo(ruta, self.config["siigo"]["grupos"])
        os.makedirs(DATOS_DIR, exist_ok=True)
        import shutil
        shutil.copyfile(ruta, MAPEO_USUARIO)
        self._mapeo = nuevo
        return {"productos": len(nuevo.clave_de_excel), "kits": len(nuevo.kits), "avisos": nuevo.avisos}

    def cargar_siigo(self, rutas):
        resultado = []
        ignorar = self.config["siigo"].get("vendedores_ignorar", [])
        for ruta in rutas:
            nombre = os.path.basename(ruta)
            try:
                if siigo_mod.es_movimiento(ruta):
                    resultado.append(self._cargar_movimiento(ruta, ignorar))
                    continue
                rep = siigo_mod.leer_reporte(ruta, lambda t: identificar_punto(t, self.config), ignorar)
            except Exception as e:
                resultado.append({"archivo": nombre, "error": str(e)})
                continue
            avisos = list(rep.avisos)
            if rep.desde is None:
                resultado.append({"archivo": nombre, "error": "No se pudo leer la fecha del reporte.",
                                  "avisos": avisos})
                continue
            if rep.desde != rep.hasta:
                resultado.append({"archivo": nombre, "error":
                                  f"El reporte va del {rep.desde:%d/%m/%Y} al {rep.hasta:%d/%m/%Y}. "
                                  f"Para comparar unidades debe ser de un solo día.", "avisos": avisos})
                continue
            self.siigo[rep.desde] = rep
            puntos = sorted({ln.punto for ln in rep.lineas})
            resultado.append({"archivo": nombre, "error": None, "fecha": rep.desde.isoformat(),
                              "puntos": [self.nombre_punto(x) for x in puntos], "avisos": avisos})
        return resultado

    def _cargar_movimiento(self, ruta, ignorar):
        """'Movimiento ventas y compras': un reporte de varios días (y de uno o
        varios puntos) se reparte día por día. Si ya había un reporte de
        movimiento de otro punto para ese día, se suman; los puntos repetidos no."""
        nombre = os.path.basename(ruta)
        dias, avisos = siigo_mod.leer_movimiento(ruta, lambda t: identificar_punto(t, self.config), ignorar)
        puntos = set()
        for fecha, rep in dias.items():
            puntos |= rep.puntos
            prev = self.siigo.get(fecha)
            if prev is not None and prev.puntos is not None:
                nuevos = rep.puntos - prev.puntos
                prev.lineas += [ln for ln in rep.lineas if ln.punto in nuevos]
                prev.pagos += [pg for pg in rep.pagos if pg.punto in nuevos]
                prev.fechas_cambiadas += [x for x in rep.fechas_cambiadas if x[1] in nuevos]
                prev.puntos = prev.puntos | nuevos
                if nombre not in prev.archivo:
                    prev.archivo += " + " + nombre
            else:
                rep.puntos = set(rep.puntos)
                self.siigo[fecha] = rep
        f = sorted(dias)
        return {"archivo": nombre, "error": None, "fecha": f[0].isoformat() if f else None,
                "hasta": f[-1].isoformat() if f else None, "dias": len(f),
                "facturas": sum(len({pg.factura for pg in r.pagos}) for r in dias.values()),
                "puntos": [self.nombre_punto(x) for x in sorted(puntos)], "avisos": avisos}

    def estado_siigo(self):
        """Agrupado por archivo: un reporte del mes son 30 días, no 30 renglones."""
        por_archivo = {}
        for f, r in sorted(self.siigo.items()):
            por_archivo.setdefault(r.archivo, []).append(f)
        return [{"fecha": fs[0].isoformat(), "hasta": fs[-1].isoformat(), "dias": len(fs), "archivo": a}
                for a, fs in por_archivo.items()]

    # ------------------------------------------------------------------
    def cargar_xlsx(self, rutas, log=print):
        self.config = cargar_config()
        resultado = []
        for ruta in rutas:
            nombre = os.path.basename(ruta)
            avisos_carga = []

            def log_y_avisos(m):
                log(m)
                if m.startswith("Aviso"):
                    avisos_carga.append(m)
            try:
                libro = leer_libro(ruta, log_y_avisos)
            except ErrorLectura as e:
                self.no_asignados.append((ruta, str(e)))
                resultado.append({"archivo": nombre, "punto": None, "error": str(e)})
                continue
            punto = (identificar_punto(libro.punto_texto, self.config)
                     or identificar_punto(nombre, self.config))
            if not punto:
                motivo = (f"No reconozco el punto '{libro.punto_texto}'. Agrega el nombre como alias en "
                          f"cierre_config.json.")
                self.no_asignados.append((ruta, motivo))
                resultado.append({"archivo": nombre, "punto": None, "error": motivo})
                continue
            reemplaza = self.archivos.get(punto)
            self.libros[punto] = libro
            self.archivos[punto] = ruta
            resultado.append({"archivo": nombre, "punto": punto, "error": None,
                              "mes": f"{libro.anio}-{libro.mes:02d}", "avisos": libro.avisos + avisos_carga,
                              "reemplaza": os.path.basename(reemplaza) if reemplaza and reemplaza != ruta else None})
            log(f"✓ {nombre} → {self.nombre_punto(punto)} ({len(libro.dias)} días)")
        return resultado

    def quitar_todos(self):
        self.libros, self.archivos, self.no_asignados, self.siigo = {}, {}, [], {}
        self.banco = banco_mod.DatosBanco()
        self.tarjetas = tarjetas_mod.DatosTarjetas()

    def nombre_punto(self, pid):
        return next((p["nombre"] for p in self.config["puntos"] if p["id"] == pid), pid)

    def fechas_disponibles(self):
        """Días que se pueden revisar: los de los archivos cargados más los que
        ya están guardados en el historial (de sesiones anteriores)."""
        fechas = {dt.date.fromisoformat(f) for f in self.db.fechas()}
        for libro in self.libros.values():
            fechas.update(libro.dias.keys())
        return sorted(fechas)

    def fechas_en_archivos(self, mes=None):
        fechas = set()
        for libro in self.libros.values():
            fechas.update(f for f in libro.dias if mes is None or f.isoformat()[:7] == mes)
        return sorted(fechas)

    def meses_disponibles(self):
        return sorted({f.isoformat()[:7] for f in self.fechas_disponibles()})

    def estado_archivos(self):
        return [{"punto": p["id"], "nombre": p["nombre"],
                 "archivo": self.libros[p["id"]].nombre if p["id"] in self.libros else None,
                 "google": str(self.archivos.get(p["id"], "")).startswith("https://")}
                for p in self.config["puntos"]]

    # ------------------------------------------------------------------
    def revisar(self, fecha):
        """Revisa el día en los 11 puntos. Con archivo cargado se calcula y se
        guarda en el historial (reemplazando lo anterior de ese día y punto); sin
        archivo, se muestra lo que haya guardado de una revisión anterior."""
        self.config = cargar_config()
        if isinstance(fecha, str):
            fecha = dt.date.fromisoformat(fecha)
        filas = []
        for p in self.config["puntos"]:
            libro = self.libros.get(p["id"])
            if libro is not None and fecha in libro.dias:
                filas.append(self._revisar_y_guardar(p, libro, fecha))
                continue
            guardado = self.db.dia(fecha.isoformat(), p["id"])
            if guardado:
                filas.append(self._fila_guardada(p, guardado))
            else:
                filas.append(self._fila_vacia(p, fecha, "sin archivo" if libro is None else "sin hoja de ese día"))
        return {"fecha": fecha.isoformat(), "puntos": filas}

    def revisar_mes(self, mes, log=print):
        """Revisa y guarda todos los días de `mes` (AAAA-MM) que traen los
        archivos cargados. Para llenar de una vez las pantallas Punto y Asesora."""
        fechas = self.fechas_en_archivos(mes)
        for k, f in enumerate(fechas, 1):
            log(f"Revisando {f:%d/%m} ({k} de {len(fechas)})…")
            self.revisar(f)
        return len(fechas)

    def _revisar_y_guardar(self, p, libro, fecha):
        fila = self._revisar_punto(p, libro, fecha)
        dia = libro.dias[fecha]
        extra = {
            "fuentes": fila.get("fuentes", ["excel"]),
            "descuentos": sum(x.descuento for x in dia.productos),
            "regalos": sum(x.regalos_valor for x in dia.productos),
            "ajustes": sum((getattr(dia.caja, k) or 0) for k in ("danados", "devoluciones", "cambios")),
        }
        fila["hallazgos"] = self.db.guardar_dia(fila, extra)
        fila["fuente"] = "archivo"
        return fila

    def _fila_guardada(self, p, d):
        return {"punto": p["id"], "nombre": p["nombre"], "fecha": d["fecha"], "estado": d["estado"],
                "hoja": d["hoja"], "archivo": d["archivo"], "asesoras": d["asesoras"], "venta": d["venta"],
                "descuadre": d["descuadre"], "explicado": d["explicado"], "sin_explicar": d["sin_explicar"],
                "causa_principal": d["causa_principal"], "avisos": d["avisos"],
                "hallazgos": self.db.hallazgos_dia(d["fecha"], p["id"]),
                "fuente": "guardado", "revisado_en": d["revisado_en"], "fuentes": d["fuentes"]}

    def _fila_vacia(self, p, fecha, estado):
        return {"punto": p["id"], "nombre": p["nombre"], "fecha": fecha.isoformat(), "estado": estado,
                "asesoras": [], "venta": None, "descuadre": None, "explicado": 0, "sin_explicar": None,
                "causa_principal": None, "hallazgos": [], "avisos": [], "fuente": None}

    def marcar(self, hallazgo_id, revision, nota=""):
        return self.db.marcar(int(hallazgo_id), revision, nota)

    # ------------------------------------------------------------------
    # Vistas del historial (cada una responde una pregunta)
    # ------------------------------------------------------------------
    def vista_punto(self, punto, mes):
        """¿Cómo va este punto? Calendario del mes + totales."""
        anio, m = map(int, mes.split("-"))
        dias = {d["fecha"]: d for d in self.db.dias_mes(mes, punto)}
        pend = self.db.conteo_pendientes(mes=mes, punto=punto)
        n_dias = (dt.date(anio + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
        calendario = []
        for d in range(1, n_dias + 1):
            f = dt.date(anio, m, d).isoformat()
            x = dias.get(f)
            calendario.append({
                "fecha": f, "estado": x["estado"] if x else "sin revisar",
                "descuadre": x["descuadre"] if x else None, "sin_explicar": x["sin_explicar"] if x else None,
                "asesoras": x["asesoras"] if x else [], "pendientes": pend.get((f, punto), 0)})
        rev = list(dias.values())
        totales = {
            "dias_revisados": len(rev),
            "venta": sum(x["venta"] or 0 for x in rev),
            "descuadre_neto": sum(x["descuadre"] or 0 for x in rev),
            "faltante_sin_explicar": sum(min(x["sin_explicar"] or 0, 0) for x in rev if x["estado"] == "sin explicar"),
            "sobrante_sin_explicar": sum(max(x["sin_explicar"] or 0, 0) for x in rev if x["estado"] == "sin explicar"),
            "por_estado": {e: sum(1 for x in rev if x["estado"] == e) for e in ("cuadra", "explicado", "sin explicar")},
            "pendientes": sum(pend.values()),
        }
        return {"punto": punto, "nombre": self.nombre_punto(punto), "mes": mes,
                "calendario": calendario, "totales": totales}

    def vista_asesoras(self, mes):
        """¿Cómo va cada persona? Días trabajados, faltantes sin explicar,
        señales de riesgo y hallazgos pendientes del mes."""
        dias = self.db.dias_mes(mes)
        nombres = {}
        for d in dias:
            nombres.setdefault(d["punto"], set()).update(d["asesoras"])
        mapa = construir_mapa(nombres, self.config.get("asesoras_alias"))
        pend = self.db.conteo_pendientes(mes=mes)
        riesgo = self.config["riesgo"]

        # promedio diario por punto, para comparar a cada asesora con su punto
        prom_punto = {}
        for d in dias:
            acc = prom_punto.setdefault(d["punto"], {"n": 0, "descuentos": 0, "regalos": 0, "ajustes": 0})
            acc["n"] += 1
            for k in ("descuentos", "regalos", "ajustes"):
                acc[k] += d[k] or 0

        personas = {}
        for d in dias:
            canon = sorted({mapa[(d["punto"], a)] for a in d["asesoras"]})
            for a in canon:
                per = personas.setdefault(a, {"asesora": a, "dias": [], "puntos": set()})
                per["puntos"].add(d["punto"])
                per["dias"].append({
                    "fecha": d["fecha"], "punto": d["punto"], "nombre_punto": self.nombre_punto(d["punto"]),
                    "estado": d["estado"], "descuadre": d["descuadre"], "sin_explicar": d["sin_explicar"],
                    "compartido": len(canon) > 1, "pendientes": pend.get((d["fecha"], d["punto"]), 0),
                    "descuentos": d["descuentos"] or 0, "regalos": d["regalos"] or 0, "ajustes": d["ajustes"] or 0})

        salida = []
        for per in personas.values():
            ds = per["dias"]
            falt = [x for x in ds if x["estado"] == "sin explicar" and (x["sin_explicar"] or 0) < 0]
            sobr = [x for x in ds if x["estado"] == "sin explicar" and (x["sin_explicar"] or 0) > 0]
            senales = []
            if len(falt) >= riesgo["faltantes_repetidos"]:
                senales.append(f"{len(falt)} días con faltante sin explicar "
                               f"({pesos(sum(x['sin_explicar'] for x in falt))}). Revisar.")
            for k, nombre in (("descuentos", "Descuentos"), ("regalos", "Regalos"),
                              ("ajustes", "Dañados/devoluciones/cambios")):
                suyo = sum(x[k] for x in ds) / len(ds)
                base_n = sum(prom_punto[p]["n"] for p in per["puntos"])
                base = sum(prom_punto[p][k] for p in per["puntos"]) / base_n if base_n else 0
                if suyo >= riesgo["monto_minimo_senal"] and base > 0 and suyo > riesgo["factor_sobre_promedio"] * base:
                    senales.append(f"{nombre}: {pesos(suyo)} por día, {suyo / base:.1f} veces el promedio "
                                   f"del punto ({pesos(base)}). Revisar.")
            salida.append({
                "asesora": per["asesora"],
                "puntos": sorted(self.nombre_punto(p) for p in per["puntos"]),
                "dias_trabajados": len(ds),
                "dias_compartidos": sum(1 for x in ds if x["compartido"]),
                "faltantes": {"dias": len(falt), "monto": sum(x["sin_explicar"] for x in falt)},
                "sobrantes": {"dias": len(sobr), "monto": sum(x["sin_explicar"] for x in sobr)},
                "pendientes": sum(x["pendientes"] for x in ds),
                "senales": senales,
                "dias": sorted(ds, key=lambda x: x["fecha"]),
            })
        salida.sort(key=lambda a: (a["faltantes"]["monto"], -len(a["senales"]), a["asesora"]))
        return {"mes": mes, "asesoras": salida}

    def vista_pendientes(self, incluir_menores=False):
        """Hallazgos sin revisar, del más antiguo al más reciente."""
        hs = self.db.pendientes(incluir_menores)
        for h in hs:
            h["nombre_punto"] = self.nombre_punto(h["punto"])
        return {"pendientes": hs, "total": len(hs)}

    def _revisar_punto(self, p, libro, fecha):
        dias = [libro.dias[f] for f in sorted(libro.dias)]
        if not hasattr(libro, "_plantilla"):
            libro._plantilla = plantilla_mod.construir(dias)
        i = next(k for k, d in enumerate(dias) if d.fecha_hoja == fecha)
        dia = dias[i]
        cx = ContextoRegla(
            dia=dia, anterior=dias[i - 1] if i > 0 else None,
            siguiente=dias[i + 1] if i + 1 < len(dias) else None,
            desc_fact=libro.desc_fact, plantilla=libro._plantilla, config=self.config,
            es_primer_dia=(fecha.day == 1), punto=p["id"],
            anterior2=dias[i - 2] if i > 1 else None)

        hallazgos, avisos = [], list(libro.avisos)
        reglas = list(REGLAS)
        fuentes = ["excel"]
        rep = self.siigo.get(fecha)
        if rep is not None and rep.puntos is not None and not rep.trae_punto(p["id"]):
            # Reporte de movimiento exportado para otros puntos: comparar daría
            # "todo lo del Excel falta en Siigo".
            rep = None
        if rep is not None:
            try:
                cx.mapeo = self.mapeo()
                cx.siigo = siigo_mod.unidades_punto(rep, p["id"], cx.mapeo)
                cx.siigo_archivo = rep.archivo
                cx.siigo_dias = self.siigo
                reglas += REGLAS_N2 + REGLAS_SIIGO_PAGOS
                fuentes.append("siigo")
                if not cx.siigo.por_clave and not cx.siigo.sin_mapeo:
                    avisos.append(f"El reporte de Siigo ({rep.archivo}) no trae ventas de este punto.")
            except Exception as e:
                avisos.append(f"No se pudo usar el reporte de Siigo: {e}")
        if fecha in self.banco.fechas:
            cx.banco = self.banco
            reglas += REGLAS_N3
            fuentes.append("banco")
        if self.tarjetas.cubre(fecha, p["id"]):
            cx.tarjetas = self.tarjetas
            reglas += REGLAS_TARJETAS
            fuentes.append("tarjetas")
        for regla in reglas:
            try:
                hallazgos.extend(regla(cx))
            except Exception as e:  # una regla rota nunca tumba la revisión
                avisos.append(f"La regla {regla.__name__.upper()} falló: {e}")

        # "Explica" nunca pasa del descuadre: una causa de $42.900 en un día de
        # +$30.100 explica $30.100 (el texto del hallazgo conserva el total).
        tope = abs(dia.caja.descuadre or 0.0)
        for h in hallazgos:
            if h.monto and abs(h.monto) > tope:
                h.monto = round(tope if h.monto > 0 else -tope, 2)

        prioridad = {r: k for k, r in enumerate(self.config["prioridad_reglas"])}
        orden_tipo = {"causa": 0, "señal": 1, "integridad": 2}
        orden_sev = {"alta": 0, "media": 1, "baja": 2, "info": 3}
        hallazgos.sort(key=lambda h: (orden_tipo.get(h.tipo, 9), -abs(h.monto),
                                      prioridad.get(h.regla, 99), orden_sev.get(h.severidad, 9)))

        descuadre = dia.caja.descuadre or 0.0
        tol = self.config["estado"]["tolerancia_cuadra"]
        causas = [h for h in hallazgos if h.tipo == "causa" and h.monto]
        # Las causas son hipótesis alternativas: se toma la que más explica, no
        # la suma. R05 (combinación de precios) se muestra pero no basta sola
        # para dar el día por explicado: casi cualquier monto redondo cuadra.
        sin_peso = set(self.config["estado"].get("reglas_sin_peso_en_estado", []))
        explicado = min(abs(descuadre), max((abs(h.monto) for h in causas if h.regla not in sin_peso),
                                            default=0.0))
        if abs(descuadre) <= tol:
            estado = "cuadra"
        elif explicado >= self.config["estado"]["porcentaje_para_explicado"] * abs(descuadre):
            estado = "explicado"
        else:
            estado = "sin explicar"
        principal = causas[0] if causas and abs(descuadre) > tol else None
        signo = 1 if descuadre >= 0 else -1

        return {
            "punto": p["id"], "nombre": p["nombre"], "fecha": fecha.isoformat(), "estado": estado,
            "hoja": dia.hoja, "archivo": libro.nombre,
            "asesoras": dia.asesoras, "venta": dia.caja.valor_teorico, "descuadre": descuadre,
            "explicado": signo * explicado, "sin_explicar": descuadre - signo * explicado,
            "causa_principal": ({"regla": principal.regla, "texto": principal.texto,
                                 "monto": principal.monto} if principal else None),
            "hallazgos": [h.to_dict() for h in hallazgos],
            "avisos": avisos,
            "fuentes": fuentes,
        }


def resumen_texto(resultado):
    """Para pruebas por consola."""
    lineas = [f"Revisión del {resultado['fecha']}"]
    for f in resultado["puntos"]:
        if f["descuadre"] is None:
            lineas.append(f"  {f['nombre']:<16} {f['estado']}")
            continue
        lineas.append(f"  {f['nombre']:<16} {pesos(f['descuadre']):>10}  {f['estado']:<12} "
                      f"{', '.join(f['asesoras'])}")
        for h in f["hallazgos"]:
            lineas.append(f"      [{h['regla']} {h['tipo']}/{h['severidad']} {pesos(h['monto'])}] {h['texto']}")
        for a in f["avisos"]:
            lineas.append(f"      AVISO: {a}")
    return "\n".join(lineas)
