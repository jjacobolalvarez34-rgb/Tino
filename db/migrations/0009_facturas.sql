-- =============================================================================
-- 0009_facturas.sql
-- Facturas traídas del programa de facturación de la empresa (Siigo hoy; Alegra,
-- World Office o Loggro después), con la misma forma para todos (D-041).
--
-- Cada factura es una venta con su id en el programa de origen. Traer otra vez el mismo
-- rango no la repite: si ya está, se salta; si en el programa la anularon, aquí queda
-- anulada con nota. Nada se borra.
-- =============================================================================

alter table public.venta
  add column fuente_origen   text,
  add column id_origen       text,
  add column vendedor_texto  text,
  -- Cómo dice el programa que se pagó: [{"nombre": "Efectivo", "valor": 35900}]. Es lo
  -- que reporta la factura; los pagos que se concilian siguen saliendo del Excel del día.
  add column pagos_reportados jsonb not null default '[]'::jsonb,
  add constraint venta_origen_completo check ((fuente_origen is null) = (id_origen is null));

create index venta_origen_idx on public.venta (empresa_id, fuente_origen, id_origen) where id_origen is not null;

-- Las facturas que cuentan: de un archivo cargado.
create view public.v_factura with (security_invoker = true) as
select v.id, v.empresa_id, v.jornada_id, j.punto_id, j.fecha, v.numero_factura, v.total, v.descuento, v.anulada,
       v.nota, v.fuente_origen, v.id_origen, v.vendedor_texto, v.pagos_reportados, v.archivo_id, v.fila_origen
from public.venta v
join public.jornada j on j.id = v.jornada_id
join public.archivo_importado a on a.id = v.archivo_id and a.estado = 'cargado'
where v.id_origen is not null;


-- -----------------------------------------------------------------------------
-- Cargar facturas
-- p = {fuente, nombre, hash, desde, hasta, facturas: [{id_origen, numero, punto_id,
--      fecha, total, descuento, anulada, vendedor, pagos, items: [...]}], errores: [...]}
-- Devuelve {archivo, nuevas, repetidas, anuladas}.
-- -----------------------------------------------------------------------------

create or replace function public.importar_facturas(p jsonb)
returns jsonb
language plpgsql security invoker set search_path = ''
as $$
declare
  v_empresa   uuid := app.empresa_actual();
  v_archivo   uuid;
  v_jornada   uuid;
  v_venta     uuid;
  v_existente record;
  f           jsonb;
  v_fila      int := 0;
  v_nuevas    int := 0;
  v_repetidas int := 0;
  v_anuladas  int := 0;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;

  insert into public.archivo_importado (empresa_id, fuente, nombre, hash, desde, hasta, subido_por)
  values (v_empresa, 'siigo', p ->> 'nombre', p ->> 'hash', (p ->> 'desde')::date, (p ->> 'hasta')::date, auth.uid())
  returning id into v_archivo;

  for f in select * from jsonb_array_elements(coalesce(p -> 'facturas', '[]'::jsonb))
  loop
    v_fila := v_fila + 1;
    -- ¿Ya está en un archivo que cuenta?
    select v.id, v.anulada into v_existente
    from public.venta v join public.archivo_importado a on a.id = v.archivo_id and a.estado = 'cargado'
    where v.empresa_id = v_empresa and v.fuente_origen = p ->> 'fuente' and v.id_origen = f ->> 'id_origen'
    limit 1;

    if v_existente.id is not null then
      v_repetidas := v_repetidas + 1;
      if (f ->> 'anulada')::boolean and not v_existente.anulada then
        update public.venta set anulada = true, nota = 'Anulada en ' || (p ->> 'fuente') where id = v_existente.id;
        v_anuladas := v_anuladas + 1;
      end if;
      continue;
    end if;

    insert into public.jornada (empresa_id, punto_id, fecha)
    values (v_empresa, (f ->> 'punto_id')::uuid, (f ->> 'fecha')::date)
    on conflict (empresa_id, punto_id, fecha) do nothing;
    select id into v_jornada from public.jornada
    where empresa_id = v_empresa and punto_id = (f ->> 'punto_id')::uuid and fecha = (f ->> 'fecha')::date;

    insert into public.venta (empresa_id, jornada_id, numero_factura, total, descuento, anulada, archivo_id,
                              fila_origen, fuente_origen, id_origen, vendedor_texto, pagos_reportados)
    values (v_empresa, v_jornada, f ->> 'numero', (f ->> 'total')::bigint, coalesce((f ->> 'descuento')::bigint, 0),
            coalesce((f ->> 'anulada')::boolean, false), v_archivo, v_fila, p ->> 'fuente', f ->> 'id_origen',
            f ->> 'vendedor', coalesce(f -> 'pagos', '[]'::jsonb))
    returning id into v_venta;

    insert into public.venta_detalle (empresa_id, venta_id, producto_id, texto_producto, cantidad, precio_lista,
                                      valor, descuento, archivo_id, fila_origen)
    select v_empresa, v_venta, x.producto_id, x.texto_producto, coalesce(x.cantidad, 0), coalesce(x.precio, 0),
           coalesce(x.valor, 0), coalesce(x.descuento, 0), v_archivo, v_fila
    from jsonb_to_recordset(coalesce(f -> 'items', '[]'::jsonb))
         as x(producto_id uuid, texto_producto text, cantidad int, precio bigint, valor bigint, descuento bigint);
    v_nuevas := v_nuevas + 1;
  end loop;

  insert into public.error_importacion (empresa_id, archivo_id, fila_origen, tipo, texto)
  select v_empresa, v_archivo, x.fila_origen, x.tipo, x.texto
  from jsonb_to_recordset(coalesce(p -> 'errores', '[]'::jsonb)) as x(fila_origen int, tipo text, texto text);

  update public.archivo_importado set filas = v_nuevas where id = v_archivo;
  return jsonb_build_object('archivo', v_archivo, 'nuevas', v_nuevas, 'repetidas', v_repetidas, 'anuladas', v_anuladas);
end;
$$;

revoke execute on function public.importar_facturas(jsonb) from public, anon;
grant execute on function public.importar_facturas(jsonb) to authenticated;

-- =============================================================================
-- Fin de 0009.
-- =============================================================================
