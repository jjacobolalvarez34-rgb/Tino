-- =============================================================================
-- 0004_operacion_diaria.sql
-- Lo que pasó cada día en cada punto: la jornada, quién trabajó, lo vendido, cómo
-- se pagó, la caja que reportó el punto, sus gastos y consignaciones, notas y metas.
--
-- Paso 2.2 del plan. Ver docs/MODELO_DATOS.md.
--
-- Reglas que esta migración implementa:
--   * Toda fila importada guarda archivo_id y fila_origen.
--   * Lo de un archivo deshecho no se borra: deja de contar, porque las vistas solo
--     leen lo que viene de archivos en estado 'cargado' (D-005).
--   * Lo que reporta el punto de su caja se guarda por archivo (reporte_caja): si el
--     Excel se corrige y se vuelve a subir, cuenta el último cargado y el anterior
--     queda en el historial.
--   * Ver: dueño, encargada, finanzas y soporte, todo lo de su empresa; la asesora,
--     solo su punto. Escribir: quien sube archivos (dueño, encargada, finanzas y
--     soporte). Cerrar o desbloquear un día: dueño, encargada o soporte.
-- =============================================================================

-- El punto fijo de quien consulta. Lo usan las políticas de la asesora.
create or replace function app.punto_actual()
returns uuid
language sql stable security definer set search_path = ''
as $$
  select u.punto_id
  from public.usuario u
  where u.id = auth.uid() and u.activo
$$;


-- -----------------------------------------------------------------------------
-- 1. Jornada: un día de un punto
-- -----------------------------------------------------------------------------

create table public.jornada (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  punto_id    uuid not null,
  fecha       date not null,
  estado      text not null default 'abierta'
                check (estado in ('abierta', 'cerrada', 'conciliada', 'bloqueada')),
  creado_en   timestamptz not null default now(),
  unique (empresa_id, punto_id, fecha),
  unique (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id)
);


-- -----------------------------------------------------------------------------
-- 2. Lo que el punto reportó de su caja
-- Una fila por archivo: cuenta la del último archivo cargado de esa jornada.
-- fila_origen es la fila de la celda del descuadre en la hoja del día.
-- -----------------------------------------------------------------------------

create table public.reporte_caja (
  id                uuid primary key default gen_random_uuid(),
  empresa_id        uuid not null references public.empresa (id),
  jornada_id        uuid not null,
  archivo_id        uuid not null,
  hoja              text,
  fila_origen       int not null check (fila_origen > 0),
  efectivo_contado  bigint,
  venta_teorica     bigint,
  descuadre         bigint,
  asesoras_texto    text,
  creado_en         timestamptz not null default now(),
  unique (empresa_id, jornada_id, archivo_id),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id)
);


-- -----------------------------------------------------------------------------
-- 3. Quién trabajó: el nombre tal como venía y, si se reconoce, la asesora.
-- Un nombre que nadie puede resolver queda sin asesora (D-032).
-- -----------------------------------------------------------------------------

create table public.turno (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  jornada_id      uuid not null,
  asesora_id      uuid,
  texto_original  text not null,
  archivo_id      uuid,
  fila_origen     int check (fila_origen > 0),
  creado_en       timestamptz not null default now(),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  -- Lo importado dice de qué fila salió.
  check ((archivo_id is null) = (fila_origen is null))
);


-- -----------------------------------------------------------------------------
-- 4. Ventas y su detalle (D-013)
-- Cada venta, o el total del día o de la asesora si el reporte no trae detalle.
-- -----------------------------------------------------------------------------

create table public.venta (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  jornada_id      uuid not null,
  asesora_id      uuid,
  tipo_venta_id   uuid,
  numero_factura  text,
  total           bigint not null,
  descuento       bigint not null default 0 check (descuento >= 0),
  es_total_dia    boolean not null default false,
  anulada         boolean not null default false,
  nota            text,
  archivo_id      uuid,
  fila_origen     int check (fila_origen > 0),
  creado_en       timestamptz not null default now(),
  unique (empresa_id, id),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, tipo_venta_id) references public.tipo_venta (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check ((archivo_id is null) = (fila_origen is null))
);

