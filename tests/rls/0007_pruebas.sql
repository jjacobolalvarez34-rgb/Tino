-- =============================================================================
-- Pruebas de 0007_vistas_panel.sql
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

-- Un Excel de un día: caja, dos transferencias, venta con detalle y quién trabajó.
create temp table carga (nombre text primary key, p jsonb);
insert into carga values
  ('excel', $j${
    "fuente": "excel_dia", "nombre": "punto1_sept.xlsx", "hash": "1111111111111111111111111111111111111111111111111111111111111111",
    "desde": "2026-09-18", "hasta": "2026-09-18",
    "jornadas": [{
      "punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-09-18",
      "reporte": {"hoja": "18", "fila_origen": 45, "efectivo_contado": 500000, "venta_teorica": 900000,
                  "descuadre": -35900, "asesoras_texto": "Ana"},
      "pagos": [{"medio_pago_id": "aaaaaaaa-0000-0000-0000-000000000051", "monto": 85000, "fila_origen": 30},
                {"medio_pago_id": "aaaaaaaa-0000-0000-0000-000000000051", "monto": 40000, "fila_origen": 31}],
      "turnos": [{"asesora_id": "aaaaaaaa-0000-0000-0000-000000000021", "texto_original": "Ana", "fila_origen": 3}],
      "venta": {"total": 900000, "fila_origen": 44,
                "detalle": [{"producto_id": "aaaaaaaa-0000-0000-0000-000000000031", "texto_producto": "Producto A",
                             "cantidad": 2, "precio_lista": 35900, "valor": 71800, "fila_origen": 8},
                            {"producto_id": null, "texto_producto": "Crema nueva", "cantidad": 1,
                             "precio_lista": 20000, "valor": 20000, "fila_origen": 9}]}
    }],
    "errores": [{"fila_origen": 9, "tipo": "producto_sin_reconocer", "texto": "Crema nueva"}]
  }$j$),
  ('banco', $j${
    "fuente": "banco", "nombre": "extracto.pdf", "hash": "2222222222222222222222222222222222222222222222222222222222222222",
    "movimientos": [
      {"fila_origen": 5, "fuente": "banco", "tipo": "transferencia", "fecha": "2026-09-18",
       "punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "referencia": "90001234", "bruto": 85000},
      {"fila_origen": 6, "fuente": "banco", "tipo": "transferencia", "fecha": "2026-09-19",
       "punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "referencia": "90001234", "bruto": 40000}]
  }$j$),
  ('malo', $j${
    "fuente": "excel_dia", "nombre": "malo.xlsx", "hash": "3333333333333333333333333333333333333333333333333333333333333333",
    "jornadas": [{"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-09-20",
                  "pagos": [{"medio_pago_id": "aaaaaaaa-0000-0000-0000-000000000051", "monto": 0, "fila_origen": 30}]}]
  }$j$);
grant select on carga to authenticated;

set role authenticated;

-- 1. Cargar un archivo entero ----------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table ids as select public.importar_archivo((select p from carga where nombre = 'excel')) as excel;
select pg_temp.ok((select filas from public.archivo_importado where id = (select excel from ids)) = 5,
                  'El Excel entra entero y cuenta sus filas');
select pg_temp.ok((select count(*) from public.v_pago_vigente where fecha = '2026-09-18') = 2,
                  'Sus transferencias quedan vigentes, con su fecha y su punto');
select pg_temp.ok((select descuadre_reportado = -35900 and punto_codigo = 'P01' from public.v_jornada
                   where fecha = '2026-09-18' and punto_id = 'aaaaaaaa-0000-0000-0000-000000000011'),
                  'La jornada muestra lo que reportó la caja');
select pg_temp.ok((select count(*) from public.v_detalle_vigente where texto_producto = 'Crema nueva'
                   and producto_id is null) = 1, 'Un producto sin reconocer entra con su texto');
select pg_temp.ok((select count(*) from public.error_importacion where archivo_id = (select excel from ids)
                   and not resuelto) = 1, 'Y queda pendiente de resolver');

select pg_temp.falla($$select public.importar_archivo((select p from carga where nombre = 'excel'))$$,
                     '23505', 'El mismo archivo no entra dos veces');
select pg_temp.falla($$select public.importar_archivo((select p from carga where nombre = 'malo'))$$,
                     '23514', 'Un archivo con una fila mala no entra');
select pg_temp.ok(not exists (select from public.archivo_importado where nombre = 'malo.xlsx')
                  and not exists (select from public.jornada where fecha = '2026-09-20'),
                  'Y no deja medio archivo');

alter table ids add column banco uuid;
update ids set banco = public.importar_archivo((select p from carga where nombre = 'banco'));
select pg_temp.ok((select count(*) from public.v_movimiento_vigente where archivo_id = (select banco from ids)) = 2,
                  'El extracto entra con el neto calculado');

-- 2. Guardar la revisión --------------------------------------------------------
create temp table rev as
select (select id from public.jornada where fecha = '2026-09-18'
        and punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') as jornada,
       (select id from public.pago where fila_origen = 30 and archivo_id = (select excel from ids)) as pago85,
       (select id from public.pago where fila_origen = 31 and archivo_id = (select excel from ids)) as pago40,
       (select id from public.movimiento_externo where fila_origen = 5 and archivo_id = (select banco from ids)) as mov85,
       (select id from public.movimiento_externo where fila_origen = 6 and archivo_id = (select banco from ids)) as mov40;

select public.guardar_revision(jsonb_build_object(
  'descuadres', jsonb_build_array(jsonb_build_object(
    'jornada_id', (select jornada from rev), 'monto', -35900, 'explicado', 0, 'sin_explicar', -35900,
    'estado_motor', 'sin_explicar', 'causa_codigo', 'sin_causa_clara',
    'evidencias', jsonb_build_array(jsonb_build_object('causa_codigo', 'precios', 'tipo', 'pista', 'total', -35900,
                                                       'detalle', '{"combinaciones": [[35900]]}'::jsonb)))),
  'cruces', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago85 from rev), 'movimiento_id', (select mov85 from rev), 'tipo', 'mismo_dia'),
    jsonb_build_object('pago_id', (select pago40 from rev), 'movimiento_id', (select mov40 from rev), 'tipo', 'otro_dia')),
  'verificaciones', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago85 from rev), 'estado', 'confirmada', 'extracto_id', (select mov85 from rev)),
    jsonb_build_object('pago_id', (select pago40 from rev), 'estado', 'sospechosa'))));
