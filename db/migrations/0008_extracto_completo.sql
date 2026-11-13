-- =============================================================================
-- 0008_extracto_completo.sql
-- El extracto entra completo y ordenado: cada línea con su tipo, según las reglas del
-- perfil del banco de cada empresa (D-040). Antes solo entraban los pagos con código.
--
-- Tipos de movimiento nuevos: consignacion (plata que el punto lleva al banco) y cargo
-- (lo que sale: nómina, impuestos, comisiones del banco). etiqueta guarda lo que dice
-- la regla que lo clasificó, como "Nequi u otro banco" o "Datáfono".
--
-- Un pago de cliente sin punto (sin código, o con un código que no es de ningún punto)
-- es una transferencia con punto_id vacío: se asigna a mano, con nota, y queda en
-- auditoría quién lo hizo.
-- =============================================================================

alter table public.movimiento_externo drop constraint movimiento_externo_tipo_check;
alter table public.movimiento_externo add constraint movimiento_externo_tipo_check
  check (tipo in ('transferencia', 'cobro', 'reversion', 'deposito', 'consignacion', 'cargo', 'otro'));

alter table public.movimiento_externo add column etiqueta text;

-- Asignar (o cambiar) el punto de un pago es una decisión: exige una nota nueva. Quién
-- lo hizo y cuándo queda en auditoría.
create or replace function app.asignar_punto_con_nota()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  if new.punto_id is distinct from old.punto_id
     and (coalesce(btrim(new.nota), '') = '' or new.nota is not distinct from old.nota) then
    raise exception 'Asignar un pago a un punto exige una nota nueva' using errcode = '23514';
  end if;
  return new;
end;
$$;

create trigger movimiento_externo_asignar
  before update on public.movimiento_externo
  for each row execute function app.asignar_punto_con_nota();

-- Para la lista de pagos sin punto, que se consulta por fecha.
create index movimiento_externo_sin_punto_idx on public.movimiento_externo (empresa_id, fecha)
  where punto_id is null and tipo = 'transferencia';

-- La vista toma la columna nueva (en una vista, * se fija al crearla).
create or replace view public.v_movimiento_vigente with (security_invoker = true) as
select m.id, m.empresa_id, m.archivo_id, m.fila_origen, m.fuente, m.tipo, m.fecha, m.hora, m.fecha_canje,
       m.punto_id, m.terminal_id, m.cuenta_id, m.referencia, m.descripcion, m.franquicia, m.tipo_tarjeta,
       m.bruto, m.comision, m.retenciones, m.prestamo, m.neto, m.nota, m.creado_en, m.etiqueta
from public.movimiento_externo m
join public.archivo_importado a on a.id = m.archivo_id and a.estado = 'cargado';