-- Precio de lista y lo cobrado, para medir descuentos. El producto puede quedar sin
-- reconocer: se guarda el texto y se resuelve después (error_importacion).
create table public.venta_detalle (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  venta_id        uuid not null,
  producto_id     uuid,
  texto_producto  text not null,
  cantidad        int not null default 0,
  precio_lista    bigint not null default 0 check (precio_lista >= 0),
  valor           bigint not null default 0,
  descuento       bigint not null default 0 check (descuento >= 0),
  regalos         int not null default 0 check (regalos >= 0),
  archivo_id      uuid,
  fila_origen     int check (fila_origen > 0),
  creado_en       timestamptz not null default now(),
  foreign key (empresa_id, venta_id) references public.venta (empresa_id, id),
  foreign key (empresa_id, producto_id) references public.producto (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check ((archivo_id is null) = (fila_origen is null))
);


-- -----------------------------------------------------------------------------
-- 5. Pagos: cómo se pagó, uno por uno o agregado del día por medio de pago.
-- Cada transferencia o cobro con tarjeta anotado en el Excel es una fila.
-- -----------------------------------------------------------------------------

create table public.pago (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  jornada_id     uuid not null,
  venta_id       uuid,
  medio_pago_id  uuid not null,
  -- Lo que dice el reporte del medio: 'debito', 'credito'. El medio dice el tipo.
  detalle_medio  text,
  monto          bigint not null check (monto <> 0),
  referencia     text,
  anulado        boolean not null default false,
  nota           text,
  archivo_id     uuid,
  fila_origen    int check (fila_origen > 0),
  creado_en      timestamptz not null default now(),
  unique (empresa_id, id),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, venta_id) references public.venta (empresa_id, id),
  foreign key (empresa_id, medio_pago_id) references public.medio_pago (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check ((archivo_id is null) = (fila_origen is null))
);


-- -----------------------------------------------------------------------------
-- 6. Caja del punto: gastos, consignaciones, retiros y base.
-- -----------------------------------------------------------------------------

create table public.movimiento_caja (
  id           uuid primary key default gen_random_uuid(),
  empresa_id   uuid not null references public.empresa (id),
  jornada_id   uuid not null,
  tipo         text not null check (tipo in ('gasto', 'consignacion', 'retiro', 'base', 'otro')),
  concepto     text,
  monto        bigint not null,
  anulado      boolean not null default false,
  nota         text,
  archivo_id   uuid,
  fila_origen  int check (fila_origen > 0),
  creado_en    timestamptz not null default now(),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check ((archivo_id is null) = (fila_origen is null))
);


-- -----------------------------------------------------------------------------
-- 7. Notas del día y metas
-- -----------------------------------------------------------------------------

create table public.observacion (
  id           uuid primary key default gen_random_uuid(),
  empresa_id   uuid not null references public.empresa (id),
  jornada_id   uuid not null,
  texto        text not null,
  autor_id     uuid references public.usuario (id),
  archivo_id   uuid,
  fila_origen  int check (fila_origen > 0),
  creado_en    timestamptz not null default now(),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check ((archivo_id is null) = (fila_origen is null))
);

-- Meta de venta de un día, por punto o por asesora del punto.
create table public.meta (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  punto_id    uuid not null,
  asesora_id  uuid,
  fecha       date not null,
  monto       bigint not null check (monto >= 0),
  activo      boolean not null default true,
  creado_en   timestamptz not null default now(),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id)
);
-- Una sola meta activa por punto, asesora y día.
create unique index meta_activa_unica
  on public.meta (empresa_id, punto_id,
                  coalesce(asesora_id, '00000000-0000-0000-0000-000000000000'::uuid), fecha)
  where activo;


-- -----------------------------------------------------------------------------
-- 8. Índices
-- -----------------------------------------------------------------------------

create index jornada_empresa_fecha_idx      on public.jornada (empresa_id, fecha);
create index reporte_caja_jornada_idx       on public.reporte_caja (jornada_id);
create index reporte_caja_archivo_idx       on public.reporte_caja (archivo_id);
create index turno_jornada_idx              on public.turno (jornada_id);
create index turno_empresa_idx              on public.turno (empresa_id);
create index venta_jornada_idx              on public.venta (jornada_id);
create index venta_empresa_idx              on public.venta (empresa_id);
create index venta_archivo_idx              on public.venta (archivo_id);
create index venta_detalle_venta_idx        on public.venta_detalle (venta_id);
create index venta_detalle_empresa_idx      on public.venta_detalle (empresa_id);
create index pago_jornada_idx               on public.pago (jornada_id);
create index pago_empresa_idx               on public.pago (empresa_id);
create index pago_archivo_idx               on public.pago (archivo_id);
create index movimiento_caja_jornada_idx    on public.movimiento_caja (jornada_id);
create index movimiento_caja_empresa_idx    on public.movimiento_caja (empresa_id);
create index observacion_jornada_idx        on public.observacion (jornada_id);
create index observacion_empresa_idx        on public.observacion (empresa_id);
create index meta_empresa_idx               on public.meta (empresa_id, fecha);


