-- =============================================================================
-- 0015_formacion.sql
-- Formación y desempeño (tarea 011, bloque A): el registro del día por persona, los
-- indicadores de cada empresa, las etapas del ciclo de formación y la plantilla sugerida.
--
-- Reglas que esta migración implementa (docs/REGLAS/equipo.md, "Formación"):
--   * Registro del día: por persona, punto y día, los clientes atendidos (fijo: es la base de
--     la conversión) y un contador por cada indicador que la empresa defina. Una sola fila por
--     persona, punto, día y origen.
--   * Origen: "manual" (lo llena una persona) o "integracion" (otra aplicación, en el futuro).
--     Los dos pueden existir el mismo día y no se pisan. Hoy los usuarios solo escriben
--     "manual"; "integracion" queda para un servicio que todavía no existe (A9).
--   * Se corrige libre el mismo día (hora de Bogotá); después, solo con nota. Nada se borra:
--     un registro se anula con nota.
--   * Lo llenan el responsable de punto (solo su punto), el lider y el dueño. Lo ven los que ven
--     el acompañamiento (app.ve_equipo).
--   * Un día sin registro no cuenta como cero: simplemente no hay fila.
--   * Etapas del ciclo: configurables por empresa (clase 'etapa' del catálogo). El paso de cada
--     persona lo cambia alguien a mano y queda la historia.
--   * Temas, criterios, indicadores y etapas no se llenan solos: la plantilla sugerida se usa
--     con un botón y no pisa lo que la empresa ya tenga.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Ayudas
-- -----------------------------------------------------------------------------

-- El día de hoy en Colombia: "el mismo día" se cuenta en hora de Bogotá, no en la del servidor.
create or replace function app.hoy()
returns date
language sql stable set search_path = ''
as $$ select (pg_catalog.now() at time zone 'America/Bogota')::date $$;

-- ¿Puede quien consulta llenar el registro del día de este punto?
create or replace function app.registra_dia(p_punto uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select app.tiene_rol(array['dueno', 'lider'])
      or (app.rol_actual() = 'responsable_punto' and p_punto = app.punto_actual())
$$;

-- ¿Puede ver el acompañamiento de esta persona? Los de oficina, a todas; el responsable de
-- punto, a las que hoy están en su punto.
create or replace function app.ve_persona(p_asesora uuid)
returns boolean
language sql stable security definer set search_path = ''
as $$
  select app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider'])
      or (app.rol_actual() = 'responsable_punto'
          and exists (select 1 from public.asesora_punto ap
                      where ap.asesora_id = p_asesora and ap.punto_id = app.punto_actual()
                        and ap.empresa_id = app.empresa_actual()
                        and ap.desde <= app.hoy() and (ap.hasta is null or ap.hasta >= app.hoy())))
$$;


-- -----------------------------------------------------------------------------
-- 2. Etapas del ciclo: una clase más del catálogo de Equipo
-- -----------------------------------------------------------------------------

alter table public.equipo_catalogo drop constraint equipo_catalogo_clase_check;
alter table public.equipo_catalogo add constraint equipo_catalogo_clase_check
  check (clase in ('tema', 'criterio', 'tipo_observacion', 'etapa'));


-- -----------------------------------------------------------------------------
-- 3. Indicadores del registro del día
-- base: contra qué se saca el porcentaje.
--   atendidos -> valor ÷ clientes atendidos (ej.: explicó el programa de fidelización)
--   facturas  -> valor ÷ facturas del día de esa persona (ej.: consultó puntos antes de cobrar)
--   conteo    -> solo se suma (ej.: referidos)
-- La base no se cambia después de creado: cambiaría el sentido de lo ya registrado.
-- -----------------------------------------------------------------------------

create table public.indicador_dia (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  nombre      text not null check (length(trim(nombre)) > 0),
  base        text not null check (base in ('atendidos', 'facturas', 'conteo')),
  orden       int not null default 0,
  activo      boolean not null default true,
  creado_en   timestamptz not null default now(),
  unique (empresa_id, id),
  unique (empresa_id, nombre)
);
create index indicador_dia_empresa_idx on public.indicador_dia (empresa_id, orden);


-- -----------------------------------------------------------------------------
-- 4. Registro del día
-- -----------------------------------------------------------------------------

create table public.registro_dia (
  id                  uuid primary key default gen_random_uuid(),
  empresa_id          uuid not null references public.empresa (id),
  asesora_id          uuid not null,
  punto_id            uuid not null,
  fecha               date not null,
  origen              text not null default 'manual' check (origen in ('manual', 'integracion')),
  fuente              text,                       -- qué integración lo trajo (vacío si es manual)
  clientes_atendidos  int not null check (clientes_atendidos >= 0),
  nota_correccion     text,                       -- la última nota con que se corrigió después del día
  anulado             boolean not null default false,
  nota_anulacion      text,
  autor_id            uuid default auth.uid(),
  creado_en           timestamptz not null default now(),
  actualizado_en      timestamptz not null default now(),
  unique (empresa_id, id),
  check (not anulado or length(trim(coalesce(nota_anulacion, ''))) > 0),
  check ((origen = 'manual') = (fuente is null)),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id)
);
-- Una sola fila vigente por persona, punto, día y origen.
create unique index registro_dia_unico on public.registro_dia (empresa_id, asesora_id, punto_id, fecha, origen)
  where not anulado;
