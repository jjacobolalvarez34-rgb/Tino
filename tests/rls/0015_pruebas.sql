-- =============================================================================
-- Pruebas de 0015_formacion.sql
-- Usa las empresas A y B de 0001 y el lider, el responsable de A1 y el lider de B de 0011.
-- =============================================================================

create function pg_temp.como(usuario uuid) returns void language sql as $$
  select set_config('request.jwt.claims', json_build_object('sub', usuario)::text, false);
$$;

create function pg_temp.ok(condicion boolean, prueba text) returns void language plpgsql as $$
begin
  if not coalesce(condicion, false) then raise exception 'FALLÓ: %', prueba; end if;
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

-- Datos de partida (como dueño de la base): dos personas en A1 y una en A Dos, una en B1.
insert into public.asesora (id, empresa_id, codigo, nombre_completo) values
  ('aaaaaaaa-0000-0000-0000-0000000015a1', 'aaaaaaaa-0000-0000-0000-000000000000', 'F01', 'Persona Formación Uno'),
  ('aaaaaaaa-0000-0000-0000-0000000015a2', 'aaaaaaaa-0000-0000-0000-000000000000', 'F02', 'Persona Formación Dos'),
  ('aaaaaaaa-0000-0000-0000-0000000015a3', 'aaaaaaaa-0000-0000-0000-000000000000', 'F03', 'Persona Formación Tres'),
  ('bbbbbbbb-0000-0000-0000-0000000015b1', 'bbbbbbbb-0000-0000-0000-000000000000', 'F01', 'Persona B Formación');
insert into public.asesora_punto (empresa_id, asesora_id, punto_id, desde) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-01-01'),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a2', 'aaaaaaaa-0000-0000-0000-000000000011', '2026-01-01'),
  ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a3', 'aaaaaaaa-0000-0000-0000-0000000000f2', '2026-01-01'),
  ('bbbbbbbb-0000-0000-0000-000000000000', 'bbbbbbbb-0000-0000-0000-0000000015b1', 'bbbbbbbb-0000-0000-0000-000000000011', '2026-01-01');
update public.empresa_config set textos = textos || '{"programa": "Club Demo"}'::jsonb
where empresa_id = 'bbbbbbbb-0000-0000-0000-000000000000';

create temp table ids (clave text primary key, id uuid);
grant select, insert on ids to authenticated;

set role authenticated;

-- 1. Plantilla sugerida -----------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');  -- lider A
select pg_temp.ok((select count(*) from public.indicador_dia) = 0
                  and (select count(*) from public.equipo_catalogo where clase = 'etapa') = 0,
                  'Indicadores y etapas empiezan vacíos: no se llenan solos');
create temp table antes_plantilla as
  select (select count(*) from public.equipo_catalogo where clase in ('tema', 'criterio')) as temas_criterios;
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');  -- finanzas A
select pg_temp.falla($$select public.usar_plantilla_formacion()$$, '42501', 'Finanzas no usa la plantilla');
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');  -- asesora A
select pg_temp.falla($$select public.usar_plantilla_formacion()$$, '42501', 'La asesora no usa la plantilla');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');
create temp table plantilla_a as select (public.usar_plantilla_formacion() ->> 'agregados')::int as agregados;
select pg_temp.ok((select agregados from plantilla_a) > 0
                  and (select count(*) from public.equipo_catalogo where clase = 'etapa') = 5
                  and (select count(*) from public.indicador_dia) = 3
                  and (select count(*) from public.equipo_catalogo where clase in ('tema', 'criterio'))
                      >= (select temas_criterios from antes_plantilla),
                  'El lider usa la plantilla: llena etapas e indicadores y no pisa los temas y criterios que había');
select pg_temp.ok((select public.usar_plantilla_formacion() ->> 'agregados')::int = 0,
                  'Usarla otra vez no repite nada');
select pg_temp.ok(exists (select 1 from public.indicador_dia where nombre = 'Explicó el programa de fidelización' and base = 'atendidos')
                  and exists (select 1 from public.indicador_dia where nombre = 'Consultó puntos antes de cobrar' and base = 'facturas')
                  and exists (select 1 from public.indicador_dia where nombre = 'Referidos' and base = 'conteo'),
                  'Los indicadores de la plantilla traen su base');
