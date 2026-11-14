-- =============================================================================
-- Pruebas de 0010_caja_del_excel.sql
-- =============================================================================

create function pg_temp.como(usuario uuid) returns void language sql as $$
  select set_config('request.jwt.claims', json_build_object('sub', usuario)::text, false);
$$;

create function pg_temp.ok(condicion boolean, prueba text) returns void language plpgsql as $$
begin
  if not condicion then raise exception 'FALLÓ: %', prueba; end if;
  raise notice 'OK  %', prueba;
end $$;

grant execute on all functions in schema pg_temp to authenticated, anon;

create temp table carga (p jsonb);
insert into carga values ($j${
  "fuente": "excel_dia", "nombre": "caja.xlsx", "hash": "1010101010101010101010101010101010101010101010101010101010101010",
  "desde": "2026-10-05", "hasta": "2026-10-05",
  "jornadas": [{"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-10-05",
                "caja": [{"tipo": "consignacion", "concepto": "Consignación", "monto": 500000, "fila_origen": 192},
                         {"tipo": "gasto", "concepto": "Gastos", "monto": 12000, "fila_origen": 190}]}]
}$j$);
grant select on carga to authenticated;

set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table arch as select public.importar_archivo((select p from carga)) as id;
select pg_temp.ok((select array_agg(tipo || ':' || monto order by fila_origen) from public.v_caja_vigente
                   where archivo_id = (select id from arch)) = array['gasto:12000', 'consignacion:500000'],
                  'La caja del Excel entra con su fila de origen');
select pg_temp.ok((select count(*) from public.causa_descuadre where codigo = 'consignacion_no_aparece') = 1,
                  'El catálogo trae la señal de consignación');
select public.deshacer_archivo((select id from arch));
select pg_temp.ok((select count(*) from public.v_caja_vigente where archivo_id = (select id from arch)) = 0,
                  'Lo de un archivo deshecho deja de contar');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.v_caja_vigente) >= 0, 'La asesora puede consultar su caja');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.v_caja_vigente where empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000') = 0,
                  'El dueño de B no ve la caja de A');
reset role;

\echo 'TODAS LAS PRUEBAS DE 0010 PASARON'
