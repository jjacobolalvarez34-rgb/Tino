# -*- coding: utf-8 -*-
"""Prueba Equipo (0011) en Supabase con dos empresas inventadas y configuraciones distintas.

Usa las empresas, puntos y usuarios de probar_supabase.py y agrega un lider y un
responsable de punto en A, un lider en B y un segundo punto en A. B se configura distinto
(otras palabras, otros umbrales, otro criterio) y se comprueba que ninguna ve lo de la otra
y que cada rol ve solo lo que le toca. Como nada se borra, lo creado se queda.

Uso: python tests/rls/probar_equipo_supabase.py <archivo de contraseñas, fuera del repo>
Nunca imprime llaves, contraseñas ni tokens.
"""
import json
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import probar_supabase as base  # noqa: E402
from probar_supabase import EMPRESAS, PUBLICA, PUNTOS, SECRETA, ok, pedir, rechaza, ver  # noqa: E402

PUNTO_A2 = "aaaaaaaa-0000-4000-8000-000000000012"
EXTRA = {"lider.a": ("lider", "a", None), "responsable.a": ("responsable_punto", "a", PUNTOS["a"]),
         "lider.b": ("lider", "b", None)}


def preparar_extra(archivo, usuarios):
    estado, r = pedir("POST", "/rest/v1/punto_venta?on_conflict=id", SECRETA,
                      cuerpo={"id": PUNTO_A2, "empresa_id": EMPRESAS["a"], "codigo": "P02", "nombre": "Punto A2"},
                      prefer="resolution=ignore-duplicates,return=minimal")
    assert estado < 300, (estado, r)
    for clave, (rol, letra, punto) in EXTRA.items():
        if clave not in usuarios:
            contrasena = secrets.token_urlsafe(24)
            estado, r = pedir("POST", "/auth/v1/admin/users", SECRETA, cuerpo={
                "email": f"{clave}@prueba-tino.example.com", "password": contrasena, "email_confirm": True})
            assert estado < 300, (estado, r)
            usuarios[clave] = {"id": r["id"], "contrasena": contrasena}
            archivo.write_text(json.dumps(usuarios, indent=1), encoding="utf-8")
        estado, r = pedir("POST", "/rest/v1/usuario?on_conflict=id", SECRETA,
                          cuerpo={"id": usuarios[clave]["id"], "empresa_id": EMPRESAS[letra],
                                  "nombre": clave.replace(".", " ").title(), "rol": rol, "punto_id": punto},
                          prefer="resolution=ignore-duplicates,return=minimal")
        assert estado < 300, (estado, r)
    return usuarios


def entrar(usuarios, claves):
    tokens = {}
    for clave in claves:
        correo = (f"{clave}@prueba-tino.example.com" if clave in EXTRA
                  else "{}.{}@prueba-tino.example.com".format(*clave.split(".")))
        estado, r = pedir("POST", "/auth/v1/token?grant_type=password", PUBLICA,
                          cuerpo={"email": correo, "password": usuarios[clave]["contrasena"]})
        assert estado == 200, (clave, estado)
        tokens[clave] = r["access_token"]
        time.sleep(0.2)
    return tokens


def crear(token, tabla, fila):
    estado, r = pedir("POST", f"/rest/v1/{tabla}", PUBLICA, token, fila, "return=representation")
    assert estado == 201, (tabla, estado, r)
    return r[0]


