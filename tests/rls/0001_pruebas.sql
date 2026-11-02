-- =============================================================================
-- Pruebas de permisos de 0001_cimientos.sql
-- Cada prueba imprime OK o detiene todo con un error que dice qué falló.
-- Se corre en una base de prueba, después de 00_supabase_simulado.sql y 0001.
-- =============================================================================

-- Datos de prueba (como administrador, sin RLS) -------------------------------
-- Dos empresas con un usuario de cada rol. El id termina en: d dueño,
-- e encargada, f finanzas, a asesora, c soporte.
insert into auth.users (id) values
  ('a0000000-0000-0000-0000-00000000000d'),
  ('a0000000-0000-0000-0000-00000000000e'),
  ('a0000000-0000-0000-0000-00000000000f'),
  ('a0000000-0000-0000-0000-00000000000a'),
  ('a0000000-0000-0000-0000-00000000000c'),
  ('b0000000-0000-0000-0000-00000000000d'),
  ('b0000000-0000-0000-0000-00000000000e'),
  ('b0000000-0000-0000-0000-00000000000f'),
  ('b0000000-0000-0000-0000-00000000000a'),
  ('b0000000-0000-0000-0000-00000000000c'),
  ('c0000000-0000-0000-0000-000000000000');  -- usuario de Auth sin empresa

insert into public.empresa (id, nombre) values
  ('aaaaaaaa-0000-0000-0000-000000000000', 'Empresa A'),
  ('bbbbbbbb-0000-0000-0000-000000000000', 'Empresa B');

insert into public.usuario (id, empresa_id, nombre, rol) values
  ('a0000000-0000-0000-0000-00000000000d', 'aaaaaaaa-0000-0000-0000-000000000000', 'Dueño A', 'dueno'),
  ('a0000000-0000-0000-0000-00000000000e', 'aaaaaaaa-0000-0000-0000-000000000000', 'Encargada A', 'encargada'),
  ('a0000000-0000-0000-0000-00000000000f', 'aaaaaaaa-0000-0000-0000-000000000000', 'Finanzas A', 'finanzas'),
  ('a0000000-0000-0000-0000-00000000000a', 'aaaaaaaa-0000-0000-0000-000000000000', 'Asesora A', 'asesora'),
  ('a0000000-0000-0000-0000-00000000000c', 'aaaaaaaa-0000-0000-0000-000000000000', 'Soporte A', 'soporte'),
  ('b0000000-0000-0000-0000-00000000000d', 'bbbbbbbb-0000-0000-0000-000000000000', 'Dueño B', 'dueno'),
  ('b0000000-0000-0000-0000-00000000000e', 'bbbbbbbb-0000-0000-0000-000000000000', 'Encargada B', 'encargada'),
  ('b0000000-0000-0000-0000-00000000000f', 'bbbbbbbb-0000-0000-0000-000000000000', 'Finanzas B', 'finanzas'),
  ('b0000000-0000-0000-0000-00000000000a', 'bbbbbbbb-0000-0000-0000-000000000000', 'Asesora B', 'asesora'),
  ('b0000000-0000-0000-0000-00000000000c', 'bbbbbbbb-0000-0000-0000-000000000000', 'Soporte B', 'soporte');

insert into public.punto_venta (id, empresa_id, codigo, nombre) values
  ('aaaaaaaa-0000-0000-0000-000000000011', 'aaaaaaaa-0000-0000-0000-000000000000', 'P01', 'Punto A1'),
  ('bbbbbbbb-0000-0000-0000-000000000011', 'bbbbbbbb-0000-0000-0000-000000000000', 'P01', 'Punto B1');

insert into public.asesora (id, empresa_id, codigo, nombre_completo) values
  ('aaaaaaaa-0000-0000-0000-000000000021', 'aaaaaaaa-0000-0000-0000-000000000000', 'A01', 'Asesora Uno'),
  ('bbbbbbbb-0000-0000-0000-000000000021', 'bbbbbbbb-0000-0000-0000-000000000000', 'A01', 'Asesora Dos');

