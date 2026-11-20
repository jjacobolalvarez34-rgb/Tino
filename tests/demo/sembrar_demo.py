# -*- coding: utf-8 -*-
"""Crea (o completa) la empresa de demostración en tino-pruebas, con datos INVENTADOS: 4 puntos,
8 personas, ventas por persona de octubre y lo que va de noviembre, metas, compromisos,
observaciones y una sesión. Sirve para capturas y demos: ningún dato real de un cliente.

Se puede correr varias veces: lo que ya existe no se repite (las ventas se cargan como un
archivo por mes y la base rechaza el mismo archivo dos veces).

Uso: python tests/demo/sembrar_demo.py <archivo de contraseñas fuera del repo>
Lee las llaves de .env. Nunca imprime llaves ni contraseñas.
"""
import datetime as dt
import hashlib
import json
import random
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rls"))
from probar_supabase import PUBLICA, SECRETA, pedir  # noqa: E402

EMPRESA = "dddddddd-0000-4000-8000-000000000001"
PUNTOS = {"Punto Centro": "dddddddd-0000-4000-8000-000000000011", "Punto Norte": "dddddddd-0000-4000-8000-000000000012",
          "Punto Plaza": "dddddddd-0000-4000-8000-000000000013", "Punto Estación": "dddddddd-0000-4000-8000-000000000014"}
PERSONAS = [("Laura Gómez", ["Punto Centro"]), ("Andrés Ruiz", ["Punto Centro", "Punto Norte"]),
            ("Camila Torres", ["Punto Norte"]), ("Felipe Ríos", ["Punto Plaza"]), ("Valentina Mora", ["Punto Plaza"]),
            ("Julián Pardo", ["Punto Estación"]), ("Sara Medina", ["Punto Estación", "Punto Plaza"]),
            ("Diego Castaño", ["Punto Norte"])]
CORREO = "demo.dueno@prueba-tino.example.com"
HOY = dt.date(2026, 11, 19)


def ok(estado, r, que):
    assert estado < 300, (que, estado, r)
    return r


