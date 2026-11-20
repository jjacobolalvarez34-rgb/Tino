-- =============================================================================
-- Pruebas de 0012_resolver_en_la_web.sql
-- Usa las empresas, puntos, personas, productos y usuarios de las pruebas anteriores.
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

create temp table carga (p jsonb);
insert into carga values ($j${
  "fuente": "excel_dia", "nombre": "noviembre.xlsx", "hash": "a012a012a012a012a012a012a012a012a012a012a012a012a012a012a012a012",
  "desde": "2026-11-03", "hasta": "2026-11-04",
  "jornadas": [{"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-11-03", "pagos": [],
                "turnos": [{"asesora_id": null, "texto_original": "Angie", "fila_origen": 5}],
                "reporte": {"hoja": "03", "fila_origen": 177, "efectivo_contado": 0, "venta_teorica": 0, "descuadre": 0, "asesoras_texto": "Angie"},
                "venta": {"total": 0, "fila_origen": 176, "detalle": [
                  {"producto_id": null, "texto_producto": "Bolsas Kit Profesional", "cantidad": 2, "precio_lista": 5000,
                   "valor": 10000, "fila_origen": 127}]}}],
  "ventas_persona": [
    {"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-11-03", "asesora_id": null, "texto_original": "angie",
     "venta": 900000, "facturas": 9, "venta_dia": 900000, "facturas_dia": 9, "personas_dia": 1, "fila_origen": 33},
    {"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-11-04", "asesora_id": null, "texto_original": "Tatiana",
     "venta": 500000, "facturas": 5, "venta_dia": 500000, "facturas_dia": 5, "personas_dia": 1, "fila_origen": 34}],
  "errores": [
    {"fila_origen": 33, "tipo": "nombre_sin_reconocer", "texto": "Angie (DESC FACT)"},
    {"fila_origen": 5, "tipo": "nombre_sin_reconocer", "texto": "Angie (03)"},
    {"fila_origen": 34, "tipo": "nombre_sin_reconocer", "texto": "Tatiana (DESC FACT)"},
    {"fila_origen": 127, "tipo": "producto_sin_reconocer", "texto": "Bolsas Kit Profesional (03)"},
    {"fila_origen": 176, "tipo": "archivo_inconsistente", "texto": "2026-11-03: la hoja «03» dice $ 0 y el resumen dice $ 900.000."}]
}$j$);
grant select on carga to authenticated;

set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table arch as select public.importar_archivo((select p from carga)) as id;
select pg_temp.ok((select count(*) from public.error_importacion where archivo_id = (select id from arch)
                   and tipo = 'archivo_inconsistente') = 1, 'Un problema del archivo queda como error propio, con su fila');
select pg_temp.ok((select sum(venta) from public.v_venta_asesora where asesora_id is null
                   and fecha between '2026-11-03' and '2026-11-04') = 1400000, 'Entran 1.400.000 sin persona');

-- Asignar un nombre en un toque
select pg_temp.ok(public.resolver_nombre('Angie', 'aaaaaaaa-0000-0000-0000-000000000011',
                                         'aaaaaaaa-0000-0000-0000-000000000021') = 1,
                  'Finanzas asigna "Angie" del punto A1 a una persona: se reprocesa la fila');
select pg_temp.ok((select sum(venta) from public.v_venta_asesora where asesora_id is null
                   and fecha between '2026-11-03' and '2026-11-04') = 500000,
                  'La venta sin persona baja exactamente en lo de ese nombre');
select pg_temp.ok((select count(*) from public.turno t join public.jornada j on j.id = t.jornada_id
                   where j.fecha = '2026-11-03' and t.asesora_id = 'aaaaaaaa-0000-0000-0000-000000000021') = 1,
                  'El turno del día también queda con su persona');
select pg_temp.ok((select bool_and(resuelto and resuelto_por = 'a0000000-0000-0000-0000-00000000000f')
                   from public.error_importacion where archivo_id = (select id from arch) and texto like 'Angie%'),
                  'Los dos avisos de "Angie" quedan resueltos, con quién lo hizo');
select pg_temp.ok((select not resuelto from public.error_importacion where archivo_id = (select id from arch)
                   and texto like 'Tatiana%'), 'Lo ambiguo sigue por resolver');
select pg_temp.ok((select count(*) from public.asesora_alias where texto_normalizado = 'angie'
                   and punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') = 1,
                  'Queda el nombre del punto: el próximo archivo ya lo reconoce');
select pg_temp.ok(public.resolver_nombre('ANGIE', 'aaaaaaaa-0000-0000-0000-000000000011',
                                         'aaaaaaaa-0000-0000-0000-000000000021') = 0,
                  'Asignarlo otra vez no repite ni falla');

reset role;
insert into public.asesora (id, empresa_id, codigo, nombre_completo) values
  ('aaaaaaaa-0000-0000-0000-0000000000c9', 'aaaaaaaa-0000-0000-0000-000000000000', 'A912', 'Otra Persona');
set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.falla($$select public.resolver_nombre('Angie', 'aaaaaaaa-0000-0000-0000-000000000011',
                                                     'aaaaaaaa-0000-0000-0000-0000000000c9')$$,
                     '23505', 'Un nombre que ya es de otra persona en ese punto no se pisa');

-- Producto
select pg_temp.ok(public.resolver_producto('BOLSAS KIT PROFESIONAL', 'aaaaaaaa-0000-0000-0000-000000000031') = 1,
                  'Finanzas asigna un producto y se reprocesa su fila');
select pg_temp.ok((select resuelto from public.error_importacion where archivo_id = (select id from arch)
                   and tipo = 'producto_sin_reconocer'), 'El aviso del producto queda resuelto');

-- Descartar con nota
select pg_temp.falla($$select public.descartar_error((select id from public.error_importacion
                       where tipo = 'archivo_inconsistente' and not resuelto limit 1), '')$$,
                     '23514', 'Descartar pide una nota');
select pg_temp.ok(public.descartar_error((select id from public.error_importacion
                  where tipo = 'archivo_inconsistente' and not resuelto limit 1), 'Revisado con el punto') = 1,
                  'Se descarta con nota');

-- Permisos y empresas
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.falla($$select public.resolver_nombre('Tatiana', 'aaaaaaaa-0000-0000-0000-000000000011',
                                                     'aaaaaaaa-0000-0000-0000-000000000021')$$,
                     '42501', 'La asesora no resuelve nombres');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$select public.resolver_nombre('Tatiana', 'aaaaaaaa-0000-0000-0000-000000000011',
                                                     'aaaaaaaa-0000-0000-0000-000000000021')$$,
                     '23503', 'B no resuelve nombres en un punto de A');
select pg_temp.ok((select count(*) from public.error_importacion) = 0, 'B no ve los avisos de A');
reset role;

\echo 'TODAS LAS PRUEBAS DE 0012 PASARON'