update public.indicador_dia set nombre = 'Referidos del mes' where nombre = 'Referidos';
select pg_temp.ok(exists (select 1 from public.indicador_dia where nombre = 'Referidos del mes'), 'El lider cambia el nombre de un indicador');
select pg_temp.falla($$update public.indicador_dia set base = 'conteo' where nombre = 'Consultó puntos antes de cobrar'$$,
                     '42501', 'La base de un indicador no se cambia');
insert into ids select 'explico', id from public.indicador_dia where base = 'atendidos';
insert into ids select 'consulto', id from public.indicador_dia where base = 'facturas';
insert into ids select 'referidos', id from public.indicador_dia where base = 'conteo';
insert into ids select 'etapa1', id from public.equipo_catalogo where clase = 'etapa' and nombre = 'Diagnóstico';
insert into ids select 'etapa2', id from public.equipo_catalogo where clase = 'etapa' and nombre = 'Formación';
insert into ids select 'tema1', id from public.equipo_catalogo where clase = 'tema' and nombre = 'Venta consultiva';

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');  -- dueño B
select pg_temp.ok((select count(*) from public.indicador_dia) = 0, 'B no ve los indicadores de A');
create temp table plantilla_b as select (public.usar_plantilla_formacion() ->> 'agregados')::int as agregados;
select pg_temp.ok((select agregados from plantilla_b) = 18, 'B usa su propia plantilla');
select pg_temp.ok(exists (select 1 from public.indicador_dia where nombre = 'Explicó el Club Demo')
                  and exists (select 1 from public.equipo_catalogo where nombre = 'Explica el Club Demo'),
                  'La plantilla usa el nombre del programa de la empresa');
insert into ids select 'explico_b', id from public.indicador_dia where base = 'atendidos';
-- B arma sus propios indicadores y etapas, distintos de los de A.
insert into public.indicador_dia (empresa_id, nombre, base, orden)
values ('bbbbbbbb-0000-0000-0000-000000000000', 'Ofreció garantía extendida', 'facturas', 9);
insert into public.equipo_catalogo (empresa_id, clase, nombre, orden)
values ('bbbbbbbb-0000-0000-0000-000000000000', 'etapa', 'Inducción', 0);
select pg_temp.ok((select count(*) from public.indicador_dia) = 4 and (select count(*) from public.equipo_catalogo where clase = 'etapa') = 6,
                  'B tiene sus propios indicadores y etapas');

-- 2. Registro del día: quién lo llena -------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');  -- responsable de A1
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(
    jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 20,
      'valores', jsonb_build_object((select id from ids where clave = 'explico'), 8, (select id from ids where clave = 'consulto'), 5,
                                    (select id from ids where clave = 'referidos'), 2)),
    jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a2', 'clientes_atendidos', 15,
      'valores', jsonb_build_object((select id from ids where clave = 'explico'), 3))))) = 2,
  'El responsable registra el día de dos personas de su punto de una vez');
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a2', 'clientes_atendidos', 15,
      'valores', jsonb_build_object((select id from ids where clave = 'explico'), 3))))) = 0,
  'Guardar lo mismo otra vez no cambia nada');
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a2', 'clientes_atendidos', 16,
      'valores', jsonb_build_object((select id from ids where clave = 'explico'), 4))))) = 1,
  'El mismo día se corrige sin nota');
select pg_temp.ok((select count(*) from public.registro_dia where fecha = app.hoy()) = 2
                  and (select clientes_atendidos from public.registro_dia where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a2') = 16,
                  'Sigue habiendo una sola fila por persona, punto y día');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-0000000000f2', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a3', 'clientes_atendidos', 5))))$$,
  '42501', 'El responsable no registra en otro punto');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a3', 'clientes_atendidos', 5))))$$,
  '23514', 'No se registra a una persona que no estaba en ese punto');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 20,
      'valores', jsonb_build_object((select id from ids where clave = 'explico'), 21)))))$$,
  '22023', 'Explicar el programa no puede pasar de los clientes atendidos');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy() + 1,
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 1))))$$,
  '22023', 'No se registra un día que no ha pasado');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 20,
      'valores', jsonb_build_object((select id from ids where clave = 'explico_b'), 1)))))$$,
  '23514', 'No se usa un indicador de otra empresa');
