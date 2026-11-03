-- =============================================================================
-- 0005_bancos_conciliacion.sql
-- Lo que de verdad llegó (extracto, Bold, Redeban y, después, avisos), el cruce
-- entre lo anotado y lo que llegó, la verificación de cada transferencia y los
-- festivos con que se calcula el día de consignación.
--
-- Pasos 3.1 y 3.2 del plan. Ver docs/MODELO_DATOS.md y docs/REGLAS/.
--
-- Reglas que esta migración implementa:
--   * Una propuesta nunca se confirma sola (D-006). El motor solo deja confirmado lo
--     que coincide el mismo día; lo demás queda propuesto hasta que una persona decida.
--   * Decidir a mano exige una nota y queda con quién y cuándo, puesto por la base.
--   * Una misma línea del banco no confirma dos pagos.
--   * Nada pasa a confirmada sin el extracto.
--   * Un cruce no se borra: se rechaza y queda en el historial.
-- =============================================================================

-- Las tablas nuevas apuntan a estos maestros con la empresa, como las demás.
alter table public.terminal_datafono
  add constraint terminal_datafono_empresa_id_id_key unique (empresa_id, id);
alter table public.cuenta_recaudo
  add constraint cuenta_recaudo_empresa_id_id_key unique (empresa_id, id);


-- -----------------------------------------------------------------------------
-- 1. Festivos (⚑ C4)
-- Los de Colombia (ley 51 de 1983): fijos, los que pasan al lunes y los que dependen
-- de la Pascua. No son de una empresa: todos los leen y nadie los escribe desde la
-- aplicación. Un año nuevo se agrega con otra migración.
-- -----------------------------------------------------------------------------

create table public.festivo (
  fecha   date primary key,
  nombre  text not null,
  pais    text not null default 'CO'
);

