-- =============================================================================
-- Pruebas de 0005_bancos_conciliacion.sql
-- Se corre después de las pruebas anteriores y usa sus empresas, jornadas y pagos.
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

-- 1. Festivos -------------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok(exists (select from public.festivo where fecha = '2026-11-02'), 'Todos ven los festivos');
select pg_temp.ok((select count(*) from public.festivo where extract(year from fecha) = 2026) = 18,
                  '2026 tiene 18 festivos');
select pg_temp.falla($$insert into public.festivo (fecha, nombre) values ('2026-11-03', 'Inventado')$$,
                     '42501', 'Nadie agrega festivos desde la aplicación');

-- 2. Lo que llegó ---------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
insert into public.archivo_importado (id, empresa_id, fuente, nombre, hash) values
  ('aaaaaaaa-0000-0000-0000-0000000000c0', 'aaaaaaaa-0000-0000-0000-000000000000', 'banco', 'extracto.pdf',
   repeat('f', 64));
insert into public.movimiento_externo (id, empresa_id, archivo_id, fila_origen, fuente, tipo, fecha, punto_id,
                                      referencia, bruto, neto) values
  ('aaaaaaaa-0000-0000-0000-0000000000c1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-0000000000c0', 10, 'banco', 'transferencia', '2026-09-16',
   'aaaaaaaa-0000-0000-0000-000000000011', '12345678', 85000, 85000),
  ('aaaaaaaa-0000-0000-0000-0000000000c2', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-0000000000c0', 11, 'banco', 'transferencia', '2026-09-17', null,
   null, 40000, 40000);
select pg_temp.ok(true, 'Finanzas carga el extracto, con un pago sin punto');

select pg_temp.falla($$insert into public.movimiento_externo (empresa_id, archivo_id, fila_origen, fuente, tipo, fecha,
                                                              bruto, comision, neto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c0', 12, 'bold',
                        'cobro', '2026-09-16', 100000, 3000, 100000)$$,
                     '23514', 'El neto es el bruto menos comisión, retenciones y préstamo');
select pg_temp.falla($$insert into public.movimiento_externo (empresa_id, archivo_id, fuente, tipo, fecha, bruto, neto)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c0',
                               'banco', 'transferencia', '2026-09-16', 1, 1)$$,
                     '23502', 'Lo que llegó dice de qué fila salió');
select pg_temp.falla($$update public.movimiento_externo set bruto = 1, neto = 1
                       where id = 'aaaaaaaa-0000-0000-0000-0000000000c1'$$,
                     '42501', 'Nadie cambia el monto de lo que llegó');
update public.movimiento_externo set punto_id = 'aaaaaaaa-0000-0000-0000-000000000012', nota = 'Era del punto A9'
where id = 'aaaaaaaa-0000-0000-0000-0000000000c2';
select pg_temp.ok((select punto_id from public.movimiento_externo where id = 'aaaaaaaa-0000-0000-0000-0000000000c2')
                  = 'aaaaaaaa-0000-0000-0000-000000000012', 'Un pago sin código se asigna a mano a un punto');

-- 3. Conciliación ---------------------------------------------------------------
insert into public.conciliacion (id, empresa_id, pago_id, movimiento_id, tipo, estado) values
  ('aaaaaaaa-0000-0000-0000-0000000000d1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-0000000000a1', 'aaaaaaaa-0000-0000-0000-0000000000c1', 'mismo_dia', 'confirmada');
select pg_temp.ok(true, 'Lo que coincide el mismo día nace confirmado');

select pg_temp.falla($$insert into public.conciliacion (empresa_id, pago_id, movimiento_id, tipo, estado) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a2',
                        'aaaaaaaa-0000-0000-0000-0000000000c2', 'otro_dia', 'confirmada')$$,
                     '23514', 'Lo que llegó otro día no nace confirmado (D-006)');
select pg_temp.falla($$insert into public.conciliacion (empresa_id, pago_id, movimiento_id, tipo, estado) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a2',
                        'aaaaaaaa-0000-0000-0000-0000000000c1', 'mismo_dia', 'confirmada')$$,
                     '23505', 'Una línea del banco no confirma dos pagos');
select pg_temp.falla($$insert into public.conciliacion (empresa_id, pago_id, movimiento_id, tipo, estado) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a2',
                        'aaaaaaaa-0000-0000-0000-0000000000c2', 'otro_dia', 'rechazada')$$,
                     '23514', 'Nada nace rechazado');

insert into public.conciliacion (id, empresa_id, pago_id, movimiento_id, tipo) values
  ('aaaaaaaa-0000-0000-0000-0000000000d2', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-0000000000a2', 'aaaaaaaa-0000-0000-0000-0000000000c2', 'otro_dia');
select pg_temp.falla($$update public.conciliacion set estado = 'confirmada'
                       where id = 'aaaaaaaa-0000-0000-0000-0000000000d2'$$,
                     '23514', 'Confirmar a mano exige una nota');
update public.conciliacion set estado = 'confirmada', nota = 'Llegó el 17, es la misma'
where id = 'aaaaaaaa-0000-0000-0000-0000000000d2';
select pg_temp.ok((select decidido_por = 'a0000000-0000-0000-0000-00000000000f' and decidido_en is not null
                   from public.conciliacion where id = 'aaaaaaaa-0000-0000-0000-0000000000d2'),
                  'La base anota quién confirmó y cuándo');
select pg_temp.falla($$update public.conciliacion set decidido_por = null
                       where id = 'aaaaaaaa-0000-0000-0000-0000000000d2'$$,
                     '42501', 'Nadie cambia quién decidió');
select pg_temp.falla($$update public.conciliacion set estado = 'rechazada', nota = 'Llegó el 17, es la misma'
                       where id = 'aaaaaaaa-0000-0000-0000-0000000000d2'$$,
                     '23514', 'Cada decisión lleva su propia nota');
update public.conciliacion set estado = 'rechazada', nota = 'No era de este punto'
where id = 'aaaaaaaa-0000-0000-0000-0000000000d2';
select pg_temp.ok((select count(*) from public.conciliacion) = 2, 'Rechazar no borra: el cruce queda en el historial');

-- 4. Verificación de transferencias ---------------------------------------------
select pg_temp.falla($$insert into public.verificacion_transferencia (empresa_id, pago_id, estado) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a1', 'confirmada')$$,
                     '23514', 'Nada pasa a confirmada sin el extracto');
insert into public.verificacion_transferencia (empresa_id, pago_id, estado, extracto_id) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a1', 'confirmada',
   'aaaaaaaa-0000-0000-0000-0000000000c1');