select pg_temp.falla($$insert into public.registro_dia (empresa_id, asesora_id, punto_id, fecha, clientes_atendidos)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1',
                               'aaaaaaaa-0000-0000-0000-000000000011', app.hoy() - 3, 1)$$,
                     '42501', 'Nadie escribe la tabla directamente: solo con guardar_registros_dia');
select pg_temp.falla($$update public.registro_dia set clientes_atendidos = 99$$, '42501', 'Nadie cambia la tabla directamente');
select pg_temp.falla($$update public.registro_dia_valor set valor = 99$$, '42501', 'Nadie cambia los contadores directamente');

-- Otros roles
select pg_temp.como('a0000000-0000-0000-0000-00000000000a');  -- asesora
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object('punto_id', 'aaaaaaaa-0000-0000-0000-000000000011',
  'fecha', app.hoy(), 'filas', '[]'::jsonb))$$, '42501', 'La asesora no llena el registro del día');
select pg_temp.ok((select count(*) from public.registro_dia) = 0, 'La asesora no ve los registros del día');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');  -- finanzas
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object('punto_id', 'aaaaaaaa-0000-0000-0000-000000000011',
  'fecha', app.hoy(), 'filas', '[]'::jsonb))$$, '42501', 'Finanzas no llena el registro del día');
select pg_temp.ok((select count(*) from public.registro_dia) = 0 and (select count(*) from public.registro_dia_valor) = 0,
                  'Finanzas no ve los registros del día');
select pg_temp.como('a0000000-0000-0000-0000-00000000000e');  -- encargada
select pg_temp.ok((select count(*) from public.registro_dia) = 2, 'La encargada ve los registros del día');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');  -- dueño B
select pg_temp.ok((select count(*) from public.registro_dia) = 0 and (select count(*) from public.registro_dia_valor) = 0,
                  'B no ve los registros de A');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object('punto_id', 'aaaaaaaa-0000-0000-0000-000000000011',
  'fecha', app.hoy(), 'filas', '[]'::jsonb))$$, 'P0002', 'El dueño de B no registra en un punto de A');
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'bbbbbbbb-0000-0000-0000-000000000011', 'fecha', app.hoy(),
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'bbbbbbbb-0000-0000-0000-0000000015b1', 'clientes_atendidos', 10,
      'valores', jsonb_build_object((select id from public.indicador_dia where nombre = 'Ofreció garantía extendida'), 2))))) = 1,
  'El dueño de B registra el día con sus propios indicadores');

-- 3. Días que ya pasaron ----------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');  -- dueño A
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy() - 1,
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 12)))) = 1,
  'El dueño registra un día que se le había quedado sin llenar');
select pg_temp.falla($$select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy() - 1,
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 13))))$$,
  '22023', 'Corregir un día que ya pasó exige nota');
create temp table corregido as select public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy() - 1, 'nota', 'Contó mal los clientes',
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'clientes_atendidos', 13)))) as n;
select pg_temp.ok((select n from corregido) = 1
  and (select nota_correccion from public.registro_dia where fecha = app.hoy() - 1) = 'Contó mal los clientes',
  'Con nota sí se corrige, y la nota queda');
select pg_temp.ok((select count(*) from public.auditoria where tabla = 'registro_dia' and accion = 'update') >= 2,
                  'Cada corrección queda en la auditoría');

-- 4. Anular ------------------------------------------------------------------------------
insert into ids select 'ayer', id from public.registro_dia where fecha = app.hoy() - 1;
select pg_temp.falla($$select public.anular_registro_dia((select id from ids where clave = 'ayer'), '')$$,
                     '22023', 'Anular exige nota');
select public.anular_registro_dia((select id from ids where clave = 'ayer'), 'Era de otra persona');
select pg_temp.ok((select anulado from public.registro_dia where id = (select id from ids where clave = 'ayer')),
                  'Un registro se anula con nota y no se borra');