insert into public.festivo (fecha, nombre) values
  ('2024-01-01', 'Año Nuevo'),
  ('2024-01-08', 'Reyes Magos'),
  ('2024-03-25', 'San José'),
  ('2024-03-28', 'Jueves Santo'),
  ('2024-03-29', 'Viernes Santo'),
  ('2024-05-01', 'Día del Trabajo'),
  ('2024-05-13', 'Ascensión del Señor'),
  ('2024-06-03', 'Corpus Christi'),
  ('2024-06-10', 'Sagrado Corazón'),
  ('2024-07-01', 'San Pedro y San Pablo'),
  ('2024-07-20', 'Independencia'),
  ('2024-08-07', 'Batalla de Boyacá'),
  ('2024-08-19', 'Asunción de la Virgen'),
  ('2024-10-14', 'Día de la Raza'),
  ('2024-11-04', 'Todos los Santos'),
  ('2024-11-11', 'Independencia de Cartagena'),
  ('2024-12-08', 'Inmaculada Concepción'),
  ('2024-12-25', 'Navidad'),
  ('2025-01-01', 'Año Nuevo'),
  ('2025-01-06', 'Reyes Magos'),
  ('2025-03-24', 'San José'),
  ('2025-04-17', 'Jueves Santo'),
  ('2025-04-18', 'Viernes Santo'),
  ('2025-05-01', 'Día del Trabajo'),
  ('2025-06-02', 'Ascensión del Señor'),
  ('2025-06-23', 'Corpus Christi'),
  ('2025-06-30', 'Sagrado Corazón y San Pedro y San Pablo'),
  ('2025-07-20', 'Independencia'),
  ('2025-08-07', 'Batalla de Boyacá'),
  ('2025-08-18', 'Asunción de la Virgen'),
  ('2025-10-13', 'Día de la Raza'),
  ('2025-11-03', 'Todos los Santos'),
  ('2025-11-17', 'Independencia de Cartagena'),
  ('2025-12-08', 'Inmaculada Concepción'),
  ('2025-12-25', 'Navidad'),
  ('2026-01-01', 'Año Nuevo'),
  ('2026-01-12', 'Reyes Magos'),
  ('2026-03-23', 'San José'),
  ('2026-04-02', 'Jueves Santo'),
  ('2026-04-03', 'Viernes Santo'),
  ('2026-05-01', 'Día del Trabajo'),
  ('2026-05-18', 'Ascensión del Señor'),
  ('2026-06-08', 'Corpus Christi'),
  ('2026-06-15', 'Sagrado Corazón'),
  ('2026-06-29', 'San Pedro y San Pablo'),
  ('2026-07-20', 'Independencia'),
  ('2026-08-07', 'Batalla de Boyacá'),
  ('2026-08-17', 'Asunción de la Virgen'),
  ('2026-10-12', 'Día de la Raza'),
  ('2026-11-02', 'Todos los Santos'),
  ('2026-11-16', 'Independencia de Cartagena'),
  ('2026-12-08', 'Inmaculada Concepción'),
  ('2026-12-25', 'Navidad'),
  ('2027-01-01', 'Año Nuevo'),
  ('2027-01-11', 'Reyes Magos'),
  ('2027-03-22', 'San José'),
  ('2027-03-25', 'Jueves Santo'),
  ('2027-03-26', 'Viernes Santo'),
  ('2027-05-01', 'Día del Trabajo'),
  ('2027-05-10', 'Ascensión del Señor'),
  ('2027-05-31', 'Corpus Christi'),
  ('2027-06-07', 'Sagrado Corazón'),
  ('2027-07-05', 'San Pedro y San Pablo'),
  ('2027-07-20', 'Independencia'),
  ('2027-08-07', 'Batalla de Boyacá'),
  ('2027-08-16', 'Asunción de la Virgen'),
  ('2027-10-18', 'Día de la Raza'),
  ('2027-11-01', 'Todos los Santos'),
  ('2027-11-15', 'Independencia de Cartagena'),
  ('2027-12-08', 'Inmaculada Concepción'),
  ('2027-12-25', 'Navidad'),
  ('2028-01-01', 'Año Nuevo'),
  ('2028-01-10', 'Reyes Magos'),
  ('2028-03-20', 'San José'),
  ('2028-04-13', 'Jueves Santo'),
  ('2028-04-14', 'Viernes Santo'),
  ('2028-05-01', 'Día del Trabajo'),
  ('2028-05-29', 'Ascensión del Señor'),
  ('2028-06-19', 'Corpus Christi'),
  ('2028-06-26', 'Sagrado Corazón'),
  ('2028-07-03', 'San Pedro y San Pablo'),
  ('2028-07-20', 'Independencia'),
  ('2028-08-07', 'Batalla de Boyacá'),
  ('2028-08-21', 'Asunción de la Virgen'),
  ('2028-10-16', 'Día de la Raza'),
  ('2028-11-06', 'Todos los Santos'),
  ('2028-11-13', 'Independencia de Cartagena'),
  ('2028-12-08', 'Inmaculada Concepción'),
  ('2028-12-25', 'Navidad'),
  ('2029-01-01', 'Año Nuevo'),
  ('2029-01-08', 'Reyes Magos'),
  ('2029-03-19', 'San José'),
  ('2029-03-29', 'Jueves Santo'),
  ('2029-03-30', 'Viernes Santo'),
  ('2029-05-01', 'Día del Trabajo'),
  ('2029-05-14', 'Ascensión del Señor'),
  ('2029-06-04', 'Corpus Christi'),
  ('2029-06-11', 'Sagrado Corazón'),
  ('2029-07-02', 'San Pedro y San Pablo'),
  ('2029-07-20', 'Independencia'),
  ('2029-08-07', 'Batalla de Boyacá'),
  ('2029-08-20', 'Asunción de la Virgen'),
  ('2029-10-15', 'Día de la Raza'),
  ('2029-11-05', 'Todos los Santos'),
  ('2029-11-12', 'Independencia de Cartagena'),
  ('2029-12-08', 'Inmaculada Concepción'),
  ('2029-12-25', 'Navidad'),
  ('2030-01-01', 'Año Nuevo'),
  ('2030-01-07', 'Reyes Magos'),
  ('2030-03-25', 'San José'),
  ('2030-04-18', 'Jueves Santo'),
  ('2030-04-19', 'Viernes Santo'),
  ('2030-05-01', 'Día del Trabajo'),
  ('2030-06-03', 'Ascensión del Señor'),
  ('2030-06-24', 'Corpus Christi'),
  ('2030-07-01', 'Sagrado Corazón y San Pedro y San Pablo'),
  ('2030-07-20', 'Independencia'),
  ('2030-08-07', 'Batalla de Boyacá'),
  ('2030-08-19', 'Asunción de la Virgen'),
  ('2030-10-14', 'Día de la Raza'),
  ('2030-11-04', 'Todos los Santos'),
  ('2030-11-11', 'Independencia de Cartagena'),
  ('2030-12-08', 'Inmaculada Concepción'),
  ('2030-12-25', 'Navidad');

alter table public.festivo enable row level security;

create policy festivo_ver on public.festivo
  for select to authenticated
  using (true);

-- Sin políticas de crear, cambiar ni borrar: RLS lo impide, como en las demás tablas.
revoke truncate on public.festivo from anon, authenticated;