select pg_temp.falla($$insert into public.verificacion_transferencia (empresa_id, pago_id, estado, extracto_id) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a2', 'confirmada',
                        'aaaaaaaa-0000-0000-0000-0000000000c1')$$,
                     '23505', 'Una línea del extracto no verifica dos transferencias');
insert into public.verificacion_transferencia (id, empresa_id, pago_id, estado) values
  ('aaaaaaaa-0000-0000-0000-0000000000e2', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-0000000000a2', 'sospechosa');
update public.verificacion_transferencia
set estado = 'confirmada', extracto_id = 'aaaaaaaa-0000-0000-0000-0000000000c2',
    nota = 'Confirmada por extracto después de sospecha'
where id = 'aaaaaaaa-0000-0000-0000-0000000000e2';
select pg_temp.ok((select estado from public.verificacion_transferencia
                   where id = 'aaaaaaaa-0000-0000-0000-0000000000e2') = 'confirmada',
                  'Una sospechosa que aparece en el extracto se confirma con nota');

-- 5. Roles y otra empresa -------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.movimiento_externo) = 0 and (select count(*) from public.conciliacion) = 0
                  and (select count(*) from public.verificacion_transferencia) = 0,
                  'La asesora no ve el banco ni los cruces');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.movimiento_externo) = 0 and (select count(*) from public.conciliacion) = 0,
                  'El dueño de B no ve el banco de A');
with c as (update public.conciliacion set estado = 'propuesta', nota = 'x' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño de B no decide cruces de A');
select pg_temp.falla($$insert into public.movimiento_externo (empresa_id, archivo_id, fila_origen, fuente, tipo, fecha,
                                                              bruto, neto) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c0', 1, 'banco',
                        'transferencia', '2026-09-16', 1, 1)$$,
                     '23503', 'Lo que llega a B no apunta a un archivo de A');
insert into public.archivo_importado (id, empresa_id, fuente, nombre, hash) values
  ('bbbbbbbb-0000-0000-0000-0000000000c0', 'bbbbbbbb-0000-0000-0000-000000000000', 'banco', 'b.pdf', repeat('9', 64));
insert into public.movimiento_externo (id, empresa_id, archivo_id, fila_origen, fuente, tipo, fecha, bruto, neto) values
  ('bbbbbbbb-0000-0000-0000-0000000000c1', 'bbbbbbbb-0000-0000-0000-000000000000',
   'bbbbbbbb-0000-0000-0000-0000000000c0', 1, 'banco', 'transferencia', '2026-09-16', 1, 1);
select pg_temp.falla($$insert into public.conciliacion (empresa_id, pago_id, movimiento_id, tipo) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000a1',
                        'bbbbbbbb-0000-0000-0000-0000000000c1', 'otro_dia')$$,
                     '23503', 'Un cruce de B no usa un pago de A');
select pg_temp.falla($$insert into public.movimiento_externo (empresa_id, archivo_id, fila_origen, fuente, tipo, fecha,
                                                              punto_id, bruto, neto) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-0000000000c0', 2, 'banco',
                        'transferencia', '2026-09-16', 'aaaaaaaa-0000-0000-0000-000000000011', 1, 1)$$,
                     '23503', 'Lo que llega a B no se asigna a un punto de A');

-- 6. Nadie borra ----------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
with c as (delete from public.conciliacion returning 1) select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra cruces');
with c as (delete from public.movimiento_externo returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra lo que llegó');
select pg_temp.falla($$truncate public.conciliacion cascade$$, '42501', 'Nadie vacía la tabla de cruces');
select pg_temp.ok((select count(*) from public.auditoria where tabla = 'conciliacion' and accion = 'update') = 2,
                  'Cada decisión queda en auditoría');

-- 7. Sin sesión -----------------------------------------------------------------
reset role;
set role anon;
select set_config('request.jwt.claims', '', false);
select pg_temp.ok((select count(*) from public.movimiento_externo) = 0 and (select count(*) from public.festivo) = 0,
                  'anon no ve el banco ni los festivos');
reset role;

-- 8. Estructura -----------------------------------------------------------------
select pg_temp.ok(
  not exists (select from pg_tables where schemaname = 'public' and not rowsecurity), 'Todas las tablas tienen RLS');
select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');
select pg_temp.ok(
  not exists (select from information_schema.columns
              where table_schema = 'public' and table_name = 'movimiento_externo'
                and column_name in ('bruto', 'comision', 'retenciones', 'prestamo', 'neto') and data_type <> 'bigint'),
  'Toda la plata de lo que llegó es bigint');

\echo 'TODAS LAS PRUEBAS DE 0005 PASARON'
