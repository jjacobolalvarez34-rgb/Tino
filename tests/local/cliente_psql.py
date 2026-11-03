# -*- coding: utf-8 -*-
"""Un cliente de prueba con las mismas operaciones que panel/datos/cliente.py, sobre psql.

Corre cada consulta como lo hace la API de Supabase: con el rol authenticated y el
usuario en request.jwt.claims, así RLS y las funciones de la base se prueban de verdad.
Solo para un Postgres local de este PC; nunca para Supabase.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PSQL = Path(r"C:\Program Files\PostgreSQL\16\bin\psql.exe")
OPERADORES = {"eq": "=", "gte": ">=", "lte": "<=", "gt": ">", "lt": "<", "neq": "<>"}


# El mismo error que el cliente real, para que el programa no note la diferencia.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from panel.datos.cliente import ErrorBase  # noqa: E402


def _literal(valor):
    return "'" + str(valor).replace("'", "''") + "'"


class ClientePsql:
    def __init__(self, url, usuario):
        if "localhost" not in url and "127.0.0.1" not in url:
            raise SystemExit("cliente_psql solo corre contra un Postgres local.")
        self.url, self.usuario = url, usuario

    def _sql(self, consulta):
        claims = json.dumps({"sub": self.usuario, "role": "authenticated"})
        texto = (f"\\set ON_ERROR_STOP 1\nset role authenticated;\n"
                 f"do $c$ begin perform set_config('request.jwt.claims', {_literal(claims)}, false); end $c$;\n"
                 f"\\set VERBOSITY verbose\n{consulta};\n")
        with tempfile.NamedTemporaryFile("w", suffix=".sql", delete=False, encoding="utf-8",
                                         dir=os.environ.get("TEMP")) as f:
            f.write(texto)
        try:
            # Mensajes del servidor en inglés: en español llegan en la codificación de Windows.
            r = subprocess.run([str(PSQL), "-X", "-q", "-A", "-t", "-f", f.name, self.url], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                               env={**os.environ, "PGCLIENTENCODING": "UTF8", "PGOPTIONS": "-c lc_messages=C"})
        finally:
            os.unlink(f.name)
        if r.returncode != 0:
            m = re.search(r"ERROR:\s+([0-9A-Z]{5}):\s*(.*)", r.stderr)
            raise ErrorBase(m.group(2) if m else r.stderr.strip(), m.group(1) if m else None, r.stderr)
        salida = r.stdout.strip()
        return json.loads(salida) if salida else None

    def leer(self, tabla, filtros=(), columnas="*", orden="id"):
        donde = []
        for col, op, valor in filtros:
            if op == "is":
                donde.append(f"{col} is {valor}")
            else:
                donde.append(f"{col} {OPERADORES[op]} {_literal(valor)}")
        w = (" where " + " and ".join(donde)) if donde else ""
        orden = re.sub(r"\.(asc|desc)\b", r" \1", orden)  # creado_en.desc, como en PostgREST
        return self._sql(f"select coalesce(json_agg(t), '[]') from (select {columnas} from public.{tabla}{w} "
                         f"order by {orden}) t")

    def rpc(self, funcion, argumentos):
        args = ", ".join(f"{k} => {_literal(json.dumps(v) if isinstance(v, (dict, list)) else v)}"
                         for k, v in argumentos.items())
        return self._sql(f"select to_json(public.{funcion}({args}))")

    def cambiar(self, tabla, filtros, valores):
        sets = ", ".join(f"{k} = {_literal(v) if v is not None else 'null'}" for k, v in valores.items())
        donde = " and ".join(f"{c} {OPERADORES[o]} {_literal(v)}" for c, o, v in filtros)
        return self._sql(f"with c as (update public.{tabla} set {sets} where {donde} returning *) "
                         f"select coalesce(json_agg(c), '[]') from c")