-- -----------------------------------------------------------------------------
-- 2. Lo que de verdad llegó
-- Una fila por línea del extracto o por cobro del reporte de Bold o Redeban. En el
-- banco, bruto y neto son lo mismo. punto_id vacío: no se sabe de qué punto es
-- (un pago sin código) hasta que alguien lo asigne.
-- -----------------------------------------------------------------------------

create table public.movimiento_externo (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  archivo_id     uuid not null,
  fila_origen    int not null check (fila_origen > 0),
  fuente         text not null check (fuente in ('banco', 'bold', 'redeban', 'correo')),
  tipo           text not null
                   check (tipo in ('transferencia', 'cobro', 'reversion', 'deposito', 'otro')),
  fecha          date not null,
  hora           time,
  fecha_canje    date,
  punto_id       uuid,
  terminal_id    uuid,
  cuenta_id      uuid,
  referencia     text,
  descripcion    text,
  franquicia     text,
  tipo_tarjeta   text check (tipo_tarjeta in ('debito', 'credito')),
  bruto          bigint not null,
  comision       bigint not null default 0,
  retenciones    bigint not null default 0,
  -- Lo que el proveedor descontó por un préstamo de la empresa (D-029): no es plata perdida.
  prestamo       bigint not null default 0,
  neto           bigint not null,
  nota           text,
  creado_en      timestamptz not null default now(),
  unique (empresa_id, id),
  check (neto = bruto - comision - retenciones - prestamo),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, terminal_id) references public.terminal_datafono (empresa_id, id),
  foreign key (empresa_id, cuenta_id) references public.cuenta_recaudo (empresa_id, id)
);


-- -----------------------------------------------------------------------------
-- 3. Conciliación: un pago anotado y el movimiento que lo cubre
-- tipo dice cómo se encontró. Solo 'mismo_dia' puede nacer confirmada.
-- -----------------------------------------------------------------------------

create table public.conciliacion (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  pago_id        uuid not null,
  movimiento_id  uuid not null,
  tipo           text not null
                   check (tipo in ('mismo_dia', 'otro_dia', 'mal_digitado', 'junto_con', 'dia_tarde', 'manual')),
  estado         text not null default 'propuesta' check (estado in ('propuesta', 'confirmada', 'rechazada')),
  nota           text,
  decidido_por   uuid references public.usuario (id),
  decidido_en    timestamptz,
  creado_en      timestamptz not null default now(),
  foreign key (empresa_id, pago_id) references public.pago (empresa_id, id),
  foreign key (empresa_id, movimiento_id) references public.movimiento_externo (empresa_id, id),
  -- Confirmada sin persona solo si coincidió el mismo día.
  check (estado <> 'confirmada' or tipo = 'mismo_dia' or decidido_por is not null),
  check (estado <> 'rechazada' or decidido_por is not null)
);

-- Un pago se confirma una vez, y una línea del banco cubre un solo pago.
create unique index conciliacion_pago_confirmado
  on public.conciliacion (empresa_id, pago_id) where estado = 'confirmada';
create unique index conciliacion_movimiento_confirmado
  on public.conciliacion (empresa_id, movimiento_id) where estado = 'confirmada';
-- La misma pareja no se propone dos veces mientras siga viva.
create unique index conciliacion_pareja_viva
  on public.conciliacion (empresa_id, pago_id, movimiento_id) where estado <> 'rechazada';


-- -----------------------------------------------------------------------------
-- 4. Verificación de cada transferencia
-- Una por pago. Hoy se verifica con el extracto a la mañana siguiente; el aviso del
-- banco y el comprobante llegan en una fase posterior (T4).
-- -----------------------------------------------------------------------------

create table public.verificacion_transferencia (
  id                uuid primary key default gen_random_uuid(),
  empresa_id        uuid not null references public.empresa (id),
  pago_id           uuid not null,
  estado            text not null default 'pendiente'
                      check (estado in ('pendiente', 'confirmada', 'propuesta', 'sospechosa', 'rechazada')),
  extracto_id       uuid,
  aviso_id          uuid,
  comprobante_hash  text check (comprobante_hash ~ '^[0-9a-f]{64}$'),
  nota              text,
  decidido_por      uuid references public.usuario (id),
  decidido_en       timestamptz,
  creado_en         timestamptz not null default now(),
  unique (empresa_id, pago_id),
  foreign key (empresa_id, pago_id) references public.pago (empresa_id, id),
  foreign key (empresa_id, extracto_id) references public.movimiento_externo (empresa_id, id),
  foreign key (empresa_id, aviso_id) references public.movimiento_externo (empresa_id, id),
  -- Nada pasa a confirmada sin el extracto.
  check (estado <> 'confirmada' or extracto_id is not null),
  check (estado <> 'rechazada' or decidido_por is not null)
);

