-- =============================================================================
-- Pruebas de 0014_cerrar_el_dia.sql
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

-- Un día con su archivo, su caja y un descuadre abierto, en el punto A1.
create temp table carga (p jsonb);
insert into carga values ($j${
  "fuente": "excel_dia", "nombre": "cierre.xlsx", "hash": "a014a014a014a014a014a014a014a014a014a014a014a014a014a014a014a014",
  "desde": "2026-12-01", "hasta": "2026-12-02",
  "jornadas": [{"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-12-01", "pagos": [], "turnos": [],
                "caja": [{"tipo": "gasto", "concepto": "Gastos", "monto": 5000, "fila_origen": 190}]},
               {"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-12-02", "pagos": [], "turnos": [],
                "caja": [{"tipo": "gasto", "concepto": "Gastos", "monto": 3000, "fila_origen": 191}]}]
}$j$);
grant select on carga to authenticated;
set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table arch as select public.importar_archivo((select p from carga)) as id;
reset role;
create temp table dias as select id, fecha from public.jornada
  where punto_id = 'aaaaaaaa-0000-0000-0000-000000000011' and fecha in ('2026-12-01', '2026-12-02');
grant select on dias, arch to authenticated;
insert into public.descuadre (empresa_id, jornada_id, monto, explicado, sin_explicar, estado_motor)
select 'aaaaaaaa-0000-0000-0000-000000000000', id, -85000, 0, -85000, 'sin_explicar' from dias where fecha = '2026-12-01';
set role authenticated;

-- Cerrar
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.falla($$select public.cerrar_dias(array(select id from dias))$$, '42501', 'Finanzas no cierra el día');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');  -- asesora del punto A1
select pg_temp.ok(public.cerrar_dias(array(select id from dias where fecha = '2026-12-01')) = 1,
                  'La asesora cierra el día de su punto');
select pg_temp.ok((select estado from public.jornada where id = (select id from dias where fecha = '2026-12-01')) = 'cerrada',
                  'El día queda cerrado');
select pg_temp.ok((select descuadres_abiertos = 1 and accion = 'cerrar' from public.v_jornada_cierre
                   where jornada_id = (select id from dias where fecha = '2026-12-01')),
                  'Un día con descuadres abiertos se cierra, pero queda marcado');
select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
select pg_temp.ok(public.cerrar_dias(array(select id from dias)) = 1, 'La encargada cierra lo que faltaba (lo cerrado no se repite)');
select pg_temp.falla($$update public.jornada set estado = 'abierta' where id = (select id from dias where fecha = '2026-12-01')$$,
                     '23514', 'Ni la encargada abre un día cambiando el estado a mano sin nota');

-- El candado
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.falla($$insert into public.movimiento_caja (empresa_id, jornada_id, tipo, concepto, monto)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', (select id from dias where fecha = '2026-12-01'),
                               'gasto', 'Aseo', 1000)$$,
                     '55000', 'Un día cerrado no recibe caja nueva');
select pg_temp.falla($$update public.movimiento_caja set anulado = true, nota = 'x'
                       where jornada_id = (select id from dias where fecha = '2026-12-01')$$,
                     '55000', 'Ni se le anula nada');
select pg_temp.falla($$select public.deshacer_archivo((select id from arch))$$,
                     '55000', 'Un archivo con días cerrados no se deshace');

-- Desbloquear
select pg_temp.falla($$select public.desbloquear_dia((select id from dias where fecha = '2026-12-01'), 'corregir')$$,
                     '42501', 'Finanzas no desbloquea');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$select public.desbloquear_dia((select id from dias where fecha = '2026-12-01'), 'corregir')$$,
                     '42501', 'La asesora no desbloquea');
select pg_temp.como('a0000000-0000-0000-0000-00000000000c');
select pg_temp.falla($$select public.desbloquear_dia((select id from dias where fecha = '2026-12-01'), 'corregir')$$,
                     '42501', 'Soporte no desbloquea (tabla de roles)');
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$select public.desbloquear_dia((select id from dias where fecha = '2026-12-01'), '')$$,
                     '23514', 'Desbloquear pide nota');
select public.desbloquear_dia((select id from dias where fecha = '2026-12-01'), 'Llegó el Excel corregido');
select pg_temp.ok((select estado from public.jornada where id = (select id from dias where fecha = '2026-12-01')) = 'abierta'
                  and (select accion = 'desbloquear' and nota = 'Llegó el Excel corregido' from public.v_jornada_cierre
                       where jornada_id = (select id from dias where fecha = '2026-12-01')),
                  'El dueño desbloquea con nota y queda en el historial');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
insert into public.movimiento_caja (empresa_id, jornada_id, tipo, concepto, monto)
values ('aaaaaaaa-0000-0000-0000-000000000000', (select id from dias where fecha = '2026-12-01'), 'gasto', 'Aseo', 1000);
select pg_temp.ok(true, 'Desbloqueado, el día vuelve a recibir datos');
select pg_temp.falla($$select public.deshacer_archivo((select id from arch))$$,
                     '55000', 'El archivo sigue sin deshacerse mientras el otro día siga cerrado');

-- Empresas
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$select public.cerrar_dias(array(select id from dias))$$, 'P0002', 'B no cierra días de A');
select pg_temp.falla($$select public.desbloquear_dia((select id from dias where fecha = '2026-12-02'), 'intrusa')$$,
                     'P0002', 'B no desbloquea días de A');
select pg_temp.ok((select count(*) from public.jornada_cierre) = 0, 'B no ve los cierres de A');
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.jornada_cierre (empresa_id, jornada_id, accion)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', (select id from dias where fecha = '2026-12-02'), 'cerrar')$$,
                     '42501', 'Nadie escribe el historial de cierres a mano');
reset role;

\echo 'TODAS LAS PRUEBAS DE 0014 PASARON'
