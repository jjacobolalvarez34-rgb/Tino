# -*- coding: utf-8 -*-
"""
historial_db.py — registro histórico de verificaciones (Bold/Redeban contra
Bancolombia), en SQLite. Módulo de persistencia puro: no sabe nada de Excel,
PDF ni Tkinter/web. `bridge.py` arma las filas a partir de los resultados de
`verify.py` y se las pasa a `record_verification`.

Vive en la carpeta de datos del usuario (no en la carpeta de instalación),
para que sobreviva reinstalaciones/actualizaciones del programa.
"""
import os
import sqlite3
import datetime as dt

APPDATA = os.getenv("APPDATA") or os.path.expanduser("~")
DB_DIR = os.path.join(APPDATA, "SuiteIrina")
DB_PATH = os.path.join(DB_DIR, "historial.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    xlsx_path TEXT,
    pdf_path TEXT
);

CREATE TABLE IF NOT EXISTS resultados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    tipo TEXT NOT NULL,              -- 'bold' | 'redeban'
    punto_venta TEXT NOT NULL,
    franquicia TEXT,
    fecha TEXT NOT NULL,             -- ISO date (fecha entrada/canje)
    computed_total REAL NOT NULL,
    bank_total REAL NOT NULL,
    matched INTEGER NOT NULL,
    cruzado INTEGER NOT NULL DEFAULT 0,
    diferencia REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resultados_run ON resultados(run_id);
