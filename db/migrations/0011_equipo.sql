-- =============================================================================
-- 0011_equipo.sql
-- Módulo Equipo: quién trabaja dónde, cuánto vende cada persona, sus metas, y el
-- acompañamiento (observaciones, evaluaciones, sesiones y compromisos).
--
-- Reglas que esta migración implementa (docs/REGLAS/equipo.md):
--   * Dos roles nuevos: lider (acompaña a todo el equipo) y responsable_punto (solo su
--     punto). Ven ventas como la encargada, pero el responsable solo las de su punto.
--   * Una persona puede estar en varios puntos a la vez; cada asignación tiene vigencia.
--   * La venta por persona sale del reporte del día (perfil de la empresa) y se guarda
--     aparte de venta: la venta del día ya está allí y no se puede contar dos veces.
--   * Un día con varias personas se reparte según empresa_config.equipo_reparto (⚑).
--   * Observaciones y evaluaciones son privadas: las ven dueño, encargada, lider y
--     soporte; el responsable de punto, solo las de su punto. Nadie más.
--   * Nada se borra: se anula o se cierra. Todo queda en auditoria.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Roles nuevos
-- -----------------------------------------------------------------------------

alter table public.usuario drop constraint usuario_rol_check;
alter table public.usuario add constraint usuario_rol_check
  check (rol in ('dueno', 'encargada', 'finanzas', 'asesora', 'soporte', 'lider', 'responsable_punto'));

-- ¿Puede quien consulta ver lo de este punto? Los de oficina ven todos; la asesora y el
-- responsable, solo el suyo.
create or replace function app.ve_punto(p_punto uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte', 'lider'])
      or (app.tiene_rol(array['asesora', 'responsable_punto']) and p_punto = app.punto_actual())
$$;

-- ¿Puede ver el acompañamiento (observaciones, evaluaciones, compromisos) de este punto?
-- Finanzas y la asesora no.
create or replace function app.ve_equipo(p_punto uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
      or (app.rol_actual() = 'responsable_punto' and p_punto = app.punto_actual())
$$;

-- La jornada se ve si se ve su punto: así lider y responsable leen ventas y turnos.
create or replace function app.ve_jornada(p_jornada uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select exists (
    select 1 from public.jornada j
    where j.id = p_jornada and j.empresa_id = app.empresa_actual() and app.ve_punto(j.punto_id)
  )
$$;

drop policy jornada_ver on public.jornada;
create policy jornada_ver on public.jornada
  for select to authenticated
  using (empresa_id = app.empresa_actual() and app.ve_punto(punto_id));

drop policy meta_ver on public.meta;
create policy meta_ver on public.meta
  for select to authenticated
  using (empresa_id = app.empresa_actual() and app.ve_punto(punto_id));

-- Lo que cuenta de cada venta depende de su archivo (cargado o deshecho): lider y
-- responsable ven la lista de archivos, sin poder subir ni deshacer.
create policy archivo_importado_ver_equipo on public.archivo_importado
  for select to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['lider', 'responsable_punto']));

-- El lider crea y edita personas y sus nombres por punto, como la encargada.
drop policy asesora_crear on public.asesora;
drop policy asesora_cambiar on public.asesora;
create policy asesora_crear on public.asesora
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']));
create policy asesora_cambiar on public.asesora
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());

drop policy asesora_alias_crear on public.asesora_alias;
drop policy asesora_alias_cambiar on public.asesora_alias;
create policy asesora_alias_crear on public.asesora_alias
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']));
create policy asesora_alias_cambiar on public.asesora_alias
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());

-- El código lo pone la base (0002): quien crea a una persona no lo escribe, y no se cambia: es el que identifica a la persona en todo el historial.
revoke update on public.asesora from anon, authenticated;
grant update (nombre_completo, activa, fecha_ingreso, fecha_retiro) on public.asesora to authenticated;


-- -----------------------------------------------------------------------------
-- 2. Configuración por empresa (⚑)
-- Umbrales vacíos = no configurados: Pendientes no marca a nadie hasta que se pongan.
-- textos: las palabras de la pantalla propias de la empresa, por ejemplo
--   {"persona": "vendedora", "personas": "vendedoras", "punto": "tienda"}.
-- -----------------------------------------------------------------------------

