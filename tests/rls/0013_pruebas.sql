-- =============================================================================
-- Pruebas de 0013_archivos_en_cola.sql (la tabla; Storage solo existe en Supabase)
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
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
insert into public.archivo_en_cola (id, empresa_id, ruta, nombre, tamano, hash) values
  ('aaaaaaaa-0000-0000-0000-0000000013c1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000000/' || repeat('c', 64) || '/dia.xlsx', 'dia.xlsx', 1200, repeat('c', 64));
select pg_temp.ok((select estado = 'en_cola' and subido_por = 'a0000000-0000-0000-0000-00000000000f'
                   from public.archivo_en_cola), 'Finanzas deja un archivo en cola, a su nombre');
select pg_temp.falla($$insert into public.archivo_en_cola (empresa_id, ruta, nombre, tamano, hash) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000000/x/dia.xlsx',
                        'dia.xlsx', 1200, repeat('c', 64))$$,
                     '23505', 'El mismo archivo no entra dos veces a la cola');
select pg_temp.falla($$insert into public.archivo_en_cola (empresa_id, ruta, nombre, tamano, hash) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000000/x/y.xlsx',
                        'y.xlsx', 10, repeat('d', 64))$$,
                     '23514', 'La ruta va siempre en la carpeta de su empresa');
select pg_temp.falla($$insert into public.archivo_en_cola (empresa_id, ruta, nombre, tamano, hash, estado) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000000/x/y.xlsx',
                        'y.xlsx', 10, repeat('e', 64), 'cargado')$$,
                     '42501', 'Un archivo nuevo solo entra en cola');

update public.archivo_en_cola set estado = 'procesando' where id = 'aaaaaaaa-0000-0000-0000-0000000013c1';
select pg_temp.ok((select procesado_por = 'a0000000-0000-0000-0000-00000000000f' and procesado_en is not null
                   from public.archivo_en_cola), 'Al procesar, la base anota quién y cuándo');
select pg_temp.falla($$update public.archivo_en_cola set estado = 'cargado' where id = 'aaaaaaaa-0000-0000-0000-0000000013c1'$$,
                     '23514', 'Cargado exige el archivo importado');
update public.archivo_en_cola set estado = 'error', mensaje = 'No se sabe de qué punto es' where id = 'aaaaaaaa-0000-0000-0000-0000000013c1';
select pg_temp.ok((select estado = 'error' from public.archivo_en_cola), 'Un error queda con su mensaje');
insert into public.archivo_en_cola (empresa_id, ruta, nombre, tamano, hash) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000000/' || repeat('c', 64) || '/dia (2).xlsx',
   'dia (2).xlsx', 1200, repeat('c', 64));
select pg_temp.ok(true, 'Después de un error, el mismo archivo se puede volver a subir');
select pg_temp.falla($$update public.archivo_en_cola set ruta = 'otra'$$, '42501', 'La ruta no se cambia');
with b as (delete from public.archivo_en_cola returning 1)
select pg_temp.ok((select count(*) from b) = 0, 'Nadie borra la cola');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.archivo_en_cola) = 0, 'La asesora no ve la cola');
select pg_temp.falla($$insert into public.archivo_en_cola (empresa_id, ruta, nombre, tamano, hash) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000000/x/z.xlsx',
                        'z.xlsx', 10, repeat('f', 64))$$,
                     '42501', 'La asesora no sube archivos');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.archivo_en_cola) = 0, 'El dueño de B no ve la cola de A');
reset role;

\echo 'TODAS LAS PRUEBAS DE 0013 PASARON'
