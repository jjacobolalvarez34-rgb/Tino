-- =============================================================================
-- Pruebas de 0008_extracto_completo.sql
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

create temp table extracto (p jsonb);
insert into extracto values ($j${
  "fuente": "banco", "nombre": "extracto_completo.pdf",
  "hash": "8888888888888888888888888888888888888888888888888888888888888888",
  "desde": "2026-10-01", "hasta": "2026-10-01",
  "movimientos": [
    {"fila_origen": 1, "fuente": "banco", "tipo": "transferencia", "fecha": "2026-10-01",
     "punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "referencia": "90001234", "descripcion": "PAGO QR X", "bruto": 35900},
    {"fila_origen": 2, "fuente": "banco", "tipo": "transferencia", "fecha": "2026-10-01",
     "descripcion": "TRANSFERENCIA DESDE NEQUI", "etiqueta": "Nequi u otro banco", "bruto": 85000},
    {"fila_origen": 3, "fuente": "banco", "tipo": "deposito", "fecha": "2026-10-01",
     "descripcion": "ABONO NETO VISA", "etiqueta": "Datáfono", "bruto": 100000},
    {"fila_origen": 4, "fuente": "banco", "tipo": "consignacion", "fecha": "2026-10-01",
     "descripcion": "CONSIG LOCAL CAJ", "bruto": 500000},
    {"fila_origen": 5, "fuente": "banco", "tipo": "cargo", "fecha": "2026-10-01",
     "descripcion": "IMPTO GOBIERNO", "bruto": -4000}]
}$j$);
grant select on extracto to authenticated;

set role authenticated;

-- 1. El extracto entra completo, ordenado por tipo -------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table arch as select public.importar_archivo((select p from extracto)) as id;
select pg_temp.ok((select array_agg(tipo order by fila_origen) from public.v_movimiento_vigente
                   where archivo_id = (select id from arch))
                  = array['transferencia', 'transferencia', 'deposito', 'consignacion', 'cargo'],
                  'Cada línea entra con su tipo: transferencia, depósito, consignación y cargo');
select pg_temp.ok((select etiqueta from public.v_movimiento_vigente where archivo_id = (select id from arch)
                   and fila_origen = 2) = 'Nequi u otro banco', 'La etiqueta de la regla queda guardada');
select pg_temp.ok((select neto from public.movimiento_externo where archivo_id = (select id from arch)
                   and fila_origen = 5) = -4000, 'Un cargo entra en negativo');
select pg_temp.falla($$insert into public.movimiento_externo (empresa_id, archivo_id, fila_origen, fuente, tipo, fecha,
                                                              bruto, neto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', (select id from arch), 9, 'banco', 'inventado',
                        '2026-10-01', 1, 1)$$, '23514', 'Un tipo inventado no entra');

-- 2. Asignar un pago sin punto --------------------------------------------------
create temp table sin_punto as select id from public.movimiento_externo where archivo_id = (select id from arch)
  and fila_origen = 2;
select pg_temp.falla($$update public.movimiento_externo set punto_id = 'aaaaaaaa-0000-0000-0000-000000000011'
                       where id = (select id from sin_punto)$$, '23514', 'Asignar un punto exige una nota');
update public.movimiento_externo set punto_id = 'aaaaaaaa-0000-0000-0000-000000000011',
                                     nota = 'La asesora mandó el comprobante'
where id = (select id from sin_punto);
select pg_temp.ok((select punto_id = 'aaaaaaaa-0000-0000-0000-000000000011' from public.movimiento_externo
                   where id = (select id from sin_punto)), 'Con nota, el pago queda en su punto');
select pg_temp.falla($$update public.movimiento_externo set punto_id = null
                       where id = (select id from sin_punto)$$, '23514', 'Quitarlo también exige una nota nueva');
update public.movimiento_externo set nota = 'Otra nota sin cambiar el punto' where id = (select id from sin_punto);
select pg_temp.ok(true, 'Cambiar solo la nota no exige nada más');
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.auditoria where tabla = 'movimiento_externo' and accion = 'update'
                   and registro_id = (select id from sin_punto)) = 2, 'La asignación queda en auditoría');

-- 3. Roles y otra empresa -------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
with c as (update public.movimiento_externo set punto_id = null, nota = 'x' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'La asesora no asigna pagos');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
with c as (update public.movimiento_externo set punto_id = null, nota = 'x' where id = (select id from sin_punto) returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño de B no asigna pagos de A');
select pg_temp.ok((select count(*) from public.v_movimiento_vigente where archivo_id = (select id from arch)) = 0,
                  'El dueño de B no ve el extracto de A');
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$update public.movimiento_externo set punto_id = 'bbbbbbbb-0000-0000-0000-000000000011', nota = 'x'
                       where id = (select id from sin_punto)$$, '23503', 'Un pago de A no se asigna a un punto de B');

reset role;
select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Sigue sin haber políticas de DELETE');

\echo 'TODAS LAS PRUEBAS DE 0008 PASARON'
