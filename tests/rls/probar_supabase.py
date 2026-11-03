# -*- coding: utf-8 -*-
"""Prueba la separación entre empresas en Supabase, por el camino real.

Entra con usuarios de verdad y la llave pública, igual que el programa. Crea dos
empresas inventadas con un usuario de cada rol; como nada se borra, se quedan ahí.
Sirve correrla varias veces: los usuarios se reutilizan.

Uso: python tests/rls/probar_supabase.py <archivo para las contraseñas, fuera del repo>
Lee las llaves de .env. Nunca imprime llaves, contraseñas ni tokens.
"""
import json
import secrets
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
ENV = dict(linea.split("=", 1) for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in linea)
URL, PUBLICA, SECRETA = ENV["SUPABASE_URL"].rstrip("/"), ENV["SUPABASE_ANON_KEY"], ENV["SUPABASE_SERVICE_ROLE_KEY"]
ROLES = ("dueno", "encargada", "finanzas", "asesora", "soporte")
EMPRESAS = {"a": "aaaaaaaa-0000-4000-8000-000000000001", "b": "bbbbbbbb-0000-4000-8000-000000000001"}
PUNTOS = {"a": "aaaaaaaa-0000-4000-8000-000000000011", "b": "bbbbbbbb-0000-4000-8000-000000000011"}
fallas = []
bien = 0


def pedir(metodo, ruta, llave, token=None, cuerpo=None, prefer=None):
    cabeceras = {"apikey": llave, "Content-Type": "application/json"}
    if token:
        cabeceras["Authorization"] = f"Bearer {token}"
    if prefer:
        cabeceras["Prefer"] = prefer
    datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
    pedido = urllib.request.Request(URL + ruta, data=datos, headers=cabeceras, method=metodo)
    try:
        with urllib.request.urlopen(pedido, timeout=30) as r:
            texto = r.read().decode("utf-8")
            return r.status, json.loads(texto) if texto else None
    except urllib.error.HTTPError as e:
        texto = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(texto)
        except ValueError:
            return e.code, {"message": texto[:120]}


def ok(condicion, prueba, detalle=""):
    global bien
    if condicion:
        bien += 1
        print(f"OK     {prueba}")
    else:
        fallas.append(prueba)
        print(f"FALLA  {prueba} {str(detalle)[:110]}")


def ver(tabla, token, consulta="select=*"):
    return pedir("GET", f"/rest/v1/{tabla}?{consulta}", PUBLICA, token)[1]


def rechaza(respuesta, codigo, prueba):
    estado, cuerpo = respuesta
    ok(estado >= 400 and isinstance(cuerpo, dict) and cuerpo.get("code") == codigo, prueba, (estado, cuerpo))


def preparar(archivo):
    """Crea lo que falte como administrador y devuelve el id y la clave de cada usuario."""
    usuarios = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    for letra, empresa in EMPRESAS.items():
        estado, r = pedir("POST", "/rest/v1/empresa?on_conflict=id", SECRETA,
                          cuerpo={"id": empresa, "nombre": f"Prueba {letra.upper()}"},
                          prefer="resolution=ignore-duplicates,return=minimal")
        assert estado < 300, (estado, r)
        estado, r = pedir("POST", "/rest/v1/punto_venta?on_conflict=id", SECRETA,
                          cuerpo={"id": PUNTOS[letra], "empresa_id": empresa, "codigo": "P01",
                                  "nombre": f"Punto {letra.upper()}1"},
                          prefer="resolution=ignore-duplicates,return=minimal")
        assert estado < 300, (estado, r)
        for rol in ROLES:
            clave = f"{rol}.{letra}"
            if clave not in usuarios:
                contrasena = secrets.token_urlsafe(24)
                estado, r = pedir("POST", "/auth/v1/admin/users", SECRETA, cuerpo={
                    "email": f"{rol}.{letra}@prueba-tino.example.com", "password": contrasena, "email_confirm": True})
                assert estado < 300, (estado, r)
                usuarios[clave] = {"id": r["id"], "contrasena": contrasena}
                archivo.write_text(json.dumps(usuarios, indent=1), encoding="utf-8")
            estado, r = pedir("POST", "/rest/v1/usuario?on_conflict=id", SECRETA,
                              cuerpo={"id": usuarios[clave]["id"], "empresa_id": empresa,
                                      "nombre": f"{rol.capitalize()} {letra.upper()}", "rol": rol},
                              prefer="resolution=ignore-duplicates,return=minimal")
            assert estado < 300, (estado, r)
    return usuarios