-- importar_archivo guarda también la etiqueta. Lo demás es igual a 0007.
create or replace function public.importar_archivo(p jsonb)
returns uuid
language plpgsql security invoker set search_path = ''
as $$
declare
  v_empresa  uuid := app.empresa_actual();
  v_archivo  uuid;
  v_jornada  uuid;
  v_venta    uuid;
  j          jsonb;
  v_filas    int := 0;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;

  insert into public.archivo_importado (empresa_id, fuente, nombre, hash, desde, hasta, subido_por)
  values (v_empresa, p ->> 'fuente', p ->> 'nombre', p ->> 'hash', (p ->> 'desde')::date, (p ->> 'hasta')::date,
          auth.uid())
  returning id into v_archivo;

  for j in select * from jsonb_array_elements(coalesce(p -> 'jornadas', '[]'::jsonb))
  loop
    insert into public.jornada (empresa_id, punto_id, fecha)
    values (v_empresa, (j ->> 'punto_id')::uuid, (j ->> 'fecha')::date)
    on conflict (empresa_id, punto_id, fecha) do nothing;
    select id into v_jornada from public.jornada
    where empresa_id = v_empresa and punto_id = (j ->> 'punto_id')::uuid and fecha = (j ->> 'fecha')::date;

    if j ? 'reporte' and jsonb_typeof(j -> 'reporte') = 'object' then
      insert into public.reporte_caja (empresa_id, jornada_id, archivo_id, hoja, fila_origen, efectivo_contado,
                                       venta_teorica, descuadre, asesoras_texto)
      select v_empresa, v_jornada, v_archivo, r.hoja, r.fila_origen, r.efectivo_contado, r.venta_teorica,
             r.descuadre, r.asesoras_texto
      from jsonb_to_record(j -> 'reporte') as r(hoja text, fila_origen int, efectivo_contado bigint,
                                                venta_teorica bigint, descuadre bigint, asesoras_texto text);
      v_filas := v_filas + 1;
    end if;

    insert into public.pago (empresa_id, jornada_id, medio_pago_id, detalle_medio, monto, archivo_id, fila_origen)
    select v_empresa, v_jornada, x.medio_pago_id, x.detalle_medio, x.monto, v_archivo, x.fila_origen
    from jsonb_to_recordset(coalesce(j -> 'pagos', '[]'::jsonb))
         as x(medio_pago_id uuid, detalle_medio text, monto bigint, fila_origen int);
    v_filas := v_filas + jsonb_array_length(coalesce(j -> 'pagos', '[]'::jsonb));

    insert into public.turno (empresa_id, jornada_id, asesora_id, texto_original, archivo_id, fila_origen)
    select v_empresa, v_jornada, x.asesora_id, x.texto_original, v_archivo, x.fila_origen
    from jsonb_to_recordset(coalesce(j -> 'turnos', '[]'::jsonb))
         as x(asesora_id uuid, texto_original text, fila_origen int);

    if j ? 'venta' and jsonb_typeof(j -> 'venta') = 'object' then
      insert into public.venta (empresa_id, jornada_id, total, es_total_dia, archivo_id, fila_origen)
      values (v_empresa, v_jornada, (j -> 'venta' ->> 'total')::bigint, true, v_archivo,
              (j -> 'venta' ->> 'fila_origen')::int)
      returning id into v_venta;
      insert into public.venta_detalle (empresa_id, venta_id, producto_id, texto_producto, cantidad, precio_lista,
                                        valor, descuento, regalos, archivo_id, fila_origen)
      select v_empresa, v_venta, x.producto_id, x.texto_producto, coalesce(x.cantidad, 0), coalesce(x.precio_lista, 0),
             coalesce(x.valor, 0), coalesce(x.descuento, 0), coalesce(x.regalos, 0), v_archivo, x.fila_origen
      from jsonb_to_recordset(coalesce(j -> 'venta' -> 'detalle', '[]'::jsonb))
           as x(producto_id uuid, texto_producto text, cantidad int, precio_lista bigint, valor bigint,
                descuento bigint, regalos int, fila_origen int);
      v_filas := v_filas + jsonb_array_length(coalesce(j -> 'venta' -> 'detalle', '[]'::jsonb));
    end if;
  end loop;

  insert into public.movimiento_externo (empresa_id, archivo_id, fila_origen, fuente, tipo, fecha, hora, fecha_canje,
                                         punto_id, terminal_id, referencia, descripcion, etiqueta, franquicia,
                                         tipo_tarjeta, bruto, comision, retenciones, prestamo, neto)
  select v_empresa, v_archivo, x.fila_origen, x.fuente, x.tipo, x.fecha, x.hora, x.fecha_canje, x.punto_id,
         x.terminal_id, x.referencia, x.descripcion, x.etiqueta, x.franquicia, x.tipo_tarjeta, x.bruto,
         coalesce(x.comision, 0), coalesce(x.retenciones, 0), coalesce(x.prestamo, 0),
         x.bruto - coalesce(x.comision, 0) - coalesce(x.retenciones, 0) - coalesce(x.prestamo, 0)
  from jsonb_to_recordset(coalesce(p -> 'movimientos', '[]'::jsonb))
       as x(fila_origen int, fuente text, tipo text, fecha date, hora time, fecha_canje date, punto_id uuid,
            terminal_id uuid, referencia text, descripcion text, etiqueta text, franquicia text, tipo_tarjeta text,
            bruto bigint, comision bigint, retenciones bigint, prestamo bigint);
  v_filas := v_filas + jsonb_array_length(coalesce(p -> 'movimientos', '[]'::jsonb));

  insert into public.error_importacion (empresa_id, archivo_id, fila_origen, tipo, texto)
  select v_empresa, v_archivo, x.fila_origen, x.tipo, x.texto
  from jsonb_to_recordset(coalesce(p -> 'errores', '[]'::jsonb)) as x(fila_origen int, tipo text, texto text);

  update public.archivo_importado set filas = v_filas where id = v_archivo;
  return v_archivo;
end;
$$;

-- =============================================================================
-- Fin de 0008.
-- =============================================================================
