# -*- coding: utf-8 -*-
"""
Día normalizado: estructura neutral sobre la que trabajan las reglas.
Ningún campo depende de letras de columna ni de filas fijas; los lectores
(xlsx hoy, Google Sheets/Supabase después) son los únicos que saben de celdas.
"""
from dataclasses import dataclass, field
import datetime as dt
from typing import Optional


@dataclass
class Producto:
    fila: int
    nombre: str
    precio: float = 0.0
    inv_inicial: float = 0.0
    entradas: float = 0.0
    salidas_siigo: float = 0.0       # F
    efectivo_cant: float = 0.0       # L
    efectivo_desc_unit: float = 0.0  # M
    salidas_tot: float = 0.0         # G
    inv_final: float = 0.0           # E
    valor: float = 0.0               # H
    regalos_cant: float = 0.0        # I
    regalos_valor: float = 0.0       # J
    descuento: float = 0.0           # K
    efectivo_total: float = 0.0      # N


@dataclass
class Pagos:
    transferencias: list = field(default_factory=list)  # [(fila, monto)]
    debito: list = field(default_factory=list)
    credito: list = field(default_factory=list)


@dataclass
class Caja:
    efectivo_contado: Optional[float] = None
    addi: Optional[float] = None
    consignacion: Optional[float] = None
    tarjetas: Optional[float] = None
    transferencias: Optional[float] = None
    gastos: Optional[float] = None
    descuentos: Optional[float] = None
    descuentos_idunn: Optional[float] = None
    regalos: Optional[float] = None
    regalos_idunn: Optional[float] = None
    danados: Optional[float] = None
    devoluciones: Optional[float] = None
    cambios: Optional[float] = None
    efectivo_apartado: Optional[float] = None
    base: Optional[float] = None
    sencillo_recibido: Optional[float] = None
    total: Optional[float] = None
    descuadre: Optional[float] = None
    cantidad_facturas: Optional[float] = None
    valor_teorico: Optional[float] = None


@dataclass
class DiaPunto:
    fecha: Optional[dt.date]          # la que dice la hoja (B3)
    fecha_hoja: Optional[dt.date]     # la que implica el nombre de la hoja
    punto: str
    hoja: str
    asesoras: list = field(default_factory=list)
    asesoras_texto: str = ""
    productos: list = field(default_factory=list)
    pagos: Pagos = field(default_factory=Pagos)
    caja: Caja = field(default_factory=Caja)
    observaciones: list = field(default_factory=list)  # [(celda, texto)]
    # celda -> fórmula (solo celdas con fórmula) y celda -> valor crudo
    formulas: dict = field(default_factory=dict)
    # rol -> celda, para que las reglas puedan citar evidencia y comparar
    # fórmulas sin saber letras: "caja.base" -> "B204", "col.valor" -> "H", etc.
    celdas: dict = field(default_factory=dict)
    fila_totales: Optional[int] = None
    valores: dict = field(default_factory=dict)


@dataclass
class FilaDescFact:
    fila: int
    dia: Optional[int]
    asesor: str = ""
    descuadre: Optional[float] = None
    venta: Optional[float] = None
    facturas: Optional[float] = None
    efectivo_sin_facturar: Optional[float] = None
    saldo: Optional[float] = None
    entregado: Optional[float] = None
    formulas: dict = field(default_factory=dict)  # columna -> fórmula


@dataclass
class Evidencia:
    hoja: str
    celda: str = ""
    valor: object = None
    formula: str = ""
    nota: str = ""

    def to_dict(self):
        v = self.valor
        if isinstance(v, (dt.date, dt.datetime)):
            v = v.isoformat()
        return {"hoja": self.hoja, "celda": self.celda, "valor": v,
                "formula": self.formula, "nota": self.nota}


@dataclass
class Hallazgo:
    punto: str
    fecha: dt.date
    regla: str           # "R01"...
    tipo: str            # "causa" (explica descuadre) | "señal" | "integridad"
    severidad: str       # "alta" | "media" | "baja" | "info"
    texto: str
    monto: float = 0.0   # cuánto del descuadre explica (con signo del descuadre)
    evidencia: list = field(default_factory=list)

    def to_dict(self):
        return {
            "punto": self.punto,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "regla": self.regla, "tipo": self.tipo, "severidad": self.severidad,
            "texto": self.texto, "monto": self.monto,
            "evidencia": [e.to_dict() for e in self.evidencia],
        }
