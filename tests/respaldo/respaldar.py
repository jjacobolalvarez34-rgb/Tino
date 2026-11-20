# -*- coding: utf-8 -*-
"""Respaldo y prueba de restauración de una base de Tino, todo en D:.

  respaldar <conexión> <carpeta>          -> pg_dump en formato propio (.dump), con fecha
  restaurar <archivo.dump> <base local>   -> lo restaura en una base NUEVA del Postgres local
  comparar  <conexión origen> <conexión restaurada>
                                          -> cuenta filas de cada tabla de public en las dos y
                                             dice si son iguales

La conexión se lee de un archivo JSON fuera del repositorio (clave "conexion"), para que la
clave de la base nunca quede en la línea de comandos ni en el historial:
  python tests/respaldo/respaldar.py respaldar D:/Repositorios/Tino-datos/produccion.json D:/Repositorios/Tino-datos/respaldos

Para una base local se puede pasar la URL directa (solo si es localhost).
"""
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")
ENV = {**os.environ, "PGCLIENTENCODING": "UTF8"}


def conexion(arg):
    if arg.startswith("postgres"):
        if "localhost" not in arg and "127.0.0.1" not in arg:
            raise SystemExit("Una conexión remota va en un archivo JSON, no en la línea de comandos.")
        return arg
    valor = json.loads(Path(arg).read_text(encoding="utf-8")).get("conexion", "")
    if not valor:
        raise SystemExit(f"{arg} no tiene «conexion».")
    return valor


def correr(*args):
    r = subprocess.run([str(a) for a in args], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit(r.stderr.strip()[-600:])
    return r.stdout


def respaldar(origen, carpeta):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"tino-{dt.datetime.now():%Y%m%d-%H%M}.dump"
    # Solo los esquemas de Tino; los de Supabase (auth, storage…) los respalda Supabase.
    correr(BIN / "pg_dump", "--format=custom", "--no-owner", "--no-privileges", "--schema=public", "--schema=app",
           f"--file={destino}", conexion(origen))
    # Los ids de los accesos (auth.users): las tablas de Tino apuntan a ellos. Solo el id; los
    # accesos completos (correos, claves) los guarda el respaldo de Supabase.
    ids = correr(BIN / "psql", "-At", "-c", "select id from auth.users order by id", conexion(origen))
    destino.with_suffix(".accesos.txt").write_text(ids, encoding="utf-8")
    print("respaldo:", destino, f"{destino.stat().st_size / 1e6:.1f} MB", "·", len(ids.split()), "accesos")


def restaurar(archivo, base):
    url = f"postgresql://postgres@localhost:55433/postgres"
    correr(BIN / "psql", "-q", "-c", f'drop database if exists "{base}";', "-c", f'create database "{base}";', url)
    destino = url.rsplit("/", 1)[0] + f"/{base}"
    # Los roles y esquemas de Supabase que las tablas esperan (auth.uid(), authenticated…).
    simulado = Path(__file__).resolve().parents[1] / "rls" / "00_supabase_simulado.sql"
    for linea in ("anon", "authenticated", "service_role"):
        correr(BIN / "psql", "-q", "-c",
               f"do $$ begin if not exists (select from pg_roles where rolname = '{linea}') then create role {linea} nologin; end if; end $$;",
               destino)
    sql = "\n".join(l for l in simulado.read_text(encoding="utf-8").splitlines() if not l.startswith("create role"))
    r = subprocess.run([str(BIN / "psql"), "-q", "-v", "ON_ERROR_STOP=1", "-f", "-", destino], input=sql, text=True,
                       capture_output=True, env=ENV)
    if r.returncode != 0:
        raise SystemExit(r.stderr[-400:])
    accesos = Path(archivo).with_suffix(".accesos.txt")
    if accesos.exists():
        valores = ",".join(f"('{x}')" for x in accesos.read_text(encoding="utf-8").split())
        if valores:
            correr(BIN / "psql", "-q", "-c", f"insert into auth.users (id) values {valores} on conflict do nothing;", destino)
    # El respaldo trae su propio esquema public: la base nueva lo deja vacío para recibirlo.
    correr(BIN / "psql", "-q", "-c",
           "create schema if not exists extensions; create extension if not exists pgcrypto with schema extensions; "
           "create extension if not exists btree_gist with schema extensions;", "-c", "drop schema if exists public cascade;",
           destino)
    r = subprocess.run([str(BIN / "pg_restore"), "--no-owner", "--no-privileges", "--exit-on-error", f"--dbname={destino}",
                        str(archivo)], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)
    if r.returncode != 0:
        raise SystemExit(r.stderr.strip()[-600:])
    print("restaurado en", base)
    return destino


CONTAR = """select string_agg(format('%s=%s', t.tablename,
  (xpath('/row/n/text()', query_to_xml(format('select count(*) as n from public.%I', t.tablename), false, true, '')))[1]::text), ' ' order by t.tablename)
from pg_tables t where t.schemaname = 'public'"""


def contar(url):
    return dict(x.split("=") for x in correr(BIN / "psql", "-At", "-c", CONTAR, url).strip().split())


def comparar(origen, copia):
    a, b = contar(conexion(origen)), contar(conexion(copia))
    distintas = {t: (a.get(t), b.get(t)) for t in sorted(set(a) | set(b)) if a.get(t) != b.get(t)}
    print(f"{len(a)} tablas, {sum(int(v) for v in a.values())} filas en el origen")
    if distintas:
        print("DIFERENCIAS:", distintas)
        raise SystemExit(1)
    print("La copia restaurada tiene exactamente las mismas filas en cada tabla.")


if __name__ == "__main__":
    accion, *resto = sys.argv[1:]
    {"respaldar": respaldar, "restaurar": restaurar, "comparar": comparar}[accion](*resto)
