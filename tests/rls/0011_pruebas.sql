-- =============================================================================
-- Pruebas de 0011_equipo.sql
-- Usa las empresas A y B de 0001 y agrega un lider y un responsable de punto en A.
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

-- Datos de partida (como dueño de la base): un segundo punto fijo, un lider, un
-- responsable del punto A1 y un lider en B.
insert into public.punto_venta (id, empresa_id, codigo, nombre) values
  ('aaaaaaaa-0000-0000-0000-0000000000f2', 'aaaaaaaa-0000-0000-0000-000000000000', 'E02', 'Punto A Dos');
insert into auth.users (id) values
  ('a0000000-0000-0000-0000-0000000000e1'), ('a0000000-0000-0000-0000-0000000000e2'),
  ('b0000000-0000-0000-0000-0000000000e1');
insert into public.usuario (id, empresa_id, nombre, rol, punto_id) values
  ('a0000000-0000-0000-0000-0000000000e1', 'aaaaaaaa-0000-0000-0000-000000000000', 'Lider A', 'lider', null),
  ('a0000000-0000-0000-0000-0000000000e2', 'aaaaaaaa-0000-0000-0000-000000000000', 'Responsable A1',
   'responsable_punto', 'aaaaaaaa-0000-0000-0000-000000000011'),
  ('b0000000-0000-0000-0000-0000000000e1', 'bbbbbbbb-0000-0000-0000-000000000000', 'Lider B', 'lider', null);
select pg_temp.ok(true, 'La base acepta los roles lider y responsable_punto');

select pg_temp.falla($$insert into public.usuario (id, empresa_id, nombre, rol)
                       values ('a0000000-0000-0000-0000-00000000000d', 'aaaaaaaa-0000-0000-0000-000000000000', 'x', 'jefe')$$,
                     '23514', 'Un rol que no existe se rechaza');

-- 1. Plantilla de configuración ---------------------------------------------------
select pg_temp.ok((select count(*) from public.equipo_catalogo
                   where empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000' and clase = 'tipo_observacion') = 7,
                  'Cada empresa empieza con los 7 tipos de observación de la plantilla');
select pg_temp.ok((select count(*) from public.equipo_catalogo
                   where empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000' and clase in ('tema', 'criterio')) = 0,
                  'Temas y criterios empiezan vacíos');
insert into public.empresa (id, nombre) values ('cccc0011-0000-0000-0000-000000000000', 'Empresa Plantilla');
select pg_temp.ok((select count(*) from public.equipo_catalogo
                   where empresa_id = 'cccc0011-0000-0000-0000-000000000000') = 7,
                  'Una empresa nueva nace con la plantilla');
select pg_temp.ok((select equipo_umbral_cumplimiento is null and equipo_reparto = 'partes_iguales'
                   from public.empresa_config where empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000'),
                  'Los umbrales empiezan vacíos y el reparto en partes iguales');

set role authenticated;

-- 2. Personas y puntos ----------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
insert into public.asesora (id, empresa_id, nombre_completo) values
  ('aaaaaaaa-0000-0000-0000-0000000000c1', 'aaaaaaaa-0000-0000-0000-000000000000', 'Persona Nueva');
select pg_temp.ok((select codigo ~ '^A[0-9]{3}$' from public.asesora where id = 'aaaaaaaa-0000-0000-0000-0000000000c1'),
                  'El lider crea una persona y la base le pone el código');
insert into public.asesora_punto (empresa_id, asesora_id, punto_id, desde) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-10-01'),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1', 'aaaaaaaa-0000-0000-0000-0000000000f2', '2026-10-01');
select pg_temp.ok((select count(*) from public.asesora_punto where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000000c1'
                   and hasta is null) = 2, 'Una persona queda en dos puntos a la vez');
select pg_temp.falla($$insert into public.asesora_punto (empresa_id, asesora_id, punto_id, desde) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'aaaaaaaa-0000-0000-0000-000000000011', '2026-11-01')$$,
                     '23P01', 'No puede tener dos asignaciones cruzadas al mismo punto');
update public.asesora_punto set hasta = '2026-10-31'
where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000000c1' and punto_id = 'aaaaaaaa-0000-0000-0000-0000000000f2';
select pg_temp.ok((select hasta = '2026-10-31' from public.asesora_punto
                   where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000000c1' and punto_id = 'aaaaaaaa-0000-0000-0000-0000000000f2'),
                  'Sacarla de un punto es cerrar la asignación con fecha');
select pg_temp.falla($$update public.asesora_punto set punto_id = 'aaaaaaaa-0000-0000-0000-000000000011'
                       where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000000c1'$$,
                     '42501', 'Una asignación no se mueve de punto: se cierra y se crea otra');
select pg_temp.falla($$update public.asesora set codigo = 'Z9' where id = 'aaaaaaaa-0000-0000-0000-0000000000c1'$$,
                     '42501', 'El código de una persona no se cambia');
update public.asesora set activa = false where id = 'aaaaaaaa-0000-0000-0000-0000000000c1';
update public.asesora set activa = true where id = 'aaaaaaaa-0000-0000-0000-0000000000c1';
select pg_temp.ok(true, 'El lider desactiva y activa a una persona');
with b as (delete from public.asesora_punto returning 1)
select pg_temp.ok((select count(*) from b) = 0, 'Nadie borra asignaciones');

select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.falla($$insert into public.asesora (empresa_id, nombre_completo)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'x')$$,
                     '42501', 'El responsable de punto no crea personas');
select pg_temp.falla($$insert into public.asesora_punto (empresa_id, asesora_id, punto_id) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'aaaaaaaa-0000-0000-0000-000000000011')$$,
                     '42501', 'El responsable de punto no asigna personas');

