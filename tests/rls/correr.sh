#!/usr/bin/env bash
# Corre las migraciones y las pruebas de permisos en una base local de Postgres.
# Uso: ./tests/rls/correr.sh "postgresql://postgres@localhost:5432/postgres"
# La base cuadre_test se borra y se crea de nuevo en cada corrida.
# En Windows, psql vive en C:\Program Files\PostgreSQL\16\bin: agrégalo al PATH.
set -euo pipefail
URL="${1:?Pasa la URL de un Postgres local (nunca la de Supabase)}"
DIR="$(cd "$(dirname "$0")" && pwd)"
RAIZ="$DIR/../.."

# Este script borra una base. Solo corre contra un servidor de esta máquina.
case "$URL" in
  *@localhost[:/]*|*@127.0.0.1[:/]*|*//localhost[:/]*|*//127.0.0.1[:/]*) ;;
  *) echo "Este script solo corre en un Postgres local: $URL" >&2; exit 1 ;;
esac

# En Windows, psql no asume UTF-8 y los archivos lo son.
export PGCLIENTENCODING=UTF8

# La URL va de última: en Windows, psql ignora las opciones que vienen después.
psql -q -c "drop database if exists cuadre_test;" -c "create database cuadre_test;" "$URL"
# La misma URL, apuntando a la base cuadre_test.
TEST_URL="$(echo "$URL" | sed -E 's#/[^/?]*(\?|$)#/cuadre_test\1#')"

# Roles de Supabase: se crean una vez por servidor.
psql -q -c "do \$\$ begin
  if not exists (select from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select from pg_roles where rolname = 'service_role') then create role service_role nologin bypassrls; end if;
end \$\$;" "$TEST_URL"

grep -v '^create role' "$DIR/00_supabase_simulado.sql" | psql -q -v ON_ERROR_STOP=1 -f - "$TEST_URL"

for m in "$RAIZ"/db/migrations/*.sql; do
  echo "Aplicando $(basename "$m")"
  psql -q -v ON_ERROR_STOP=1 -f "$m" "$TEST_URL"
done

for t in "$DIR"/0*_pruebas.sql; do
  echo "Probando $(basename "$t")"
  psql -q -v ON_ERROR_STOP=1 -o /dev/null -f "$t" "$TEST_URL" 2>&1 | sed -E 's/^psql:.*\.sql:[0-9]+: //; s/^NOTICE:  //'
done