select pg_temp.ok((select estado_motor = 'sin_explicar' and descuadre = -35900 from public.v_jornada
                   where id = (select jornada from rev)), 'La revisión guarda el descuadre del día');
select pg_temp.ok((select array_agg(estado order by tipo) from public.v_cruce where pago_id in
                   ((select pago85 from rev), (select pago40 from rev))) = array['confirmada', 'propuesta'],
                  'El mismo día queda confirmado; otro día, propuesto');
select pg_temp.ok((select array_agg(estado order by monto) from public.v_transferencia
                   where jornada_id = (select jornada from rev)) = array['sospechosa', 'confirmada'],
                  'Cada transferencia queda con su verificación');

-- Llega información nueva: ahora cuadra y la sospechosa aparece en el extracto.
select public.guardar_revision(jsonb_build_object(
  'descuadres', jsonb_build_array(jsonb_build_object(
    'jornada_id', (select jornada from rev), 'monto', -35900, 'explicado', -35900, 'sin_explicar', 0,
    'estado_motor', 'cuadra', 'causa_codigo', null, 'evidencias', '[]'::jsonb)),
  'cruces', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago40 from rev), 'movimiento_id', (select mov40 from rev), 'tipo', 'otro_dia')),
  'verificaciones', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago40 from rev), 'estado', 'confirmada', 'extracto_id', (select mov40 from rev)))));
select pg_temp.ok((select descuadre_estado = 'resuelto' and descuadre_nota = 'Se resolvió con datos nuevos'
                   from public.v_jornada where id = (select jornada from rev)),
                  'Si ahora cuadra, el descuadre abierto se resuelve con nota');
select pg_temp.ok((select count(*) from public.descuadre_evidencia where not vigente) >= 1,
                  'Las pruebas viejas quedan, sin vigencia');
select pg_temp.ok((select count(*) from public.conciliacion where pago_id = (select pago40 from rev)) = 1,
                  'Una pareja viva no se propone dos veces');
select pg_temp.ok((select estado = 'confirmada' and nota = 'Confirmada por extracto después de sospecha'
                   from public.v_transferencia where pago_id = (select pago40 from rev)),
                  'La sospechosa que aparece en el extracto se confirma con nota');

-- 3. Deshacer un archivo --------------------------------------------------------
select public.deshacer_archivo((select excel from ids));
select pg_temp.ok((select count(*) from public.v_pago_vigente where fecha = '2026-09-18') = 0
                  and (select reporte_id is null from public.v_jornada where id = (select jornada from rev)),
                  'Lo de un archivo deshecho deja de contar');
select pg_temp.ok((select count(*) from public.pago where archivo_id = (select excel from ids)) = 2,
                  'Pero no se borra');
select pg_temp.falla($$select public.deshacer_archivo((select excel from ids))$$, 'P0002',
                     'Un archivo deshecho no se deshace otra vez');