alter table public.empresa_config
  add column equipo_reparto text not null default 'partes_iguales'
    check (equipo_reparto in ('partes_iguales')),
  add column equipo_umbral_cumplimiento int check (equipo_umbral_cumplimiento between 1 and 100),
  add column equipo_umbral_dias_sin_seguimiento int check (equipo_umbral_dias_sin_seguimiento > 0),
  add column equipo_umbral_compromisos_vencidos int check (equipo_umbral_compromisos_vencidos > 0),
  add column equipo_dias_proximos int not null default 7 check (equipo_dias_proximos between 1 and 60),
  add column textos jsonb not null default '{}'::jsonb check (jsonb_typeof(textos) = 'object');

-- Temas, criterios de evaluación y tipos de observación de cada empresa.
create table public.equipo_catalogo (
  id           uuid primary key default gen_random_uuid(),
  empresa_id   uuid not null references public.empresa (id),
  clase        text not null check (clase in ('tema', 'criterio', 'tipo_observacion')),
  nombre       text not null check (length(trim(nombre)) > 0),
  descripcion  text,
  orden        int not null default 0,
  activo       boolean not null default true,
  creado_en    timestamptz not null default now(),
  unique (empresa_id, id),
  unique (empresa_id, clase, nombre)
);
create index equipo_catalogo_empresa_idx on public.equipo_catalogo (empresa_id, clase);

-- La plantilla inicial: solo tipos de observación. Temas y criterios empiezan vacíos.
create or replace function app.plantilla_equipo(p_empresa uuid)
returns void
language sql security definer set search_path = ''
as $$
  insert into public.equipo_catalogo (empresa_id, clase, nombre, orden)
  select p_empresa, 'tipo_observacion', t.nombre, t.orden
  from (values ('Coaching', 1), ('Cliente incógnito', 2), ('Presentación personal', 3), ('Uso del celular', 4),
               ('Puntualidad', 5), ('Novedad operativa', 6), ('Otro', 7)) as t (nombre, orden)
  on conflict (empresa_id, clase, nombre) do nothing
$$;
revoke execute on function app.plantilla_equipo(uuid) from public, authenticated;

create or replace function app.plantilla_equipo_empresa_nueva()
returns trigger
language plpgsql security definer set search_path = ''
as $$
begin
  perform app.plantilla_equipo(new.id);
  return new;
end;
$$;

create trigger empresa_plantilla_equipo
  after insert on public.empresa
  for each row execute function app.plantilla_equipo_empresa_nueva();

do $$ begin perform app.plantilla_equipo(id) from public.empresa; end $$;


-- -----------------------------------------------------------------------------
-- 3. Persona en punto, con vigencia
-- hasta vacío = sigue ahí. Para sacarla de un punto se pone hasta; no se borra.
-- Una persona no puede tener dos asignaciones cruzadas al mismo punto.
-- -----------------------------------------------------------------------------

create table public.asesora_punto (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  asesora_id  uuid not null,
  punto_id    uuid not null,
  desde       date not null default current_date,
  hasta       date,
  nota        text,
  creado_por  uuid default auth.uid(),
  creado_en   timestamptz not null default now(),
  check (hasta is null or hasta >= desde),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  constraint asesora_punto_sin_cruces exclude using gist (
    empresa_id with =, asesora_id with =, punto_id with =,
    (daterange(desde, hasta, '[]')) with &&
  )
);
create index asesora_punto_empresa_idx on public.asesora_punto (empresa_id, punto_id);
create index asesora_punto_asesora_idx on public.asesora_punto (asesora_id);


-- -----------------------------------------------------------------------------
-- 4. Venta por persona y día
-- Una fila por persona y día, con su parte. venta_dia y personas_dia guardan lo que traía
-- la fila del reporte, para poder rehacer el reparto. facturas puede venir vacío: ese
-- día no cuenta para el ticket promedio.
-- -----------------------------------------------------------------------------