insert into public.producto (id, empresa_id, codigo, nombre) values
  ('aaaaaaaa-0000-0000-0000-000000000031', 'aaaaaaaa-0000-0000-0000-000000000000', 'X1', 'Producto A'),
  ('bbbbbbbb-0000-0000-0000-000000000031', 'bbbbbbbb-0000-0000-0000-000000000000', 'X1', 'Producto B');

insert into public.tipo_venta (id, empresa_id, codigo, nombre) values
  ('aaaaaaaa-0000-0000-0000-000000000041', 'aaaaaaaa-0000-0000-0000-000000000000', 'DET', 'Detal A'),
  ('aaaaaaaa-0000-0000-0000-000000000042', 'aaaaaaaa-0000-0000-0000-000000000000', 'MAY', 'Mayor A'),
  ('bbbbbbbb-0000-0000-0000-000000000041', 'bbbbbbbb-0000-0000-0000-000000000000', 'DET', 'Detal B');

insert into public.medio_pago (id, empresa_id, codigo, nombre, tipo) values
  ('aaaaaaaa-0000-0000-0000-000000000051', 'aaaaaaaa-0000-0000-0000-000000000000', 'TR', 'Transferencia', 'transferencia'),
  ('bbbbbbbb-0000-0000-0000-000000000051', 'bbbbbbbb-0000-0000-0000-000000000000', 'TR', 'Transferencia', 'transferencia');

-- Funciones de ayuda ----------------------------------------------------------
create function pg_temp.como(usuario uuid) returns void language sql as $$
  select set_config('request.jwt.claims', json_build_object('sub', usuario)::text, false);
$$;

create function pg_temp.ok(condicion boolean, prueba text) returns void language plpgsql as $$
begin
  if not condicion then raise exception 'FALLÓ: %', prueba; end if;
  raise notice 'OK  %', prueba;
end $$;

-- Pasa si la consulta da exactamente el error esperado. Códigos de Postgres:
-- 42501 sin permiso, 23503 llave foránea, 23505 repetido, 23502 campo vacío,
-- 23514 check, 23P01 vigencias cruzadas.
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

-- 1. Cada uno ve solo su empresa ----------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.empresa) = 1
                  and (select nombre from public.empresa) = 'Empresa A',
                  'El dueño de A solo ve la empresa A');
select pg_temp.ok((select count(*) from public.punto_venta) = 1,
                  'El dueño de A solo ve los puntos de A');
select pg_temp.ok((select count(*) from public.usuario) = 5,
                  'El dueño de A ve los 5 usuarios de A y ninguno de B');

-- 2. No puede escribir en otra empresa ----------------------------------------
do $$ begin
  insert into public.punto_venta (empresa_id, codigo, nombre)
  values ('bbbbbbbb-0000-0000-0000-000000000000', 'X1', 'Intruso');
  raise exception 'FALLÓ: el dueño de A pudo crear un punto en B';
exception when insufficient_privilege then
  raise notice 'OK  El dueño de A no puede crear puntos en B';
end $$;

with c as (update public.punto_venta set nombre = 'Hackeado'
           where id = 'bbbbbbbb-0000-0000-0000-000000000011' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño de A no puede cambiar puntos de B');

do $$ begin
  update public.punto_venta set empresa_id = 'bbbbbbbb-0000-0000-0000-000000000000'
  where id = 'aaaaaaaa-0000-0000-0000-000000000011';
  raise exception 'FALLÓ: el dueño de A pudo pasar un punto suyo a la empresa B';
exception when insufficient_privilege then
  raise notice 'OK  Un punto no se puede mover a otra empresa';
end $$;

-- 3. Nadie borra ---------------------------------------------------------------
with c as (delete from public.punto_venta
           where id = 'aaaaaaaa-0000-0000-0000-000000000011' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'El dueño no puede borrar puntos (se desactivan)');

-- 4. Roles dentro de la empresa -----------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
insert into public.punto_venta (empresa_id, codigo, nombre)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'P02', 'Punto A2');
select pg_temp.ok(true, 'La encargada puede crear puntos en su empresa');

do $$ begin
  insert into public.perfil_fuente (empresa_id, fuente, nombre)
  values ('aaaaaaaa-0000-0000-0000-000000000000', 'banco', 'Bancolombia CSV');
  raise exception 'FALLÓ: la encargada pudo configurar un perfil de fuente';
