-- =============================================================================
-- 0003_importacion.sql
-- Cada archivo que entra al sistema y lo que no se pudo leer de él.
--
-- Paso 2.1 del plan. Ver docs/MODELO_DATOS.md.
--
-- El hash impide cargar dos veces el mismo archivo y duplicar plata. Un archivo no
-- se borra: se deshace (D-005). Deshecho deja de contar para el hash, para que se
-- pueda volver a subir.
-- =============================================================================

-- archivo_importado apunta al perfil con la empresa, como las demás tablas.
alter table public.perfil_fuente
  add constraint perfil_fuente_empresa_id_id_key unique (empresa_id, id);


-- -----------------------------------------------------------------------------
-- 1. Archivos
-- -----------------------------------------------------------------------------

create table public.archivo_importado (
  id           uuid primary key default gen_random_uuid(),
  empresa_id   uuid not null references public.empresa (id),
  perfil_id    uuid,
  fuente       text not null
                 check (fuente in ('excel_dia', 'siigo', 'banco', 'bold', 'redeban', 'correo')),
  nombre       text not null,
  hash         text not null check (hash ~ '^[0-9a-f]{64}$'),
  filas        int not null default 0 check (filas >= 0),
  desde        date,
  hasta        date,
  estado       text not null default 'cargado' check (estado in ('cargado', 'deshecho')),
  subido_por   uuid references public.usuario (id),
  creado_en    timestamptz not null default now(),
  deshecho_por uuid references public.usuario (id),
  deshecho_en  timestamptz,
  unique (empresa_id, id),
  foreign key (empresa_id, perfil_id) references public.perfil_fuente (empresa_id, id),
  check (hasta is null or desde is null or hasta >= desde),
  -- Deshecho siempre dice quién y cuándo.
  check ((estado = 'deshecho') = (deshecho_en is not null))
);

-- El hash es único por empresa, no global: dos empresas pueden subir un archivo igual.
create unique index archivo_hash_vigente
  on public.archivo_importado (empresa_id, hash)
  where estado = 'cargado';

create index archivo_importado_empresa_idx on public.archivo_importado (empresa_id, creado_en desc);


-- -----------------------------------------------------------------------------
-- 2. Errores de importación
-- Filas que no se pudieron leer y nombres sin reconocer. Nada se descarta en
-- silencio: lo que no entró queda aquí hasta que una persona lo resuelva.
-- -----------------------------------------------------------------------------

create table public.error_importacion (
  id            uuid primary key default gen_random_uuid(),
  empresa_id    uuid not null references public.empresa (id),
  archivo_id    uuid not null,
  fila_origen   int check (fila_origen > 0),
  tipo          text not null
                  check (tipo in ('fila_ilegible', 'nombre_sin_reconocer', 'producto_sin_reconocer',
                                  'datafono_sin_punto', 'otro')),
  texto         text not null,
  resuelto      boolean not null default false,
  resuelto_por  uuid references public.usuario (id),
  resuelto_en   timestamptz,
  nota          text,
  creado_en     timestamptz not null default now(),
  foreign key (empresa_id, archivo_id) references public.archivo_importado (empresa_id, id),
  check (resuelto = (resuelto_en is not null))
);

create index error_importacion_empresa_idx on public.error_importacion (empresa_id, resuelto);
create index error_importacion_archivo_idx on public.error_importacion (archivo_id);


-- -----------------------------------------------------------------------------
-- 3. Seguridad por filas
-- Ver: todos en la empresa menos la asesora, que no maneja archivos.
-- Subir y resolver: dueño, encargada, finanzas o soporte.
-- Borrar: nadie (D-005).
-- -----------------------------------------------------------------------------

alter table public.archivo_importado enable row level security;
alter table public.error_importacion enable row level security;

do $$
declare
  t text;
begin
  foreach t in array array['archivo_importado', 'error_importacion']
  loop
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

revoke truncate on public.archivo_importado, public.error_importacion from anon, authenticated;

-- =============================================================================
-- Fin de 0003. Siguiente: 0004_operacion_diaria.sql
-- =============================================================================
