# -*- coding: utf-8 -*-
"""
Lector de Google Sheets (fase 5): lee los Sheets de los 11 puntos directo de
Google Drive, sin descargarlos. Entrega el mismo LibroMensual que el lector
.xlsx, así que las reglas no cambian.

Autenticación: OAuth con la cuenta de Google del usuario (la carpeta "cierres
2026" se la compartieron, no es dueño), SOLO LECTURA:
  - drive.metadata.readonly: ver nombres de carpetas y archivos (no su contenido)
  - spreadsheets.readonly:   leer los Sheets
Las credenciales del proyecto de Google (el JSON que se descarga de Google Cloud)
y el permiso que da el usuario quedan en %APPDATA%\\SuiteIrina\\ para no pedir
inicio de sesión cada día.

Detección: carpeta "cierres <año>" → subcarpeta del mes (comparando sin tildes ni
mayúsculas) → cada Sheet a su punto por el nombre del archivo. El Sheet que
empieza por un número y dice "transferencias" es el de control de
transferencias, no un punto.
"""
import json
import os
import re
import shutil

from .lector_xlsx import LibroMensual, es_hoja_util
from .texto import norm

SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly",
          "https://www.googleapis.com/auth/spreadsheets.readonly"]
TIPO_CARPETA = "application/vnd.google-apps.folder"
TIPO_SHEET = "application/vnd.google-apps.spreadsheet"
RANGO_HOJA = "A1:BH400"          # 60 columnas x 400 filas, igual que el lector .xlsx
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
         "septiembre", "octubre", "noviembre", "diciembre"]


class ErrorGoogle(Exception):
    pass


def url_sheet(sheet_id):
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"