exception when insufficient_privilege then
  raise notice 'OK  La encargada no configura perfiles de fuente';
end $$;

select pg_temp.ok((select count(*) from public.auditoria) = 0,
                  'La encargada no ve la auditoría');

select pg_temp.como('a0000000-0000-0000-0000-00000000000a');
do $$ begin
  insert into public.punto_venta (empresa_id, codigo, nombre)
  values ('aaaaaaaa-0000-0000-0000-000000000000', 'P03', 'Punto A3');
  raise exception 'FALLÓ: la asesora pudo crear un punto';
exception when insufficient_privilege then
  raise notice 'OK  La asesora no puede editar maestros';
end $$;

select pg_temp.ok((select count(*) from public.punto_venta) = 2,
                  'La asesora sí puede leer los puntos de su empresa');
select pg_temp.ok((select count(*) from public.usuario) = 1,
                  'La asesora solo se ve a sí misma en usuarios');

-- 5. Auditoría ----------------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.auditoria
                   where tabla = 'punto_venta' and despues ->> 'codigo' = 'P02') = 1,
                  'La creación de P02 quedó en auditoría y el dueño la ve');
select pg_temp.ok((select count(*) from public.auditoria
                   where empresa_id = 'bbbbbbbb-0000-0000-0000-000000000000') = 0,
                  'El dueño de A no ve la auditoría de B');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.punto_venta) = 1
                  and (select nombre from public.punto_venta) = 'Punto B1',
                  'El dueño de B solo ve su punto, intacto');

-- 6. Configuración por empresa -------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select count(*) from public.empresa_config) = 1,
                  'La empresa nace con su configuración, sin crearla a mano');

create temp table config_antes as select actualizado_en from public.empresa_config;
update public.empresa_config set desc_umbral = 2000;
select pg_temp.ok((select desc_umbral from public.empresa_config) = 2000
                  and (select count(*) from public.empresa_config) = 1,
                  'El dueño de A cambia el umbral de su empresa y solo ve su configuración');
select pg_temp.ok((select actualizado_en from public.empresa_config)
                  > (select actualizado_en from config_antes),
                  'actualizado_en cambia cuando cambia la configuración');
select pg_temp.ok((select registro_id from public.auditoria
                   where tabla = 'empresa_config' and accion = 'update')
                  = 'aaaaaaaa-0000-0000-0000-000000000000',
                  'El cambio de configuración queda en auditoría con su registro');

select pg_temp.como('a0000000-0000-0000-0000-00000000000e');
with c as (update public.empresa_config set desc_umbral = 5 returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'La encargada no cambia la configuración');

select pg_temp.como('b0000000-0000-0000-0000-00000000000d');
select pg_temp.ok((select desc_umbral from public.empresa_config) = 1000,
                  'La configuración de B no cambió');

-- 7. Sin sesión no se ve nada ---------------------------------------------------
select set_config('request.jwt.claims', '', false);
select pg_temp.ok((select count(*) from public.empresa) = 0
                  and (select count(*) from public.punto_venta) = 0,
                  'Sin usuario no se ve ningún dato');

select pg_temp.como('c0000000-0000-0000-0000-000000000000');
select pg_temp.ok((select count(*) from public.empresa) = 0,
                  'Un usuario de Auth sin empresa no ve nada');

-- 8. Cada rol de cada empresa ---------------------------------------------------
do $$
declare
  fila record;
begin
  for fila in
    select * from (values
      ('a0000000-0000-0000-0000-00000000000d'::uuid, 'Empresa A', 'dueño'),
      ('a0000000-0000-0000-0000-00000000000e'::uuid, 'Empresa A', 'encargada'),
      ('a0000000-0000-0000-0000-00000000000f'::uuid, 'Empresa A', 'finanzas'),
      ('a0000000-0000-0000-0000-00000000000a'::uuid, 'Empresa A', 'asesora'),
      ('a0000000-0000-0000-0000-00000000000c'::uuid, 'Empresa A', 'soporte'),
      ('b0000000-0000-0000-0000-00000000000d'::uuid, 'Empresa B', 'dueño'),
      ('b0000000-0000-0000-0000-00000000000e'::uuid, 'Empresa B', 'encargada'),
      ('b0000000-0000-0000-0000-00000000000f'::uuid, 'Empresa B', 'finanzas'),
      ('b0000000-0000-0000-0000-00000000000a'::uuid, 'Empresa B', 'asesora'),
      ('b0000000-0000-0000-0000-00000000000c'::uuid, 'Empresa B', 'soporte')
    ) as v (id, empresa, rol)
  loop
    perform pg_temp.como(fila.id);
    perform pg_temp.ok((select count(*) from public.empresa) = 1
                       and (select nombre from public.empresa) = fila.empresa
                       and (select count(*) from public.punto_venta
                            where empresa_id <> app.empresa_actual()) = 0,
                       format('%s de %s solo ve su empresa', fila.rol, fila.empresa));
  end loop;
