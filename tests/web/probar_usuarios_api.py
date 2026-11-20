# -*- coding: utf-8 -*-
"""Prueba la API de Usuarios (web/app/api/usuarios) con las empresas inventadas de
tests/rls/probar_supabase.py. Crea un usuario con rol dueño SIN invitarlo: no se manda ningún
correo. Como nada se borra, el usuario de prueba se queda (con un correo @prueba-tino.example.com).

Uso: python tests/web/probar_usuarios_api.py <url de la web, p. ej. http://localhost:6001> <contraseñas fuera del repo>
"""
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rls"))
from probar_supabase import PUBLICA, URL, ok  # noqa: E402
import probar_supabase as base  # noqa: E402

WEB = sys.argv[1].rstrip("/")


def token(usuarios, clave):
    rol, letra = clave.split(".")
    correo = f"{clave}@prueba-tino.example.com" if rol in ("lider", "responsable") else f"{rol}.{letra}@prueba-tino.example.com"
    datos = json.dumps({"email": correo, "password": usuarios[clave]["contrasena"]}).encode()
    pedido = urllib.request.Request(URL + "/auth/v1/token?grant_type=password", data=datos,
                                    headers={"apikey": PUBLICA, "Content-Type": "application/json"})
    with urllib.request.urlopen(pedido, timeout=30) as r:
        return json.loads(r.read())["access_token"]


def api(tok, metodo="GET", cuerpo=None):
    pedido = urllib.request.Request(WEB + "/api/usuarios", method=metodo,
                                    data=None if cuerpo is None else json.dumps(cuerpo).encode(),
                                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(pedido, timeout=90) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def main():
    usuarios = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    d_a, d_b, ases_a = token(usuarios, "dueno.a"), token(usuarios, "dueno.b"), token(usuarios, "asesora.a")
    estado, r = api(d_a)
    ok(estado == 200 and r["usuarios"], "El dueño de A ve los usuarios de su empresa", (estado, r))
    antes = {u["id"] for u in r["usuarios"]}
    estado, r = api(d_b)
    ok(estado == 200 and not antes & {u["id"] for u in r["usuarios"]}, "El dueño de B no ve a ningún usuario de A")
    estado, r = api(ases_a)
    ok(estado == 403, "La asesora no administra usuarios", estado)
    estado, r = api("", "GET")
    ok(estado == 401, "Sin sesión no se entra", estado)

    marca = str(int(time.time()))[-6:]
    correo = f"dueno-nuevo-{marca}@prueba-tino.example.com"
    estado, r = api(d_a, "POST", {"accion": "crear", "correo": correo, "nombre": "Dueña Nueva Prueba", "rol": "dueno"})
    ok(estado == 200 and r.get("id"), "El dueño crea un usuario con rol dueño, sin invitarlo", (estado, r))
    nuevo = r.get("id")
    estado, r = api(d_a)
    fila = next((u for u in r["usuarios"] if u["id"] == nuevo), None)
    ok(fila and fila["rol"] == "dueno" and fila["activo"] and not fila["invitado_en"] and not fila["ultimo_ingreso"],
       "Queda activo y sin invitar (no se mandó ningún correo)", fila)
    estado, r = api(d_a, "POST", {"accion": "crear", "correo": correo, "nombre": "Otra", "rol": "dueno"})
    ok(estado == 400, "El mismo correo no se crea dos veces", (estado, r))
    estado, r = api(d_a, "POST", {"accion": "crear", "correo": f"x{marca}@prueba-tino.example.com", "nombre": "Sin Punto",
                                  "rol": "responsable_punto"})
    ok(estado == 400, "Un responsable de punto necesita su punto", (estado, r))
    estado, r = api(d_b, "POST", {"accion": "desactivar", "id": nuevo})
    ok(estado == 404, "B no desactiva a un usuario de A", (estado, r))
    estado, r = api(d_a, "POST", {"accion": "desactivar", "id": nuevo})
    ok(estado == 200, "El dueño lo desactiva", (estado, r))
    estado, r = api(d_a, "POST", {"accion": "activar", "id": nuevo})
    ok(estado == 200, "Y lo activa otra vez", (estado, r))
    yo = next(u for u in api(d_a)[1]["usuarios"] if u["es_yo"])
    estado, r = api(d_a, "POST", {"accion": "desactivar", "id": yo["id"]})
    ok(estado == 400, "Nadie se desactiva a sí mismo", (estado, r))

    print(f"\nResultado: {base.bien} bien, {len(base.fallas)} fallas")
    sys.exit(1 if base.fallas else 0)


if __name__ == "__main__":
    main()