class Google:
    def __init__(self, carpeta_datos):
        self.ruta_cliente = os.path.join(carpeta_datos, "google_cliente.json")
        self.ruta_token = os.path.join(carpeta_datos, "google_permiso.json")
        self._cred = None
        self._servicios = {}

    # ------------------------------------------------------------------
    # Credenciales y permiso
    # ------------------------------------------------------------------
    def tiene_credenciales(self):
        return os.path.exists(self.ruta_cliente)

    def guardar_credenciales(self, ruta_json):
        """Valida el JSON descargado de Google Cloud (ID de cliente OAuth de tipo
        'App de escritorio') y lo copia a la carpeta de datos."""
        try:
            with open(ruta_json, encoding="utf-8") as f:
                datos = json.load(f)
        except (OSError, ValueError) as e:
            raise ErrorGoogle(f"No pude leer ese archivo: {e}")
        if "installed" not in datos:
            tipo = next(iter(datos), "desconocido") if isinstance(datos, dict) else "desconocido"
            raise ErrorGoogle("Ese JSON no es de un ID de cliente OAuth de tipo 'App de escritorio' "
                              f"(trae '{tipo}'). Créalo como 'App de escritorio' y vuelve a descargarlo.")
        os.makedirs(os.path.dirname(self.ruta_cliente), exist_ok=True)
        shutil.copyfile(ruta_json, self.ruta_cliente)
        self.desconectar()

    def _credenciales(self):
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        if self._cred is None and os.path.exists(self.ruta_token):
            try:
                self._cred = Credentials.from_authorized_user_file(self.ruta_token, SCOPES)
            except (OSError, ValueError):
                self._cred = None
        if self._cred and not self._cred.valid and self._cred.expired and self._cred.refresh_token:
            try:
                self._cred.refresh(Request())
                self._guardar_token()
            except Exception:
                self._cred = None    # permiso revocado o vencido: hay que volver a conectar
        return self._cred if self._cred and self._cred.valid else None

    def conectado(self):
        return self._credenciales() is not None

    def conectar(self):
        """Abre el navegador para que el usuario inicie sesión y dé permiso de
        solo lectura. Bloquea hasta que termina (máximo 5 minutos)."""
        if not self.tiene_credenciales():
            raise ErrorGoogle("Primero carga las credenciales (el JSON de Google Cloud).")
        from google_auth_oauthlib.flow import InstalledAppFlow
        flujo = InstalledAppFlow.from_client_secrets_file(self.ruta_cliente, SCOPES)
        try:
            self._cred = flujo.run_local_server(
                port=0, open_browser=True, timeout_seconds=300,
                authorization_prompt_message="",
                success_message="Listo. Suite Irina ya puede leer los Sheets (solo lectura). "
                                "Puedes cerrar esta pestaña y volver al programa.")
        except Exception as e:
            raise ErrorGoogle(f"No se completó el inicio de sesión: {e}")
        if not self._cred:
            raise ErrorGoogle("No se completó el inicio de sesión (¿se cerró el navegador?).")
        self._guardar_token()
        self._servicios = {}

    def _guardar_token(self):
        with open(self.ruta_token, "w", encoding="utf-8") as f:
            f.write(self._cred.to_json())

    def desconectar(self):
        self._cred = None
        self._servicios = {}
        if os.path.exists(self.ruta_token):
            os.remove(self.ruta_token)

    def _servicio(self, nombre, version):
        if (nombre, version) not in self._servicios:
            from googleapiclient.discovery import build
            cred = self._credenciales()
            if cred is None:
                raise ErrorGoogle("No hay conexión con Google. Dale 'Conectar con Google'.")
            self._servicios[(nombre, version)] = build(nombre, version, credentials=cred, cache_discovery=False)
        return self._servicios[(nombre, version)]

    def cuenta(self):
        try:
            info = self._servicio("drive", "v3").about().get(fields="user(emailAddress)").execute()
            return info.get("user", {}).get("emailAddress", "")
        except Exception:
            return ""

    # ------------------------------------------------------------------
    # Drive: carpetas y archivos
    # ------------------------------------------------------------------
    def _listar(self, q):
        drive = self._servicio("drive", "v3")
        out, token = [], None
        while True:
            r = drive.files().list(q=q, fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                                   pageSize=200, pageToken=token, supportsAllDrives=True,
                                   includeItemsFromAllDrives=True).execute()
            out += r.get("files", [])
            token = r.get("nextPageToken")
            if not token:
                return out

    def carpeta_del_anio(self, anio):
        candidatas = self._listar(f"mimeType='{TIPO_CARPETA}' and trashed=false and name contains 'cierres'")
        return elegir_carpeta_anio(candidatas, anio)

    def carpeta_del_mes(self, carpeta_anio_id, mes):
        hijas = self._listar(f"'{carpeta_anio_id}' in parents and mimeType='{TIPO_CARPETA}' and trashed=false")
        return elegir_carpeta_mes(hijas, mes)

    def sheets_de(self, carpeta_id):
        return self._listar(f"'{carpeta_id}' in parents and mimeType='{TIPO_SHEET}' and trashed=false")

    def archivo(self, file_id):
        return self._servicio("drive", "v3").files().get(
            fileId=file_id, fields="id, name, modifiedTime", supportsAllDrives=True).execute()

    # ------------------------------------------------------------------
    # Sheets: lectura
    # ------------------------------------------------------------------
    def _hojas(self, sheet_id):
        api = self._servicio("sheets", "v4")
        meta = api.spreadsheets().get(spreadsheetId=sheet_id, fields="sheets.properties.title").execute()
        return [s["properties"]["title"] for s in meta.get("sheets", [])]

    def _valores(self, sheet_id, titulos, render):
        if not titulos:
            return {}
        api = self._servicio("sheets", "v4")
        rangos = [f"'{t}'!{RANGO_HOJA}" for t in titulos]
        r = api.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id, ranges=rangos, valueRenderOption=render,
            dateTimeRenderOption="SERIAL_NUMBER", majorDimension="ROWS").execute()
        return {t: vr.get("values", []) for t, vr in zip(titulos, r.get("valueRanges", []))}

    def leer_libro(self, sheet_id, nombre):
        titulos = self._hojas(sheet_id)
        utiles = [t for t in titulos if es_hoja_util(t)]
        valores = self._valores(sheet_id, utiles, "UNFORMATTED_VALUE")
        formulas = self._valores(sheet_id, utiles, "FORMULA")
        return libro_desde_api(url_sheet(sheet_id), nombre, titulos, formulas, valores)

    def leer_filas(self, sheet_id, pred_titulo, rango="A1:CB60"):
        """{título: [filas]} de las hojas cuyo título cumple pred_titulo (para el
        Sheet de transferencias y su hoja URL)."""
        titulos = [t for t in self._hojas(sheet_id) if pred_titulo(t)]
        if not titulos:
            return {}
        api = self._servicio("sheets", "v4")
        r = api.spreadsheets().values().batchGet(
            spreadsheetId=sheet_id, ranges=[f"'{t}'!{rango}" for t in titulos],
            valueRenderOption="UNFORMATTED_VALUE", majorDimension="ROWS").execute()
        return {t: [tuple(v if v != "" else None for v in fila) for fila in vr.get("values", [])]
                for t, vr in zip(titulos, r.get("valueRanges", []))}


# ---------------------------------------------------------------------------
# Funciones puras (sin red): se prueban sin conexión
# ---------------------------------------------------------------------------
def a_grilla(filas):
    """values de la API (lista de filas) -> {(fila, col): valor}, base 1, sin vacíos."""
    g = {}
    for r, fila in enumerate(filas, 1):
        for c, v in enumerate(fila, 1):
            if v is not None and v != "":
                g[(r, c)] = v
    return g