def entrar(usuarios):
    tokens = {}
    for clave, u in usuarios.items():
        rol, letra = clave.split(".")
        estado, r = pedir("POST", "/auth/v1/token?grant_type=password", PUBLICA, cuerpo={
            "email": f"{rol}.{letra}@prueba-tino.example.com", "password": u["contrasena"]})
        assert estado == 200, (clave, estado, r.get("msg") or r.get("error_description"))
        tokens[clave] = r["access_token"]
        time.sleep(0.2)
    return tokens


def main():
    usuarios = preparar(Path(sys.argv[1]))
    t = entrar(usuarios)
    marca = str(int(time.time()))[-6:]
    a, b = EMPRESAS["a"], EMPRESAS["b"]
    punto_a, punto_b = PUNTOS["a"], PUNTOS["b"]

    # Separación entre empresas
    for clave, token in t.items():
        filas = ver("empresa", token)
        letra = clave.split(".")[1]
        ok(len(filas) == 1 and filas[0]["id"] == EMPRESAS[letra], f"{clave} solo ve su empresa", filas)
        puntos = ver("punto_venta", token)
        ok(all(p["empresa_id"] == EMPRESAS[letra] for p in puntos) and puntos, f"{clave} solo ve sus puntos", len(puntos))

    d_a = t["dueno.a"]
    rechaza(pedir("POST", "/rest/v1/punto_venta", PUBLICA, d_a,
                  {"empresa_id": b, "codigo": f"X{marca}", "nombre": "Intruso"}), "42501",
            "El dueño de A no crea puntos en B")
    estado, r = pedir("PATCH", f"/rest/v1/punto_venta?id=eq.{punto_b}", PUBLICA, d_a,
                      {"nombre": "Hackeado"}, "return=representation")
    ok(r == [], "El dueño de A no cambia puntos de B", r)
    rechaza(pedir("PATCH", f"/rest/v1/punto_venta?id=eq.{punto_a}", PUBLICA, d_a, {"empresa_id": b}), "42501",
            "Un punto no se puede mover a otra empresa")
    rechaza(pedir("POST", "/rest/v1/terminal_datafono", PUBLICA, d_a,
                  {"empresa_id": a, "punto_id": punto_b, "proveedor": "bold", "codigo_terminal": f"T{marca}",
                   "activo_desde": "2026-01-01"}), "23503", "Un datáfono de A no apunta a un punto de B")
    rechaza(pedir("POST", "/rest/v1/codigo_recaudo", PUBLICA, d_a,
                  {"empresa_id": a, "punto_id": punto_b, "codigo": f"99{marca}", "activo_desde": "2026-01-01"}),
            "23503", "Un código de pago de A no apunta a un punto de B")

    # Nadie borra
    for clave, token in t.items():
        estado, r = pedir("DELETE", f"/rest/v1/punto_venta?id=eq.{PUNTOS[clave.split('.')[1]]}", PUBLICA, token,
                          prefer="return=representation")
        ok(r == [], f"{clave} no borra puntos", r)

    # Plan y estado
    rechaza(pedir("PATCH", f"/rest/v1/empresa?id=eq.{a}", PUBLICA, d_a, {"plan": "completo"}), "42501",
            "El dueño no se sube de plan")
    rechaza(pedir("PATCH", f"/rest/v1/empresa?id=eq.{a}", PUBLICA, d_a, {"estado": "activa"}), "42501",
            "El dueño no cambia el estado de su empresa")

    # Roles
    estado, r = pedir("POST", "/rest/v1/punto_venta", PUBLICA, t["encargada.a"],
                      {"empresa_id": a, "codigo": f"E{marca}", "nombre": "Punto de la encargada"}, "return=minimal")
    ok(estado == 201, "La encargada crea puntos en su empresa", (estado, r))
    rechaza(pedir("POST", "/rest/v1/perfil_fuente", PUBLICA, t["encargada.a"],
                  {"empresa_id": a, "fuente": "banco", "nombre": f"E{marca}"}), "42501",
            "La encargada no configura perfiles de fuente")
    rechaza(pedir("POST", "/rest/v1/punto_venta", PUBLICA, t["asesora.a"],
                  {"empresa_id": a, "codigo": f"S{marca}", "nombre": "x"}), "42501", "La asesora no edita maestros")
    rechaza(pedir("POST", "/rest/v1/punto_venta", PUBLICA, t["finanzas.a"],
                  {"empresa_id": a, "codigo": f"F{marca}", "nombre": "x"}), "42501", "Finanzas no edita maestros")
    ok(len(ver("usuario", t["asesora.a"])) == 1, "La asesora solo se ve a sí misma")
    ok(len(ver("usuario", t["finanzas.a"])) == 1, "Finanzas no ve la lista de usuarios")
    ok(len(ver("usuario", d_a)) == 5, "El dueño ve los 5 usuarios de su empresa y ninguno de B")

    # Auditoría
    nombre = f"Punto A1 {marca}"
    estado, r = pedir("PATCH", f"/rest/v1/punto_venta?id=eq.{punto_a}", PUBLICA, d_a, {"nombre": nombre}, "return=minimal")
    ok(estado == 204, "El dueño cambia un punto suyo", (estado, r))
    filas = ver("auditoria", d_a, f"select=accion,despues,usuario_id&registro_id=eq.{punto_a}&accion=eq.update&order=id.desc&limit=1")
    ok(filas and filas[0]["despues"]["nombre"] == nombre and filas[0]["usuario_id"] == usuarios["dueno.a"]["id"],
       "El cambio queda en auditoría, con quién lo hizo", filas)
    ok(ver("auditoria", t["encargada.a"]) == [], "La encargada no ve la auditoría")
    ok(ver("auditoria", t["finanzas.a"]) == [], "Finanzas no ve la auditoría")
    ok(ver("auditoria", t["dueno.b"], f"select=id&empresa_id=eq.{a}") == [], "El dueño de B no ve la auditoría de A")
    rechaza(pedir("POST", "/rest/v1/auditoria", PUBLICA, d_a, {"tabla": "x", "accion": "insert"}), "42501",
            "Nadie escribe a mano en la auditoría")

    # Configuración
    filas = ver("empresa_config", d_a)
    ok(len(filas) == 1 and filas[0]["empresa_id"] == a, "La empresa nació con su configuración", filas)

    # Sin sesión
    for tabla in ("empresa", "usuario", "punto_venta", "auditoria", "empresa_config"):
        ok(pedir("GET", f"/rest/v1/{tabla}?select=*", PUBLICA)[1] == [], f"Sin sesión no se ve {tabla}")
    rechaza(pedir("POST", "/rest/v1/punto_venta", PUBLICA, None,
                  {"empresa_id": a, "codigo": f"N{marca}", "nombre": "x"}), "42501", "Sin sesión no se escribe")

    registro = pedir("GET", "/auth/v1/settings", PUBLICA)[1]
    print("\nRegistro de usuarios abierto:", not registro.get("disable_signup"))
    print(f"\nResultado: {bien} bien, {len(fallas)} fallas")
    for falla in fallas:
        print("  ", falla)
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