create table public.venta_asesora_dia (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  punto_id        uuid not null,
  fecha           date not null,
  asesora_id      uuid,
  texto_original  text not null,
  venta           bigint not null,
  facturas        numeric(9, 2) check (facturas >= 0),
  venta_dia       bigint not null,
  facturas_dia    int check (facturas_dia >= 0),
  personas_dia    int not null default 1 check (personas_dia >= 1),
  anulada         boolean not null default false,
  archivo_id      uuid not null,
  fila_origen     int not null check (fila_origen > 0),
  creado_en       timestamptz not null default now(),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id)
);
create index venta_asesora_dia_empresa_idx on public.venta_asesora_dia (empresa_id, fecha);
create index venta_asesora_dia_asesora_idx on public.venta_asesora_dia (asesora_id, fecha);
create index venta_asesora_dia_archivo_idx on public.venta_asesora_dia (archivo_id);

-- Lo que cuenta: de un archivo cargado y, si dos archivos traen el mismo punto y día, el
-- último que se cargó (D-038).
create view public.v_venta_asesora with (security_invoker = true) as
select v.id, v.empresa_id, v.punto_id, v.fecha, v.asesora_id, v.texto_original, v.venta, v.facturas,
       v.venta_dia, v.facturas_dia, v.personas_dia, v.archivo_id, v.fila_origen
from (
  select v.*, dense_rank() over (partition by v.empresa_id, v.punto_id, v.fecha
                                 order by a.creado_en desc, a.id desc) as orden
  from public.venta_asesora_dia v
  join public.archivo_importado a on a.id = v.archivo_id and a.estado = 'cargado'
  where not v.anulada
) v
where v.orden = 1;


-- -----------------------------------------------------------------------------
-- 5. Metas por período (por punto o por persona dentro de un punto)
-- -----------------------------------------------------------------------------

create table public.meta_periodo (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  punto_id    uuid not null,
  asesora_id  uuid,
  desde       date not null,
  hasta       date not null,
  monto       bigint not null check (monto > 0),
  activo      boolean not null default true,
  archivo_id  uuid,
  fila_origen int check (fila_origen > 0),
  creado_por  uuid default auth.uid(),
  creado_en   timestamptz not null default now(),
  check (hasta >= desde),
  -- Una meta que vino en un archivo dice de qué fila salió; una escrita a mano, no.
  check ((archivo_id is null) = (fila_origen is null)),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id)
);
create index meta_periodo_empresa_idx on public.meta_periodo (empresa_id, desde);
-- Una sola meta activa por punto (o persona en el punto) para cada día.
alter table public.meta_periodo add constraint meta_periodo_sin_cruces exclude using gist (
  empresa_id with =, punto_id with =,
  (coalesce(asesora_id, '00000000-0000-0000-0000-000000000000'::uuid)) with =,
  (daterange(desde, hasta, '[]')) with &&
) where (activo);


-- -----------------------------------------------------------------------------
-- 6. Acompañamiento
-- seguimiento: diagnóstico, objetivo, observación o evaluación de una persona. punto_id
-- es el punto donde pasó: decide quién lo ve.
-- -----------------------------------------------------------------------------

create table public.seguimiento (
  id                   uuid primary key default gen_random_uuid(),
  empresa_id           uuid not null references public.empresa (id),
  asesora_id           uuid not null,
  punto_id             uuid not null,
  tipo                 text not null check (tipo in ('diagnostico', 'objetivo', 'observacion', 'evaluacion')),
  tipo_observacion_id  uuid,
  tema_id              uuid,
  fecha                date not null default current_date,
  texto                text not null default '',
  valoracion           text check (valoracion in ('bien', 'a_mejorar', 'neutral')),
  anulado              boolean not null default false,
  nota_anulacion       text,
  autor_id             uuid default auth.uid(),
  creado_en            timestamptz not null default now(),
  unique (empresa_id, id),
  check (not anulado or length(trim(coalesce(nota_anulacion, ''))) > 0),
  check (tipo <> 'observacion' or tipo_observacion_id is not null),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, tipo_observacion_id) references public.equipo_catalogo (empresa_id, id),
  foreign key (empresa_id, tema_id) references public.equipo_catalogo (empresa_id, id)
);
create index seguimiento_empresa_idx on public.seguimiento (empresa_id, fecha desc);
create index seguimiento_asesora_idx on public.seguimiento (asesora_id, fecha desc);

