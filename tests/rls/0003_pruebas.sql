-- =============================================================================
-- Pruebas de 0003_importacion.sql
-- Se corre después de las pruebas anteriores y usa sus empresas y usuarios.
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

grant execute on all functions in schema pg_temp to authenticated, anon;

set role authenticated;

-- 1. Subir un archivo -----------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
insert into public.archivo_importado (id, empresa_id, fuente, nombre, hash, filas) values
  ('aaaaaaaa-0000-0000-0000-000000000061', 'aaaaaaaa-0000-0000-0000-000000000000', 'bold', 'bold.xlsx',
   repeat('a', 64), 10);
select pg_temp.ok(true, 'Finanzas sube archivos');

select pg_temp.falla($$insert into public.archivo_importado (empresa_id, fuente, nombre, hash)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'bold', 'otra vez.xlsx', repeat('a', 64))$$,
                     '23505', 'El mismo archivo no entra dos veces, aunque cambie de nombre');
select pg_temp.falla($$insert into public.archivo_importado (empresa_id, fuente, nombre, hash)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'bold', 'x.xlsx', 'corto')$$,
                     '23514', 'Un hash mal formado no entra');
select pg_temp.falla($$insert into public.archivo_importado (empresa_id, fuente, nombre, hash)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'whatsapp', 'x.xlsx', repeat('b', 64))$$,
                     '23514', 'Una fuente inventada no entra');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
insert into public.archivo_importado (empresa_id, fuente, nombre, hash) values
  ('bbbbbbbb-0000-0000-0000-000000000000', 'bold', 'bold.xlsx', repeat('a', 64));
select pg_temp.ok(true, 'Otra empresa puede subir un archivo igual');
select pg_temp.ok((select count(*) from public.archivo_importado) = 1,
                  'El dueño de B solo ve sus archivos');

-- 2. Roles ----------------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$insert into public.archivo_importado (empresa_id, fuente, nombre, hash)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'bold', 'x.xlsx', repeat('c', 64))$$,
                     '42501', 'La asesora no sube archivos');
select pg_temp.ok((select count(*) from public.archivo_importado) = 0, 'La asesora no ve los archivos');

select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
select pg_temp.ok((select count(*) from public.archivo_importado) = 1, 'La encargada ve los archivos de su empresa');

select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.archivo_importado (empresa_id, fuente, nombre, hash)
                       values ('bbbbbbbb-0000-0000-0000-000000000000', 'bold', 'x.xlsx', repeat('d', 64))$$,
                     '42501', 'El dueño de A no sube archivos a B');

-- 3. Errores --------------------------------------------------------------------
insert into public.error_importacion (id, empresa_id, archivo_id, fila_origen, tipo, texto) values
  ('aaaaaaaa-0000-0000-0000-000000000071', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000061', 12, 'nombre_sin_reconocer', 'Angie');
select pg_temp.ok((select count(*) from public.error_importacion where not resuelto) = 1,
                  'Un nombre sin reconocer queda pendiente, con su archivo y su fila');

select pg_temp.falla($$update public.error_importacion set resuelto = true
                       where id = 'aaaaaaaa-0000-0000-0000-000000000071'$$,
                     '23514', 'Resolver un error exige decir cuándo');
update public.error_importacion set resuelto = true, resuelto_en = now(), nota = 'Se decidió a mano'
where id = 'aaaaaaaa-0000-0000-0000-000000000071';
select pg_temp.ok((select count(*) from public.error_importacion where resuelto) = 1, 'Un error se resuelve con nota');

select pg_temp.falla($$insert into public.error_importacion (empresa_id, archivo_id, tipo, texto)
                       values ('bbbbbbbb-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000061', 'otro', 'x')$$,
                     '42501', 'El dueño de A no escribe errores en B');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.error_importacion (empresa_id, archivo_id, tipo, texto)
                       values ('bbbbbbbb-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000061', 'otro', 'x')$$,
                     '23503', 'Un error de B no apunta a un archivo de A');
select pg_temp.ok((select count(*) from public.error_importacion) = 0, 'El dueño de B no ve errores de A');

-- 4. Deshacer un archivo --------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$update public.archivo_importado set estado = 'deshecho'
                       where id = 'aaaaaaaa-0000-0000-0000-000000000061'$$,
                     '23514', 'Deshacer exige decir cuándo y por quién');
update public.archivo_importado
set estado = 'deshecho', deshecho_en = now(), deshecho_por = 'a0000000-0000-0000-0000-00000000000d'
where id = 'aaaaaaaa-0000-0000-0000-000000000061';
select pg_temp.ok((select estado from public.archivo_importado
                   where id = 'aaaaaaaa-0000-0000-0000-000000000061') = 'deshecho',
                  'Un archivo se deshace y sigue en el historial');

insert into public.archivo_importado (empresa_id, fuente, nombre, hash) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'bold', 'corregido.xlsx', repeat('a', 64));
select pg_temp.ok(true, 'Un archivo deshecho se puede volver a subir');

select pg_temp.ok((select count(*) from public.auditoria where tabla = 'archivo_importado'
                   and accion = 'update' and empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000') = 1,
                  'Deshacer queda en auditoría');

-- 5. Nadie borra ----------------------------------------------------------------
with c as (delete from public.archivo_importado returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra archivos');
with c as (delete from public.error_importacion returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra errores');
select pg_temp.falla($$truncate public.archivo_importado cascade$$, '42501', 'Nadie vacía la tabla de archivos');

-- 6. Sin sesión -----------------------------------------------------------------
reset role;
set role anon;
select set_config('request.jwt.claims', '', false);
select pg_temp.ok((select count(*) from public.archivo_importado) = 0
                  and (select count(*) from public.error_importacion) = 0, 'anon no ve archivos ni errores');
reset role;

-- 7. Estructura -----------------------------------------------------------------
select pg_temp.ok(
  not exists (select from pg_tables where schemaname = 'public' and not rowsecurity), 'Todas las tablas tienen RLS');
select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');

\echo 'TODAS LAS PRUEBAS DE 0003 PASARON'
