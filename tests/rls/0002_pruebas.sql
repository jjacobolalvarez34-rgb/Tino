-- =============================================================================
-- Pruebas de 0002_asesoras.sql
-- Se corre después de 0001_pruebas.sql y usa sus empresas y usuarios.
-- =============================================================================

create function pg_temp.como(usuario uuid) returns void language sql as $$
  select set_config('request.jwt.claims', json_build_object('sub', usuario)::text, false);
$$;

create function pg_temp.ok(condicion boolean, prueba text) returns void language plpgsql as $$
begin
  if not condicion then raise exception 'FALLÓ: %', prueba; end if;
  raise notice 'OK  %', prueba;
end $$;

create function pg_temp.falla(consulta text, esperado text, prueba text)
returns void language plpgsql as $$
declare
  v_estado text;
begin
  begin
    execute consulta;
  exception when others then
    get stacked diagnostics v_estado = returned_sqlstate;
    if v_estado = esperado then
      raise notice 'OK  %', prueba;
      return;
    end if;
    raise exception 'FALLÓ: % (dio %, se esperaba %: %)', prueba, v_estado, esperado, sqlerrm;
  end;
  raise exception 'FALLÓ: % (no dio error)', prueba;
end $$;

grant execute on all functions in schema pg_temp to authenticated;

-- Un segundo punto en cada empresa, para probar nombres repetidos.
insert into public.punto_venta (id, empresa_id, codigo, nombre) values
  ('aaaaaaaa-0000-0000-0000-000000000012', 'aaaaaaaa-0000-0000-0000-000000000000', 'P09', 'Punto A9');

set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');

-- 1. Código automático ---------------------------------------------------------
insert into public.asesora (id, empresa_id, nombre_completo) values
  ('aaaaaaaa-0000-0000-0000-000000000022', 'aaaaaaaa-0000-0000-0000-000000000000', 'Primera sin código'),
  ('aaaaaaaa-0000-0000-0000-000000000023', 'aaaaaaaa-0000-0000-0000-000000000000', 'Segunda sin código');
select pg_temp.ok((select array_agg(codigo order by codigo) from public.asesora
                   where id in ('aaaaaaaa-0000-0000-0000-000000000022', 'aaaaaaaa-0000-0000-0000-000000000023'))
                  = array['A002', 'A003'],
                  'Sin código, la base asigna el siguiente de la empresa');

insert into public.asesora (empresa_id, codigo, nombre_completo)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'ESPECIAL', 'Con código propio');
select pg_temp.ok((select count(*) from public.asesora where codigo = 'ESPECIAL') = 1,
                  'Un código escrito a mano se respeta');

insert into public.asesora (empresa_id, nombre_completo)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'Después del código propio');
select pg_temp.ok((select codigo from public.asesora where nombre_completo = 'Después del código propio') = 'A004',
                  'Un código escrito a mano no rompe la secuencia');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
insert into public.asesora (empresa_id, nombre_completo)
values ('bbbbbbbb-0000-0000-0000-000000000000', 'Primera de B');
select pg_temp.ok((select codigo from public.asesora where nombre_completo = 'Primera de B') = 'A002',
                  'Cada empresa lleva su propia secuencia');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$insert into public.asesora (empresa_id, nombre_completo)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'x')$$,
                     '42501', 'La asesora no crea asesoras');

select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.asesora (empresa_id, nombre_completo)
                       values ('bbbbbbbb-0000-0000-0000-000000000000', 'Intrusa')$$,
                     '42501', 'El dueño de A no crea asesoras en B');

-- 2. Alias por punto -----------------------------------------------------------
insert into public.asesora_alias (empresa_id, asesora_id, punto_id, texto_original) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000022',
   'aaaaaaaa-0000-0000-0000-000000000011', 'Leidy'),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000023',
   'aaaaaaaa-0000-0000-0000-000000000012', 'LEIDY');
select pg_temp.ok((select count(distinct asesora_id) from public.asesora_alias
                   where texto_normalizado = 'leidy') = 2,
                  'Dos asesoras se pueden llamar igual en puntos distintos');

select pg_temp.falla($$insert into public.asesora_alias (empresa_id, asesora_id, punto_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000023',
                               'aaaaaaaa-0000-0000-0000-000000000011', 'leidy.')$$,
                     '23505', 'En un mismo punto, un nombre es de una sola asesora');

select pg_temp.falla($$insert into public.asesora_alias (empresa_id, asesora_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000022', 'Sin punto')$$,
                     '23502', 'Un alias no se crea sin punto');

select pg_temp.falla($$insert into public.asesora_alias (empresa_id, asesora_id, punto_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000022',
                               'bbbbbbbb-0000-0000-0000-000000000011', 'Cruce')$$,
                     '23503', 'Un alias de A no apunta a un punto de B');

select pg_temp.ok((select count(*) from public.auditoria
                   where tabla = 'asesora_alias' and despues ->> 'texto_normalizado' = 'leidy') = 2,
                  'Los alias nuevos quedan en auditoría');

reset role;

-- 3. La tabla sigue con sus políticas -------------------------------------------
select pg_temp.ok((select count(*) from pg_policies
                   where schemaname = 'public' and tablename = 'asesora_alias') = 3,
                  'asesora_alias conserva sus tres políticas');

select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');

\echo 'TODAS LAS PRUEBAS DE 0002 PASARON'
