# -*- coding: utf-8 -*-
"""
Bold / Redeban — lo que se cobró en los datáfonos, por punto y día (R33).

Reutiliza los cargadores del módulo Bold/Redeban (core.load_bold, core.load_redeban)
sin modificarlos:
  Bold     un datáfono por punto (columna NOMBRE DEL DATÁFONO); se usa la fecha y
           hora de la transacción y el VALOR TOTAL. En el formato nuevo solo
           cuentan los "COBRO EXITOSO".
  Redeban  el punto sale de los 2 últimos dígitos del CODIGO ESTABLECIMIENTO; se
           usa la FECHA DE TRANSACCION (no la de canje) y el VALOR TOTAL.

Cobertura: un reporte cubre, para TODOS los puntos de ese procesador, los días
entre su primera y su última transacción. Un punto sin cobros en un día cubierto
quiere decir que ese día no pasó tarjetas.

Los reportes no distinguen débito de crédito, así que se compara la suma de las
listas T (débito) y U (crédito) del Excel contra todo lo cobrado.
"""
import datetime as dt
import os
from dataclasses import dataclass, field

from .banco import MovBanco


@dataclass
class DatosTarjetas:
    cobros: dict = field(default_factory=dict)      # (fecha, punto) -> [MovBanco]
    cobertura: dict = field(default_factory=dict)   # punto -> set(fechas)
    archivos: list = field(default_factory=list)
    avisos: list = field(default_factory=list)

    def cubre(self, fecha, punto):
        return fecha in self.cobertura.get(punto, ())

    def de(self, fecha, punto):
        return self.cobros.get((fecha, punto), []) if self.cubre(fecha, punto) else []

    def agregar(self, otro, puntos_procesador):
        """Suma otro reporte. Los días que ya cubría otro reporte del mismo
        punto no se vuelven a sumar (evita duplicar si se carga dos veces)."""
        for (f, p), movs in otro.cobros.items():
            if not self.cubre(f, p):
                self.cobros.setdefault((f, p), []).extend(movs)
        repetidos = set()
        for p in puntos_procesador:
            nuevos = otro.cobertura.get(p, set())
            repetidos |= nuevos & self.cobertura.get(p, set())
            self.cobertura.setdefault(p, set()).update(nuevos)
        self.archivos += otro.archivos
        self.avisos += otro.avisos
        if repetidos:
            self.avisos.append(f"{', '.join(otro.archivos)}: los días "
                               f"{', '.join(f'{d:%d/%m}' for d in sorted(repetidos))} ya venían en otro "
                               f"reporte; se usó el primero.")

    def fechas(self):
        return set().union(*self.cobertura.values()) if self.cobertura else set()


def _rango(fechas):
    if not fechas:
        return set()
    a, b = min(fechas), max(fechas)
    return {a + dt.timedelta(days=k) for k in range((b - a).days + 1)}


def leer(ruta, identificar_punto):
    """Detecta si es Bold o Redeban y lo lee. Devuelve (tipo, DatosTarjetas,
    puntos del procesador)."""
    import core     # motor Bold/Redeban (reutilizado tal cual)

    nombre = os.path.basename(ruta)
    tipo = core.detect_file_type(ruta)
    datos = DatosTarjetas(archivos=[nombre])
    if tipo == "bold":
        filas, _, omitidas = core.load_bold(ruta)
        tiendas = {core._norm(t): t for t in core.BOLD_STORES}
        puntos_proc = {identificar_punto(t) for t in core.BOLD_STORES} - {None}
        desconocidos = set()
        for r in filas:
            datafono = r["NOMBRE DEL DATÁFONO"]
            punto = identificar_punto(tiendas.get(r["NOMBRE DEL DATÁFONO_NORM"], datafono))
            if punto is None:
                desconocidos.add(datafono)
                continue
            puntos_proc.add(punto)
            hora = r["Fecha antigua"]
            datos.cobros.setdefault((r["FECHA"], punto), []).append(MovBanco(
                r["FECHA"], float(r["VALOR TOTAL"] or 0), punto, "",
                f"{hora:%H:%M}" if isinstance(hora, dt.datetime) and (hora.hour or hora.minute) else "",
                f"{nombre}, datáfono {datafono}", fuente="Bold"))
        fechas = {r["FECHA"] for r in filas}
        if omitidas:
            datos.avisos.append(f"{nombre}: {omitidas} operación(es) que no son 'COBRO EXITOSO' no se cuentan.")
        if desconocidos:
            datos.avisos.append(f"{nombre}: no reconozco el datáfono " + ", ".join(sorted(desconocidos)) + ".")
    else:
        filas = core.load_redeban(ruta)
        puntos_proc = {identificar_punto(n) for n in core.REDEBAN_STORES.values()} - {None}
        desconocidos = set()
        for r in filas:
            codigo = r["CODIGO ESTABLECIMIENTO"]
            tienda = core.REDEBAN_STORES.get(codigo)
            punto = identificar_punto(tienda) if tienda else None
            if punto is None:
                desconocidos.add(codigo)
                continue
            f = r["FECHA DE TRANSACCION"]
            datos.cobros.setdefault((f, punto), []).append(MovBanco(
                f, float(r["VALOR TOTAL"] or 0), punto, "", r["FRANQUICIA"].title(),
                f"{nombre}, establecimiento …{codigo}", fuente="Redeban"))
        fechas = {r["FECHA DE TRANSACCION"] for r in filas}
        if desconocidos:
            datos.avisos.append(f"{nombre}: no reconozco los establecimientos terminados en "
                                + ", ".join(sorted(desconocidos)) + ".")
    # Solo se revisan los puntos que aparecen en el reporte: si un punto no tiene
    # ni un cobro en todo el periodo (p. ej. Portal Sur en el Redeban de
    # septiembre), lo más probable es que pase tarjetas por otro lado, y marcar
    # todas sus ventas con tarjeta como "no aparecen" serían falsas alarmas.
    cubiertas = _rango(fechas)
    presentes = {p for _, p in datos.cobros}
    ausentes = puntos_proc - presentes
    if ausentes and filas:
        datos.avisos.append(f"{nombre}: no trae ningún cobro de {', '.join(sorted(ausentes))}; "
                            f"sus tarjetas no se revisan con este reporte.")
    puntos_proc = presentes
    for p in puntos_proc:
        datos.cobertura[p] = set(cubiertas)
    if not filas:
        datos.avisos.append(f"{nombre}: no trae transacciones.")
    return tipo, datos, puntos_proc