select pg_temp.ok((select count(*) from public.conciliacion where estado = 'rechazada'
                   and pago_id in ((select pago85 from rev), (select pago40 from rev))) = 2,
                  'Los cruces de un archivo deshecho se rechazan con nota');
select pg_temp.ok((select count(*) from public.verificacion_transferencia where estado = 'rechazada'
                   and nota like 'Se deshizo el archivo%') = 2,
                  'Y las transferencias de sus pagos también');
select pg_temp.ok((select count(*) from public.error_importacion where archivo_id = (select excel from ids)
                   and not resuelto) = 0, 'Sus errores pendientes dejan de estar pendientes');

update ids set excel = public.importar_archivo((select p from carga where nombre = 'excel'));
select pg_temp.ok((select count(*) from public.v_pago_vigente where fecha = '2026-09-18') = 2,
                  'El archivo corregido se vuelve a subir y cuenta de nuevo');
update rev set pago85 = (select id from public.pago where fila_origen = 30 and archivo_id = (select excel from ids));
select public.guardar_revision(jsonb_build_object(
  'cruces', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago85 from rev), 'movimiento_id', (select mov85 from rev), 'tipo', 'mismo_dia')),
  'verificaciones', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago85 from rev), 'estado', 'confirmada', 'extracto_id', (select mov85 from rev)))));
select pg_temp.ok((select estado from public.v_transferencia where pago_id = (select pago85 from rev)) = 'confirmada',
                  'La línea del banco quedó libre: el pago nuevo se confirma con ella');

select public.deshacer_archivo((select banco from ids));
select pg_temp.ok((select estado = 'pendiente' and extracto_id is null from public.verificacion_transferencia
                   where pago_id = (select pago85 from rev)),
                  'Si se deshace el extracto, la transferencia vuelve a pendiente');
update ids set banco = public.importar_archivo((select p from carga where nombre = 'banco'));
update rev set mov85 = (select id from public.movimiento_externo where fila_origen = 5 and archivo_id = (select banco from ids));
select public.guardar_revision(jsonb_build_object(
  'verificaciones', jsonb_build_array(
    jsonb_build_object('pago_id', (select pago85 from rev), 'estado', 'confirmada', 'extracto_id', (select mov85 from rev)))));
select pg_temp.ok((select estado from public.v_transferencia where pago_id = (select pago85 from rev)) = 'confirmada',
                  'Con el extracto de nuevo, se vuelve a confirmar');

-- 4. Roles y otra empresa -------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$select public.importar_archivo('{"fuente": "excel_dia", "nombre": "x", "hash": "4444444444444444444444444444444444444444444444444444444444444444"}')$$,
                     '42501', 'La asesora no sube archivos');
select pg_temp.ok((select count(*) from public.v_cruce) = 0 and (select count(*) from public.v_transferencia) = 0,
                  'La asesora no ve cruces ni verificaciones');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.v_jornada where empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000') = 0
                  and (select count(*) from public.v_pago_vigente) = 0 and (select count(*) from public.v_cruce) = 0,
                  'El dueño de B no ve nada de A por las vistas');
select pg_temp.falla($$select public.importar_archivo('{"fuente": "excel_dia", "nombre": "x",
                         "hash": "5555555555555555555555555555555555555555555555555555555555555555",
                         "jornadas": [{"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-09-18"}]}')$$,
                     '23503', 'B no carga días en un punto de A');
select pg_temp.falla($$select public.guardar_revision(jsonb_build_object('descuadres', jsonb_build_array(
                         jsonb_build_object('jornada_id', (select jornada from rev), 'monto', 1, 'explicado', 0,
                                            'sin_explicar', 1, 'estado_motor', 'sin_explicar'))))$$,
                     '23503', 'B no guarda descuadres en una jornada de A');
select pg_temp.falla($$select public.deshacer_archivo((select banco from ids))$$, 'P0002', 'B no deshace archivos de A');

reset role;
set role anon;
select set_config('request.jwt.claims', '', false);
select pg_temp.falla($$select public.importar_archivo('{}')$$, '42501', 'Sin sesión no se carga nada');
select pg_temp.ok((select count(*) from public.v_jornada) = 0, 'anon no ve jornadas por las vistas');
reset role;

-- 5. Estructura -----------------------------------------------------------------
select pg_temp.ok(
  not exists (select from pg_class c join pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'public' and c.relkind = 'v'
                and not coalesce(c.reloptions @> array['security_invoker=true'], false)),
  'Todas las vistas corren con los permisos de quien consulta');
select pg_temp.ok(
  not exists (select from pg_proc p join pg_namespace n on n.oid = p.pronamespace
              where n.nspname = 'public' and p.prosecdef),
  'Ninguna función pública se salta los permisos');

\echo 'TODAS LAS PRUEBAS DE 0007 PASARON'