select pg_temp.como('b0000000-0000-0000-0000-0000000000e1');
select pg_temp.ok((select count(*) from public.asesora_punto) = 0, 'El lider de B no ve las asignaciones de A');
select pg_temp.falla($$insert into public.asesora_punto (empresa_id, asesora_id, punto_id) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'bbbbbbbb-0000-0000-0000-000000000011')$$,
                     '23503', 'B no puede asignar a su punto una persona de A');

-- 3. Venta por persona ------------------------------------------------------------
reset role;
create temp table carga (n int, p jsonb);
insert into carga values (1, $j${
  "fuente": "excel_dia", "nombre": "octubre.xlsx", "hash": "e011e011e011e011e011e011e011e011e011e011e011e011e011e011e011e011",
  "desde": "2026-10-03", "hasta": "2026-10-03", "jornadas": [],
  "ventas_persona": [
    {"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-10-03", "asesora_id": "aaaaaaaa-0000-0000-0000-0000000000c1",
     "texto_original": "Persona Nueva", "venta": 3777100, "facturas": 44, "venta_dia": 7554200, "facturas_dia": 88,
     "personas_dia": 2, "fila_origen": 5},
    {"punto_id": "aaaaaaaa-0000-0000-0000-000000000011", "fecha": "2026-10-03", "asesora_id": "aaaaaaaa-0000-0000-0000-000000000021",
     "texto_original": "Asesora Uno", "venta": 3777100, "facturas": 44, "venta_dia": 7554200, "facturas_dia": 88,
     "personas_dia": 2, "fila_origen": 5},
    {"punto_id": "aaaaaaaa-0000-0000-0000-0000000000f2", "fecha": "2026-10-03", "asesora_id": "aaaaaaaa-0000-0000-0000-0000000000c1",
     "texto_original": "Persona Nueva", "venta": 1000000, "facturas": null, "venta_dia": 1000000, "facturas_dia": null,
     "personas_dia": 1, "fila_origen": 6}],
  "metas": [{"punto_id": "aaaaaaaa-0000-0000-0000-0000000000f2", "asesora_id": null, "desde": "2026-11-01",
             "hasta": "2026-11-30", "monto": 25000000, "fila_origen": 2}]
}$j$), (2, $j${
  "fuente": "excel_dia", "nombre": "octubre corregido.xlsx", "hash": "f011f011f011f011f011f011f011f011f011f011f011f011f011f011f011f011",
  "desde": "2026-10-03", "hasta": "2026-10-03", "jornadas": [],
  "ventas_persona": [
    {"punto_id": "aaaaaaaa-0000-0000-0000-0000000000f2", "fecha": "2026-10-03", "asesora_id": "aaaaaaaa-0000-0000-0000-0000000000c1",
     "texto_original": "Persona Nueva", "venta": 1200000, "facturas": 9, "venta_dia": 1200000, "facturas_dia": 9,
     "personas_dia": 1, "fila_origen": 6}]
}$j$);
grant select on carga to authenticated;
set role authenticated;

select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
create temp table arch as select n, public.importar_archivo(p) as id from carga where n = 1;
select pg_temp.ok((select sum(venta) from public.v_venta_asesora) = 8554200,
                  'Finanzas sube el Excel y la venta por persona entra con su archivo');
