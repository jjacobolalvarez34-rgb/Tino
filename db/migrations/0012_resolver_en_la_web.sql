-- =============================================================================
-- 0012_resolver_en_la_web.sql
-- Resolver en un toque lo que la importación no reconoció, y avisar los problemas del
-- archivo.
--
--   * Tipo nuevo de error: archivo_inconsistente. Por ejemplo, la hoja del día y el resumen
--     del mes dicen ventas distintas. Se avisa con su fila; Tino no elige ni cambia valores.
--   * resolver_nombre: crea el nombre por punto (alias) y pone a la persona en las filas
--     que estaban sin ella (venta por persona y turnos), y da por resueltos esos errores.
--   * resolver_producto: lo mismo para un producto.
--   * descartar_error: para lo que no es nombre ni producto. Exige una nota.
--   * Finanzas, que sube y revisa los archivos, también puede crear esos alias.
-- Nada se borra: las filas se completan, los errores se marcan resueltos con quién y cuándo.
-- =============================================================================

alter table public.error_importacion drop constraint error_importacion_tipo_check;
alter table public.error_importacion add constraint error_importacion_tipo_check
  check (tipo in ('fila_ilegible', 'nombre_sin_reconocer', 'producto_sin_reconocer',
                  'datafono_sin_punto', 'archivo_inconsistente', 'otro'));

-- Quien revisa los archivos también resuelve nombres y productos.
drop policy asesora_alias_crear on public.asesora_alias;
create policy asesora_alias_crear on public.asesora_alias
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte', 'lider']));
drop policy producto_alias_crear on public.producto_alias;
create policy producto_alias_crear on public.producto_alias
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));
drop policy venta_asesora_dia_cambiar on public.venta_asesora_dia;
create policy venta_asesora_dia_cambiar on public.venta_asesora_dia
  for update to authenticated
  using (empresa_id = app.empresa_actual()
         and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());


-- -----------------------------------------------------------------------------
-- resolver_nombre: este texto, en este punto, es esta persona.
-- Corre con los permisos de quien la llama (RLS y grants de siempre).
-- Devuelve cuántas filas de venta por persona quedaron con su persona.
-- -----------------------------------------------------------------------------
create or replace function public.resolver_nombre(p_texto text, p_punto uuid, p_asesora uuid)
returns int
language plpgsql security invoker set search_path = ''
as $$
declare
  v_empresa uuid := app.empresa_actual();
  v_norm    text := app.normalizar_texto(p_texto);
  v_filas   int;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;
  if coalesce(v_norm, '') = '' then
    raise exception 'El nombre está vacío' using errcode = '23514';
  end if;

  insert into public.asesora_alias (empresa_id, asesora_id, punto_id, texto_original, fuente)
  values (v_empresa, p_asesora, p_punto, trim(p_texto), 'resuelto en la web')
  on conflict (empresa_id, punto_id, texto_normalizado) do nothing;

  -- Si ese texto ya era de otra persona en este punto, no se pisa: se avisa.
  if exists (select 1 from public.asesora_alias a
             where a.empresa_id = v_empresa and a.punto_id = p_punto
               and a.texto_normalizado = v_norm and a.asesora_id <> p_asesora) then
    raise exception 'Ese nombre ya es de otra persona en este punto' using errcode = '23505';
  end if;

  update public.venta_asesora_dia v set asesora_id = p_asesora
  where v.empresa_id = v_empresa and v.punto_id = p_punto and v.asesora_id is null
    and app.normalizar_texto(v.texto_original) = v_norm;
  get diagnostics v_filas = row_count;

  update public.turno t set asesora_id = p_asesora
  from public.jornada j
  where j.id = t.jornada_id and t.empresa_id = v_empresa and j.punto_id = p_punto and t.asesora_id is null
    and app.normalizar_texto(t.texto_original) = v_norm;

  update public.error_importacion e
  set resuelto = true, resuelto_en = pg_catalog.now(), resuelto_por = auth.uid(),
      nota = coalesce(e.nota, 'Asignado a una persona en la web')
  where e.empresa_id = v_empresa and not e.resuelto and e.tipo = 'nombre_sin_reconocer'
    and app.normalizar_texto(regexp_replace(e.texto, '\s*\([^)]*\)\s*$', '')) = v_norm
    and app.punto_de_archivo(e.archivo_id) = p_punto;

  return v_filas;
