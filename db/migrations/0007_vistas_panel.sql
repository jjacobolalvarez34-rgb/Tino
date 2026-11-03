-- =============================================================================
-- 0007_vistas_panel.sql
-- Lo que leen y escriben las pantallas: vistas con solo lo que cuenta, y funciones
-- para cargar un archivo entero y para guardar lo que calculó la revisión.
--
-- Paso 4.1 del plan. Ver docs/MODELO_DATOS.md.
--
-- Reglas que esta migración implementa:
--   * Las vistas corren con los permisos de quien consulta (security_invoker): RLS
--     sigue mandando, igual que en las tablas.
--   * Lo de un archivo deshecho deja de contar en todas las vistas (D-005).
--   * Un archivo entra entero o no entra: la función lo carga en una sola
--     transacción. Si algo falla, no queda medio archivo.
--   * Las funciones también corren con los permisos de quien llama (security
--     invoker): no se saltan ninguna regla.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Vistas de lo vigente
-- -----------------------------------------------------------------------------

-- El reporte de caja que cuenta: el del último archivo cargado de cada jornada.
create view public.v_reporte_vigente with (security_invoker = true) as
select distinct on (r.jornada_id)
       r.id, r.empresa_id, r.jornada_id, r.archivo_id, r.hoja, r.fila_origen, r.efectivo_contado,
       r.venta_teorica, r.descuadre, r.asesoras_texto, a.creado_en as cargado_en
from public.reporte_caja r
join public.archivo_importado a on a.id = r.archivo_id and a.estado = 'cargado'
order by r.jornada_id, a.creado_en desc, r.creado_en desc;

-- Pagos que cuentan: no anulados y de un archivo cargado, o escritos a mano.
create view public.v_pago_vigente with (security_invoker = true) as
select p.id, p.empresa_id, p.jornada_id, j.punto_id, j.fecha, p.medio_pago_id, m.codigo as medio_codigo,
       m.tipo as medio_tipo, p.detalle_medio, p.monto, p.referencia, p.archivo_id, p.fila_origen
from public.pago p
join public.jornada j on j.id = p.jornada_id
join public.medio_pago m on m.id = p.medio_pago_id
left join public.archivo_importado a on a.id = p.archivo_id
where not p.anulado and (p.archivo_id is null or a.estado = 'cargado');

-- Lo que llegó y cuenta: de un archivo cargado.
create view public.v_movimiento_vigente with (security_invoker = true) as
select m.*
from public.movimiento_externo m
join public.archivo_importado a on a.id = m.archivo_id and a.estado = 'cargado';

-- Productos vendidos que cuentan, con la jornada, para la pista de precios.
create view public.v_detalle_vigente with (security_invoker = true) as
select d.id, d.empresa_id, v.jornada_id, j.punto_id, j.fecha, d.producto_id, d.texto_producto, d.cantidad,
       d.precio_lista, d.valor, d.descuento, d.regalos, d.archivo_id, d.fila_origen
from public.venta_detalle d
join public.venta v on v.id = d.venta_id and not v.anulada
join public.jornada j on j.id = v.jornada_id
left join public.archivo_importado a on a.id = d.archivo_id
where d.archivo_id is null or a.estado = 'cargado';

-- Un día de un punto, con lo que reportó y cómo quedó su descuadre.
create view public.v_jornada with (security_invoker = true) as
select j.id, j.empresa_id, j.punto_id, p.codigo as punto_codigo, p.nombre as punto_nombre, j.fecha, j.estado,
       r.id as reporte_id, r.venta_teorica, r.efectivo_contado, r.descuadre as descuadre_reportado, r.asesoras_texto,
       d.id as descuadre_id, d.monto as descuadre, d.explicado, d.sin_explicar, d.estado_motor,
       d.causa_codigo, d.estado as descuadre_estado, d.nota as descuadre_nota
from public.jornada j
join public.punto_venta p on p.id = j.punto_id
left join public.v_reporte_vigente r on r.jornada_id = j.id
left join public.descuadre d on d.jornada_id = j.id;

-- Cada transferencia anotada con su verificación.
create view public.v_transferencia with (security_invoker = true) as
select p.id as pago_id, p.empresa_id, p.jornada_id, p.punto_id, p.fecha, p.monto, p.fila_origen,
       coalesce(v.estado, 'pendiente') as estado, v.extracto_id, m.fecha as fecha_banco, m.referencia,
       v.nota, v.decidido_en
from public.v_pago_vigente p
left join public.verificacion_transferencia v on v.pago_id = p.id
left join public.movimiento_externo m on m.id = v.extracto_id
where p.medio_tipo = 'transferencia';

-- Cada cruce, con lo anotado y lo que llegó, para confirmar o rechazar.
create view public.v_cruce with (security_invoker = true) as
select c.id, c.empresa_id, c.tipo, c.estado, c.nota, c.decidido_en, c.creado_en,
       p.id as pago_id, p.punto_id, p.fecha as fecha_anotada, p.monto as monto_anotado, p.medio_tipo, p.fila_origen,
       m.id as movimiento_id, m.fuente, m.fecha as fecha_externa, m.bruto as monto_externo, m.referencia