end $$;

-- 9. Nadie borra, con ningún rol ni en ninguna tabla -----------------------------
do $$
declare
  usuario uuid;
  t text;
  n bigint;
begin
  foreach usuario in array array[
    'a0000000-0000-0000-0000-00000000000d', 'a0000000-0000-0000-0000-00000000000e',
    'a0000000-0000-0000-0000-00000000000f', 'a0000000-0000-0000-0000-00000000000a',
    'a0000000-0000-0000-0000-00000000000c'
  ]::uuid[]
  loop
    perform pg_temp.como(usuario);
    for t in select tablename from pg_tables where schemaname = 'public' loop
      execute format('delete from public.%I', t);
      get diagnostics n = row_count;
      if n <> 0 then
        raise exception 'FALLÓ: el usuario % borró % filas de %', usuario, n, t;
      end if;
    end loop;
    perform pg_temp.ok(true, format('Ningún borrado funciona con el usuario %s', usuario));
  end loop;
end $$;

-- 10. La auditoría no se toca ----------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.auditoria (tabla, accion) values ('x', 'insert')$$,
                     '42501', 'Nadie escribe a mano en la auditoría');
with c as (update public.auditoria set tabla = 'x' returning 1)
select pg_temp.ok((select count(*) from c) = 0, 'Nadie cambia la auditoría');

-- 11. Finanzas y soporte --------------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000f');
select pg_temp.falla($$insert into public.punto_venta (empresa_id, codigo, nombre)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'F1', 'x')$$,
                     '42501', 'Finanzas no edita maestros');
select pg_temp.falla($$insert into public.perfil_fuente (empresa_id, fuente, nombre)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'banco', 'x')$$,
                     '42501', 'Finanzas no configura perfiles de fuente');
select pg_temp.ok((select count(*) from public.auditoria) = 0, 'Finanzas no ve la auditoría');

select pg_temp.como('a0000000-0000-0000-0000-00000000000c');
insert into public.perfil_fuente (empresa_id, fuente, nombre)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'banco', 'Extracto de prueba');
select pg_temp.ok((select count(*) from public.perfil_fuente) = 1,
                  'Soporte configura perfiles de fuente en su empresa');
select pg_temp.ok((select count(*) from public.auditoria) > 0, 'Soporte ve la auditoría');

-- 12. Ninguna fila puede apuntar a otra empresa ----------------------------------
-- El dueño de A intenta enlazar filas suyas a filas de B. El error es el mismo
-- de un id que no existe, así que tampoco sirve para averiguar qué hay en B.
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.asesora_alias (empresa_id, asesora_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000021', 'x')$$,
                     '23503', 'Un alias de A no apunta a una asesora de B');
