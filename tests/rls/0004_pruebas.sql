-- =============================================================================
-- Pruebas de 0004_operacion_diaria.sql
-- Se corre después de las pruebas anteriores y usa sus empresas, puntos y usuarios.
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

-- La asesora de A trabaja en el punto A1.
update public.usuario set punto_id = 'aaaaaaaa-0000-0000-0000-000000000011'
where id = 'a0000000-0000-0000-0000-00000000000a';

set role authenticated;

-- 1. Cargar un día ---------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
insert into public.archivo_importado (id, empresa_id, fuente, nombre, hash) values
  ('aaaaaaaa-0000-0000-0000-000000000081', 'aaaaaaaa-0000-0000-0000-000000000000', 'excel_dia', 'punto1.xlsx',
   repeat('e', 64));
insert into public.jornada (id, empresa_id, punto_id, fecha) values
  ('aaaaaaaa-0000-0000-0000-000000000091', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-16'),
  ('aaaaaaaa-0000-0000-0000-000000000092', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000012', '2026-09-16');
insert into public.reporte_caja (empresa_id, jornada_id, archivo_id, hoja, fila_origen, efectivo_contado,
                                 venta_teorica, descuadre, asesoras_texto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
   'aaaaaaaa-0000-0000-0000-000000000081', '16', 45, 300000, 1000000, -35900, 'Ana');
insert into public.pago (id, empresa_id, jornada_id, medio_pago_id, monto, archivo_id, fila_origen) values
  ('aaaaaaaa-0000-0000-0000-0000000000a1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000091', 'aaaaaaaa-0000-0000-0000-000000000051', 85000,
   'aaaaaaaa-0000-0000-0000-000000000081', 32),
  ('aaaaaaaa-0000-0000-0000-0000000000a2', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000092', 'aaaaaaaa-0000-0000-0000-000000000051', 40000,
   'aaaaaaaa-0000-0000-0000-000000000081', 33);
insert into public.venta (id, empresa_id, jornada_id, total, es_total_dia, archivo_id, fila_origen) values
  ('aaaaaaaa-0000-0000-0000-0000000000b1', 'aaaaaaaa-0000-0000-0000-000000000000',
   'aaaaaaaa-0000-0000-0000-000000000091', 1000000, true, 'aaaaaaaa-0000-0000-0000-000000000081', 40);
insert into public.venta_detalle (empresa_id, venta_id, producto_id, texto_producto, cantidad, precio_lista, valor,
                                  archivo_id, fila_origen) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000b1',
   'aaaaaaaa-0000-0000-0000-000000000031', 'Producto A', 2, 35900, 71800, 'aaaaaaaa-0000-0000-0000-000000000081', 8);
insert into public.turno (empresa_id, jornada_id, asesora_id, texto_original, archivo_id, fila_origen) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
   'aaaaaaaa-0000-0000-0000-000000000021', 'Ana', 'aaaaaaaa-0000-0000-0000-000000000081', 3);
insert into public.movimiento_caja (empresa_id, jornada_id, tipo, concepto, monto, archivo_id, fila_origen) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091', 'gasto', 'Aseo', 12000,
   'aaaaaaaa-0000-0000-0000-000000000081', 50);
insert into public.observacion (empresa_id, jornada_id, texto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091', 'Se fue la luz');
select pg_temp.ok(true, 'Finanzas carga un día: jornada, caja, pagos, venta, turno, gasto y nota');

select pg_temp.falla($$insert into public.jornada (empresa_id, punto_id, fecha) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-16')$$,
                     '23505', 'Un punto tiene una sola jornada por día');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000051', 0)$$,
                     '23514', 'Un pago de cero no entra');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto, archivo_id) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000051', 1000, 'aaaaaaaa-0000-0000-0000-000000000081')$$,
                     '23514', 'Un pago importado dice de qué fila salió');
select pg_temp.falla($$insert into public.reporte_caja (empresa_id, jornada_id, archivo_id, fila_origen) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000081', 45)$$,
                     '23505', 'Un archivo deja un solo reporte de caja por jornada');

-- 2. Lo importado no se reescribe: se anula -------------------------------------
select pg_temp.falla($$update public.pago set monto = 1 where id = 'aaaaaaaa-0000-0000-0000-0000000000a1'$$,
                     '42501', 'Nadie cambia el monto de un pago importado');
select pg_temp.falla($$update public.reporte_caja set descuadre = 0$$,
                     '42501', 'Nadie cambia lo que reportó la caja');
update public.pago set anulado = true, nota = 'Repetido en el Excel' where id = 'aaaaaaaa-0000-0000-0000-0000000000a2';
select pg_temp.ok((select anulado from public.pago where id = 'aaaaaaaa-0000-0000-0000-0000000000a2'),
                  'Un pago se anula con nota y sigue ahí');