-- Una evaluación califica cada criterio de 1 a 5.
create table public.seguimiento_criterio (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  seguimiento_id  uuid not null,
  criterio_id     uuid not null,
  puntaje         smallint not null check (puntaje between 1 and 5),
  comentario      text,
  creado_en       timestamptz not null default now(),
  unique (seguimiento_id, criterio_id),
  foreign key (empresa_id, seguimiento_id) references public.seguimiento (empresa_id, id),
  foreign key (empresa_id, criterio_id) references public.equipo_catalogo (empresa_id, id)
);
create index seguimiento_criterio_seg_idx on public.seguimiento_criterio (seguimiento_id);
create index seguimiento_criterio_empresa_idx on public.seguimiento_criterio (empresa_id);

-- Sesión de formación: punto vacío = para varios puntos.
create table public.sesion_formacion (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  punto_id    uuid,
  tema_id     uuid,
  titulo      text not null check (length(trim(titulo)) > 0),
  fecha       date not null,
  hora        time,
  estado      text not null default 'programada' check (estado in ('programada', 'hecha', 'cancelada')),
  notas       text,
  autor_id    uuid default auth.uid(),
  creado_en   timestamptz not null default now(),
  unique (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, tema_id) references public.equipo_catalogo (empresa_id, id)
);
create index sesion_formacion_empresa_idx on public.sesion_formacion (empresa_id, fecha);

create table public.sesion_asistente (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  sesion_id   uuid not null,
  asesora_id  uuid not null,
  asistio     boolean,
  creado_en   timestamptz not null default now(),
  unique (sesion_id, asesora_id),
  foreign key (empresa_id, sesion_id) references public.sesion_formacion (empresa_id, id),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id)
);
create index sesion_asistente_asesora_idx on public.sesion_asistente (asesora_id);
create index sesion_asistente_empresa_idx on public.sesion_asistente (empresa_id);

-- Compromiso: qué, quién responde (vacío = la misma persona), para cuándo, prioridad,
-- estado y avance. Se cierra cumplido o no cumplido; se anula con nota.
create table public.compromiso (
  id                      uuid primary key default gen_random_uuid(),
  empresa_id              uuid not null references public.empresa (id),
  asesora_id              uuid not null,
  punto_id                uuid not null,
  seguimiento_id          uuid,
  que                     text not null check (length(trim(que)) > 0),
  responsable_usuario_id  uuid references public.usuario (id),
  fecha_limite            date not null,
  prioridad               text not null default 'media' check (prioridad in ('alta', 'media', 'baja')),
  estado                  text not null default 'abierto'
                            check (estado in ('abierto', 'en_curso', 'cumplido', 'no_cumplido', 'anulado')),
  avance                  smallint not null default 0 check (avance between 0 and 100),
  nota                    text,
  cerrado_en              timestamptz,
  autor_id                uuid default auth.uid(),
  creado_en               timestamptz not null default now(),
  actualizado_en          timestamptz not null default now(),
  check (estado <> 'anulado' or length(trim(coalesce(nota, ''))) > 0),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, seguimiento_id) references public.seguimiento (empresa_id, id)
);
create index compromiso_empresa_idx on public.compromiso (empresa_id, estado, fecha_limite);
create index compromiso_asesora_idx on public.compromiso (asesora_id);

-- Al cerrar un compromiso la base anota cuándo; si se reabre, lo borra.
create or replace function app.compromiso_al_cambiar()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  new.actualizado_en := pg_catalog.now();
  if new.estado in ('cumplido', 'no_cumplido', 'anulado') then
    new.cerrado_en := coalesce(old.cerrado_en, pg_catalog.now());
    if new.estado = 'cumplido' then new.avance := 100; end if;
  else
    new.cerrado_en := null;
  end if;
  return new;
