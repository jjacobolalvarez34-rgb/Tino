# -*- coding: utf-8 -*-
"""Trae las facturas de venta de Siigo Nube por su API y las deja en la forma de Tino.

Documentación: docs/FUENTES/facturacion_api.md. Se entra con el usuario y la llave de
acceso que da Siigo (Alianzas → Mi credencial API) y un Partner-Id. El token dura 24 h.

De qué punto es cada factura lo dice el perfil de la empresa (perfil_fuente 'siigo'):
    {"campo": "cost_center" | "warehouse" | "prefix" | "document", "puntos": {"<valor>": "<código del punto>"}}
Así sirve para cualquier empresa, la use como la use. Lo que no se puede ubicar no se
inventa: queda como error por resolver.

La conversación con Siigo pasa por `transporte`, que se puede cambiar en las pruebas.
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "motores"))
from nucleo.logica import a_pesos  # noqa: E402

URL = "https://api.siigo.com"
CAMPOS = {"cost_center": "Centro de costo", "warehouse": "Bodega", "prefix": "Prefijo de la factura",
          "document": "Tipo de documento"}


class ErrorSiigo(Exception):
    pass


def _http(metodo, url, cabeceras, cuerpo=None):
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    pedido = urllib.request.Request(url, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        texto = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, {"mensaje": texto[:300]}
    except urllib.error.URLError as e:
        raise ErrorSiigo(f"No hay conexión con Siigo: {e.reason}") from None


def pesos(valor):
    """Siigo manda decimales (35900.0): se pasan a pesos enteros sin float."""
    if valor is None:
        return 0
    return a_pesos(format(Decimal(str(valor)), "f")) or 0


class Siigo:
    def __init__(self, usuario, llave, partner_id, transporte=_http, url=URL):
        if not (usuario and llave and partner_id):
            raise ErrorSiigo("Faltan el usuario, la llave de acceso o el Partner-Id de Siigo.")
        self.usuario, self.llave, self.partner = usuario, llave, partner_id
        self.transporte, self.url = transporte, url.rstrip("/")
        self.token, self.vence = None, 0

    def _entrar(self):
        estado, r = self.transporte("POST", f"{self.url}/auth",
                                    {"Content-Type": "application/json", "Partner-Id": self.partner},
                                    {"username": self.usuario, "access_key": self.llave})
        if estado != 200 or not (r or {}).get("access_token"):
            raise ErrorSiigo("Siigo no aceptó el usuario, la llave o el Partner-Id. Revíselos en Siigo Nube → "
                             "Alianzas → Mi credencial API.")
        self.token = r["access_token"]
        self.vence = time.time() + int(r.get("expires_in", 86400)) - 300

    def pedir(self, ruta, params=None):
        if not self.token or time.time() > self.vence:
            self._entrar()
        url = f"{self.url}{ruta}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
        cab = {"Authorization": f"Bearer {self.token}", "Partner-Id": self.partner,
               "Content-Type": "application/json"}
        for intento in range(4):
            estado, r = self.transporte("GET", url, cab)
            if estado == 429:  # muchas peticiones seguidas: se espera y se vuelve a intentar
                time.sleep(2 ** intento * 5)
                continue
            if estado == 401 and intento == 0:
                self._entrar()
                cab["Authorization"] = f"Bearer {self.token}"
                continue
            if estado >= 400:
                detalle = (r or {}).get("Errors") or (r or {}).get("mensaje") or r
                raise ErrorSiigo(f"Siigo respondió {estado} en {ruta}: {str(detalle)[:200]}")
            return r
        raise ErrorSiigo("Siigo sigue pidiendo esperar. Intente en unos minutos.")

    def probar(self):
        self._entrar()
        return True

    def facturas(self, desde, hasta, avance=None):
        """Todas las facturas de venta con fecha entre desde y hasta (AAAA-MM-DD), los dos incluidos.

        En Siigo `date_end` no incluye ese día (probado con octubre de 2026: pedir del 1 al 7
        devolvía solo hasta el 6). Por eso se pide hasta el día siguiente y se filtra aquí."""
        import datetime as _dt
        fin = (_dt.date.fromisoformat(hasta) + _dt.timedelta(days=1)).isoformat()
        salida, pagina = [], 1
        while True:
            r = self.pedir("/v1/invoices", {"date_start": desde, "date_end": fin, "page": pagina, "page_size": 100})
            resultados = (r or {}).get("results", [])
            salida += resultados
            total = ((r or {}).get("pagination") or {}).get("total_results", len(salida))
            if avance:
                avance(len(salida), total)
            if not resultados or len(salida) >= total:
                return [f for f in salida if desde <= str(f.get("date", ""))[:10] <= hasta]
            pagina += 1

    def catalogo(self, campo):
        """Nombres de centros de costo, bodegas o tipos de documento, para mostrarlos. Si falla, vacío."""
        ruta = {"cost_center": "/v1/cost-centers", "warehouse": "/v1/warehouses",
                "document": "/v1/document-types?type=FV"}.get(campo)
        if not ruta:
            return {}
        try:
            r = self.pedir(ruta)
        except ErrorSiigo:
            return {}
        filas = r if isinstance(r, list) else (r or {}).get("results", [])
        return {str(x.get("id")): f"{x.get('code', '')} {x.get('name', '')}".strip() for x in filas if isinstance(x, dict)}


def valor_de(factura, campo):
    """El valor con que se reconoce el punto de una factura, según el campo del perfil."""
    if campo == "cost_center":
        v = factura.get("cost_center")
    elif campo == "warehouse":
        v = next(((i.get("warehouse") or {}).get("id") for i in factura.get("items", []) if i.get("warehouse")), None)
    elif campo == "prefix":
        v = factura.get("prefix") or (str(factura.get("name", "")).rsplit("-", 1)[0] or None)
    elif campo == "document":
        v = (factura.get("document") or {}).get("id")
    else:
        v = None
    return None if v in (None, "") else str(v)


def valores_encontrados(facturas, campo):
    """Cada valor del campo y cuántas facturas lo tienen, para armar el perfil en pantalla."""
    cuenta = {}
    for f in facturas:
        v = valor_de(f, campo)
        if v is not None:
            cuenta[v] = cuenta.get(v, 0) + 1
    return cuenta


def normalizar(facturas, perfil, punto_por_codigo, producto_por_codigo, desde, hasta):
    """La carga para importar_facturas: cada factura con su punto, en pesos enteros."""
    campo, mapa = perfil.get("campo"), perfil.get("puntos", {})
    salida, errores = [], []
    for i, f in enumerate(facturas, start=1):
        clave = valor_de(f, campo)
        codigo = mapa.get(clave) if clave is not None else None
        punto_id = punto_por_codigo.get(codigo) if codigo else None
        numero = f.get("name") or f"{f.get('prefix', '')}-{f.get('number', '')}"
        if punto_id is None:
            errores.append({"fila_origen": i, "tipo": "otro",
                            "texto": f"{numero}: {CAMPOS.get(campo, 'campo')} {clave or 'vacío'} sin punto asignado"})
            continue
        items = []
        for it in f.get("items", []):
            descuento = it.get("discount") or {}
            items.append({"producto_id": producto_por_codigo.get(str(it.get("code") or "")),
                          "texto_producto": it.get("description") or str(it.get("code") or ""),
                          "cantidad": int(Decimal(str(it.get("quantity") or 0))), "precio": pesos(it.get("price")),
                          "valor": pesos(it.get("total")), "descuento": pesos(descuento.get("value"))})
        salida.append({"id_origen": str(f.get("id")), "numero": numero, "punto_id": punto_id,
                       "fecha": str(f.get("date"))[:10], "total": pesos(f.get("total")),
                       "descuento": sum(x["descuento"] for x in items),
                       "anulada": bool(f.get("annulled")), "vendedor": None if f.get("seller") is None else str(f.get("seller")),
                       "pagos": [{"nombre": p.get("name") or str(p.get("id")), "valor": pesos(p.get("value"))}
                                 for p in f.get("payments", [])],
                       "items": items})
    huella = hashlib.sha256(json.dumps([(f["id_origen"], f["anulada"], f["total"]) for f in salida] +
                                       [desde, hasta], sort_keys=True).encode()).hexdigest()
    return {"fuente": "siigo", "nombre": f"Siigo {desde} a {hasta}", "hash": huella, "desde": desde, "hasta": hasta,
            "facturas": salida, "errores": errores}