from public.conciliacion c
join public.v_pago_vigente p on p.id = c.pago_id
join public.v_movimiento_vigente m on m.id = c.movimiento_id;


-- -----------------------------------------------------------------------------
-- 2. Cargar un archivo entero
--
-- Recibe lo que ya leyó el lector, con los ids de punto, medio, producto y
-- asesora resueltos. Lo que no se pudo resolver llega en "errores". Devuelve el id
-- del archivo. Si el mismo archivo ya está cargado, falla con 23505.
-- -----------------------------------------------------------------------------

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
                                         punto_id, terminal_id, referencia, descripcion, franquicia, tipo_tarjeta,
                                         bruto, comision, retenciones, prestamo, neto)
  select v_empresa, v_archivo, x.fila_origen, x.fuente, x.tipo, x.fecha, x.hora, x.fecha_canje, x.punto_id,
         x.terminal_id, x.referencia, x.descripcion, x.franquicia, x.tipo_tarjeta, x.bruto,
         coalesce(x.comision, 0), coalesce(x.retenciones, 0), coalesce(x.prestamo, 0),
         x.bruto - coalesce(x.comision, 0) - coalesce(x.retenciones, 0) - coalesce(x.prestamo, 0)
  from jsonb_to_recordset(coalesce(p -> 'movimientos', '[]'::jsonb))
       as x(fila_origen int, fuente text, tipo text, fecha date, hora time, fecha_canje date, punto_id uuid,
            terminal_id uuid, referencia text, descripcion text, franquicia text, tipo_tarjeta text, bruto bigint,
            comision bigint, retenciones bigint, prestamo bigint);
  v_filas := v_filas + jsonb_array_length(coalesce(p -> 'movimientos', '[]'::jsonb));

  insert into public.error_importacion (empresa_id, archivo_id, fila_origen, tipo, texto)
  select v_empresa, v_archivo, x.fila_origen, x.tipo, x.texto
  from jsonb_to_recordset(coalesce(p -> 'errores', '[]'::jsonb)) as x(fila_origen int, tipo text, texto text);

  update public.archivo_importado set filas = v_filas where id = v_archivo;
  return v_archivo;
end;
$$;

-- Deshacer un archivo: deja de contar, no se borra. La base pone quién y cuándo.
-- Lo que se decidió con sus filas también deja de contar, con nota y en el historial:
-- sus cruces se rechazan, las transferencias que confirmaba una línea suya vuelven a
-- pendiente, las de sus pagos se rechazan y sus errores pendientes se dan por resueltos.
-- Si no, una línea del banco seguiría "ocupada" por un pago que ya no cuenta.
create or replace function public.deshacer_archivo(p_archivo uuid)
returns void
language plpgsql security invoker set search_path = ''
as $$
declare
  v_nota text;
begin
  update public.archivo_importado
  set estado = 'deshecho', deshecho_en = pg_catalog.now(), deshecho_por = auth.uid()
  where id = p_archivo and estado = 'cargado'
  returning 'Se deshizo el archivo ' || nombre into v_nota;
  if not found then
    raise exception 'El archivo no existe o ya estaba deshecho' using errcode = 'P0002';
  end if;

  update public.conciliacion c set estado = 'rechazada', nota = v_nota
  where c.estado <> 'rechazada'
    and (c.pago_id in (select id from public.pago where archivo_id = p_archivo)
         or c.movimiento_id in (select id from public.movimiento_externo where archivo_id = p_archivo));

  update public.verificacion_transferencia v set estado = 'rechazada', nota = v_nota
  where v.estado <> 'rechazada' and v.pago_id in (select id from public.pago where archivo_id = p_archivo);

  update public.verificacion_transferencia v set estado = 'pendiente', extracto_id = null, nota = v_nota
  where v.estado <> 'rechazada'
    and v.extracto_id in (select id from public.movimiento_externo where archivo_id = p_archivo);

  update public.error_importacion set resuelto = true, resuelto_en = pg_catalog.now(), resuelto_por = auth.uid(),
                                      nota = v_nota
  where archivo_id = p_archivo and not resuelto;
end;
$$;


-- -----------------------------------------------------------------------------
-- 3. Guardar lo que calculó la revisión
--
-- descuadres: uno por jornada. Si ya existía, se recalcula: lo calculado cambia,
--   las pruebas viejas dejan de estar vigentes y lo que decidió una persona se
--   respeta. Si el día ahora cuadra y seguía abierto, pasa a resuelto con la nota
--   "Se resolvió con datos nuevos".
-- cruces: lo anotado y lo que llegó. Una pareja viva no se repite; lo que ya está
--   confirmado no se toca.
-- verificaciones: una por transferencia. Lo que confirmó o rechazó una persona no se
--   toca; una abierta que ahora aparece en el extracto pasa a confirmada con nota.
-- -----------------------------------------------------------------------------