select pg_temp.ok((select monto = 25000000 and fila_origen = 2 from public.meta_periodo
                   where archivo_id = (select id from arch)), 'La meta del mes entra con el Excel y su fila de origen');
select pg_temp.falla($$insert into public.meta_periodo (empresa_id, punto_id, desde, hasta, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011',
                        '2027-01-01', '2027-01-31', 1)$$,
                     '42501', 'Finanzas no escribe metas a mano');
select pg_temp.ok((select filas from public.archivo_importado where id = (select id from arch)) = 3,
                  'El archivo cuenta sus filas de venta por persona');
select pg_temp.ok((select sum(venta) from public.v_venta_asesora where fecha = '2026-10-03'
                   and punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') = 7554200,
                  'Un día de dos personas suma lo mismo que el día');
insert into arch select n, public.importar_archivo(p) from carga where n = 2;
select pg_temp.ok((select sum(venta) from public.v_venta_asesora
                   where punto_id = 'aaaaaaaa-0000-0000-0000-0000000000f2') = 1200000,
                  'Si dos archivos traen el mismo punto y día, cuenta el último (D-038)');

select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select count(distinct punto_id) from public.v_venta_asesora) = 1
                  and (select bool_and(punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') from public.v_venta_asesora),
                  'El responsable de punto solo ve la venta de su punto');
select pg_temp.falla($$select public.importar_archivo((select p from carga where n = 1))$$,
                     '42501', 'El responsable de punto no sube archivos');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
select pg_temp.ok((select count(distinct punto_id) from public.v_venta_asesora) = 2,
                  'El lider ve la venta de todos los puntos');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.venta_asesora_dia) = 2
                  and (select bool_and(punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') from public.venta_asesora_dia),
                  'La asesora solo ve la venta de su punto');
select pg_temp.falla($$update public.venta_asesora_dia set venta = 1$$, '42501', 'Nadie cambia la venta importada');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.venta_asesora_dia) = 0, 'El dueño de B no ve la venta por persona de A');

select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select public.deshacer_archivo((select id from arch where n = 2));
select pg_temp.ok((select sum(venta) from public.v_venta_asesora
                   where punto_id = 'aaaaaaaa-0000-0000-0000-0000000000f2') = 1000000,
                  'Al deshacer el último archivo vuelve a contar el anterior');

-- 4. Metas por período --------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
insert into public.meta_periodo (empresa_id, punto_id, desde, hasta, monto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-10-01', '2026-10-31', 120000000),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f2', '2026-10-01', '2026-10-31', 30000000);
insert into public.meta_periodo (empresa_id, punto_id, asesora_id, desde, hasta, monto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011',
   'aaaaaaaa-0000-0000-0000-0000000000c1', '2026-10-01', '2026-10-31', 40000000);
select pg_temp.ok(true, 'El lider pone metas de octubre por punto y por persona');
select pg_temp.falla($$insert into public.meta_periodo (empresa_id, punto_id, desde, hasta, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011',
                        '2026-10-15', '2026-11-15', 1)$$,
                     '23P01', 'No hay dos metas activas cruzadas para el mismo punto');
select pg_temp.falla($$update public.meta_periodo set monto = 1$$, '42501', 'Una meta no se edita: se desactiva');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select count(*) from public.meta_periodo) = 2, 'El responsable solo ve las metas de su punto');
select pg_temp.falla($$insert into public.meta_periodo (empresa_id, punto_id, desde, hasta, monto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011',
                        '2026-12-01', '2026-12-31', 1)$$,
                     '42501', 'El responsable no pone metas');

-- 5. Acompañamiento: observaciones y evaluaciones son privadas ----------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
insert into public.equipo_catalogo (id, empresa_id, clase, nombre) values
  ('aaaaaaaa-0000-0000-0000-0000000000d1', 'aaaaaaaa-0000-0000-0000-000000000000', 'criterio', 'Saludo'),
  ('aaaaaaaa-0000-0000-0000-0000000000d2', 'aaaaaaaa-0000-0000-0000-000000000000', 'tema', 'Cierre de venta');
select pg_temp.ok(true, 'El lider agrega criterios y temas');
insert into public.seguimiento (id, empresa_id, asesora_id, punto_id, tipo, tipo_observacion_id, texto, valoracion) values
  ('aaaaaaaa-0000-0000-0000-0000000000e1', 'aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
   'aaaaaaaa-0000-0000-0000-000000000011', 'observacion',
   (select id from public.equipo_catalogo where nombre = 'Coaching' and empresa_id = 'aaaaaaaa-0000-0000-0000-000000000000'),
   'Ofrece el producto del mes', 'bien'),
  ('aaaaaaaa-0000-0000-0000-0000000000e2', 'aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
   'aaaaaaaa-0000-0000-0000-0000000000f2', 'evaluacion', null, '', null);
