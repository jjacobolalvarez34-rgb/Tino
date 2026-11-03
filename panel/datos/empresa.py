# -*- coding: utf-8 -*-
"""Lo propio de la empresa, leído de la base: puntos, datáfonos, códigos, alias y reglas.

Arma la misma configuración que los lectores y la revisión usaban desde puntos.json,
pero desde las tablas: terminal_datafono, codigo_recaudo, perfil_fuente y
empresa_config. Así nada de un cliente queda en el código ni en un archivo suelto.
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores")]

from ingesta.maestros import norm_alias  # noqa: E402


class Empresa:
    def __init__(self, cliente):
        c = cliente
        self.puntos = c.leer("punto_venta", [("activo", "eq", "true")], "id,codigo,nombre,tipo")
        self.medios = c.leer("medio_pago", [("activo", "eq", "true")], "id,codigo,nombre,tipo")
        terminales = c.leer("terminal_datafono", [("activo_hasta", "is", "null")], "id,codigo_terminal,proveedor,punto_id")
        codigos = c.leer("codigo_recaudo", [("activo_hasta", "is", "null")], "codigo,punto_id")
        perfiles = c.leer("perfil_fuente", [("activo", "eq", "true")], "fuente,mapeo_columnas")
        self.config_base = c.leer("empresa_config", columnas="*", orden="empresa_id")[0]
        self.festivos = [f["fecha"] for f in c.leer("festivo", columnas="fecha", orden="fecha")]
        alias_p = c.leer("producto_alias", columnas="producto_id,texto_normalizado")
        alias_a = c.leer("asesora_alias", columnas="asesora_id,punto_id,texto_normalizado")

        self.por_id = {p["id"]: p for p in self.puntos}
        # Cómo se llama cada punto en pantalla. Si dos se llaman igual, llevan su código al
        # lado: el código es único en la empresa y así nunca se confunden.
        repetidos = {n for n in (p["nombre"] for p in self.puntos) if sum(q["nombre"] == n for q in self.puntos) > 1}
        nombre = {p["id"]: f"{p['nombre']} ({p['codigo']})" if p["nombre"] in repetidos else p["nombre"]
                  for p in self.puntos}
        self.etiqueta = nombre
        self.id_por_nombre = {v: k for k, v in nombre.items()}
        por_codigo = {p["codigo"]: nombre[p["id"]] for p in self.puntos}
        mapeo = {p["fuente"]: p["mapeo_columnas"] or {} for p in perfiles}

        self.terminal_id = {(t["proveedor"], str(t["codigo_terminal"]).strip().upper()): t["id"] for t in terminales}
        self.proveedor_del_punto = {}
        for t in terminales:
            self.proveedor_del_punto.setdefault(t["punto_id"], t["proveedor"])
        self.producto_por_alias = {a["texto_normalizado"]: a["producto_id"] for a in alias_p}
        self.asesora_por_alias = {(a["punto_id"], a["texto_normalizado"]): a["asesora_id"] for a in alias_a}

        # La misma forma que puntos.json, que es lo que esperan los lectores.
        self.lectores = {
            "bold": {t["codigo_terminal"]: nombre[t["punto_id"]] for t in terminales if t["proveedor"] == "bold"},
            "redeban": {t["codigo_terminal"]: nombre[t["punto_id"]] for t in terminales if t["proveedor"] == "redeban"},
            "codigos": {nombre[c["punto_id"]]: c["codigo"] for c in codigos},
            "excel": {texto: por_codigo[cod] for texto, cod in mapeo.get("excel_dia", {}).get("puntos", {}).items()
                      if cod in por_codigo},
            "ignorar": [n for f in ("bold", "redeban") for n in mapeo.get(f, {}).get("ignorar", [])],
            "config": self._config(self.config_base),
        }

    @staticmethod
    def _config(c):
        """Los valores ⚑ de las reglas, con los nombres que usa la revisión."""
        return {
            "tolerancia_cuadra": c["desc_umbral"],
            "porcentaje_explicado": c["desc_porcentaje_explicado"],
            "reglas_sin_peso": c["desc_reglas_sin_peso"],
            "compensacion": {"monto_minimo": c["desc_comp_minimo"], "tolerancia": c["desc_comp_tolerancia"],
                             "porcentaje": c["desc_comp_porcentaje"]},
            "billete": {"denominaciones": c["desc_billetes"], "max_billetes": c["desc_max_billetes"]},
            "precios": {"monto_minimo": c["desc_precios_minimo"], "max_productos": c["desc_precios_max_productos"],
                        "max_mostradas": c["desc_precios_mostradas"]},
        }

    def medio(self, tipo, punto_id=None):
        """El medio de pago de un tipo. Para tarjetas, el del proveedor del datáfono del punto."""
        del_tipo = [m for m in self.medios if m["tipo"] == tipo]
        if not del_tipo:
            raise ValueError(f"La empresa no tiene un medio de pago de tipo {tipo}.")
        proveedor = self.proveedor_del_punto.get(punto_id, "")
        return next((m["id"] for m in del_tipo if m["codigo"].lower() == proveedor), del_tipo[0]["id"])

    def producto(self, texto):
        return self.producto_por_alias.get(norm_alias(texto))

    def asesora(self, punto_id, texto):
        return self.asesora_por_alias.get((punto_id, norm_alias(texto)))