create or replace function public.guardar_revision(p jsonb)
returns void
language plpgsql security invoker set search_path = ''
as $$
declare
  v_empresa  uuid := app.empresa_actual();
  d          jsonb;
  v_id       uuid;
  v_antes    record;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;

  for d in select * from jsonb_array_elements(coalesce(p -> 'descuadres', '[]'::jsonb))
  loop
    select id, estado, estado_motor into v_antes from public.descuadre
    where empresa_id = v_empresa and jornada_id = (d ->> 'jornada_id')::uuid;

    if v_antes.id is null then
      insert into public.descuadre (empresa_id, jornada_id, reporte_id, monto, explicado, sin_explicar, estado_motor,
                                    causa_codigo)
      values (v_empresa, (d ->> 'jornada_id')::uuid, (d ->> 'reporte_id')::uuid, (d ->> 'monto')::bigint,
              (d ->> 'explicado')::bigint, (d ->> 'sin_explicar')::bigint, d ->> 'estado_motor', d ->> 'causa_codigo')
      returning id into v_id;
    else
      v_id := v_antes.id;
      update public.descuadre
      set reporte_id = (d ->> 'reporte_id')::uuid, monto = (d ->> 'monto')::bigint,
          explicado = (d ->> 'explicado')::bigint, sin_explicar = (d ->> 'sin_explicar')::bigint,
          estado_motor = d ->> 'estado_motor', causa_codigo = d ->> 'causa_codigo', calculado_en = pg_catalog.now()
      where id = v_id;
      if v_antes.estado = 'abierto' and v_antes.estado_motor <> 'cuadra' and d ->> 'estado_motor' = 'cuadra' then
        update public.descuadre set estado = 'resuelto', nota = 'Se resolvió con datos nuevos' where id = v_id;
      end if;
      update public.descuadre_evidencia set vigente = false where descuadre_id = v_id and vigente;
    end if;

    insert into public.descuadre_evidencia (empresa_id, descuadre_id, causa_codigo, tipo, monto, total, pago_id,
                                            movimiento_id, detalle)
    select v_empresa, v_id, x.causa_codigo, x.tipo, coalesce(x.monto, 0), coalesce(x.total, 0), x.pago_id,
           x.movimiento_id, coalesce(x.detalle, '{}'::jsonb)
    from jsonb_to_recordset(coalesce(d -> 'evidencias', '[]'::jsonb))
         as x(causa_codigo text, tipo text, monto bigint, total bigint, pago_id uuid, movimiento_id uuid, detalle jsonb);
  end loop;

  -- Cruces: el que choca con una pareja viva o con algo ya confirmado se salta.
  insert into public.conciliacion (empresa_id, pago_id, movimiento_id, tipo, estado)
  select v_empresa, x.pago_id, x.movimiento_id, x.tipo,
         case when x.tipo = 'mismo_dia' then 'confirmada' else 'propuesta' end
  from jsonb_to_recordset(coalesce(p -> 'cruces', '[]'::jsonb)) as x(pago_id uuid, movimiento_id uuid, tipo text)
  on conflict do nothing;

  -- Verificaciones nuevas.
  insert into public.verificacion_transferencia (empresa_id, pago_id, estado, extracto_id)
  select v_empresa, x.pago_id, x.estado, x.extracto_id
  from jsonb_to_recordset(coalesce(p -> 'verificaciones', '[]'::jsonb)) as x(pago_id uuid, estado text, extracto_id uuid)
  on conflict do nothing;

  -- Las que ya existían y siguen abiertas avanzan solo hacia confirmada, con el extracto.
  -- Lo que una persona confirmó o rechazó no se toca.
  update public.verificacion_transferencia v
  set estado = 'confirmada', extracto_id = x.extracto_id,
      nota = case when v.estado = 'sospechosa' then 'Confirmada por extracto después de sospecha'
                  else 'Confirmada por extracto' end
  from jsonb_to_recordset(coalesce(p -> 'verificaciones', '[]'::jsonb)) as x(pago_id uuid, estado text, extracto_id uuid)
  where v.empresa_id = v_empresa and v.pago_id = x.pago_id
    and x.estado = 'confirmada' and v.estado in ('pendiente', 'sospechosa', 'propuesta')
    and not exists (select 1 from public.verificacion_transferencia o
                    where o.empresa_id = v_empresa and o.extracto_id = x.extracto_id and o.estado = 'confirmada');
end;
$$;

revoke execute on function public.importar_archivo(jsonb), public.deshacer_archivo(uuid),
                           public.guardar_revision(jsonb) from public, anon;
grant execute on function public.importar_archivo(jsonb), public.deshacer_archivo(uuid),
                          public.guardar_revision(jsonb) to authenticated;

-- =============================================================================
-- Fin de 0007. Siguiente: costos, inventario y personal, en fases posteriores.
-- =============================================================================