insert into public.seguimiento_criterio (empresa_id, seguimiento_id, criterio_id, puntaje) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000e2', 'aaaaaaaa-0000-0000-0000-0000000000d1', 4);
select pg_temp.ok((select count(*) from public.seguimiento) = 2, 'El lider registra una observación y una evaluación');
select pg_temp.falla($$insert into public.seguimiento (empresa_id, asesora_id, punto_id, tipo) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'aaaaaaaa-0000-0000-0000-000000000011', 'observacion')$$,
                     '23514', 'Una observación necesita su tipo');
select pg_temp.falla($$insert into public.seguimiento_criterio (empresa_id, seguimiento_id, criterio_id, puntaje) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000e1',
                        'aaaaaaaa-0000-0000-0000-0000000000d1', 3)$$,
                     '42501', 'Los puntajes solo van en evaluaciones');
select pg_temp.falla($$update public.seguimiento set anulado = true where id = 'aaaaaaaa-0000-0000-0000-0000000000e1'$$,
                     '23514', 'Anular un registro pide una nota');
select pg_temp.falla($$update public.seguimiento set texto = 'otro' where id = 'aaaaaaaa-0000-0000-0000-0000000000e1'$$,
                     '42501', 'Un registro no se reescribe');

select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select array_agg(id) from public.seguimiento) = array['aaaaaaaa-0000-0000-0000-0000000000e1'::uuid],
                  'El responsable de punto solo ve los registros de su punto');
select pg_temp.ok((select count(*) from public.seguimiento_criterio) = 0,
                  'El responsable no ve los puntajes de una evaluación de otro punto');
select pg_temp.falla($$insert into public.seguimiento (empresa_id, asesora_id, punto_id, tipo, texto) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'aaaaaaaa-0000-0000-0000-0000000000f2', 'diagnostico', 'x')$$,
                     '42501', 'El responsable no registra en otro punto');
insert into public.seguimiento (empresa_id, asesora_id, punto_id, tipo, texto) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
   'aaaaaaaa-0000-0000-0000-000000000011', 'objetivo', 'Subir el ticket promedio');
select pg_temp.ok(true, 'El responsable registra en su punto');
select pg_temp.falla($$insert into public.seguimiento (empresa_id, asesora_id, punto_id, tipo, texto, autor_id) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
                        'aaaaaaaa-0000-0000-0000-000000000011', 'objetivo', 'x', 'a0000000-0000-0000-0000-0000000000e1')$$,
                     '42501', 'Nadie registra a nombre de otro');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.seguimiento) = 0, 'La asesora no ve observaciones ni evaluaciones');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.ok((select count(*) from public.seguimiento) = 0, 'Finanzas no ve observaciones ni evaluaciones');
select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
select pg_temp.ok((select count(*) from public.seguimiento) = 3, 'La encargada ve todo el acompañamiento');
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.seguimiento_criterio) = 1, 'El dueño ve los puntajes');
select pg_temp.como('b0000000-0000-0000-0000-0000000000e1');
select pg_temp.ok((select count(*) from public.seguimiento) = 0, 'El lider de B no ve el acompañamiento de A');
select pg_temp.falla($$insert into public.seguimiento (empresa_id, asesora_id, punto_id, tipo, tipo_observacion_id) values
                       ('bbbbbbbb-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-000000000021',
                        'bbbbbbbb-0000-0000-0000-000000000011', 'observacion',
                        'aaaaaaaa-0000-0000-0000-0000000000d1')$$,
                     '23503', 'B no puede usar un tipo de observación de A');

-- 6. Compromisos --------------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
insert into public.compromiso (id, empresa_id, asesora_id, punto_id, seguimiento_id, que, fecha_limite, prioridad) values
  ('aaaaaaaa-0000-0000-0000-0000000000a9', 'aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000c1',
   'aaaaaaaa-0000-0000-0000-000000000011', 'aaaaaaaa-0000-0000-0000-0000000000e1', 'Ofrecer el combo en cada venta',
   current_date - 3, 'alta');