select pg_temp.falla($$insert into public.producto_alias (empresa_id, producto_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000031', 'x')$$,
                     '23503', 'Un alias de A no apunta a un producto de B');
select pg_temp.falla($$insert into public.precio_producto (empresa_id, producto_id, precio, vigente_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000031', 1000, '2026-01-01')$$,
                     '23503', 'Un precio de A no apunta a un producto de B');
select pg_temp.falla($$insert into public.precio_producto
                         (empresa_id, producto_id, tipo_venta_id, precio, vigente_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000031',
                               'bbbbbbbb-0000-0000-0000-000000000041', 1000, '2026-01-01')$$,
                     '23503', 'Un precio de A no apunta a un tipo de venta de B');
select pg_temp.falla($$insert into public.terminal_datafono
                         (empresa_id, punto_id, proveedor, codigo_terminal, activo_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000011', 'bold', 'T1', '2026-01-01')$$,
                     '23503', 'Un datáfono de A no apunta a un punto de B');
select pg_temp.falla($$insert into public.terminal_datafono
                         (empresa_id, punto_id, proveedor, codigo_terminal, activo_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'cccccccc-0000-0000-0000-000000000011', 'bold', 'T1', '2026-01-01')$$,
                     '23503', 'Un id que no existe da el mismo error que uno de B');
select pg_temp.falla($$insert into public.cuenta_recaudo
                         (empresa_id, punto_id, medio_pago_id, banco, ultimos4)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000011',
                               'aaaaaaaa-0000-0000-0000-000000000051', 'Banco', '1234')$$,
                     '23503', 'Una cuenta de A no apunta a un punto de B');
select pg_temp.falla($$insert into public.cuenta_recaudo (empresa_id, medio_pago_id, banco, ultimos4)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'bbbbbbbb-0000-0000-0000-000000000051', 'Banco', '1234')$$,
                     '23503', 'Una cuenta de A no apunta a un medio de pago de B');
select pg_temp.falla($$update public.usuario set punto_id = 'bbbbbbbb-0000-0000-0000-000000000011'
                       where id = 'a0000000-0000-0000-0000-00000000000a'$$,
                     '23503', 'Un usuario de A no apunta a un punto de B');
select pg_temp.falla($$update public.usuario set asesora_id = 'bbbbbbbb-0000-0000-0000-000000000021'
                       where id = 'a0000000-0000-0000-0000-00000000000a'$$,
                     '23503', 'Un usuario de A no apunta a una asesora de B');

update public.usuario set punto_id = 'aaaaaaaa-0000-0000-0000-000000000011'
where id = 'a0000000-0000-0000-0000-00000000000a';
select pg_temp.ok((select punto_id from public.usuario
                   where id = 'a0000000-0000-0000-0000-00000000000a') is not null,
                  'Un usuario de A sí se enlaza a un punto de A');

-- 13. Plan y estado son del proveedor --------------------------------------------
select pg_temp.falla($$update public.empresa set plan = 'completo'$$,
                     '42501', 'El dueño no se sube de plan');
select pg_temp.falla($$update public.empresa set estado = 'activa'$$,
                     '42501', 'El dueño no cambia el estado de su empresa');
select pg_temp.falla($$update public.empresa set puntos_contratados = 99$$,
                     '42501', 'El dueño no cambia los puntos contratados');
update public.empresa set nombre = 'Empresa A';
select pg_temp.ok(true, 'El dueño sí cambia el nombre de su empresa');

select pg_temp.como('a0000000-0000-0000-0000-00000000000c');
select pg_temp.falla($$update public.empresa set plan = 'completo'$$,
                     '42501', 'Soporte tampoco cambia el plan como usuario');

-- 14. Medio de pago con tipo -----------------------------------------------------
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$insert into public.medio_pago (empresa_id, codigo, nombre)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'SIN', 'Sin tipo')$$,
                     '23502', 'Un medio de pago no se crea sin tipo');
select pg_temp.falla($$insert into public.medio_pago (empresa_id, codigo, nombre, tipo)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'MAL', 'Mal', 'cripto')$$,
                     '23514', 'Un medio de pago no acepta un tipo inventado');

-- 15. Precios sin vigencias cruzadas ---------------------------------------------
insert into public.precio_producto (empresa_id, producto_id, precio, vigente_desde, vigente_hasta)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000031',
        1000, '2026-01-01', '2026-06-30');

select pg_temp.falla($$insert into public.precio_producto (empresa_id, producto_id, precio, vigente_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000031', 2000, '2026-06-30')$$,
                     '23P01', 'Dos precios generales no pueden coincidir un día');

insert into public.precio_producto (empresa_id, producto_id, precio, vigente_desde)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000031',
        2000, '2026-07-01');
select pg_temp.ok(true, 'Un precio nuevo arranca el día siguiente al anterior');

select pg_temp.falla($$insert into public.precio_producto (empresa_id, producto_id, precio, vigente_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000031', 3000, '2027-01-01')$$,
                     '23P01', 'Un precio sin fecha de fin sigue vigente hacia adelante');

insert into public.precio_producto (empresa_id, producto_id, tipo_venta_id, precio, vigente_desde)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000031',
        'aaaaaaaa-0000-0000-0000-000000000042', 900, '2026-01-01');
