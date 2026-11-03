-- =============================================================================
-- 0002_asesoras.sql
-- Código automático por asesora y alias por punto de venta.
--
-- El código identifica a la asesora dentro del sistema. Pero los reportes solo
-- traen un nombre, y dos asesoras de puntos distintos pueden llamarse igual: por
-- eso cada forma de escribir un nombre vale para un punto (D-030).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Código automático
-- Si no llega código, la base asigna el siguiente de la empresa: A001, A002...
-- Como nada se borra, un número nunca se reutiliza. El bloqueo evita que dos
-- cargas al mismo tiempo tomen el mismo número.
-- -----------------------------------------------------------------------------

create or replace function app.asignar_codigo_asesora()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  v_siguiente bigint;
begin
  if new.codigo is not null then
    return new;
  end if;

  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtext(new.empresa_id::text));

  select coalesce(max(substring(a.codigo from 2)::bigint), 0) + 1
    into v_siguiente
  from public.asesora a
  where a.empresa_id = new.empresa_id and a.codigo ~ '^A[0-9]+$';

  new.codigo := 'A' || lpad(v_siguiente::text, 3, '0');
  return new;
end;
$$;

create trigger asesora_asignar_codigo
  before insert on public.asesora
  for each row execute function app.asignar_codigo_asesora();


-- -----------------------------------------------------------------------------
-- 2. Alias por punto
-- "Leidy" en un punto puede ser una persona y en otro, otra. Si una asesora rota,
-- su nombre se registra también en el otro punto.
-- punto_id es obligatorio: esto falla si la tabla ya tiene filas, y debe fallar,
-- porque habría que decidir de qué punto es cada alias.
-- -----------------------------------------------------------------------------

alter table public.asesora_alias
  add column punto_id uuid not null;

alter table public.asesora_alias
  drop constraint asesora_alias_empresa_id_texto_normalizado_key,
  add constraint asesora_alias_unico_por_punto
    unique (empresa_id, punto_id, texto_normalizado),
  add constraint asesora_alias_punto_fk foreign key (empresa_id, punto_id)
    references public.punto_venta (empresa_id, id);

create index asesora_alias_punto_idx on public.asesora_alias (punto_id);

-- =============================================================================
-- Fin de 0002. Siguiente: 0003_importacion.sql
-- =============================================================================