create index registro_dia_empresa_idx on public.registro_dia (empresa_id, fecha);
create index registro_dia_asesora_idx on public.registro_dia (asesora_id, fecha);

create table public.registro_dia_valor (
  id            uuid primary key default gen_random_uuid(),
  empresa_id    uuid not null references public.empresa (id),
  registro_id   uuid not null,
  indicador_id  uuid not null,
  valor         int not null check (valor >= 0),
  creado_en     timestamptz not null default now(),
  unique (registro_id, indicador_id),
  foreign key (empresa_id, registro_id) references public.registro_dia (empresa_id, id),
  foreign key (empresa_id, indicador_id) references public.indicador_dia (empresa_id, id)
);
create index registro_dia_valor_empresa_idx on public.registro_dia_valor (empresa_id);
create index registro_dia_valor_registro_idx on public.registro_dia_valor (registro_id);


-- -----------------------------------------------------------------------------
-- 5. Paso del ciclo de cada persona: la historia completa; el paso actual es el último.
-- -----------------------------------------------------------------------------

create table public.asesora_etapa (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  asesora_id  uuid not null,
  etapa_id    uuid not null,
  desde       date not null default app.hoy(),
  nota        text,
  autor_id    uuid default auth.uid(),
  creado_en   timestamptz not null default now(),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id),
  foreign key (empresa_id, etapa_id) references public.equipo_catalogo (empresa_id, id)
);
create index asesora_etapa_empresa_idx on public.asesora_etapa (empresa_id, asesora_id, creado_en desc);

-- La etapa tiene que ser una etapa (no un tema ni un criterio) y estar activa.
create or replace function app.asesora_etapa_validar()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  -- Lo de otra empresa lo rechaza RLS con su error de siempre; aquí no se dice nada de ella.
  if new.empresa_id is distinct from app.empresa_actual() and app.empresa_actual() is not null then
    return new;
  end if;
  if not exists (select 1 from public.equipo_catalogo c
                 where c.id = new.etapa_id and c.empresa_id = new.empresa_id and c.clase = 'etapa' and c.activo) then
    raise exception 'Esa etapa no existe o está desactivada' using errcode = '23514';
  end if;
  return new;
end;
$$;
create trigger asesora_etapa_validar
  before insert on public.asesora_etapa
  for each row execute function app.asesora_etapa_validar();

-- El paso actual de cada persona.
create view public.v_asesora_etapa with (security_invoker = true) as
select distinct on (e.asesora_id) e.empresa_id, e.asesora_id, e.etapa_id, e.desde, e.creado_en
from public.asesora_etapa e
order by e.asesora_id, e.creado_en desc, e.id desc;


-- -----------------------------------------------------------------------------
-- 6. Permisos
-- -----------------------------------------------------------------------------

-- Indicadores: los lee toda la empresa; los configuran dueño, encargada, lider y soporte
-- (los mismos que el resto del catálogo de Equipo).
alter table public.indicador_dia enable row level security;
create policy indicador_dia_ver on public.indicador_dia
  for select to authenticated using (empresa_id = app.empresa_actual());
create policy indicador_dia_crear on public.indicador_dia
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']));
create policy indicador_dia_cambiar on public.indicador_dia
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.indicador_dia from anon, authenticated;
grant update (nombre, orden, activo) on public.indicador_dia to authenticated;