select pg_temp.ok(true, 'Otro tipo de venta puede tener su propio precio las mismas fechas');

select pg_temp.falla($$insert into public.precio_producto
                         (empresa_id, producto_id, tipo_venta_id, precio, vigente_desde)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000031',
                               'aaaaaaaa-0000-0000-0000-000000000042', 800, '2026-02-01')$$,
                     '23P01', 'Dos precios del mismo tipo de venta no pueden coincidir');

-- 16. Alias: lo original se guarda y lo normalizado se compara -------------------
insert into public.asesora_alias (empresa_id, asesora_id, texto_original)
values ('aaaaaaaa-0000-0000-0000-000000000000', 'aaaaaaaa-0000-0000-0000-000000000021', 'Ánge-la  MUÑOZ.');
select pg_temp.ok((select texto_original from public.asesora_alias) = 'Ánge-la  MUÑOZ.'
                  and (select texto_normalizado from public.asesora_alias) = 'ange la munoz',
                  'El alias guarda el texto tal cual y calcula el normalizado');
select pg_temp.falla($$insert into public.asesora_alias (empresa_id, asesora_id, texto_original)
                       values ('aaaaaaaa-0000-0000-0000-000000000000',
                               'aaaaaaaa-0000-0000-0000-000000000021', 'ange la munoz')$$,
                     '23505', 'Dos formas del mismo nombre no se repiten en la empresa');

-- 17. Sin sesión, con anon -------------------------------------------------------
reset role;
set role anon;
select set_config('request.jwt.claims', '', false);
select pg_temp.ok((select count(*) from public.empresa) = 0
                  and (select count(*) from public.punto_venta) = 0
                  and (select count(*) from public.usuario) = 0
                  and (select count(*) from public.auditoria) = 0,
                  'anon no ve ningún dato');
select pg_temp.falla($$insert into public.punto_venta (empresa_id, codigo, nombre)
                       values ('aaaaaaaa-0000-0000-0000-000000000000', 'N1', 'x')$$,
                     '42501', 'anon no escribe');

-- 18. Vaciar una tabla -----------------------------------------------------------
reset role;
set role authenticated;
select pg_temp.como('a0000000-0000-0000-0000-00000000000d');
select pg_temp.falla($$truncate public.punto_venta cascade$$,
                     '42501', 'Nadie vacía una tabla con TRUNCATE');

-- 19. Como administrador ---------------------------------------------------------
reset role;

select pg_temp.falla($$delete from auth.users where id = 'a0000000-0000-0000-0000-00000000000a'$$,
                     '23503', 'Borrar un usuario en Auth no arrastra su fila: se desactiva');

insert into public.empresa (id, nombre) values ('cccccccc-0000-0000-0000-000000000000', 'Empresa C');
select pg_temp.ok((select count(*) from public.empresa_config
                   where empresa_id = 'cccccccc-0000-0000-0000-000000000000') = 1,
                  'Una empresa nueva también nace con su configuración');

-- 20. Estructura: lo que debe cumplir toda tabla ----------------------------------
select pg_temp.ok(
  not exists (select from pg_tables where schemaname = 'public' and not rowsecurity),
  'Todas las tablas tienen RLS');

select pg_temp.ok(
  not exists (select from pg_policies where schemaname = 'public' and cmd in ('DELETE', 'ALL')),
  'Ninguna tabla tiene política de DELETE');

select pg_temp.ok(
  not exists (
    select from pg_class c
    join pg_namespace n on n.oid = c.relnamespace
    where n.nspname = 'public' and c.relkind = 'r'
      and exists (select from pg_attribute a
                  where a.attrelid = c.oid and a.attname = 'empresa_id')
      and not exists (
        select from pg_index i
        join pg_attribute a on a.attrelid = i.indrelid and a.attnum = i.indkey[0]
        where i.indrelid = c.oid and a.attname = 'empresa_id' and i.indpred is null)),
  'Toda tabla con empresa_id tiene un índice completo que empieza por empresa_id');

\echo 'TODAS LAS PRUEBAS PASARON'
