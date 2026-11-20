# -*- coding: utf-8 -*-
"""Aplica las migraciones de db/migrations a una base nueva (producción) y verifica permisos.

Cada migración va en su propia transacción: si una falla, esa no queda a medias y el script se
detiene ahí. Una base que ya tiene tablas de Tino no se toca, salvo que se diga desde cuál
migración seguir.

Uso: python tests/produccion/aplicar_migraciones.py <produccion.json fuera del repo> [--desde 0012]
     (para probarlo en local se puede pasar una URL postgresql://...@localhost)
"""
import json
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PSQL = r"C:\Program Files\PostgreSQL\16\bin\psql.exe"
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


def psql(url, *args, entrada=None):
    return subprocess.run([PSQL, "-X", "-q", "-v", "ON_ERROR_STOP=1", *args, url], capture_output=True, text=True,
                          env=ENV, input=entrada, stdin=None if entrada is not None else subprocess.DEVNULL)


def main():
    url = conexion(sys.argv[1])
    desde = sys.argv[sys.argv.index("--desde") + 1] if "--desde" in sys.argv else None
    hay = psql(url, "-At", "-c", "select to_regclass('public.empresa') is not null")
    if hay.returncode != 0:
        raise SystemExit("No se pudo conectar: " + hay.stderr.strip()[-300:])
    if hay.stdout.strip() == "t" and not desde:
        raise SystemExit("Esa base ya tiene tablas de Tino. Para seguir desde una migración: --desde 0012")
    migraciones = sorted((RAIZ / "db" / "migrations").glob("*.sql"))
    if desde:
        migraciones = [m for m in migraciones if m.name >= desde]
    for m in migraciones:
        r = psql(url, "-1", "-f", str(m))
        if r.returncode != 0:
            raise SystemExit(f"FALLÓ {m.name}: {r.stderr.strip()[-500:]}")
        print("aplicada", m.name)
    r = psql(url, "-f", str(RAIZ / "tests" / "produccion" / "verificar.sql"))
    print("\n".join(l.split("NOTICE:  ")[-1] for l in r.stderr.splitlines() if "NOTICE" in l or "FALL" in l))
    if r.returncode != 0:
        raise SystemExit("La verificación de permisos falló.")


if __name__ == "__main__":
    main()
