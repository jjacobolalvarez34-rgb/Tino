# -*- coding: utf-8 -*-
"""
Historial propio del módulo Cierre del día: %APPDATA%\\SuiteIrina\\cierre.db.

Revisar un día otra vez REEMPLAZA el resultado anterior de ese día y punto (no
duplica), pero conserva lo que ya se marcó: si un hallazgo vuelve a salir igual
(misma regla y mismo texto), mantiene su revisión y su nota.
"""
import datetime as dt
import hashlib
import json
import os
import sqlite3

REVISIONES = ("pendiente", "revisado", "error confirmado", "descartado")

ESQUEMA = """
CREATE TABLE IF NOT EXISTS dias (
    fecha TEXT NOT NULL,
    punto TEXT NOT NULL,
    asesoras TEXT NOT NULL DEFAULT '[]',
    venta REAL,
    descuadre REAL,
    monto_explicado REAL,
    monto_sin_explicar REAL,
    estado TEXT NOT NULL,
    causa_principal TEXT,
    fuentes TEXT NOT NULL DEFAULT '[]',
    descuentos REAL DEFAULT 0,
    regalos REAL DEFAULT 0,
    ajustes REAL DEFAULT 0,
    hoja TEXT,
    archivo TEXT,
    avisos TEXT NOT NULL DEFAULT '[]',
    revisado_en TEXT NOT NULL,
    PRIMARY KEY (fecha, punto)
);

CREATE TABLE IF NOT EXISTS hallazgos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    punto TEXT NOT NULL,
    regla TEXT NOT NULL,
    tipo TEXT NOT NULL,
    severidad TEXT NOT NULL,
    monto REAL NOT NULL DEFAULT 0,
    texto TEXT NOT NULL,
    evidencia TEXT NOT NULL DEFAULT '[]',
    firma TEXT NOT NULL,
    orden INTEGER NOT NULL DEFAULT 0,
    revision TEXT NOT NULL DEFAULT 'pendiente',
    nota TEXT,
    fecha_revision TEXT,
    UNIQUE (fecha, punto, firma)
);

CREATE TABLE IF NOT EXISTS asesoras_dia (
    fecha TEXT NOT NULL,
    punto TEXT NOT NULL,
    asesora TEXT NOT NULL,
    PRIMARY KEY (fecha, punto, asesora)
);

CREATE INDEX IF NOT EXISTS idx_h_revision ON hallazgos (revision, fecha);
CREATE INDEX IF NOT EXISTS idx_h_dia ON hallazgos (fecha, punto);
"""


def firma(h):
    base = f"{h['regla']}|{h['tipo']}|{h['texto']}"
    return hashlib.sha1(base.encode("utf-8")).hexdigest()[:16]


