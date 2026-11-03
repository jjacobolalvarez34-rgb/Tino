# -*- coding: utf-8 -*-
"""Carga los maestros de una empresa en Supabase desde un archivo JSON.

Por defecto solo simula: dice qué crearía, sin escribir nada. Para escribir de verdad
hay que pasar --aplicar. Se puede correr varias veces: lo que ya existe no se repite.

Uso: python ingesta/maestros.py datos.json [--aplicar]

Usa la llave de servicio, que se salta RLS: por eso cada fila lleva su empresa_id y el
programa se niega a correr si .env no dice SUPABASE_PROYECTO=pruebas. El archivo trae
datos de un cliente: se guarda fuera del repositorio. Nada se borra.
"""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "motores"))


def norm_alias(texto):
    """Lo mismo que app.normalizar_texto en la base, para comparar antes de escribir."""
    import re
    tabla = str.maketrans("ÁÉÍÓÚÜÑÀÈÌÒÙáéíóúüñàèìòù", "AEIOUUNAEIOUaeiouunaeiou")
    return re.sub(r"[^a-z0-9%$]+", " ", texto.translate(tabla).lower()).strip()


def plan(datos, existentes):
    """Devuelve, tabla por tabla, las filas que faltan y los avisos. No toca la red.

    `existentes` tiene lo que ya está en la base. Cada tabla se compara por su clave,
    la misma que hace única a la fila dentro de la empresa.
    """
    empresa = datos["empresa"]["id"]
    avisos, faltan = [], {}
    puntos = {p["codigo"]: p["id"] for p in datos["puntos"]}
    asesoras = {a["nombre_completo"]: a["id"] for a in datos["asesoras"]}
    productos = {p["codigo"]: p["id"] for p in datos["productos"]}

    def agregar(tabla, filas, clave):
        vistos = set(existentes.get(tabla, []))
        nuevas = []
        for fila in filas:
            k = clave(fila)
            if k in vistos:
                continue
            vistos.add(k)
            nuevas.append(fila)
        faltan[tabla] = nuevas

    agregar("empresa", [{"id": empresa, "nombre": datos["empresa"]["nombre"], "plan": "piloto", "estado": "prueba"}],
            lambda f: f["id"])
    agregar("punto_venta", [{**p, "empresa_id": empresa} for p in datos["puntos"]], lambda f: f["codigo"])
    agregar("medio_pago", [{**m, "empresa_id": empresa} for m in datos["medios_pago"]], lambda f: f["codigo"])
    agregar("tipo_venta", [{**t, "empresa_id": empresa} for t in datos["tipos_venta"]], lambda f: f["codigo"])
    agregar("asesora", [{**a, "empresa_id": empresa} for a in datos["asesoras"]], lambda f: f["nombre_completo"])

    filas = []
    for a in datos["alias"]:
        if a["punto"] not in puntos or a["asesora"] not in asesoras:
            avisos.append(f"Alias sin punto o asesora conocidos: {a['texto']}")
            continue
        filas.append({"empresa_id": empresa, "punto_id": puntos[a["punto"]], "asesora_id": asesoras[a["asesora"]],
                      "texto_original": a["texto"], "fuente": a.get("fuente")})
    agregar("asesora_alias", filas, lambda f: (f["punto_id"], norm_alias(f["texto_original"])))

    agregar("producto", [{**p, "empresa_id": empresa} for p in datos["productos"]], lambda f: f["codigo"])
    filas, dueno = [], {}
    for a in datos["producto_alias"]:
        n = norm_alias(a["texto"])
        if dueno.setdefault(n, a["producto"]) != a["producto"]:
            avisos.append(f"Nombre de producto usado por dos productos, no se carga: {a['texto']}")
            continue
        filas.append({"empresa_id": empresa, "producto_id": productos[a["producto"]],
                      "texto_original": a["texto"], "fuente": a.get("fuente")})
    agregar("producto_alias", filas, lambda f: norm_alias(f["texto_original"]))

    agregar("terminal_datafono",
            [{"empresa_id": empresa, "punto_id": puntos[d["punto"]], "proveedor": d["proveedor"],
              "codigo_terminal": d["codigo_terminal"], "activo_desde": d["activo_desde"]} for d in datos["datafonos"]],
            lambda f: f["codigo_terminal"])
    agregar("codigo_recaudo",
            [{"empresa_id": empresa, "punto_id": puntos[c["punto"]], "codigo": c["codigo"],
              "activo_desde": c["activo_desde"]} for c in datos["codigos_recaudo"]],
            lambda f: f["codigo"])

    # Lo propio de cada fuente: cómo se llama cada punto en el Excel, qué datáfonos se ignoran.
    agregar("perfil_fuente",
            [{"empresa_id": empresa, "fuente": p["fuente"], "nombre": p["nombre"], "mapeo_columnas": p["mapeo"]}
             for p in datos.get("perfiles", [])],
            lambda f: f["nombre"])

    finales = {}
    for c in datos["codigos_recaudo"]:
        if finales.setdefault(c["codigo"][-4:], c["punto"]) != c["punto"]:
            avisos.append(f"Dos puntos comparten los últimos 4 dígitos: {c['codigo'][-4:]}")
    return faltan, avisos


