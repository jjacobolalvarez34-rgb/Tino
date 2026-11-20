# -*- coding: utf-8 -*-
"""Prueba de punta a punta de la cola (D-057) en tino-pruebas, con la empresa de demostración
(datos inventados) y la empresa B de las pruebas:

  1. La dueña demo sube a Storage un archivo inventado y lo deja en cola.
  2. El mismo archivo no entra dos veces a la cola.
  3. B no puede bajar el archivo de la demo ni verlo en la cola.
  4. El procesador del programa de escritorio (Servicio.procesar_cola) lo toma y lo deja con su
     resultado (este archivo no es un Excel del día: debe quedar "error" con su mensaje).

Uso: python tests/web/probar_cola.py <archivo de contraseñas fuera del repo>
"""
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "tests" / "rls")]
import probar_supabase as base  # noqa: E402
from probar_supabase import PUBLICA, URL, ok  # noqa: E402
from panel.datos.cliente import Cliente  # noqa: E402
from panel.servicio import Servicio  # noqa: E402

DEMO = "dddddddd-0000-4000-8000-000000000001"


def entrar(correo, clave):
    c = Cliente(URL, PUBLICA)
    c.iniciar_sesion(correo, clave)
    return c


def subir_objeto(cli, ruta, datos):
    pedido = urllib.request.Request(f"{URL}/storage/v1/object/archivos/{ruta}", data=datos, method="POST",
                                    headers={"apikey": PUBLICA, "Authorization": f"Bearer {cli.token}",
                                             "Content-Type": "text/csv", "x-upsert": "false"})
    try:
        with urllib.request.urlopen(pedido, timeout=60) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    claves = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    demo = entrar(claves["demo.dueno"]["correo"], claves["demo.dueno"]["contrasena"])
    otra = entrar("dueno.b@prueba-tino.example.com", claves["dueno.b"]["contrasena"])

    datos = f"columna,valor\nprueba de cola,{int(time.time())}\n".encode()
    huella = hashlib.sha256(datos).hexdigest()
    ruta = f"{DEMO}/{huella}/prueba-cola.csv"
    ok(subir_objeto(demo, ruta, datos) in (200, 201), "La dueña demo sube el archivo a la carpeta de su empresa")
    ok(subir_objeto(demo, f"bbbbbbbb-0000-4000-8000-000000000001/{huella}/x.csv", datos) >= 400,
       "No puede subir a la carpeta de otra empresa")
    fila = demo.crear("archivo_en_cola", {"empresa_id": DEMO, "ruta": ruta, "nombre": "prueba-cola.csv",
                                          "tamano": len(datos), "hash": huella})[0]
    ok(fila["estado"] == "en_cola", "Queda en cola")
    try:
        demo.crear("archivo_en_cola", {"empresa_id": DEMO, "ruta": ruta, "nombre": "otra vez.csv", "tamano": len(datos), "hash": huella})
        ok(False, "El mismo archivo no entra dos veces a la cola")
    except Exception as e:  # noqa: BLE001
        ok(getattr(e, "codigo", "") == "23505", "El mismo archivo no entra dos veces a la cola", e)
    try:
        otra.bajar("archivos", ruta)
        ok(False, "B no baja el archivo de la demo")
    except Exception:  # noqa: BLE001
        ok(True, "B no baja el archivo de la demo")
    ok(not otra.leer("archivo_en_cola", [("id", "eq", fila["id"])], "id"), "B no ve la cola de la demo")

    servicio = Servicio(demo, carpeta=None)
    servicio.entrar()
    resumen = servicio.procesar_cola()
    final = demo.leer("archivo_en_cola", [("id", "eq", fila["id"])], "estado,mensaje,procesado_por")[0]
    ok(final["estado"] == "error" and final["mensaje"] and final["procesado_por"] == claves["demo.dueno"]["id"],
       "El programa lo procesa y deja el error con su mensaje y quién lo procesó", (resumen, final))

    print(f"\nResultado: {base.bien} bien, {len(base.fallas)} fallas")
    sys.exit(1 if base.fallas else 0)


if __name__ == "__main__":
    main()
