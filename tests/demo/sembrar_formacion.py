# -*- coding: utf-8 -*-
"""Siembra la formación (0015) en la empresa de demostración de tino-pruebas, con datos
INVENTADOS: el nombre del programa, la plantilla sugerida, una responsable del Punto Plaza y una
líder, el paso del ciclo de cada persona, registros del día de octubre y noviembre (con días
sin registro a propósito), evaluaciones con criterios y sesiones de esta semana.

Corre después de sembrar_demo.py. Se puede correr varias veces: lo que ya existe no se repite.

Uso: python tests/demo/sembrar_formacion.py <archivo de contraseñas fuera del repo>
Nunca imprime llaves ni contraseñas.
"""
import datetime as dt
import json
import random
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "rls"))
from probar_supabase import PUBLICA, SECRETA, pedir  # noqa: E402
from sembrar_demo import CORREO, EMPRESA, PERSONAS, PUNTOS, ok  # noqa: E402

HOY = dt.datetime.now(dt.timezone(dt.timedelta(hours=-5))).date()   # hoy en Bogotá
USUARIOS = {  # clave en el archivo: (correo, nombre, rol, punto)
    "demo.responsable": ("demo.responsable@prueba-tino.example.com", "Responsable Plaza Demo", "responsable_punto", "Punto Plaza"),
    "demo.lider": ("demo.lider@prueba-tino.example.com", "Líder Demo", "lider", None),
}
# Cómo atiende cada persona (inventado): qué tanto explica el programa, consulta puntos y pide referidos.
ESTILO = {"Laura Gómez": (.70, .88, .12), "Andrés Ruiz": (.45, .70, .05), "Camila Torres": (.30, .50, .03),
          "Felipe Ríos": (.25, .45, .02), "Valentina Mora": (.62, .82, .09), "Julián Pardo": (.40, .60, .04),
          "Sara Medina": (.55, .75, .07), "Diego Castaño": (.35, .55, .03)}
PASO = {"Laura Gómez": "Compromisos", "Andrés Ruiz": "Acompañamiento", "Camila Torres": "Formación",
        "Felipe Ríos": "Diagnóstico", "Valentina Mora": "Evaluación", "Julián Pardo": "Acompañamiento",
        "Sara Medina": "Evaluación", "Diego Castaño": "Formación"}