end;
$$;

create trigger compromiso_cambiar
  before update on public.compromiso
  for each row execute function app.compromiso_al_cambiar();


-- -----------------------------------------------------------------------------
-- 7. Recorrido guiado: qué vio cada usuario. Cada uno ve y escribe solo lo suyo.
-- -----------------------------------------------------------------------------

create table public.recorrido_usuario (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  usuario_id  uuid not null default auth.uid() references public.usuario (id),
  recorrido   text not null,
  estado      text not null check (estado in ('visto', 'saltado')),
  paso        int not null default 0 check (paso >= 0),
  creado_en   timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  unique (usuario_id, recorrido)
);
create index recorrido_usuario_empresa_idx on public.recorrido_usuario (empresa_id);

create trigger recorrido_usuario_actualizado
  before update on public.recorrido_usuario
  for each row execute function app.tocar_actualizado_en();


-- -----------------------------------------------------------------------------
-- 8. Seguridad por filas
-- -----------------------------------------------------------------------------

-- Catálogo: lo leen todos los de la empresa; lo configuran dueño, encargada, lider y soporte.
alter table public.equipo_catalogo enable row level security;
create policy equipo_catalogo_ver on public.equipo_catalogo
  for select to authenticated using (empresa_id = app.empresa_actual());
create policy equipo_catalogo_crear on public.equipo_catalogo
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']));
create policy equipo_catalogo_cambiar on public.equipo_catalogo
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.equipo_catalogo from anon, authenticated;
grant update (nombre, descripcion, orden, activo) on public.equipo_catalogo to authenticated;

-- Asignaciones: las lee toda la empresa (quién está dónde no es privado); las cambian
-- dueño, encargada, lider y soporte. Solo se cierra (hasta) o se le pone nota.
alter table public.asesora_punto enable row level security;
create policy asesora_punto_ver on public.asesora_punto
  for select to authenticated using (empresa_id = app.empresa_actual());
create policy asesora_punto_crear on public.asesora_punto
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']));
create policy asesora_punto_cambiar on public.asesora_punto
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.asesora_punto from anon, authenticated;
grant update (hasta, nota) on public.asesora_punto to authenticated;

-- Venta por persona: se ve si se ve el punto; la escribe quien sube archivos. Solo se
-- resuelve el nombre (asesora_id) o se anula.
alter table public.venta_asesora_dia enable row level security;
create policy venta_asesora_dia_ver on public.venta_asesora_dia
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_punto(punto_id));
create policy venta_asesora_dia_crear on public.venta_asesora_dia
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));
create policy venta_asesora_dia_cambiar on public.venta_asesora_dia
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.venta_asesora_dia from anon, authenticated;
grant update (asesora_id, anulada) on public.venta_asesora_dia to authenticated;

-- Metas por período: se ven si se ve el punto; las ponen dueño, encargada, lider y soporte.
-- Una meta no se edita: se desactiva y se pone otra.
alter table public.meta_periodo enable row level security;
create policy meta_periodo_ver on public.meta_periodo
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_punto(punto_id));
-- Finanzas sube archivos: puede dejar la meta que trae el Excel, no escribir una a mano.
create policy meta_periodo_crear on public.meta_periodo
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and (app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
                   or (app.rol_actual() = 'finanzas' and archivo_id is not null)));
create policy meta_periodo_cambiar on public.meta_periodo
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.meta_periodo from anon, authenticated;
grant update (activo) on public.meta_periodo to authenticated;

-- Acompañamiento: privado (app.ve_equipo). Lo escriben los mismos que lo ven, y el
-- responsable solo en su punto.
alter table public.seguimiento enable row level security;
create policy seguimiento_ver on public.seguimiento
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id));
create policy seguimiento_crear on public.seguimiento
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id) and autor_id = auth.uid());
create policy seguimiento_cambiar on public.seguimiento
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id))
  with check (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id));
revoke update on public.seguimiento from anon, authenticated;
grant update (anulado, nota_anulacion) on public.seguimiento to authenticated;

