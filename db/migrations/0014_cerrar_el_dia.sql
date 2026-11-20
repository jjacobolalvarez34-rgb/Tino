-- =============================================================================
-- 0014_cerrar_el_dia.sql
-- Cerrar el día y desbloquearlo (GLOSARIO "Día cerrado", REGLAS/descuadres.md, roles de
-- MODELO_DATOS.md).
--
--   * Cierran: dueño y encargada cualquier punto; asesora y responsable de punto, el suyo.
--   * Desbloquean: dueño o encargada, siempre con nota.
--   * Un día con descuadres abiertos se puede cerrar, pero queda marcado (cuántos tenía).
--   * Un día cerrado no recibe caja, pagos, ventas, detalle, turnos ni notas nuevas, ni se le
--     cambian, y no se le puede deshacer un archivo: hay que desbloquearlo primero. Conciliar,
--     decidir descuadres y la revisión siguen funcionando.
--   * Cada cierre y cada desbloqueo queda en jornada_cierre, con quién, cuándo y la nota.
--   * Los estados "conciliada" y "bloqueada" no se usan todavía: las reglas no los definen.
-- =============================================================================

create table public.jornada_cierre (
  id                   uuid primary key default gen_random_uuid(),
  empresa_id           uuid not null references public.empresa (id),
  jornada_id           uuid not null,
  accion               text not null check (accion in ('cerrar', 'desbloquear')),
  nota                 text,
  descuadres_abiertos  int not null default 0 check (descuadres_abiertos >= 0),
  usuario_id           uuid references public.usuario (id),
  creado_en            timestamptz not null default now(),
  check (accion <> 'desbloquear' or length(trim(coalesce(nota, ''))) >= 3),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id)
);
create index jornada_cierre_empresa_idx on public.jornada_cierre (empresa_id, creado_en desc);
create index jornada_cierre_jornada_idx on public.jornada_cierre (jornada_id, creado_en desc);

create trigger jornada_cierre_auditoria
  after insert or update or delete on public.jornada_cierre
  for each row execute function app.registrar_auditoria();

alter table public.jornada_cierre enable row level security;
create policy jornada_cierre_ver on public.jornada_cierre
  for select to authenticated using (empresa_id = app.empresa_actual() and app.ve_jornada(jornada_id));
-- Nadie lo escribe directo: lo escribe la base cuando cambia el estado de un día.
revoke insert, update on public.jornada_cierre from anon, authenticated;
revoke truncate on public.jornada_cierre from anon, authenticated;

-- Cada cambio de estado de una jornada, venga de donde venga, pasa por aquí: abrir un día cerrado
-- exige dueño o encargada y una nota (la deja desbloquear_dia en app.nota_desbloqueo), y todo queda
-- en jornada_cierre. security definer: para escribir el historial, que nadie escribe a mano.
create or replace function app.al_cambiar_estado()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  v_nota text := nullif(trim(current_setting('app.nota_desbloqueo', true)), '');
begin
  if new.estado is not distinct from old.estado then
    return new;
  end if;
  if old.estado = 'abierta' then
    insert into public.jornada_cierre (empresa_id, jornada_id, accion, descuadres_abiertos, usuario_id)
    values (new.empresa_id, new.id, 'cerrar',
            (select count(*) from public.descuadre d where d.jornada_id = new.id and d.estado = 'abierto'), auth.uid());
  elsif new.estado = 'abierta' then
    if not app.tiene_rol(array['dueno', 'encargada']) then
      raise exception 'Solo el dueño o la encargada desbloquean un día' using errcode = '42501';
    end if;
    if v_nota is null or length(v_nota) < 3 then
      raise exception 'Escriba por qué se desbloquea' using errcode = '23514';
    end if;
    insert into public.jornada_cierre (empresa_id, jornada_id, accion, nota, usuario_id)
    values (new.empresa_id, new.id, 'desbloquear', v_nota, auth.uid());
  end if;
  return new;
end;
$$;

create trigger jornada_estado
  before update of estado on public.jornada
  for each row execute function app.al_cambiar_estado();


-- -----------------------------------------------------------------------------
-- Cerrar y desbloquear. La lógica vive en app (security definer, revisa empresa y rol a mano);
-- las públicas solo la llaman, para que nada en public se salte los permisos.
-- -----------------------------------------------------------------------------
create or replace function app.cerrar_dias(p_jornadas uuid[])
returns int
language plpgsql security definer set search_path = ''
as $$
declare
  v_empresa uuid := app.empresa_actual();
  j record;
  v_hechas int := 0;
begin
  if v_empresa is null then
    raise exception 'Sin sesión' using errcode = '42501';
  end if;
  for j in select * from public.jornada where id = any (p_jornadas) for update loop
    if j.empresa_id <> v_empresa then
      raise exception 'No se encontró ese día' using errcode = 'P0002';
    end if;
    if not (app.tiene_rol(array['dueno', 'encargada'])
            or (app.tiene_rol(array['asesora', 'responsable_punto']) and j.punto_id = app.punto_actual())) then
      raise exception 'Su usuario no puede cerrar ese día' using errcode = '42501';
    end if;
    continue when j.estado <> 'abierta';
    update public.jornada set estado = 'cerrada' where id = j.id;  -- el historial lo deja el trigger
    v_hechas := v_hechas + 1;
  end loop;
  return v_hechas;
