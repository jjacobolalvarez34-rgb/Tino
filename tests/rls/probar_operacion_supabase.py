# -*- coding: utf-8 -*-
"""Prueba en Supabase la operación diaria (0004 a 0007) con el cliente del programa.

Entra con los usuarios de las empresas inventadas A y B (los crea probar_supabase.py),
la llave pública y la sesión de cada uno, igual que Tino.exe. Sube un archivo inventado
a A, revisa que B no lo vea ni lo toque, guarda una revisión y lo deshace. Como nada se
borra, lo de cada corrida se queda en A, deshecho.

Uso: python tests/rls/probar_operacion_supabase.py <archivo de contraseñas, fuera del repo>
Nunca imprime llaves, contraseñas ni tokens.
"""
import json
import secrets
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from panel.datos.cliente import Cliente, ErrorBase  # noqa: E402

ENV = dict(linea.split("=", 1) for linea in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in linea)
PUNTO_A = "aaaaaaaa-0000-4000-8000-000000000011"
fallas, bien = [], 0


def ok(condicion, prueba):
    global bien
    if condicion:
        bien += 1
        print("OK ", prueba)
    else:
        fallas.append(prueba)
        print("FALLÓ", prueba)


def falla_con(codigo, funcion, prueba):
    try:
        funcion()
        ok(False, f"{prueba} (no dio error)")
    except ErrorBase as e:
        ok(e.codigo == codigo, f"{prueba}" + ("" if e.codigo == codigo else f" (dio {e.codigo})"))


def entrar(usuarios, clave):
    rol, letra = clave.split(".")
    c = Cliente(ENV["SUPABASE_URL"], ENV["SUPABASE_ANON_KEY"])
    c.iniciar_sesion(f"{rol}.{letra}@prueba-tino.example.com", usuarios[clave]["contrasena"])
    return c


def main():
    usuarios = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    dueno_a, fin_a, ase_a, dueno_b = (entrar(usuarios, k) for k in ("dueno.a", "finanzas.a", "asesora.a", "dueno.b"))
    ok(True, "Cuatro usuarios entran con correo y clave, como en el programa")

    medios = dueno_a.leer("medio_pago", [("codigo", "eq", "TR")], "id")
    medio = medios[0]["id"] if medios else dueno_a.crear("medio_pago", [{
        "empresa_id": "aaaaaaaa-0000-4000-8000-000000000001", "codigo": "TR", "nombre": "Transferencia",
        "tipo": "transferencia"}])[0]["id"]
    ok(len(fin_a.leer("festivo", [("fecha", "gte", "2026-01-01"), ("fecha", "lte", "2026-12-31")], "fecha", "fecha")) == 18,
       "Los festivos de 2026 están en la base")

    carga = {"fuente": "excel_dia", "nombre": "inventado.xlsx", "hash": secrets.token_hex(32),
             "desde": "2026-09-16", "hasta": "2026-09-16",
             "jornadas": [{"punto_id": PUNTO_A, "fecha": "2026-09-16",
                           "reporte": {"hoja": "16", "fila_origen": 45, "efectivo_contado": 100000,
                                       "venta_teorica": 300000, "descuadre": -20000, "asesoras_texto": "Ana"},
                           "pagos": [{"medio_pago_id": medio, "monto": 85000, "fila_origen": 30},
                                     {"medio_pago_id": medio, "monto": 40000, "fila_origen": 31}]}]}
    archivo = fin_a.rpc("importar_archivo", {"p": carga})
    ok(bool(archivo), "Finanzas de A sube un archivo entero")
    falla_con("23505", lambda: fin_a.rpc("importar_archivo", {"p": carga}), "El mismo archivo no entra dos veces")
    ok(len(fin_a.leer("v_pago_vigente", [("archivo_id", "eq", archivo)], "id")) == 2, "Sus pagos quedan vigentes")

    ok(dueno_b.leer("v_pago_vigente", [("archivo_id", "eq", archivo)], "id") == [], "El dueño de B no ve los pagos de A")
    falla_con("P0002", lambda: dueno_b.rpc("deshacer_archivo", {"p_archivo": archivo}),
              "El dueño de B no deshace archivos de A")
    falla_con("42501", lambda: ase_a.rpc("importar_archivo", {"p": {**carga, "hash": secrets.token_hex(32)}}),
              "La asesora no sube archivos")
    ok(ase_a.leer("v_transferencia", columnas="pago_id", orden="pago_id") == [], "La asesora no ve transferencias")

    jornada = fin_a.leer("v_jornada", [("punto_id", "eq", PUNTO_A), ("fecha", "eq", "2026-09-16")], "id,reporte_id")[0]
    fin_a.rpc("guardar_revision", {"p": {"descuadres": [{
        "jornada_id": jornada["id"], "reporte_id": jornada["reporte_id"], "monto": -20000, "explicado": -20000,
        "sin_explicar": 0, "estado_motor": "explicado", "causa_codigo": "billete",
        "evidencias": [{"causa_codigo": "billete", "tipo": "causa", "monto": -20000, "total": -20000,
                        "detalle": {"denominacion": 20000, "cantidad": 1}}]}]}})
    vista = fin_a.leer("v_jornada", [("id", "eq", jornada["id"])], "estado_motor,causa_codigo")[0]
    ok(vista == {"estado_motor": "explicado", "causa_codigo": "billete"}, "La revisión guarda el descuadre con su causa")
    ok(dueno_b.leer("descuadre", columnas="id") == [], "El dueño de B no ve descuadres de A")

    fin_a.rpc("deshacer_archivo", {"p_archivo": archivo})
    ok(fin_a.leer("v_pago_vigente", [("archivo_id", "eq", archivo)], "id") == [], "Lo de un archivo deshecho deja de contar")

    print(f"\n{bien} bien, {len(fallas)} fallas")
    sys.exit(1 if fallas else 0)


if __name__ == "__main__":
    main()