CLAVES = {"empresa": ("id",), "punto_venta": ("codigo",), "medio_pago": ("codigo",), "tipo_venta": ("codigo",),
          "asesora": ("nombre_completo",), "asesora_alias": ("punto_id", "texto_normalizado"), "producto": ("codigo",),
          "producto_alias": ("texto_normalizado",), "terminal_datafono": ("codigo_terminal",), "codigo_recaudo": ("codigo",),
          "perfil_fuente": ("nombre",)}


class Supabase:
    def __init__(self):
        env = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines() if "=" in l)
        if env.get("SUPABASE_PROYECTO") != "pruebas":
            raise SystemExit("Este programa solo corre si .env dice SUPABASE_PROYECTO=pruebas.")
        self.url, self.llave = env["SUPABASE_URL"].rstrip("/"), env["SUPABASE_SERVICE_ROLE_KEY"]

    def pedir(self, metodo, ruta, cuerpo=None, prefer=None):
        cabeceras = {"apikey": self.llave, "Content-Type": "application/json"}
        if prefer:
            cabeceras["Prefer"] = prefer
        datos = None if cuerpo is None else json.dumps(cuerpo).encode("utf-8")
        pedido = urllib.request.Request(self.url + ruta, data=datos, headers=cabeceras, method=metodo)
        try:
            with urllib.request.urlopen(pedido, timeout=60) as r:
                texto = r.read().decode("utf-8")
                return json.loads(texto) if texto else None
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Supabase rechazó {metodo} {ruta.split('?')[0]}: {e.read().decode('utf-8')[:200]}")

    def existentes(self, empresa):
        salida = {}
        for tabla, columnas in CLAVES.items():
            filtro = f"id=eq.{empresa}" if tabla == "empresa" else f"empresa_id=eq.{empresa}"
            filas = self.pedir("GET", f"/rest/v1/{tabla}?select={','.join(columnas)}&{filtro}&limit=10000")
            salida[tabla] = [f[columnas[0]] if len(columnas) == 1 else tuple(f[c] for c in columnas) for f in filas]
        return salida


def main():
    datos = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    aplicar = "--aplicar" in sys.argv
    base = Supabase()
    faltan, avisos = plan(datos, base.existentes(datos["empresa"]["id"]))
    for tabla, filas in faltan.items():
        print(f"{tabla:20} {len(filas):4} por crear")
    for aviso in avisos:
        print("Aviso:", aviso)
    if not aplicar:
        print("\nSimulacro: no se escribió nada. Para cargar, agrega --aplicar.")
        return
    for tabla, filas in faltan.items():
        if filas:
            base.pedir("POST", f"/rest/v1/{tabla}", filas, "return=minimal")
            print(f"{tabla:20} {len(filas):4} creadas")
    print("\nCarga terminada.")


if __name__ == "__main__":
    main()
