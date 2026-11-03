-- =============================================================================
-- Pruebas de 0006_descuadres.sql
-- Se corre después de las pruebas anteriores y usa sus jornadas, pagos y movimientos.
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

-- 1. Configuración --------------------------------------------------------------
-- B no tocó su configuración en las pruebas anteriores (A sí cambió su umbral).
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select desc_umbral = 100 and desc_porcentaje_explicado = 80 and desc_reglas_sin_peso = array['R05']
                          and desc_billetes[6] = 100000 and desc_comp_porcentaje = 25
                   from public.empresa_config), 'La empresa nace con los valores D1 a D6 de las reglas');
select pg_temp.falla($$update public.empresa_config set desc_billetes = array[0]::bigint[]$$,
                     '23514', 'Un billete de cero no se configura');
select pg_temp.falla($$update public.empresa_config set desc_porcentaje_explicado = 120$$,
                     '23514', 'Un porcentaje de más de 100 no se configura');

-- 2. Calcular un descuadre -------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.ok((select count(*) from public.causa_descuadre where codigo = 'sin_causa_clara') = 1,
                  'El catálogo dice "sin causa clara"');
insert into public.descuadre (id, empresa_id, jornada_id, reporte_id, monto, explicado, sin_explicar, estado_motor,
                              causa_codigo) values
  ('aaaaaaaa-0000-0000-0000-0000000000f1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000091',
   (select id from public.reporte_caja where jornada_id = 'aaaaaaaa-0000-0000-0000-000000000091'),
   -35900, 0, -35900, 'sin_explicar', 'sin_causa_clara');
insert into public.descuadre_evidencia (empresa_id, descuadre_id, causa_codigo, tipo, total, detalle) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f1', 'precios', 'pista', -35900,
   '{"combinaciones": [[35900]]}');
select pg_temp.ok(true, 'Finanzas guarda un descuadre sin causa clara con una pista');

select pg_temp.falla($$insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                               -1, 0, -1, 'sin_explicar')$$,
                     '23505', 'Una jornada tiene un solo descuadre');
select pg_temp.falla($$insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000092',
                               -50000, -40000, -5000, 'explicado')$$,
                     '23514', 'Lo explicado más lo sin explicar da el descuadre');
select pg_temp.falla($$insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor,
                                                     causa_codigo)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000092',
                               -50000, 0, -50000, 'sin_explicar', 'billete')$$,
                     '23514', 'Sin causa clara no lleva una causa inventada');
select pg_temp.falla($$insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor,
                                                     estado)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000092',
                               -50000, 0, -50000, 'sin_explicar', 'aceptado')$$,
                     '23514', 'Un descuadre no nace cerrado: lo cierra una persona');
select pg_temp.falla($$insert into public.descuadre_evidencia (empresa_id, descuadre_id, causa_codigo, tipo, monto)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f1',
                               'precios', 'pista', -35900)$$,
                     '23514', 'Una pista no explica plata');
select pg_temp.falla($$insert into public.descuadre_evidencia (empresa_id, descuadre_id, causa_codigo, tipo)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f1',
                               'inventada', 'causa')$$,
                     '23503', 'Una causa fuera del catálogo no entra');

-- 3. Recalcular y decidir -------------------------------------------------------
update public.descuadre_evidencia set vigente = false where descuadre_id = 'aaaaaaaa-0000-0000-0000-0000000000f1';
update public.descuadre set explicado = -35900, sin_explicar = 0, estado_motor = 'explicado', causa_codigo = 'billete',
                            calculado_en = now()
where id = 'aaaaaaaa-0000-0000-0000-0000000000f1';
select pg_temp.ok((select count(*) from public.descuadre_evidencia where not vigente) = 1,
                  'Recalcular deja las pruebas viejas, sin vigencia');
select pg_temp.falla($$update public.descuadre set estado = 'aceptado'
                       where id = 'aaaaaaaa-0000-0000-0000-0000000000f1'$$,
                     '23514', 'Cerrar un descuadre exige una nota');
select pg_temp.falla($$update public.descuadre set decidido_por = null where id = 'aaaaaaaa-0000-0000-0000-0000000000f1'$$,
                     '42501', 'Nadie cambia quién decidió');
select pg_temp.falla($$update public.descuadre_evidencia set monto = 1$$, '42501', 'Nadie reescribe una prueba');
update public.descuadre set estado = 'explicado', nota = 'Se contó mal un billete de 20 mil'
where id = 'aaaaaaaa-0000-0000-0000-0000000000f1';
select pg_temp.ok((select decidido_por = 'a0000000-0000-0000-0000-00000000000f' from public.descuadre
                   where id = 'aaaaaaaa-0000-0000-0000-0000000000f1'), 'La base anota quién lo explicó');

-- 4. Roles y otra empresa -------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.descuadre) = 0 and (select count(*) from public.descuadre_evidencia) = 0,
                  'La asesora no ve descuadres (D-036)');
with c as (update public.empresa_config set desc_umbral = 1 returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'La asesora no cambia los valores de las reglas');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.descuadre) = 0, 'El dueño de B no ve descuadres de A');
with c as (update public.descuadre set estado = 'aceptado', nota = 'x' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño de B no cierra descuadres de A');
select pg_temp.falla($$insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor)
                       values ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                               -1, 0, -1, 'sin_explicar')$$,
                     '23503', 'Un descuadre de B no cuelga de una jornada de A');

-- 5. Nadie borra ----------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
with c as (delete from public.descuadre returning 1) select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra descuadres');
with c as (delete from public.causa_descuadre returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra causas del catálogo');
select pg_temp.falla($$insert into public.causa_descuadre (codigo, regla, nombre, descripcion) values ('x', 'x', 'x', 'x')$$,
                     '42501', 'Nadie inventa causas desde la aplicación');
select pg_temp.ok((select count(*) from public.auditoria where tabla = 'descuadre') = 3,
                  'Calcular, recalcular y decidir quedan en auditoría');

-- 6. Estructura -----------------------------------------------------------------
reset role;
select pg_temp.ok(
  not exists (select from pg_tables where schemaname = 'public' and not rowsecurity), 'Todas las tablas tienen RLS');
select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');

\echo 'TODAS LAS PRUEBAS DE 0006 PASARON'