-- 3. Cerrar el día --------------------------------------------------------------
with c as (update public.jornada set estado = 'cerrada'
           where id = 'aaaaaaaa-0000-0000-0000-000000000091' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Finanzas no cierra el día');
select pg_temp.falla($$update public.jornada set fecha = '2026-09-17' where id = 'aaaaaaaa-0000-0000-0000-000000000091'$$,
                     '42501', 'Nadie cambia la fecha de una jornada');

select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
update public.jornada set estado = 'cerrada' where id = 'aaaaaaaa-0000-0000-0000-000000000091';
select pg_temp.ok((select estado from public.jornada where id = 'aaaaaaaa-0000-0000-0000-000000000091') = 'cerrada',
                  'La encargada cierra el día');
select pg_temp.falla($$update public.jornada set estado = 'olvidada' where id = 'aaaaaaaa-0000-0000-0000-000000000091'$$,
                     '23514', 'Un estado inventado no entra');

-- 4. La asesora ve solo su punto y no escribe -----------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.jornada) = 1, 'La asesora ve solo la jornada de su punto');
select pg_temp.ok((select count(*) from public.pago) = 1 and (select count(*) from public.reporte_caja) = 1,
                  'La asesora ve solo los pagos y la caja de su punto');
select pg_temp.ok((select count(*) from public.venta_detalle) = 1, 'La asesora ve el detalle de las ventas de su punto');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000051', 5000)$$,
                     '42501', 'La asesora no escribe pagos');
with c as (update public.pago set anulado = true where id = 'aaaaaaaa-0000-0000-0000-0000000000a1' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'La asesora no anula pagos');
select pg_temp.falla($$insert into public.meta (empresa_id, punto_id, fecha, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-16', 1)$$,
                     '42501', 'La asesora no pone metas');

-- 5. Metas -----------------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
insert into public.meta (empresa_id, punto_id, fecha, monto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-16', 2000000);
select pg_temp.falla($$insert into public.meta (empresa_id, punto_id, fecha, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-16', 1)$$,
                     '23505', 'Una sola meta activa por punto y día');

-- 6. Otra empresa ---------------------------------------------------------------
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.jornada) = 0 and (select count(*) from public.pago) = 0
                  and (select count(*) from public.venta_detalle) = 0 and (select count(*) from public.meta) = 0,
                  'El dueño de B no ve nada de la operación de A');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000051', 5000)$$,
                     '42501', 'El dueño de B no escribe pagos en A');
insert into public.jornada (id, empresa_id, punto_id, fecha) values
  ('bbbbbbbb-0000-0000-0000-000000000091', 'bbbbbbbb-0000-0000-0000-000000000000',
   'bbbbbbbb-0000-0000-0000-000000000011', '2026-09-16');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000091',
                        'bbbbbbbb-0000-0000-0000-000000000051', 5000)$$,
                     '23503', 'Un pago de B no cuelga de una jornada de A');
select pg_temp.falla($$insert into public.pago (empresa_id, jornada_id, medio_pago_id, monto) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000051', 5000)$$,
                     '23503', 'Un pago de B no usa un medio de pago de A');
select pg_temp.falla($$insert into public.reporte_caja (empresa_id, jornada_id, archivo_id, fila_origen) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000091',
                        'aaaaaaaa-0000-0000-0000-000000000081', 1)$$,
                     '23503', 'Un reporte de B no apunta a un archivo de A');
select pg_temp.falla($$insert into public.jornada (empresa_id, punto_id, fecha) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-09-17')$$,
                     '23503', 'Una jornada de B no usa un punto de A');
with c as (update public.jornada set estado = 'bloqueada'
           where id = 'aaaaaaaa-0000-0000-0000-000000000091' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño de B no bloquea días de A');

-- 7. Nadie borra ----------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
with c as (delete from public.pago returning 1) select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra pagos');
with c as (delete from public.jornada returning 1) select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra jornadas');
with c as (delete from public.reporte_caja returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie borra reportes de caja');
select pg_temp.falla($$truncate public.pago cascade$$, '42501', 'Nadie vacía la tabla de pagos');
select pg_temp.ok((select count(*) from public.auditoria where tabla = 'pago' and accion = 'update') = 1,
                  'Anular un pago queda en auditoría');

-- 8. Sin sesión -----------------------------------------------------------------
reset role;
set role anon;
select set_config('request.jwt.claims', '', false);
select pg_temp.ok((select count(*) from public.jornada) = 0 and (select count(*) from public.pago) = 0
                  and (select count(*) from public.reporte_caja) = 0, 'anon no ve la operación');
reset role;

-- 9. Estructura -----------------------------------------------------------------
select pg_temp.ok(
  not exists (select from pg_tables where schemaname = 'public' and not rowsecurity), 'Todas las tablas tienen RLS');
select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');
select pg_temp.ok(
  not exists (select from information_schema.columns
              where table_schema = 'public'
                and table_name in ('reporte_caja', 'venta', 'venta_detalle', 'pago', 'movimiento_caja', 'meta')
                and column_name in ('monto', 'total', 'descuento', 'valor', 'precio_lista', 'efectivo_contado',
                                    'venta_teorica', 'descuadre')
                and data_type <> 'bigint'),
  'Toda la plata de la operación es bigint');

\echo 'TODAS LAS PRUEBAS DE 0004 PASARON'