select pg_temp.ok(public.guardar_registros_dia(jsonb_build_object(
  'punto_id', 'aaaaaaaa-0000-0000-0000-000000000011', 'fecha', app.hoy() - 1,
  'filas', jsonb_build_array(jsonb_build_object('asesora_id', 'aaaaaaaa-0000-0000-0000-0000000015a2', 'clientes_atendidos', 9)))) = 1,
  'Después de anular, el día se registra a la persona correcta');
with b as (delete from public.registro_dia returning 1)
select pg_temp.ok((select count(*) from b) = 0, 'Nadie borra registros del día');

-- 5. Lo que cuenta: manual e integración el mismo día ---------------------------------------
reset role;
insert into public.registro_dia (empresa_id, asesora_id, punto_id, fecha, origen, fuente, clientes_atendidos)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1', 'aaaaaaaa-0000-0000-0000-000000000011',
        app.hoy(), 'integracion', 'App de fidelización', 25);
select pg_temp.falla($$insert into public.registro_dia (empresa_id, asesora_id, punto_id, fecha, clientes_atendidos)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1',
                               'aaaaaaaa-0000-0000-0000-000000000011', app.hoy(), 1)$$,
                     '23505', 'Ni siquiera la base acepta dos registros manuales del mismo día');
set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');
select pg_temp.ok((select count(*) from public.registro_dia where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1'
                   and fecha = app.hoy()) = 2, 'Manual e integración del mismo día se guardan los dos, sin pisarse');
select pg_temp.ok((select origen = 'manual' and clientes_atendidos = 20 and hay_otro_origen from public.v_registro_dia
                   where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1' and fecha = app.hoy()),
                  'Para los porcentajes cuenta el manual, y se avisa que hay otro');
select pg_temp.ok((select (valores ->> (select id::text from ids where clave = 'explico'))::int = 8 from public.v_registro_dia
                   where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1' and fecha = app.hoy()),
                  'La vista trae los contadores del día');
select pg_temp.ok(not exists (select 1 from public.v_registro_dia
                              where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1' and fecha = app.hoy() - 2),
                  'Un día sin registro no aparece: no cuenta como cero');

-- 6. Paso del ciclo ---------------------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-0000000000e1');  -- lider
insert into public.asesora_etapa (empresa_id, asesora_id, etapa_id)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1', (select id from ids where clave = 'etapa1'));
select pg_temp.falla($$insert into public.asesora_etapa (empresa_id, asesora_id, etapa_id)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1',
                               (select id from ids where clave = 'tema1'))$$,
                     '23514', 'Un tema no sirve como etapa');
select pg_temp.como('a0000000-0000-0000-0000-0000000000e2');  -- responsable de A1
insert into public.asesora_etapa (empresa_id, asesora_id, etapa_id, nota)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1', (select id from ids where clave = 'etapa2'),
        'Terminó el diagnóstico');
select pg_temp.ok((select etapa_id = (select id from ids where clave = 'etapa2') from public.v_asesora_etapa
                   where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1'),
                  'El responsable cambia el paso de una persona de su punto, y el actual es el último');
select pg_temp.ok((select count(*) from public.asesora_etapa where asesora_id = 'aaaaaaaa-0000-0000-0000-0000000015a1') = 2,
                  'El cambio de paso queda en la historia');
select pg_temp.falla($$insert into public.asesora_etapa (empresa_id, asesora_id, etapa_id)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a3',
                               (select id from ids where clave = 'etapa1'))$$,
                     '42501', 'El responsable no cambia el paso de alguien de otro punto');
select pg_temp.falla($$update public.asesora_etapa set nota = 'x'$$, '42501', 'La historia del ciclo no se reescribe');
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');  -- finanzas
select pg_temp.ok((select count(*) from public.asesora_etapa) = 0, 'Finanzas no ve el ciclo de formación');
select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.asesora_etapa) = 0, 'B no ve el ciclo de A');
select pg_temp.falla($$insert into public.asesora_etapa (empresa_id, asesora_id, etapa_id)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-0000000015a1',
                               (select id from ids where clave = 'etapa1'))$$,
                     '42501', 'B no cambia el paso de alguien de A');

\echo 'TODAS LAS PRUEBAS DE 0015 PASARON'