end;
$$;

create or replace function app.desbloquear_dia(p_jornada uuid, p_nota text)
returns void
language plpgsql security definer set search_path = ''
as $$
declare
  j record;
begin
  if not app.tiene_rol(array['dueno', 'encargada']) then
    raise exception 'Solo el dueño o la encargada desbloquean un día' using errcode = '42501';
  end if;
  if length(trim(coalesce(p_nota, ''))) < 3 then
    raise exception 'Escriba por qué se desbloquea' using errcode = '23514';
  end if;
  select * into j from public.jornada where id = p_jornada for update;
  if not found or j.empresa_id <> app.empresa_actual() then
    raise exception 'No se encontró ese día' using errcode = 'P0002';
  end if;
  if j.estado = 'abierta' then
    return;
  end if;
  perform set_config('app.nota_desbloqueo', trim(p_nota), true);
  update public.jornada set estado = 'abierta' where id = j.id;   -- el historial lo deja el trigger
  perform set_config('app.nota_desbloqueo', '', true);
end;
$$;

revoke execute on function app.cerrar_dias(uuid[]), app.desbloquear_dia(uuid, text) from public;
grant execute on function app.cerrar_dias(uuid[]), app.desbloquear_dia(uuid, text) to authenticated;

create or replace function public.cerrar_dias(p_jornadas uuid[])
returns int language sql security invoker set search_path = '' as $$ select app.cerrar_dias(p_jornadas) $$;
create or replace function public.desbloquear_dia(p_jornada uuid, p_nota text)
returns void language sql security invoker set search_path = '' as $$ select app.desbloquear_dia(p_jornada, p_nota) $$;


-- -----------------------------------------------------------------------------
-- El candado: lo que cuelga de un día cerrado no se escribe ni se cambia.
-- -----------------------------------------------------------------------------
create or replace function app.dia_abierto(p_jornada uuid)
returns void
language plpgsql stable security definer set search_path = ''
as $$
declare
  v_estado text;
  v_fecha date;
begin
  -- Solo los días de la propia empresa: lo de otra empresa lo rechaza RLS con su error de siempre.
  select estado, fecha into v_estado, v_fecha from public.jornada
  where id = p_jornada and empresa_id = app.empresa_actual();
  if v_estado is not null and v_estado <> 'abierta' then
    raise exception 'El día % está cerrado. Desbloquéelo para cambiarlo.', to_char(v_fecha, 'YYYY-MM-DD')
      using errcode = '55000';
  end if;
end;
$$;

create or replace function app.candado_por_jornada()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  -- Quien no puede escribir aquí recibe el error de permisos de siempre (RLS), no este.
  if not app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']) then
    return coalesce(new, old);
  end if;
  perform app.dia_abierto(case when tg_op = 'DELETE' then old.jornada_id else new.jornada_id end);
  return coalesce(new, old);
end;
$$;

create or replace function app.candado_detalle()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  if not app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']) then
    return new;
  end if;
  perform app.dia_abierto((select v.jornada_id from public.venta v where v.id = new.venta_id));
  return new;
end;
$$;

do $$
declare
  t text;
begin
  foreach t in array array['reporte_caja', 'turno', 'venta', 'pago', 'movimiento_caja', 'observacion'] loop
    execute format('create trigger %1$s_dia_cerrado before insert or update on public.%1$I
                    for each row execute function app.candado_por_jornada()', t);
  end loop;
end $$;
create trigger venta_detalle_dia_cerrado before insert or update on public.venta_detalle
  for each row execute function app.candado_detalle();

-- Deshacer un archivo cambia lo que cuenta en sus días: si alguno está cerrado, no se puede.
create or replace function app.candado_deshacer()
returns trigger
language plpgsql set search_path = ''
as $$
declare
  v_fecha date;
begin
  if new.estado = 'deshecho' and old.estado = 'cargado' then
    select j.fecha into v_fecha
    from public.jornada j
    where j.estado <> 'abierta' and j.id in (
      select jornada_id from public.reporte_caja where archivo_id = new.id
      union select jornada_id from public.pago where archivo_id = new.id
      union select jornada_id from public.venta where archivo_id = new.id
      union select jornada_id from public.movimiento_caja where archivo_id = new.id)
    order by j.fecha limit 1;
    if v_fecha is not null then
      raise exception 'Este archivo tiene días cerrados (el primero, %). Desbloquéelos para deshacerlo.',
        to_char(v_fecha, 'YYYY-MM-DD') using errcode = '55000';
    end if;
  end if;
  return new;
end;
$$;

create trigger archivo_importado_dia_cerrado
  before update on public.archivo_importado
  for each row execute function app.candado_deshacer();

-- Para las pantallas: el último cierre de cada jornada.
create view public.v_jornada_cierre with (security_invoker = true) as
select distinct on (c.jornada_id) c.jornada_id, c.accion, c.nota, c.descuadres_abiertos, c.usuario_id, c.creado_en
from public.jornada_cierre c
order by c.jornada_id, c.creado_en desc;

-- =============================================================================
-- Fin de 0014.
-- =============================================================================