end;
$$;

-- El punto de un archivo del día: el de sus jornadas o su venta por persona (un Excel del
-- día es de un solo punto). Vacío si el archivo no es de un solo punto.
create or replace function app.punto_de_archivo(p_archivo uuid)
returns uuid
language sql stable security invoker set search_path = ''
as $$
  select case when count(distinct x.punto_id) = 1 then min(x.punto_id::text)::uuid end
  from (
    select j.punto_id from public.reporte_caja r join public.jornada j on j.id = r.jornada_id where r.archivo_id = p_archivo
    union
    select v.punto_id from public.venta_asesora_dia v where v.archivo_id = p_archivo
  ) x
$$;


-- -----------------------------------------------------------------------------
-- resolver_producto: este texto es este producto (en toda la empresa).
-- -----------------------------------------------------------------------------
create or replace function public.resolver_producto(p_texto text, p_producto uuid)
returns int
language plpgsql security invoker set search_path = ''
as $$
declare
  v_empresa uuid := app.empresa_actual();
  v_norm    text := app.normalizar_texto(p_texto);
  v_filas   int;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;

  insert into public.producto_alias (empresa_id, producto_id, texto_original, fuente)
  values (v_empresa, p_producto, trim(p_texto), 'resuelto en la web')
  on conflict (empresa_id, texto_normalizado) do nothing;
  if exists (select 1 from public.producto_alias a
             where a.empresa_id = v_empresa and a.texto_normalizado = v_norm and a.producto_id <> p_producto) then
    raise exception 'Ese texto ya es de otro producto' using errcode = '23505';
  end if;

  update public.venta_detalle d set producto_id = p_producto
  where d.empresa_id = v_empresa and d.producto_id is null and app.normalizar_texto(d.texto_producto) = v_norm;
  get diagnostics v_filas = row_count;

  update public.error_importacion e
  set resuelto = true, resuelto_en = pg_catalog.now(), resuelto_por = auth.uid(),
      nota = coalesce(e.nota, 'Asignado a un producto en la web')
  where e.empresa_id = v_empresa and not e.resuelto and e.tipo = 'producto_sin_reconocer'
    and app.normalizar_texto(regexp_replace(e.texto, '\s*\([^)]*\)\s*$', '')) = v_norm;

  return v_filas;
end;
$$;


-- -----------------------------------------------------------------------------
-- descartar_error: "esto no es un nombre" o "ya se revisó el archivo". Con nota, siempre.
-- Marca todos los pendientes iguales (mismo tipo y mismo texto).
-- -----------------------------------------------------------------------------
create or replace function public.descartar_error(p_error uuid, p_nota text)
returns int
language plpgsql security invoker set search_path = ''
as $$
declare
  v_filas int;
  v_error public.error_importacion;
begin
  if length(trim(coalesce(p_nota, ''))) < 3 then
    raise exception 'Escriba por qué se descarta' using errcode = '23514';
  end if;
  select * into v_error from public.error_importacion where id = p_error;
  if not found then
    raise exception 'No se encontró' using errcode = 'P0002';
  end if;
  update public.error_importacion e
  set resuelto = true, resuelto_en = pg_catalog.now(), resuelto_por = auth.uid(), nota = trim(p_nota)
  where e.empresa_id = v_error.empresa_id and not e.resuelto and e.tipo = v_error.tipo
    and (e.id = p_error or (e.tipo <> 'archivo_inconsistente'
         and app.normalizar_texto(regexp_replace(e.texto, '\s*\([^)]*\)\s*$', ''))
           = app.normalizar_texto(regexp_replace(v_error.texto, '\s*\([^)]*\)\s*$', ''))));
  get diagnostics v_filas = row_count;
  return v_filas;
end;
$$;

-- =============================================================================
-- Fin de 0012.
-- =============================================================================