-- Los puntajes cuelgan de su evaluación: se ven y se escriben si se ve la evaluación.
alter table public.seguimiento_criterio enable row level security;
create policy seguimiento_criterio_ver on public.seguimiento_criterio
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and exists (select 1 from public.seguimiento s where s.id = seguimiento_id));
create policy seguimiento_criterio_crear on public.seguimiento_criterio
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and exists (select 1 from public.seguimiento s where s.id = seguimiento_id and s.tipo = 'evaluacion'));
revoke update on public.seguimiento_criterio from anon, authenticated;

alter table public.sesion_formacion enable row level security;
create policy sesion_formacion_ver on public.sesion_formacion
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and (app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
              or (app.rol_actual() = 'responsable_punto' and (punto_id is null or punto_id = app.punto_actual()))));
create policy sesion_formacion_crear on public.sesion_formacion
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and (app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
                   or (app.rol_actual() = 'responsable_punto' and punto_id = app.punto_actual())));
create policy sesion_formacion_cambiar on public.sesion_formacion
  for update to authenticated
  using (empresa_id = app.empresa_actual()
         and (app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
              or (app.rol_actual() = 'responsable_punto' and punto_id = app.punto_actual())))
  with check (empresa_id = app.empresa_actual());
revoke update on public.sesion_formacion from anon, authenticated;
grant update (estado, notas, fecha, hora) on public.sesion_formacion to authenticated;

alter table public.sesion_asistente enable row level security;
create policy sesion_asistente_ver on public.sesion_asistente
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and exists (select 1 from public.sesion_formacion s where s.id = sesion_id));
create policy sesion_asistente_crear on public.sesion_asistente
  for insert to authenticated
  with check (empresa_id = app.empresa_actual()
              and exists (select 1 from public.sesion_formacion s where s.id = sesion_id));
create policy sesion_asistente_cambiar on public.sesion_asistente
  for update to authenticated
  using (empresa_id = app.empresa_actual()
         and exists (select 1 from public.sesion_formacion s where s.id = sesion_id))
  with check (empresa_id = app.empresa_actual());
revoke update on public.sesion_asistente from anon, authenticated;
grant update (asistio) on public.sesion_asistente to authenticated;

alter table public.compromiso enable row level security;
create policy compromiso_ver on public.compromiso
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id));
create policy compromiso_crear on public.compromiso
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id) and autor_id = auth.uid());
create policy compromiso_cambiar on public.compromiso
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id))
  with check (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id));
revoke update on public.compromiso from anon, authenticated;
grant update (estado, avance, nota, fecha_limite, prioridad, responsable_usuario_id) on public.compromiso to authenticated;

alter table public.recorrido_usuario enable row level security;
create policy recorrido_usuario_ver on public.recorrido_usuario
  for select to authenticated using (empresa_id = app.empresa_actual() and usuario_id = auth.uid());
create policy recorrido_usuario_crear on public.recorrido_usuario
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and usuario_id = auth.uid());
create policy recorrido_usuario_cambiar on public.recorrido_usuario
  for update to authenticated
  using (empresa_id = app.empresa_actual() and usuario_id = auth.uid())
  with check (empresa_id = app.empresa_actual() and usuario_id = auth.uid());
revoke update on public.recorrido_usuario from anon, authenticated;
grant update (estado, paso) on public.recorrido_usuario to authenticated;

-- La configuración de equipo la cambia también el lider, pero solo esas columnas.
-- (empresa_config_cambiar de 0001 sigue siendo solo para dueño y soporte.)
-- La función que escribe vive en app (security definer, como las de permisos); la
-- pública solo la llama, para que nada en public se salte los permisos.
create or replace function app.guardar_config_equipo(p jsonb)
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if not app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']) then
    raise exception 'Sin permiso para cambiar la configuración de equipo' using errcode = '42501';
  end if;
  update public.empresa_config set
    equipo_umbral_cumplimiento = case when p ? 'equipo_umbral_cumplimiento'
      then (p ->> 'equipo_umbral_cumplimiento')::int else equipo_umbral_cumplimiento end,
    equipo_umbral_dias_sin_seguimiento = case when p ? 'equipo_umbral_dias_sin_seguimiento'
      then (p ->> 'equipo_umbral_dias_sin_seguimiento')::int else equipo_umbral_dias_sin_seguimiento end,
    equipo_umbral_compromisos_vencidos = case when p ? 'equipo_umbral_compromisos_vencidos'
      then (p ->> 'equipo_umbral_compromisos_vencidos')::int else equipo_umbral_compromisos_vencidos end,
    equipo_dias_proximos = case when p ? 'equipo_dias_proximos'
      then (p ->> 'equipo_dias_proximos')::int else equipo_dias_proximos end
  where empresa_id = app.empresa_actual();