-- El mismo comprobante no sirve para dos transferencias.
create unique index verificacion_comprobante_unico
  on public.verificacion_transferencia (empresa_id, comprobante_hash) where comprobante_hash is not null;
-- Una línea del extracto no verifica dos transferencias.
create unique index verificacion_extracto_unico
  on public.verificacion_transferencia (empresa_id, extracto_id) where estado = 'confirmada';


-- -----------------------------------------------------------------------------
-- 5. Decidir: quién y cuándo los pone la base, y una decisión lleva nota
-- -----------------------------------------------------------------------------

create or replace function app.registrar_decision()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  if tg_op = 'INSERT' then
    -- Nada nace rechazado: rechazar es una decisión sobre algo que ya existía.
    if new.estado = 'rechazada' then
      raise exception 'Un cruce no nace rechazado' using errcode = '23514';
    end if;
    new.decidido_por := null;
    new.decidido_en := null;
  elsif new.estado is distinct from old.estado then
    if coalesce(btrim(new.nota), '') = '' or new.nota is not distinct from old.nota then
      raise exception 'Decidir a mano exige una nota nueva' using errcode = '23514';
    end if;
    new.decidido_por := auth.uid();
    new.decidido_en := pg_catalog.now();
  end if;
  return new;
end;
$$;

create trigger conciliacion_decision
  before insert or update on public.conciliacion
  for each row execute function app.registrar_decision();
create trigger verificacion_decision
  before insert or update on public.verificacion_transferencia
  for each row execute function app.registrar_decision();


-- -----------------------------------------------------------------------------
-- 6. Valores de las reglas (⚑ C1 a C3 y T1)
-- -----------------------------------------------------------------------------

alter table public.empresa_config
  add column conc_tolerancia_deposito  bigint not null default 50 check (conc_tolerancia_deposito >= 0),
  add column conc_dias_tarde           int    not null default 1  check (conc_dias_tarde >= 0),
  add column conc_max_cruce_redeban    int    not null default 3  check (conc_max_cruce_redeban >= 1),
  add column transf_dias_vecinos       int    not null default 1  check (transf_dias_vecinos >= 0);


-- -----------------------------------------------------------------------------
-- 7. Índices
-- -----------------------------------------------------------------------------

create index movimiento_externo_empresa_idx on public.movimiento_externo (empresa_id, fecha);
create index movimiento_externo_archivo_idx on public.movimiento_externo (archivo_id);
create index movimiento_externo_punto_idx   on public.movimiento_externo (punto_id, fecha);
create index conciliacion_empresa_idx       on public.conciliacion (empresa_id, estado);
create index conciliacion_pago_idx          on public.conciliacion (pago_id);
create index conciliacion_movimiento_idx    on public.conciliacion (movimiento_id);
create index verificacion_empresa_idx       on public.verificacion_transferencia (empresa_id, estado);


-- -----------------------------------------------------------------------------
-- 8. Seguridad por filas
-- Ver, crear y decidir: dueño, encargada, finanzas o soporte (confirmar
-- conciliaciones, según la tabla de roles). La asesora no ve el banco.
-- -----------------------------------------------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array['movimiento_externo', 'conciliacion', 'verificacion_transferencia']
  loop
    execute format('alter table public.%I enable row level security', t);

    execute format($p$
      create policy %1$s_ver on public.%1$I
        for select to authenticated
        using (empresa_id = app.empresa_actual()
               and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
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

    execute format(
      'create trigger %1$s_auditoria
         after insert or update or delete on public.%1$I
         for each row execute function app.registrar_auditoria()', t);
  end loop;
end $$;

-- Lo que llegó no se reescribe: solo se le asigna punto a un pago sin código, o una
-- nota. Un cruce solo cambia de estado, con su nota; quién y cuándo los pone la base.
revoke update on public.movimiento_externo, public.conciliacion, public.verificacion_transferencia
  from anon, authenticated;
grant update (punto_id, nota)              on public.movimiento_externo         to authenticated;
grant update (estado, nota)                on public.conciliacion               to authenticated;
grant update (estado, extracto_id, nota)   on public.verificacion_transferencia to authenticated;

revoke truncate on public.movimiento_externo, public.conciliacion, public.verificacion_transferencia
  from anon, authenticated;

-- =============================================================================
-- Fin de 0005. Siguiente: 0006_descuadres.sql
-- =============================================================================