-- -----------------------------------------------------------------------------
-- 9. Seguridad por filas
-- -----------------------------------------------------------------------------

-- ¿Puede quien consulta ver esta jornada? La asesora, solo las de su punto.
create or replace function app.ve_jornada(p_jornada uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.jornada j
    where j.id = p_jornada
      and j.empresa_id = app.empresa_actual()
      and (app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte'])
           or (app.rol_actual() = 'asesora' and j.punto_id = app.punto_actual()))
  )
$$;

alter table public.jornada enable row level security;

create policy jornada_ver on public.jornada
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and (app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte'])
              or (app.rol_actual() = 'asesora' and punto_id = app.punto_actual())));

create policy jornada_crear on public.jornada
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));

-- Cerrar, bloquear o desbloquear un día: dueño, encargada o soporte. Solo el estado.
create policy jornada_cambiar on public.jornada
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte']))
  with check (empresa_id = app.empresa_actual());

revoke update on public.jornada from anon, authenticated;
grant update (estado) on public.jornada to authenticated;

-- Las tablas que cuelgan de una jornada: se ven si se ve la jornada; las escribe
-- quien sube archivos. El bloque las crea en un ciclo, igual que en 0001.
do $$
declare
  t text;
begin
  foreach t in array array['reporte_caja', 'turno', 'venta', 'pago', 'movimiento_caja', 'observacion']
  loop
    execute format('alter table public.%I enable row level security', t);

    execute format($p$
      create policy %1$s_ver on public.%1$I
        for select to authenticated
        using (empresa_id = app.empresa_actual() and app.ve_jornada(jornada_id))
    $p$, t);

    execute format($p$
      create policy %1$s_crear on public.%1$I
        for insert to authenticated
        with check (empresa_id = app.empresa_actual()
                    and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
    $p$, t);

    execute format($p$
      create policy %1$s_cambiar on public.%1$I
        for update to authenticated
        using (empresa_id = app.empresa_actual()
               and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
        with check (empresa_id = app.empresa_actual())
    $p$, t);
  end loop;
end $$;

-- venta_detalle cuelga de una venta: se ve si se ve su venta.
alter table public.venta_detalle enable row level security;

create policy venta_detalle_ver on public.venta_detalle
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and exists (select 1 from public.venta v where v.id = venta_id));

create policy venta_detalle_crear on public.venta_detalle
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));

create policy venta_detalle_cambiar on public.venta_detalle
  for update to authenticated
  using (empresa_id = app.empresa_actual()
         and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
  with check (empresa_id = app.empresa_actual());

-- meta: todos los de la empresa la ven (la asesora, solo las de su punto); la ponen
-- dueño, encargada o soporte, como los maestros.
alter table public.meta enable row level security;

create policy meta_ver on public.meta
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and (app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte'])
              or (app.rol_actual() = 'asesora' and punto_id = app.punto_actual())));

create policy meta_crear on public.meta
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte']));

create policy meta_cambiar on public.meta
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte']))
  with check (empresa_id = app.empresa_actual());

-- Lo importado no se reescribe: solo se anula o se le pone nota. Lo que cambie la
-- plata entra como fila nueva o con un archivo nuevo.
revoke update on public.reporte_caja, public.turno, public.venta, public.venta_detalle,
                 public.pago, public.movimiento_caja, public.observacion, public.meta
  from anon, authenticated;
grant update (asesora_id)       on public.turno           to authenticated;
grant update (anulada, nota)    on public.venta           to authenticated;
grant update (producto_id)      on public.venta_detalle   to authenticated;
grant update (anulado, nota)    on public.pago            to authenticated;
grant update (anulado, nota)    on public.movimiento_caja to authenticated;
grant update (activo)           on public.meta            to authenticated;


-- -----------------------------------------------------------------------------
-- 10. Auditoría y sin TRUNCATE
-- -----------------------------------------------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array['jornada', 'reporte_caja', 'turno', 'venta', 'venta_detalle', 'pago',
                           'movimiento_caja', 'observacion', 'meta']
  loop
    execute format(
      'create trigger %1$s_auditoria
         after insert or update or delete on public.%1$I
         for each row execute function app.registrar_auditoria()', t);
  end loop;
end $$;

revoke truncate on public.jornada, public.reporte_caja, public.turno, public.venta, public.venta_detalle,
                   public.pago, public.movimiento_caja, public.observacion, public.meta
  from anon, authenticated;

-- =============================================================================
-- Fin de 0004. Siguiente: 0005_bancos_conciliacion.sql
-- =============================================================================