def main():
    archivo = Path(sys.argv[1])
    claves = json.loads(archivo.read_text(encoding="utf-8"))

    def entrar(clave):
        estado, r = pedir("POST", "/auth/v1/token?grant_type=password", PUBLICA,
                          cuerpo={"email": claves[clave]["correo"], "password": claves[clave]["contrasena"]})
        return ok(estado, r, "entrar " + clave)["access_token"]

    tok = entrar("demo.dueno")

    def leer(tabla, q, token=tok):
        return ok(*pedir("GET", f"/rest/v1/{tabla}?{q}", PUBLICA, token), tabla)

    def crear(tabla, filas, token=tok):
        return ok(*pedir("POST", f"/rest/v1/{tabla}", PUBLICA, token, filas, "return=representation"), tabla)

    # 1. Nombre del programa y plantilla sugerida (como lo haría la dueña con el botón)
    cfg = leer("empresa_config", "select=textos")[0]["textos"] or {}
    if cfg.get("programa") != "Club Puntos Demo":
        ok(*pedir("PATCH", f"/rest/v1/empresa_config?empresa_id=eq.{EMPRESA}", PUBLICA, tok,
                  {"textos": {**cfg, "programa": "Club Puntos Demo"}}), "programa")
    estado, r = pedir("POST", "/rest/v1/rpc/usar_plantilla_formacion", PUBLICA, tok, {})
    print("plantilla:", ok(estado, r, "plantilla"))

    # 2. Usuarios de demostración: responsable de Punto Plaza y líder (sin correo: dominio inventado)
    for clave, (correo, nombre, rol, punto) in USUARIOS.items():
        if clave not in claves:
            contrasena = secrets.token_urlsafe(18)
            estado, r = pedir("POST", "/auth/v1/admin/users", SECRETA,
                              cuerpo={"email": correo, "password": contrasena, "email_confirm": True, "user_metadata": {"nombre": nombre}})
            ok(estado, r, "acceso " + clave)
            claves[clave] = {"id": r["id"], "contrasena": contrasena, "correo": correo}
            archivo.write_text(json.dumps(claves, indent=1), encoding="utf-8")
        ok(*pedir("POST", "/rest/v1/usuario?on_conflict=id", SECRETA,
                  cuerpo={"id": claves[clave]["id"], "empresa_id": EMPRESA, "nombre": nombre, "rol": rol,
                          "punto_id": PUNTOS[punto] if punto else None},
                  prefer="resolution=ignore-duplicates,return=minimal"), "usuario " + clave)
        # El recorrido ya visto, para que no tape las capturas.
        t2 = entrar(clave)
        for rec in ("inicio", "equipo", "ventas"):
            if not leer("recorrido_usuario", f"select=id&recorrido=eq.{rec}", t2):
                crear("recorrido_usuario", {"empresa_id": EMPRESA, "recorrido": rec, "estado": "visto", "paso": 0}, t2)

    ids = {a["nombre_completo"]: a["id"] for a in leer("asesora", "select=id,nombre_completo")}
    ind = {i["base"]: i["id"] for i in leer("indicador_dia", "select=id,base&activo=eq.true")}
    cat = {(c["clase"], c["nombre"]): c["id"] for c in leer("equipo_catalogo", "select=id,clase,nombre")}

    # 3. Paso del ciclo de cada persona (con una historia corta)
    if not leer("asesora_etapa", "select=id&limit=1"):
        uid = claves["demo.dueno"]["id"]
        for n, paso in PASO.items():
            if paso != "Diagnóstico":
                crear("asesora_etapa", {"empresa_id": EMPRESA, "asesora_id": ids[n], "etapa_id": cat[("etapa", "Diagnóstico")],
                                        "desde": "2026-10-01", "nota": "Diagnóstico inicial", "autor_id": uid})
            crear("asesora_etapa", {"empresa_id": EMPRESA, "asesora_id": ids[n], "etapa_id": cat[("etapa", paso)],
                                    "desde": (HOY - dt.timedelta(days=random.Random(n).randint(3, 25))).isoformat(), "autor_id": uid})

    # 4. Registros del día: los días con venta de cada persona, octubre y noviembre hasta ayer.
    #    Uno de cada ocho días queda sin registro a propósito: no debe contar como cero.
    if not leer("registro_dia", "select=id&limit=1"):
        ventas = leer("v_venta_asesora", "select=punto_id,fecha,asesora_id,facturas&fecha=gte.2026-10-01&asesora_id=not.is.null")
        azar = random.Random(26)
        nombre = {v: k for k, v in ids.items()}
        dias = {}
        for v in ventas:
            dias.setdefault((v["punto_id"], v["fecha"]), []).append(v)
        # Los días sin venta cargada (después del último Excel) también se registran: no tienen facturas.
        ultimo = max(f for _, f in dias) if dias else "2026-10-01"
        d = dt.date.fromisoformat(ultimo) + dt.timedelta(days=1)
        while d < HOY:
            for punto, pid in PUNTOS.items():
                gente = [n for n, pts in PERSONAS if punto in pts]
                dias[(pid, d.isoformat())] = [{"asesora_id": ids[azar.choice(gente)], "facturas": None}]
            d += dt.timedelta(days=1)
        hechos = 0
        for (pid, f), filas in sorted(dias.items(), key=lambda x: x[0][1]):
            if azar.random() < 0.125:
                continue
            mejora = 1.12 if f >= "2026-11-01" else 1.0       # noviembre un poco mejor que octubre
            enviar = []
            for v in filas:
                exp, con, ref = ESTILO[nombre[v["asesora_id"]]]
                fact = v["facturas"] if v["facturas"] is not None else azar.randint(14, 34)
                clientes = max(1, round(float(fact) * azar.uniform(1.6, 2.3)))
                enviar.append({"asesora_id": v["asesora_id"], "clientes_atendidos": clientes, "valores": {
                    ind["atendidos"]: min(clientes, round(clientes * min(.95, exp * mejora) * azar.uniform(.8, 1.2))),
                    ind["facturas"]: round(float(fact) * min(.98, con * mejora) * azar.uniform(.85, 1.1)),
                    ind["conteo"]: sum(1 for _ in range(clientes) if azar.random() < ref)}})
            estado, r = pedir("POST", "/rest/v1/rpc/guardar_registros_dia", PUBLICA, tok,
                              {"p": {"punto_id": pid, "fecha": f, "filas": enviar}})
            ok(estado, r, f"registro {f}")
            hechos += 1
        print("registros del día:", hechos, "puntos-día")

    # 5. Evaluaciones con los criterios de la plantilla y sesiones de esta semana
    criterios = [v for (clase, _), v in cat.items() if clase == "criterio"]
    if not leer("seguimiento", "select=id&tipo=eq.evaluacion&limit=1") and criterios:
        azar = random.Random(7)
        for n, punto, dias_atras in (("Felipe Ríos", "Punto Plaza", 5), ("Valentina Mora", "Punto Plaza", 8), ("Laura Gómez", "Punto Centro", 12)):
            s = crear("seguimiento", {"empresa_id": EMPRESA, "asesora_id": ids[n], "punto_id": PUNTOS[punto], "tipo": "evaluacion",
                                      "texto": "Evaluación de estándares de atención.",
                                      "fecha": (HOY - dt.timedelta(days=dias_atras)).isoformat()})[0]
            crear("seguimiento_criterio", [{"empresa_id": EMPRESA, "seguimiento_id": s["id"], "criterio_id": c,
                                            "puntaje": azar.randint(2 if n == "Felipe Ríos" else 3, 4 if n == "Felipe Ríos" else 5)}
                                           for c in criterios])
    lunes = HOY - dt.timedelta(days=HOY.weekday())
    if not leer("sesion_formacion", f"select=id&fecha=gte.{lunes.isoformat()}&titulo=like.*30%20segundos*"):
        for dias, hora, titulo, punto in ((0, "08:00", "Venta consultiva · módulo 2", "Punto Centro"),
                                          (2, "10:00", "Club Puntos Demo: cómo explicarlo en 30 segundos", None),
                                          (3, "15:00", "Coaching en el punto", "Punto Plaza"),
                                          (5, "09:00", "Evaluación de estándares", "Punto Norte")):
            crear("sesion_formacion", {"empresa_id": EMPRESA, "titulo": titulo, "fecha": (lunes + dt.timedelta(days=dias)).isoformat(),
                                       "hora": hora, "punto_id": PUNTOS[punto] if punto else None})
    print("Formación de la demo lista.")


if __name__ == "__main__":
    main()
