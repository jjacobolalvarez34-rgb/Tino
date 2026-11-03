# -*- coding: utf-8 -*-
"""Habla con la base por su API (PostgREST), con la sesión de quien usa el programa.

Nunca usa la llave de servicio: cada consulta va con el token del usuario, así RLS
decide qué ve y qué puede cambiar, igual que en la web. En Supabase la API está en
<url>/rest/v1 y el inicio de sesión en <url>/auth/v1. Para probar en este PC sirve un
PostgREST local con un token ya firmado (ver tests/local/).
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

PAGINA = 1000  # Supabase devuelve como máximo 1000 filas por consulta.

# Lo que la base responde, dicho para una persona.
MENSAJES = {
    "23505": "Eso ya estaba cargado: el mismo archivo no entra dos veces.",
    "23503": "Hay un dato que apunta a algo que no existe o es de otra empresa.",
    "23514": "Hay un dato que no cumple las reglas.",
    "42501": "Su usuario no tiene permiso para esto.",
    "P0002": "No se encontró, o ya se había hecho.",
}


class ErrorBase(Exception):
    def __init__(self, mensaje, codigo=None, detalle=""):
        super().__init__(mensaje)
        self.codigo, self.detalle = codigo, detalle


class Cliente:
    def __init__(self, url=None, llave="", rest=None, token=None):
        self.url = (url or "").rstrip("/")
        self.llave = llave
        self.rest = (rest or f"{self.url}/rest/v1").rstrip("/")
        self.token, self.refresco, self.vence, self.usuario = token, None, None, None

    # Sesión ------------------------------------------------------------------
    def iniciar_sesion(self, correo, clave):
        r = self._pedir("POST", f"{self.url}/auth/v1/token?grant_type=password",
                        {"email": correo, "password": clave}, con_token=False)
        self._guardar_sesion(r)
        return self.usuario

    def _guardar_sesion(self, r):
        self.token, self.refresco = r["access_token"], r.get("refresh_token")
        self.vence = time.time() + int(r.get("expires_in", 3600)) - 60
        self.usuario = r.get("user", {}).get("id")

    def _renovar_si_vence(self):
        if self.refresco and self.vence and time.time() > self.vence:
            r = self._pedir("POST", f"{self.url}/auth/v1/token?grant_type=refresh_token",
                            {"refresh_token": self.refresco}, con_token=False)
            self._guardar_sesion(r)

    # Consultas ---------------------------------------------------------------
    def leer(self, tabla, filtros=(), columnas="*", orden="id"):
        """Todas las filas que RLS deja ver, de a páginas. filtros: (columna, operador, valor)."""
        filas, desde = [], 0
        while True:
            q = [("select", columnas), ("order", orden), ("limit", PAGINA), ("offset", desde)]
            q += [(col, f"{op}.{valor}") for col, op, valor in filtros]
            pagina = self._pedir("GET", f"{self.rest}/{tabla}?{urllib.parse.urlencode(q)}")
            filas += pagina
            if len(pagina) < PAGINA:
                return filas
            desde += PAGINA

    def rpc(self, funcion, argumentos):
        return self._pedir("POST", f"{self.rest}/rpc/{funcion}", argumentos)

    def crear(self, tabla, filas):
        return self._pedir("POST", f"{self.rest}/{tabla}", filas, prefer="return=representation")

    def cambiar(self, tabla, filtros, valores):
        q = urllib.parse.urlencode([(col, f"{op}.{valor}") for col, op, valor in filtros])
        return self._pedir("PATCH", f"{self.rest}/{tabla}?{q}", valores, prefer="return=representation")

    # Red ---------------------------------------------------------------------
    def _pedir(self, metodo, url, cuerpo=None, con_token=True, prefer=None):
        if con_token:
            self._renovar_si_vence()
        cabeceras = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.llave:
            cabeceras["apikey"] = self.llave
        if con_token and self.token:
            cabeceras["Authorization"] = f"Bearer {self.token}"
        if prefer:
            cabeceras["Prefer"] = prefer
        datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
        pedido = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
        try:
            with urllib.request.urlopen(pedido, timeout=120) as r:
                texto = r.read().decode("utf-8")
                return json.loads(texto) if texto else None
        except urllib.error.HTTPError as e:
            texto = e.read().decode("utf-8", "replace")
            try:
                info = json.loads(texto)
            except ValueError:
                info = {}
            codigo = info.get("code") or info.get("error_code")
            if e.code in (400, 401) and "auth/v1" in url:
                raise ErrorBase("Correo o clave incorrectos.", codigo, texto) from None
            mensaje = MENSAJES.get(codigo) or info.get("message") or info.get("msg") or f"Error {e.code}"
            raise ErrorBase(mensaje, codigo, info.get("message") or texto) from None
        except urllib.error.URLError as e:
            raise ErrorBase("No hay conexión con la base. Revise el internet.", None, str(e.reason)) from None