select pg_temp.ok((select estado = 'abierto' and avance = 0 from public.compromiso), 'El lider crea un compromiso vencido');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
update public.compromiso set avance = 60, estado = 'en_curso' where id = 'aaaaaaaa-0000-0000-0000-0000000000a9';
select pg_temp.ok((select avance = 60 from public.compromiso), 'El responsable de su punto actualiza el avance');
update public.compromiso set estado = 'cumplido' where id = 'aaaaaaaa-0000-0000-0000-0000000000a9';
select pg_temp.ok((select avance = 100 and cerrado_en is not null from public.compromiso),
                  'Cumplido deja el avance en 100 y la fecha de cierre');
update public.compromiso set estado = 'abierto', avance = 20 where id = 'aaaaaaaa-0000-0000-0000-0000000000a9';
select pg_temp.ok((select cerrado_en is null from public.compromiso), 'Reabrir borra la fecha de cierre');
select pg_temp.falla($$update public.compromiso set estado = 'anulado'$$, '23514', 'Anular un compromiso pide una nota');
select pg_temp.falla($$update public.compromiso set que = 'otra cosa'$$, '42501', 'El qué de un compromiso no se reescribe');
with b as (delete from public.compromiso returning 1)
select pg_temp.ok((select count(*) from b) = 0, 'Nadie borra compromisos');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select count(*) from public.compromiso) = 0, 'La asesora no ve compromisos');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.compromiso) = 0, 'El dueño de B no ve compromisos de A');

-- 7. Sesiones de formación -----------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
insert into public.sesion_formacion (id, empresa_id, titulo, fecha) values
  ('aaaaaaaa-0000-0000-0000-0000000000b9', 'aaaaaaaa-0000-0000-0000-000000000000', 'Taller de cierre', current_date + 2);
insert into public.sesion_asistente (empresa_id, sesion_id, asesora_id) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000b9', 'aaaaaaaa-0000-0000-0000-0000000000c1');
insert into public.sesion_formacion (empresa_id, punto_id, titulo, fecha) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f2', 'Solo punto dos', current_date);
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select count(*) from public.sesion_formacion) = 1,
                  'El responsable ve las sesiones generales y las de su punto, no las de otro');
select pg_temp.falla($$insert into public.sesion_formacion (empresa_id, punto_id, titulo, fecha) values
                       ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f2', 'x', current_date)$$,
                     '42501', 'El responsable no programa sesiones en otro punto');
update public.sesion_asistente set asistio = true;
select pg_temp.ok((select bool_and(asistio) from public.sesion_asistente), 'El responsable marca la asistencia');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.ok((select count(*) from public.sesion_formacion) = 0, 'Finanzas no ve las sesiones');

-- 8. Recorrido guiado y configuración ---------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
insert into public.recorrido_usuario (empresa_id, recorrido, estado, paso) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'inicio', 'saltado', 2);
select pg_temp.ok((select count(*) from public.recorrido_usuario) = 1, 'Cada usuario guarda su recorrido');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
select pg_temp.ok((select count(*) from public.recorrido_usuario) = 0, 'Nadie ve el recorrido de otro');
select public.guardar_config_equipo('{"equipo_umbral_cumplimiento": 80, "equipo_umbral_dias_sin_seguimiento": 15}');
select pg_temp.ok((select equipo_umbral_cumplimiento = 80 and equipo_umbral_dias_sin_seguimiento = 15
                   and equipo_umbral_compromisos_vencidos is null from public.empresa_config),
                  'El lider pone los umbrales de su empresa');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.falla($$select public.guardar_config_equipo('{"equipo_umbral_cumplimiento": 1}')$$,
                     '42501', 'Finanzas no cambia los umbrales');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select equipo_umbral_cumplimiento is null from public.empresa_config),
                  'Los umbrales de A no tocan a B');

-- 9. Lo que ya existía, con los roles nuevos --------------------------------------------
reset role;
insert into public.jornada (empresa_id, punto_id, fecha) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000000f2', '2026-10-20'),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-10-20');
set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select bool_and(punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') from public.jornada),
                  'El responsable solo ve las jornadas de su punto');
select pg_temp.ok((select count(*) from public.movimiento_externo) = 0, 'El responsable no ve el banco');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
select pg_temp.ok((select count(distinct punto_id) from public.jornada where fecha = '2026-10-20') = 2,
                  'El lider ve las jornadas de todos los puntos');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
select pg_temp.ok((select bool_and(punto_id = 'aaaaaaaa-0000-0000-0000-000000000011') from public.jornada),
                  'La asesora sigue viendo solo su punto');
reset role;

\echo 'TODAS LAS PRUEBAS DE 0011 PASARON'