def main():
    archivo = Path(sys.argv[1])
    usuarios = base.preparar(archivo)
    usuarios = preparar_extra(archivo, usuarios)
    t = entrar(usuarios, ["dueno.a", "finanzas.a", "asesora.a", "dueno.b", *EXTRA])
    a, b = EMPRESAS["a"], EMPRESAS["b"]
    marca = str(int(time.time()))[-6:]

    # Plantilla y configuración distinta por empresa
    for letra in "ab":
        tipos = ver("equipo_catalogo", t[f"dueno.{letra}"], "select=empresa_id,clase&clase=eq.tipo_observacion")
        ok(len(tipos) >= 7 and all(x["empresa_id"] == EMPRESAS[letra] for x in tipos),
           f"Empresa {letra.upper()} tiene su plantilla y solo ve la suya", len(tipos))
    estado, r = pedir("POST", "/rest/v1/rpc/guardar_config_equipo", PUBLICA, t["lider.b"],
                      {"p": {"equipo_umbral_cumplimiento": 70, "equipo_dias_proximos": 10}})
    ok(estado in (200, 204), "El lider de B pone sus umbrales", (estado, r))
    estado, r = pedir("PATCH", f"/rest/v1/empresa_config?empresa_id=eq.{b}", PUBLICA, t["dueno.b"],
                      {"textos": {"persona": "vendedora", "personas": "vendedoras", "punto": "tienda"}}, "return=minimal")
    ok(estado == 204, "El dueño de B cambia las palabras de su pantalla", (estado, r))
    crear(t["lider.b"], "equipo_catalogo", {"empresa_id": b, "clase": "criterio", "nombre": f"Vitrina{marca}"})
    cfg_a = ver("empresa_config", t["dueno.a"], "select=equipo_umbral_cumplimiento,equipo_dias_proximos,textos")
    cfg_b = ver("empresa_config", t["dueno.b"], "select=equipo_umbral_cumplimiento,equipo_dias_proximos,textos")
    ok(cfg_b and cfg_b[0]["equipo_umbral_cumplimiento"] == 70 and cfg_b[0]["textos"].get("punto") == "tienda",
       "B quedó con su configuración", cfg_b)
    ok(cfg_a and cfg_a[0]["equipo_umbral_cumplimiento"] != 70 and "punto" not in (cfg_a[0]["textos"] or {}),
       "La configuración de B no toca a A", cfg_a)
    ok(ver("equipo_catalogo", t["lider.a"], f"select=id&nombre=eq.Vitrina{marca}") == [],
       "A no ve los criterios de B")
    rechaza(pedir("POST", "/rest/v1/rpc/guardar_config_equipo", PUBLICA, t["finanzas.a"],
                  {"p": {"equipo_umbral_cumplimiento": 1}}), "42501", "Finanzas no cambia umbrales")

    # Una persona en dos puntos, con observación y compromiso vencido
    p = crear(t["lider.a"], "asesora", {"empresa_id": a, "nombre_completo": f"Persona Prueba {marca}"})
    ok(p["codigo"].startswith("A"), "El lider crea una persona y la base le pone código", p["codigo"])
    for punto in (PUNTOS["a"], PUNTO_A2):
        crear(t["lider.a"], "asesora_punto",
              {"empresa_id": a, "asesora_id": p["id"], "punto_id": punto, "desde": "2026-10-01"})
    ok(len(ver("asesora_punto", t["lider.a"], f"select=id&asesora_id=eq.{p['id']}&hasta=is.null")) == 2,
       "La persona queda en dos puntos")
    coaching = ver("equipo_catalogo", t["lider.a"], "select=id&clase=eq.tipo_observacion&nombre=eq.Coaching")[0]["id"]
    obs = crear(t["lider.a"], "seguimiento", {"empresa_id": a, "asesora_id": p["id"], "punto_id": PUNTOS["a"],
                                              "tipo": "observacion", "tipo_observacion_id": coaching,
                                              "texto": "Ofrece el combo", "valoracion": "bien"})
    obs2 = crear(t["lider.a"], "seguimiento", {"empresa_id": a, "asesora_id": p["id"], "punto_id": PUNTO_A2,
                                               "tipo": "objetivo", "texto": "Subir el ticket"})
    comp = crear(t["lider.a"], "compromiso", {"empresa_id": a, "asesora_id": p["id"], "punto_id": PUNTOS["a"],
                                              "que": "Ofrecer el combo", "fecha_limite": "2026-11-01", "prioridad": "alta"})
    ok(comp["estado"] == "abierto", "El lider registra una observación y un compromiso vencido")

    resp = t["responsable.a"]
    vistos = {x["id"] for x in ver("seguimiento", resp, "select=id")}
    ok(obs["id"] in vistos and obs2["id"] not in vistos, "El responsable de A1 ve lo de su punto y no lo del otro")
    ok(any(x["id"] == comp["id"] for x in ver("compromiso", resp, "select=id")), "El responsable ve el compromiso vencido")
    estado, r = pedir("PATCH", f"/rest/v1/compromiso?id=eq.{comp['id']}", PUBLICA, resp, {"avance": 50}, "return=representation")
    ok(estado == 200 and r and r[0]["avance"] == 50, "El responsable actualiza el avance", (estado, r))
    for clave in ("finanzas.a", "asesora.a", "lider.b", "dueno.b"):
        ok(ver("seguimiento", t[clave], f"select=id&id=eq.{obs['id']}") == [], f"{clave} no ve la observación")
        ok(ver("compromiso", t[clave], f"select=id&id=eq.{comp['id']}") == [], f"{clave} no ve el compromiso")
    rechaza(pedir("POST", "/rest/v1/seguimiento", PUBLICA, resp,
                  {"empresa_id": a, "asesora_id": p["id"], "punto_id": PUNTO_A2, "tipo": "diagnostico", "texto": "x"}),
            "42501", "El responsable no registra en otro punto")
    rechaza(pedir("PATCH", f"/rest/v1/compromiso?id=eq.{comp['id']}", PUBLICA, t["lider.a"], {"que": "otra cosa"}),
            "42501", "El qué de un compromiso no se reescribe")
    estado, r = pedir("DELETE", f"/rest/v1/compromiso?id=eq.{comp['id']}", PUBLICA, t["dueno.a"], prefer="return=representation")
    ok(r == [], "Nadie borra compromisos", r)

    # B con lo suyo; cruces entre empresas
    pb = crear(t["lider.b"], "asesora", {"empresa_id": b, "nombre_completo": f"Vendedora Prueba {marca}"})
    ok(ver("asesora", t["lider.a"], f"select=id&id=eq.{pb['id']}") == [], "A no ve las personas de B")
    rechaza(pedir("POST", "/rest/v1/seguimiento", PUBLICA, t["lider.b"],
                  {"empresa_id": b, "asesora_id": pb["id"], "punto_id": PUNTOS["b"], "tipo": "observacion",
                   "tipo_observacion_id": coaching}), "23503", "B no usa un tipo de observación de A")
    rechaza(pedir("POST", "/rest/v1/asesora_punto", PUBLICA, t["lider.b"],
                  {"empresa_id": b, "asesora_id": p["id"], "punto_id": PUNTOS["b"]}), "23503",
            "B no asigna a su punto una persona de A")

    # Recorrido por usuario
    estado, r = pedir("POST", "/rest/v1/recorrido_usuario", PUBLICA, resp,
                      {"empresa_id": a, "recorrido": f"prueba{marca}", "estado": "saltado", "paso": 2}, "return=minimal")
    ok(estado == 201, "Cada usuario guarda su recorrido", (estado, r))
    ok(ver("recorrido_usuario", t["lider.a"], f"select=id&recorrido=eq.prueba{marca}") == [], "Nadie ve el recorrido de otro")

    print(f"\nResultado: {base.bien} bien, {len(base.fallas)} fallas")
    for falla in base.fallas:
        print("  ", falla)
    sys.exit(1 if base.fallas else 0)


if __name__ == "__main__":
    main()