def libro_desde_api(origen, nombre, titulos, formulas, valores):
    grillas_v = {t: a_grilla(f) for t, f in valores.items()}
    # Con FORMULA, una celda sin fórmula trae su valor: solo interesan las fórmulas.
    grillas_f = {t: {k: v for k, v in a_grilla(f).items() if isinstance(v, str) and v.startswith("=")}
                 for t, f in formulas.items()}
    return LibroMensual(origen, nombre, titulos, grillas_f, grillas_v)


def elegir_carpeta_anio(carpetas, anio):
    """'cierres 2026' entre las carpetas que dicen 'cierres'."""
    objetivo = f"cierres {anio}"
    exacta = [c for c in carpetas if norm(c["name"]) == objetivo]
    if exacta:
        return exacta[0]
    con_anio = [c for c in carpetas if str(anio) in norm(c["name"])]
    if len(con_anio) == 1:
        return con_anio[0]
    if not carpetas:
        raise ErrorGoogle(f"No encontré ninguna carpeta 'cierres' compartida contigo. Revisa que la "
                          f"cuenta conectada sea la que tiene acceso a 'cierres {anio}'.")
    nombres = ", ".join(c["name"] for c in carpetas[:6])
    raise ErrorGoogle(f"No encontré 'cierres {anio}'. Carpetas parecidas: {nombres}.")


def elegir_carpeta_mes(carpetas, mes):
    """Subcarpeta del mes: 'cierres agosto', 'CIERRES AGOSTO 2026', 'agosto'…"""
    nombre_mes = MESES[mes - 1]
    candidatas = [c for c in carpetas if re.search(rf"\b{nombre_mes}\b", norm(c["name"]))]
    if len(candidatas) == 1:
        return candidatas[0]
    if not candidatas:
        nombres = ", ".join(c["name"] for c in carpetas) or "ninguna"
        raise ErrorGoogle(f"No encontré la carpeta de {nombre_mes}. Subcarpetas que hay: {nombres}.")
    preferida = [c for c in candidatas if "cierre" in norm(c["name"])]
    return (preferida or candidatas)[0]


def es_sheet_transferencias(nombre):
    """'13. Transferencias septiembre_26': empieza por número y dice transferencias."""
    return bool(re.match(r"^\d+\s+transferencias\b", norm(nombre)))


def nombre_para_punto(nombre):
    """'01. Plaza Imperial Agosto/26' -> 'plaza imperial' (sin número, mes ni año)."""
    n = norm(nombre)
    n = re.sub(r"^\d+\s+", "", n)
    n = re.sub(r"\b(" + "|".join(MESES) + r")\b.*$", "", n)
    return n.strip()


def proponer_asignacion(sheets, identificar_punto, ids_puntos):
    """sheets: [{'id','name',...}] de la carpeta del mes.
    Devuelve {'puntos': {id_punto: sheet}, 'transferencias': sheet|None,
              'sin_asignar': [sheet], 'repetidos': {id_punto: [sheet, ...]}}."""
    out = {"puntos": {}, "transferencias": None, "sin_asignar": [], "repetidos": {}}
    for s in sorted(sheets, key=lambda x: x["name"]):
        if es_sheet_transferencias(s["name"]):
            if out["transferencias"] is None:
                out["transferencias"] = s
            else:
                out["sin_asignar"].append(s)
            continue
        pid = identificar_punto(nombre_para_punto(s["name"])) or identificar_punto(s["name"])
        if pid is None or pid not in ids_puntos:
            out["sin_asignar"].append(s)
        elif pid in out["puntos"]:
            out["repetidos"].setdefault(pid, [out["puntos"][pid]]).append(s)
        else:
            out["puntos"][pid] = s
    return out


def ids_desde_hoja_url(filas, identificar_punto):
    """Hoja 'URL' del Sheet de transferencias: columna B = punto, C = id del Sheet
    (o A = enlace completo). Devuelve {id_punto: id_sheet}."""
    out = {}
    for fila in filas:
        fila = list(fila) + [None] * 3
        punto = identificar_punto(str(fila[1])) if fila[1] else None
        if not punto:
            continue
        sid = str(fila[2]).strip() if fila[2] else ""
        if not re.fullmatch(r"[A-Za-z0-9_-]{20,}", sid):
            m = re.search(r"/spreadsheets/d/([A-Za-z0-9_-]+)", str(fila[0] or ""))
            sid = m.group(1) if m else ""
        if sid:
            out[punto] = sid
    return out