-- Registro del día: se lee si se ve el acompañamiento del punto. Se escribe solo con
-- guardar_registros_dia y anular_registro_dia (abajo), que revisan quién, cuándo y la nota.
alter table public.registro_dia enable row level security;
create policy registro_dia_ver on public.registro_dia
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_equipo(punto_id));
revoke insert, update on public.registro_dia from anon, authenticated;

alter table public.registro_dia_valor enable row level security;
create policy registro_dia_valor_ver on public.registro_dia_valor
  for select to authenticated
  using (empresa_id = app.empresa_actual()
         and exists (select 1 from public.registro_dia r where r.id = registro_id));
revoke insert, update on public.registro_dia_valor from anon, authenticated;

-- Paso del ciclo: lo ven y lo cambian los que ven a esa persona. Solo se agrega (la historia
-- no se reescribe): para corregir un paso, se pone otro.
alter table public.asesora_etapa enable row level security;
create policy asesora_etapa_ver on public.asesora_etapa
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_persona(asesora_id));
create policy asesora_etapa_crear on public.asesora_etapa
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.ve_persona(asesora_id) and autor_id = auth.uid());
revoke update on public.asesora_etapa from anon, authenticated;

do $$
declare
  t text;
begin
  foreach t in array array['indicador_dia', 'registro_dia', 'registro_dia_valor', 'asesora_etapa'] loop
    execute format(
      'create trigger %1$s_auditoria
         after insert or update or delete on public.%1$I
         for each row execute function app.registrar_auditoria()', t);
    execute format('revoke truncate on public.%I from anon, authenticated', t);
  end loop;
end $$;


-- -----------------------------------------------------------------------------
-- 7. Guardar el registro del día de varias personas de un punto en una sola vez
-- p = {"punto_id", "fecha", "nota" (si se corrige después del día),
--      "filas": [{"asesora_id", "clientes_atendidos", "valores": {"<indicador_id>": n, ...}}]}
-- Si la persona ya tiene registro manual ese día, se corrige: libre el mismo día, con nota
-- después. Devuelve cuántas filas quedaron nuevas o cambiadas.
-- -----------------------------------------------------------------------------

create or replace function app.guardar_registros_dia(p jsonb)
returns int
language plpgsql security definer set search_path = ''
as $$
declare
  v_empresa  uuid := app.empresa_actual();
  v_punto    uuid := (p ->> 'punto_id')::uuid;
  v_fecha    date := (p ->> 'fecha')::date;
  v_nota     text := nullif(trim(coalesce(p ->> 'nota', '')), '');
  f          jsonb;
  v_asesora  uuid;
  v_clientes int;
  v_reg      public.registro_dia;
  v_id       uuid;
  k          text;
  v_valor    int;
  v_ind      public.indicador_dia;
  v_cambia   boolean;
  v_hechas   int := 0;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;
  if not exists (select 1 from public.punto_venta where id = v_punto and empresa_id = v_empresa) then
    raise exception 'No se encontró ese punto' using errcode = 'P0002';
  end if;
  if not app.registra_dia(v_punto) then
    raise exception 'Su usuario no puede llenar el registro del día de ese punto' using errcode = '42501';
  end if;
  if v_fecha is null or v_fecha > app.hoy() then
    raise exception 'El registro del día no puede ser de un día que no ha pasado' using errcode = '22023';
  end if;

  for f in select * from jsonb_array_elements(coalesce(p -> 'filas', '[]'::jsonb)) loop
    v_asesora := (f ->> 'asesora_id')::uuid;
    v_clientes := (f ->> 'clientes_atendidos')::int;
    if v_clientes is null or v_clientes < 0 then
      raise exception 'Los clientes atendidos tienen que ser 0 o más' using errcode = '22023';
    end if;
    if not exists (select 1 from public.asesora_punto ap
                   where ap.empresa_id = v_empresa and ap.asesora_id = v_asesora and ap.punto_id = v_punto
                     and ap.desde <= v_fecha and (ap.hasta is null or ap.hasta >= v_fecha)) then
      raise exception 'Esa persona no estaba en ese punto ese día' using errcode = '23514';
    end if;

    select * into v_reg from public.registro_dia
    where empresa_id = v_empresa and asesora_id = v_asesora and punto_id = v_punto and fecha = v_fecha
      and origen = 'manual' and not anulado
    for update;

    -- ¿Cambia algo frente a lo guardado?
    v_cambia := v_reg.id is null or v_reg.clientes_atendidos <> v_clientes;
    if not v_cambia then
      for k, v_valor in select key, value::int from jsonb_each_text(coalesce(f -> 'valores', '{}'::jsonb)) loop
        if not exists (select 1 from public.registro_dia_valor
                       where registro_id = v_reg.id and indicador_id = k::uuid and valor = v_valor) then
          v_cambia := true;
        end if;
      end loop;
    end if;
    continue when not v_cambia;

    if v_reg.id is not null and v_fecha < app.hoy() and v_nota is null then
      raise exception 'Para corregir un día que ya pasó, escriba por qué' using errcode = '22023';
    end if;

    if v_reg.id is null then
      insert into public.registro_dia (empresa_id, asesora_id, punto_id, fecha, clientes_atendidos)
      values (v_empresa, v_asesora, v_punto, v_fecha, v_clientes)
      returning id into v_id;
    else
      v_id := v_reg.id;
      update public.registro_dia
      set clientes_atendidos = v_clientes, actualizado_en = pg_catalog.now(),
          nota_correccion = case when v_fecha < app.hoy() then v_nota else nota_correccion end
      where id = v_id;
    end if;

    for k, v_valor in select key, value::int from jsonb_each_text(coalesce(f -> 'valores', '{}'::jsonb)) loop
      select * into v_ind from public.indicador_dia where id = k::uuid and empresa_id = v_empresa;
      if v_ind.id is null or not v_ind.activo then
        raise exception 'Ese indicador no existe o está desactivado' using errcode = '23514';
      end if;
      if v_valor < 0 then
        raise exception 'Los contadores tienen que ser 0 o más' using errcode = '22023';
      end if;
      if v_ind.base = 'atendidos' and v_valor > v_clientes then
        raise exception '«%» no puede ser mayor que los clientes atendidos', v_ind.nombre using errcode = '22023';
      end if;
      insert into public.registro_dia_valor (empresa_id, registro_id, indicador_id, valor)
      values (v_empresa, v_id, v_ind.id, v_valor)
      on conflict (registro_id, indicador_id) do update set valor = excluded.valor
      where public.registro_dia_valor.valor <> excluded.valor;
    end loop;
    v_hechas := v_hechas + 1;
  end loop;
  return v_hechas;
end;
$$;

-- Anular un registro (por ejemplo, se llenó en la persona equivocada). Siempre con nota.
create or replace function app.anular_registro_dia(p_registro uuid, p_nota text)
returns void
language plpgsql security definer set search_path = ''
as $$
declare
  v_reg public.registro_dia;
begin
  select * into v_reg from public.registro_dia where id = p_registro and empresa_id = app.empresa_actual() for update;
  if v_reg.id is null then
    raise exception 'No se encontró ese registro' using errcode = 'P0002';
  end if;
  if v_reg.origen <> 'manual' or not app.registra_dia(v_reg.punto_id) then
    raise exception 'Su usuario no puede anular ese registro' using errcode = '42501';
  end if;
  if length(trim(coalesce(p_nota, ''))) = 0 then
    raise exception 'Para anular, escriba por qué' using errcode = '22023';
  end if;
  update public.registro_dia set anulado = true, nota_anulacion = trim(p_nota), actualizado_en = pg_catalog.now()
  where id = p_registro;
end;
$$;

revoke execute on function app.guardar_registros_dia(jsonb), app.anular_registro_dia(uuid, text) from public, anon;
grant execute on function app.guardar_registros_dia(jsonb), app.anular_registro_dia(uuid, text) to authenticated;

create or replace function public.guardar_registros_dia(p jsonb)
returns int language sql security invoker set search_path = '' as $$ select app.guardar_registros_dia(p) $$;
create or replace function public.anular_registro_dia(p_registro uuid, p_nota text)
returns void language sql security invoker set search_path = '' as $$ select app.anular_registro_dia(p_registro, p_nota) $$;


-- -----------------------------------------------------------------------------
-- 8. Lo que cuenta de cada día, con las facturas de esa persona
-- Si el mismo día hay registro manual y de integración, cuenta el manual y se marca que hay
-- otro (la pantalla los muestra los dos). facturas: las de la venta por persona de ese punto y
-- día; si el día lo compartieron varias, es su parte (personas_dia lo dice).
-- -----------------------------------------------------------------------------

create view public.v_registro_dia with (security_invoker = true) as
select r.id, r.empresa_id, r.asesora_id, r.punto_id, r.fecha, r.origen, r.clientes_atendidos,
       coalesce((select jsonb_object_agg(v.indicador_id, v.valor) from public.registro_dia_valor v
                 where v.registro_id = r.id), '{}'::jsonb) as valores,
       r.hay_otro_origen,
       f.facturas, f.personas_dia
from (
  select r.*, count(*) over (partition by r.empresa_id, r.asesora_id, r.punto_id, r.fecha) > 1 as hay_otro_origen,
         row_number() over (partition by r.empresa_id, r.asesora_id, r.punto_id, r.fecha
                            order by (r.origen = 'manual') desc, r.actualizado_en desc) as orden
  from public.registro_dia r
  where not r.anulado
) r
left join lateral (
  select sum(v.facturas) as facturas, max(v.personas_dia) as personas_dia
  from public.v_venta_asesora v
  where v.empresa_id = r.empresa_id and v.asesora_id = r.asesora_id and v.punto_id = r.punto_id and v.fecha = r.fecha
) f on true
where r.orden = 1;


-- -----------------------------------------------------------------------------
-- 9. Plantilla sugerida: solo cuando alguien pulsa "Usar plantilla sugerida". No pisa lo que
-- ya exista. El nombre del programa de fidelización sale de empresa_config.textos.programa.
-- -----------------------------------------------------------------------------

create or replace function app.usar_plantilla_formacion()
returns jsonb
language plpgsql security definer set search_path = ''
as $$
declare
  v_empresa  uuid := app.empresa_actual();
  v_programa text;
  v_antes    int;
  v_despues  int;
begin
  if v_empresa is null or not app.tiene_rol(array['dueno', 'encargada', 'soporte', 'lider']) then
    raise exception 'Su usuario no puede configurar Equipo' using errcode = '42501';
  end if;
  select coalesce(nullif(trim(textos ->> 'programa'), ''), 'programa de fidelización') into v_programa
  from public.empresa_config where empresa_id = v_empresa;
  v_programa := coalesce(v_programa, 'programa de fidelización');

  select (select count(*) from public.equipo_catalogo where empresa_id = v_empresa)
       + (select count(*) from public.indicador_dia where empresa_id = v_empresa) into v_antes;

  insert into public.equipo_catalogo (empresa_id, clase, nombre, orden)
  select v_empresa, t.clase, t.nombre, t.orden
  from (values
    ('tema', 'Venta consultiva', 1), ('tema', 'Programa de fidelización: ' || v_programa, 2),
    ('tema', 'Consulta de puntos', 3), ('tema', 'Estándares de atención', 4),
    ('criterio', 'Saluda y ofrece ayuda', 1), ('criterio', 'Pregunta qué necesita el cliente', 2),
    ('criterio', 'Explica el ' || v_programa, 3), ('criterio', 'Consulta los puntos antes de cobrar', 4),
    ('criterio', 'Ofrece un producto complementario', 5), ('criterio', 'Presentación personal', 6),
    ('etapa', 'Diagnóstico', 1), ('etapa', 'Formación', 2), ('etapa', 'Acompañamiento', 3),
    ('etapa', 'Evaluación', 4), ('etapa', 'Compromisos', 5)
  ) as t (clase, nombre, orden)
  on conflict (empresa_id, clase, nombre) do nothing;

  insert into public.indicador_dia (empresa_id, nombre, base, orden)
  select v_empresa, t.nombre, t.base, t.orden
  from (values ('Explicó el ' || v_programa, 'atendidos', 1), ('Consultó puntos antes de cobrar', 'facturas', 2),
               ('Referidos', 'conteo', 3)) as t (nombre, base, orden)
  on conflict (empresa_id, nombre) do nothing;

  select (select count(*) from public.equipo_catalogo where empresa_id = v_empresa)
       + (select count(*) from public.indicador_dia where empresa_id = v_empresa) into v_despues;
  return jsonb_build_object('agregados', v_despues - v_antes);
end;
$$;
revoke execute on function app.usar_plantilla_formacion() from public, anon;
grant execute on function app.usar_plantilla_formacion() to authenticated;
create or replace function public.usar_plantilla_formacion()
returns jsonb language sql security invoker set search_path = '' as $$ select app.usar_plantilla_formacion() $$;

grant execute on function app.hoy(), app.registra_dia(uuid), app.ve_persona(uuid) to authenticated;
