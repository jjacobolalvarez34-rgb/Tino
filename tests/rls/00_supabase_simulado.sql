-- Simula lo mínimo de Supabase para probar migraciones en un Postgres local.
-- NO se aplica en Supabase: allá esto ya existe.
create role anon nologin;
create role authenticated nologin;
create role service_role nologin bypassrls;
create schema auth;
create table auth.users (id uuid primary key);
create function auth.uid() returns uuid language sql stable as $$
  select nullif(nullif(current_setting('request.jwt.claims', true), '')::json ->> 'sub', '')::uuid
$$;
grant usage on schema auth to anon, authenticated, service_role;
grant execute on function auth.uid() to anon, authenticated, service_role;
-- Igual que Supabase: todos los permisos en tablas nuevas, TRUNCATE incluido.
-- Quien limita es la migración, y por eso se prueba aquí. A confirmar en Supabase.
alter default privileges in schema public grant all on tables to anon, authenticated, service_role;
grant usage on schema public to anon, authenticated, service_role;