CREATE INDEX IF NOT EXISTS idx_resultados_fecha ON resultados(fecha);
CREATE INDEX IF NOT EXISTS idx_resultados_punto ON resultados(punto_venta);
"""


def _conn():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _conn()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def record_verification(xlsx_path, pdf_path, rows):
    """rows: lista de dicts ya normalizados:
    {tipo, punto_venta, franquicia, fecha (date o iso str), computed_total,
     bank_total, matched (bool), cruzado (bool)}.
    Devuelve el id del run creado (o None si `rows` viene vacío)."""
    if not rows:
        return None
    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO runs (ts, xlsx_path, pdf_path) VALUES (?, ?, ?)",
            (dt.datetime.now().isoformat(timespec="seconds"), xlsx_path, pdf_path),
        )
        run_id = cur.lastrowid
        for r in rows:
            fecha = r["fecha"]
            if hasattr(fecha, "isoformat"):
                fecha = fecha.isoformat()
            computed = float(r["computed_total"])
            bank = float(r["bank_total"])
            conn.execute(
                "INSERT INTO resultados (run_id, tipo, punto_venta, franquicia, fecha, "
                "computed_total, bank_total, matched, cruzado, diferencia) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, r["tipo"], r["punto_venta"], r.get("franquicia"), fecha,
                 computed, bank, int(bool(r["matched"])), int(bool(r.get("cruzado"))),
                 computed - bank),
            )
        conn.commit()
        return run_id
    finally:
        conn.close()


def _date_filter(date_from, date_to):
    clause, params = [], []
    if date_from:
        clause.append("fecha >= ?")
        params.append(date_from)
    if date_to:
        clause.append("fecha <= ?")
        params.append(date_to)
    return (" AND " + " AND ".join(clause)) if clause else "", params


def get_summary(date_from=None, date_to=None):
    """Resumen general: totales esperados por tipo, cuánto no coincidió, y
    la diferencia (total esperado - lo que no coincidió)."""
    where, params = _date_filter(date_from, date_to)
    conn = _conn()
    try:
        rows = conn.execute(
            f"SELECT tipo, matched, cruzado, computed_total, bank_total, diferencia "
            f"FROM resultados WHERE 1=1 {where}", params
        ).fetchall()
    finally:
        conn.close()

    total_bold = sum(r["computed_total"] for r in rows if r["tipo"] == "bold")
    total_redeban = sum(r["computed_total"] for r in rows if r["tipo"] == "redeban")
    total_general = total_bold + total_redeban

    no_coinciden = [r for r in rows if not r["matched"] and not r["cruzado"]]
    total_no_coincidio = sum(r["computed_total"] for r in no_coinciden)
    monto_diferencia_no_coincidio = sum(r["diferencia"] for r in no_coinciden)

    cruzados = [r for r in rows if r["cruzado"]]

    fallidas_bold = sum(1 for r in no_coinciden if r["tipo"] == "bold")
    fallidas_redeban = sum(1 for r in no_coinciden if r["tipo"] == "redeban")

    return {
        "total_bold": total_bold,
        "total_redeban": total_redeban,
        "total_general": total_general,
        "total_no_coincidio": total_no_coincidio,
        "diferencia": total_general - total_no_coincidio,
        "monto_diferencia_no_coincidio": monto_diferencia_no_coincidio,
        "revisados": len(rows),
        "coinciden": sum(1 for r in rows if r["matched"] and not r["cruzado"]),
        "cruzados": len(cruzados),
        "no_coinciden": len(no_coinciden),
        "fallidas_bold": fallidas_bold,
        "fallidas_redeban": fallidas_redeban,
    }


def get_por_punto_venta(date_from=None, date_to=None, tipo=None):
    """Agrupado por punto de venta: total esperado, cuántas veces no
    coincidió, y el monto en diferencia. Si `tipo` se da ('bold'/'redeban'),
    filtra solo ese motor."""
    where, params = _date_filter(date_from, date_to)
    tipo_clause = ""
    if tipo:
        tipo_clause = " AND tipo = ?"
        params.append(tipo)
    conn = _conn()
    try:
        rows = conn.execute(
            f"SELECT punto_venta, tipo, matched, cruzado, computed_total, diferencia "
            f"FROM resultados WHERE 1=1 {where}{tipo_clause}", params
        ).fetchall()
    finally:
        conn.close()

    agg = {}
    for r in rows:
        key = (r["punto_venta"], r["tipo"])
        a = agg.setdefault(key, {
            "punto_venta": r["punto_venta"], "tipo": r["tipo"],
            "total_esperado": 0.0, "fallidas": 0, "monto_diferencia": 0.0, "revisadas": 0,
        })
        a["revisadas"] += 1
        a["total_esperado"] += r["computed_total"]
        if not r["matched"] and not r["cruzado"]:
            a["fallidas"] += 1
            a["monto_diferencia"] += r["diferencia"]

    result = list(agg.values())
    result.sort(key=lambda a: a["fallidas"], reverse=True)
    return result


def get_timeseries(date_from=None, date_to=None):
    """Fallidas por fecha, para graficar tendencia en el tiempo."""
    where, params = _date_filter(date_from, date_to)
    conn = _conn()
    try:
        rows = conn.execute(
            f"SELECT fecha, matched, cruzado FROM resultados WHERE 1=1 {where} ORDER BY fecha",
            params
        ).fetchall()
    finally:
        conn.close()
    by_date = {}
    for r in rows:
        d = by_date.setdefault(r["fecha"], {"fecha": r["fecha"], "revisadas": 0, "fallidas": 0})
        d["revisadas"] += 1
        if not r["matched"] and not r["cruzado"]:
            d["fallidas"] += 1
    return sorted(by_date.values(), key=lambda d: d["fecha"])


def get_runs(limit=30):
    conn = _conn()
    try:
        runs = conn.execute(
            "SELECT id, ts, xlsx_path, pdf_path FROM runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        out = []
        for run in runs:
            counts = conn.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN matched=0 AND cruzado=0 THEN 1 ELSE 0 END) AS fallidas "
                "FROM resultados WHERE run_id = ?", (run["id"],)
            ).fetchone()
            out.append({
                "id": run["id"], "ts": run["ts"], "xlsx_path": run["xlsx_path"],
                "pdf_path": run["pdf_path"], "total": counts["total"] or 0,
                "fallidas": counts["fallidas"] or 0,
            })
        return out
    finally:
        conn.close()