def main():
    archivo = Path(sys.argv[1])
    claves = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    ok(*pedir("POST", "/rest/v1/empresa?on_conflict=id", SECRETA, cuerpo={"id": EMPRESA, "nombre": "Distribuidora Demo"},
              prefer="resolution=ignore-duplicates,return=minimal"), "empresa")
    for i, (nombre, pid) in enumerate(PUNTOS.items(), 1):
        ok(*pedir("POST", "/rest/v1/punto_venta?on_conflict=id", SECRETA,
                  cuerpo={"id": pid, "empresa_id": EMPRESA, "codigo": f"D{i:02d}", "nombre": nombre},
                  prefer="resolution=ignore-duplicates,return=minimal"), "punto")
    if "demo.dueno" not in claves:
        contrasena = secrets.token_urlsafe(18)
        estado, r = pedir("POST", "/auth/v1/admin/users", SECRETA, cuerpo={"email": CORREO, "password": contrasena, "email_confirm": True})
        ok(estado, r, "acceso")
        claves["demo.dueno"] = {"id": r["id"], "contrasena": contrasena, "correo": CORREO}
        archivo.write_text(json.dumps(claves, indent=1), encoding="utf-8")
    uid = claves["demo.dueno"]["id"]
    ok(*pedir("POST", "/rest/v1/usuario?on_conflict=id", SECRETA, cuerpo={"id": uid, "empresa_id": EMPRESA,
              "nombre": "Dueña Demo", "rol": "dueno"}, prefer="resolution=ignore-duplicates,return=minimal"), "usuario")

    estado, r = pedir("POST", "/auth/v1/token?grant_type=password", PUBLICA,
                      cuerpo={"email": CORREO, "password": claves["demo.dueno"]["contrasena"]})
    tok = ok(estado, r, "entrar")["access_token"]

    def leer(tabla, q):
        return ok(*pedir("GET", f"/rest/v1/{tabla}?{q}", PUBLICA, tok), tabla)

    def crear(tabla, filas):
        return ok(*pedir("POST", f"/rest/v1/{tabla}", PUBLICA, tok, filas, "return=representation"), tabla)

    # Personas, asignaciones y el recorrido ya visto (para que no tape las capturas)
    existentes = {a["nombre_completo"]: a["id"] for a in leer("asesora", "select=id,nombre_completo")}
    ids = {}
    for nombre, pts in PERSONAS:
        ids[nombre] = existentes.get(nombre) or crear("asesora", {"empresa_id": EMPRESA, "nombre_completo": nombre,
                                                                  "fecha_ingreso": "2026-06-01"})[0]["id"]
        if not leer("asesora_punto", f"select=id&asesora_id=eq.{ids[nombre]}"):
            crear("asesora_punto", [{"empresa_id": EMPRESA, "asesora_id": ids[nombre], "punto_id": PUNTOS[p],
                                     "desde": "2026-06-01"} for p in pts])
    for rec in ("inicio", "equipo", "ventas"):
        if not leer("recorrido_usuario", f"select=id&recorrido=eq.{rec}"):
            crear("recorrido_usuario", {"empresa_id": EMPRESA, "recorrido": rec, "estado": "visto", "paso": 0})

    # Ventas por persona: un archivo por mes, con números inventados pero creíbles
    azar = random.Random(19)
    por_punto = {p: [n for n, pts in PERSONAS if p in pts] for p in PUNTOS}
    base_punto = {"Punto Centro": 2_600_000, "Punto Norte": 1_900_000, "Punto Plaza": 3_100_000, "Punto Estación": 1_400_000}
    for mes, (ini, fin) in {"octubre": (dt.date(2026, 10, 1), dt.date(2026, 10, 31)),
                            "noviembre": (dt.date(2026, 11, 1), HOY - dt.timedelta(days=1))}.items():
        filas, fila = [], 3
        d = ini
        while d <= fin:
            for punto, gente in por_punto.items():
                quien = azar.sample(gente, 2 if len(gente) > 1 and azar.random() < 0.25 else 1)
                venta = int(base_punto[punto] * azar.uniform(0.7, 1.35) * (1.15 if d.weekday() >= 5 else 1)) // 100 * 100
                facturas = max(5, int(venta / azar.uniform(62_000, 98_000)))
                for k, n in enumerate(quien):
                    parte = venta // len(quien) + (venta % len(quien) if k == 0 else 0)
                    filas.append({"punto_id": PUNTOS[punto], "fecha": d.isoformat(), "asesora_id": ids[n], "texto_original": n,
                                  "venta": parte, "facturas": round(facturas / len(quien), 2), "venta_dia": venta,
                                  "facturas_dia": facturas, "personas_dia": len(quien), "fila_origen": fila})
                fila += 1
            d += dt.timedelta(days=1)
        metas = [{"punto_id": pid, "asesora_id": None, "desde": ini.replace(day=1).isoformat(),
                  "hasta": (dt.date(2026, ini.month + 1, 1) - dt.timedelta(days=1)).isoformat(),
                  "monto": int(base_punto[p] * 30 * 1.05) // 1_000_000 * 1_000_000, "fila_origen": 2}
                 for p, pid in PUNTOS.items()]
        carga = {"fuente": "excel_dia", "nombre": f"demo {mes}.xlsx", "desde": ini.isoformat(), "hasta": fin.isoformat(),
                 "hash": hashlib.sha256(f"demo-{mes}-v1".encode()).hexdigest(), "jornadas": [], "ventas_persona": filas,
                 "metas": metas, "errores": []}
        estado, r = pedir("POST", "/rest/v1/rpc/importar_archivo", PUBLICA, tok, {"p": carga})
        print(mes, "cargado" if estado < 300 else "ya estaba" if r.get("code") == "23505" else (estado, r))

    # Metas personales de noviembre (para el anillo y "necesita apoyo")
    if not leer("meta_periodo", "select=id&asesora_id=not.is.null"):
        crear("meta_periodo", [{"empresa_id": EMPRESA, "punto_id": PUNTOS[pts[0]], "asesora_id": ids[n], "desde": "2026-11-01",
                                "hasta": "2026-11-30", "monto": m} for (n, pts), m in zip(PERSONAS, [
                                    42_000_000, 30_000_000, 38_000_000, 50_000_000, 46_000_000, 26_000_000, 30_000_000, 24_000_000])])

    # Configuración, acompañamiento y pendientes
    ok(*pedir("POST", "/rest/v1/rpc/guardar_config_equipo", PUBLICA, tok,
              {"p": {"equipo_umbral_cumplimiento": 80, "equipo_umbral_dias_sin_seguimiento": 21}}), "umbrales")
    cat = {c["nombre"]: c["id"] for c in leer("equipo_catalogo", "select=id,nombre")}
    for nombre in ("Saludo y atención", "Ofrece el producto del mes", "Cierre de venta"):
        if nombre not in cat:
            cat[nombre] = crear("equipo_catalogo", {"empresa_id": EMPRESA, "clase": "criterio", "nombre": nombre})[0]["id"]
    if not leer("seguimiento", "select=id&limit=1"):
        obs = [("Laura Gómez", "Punto Centro", "Coaching", "Ofreció el combo en cada venta y cerró dos adicionales.", "bien", 3),
               ("Felipe Ríos", "Punto Plaza", "Cliente incógnito", "Saludo rápido, pero no preguntó qué buscaba el cliente.", "a_mejorar", 6),
               ("Camila Torres", "Punto Norte", "Puntualidad", "Llegó 20 minutos tarde por segunda vez en la semana.", "a_mejorar", 2),
               ("Valentina Mora", "Punto Plaza", "Presentación personal", "Impecable; buena vitrina.", "bien", 9)]
        for n, p, tipo, texto, val, hace in obs:
            crear("seguimiento", {"empresa_id": EMPRESA, "asesora_id": ids[n], "punto_id": PUNTOS[p], "tipo": "observacion",
                                  "tipo_observacion_id": cat[tipo], "texto": texto, "valoracion": val,
                                  "fecha": (HOY - dt.timedelta(days=hace)).isoformat()})
        crear("seguimiento", {"empresa_id": EMPRESA, "asesora_id": ids["Laura Gómez"], "punto_id": PUNTOS["Punto Centro"],
                              "tipo": "objetivo", "texto": "Subir el ticket promedio a $ 95.000 este mes.", "fecha": "2026-11-02"})
        comps = [("Felipe Ríos", "Punto Plaza", "Preguntar qué busca el cliente antes de mostrar", -4, "alta", 25),
                 ("Camila Torres", "Punto Norte", "Llegar 10 minutos antes de abrir", -1, "media", 50),
                 ("Laura Gómez", "Punto Centro", "Enseñarle el combo a Andrés", 3, "baja", 0),
                 ("Julián Pardo", "Punto Estación", "Ordenar la vitrina con el producto del mes", 5, "media", 10)]
        for n, p, que, dias, prio, av in comps:
            c = crear("compromiso", {"empresa_id": EMPRESA, "asesora_id": ids[n], "punto_id": PUNTOS[p], "que": que,
                                     "fecha_limite": (HOY + dt.timedelta(days=dias)).isoformat(), "prioridad": prio})[0]
            if av:
                pedir("PATCH", f"/rest/v1/compromiso?id=eq.{c['id']}", PUBLICA, tok, {"avance": av, "estado": "en_curso"})
        crear("sesion_formacion", {"empresa_id": EMPRESA, "titulo": "Cierre de venta con el producto del mes",
                                   "fecha": (HOY + dt.timedelta(days=2)).isoformat(), "hora": "08:00"})
    print("Empresa demo lista.")


if __name__ == "__main__":
    main()