class HistorialCierre:
    def __init__(self, ruta):
        self.ruta = ruta
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with self._conn() as c:
            c.executescript(ESQUEMA)

    def _conn(self):
        c = sqlite3.connect(self.ruta)
        c.row_factory = sqlite3.Row
        return c

    # ------------------------------------------------------------------
    def guardar_dia(self, fila, extra):
        """fila: resultado de SesionCierre para un punto (dict de la interfaz).
        extra: {descuentos, regalos, ajustes, fuentes}. Devuelve los hallazgos
        con su id, revisión y nota ya fusionados con lo marcado antes."""
        fecha, punto = fila["fecha"], fila["punto"]
        ahora = dt.datetime.now().isoformat(timespec="seconds")
        with self._conn() as c:
            previas = {r["firma"]: r for r in c.execute(
                "SELECT firma, revision, nota, fecha_revision FROM hallazgos WHERE fecha=? AND punto=?",
                (fecha, punto))}
            c.execute("DELETE FROM hallazgos WHERE fecha=? AND punto=?", (fecha, punto))
            c.execute("DELETE FROM asesoras_dia WHERE fecha=? AND punto=?", (fecha, punto))
            causa = fila["causa_principal"]
            c.execute(
                "INSERT OR REPLACE INTO dias (fecha, punto, asesoras, venta, descuadre, monto_explicado, "
                "monto_sin_explicar, estado, causa_principal, fuentes, descuentos, regalos, ajustes, hoja, "
                "archivo, avisos, revisado_en) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (fecha, punto, json.dumps(fila["asesoras"], ensure_ascii=False), fila["venta"],
                 fila["descuadre"], fila["explicado"], fila["sin_explicar"], fila["estado"],
                 json.dumps(causa, ensure_ascii=False) if causa else None,
                 json.dumps(extra.get("fuentes", []), ensure_ascii=False),
                 extra.get("descuentos", 0), extra.get("regalos", 0), extra.get("ajustes", 0),
                 fila.get("hoja"), fila.get("archivo"),
                 json.dumps(fila.get("avisos", []), ensure_ascii=False), ahora))
            for a in fila["asesoras"]:
                c.execute("INSERT OR IGNORE INTO asesoras_dia (fecha, punto, asesora) VALUES (?,?,?)",
                          (fecha, punto, a))
            vistos = set()
            for orden, h in enumerate(fila["hallazgos"]):
                f = firma(h)
                if f in vistos:       # dos hallazgos idénticos el mismo día: uno basta
                    continue
                vistos.add(f)
                prev = previas.get(f)
                c.execute(
                    "INSERT INTO hallazgos (fecha, punto, regla, tipo, severidad, monto, texto, evidencia, "
                    "firma, orden, revision, nota, fecha_revision) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (fecha, punto, h["regla"], h["tipo"], h["severidad"], h["monto"], h["texto"],
                     json.dumps(h["evidencia"], ensure_ascii=False), f, orden,
                     prev["revision"] if prev else "pendiente", prev["nota"] if prev else None,
                     prev["fecha_revision"] if prev else None))
        return self.hallazgos_dia(fecha, punto)

    def hallazgos_dia(self, fecha, punto):
        with self._conn() as c:
            return [self._h(r) for r in c.execute(
                "SELECT * FROM hallazgos WHERE fecha=? AND punto=? ORDER BY orden", (fecha, punto))]

    @staticmethod
    def _h(r):
        return {"id": r["id"], "punto": r["punto"], "fecha": r["fecha"], "regla": r["regla"],
                "tipo": r["tipo"], "severidad": r["severidad"], "monto": r["monto"], "texto": r["texto"],
                "evidencia": json.loads(r["evidencia"]), "revision": r["revision"], "nota": r["nota"],
                "fecha_revision": r["fecha_revision"]}

    def marcar(self, hallazgo_id, revision, nota):
        if revision not in REVISIONES:
            raise ValueError(f"Revisión no válida: {revision}")
        cuando = None if revision == "pendiente" else dt.datetime.now().isoformat(timespec="seconds")
        with self._conn() as c:
            n = c.execute("UPDATE hallazgos SET revision=?, nota=?, fecha_revision=? WHERE id=?",
                          (revision, (nota or "").strip() or None, cuando, hallazgo_id)).rowcount
            if not n:
                raise ValueError("Ese hallazgo ya no existe (¿se volvió a revisar el día?).")
            return self._h(c.execute("SELECT * FROM hallazgos WHERE id=?", (hallazgo_id,)).fetchone())

    # ------------------------------------------------------------------
    def dia(self, fecha, punto):
        with self._conn() as c:
            r = c.execute("SELECT * FROM dias WHERE fecha=? AND punto=?", (fecha, punto)).fetchone()
        return self._dia(r) if r else None

    @staticmethod
    def _dia(r):
        return {"fecha": r["fecha"], "punto": r["punto"], "asesoras": json.loads(r["asesoras"]),
                "venta": r["venta"], "descuadre": r["descuadre"], "explicado": r["monto_explicado"],
                "sin_explicar": r["monto_sin_explicar"], "estado": r["estado"],
                "causa_principal": json.loads(r["causa_principal"]) if r["causa_principal"] else None,
                "fuentes": json.loads(r["fuentes"]), "descuentos": r["descuentos"], "regalos": r["regalos"],
                "ajustes": r["ajustes"], "hoja": r["hoja"], "archivo": r["archivo"],
                "avisos": json.loads(r["avisos"]), "revisado_en": r["revisado_en"]}

    def fechas(self):
        with self._conn() as c:
            return [r[0] for r in c.execute("SELECT DISTINCT fecha FROM dias ORDER BY fecha")]

    def meses(self):
        return sorted({f[:7] for f in self.fechas()})

    def dias_mes(self, mes, punto=None):
        q, p = "SELECT * FROM dias WHERE substr(fecha,1,7)=?", [mes]
        if punto:
            q += " AND punto=?"
            p.append(punto)
        with self._conn() as c:
            return [self._dia(r) for r in c.execute(q + " ORDER BY fecha", p)]

    def conteo_pendientes(self, mes=None, punto=None, incluir_menores=False):
        q = "SELECT fecha, punto, COUNT(*) n FROM hallazgos WHERE revision='pendiente'"
        p = []
        if not incluir_menores:
            q += " AND " + _FILTRO_MAYORES
        if mes:
            q += " AND substr(fecha,1,7)=?"
            p.append(mes)
        if punto:
            q += " AND punto=?"
            p.append(punto)
        with self._conn() as c:
            return {(r["fecha"], r["punto"]): r["n"] for r in c.execute(q + " GROUP BY fecha, punto", p)}

    def pendientes(self, incluir_menores=False, limite=500):
        q = "SELECT * FROM hallazgos WHERE revision='pendiente'"
        if not incluir_menores:
            q += " AND " + _FILTRO_MAYORES
        with self._conn() as c:
            return [self._h(r) for r in c.execute(q + " ORDER BY fecha, punto, orden LIMIT ?", (limite,))]

    def hallazgos_mes(self, mes):
        with self._conn() as c:
            return [self._h(r) for r in c.execute(
                "SELECT * FROM hallazgos WHERE substr(fecha,1,7)=? ORDER BY fecha, punto, orden", (mes,))]


# "Menores" = avisos de plantilla de severidad baja/info (p. ej. errores que se
# arrastran todos los días). No se esconden: se muestran aparte si se piden.
_FILTRO_MAYORES = "NOT (tipo='integridad' AND severidad IN ('baja','info'))"
