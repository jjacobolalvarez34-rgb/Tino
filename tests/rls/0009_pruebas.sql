-- =============================================================================
-- Pruebas de 0009_facturas.sql
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

create temp table lote (n int primary key, p jsonb);
insert into lote values
 (1, $j${"fuente": "siigo", "nombre": "Siigo 2026-10-02", "hash": "9191919191919191919191919191919191919191919191919191919191919191",
   "desde": "2026-10-02", "hasta": "2026-10-02",
   "facturas": [
     {"id_origen": "uuid-1", "numero": "FV-1-100", "punto_id": "aaaaaaaa-0000-0000-0000-000000000011",
      "fecha": "2026-10-02", "total": 71800, "descuento": 0, "anulada": false, "vendedor": "v1",
      "pagos": [{"nombre": "Efectivo", "valor": 71800}],
      "items": [{"producto_id": "aaaaaaaa-0000-0000-0000-000000000031", "texto_producto": "Producto A", "cantidad": 2,
                 "precio": 35900, "valor": 71800, "descuento": 0}]},
     {"id_origen": "uuid-2", "numero": "FV-1-101", "punto_id": "aaaaaaaa-0000-0000-0000-000000000011",
      "fecha": "2026-10-02", "total": 35900, "anulada": false, "items": []}],
   "errores": [{"fila_origen": 3, "tipo": "otro", "texto": "FV-1-102: centro de costo sin punto"}]}$j$),
 (2, $j${"fuente": "siigo", "nombre": "Siigo 2026-10-02 otra vez", "hash": "9292929292929292929292929292929292929292929292929292929292929292",
   "desde": "2026-10-02", "hasta": "2026-10-03",
   "facturas": [
     {"id_origen": "uuid-2", "numero": "FV-1-101", "punto_id": "aaaaaaaa-0000-0000-0000-000000000011",
      "fecha": "2026-10-02", "total": 35900, "anulada": true, "items": []},
     {"id_origen": "uuid-3", "numero": "FV-1-103", "punto_id": "aaaaaaaa-0000-0000-0000-000000000011",
      "fecha": "2026-10-03", "total": 12000, "anulada": false, "items": []}]}$j$);
grant select on lote to authenticated;

set role authenticated;

select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table r1 as select public.importar_facturas((select p from lote where n = 1)) as r;
select pg_temp.ok((select (r ->> 'nuevas')::int = 2 from r1), 'Las facturas entran como ventas');
select pg_temp.ok((select count(*) from public.v_factura where fecha = '2026-10-02') = 2
                  and (select sum(total) from public.v_factura where fecha = '2026-10-02') = 107700,
                  'Cada factura queda en el día y el punto, con su total');
select pg_temp.ok((select pagos_reportados -> 0 ->> 'nombre' from public.v_factura where numero_factura = 'FV-1-100')
                  = 'Efectivo', 'La factura guarda cómo dice que se pagó');
select pg_temp.ok((select count(*) from public.error_importacion where texto like 'FV-1-102%') = 1,
                  'La factura sin punto queda como error por resolver');

create temp table r2 as select public.importar_facturas((select p from lote where n = 2)) as r;
select pg_temp.ok((select (r ->> 'nuevas')::int = 1 and (r ->> 'repetidas')::int = 1 and (r ->> 'anuladas')::int = 1 from r2),
                  'Traer otra vez no repite: solo entra la nueva');
select pg_temp.ok((select anulada and nota = 'Anulada en siigo' from public.v_factura where numero_factura = 'FV-1-101'),
                  'Si la anularon en el programa, aquí queda anulada con nota');
select pg_temp.falla($$select public.importar_facturas((select p from lote where n = 1))$$, '23505',
                     'El mismo lote no entra dos veces');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$select public.importar_facturas((select p from lote where n = 1))$$, '42501',
                     'La asesora no trae facturas');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.v_factura) = 0, 'El dueño de B no ve facturas de A');
select pg_temp.falla($$select public.importar_facturas(jsonb_set((select p from lote where n = 1), '{hash}',
                         '"9393939393939393939393939393939393939393939393939393939393939393"'))$$,
                     '23503', 'B no carga facturas en un punto de A');

reset role;
select pg_temp.ok(
  not exists (select from pg_class c join pg_namespace n on n.oid = c.relnamespace
              where n.nspname = 'public' and c.relkind = 'v'
                and not coalesce(c.reloptions @> array['security_invoker=true'], false)),
  'Todas las vistas corren con los permisos de quien consulta');

\echo 'TODAS LAS PRUEBAS DE 0009 PASARON'
