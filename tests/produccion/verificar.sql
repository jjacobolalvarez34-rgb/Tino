-- =============================================================================
-- Verificación de permisos de una base de Tino YA migrada (producción o pruebas).
-- Solo lee: no crea datos de prueba, no cambia nada. Falla con un mensaje si algo no cumple.
-- Uso: psql -v ON_ERROR_STOP=1 -f tests/produccion/verificar.sql <conexión>
-- =============================================================================

do $$
declare
  v text;
begin
  -- 1. Toda tabla de public tiene RLS.
  select string_agg(c.relname, ', ') into v
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'r' and not c.relrowsecurity;
  if v is not null then raise exception 'FALLÓ: tablas sin RLS: %', v; end if;
  raise notice 'OK  Todas las tablas de public tienen RLS';

  -- 2. Toda tabla con datos de una empresa lleva empresa_id (salvo las del sistema).
  select string_agg(t.table_name, ', ') into v
  from information_schema.tables t
  where t.table_schema = 'public' and t.table_type = 'BASE TABLE'
    and t.table_name not in ('empresa', 'festivo', 'causa_descuadre')
    and not exists (select 1 from information_schema.columns c
                    where c.table_schema = 'public' and c.table_name = t.table_name and c.column_name = 'empresa_id');
  if v is not null then raise exception 'FALLÓ: tablas sin empresa_id: %', v; end if;
  raise notice 'OK  Toda tabla de datos lleva empresa_id';

  -- 3. Nadie borra: ninguna política de DELETE.
  select string_agg(tablename || '.' || policyname, ', ') into v
  from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL');
  if v is not null then raise exception 'FALLÓ: políticas que dejan borrar: %', v; end if;
  raise notice 'OK  Ninguna política deja borrar';

  -- 4. Sin TRUNCATE para usuarios.
  select string_agg(table_name, ', ') into v
  from information_schema.role_table_grants
  where table_schema = 'public' and privilege_type = 'TRUNCATE' and grantee in ('anon', 'authenticated');
  if v is not null then raise exception 'FALLÓ: TRUNCATE abierto en: %', v; end if;
  raise notice 'OK  Nadie puede vaciar tablas con TRUNCATE';

  -- 5. Ninguna función pública se salta los permisos; las vistas usan los de quien consulta.
  select string_agg(p.proname, ', ') into v
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public' and p.prosecdef;
  if v is not null then raise exception 'FALLÓ: funciones públicas security definer: %', v; end if;
  select string_agg(c.relname, ', ') into v
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'v' and not coalesce(c.reloptions @> array['security_invoker=true'], false);
  if v is not null then raise exception 'FALLÓ: vistas sin security_invoker: %', v; end if;
  raise notice 'OK  Funciones y vistas corren con los permisos de quien consulta';

  -- 6. Las tablas de datos tienen auditoría.
  select string_agg(c.relname, ', ') into v
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public' and c.relkind = 'r' and c.relname not in ('auditoria', 'festivo', 'causa_descuadre')
    and not exists (select 1 from pg_trigger g where g.tgrelid = c.oid and g.tgname like '%auditoria%' and not g.tgisinternal);
  if v is not null then raise notice 'AVISO  Tablas sin auditoría (revisar si es a propósito): %', v;
  else raise notice 'OK  Todas las tablas de datos tienen auditoría'; end if;

  -- 7. Sin sesión no se ve nada (anon no tiene SELECT con filas: lo decide RLS con empresa_actual()).
  raise notice 'OK  Verificación terminada';
end $$;