end;
$$;

create or replace function public.guardar_config_equipo(p jsonb)
returns void
language sql security invoker set search_path = ''
as $$
  select app.guardar_config_equipo(p)
$$;


-- -----------------------------------------------------------------------------
-- 9. Auditoría y sin TRUNCATE
-- -----------------------------------------------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array[
    'equipo_catalogo', 'asesora_punto', 'venta_asesora_dia', 'meta_periodo', 'seguimiento',
    'seguimiento_criterio', 'sesion_formacion', 'sesion_asistente', 'compromiso', 'recorrido_usuario'
  ]
  loop
    execute format(
      'create trigger %1$s_auditoria
         after insert or update or delete on public.%1$I
         for each row execute function app.registrar_auditoria()', t);
    execute format('revoke truncate on public.%I from anon, authenticated', t);
  end loop;
end $$;


-- -----------------------------------------------------------------------------
-- 10. Importar el Excel del día con la venta por persona
-- La versión de 0010 pasa a app y esta la envuelve: guarda el archivo igual que antes y,
-- en la misma transacción, las filas de venta por persona que trae p -> 'ventas_persona'.
-- -----------------------------------------------------------------------------

alter function public.importar_archivo(jsonb) rename to importar_archivo_0010;
alter function public.importar_archivo_0010(jsonb) set schema app;
revoke execute on function app.importar_archivo_0010(jsonb) from public;
grant execute on function app.importar_archivo_0010(jsonb) to authenticated;

create or replace function public.importar_archivo(p jsonb)
returns uuid
language plpgsql security invoker set search_path = ''
as $$
declare
  v_archivo uuid := app.importar_archivo_0010(p);
  v_filas   int  := jsonb_array_length(coalesce(p -> 'ventas_persona', '[]'::jsonb));
begin
  insert into public.venta_asesora_dia (empresa_id, punto_id, fecha, asesora_id, texto_original, venta, facturas,
                                        venta_dia, facturas_dia, personas_dia, archivo_id, fila_origen)
  select app.empresa_actual(), x.punto_id, x.fecha, x.asesora_id, x.texto_original, x.venta, x.facturas,
         x.venta_dia, x.facturas_dia, coalesce(x.personas_dia, 1), v_archivo, x.fila_origen
  from jsonb_to_recordset(coalesce(p -> 'ventas_persona', '[]'::jsonb))
       as x(punto_id uuid, fecha date, asesora_id uuid, texto_original text, venta bigint, facturas numeric,
            venta_dia bigint, facturas_dia int, personas_dia int, fila_origen int);

  -- La meta del mes que trae el Excel. Si ya hay una meta activa para ese punto y período
  -- (escrita a mano o de otro archivo), se queda la que había.
  insert into public.meta_periodo (empresa_id, punto_id, asesora_id, desde, hasta, monto, archivo_id, fila_origen)
  select app.empresa_actual(), x.punto_id, x.asesora_id, x.desde, x.hasta, x.monto, v_archivo, x.fila_origen
  from jsonb_to_recordset(coalesce(p -> 'metas', '[]'::jsonb))
       as x(punto_id uuid, asesora_id uuid, desde date, hasta date, monto bigint, fila_origen int)
  on conflict do nothing;

  if v_filas > 0 then
    update public.archivo_importado set filas = coalesce(filas, 0) + v_filas where id = v_archivo;
  end if;
  return v_archivo;
end;
$$;

-- =============================================================================
-- Fin de 0011.
-- =============================================================================
