-- =============================================================================
-- 0013_archivos_en_cola.sql
-- Subir archivos desde la web (D-057): el archivo se guarda en Supabase Storage, en la
-- carpeta de su empresa, y queda en cola. El programa de escritorio lo procesa con los
-- lectores de siempre y deja el resultado: cargado (con su archivo_importado), repetido o
-- error con su mensaje.
--
--   * Ruta en Storage: <empresa_id>/<huella sha256>/<nombre>. La primera carpeta decide la
--     empresa: nadie lee ni escribe en la de otra.
--   * La misma huella no entra dos veces a la cola mientras esté en cola, procesando o
--     cargada (el aviso de archivo repetido llega antes de subirlo).
--   * Nada se borra: un archivo de la cola se procesa o queda con su error.
-- =============================================================================

create table public.archivo_en_cola (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  ruta           text not null,
  nombre         text not null,
  tamano         bigint not null check (tamano > 0),
  hash           text not null check (hash ~ '^[0-9a-f]{64}$'),
  estado         text not null default 'en_cola'
                   check (estado in ('en_cola', 'procesando', 'cargado', 'repetido', 'error')),
  mensaje        text,
  archivo_id     uuid,
  subido_por     uuid not null default auth.uid() references public.usuario (id),
  procesado_por  uuid references public.usuario (id),
  creado_en      timestamptz not null default now(),
  procesado_en   timestamptz,
  -- La ruta empieza por la carpeta de su empresa.
  check (split_part(ruta, '/', 1) = empresa_id::text),
  check ((estado = 'cargado') = (archivo_id is not null)),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id)
);
create index archivo_en_cola_empresa_idx on public.archivo_en_cola (empresa_id, estado, creado_en);
create unique index archivo_en_cola_vigente on public.archivo_en_cola (empresa_id, hash)
  where estado in ('en_cola', 'procesando', 'cargado');

-- Al cambiar de estado, la base anota quién y cuándo.
create or replace function app.cola_al_cambiar()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  if new.estado is distinct from old.estado and new.estado <> 'en_cola' then
    new.procesado_en := pg_catalog.now();
    new.procesado_por := auth.uid();
  end if;
  return new;
end;
$$;

create trigger archivo_en_cola_cambiar
  before update on public.archivo_en_cola
  for each row execute function app.cola_al_cambiar();

create trigger archivo_en_cola_auditoria
  after insert or update or delete on public.archivo_en_cola
  for each row execute function app.registrar_auditoria();

-- Lo usan quienes suben archivos (los mismos de archivo_importado).
alter table public.archivo_en_cola enable row level security;
create policy archivo_en_cola_ver on public.archivo_en_cola
  for select to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));
create policy archivo_en_cola_crear on public.archivo_en_cola
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and subido_por = auth.uid() and estado = 'en_cola'
              and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']));
create policy archivo_en_cola_cambiar on public.archivo_en_cola
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
  with check (empresa_id = app.empresa_actual());
revoke update on public.archivo_en_cola from anon, authenticated;
grant update (estado, mensaje, archivo_id) on public.archivo_en_cola to authenticated;
revoke truncate on public.archivo_en_cola from anon, authenticated;

-- -----------------------------------------------------------------------------
-- Storage (solo existe en Supabase; en el Postgres local de pruebas se salta).
-- Carpeta privada "archivos"; la primera carpeta de la ruta es la empresa.
-- -----------------------------------------------------------------------------
do $$
begin
  if to_regclass('storage.objects') is null then
    raise notice 'Sin Supabase Storage: se salta la carpeta de archivos (base local).';
    return;
  end if;
  insert into storage.buckets (id, name, public, file_size_limit)
  values ('archivos', 'archivos', false, 52428800)
  on conflict (id) do nothing;

  execute $p$
    create policy "archivos_ver_su_empresa" on storage.objects
      for select to authenticated
      using (bucket_id = 'archivos' and (storage.foldername(name))[1] = app.empresa_actual()::text
             and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
  $p$;
  execute $p$
    create policy "archivos_subir_a_su_empresa" on storage.objects
      for insert to authenticated
      with check (bucket_id = 'archivos' and (storage.foldername(name))[1] = app.empresa_actual()::text
                  and app.tiene_rol(array['dueno', 'encargada', 'finanzas', 'soporte']))
  $p$;
end $$;

-- =============================================================================
-- Fin de 0013.
-- =============================================================================
