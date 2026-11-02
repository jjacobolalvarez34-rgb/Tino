-- =============================================================================
-- 0001_cimientos.sql
-- Empresas, usuarios, permisos, auditoría, maestros y perfiles de fuente.
--
-- Paso 1.2 y 1.3 del plan. Ver docs/MODELO_DATOS.md.
--
-- Reglas que esta migración implementa:
--   * Toda tabla de datos lleva empresa_id y RLS (D-011).
--   * Dinero en bigint (D-004).
--   * Nada se borra: ninguna tabla tiene política de DELETE (D-005).
--   * Todo cambio queda en auditoria.
--   * Ninguna fila puede apuntar a una fila de otra empresa: las llaves
--     foráneas entre tablas de datos incluyen empresa_id.
-- =============================================================================

create extension if not exists pgcrypto;  -- gen_random_uuid()

-- Supabase guarda las extensiones en el esquema extensions.
-- btree_gist permite impedir vigencias cruzadas en precio_producto.
create schema if not exists extensions;
create extension if not exists btree_gist with schema extensions;

-- Esquema privado para funciones internas. No se expone en la API de Supabase.
create schema if not exists app;


-- -----------------------------------------------------------------------------
-- 1. Empresa y usuario
-- -----------------------------------------------------------------------------

-- Cada negocio cliente. Todo lo demás cuelga de aquí.
create table public.empresa (
  id                 uuid primary key default gen_random_uuid(),
  nombre             text not null,
  nit                text unique,
  plan               text not null default 'piloto'
                       check (plan in ('piloto', 'basico', 'completo')),
  puntos_contratados int check (puntos_contratados > 0),
  estado             text not null default 'prueba'
                       check (estado in ('prueba', 'activa', 'suspendida')),
  creada_en          timestamptz not null default now()
);

-- Quién entra, a qué empresa y con qué rol. El id es el mismo de auth.users,
-- la tabla de usuarios de Supabase Auth.
-- Por ahora un usuario pertenece a una sola empresa (pendiente P-002).
-- on delete restrict: un usuario no se borra, se desactiva con activo (D-005).
create table public.usuario (
  id          uuid primary key references auth.users (id) on delete restrict,
  empresa_id  uuid not null references public.empresa (id),
  nombre      text not null,
  rol         text not null
                check (rol in ('dueno', 'encargada', 'finanzas', 'asesora', 'soporte')),
  asesora_id  uuid,          -- se enlaza más abajo, cuando exista la tabla asesora
  punto_id    uuid,          -- punto fijo de una asesora
  activo      boolean not null default true,
  creado_en   timestamptz not null default now()
);
create index usuario_empresa_idx on public.usuario (empresa_id);


-- -----------------------------------------------------------------------------
-- 2. Funciones de permisos
--
-- Las políticas RLS preguntan "¿de qué empresa es quien consulta?" y "¿qué rol
-- tiene?". Estas funciones lo responden leyendo la tabla usuario.
--
-- security definer: corren con los permisos de su dueño, así pueden leer
-- usuario aunque esa tabla tenga RLS (si no, la consulta se volvería circular).
-- search_path vacío: evita que alguien las engañe con tablas de otro esquema.
-- stable: Postgres puede reutilizar el resultado dentro de una misma consulta.
-- -----------------------------------------------------------------------------

create or replace function app.empresa_actual()
returns uuid
language sql stable security definer set search_path = ''
as $$
  select u.empresa_id
  from public.usuario u
  where u.id = auth.uid() and u.activo
$$;

create or replace function app.rol_actual()
returns text
language sql stable security definer set search_path = ''
as $$
  select u.rol
  from public.usuario u
  where u.id = auth.uid() and u.activo
$$;

-- ¿El rol de quien consulta está en esta lista?
create or replace function app.tiene_rol(roles text[])
returns boolean
language sql stable security definer set search_path = ''
as $$
  select coalesce(app.rol_actual() = any (roles), false)
$$;

-- Deja un nombre listo para comparar: minúsculas, sin tildes, sin puntuación y
-- con un solo espacio entre palabras. Hace lo mismo que norm() de cierre/texto.py
-- del conciliador, para que la base y los importadores den el mismo resultado.
-- translate va antes que lower porque lower no cambia las tildes en todas las
-- configuraciones de Postgres.
create or replace function app.normalizar_texto(texto text)
returns text
language sql immutable strict set search_path = ''
as $$
  select trim(regexp_replace(
    lower(translate(texto, 'ÁÉÍÓÚÜÑÀÈÌÒÙáéíóúüñàèìòù', 'AEIOUUNAEIOUaeiouunaeiou')),
    '[^a-z0-9%$]+', ' ', 'g'
  ))
$$;

grant usage on schema app to authenticated;
grant execute on all functions in schema app to authenticated;


-- -----------------------------------------------------------------------------
-- 3. Auditoría
--
-- Cada INSERT y UPDATE de las tablas auditadas guarda una fila aquí con el
-- antes y el después. Nadie la escribe a mano: la llena un trigger.
-- -----------------------------------------------------------------------------

create table public.auditoria (
  id           bigint generated always as identity primary key,
  empresa_id   uuid,
  tabla        text not null,
  registro_id  uuid,
  accion       text not null check (accion in ('insert', 'update', 'delete')),
  antes        jsonb,
  despues      jsonb,
  usuario_id   uuid,
  fecha        timestamptz not null default now()
);
create index auditoria_empresa_fecha_idx on public.auditoria (empresa_id, fecha desc);
create index auditoria_registro_idx on public.auditoria (tabla, registro_id);

create or replace function app.registrar_auditoria()
returns trigger
language plpgsql security definer set search_path = ''
as $$
declare
  v_antes   jsonb := case when tg_op in ('UPDATE', 'DELETE') then to_jsonb(old) end;
  v_despues jsonb := case when tg_op in ('INSERT', 'UPDATE') then to_jsonb(new) end;
begin
  insert into public.auditoria (empresa_id, tabla, registro_id, accion, antes, despues, usuario_id)
  values (
    -- En la tabla empresa no hay empresa_id: su propio id cumple ese papel.
    coalesce(
      v_despues ->> 'empresa_id', v_antes ->> 'empresa_id',
      case when tg_table_name = 'empresa' then coalesce(v_despues ->> 'id', v_antes ->> 'id') end
    )::uuid,
    tg_table_name,
    -- empresa_config no tiene id: su llave es empresa_id.
    coalesce(
      v_despues ->> 'id', v_antes ->> 'id',
      v_despues ->> 'empresa_id', v_antes ->> 'empresa_id'
    )::uuid,
    lower(tg_op),
    v_antes,
    v_despues,
    auth.uid()
  );
  return coalesce(new, old);
end;
$$;


-- -----------------------------------------------------------------------------
-- 4. Maestros
-- Los códigos son únicos dentro de cada empresa, no globales.
--
-- RLS revisa la empresa de cada fila, pero no a qué fila apunta una llave
-- foránea. Por eso cada tabla apunta con (empresa_id, x_id) y cada maestro lleva
-- unique (empresa_id, id): así la base impide enlazar filas de otra empresa, y
-- un id de otra empresa da el mismo error que un id que no existe.
-- -----------------------------------------------------------------------------

create table public.punto_venta (
  id          uuid primary key default gen_random_uuid(),
  empresa_id  uuid not null references public.empresa (id),
  codigo      text not null,
  nombre      text not null,
  tipo        text not null default 'detal'
                check (tipo in ('detal', 'mayorista', 'bodega')),
  activo      boolean not null default true,
  creado_en   timestamptz not null default now(),
  unique (empresa_id, codigo),
  unique (empresa_id, id)
);

-- Todas las asesoras, activas o no. Nunca se borran: se desactivan.
create table public.asesora (
  id               uuid primary key default gen_random_uuid(),
  empresa_id       uuid not null references public.empresa (id),
  codigo           text not null,
  nombre_completo  text not null,
  activa           boolean not null default true,
  fecha_ingreso    date,
  fecha_retiro     date,
  creado_en        timestamptz not null default now(),
  unique (empresa_id, codigo),
  unique (empresa_id, id),
  check (fecha_retiro is null or fecha_ingreso is null or fecha_retiro >= fecha_ingreso)
);

-- Cada forma en que aparece escrito un nombre. texto_original guarda lo que dice
-- el reporte, tal cual. texto_normalizado lo calcula la base y es el que se
-- compara, sin importar cómo lo escribieron.
create table public.asesora_alias (
  id                 uuid primary key default gen_random_uuid(),
  empresa_id         uuid not null references public.empresa (id),
  asesora_id         uuid not null,
  texto_original     text not null,
  texto_normalizado  text not null
                       generated always as (app.normalizar_texto(texto_original)) stored,
  fuente             text,
  creado_en          timestamptz not null default now(),
  unique (empresa_id, texto_normalizado),
  foreign key (empresa_id, asesora_id) references public.asesora (empresa_id, id)
);

create table public.producto (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  codigo         text not null,
  codigo_siigo   text,
  nombre         text not null,
  categoria      text,
  activo         boolean not null default true,
  creado_en      timestamptz not null default now(),
  unique (empresa_id, codigo),
  unique (empresa_id, id)
);

create table public.producto_alias (
  id                 uuid primary key default gen_random_uuid(),
  empresa_id         uuid not null references public.empresa (id),
  producto_id        uuid not null,
  texto_original     text not null,
  texto_normalizado  text not null
                       generated always as (app.normalizar_texto(texto_original)) stored,
  fuente             text,
  creado_en          timestamptz not null default now(),
  unique (empresa_id, texto_normalizado),
  foreign key (empresa_id, producto_id) references public.producto (empresa_id, id)
);

create table public.tipo_venta (
  id                   uuid primary key default gen_random_uuid(),
  empresa_id           uuid not null references public.empresa (id),
  codigo               text not null,
  nombre               text not null,
  se_factura_en_siigo  boolean not null default true,
  mueve_inventario     boolean not null default true,
  activo               boolean not null default true,
  creado_en            timestamptz not null default now(),
  unique (empresa_id, codigo),
  unique (empresa_id, id)
);

-- Precio de lista con vigencia. tipo_venta_id vacío = precio general.
-- Un producto no puede tener dos precios vigentes el mismo día para el mismo
-- tipo de venta. vigente_hasta vacío = sin fecha de fin.
create table public.precio_producto (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references public.empresa (id),
  producto_id    uuid not null,
  tipo_venta_id  uuid,
  precio         bigint not null check (precio >= 0),
  vigente_desde  date not null,
  vigente_hasta  date,
  creado_en      timestamptz not null default now(),
  check (vigente_hasta is null or vigente_hasta >= vigente_desde),
  foreign key (empresa_id, producto_id) references public.producto (empresa_id, id),
  foreign key (empresa_id, tipo_venta_id) references public.tipo_venta (empresa_id, id),
  constraint precio_sin_vigencias_cruzadas exclude using gist (
    empresa_id with =,
    producto_id with =,
    (coalesce(tipo_venta_id, '00000000-0000-0000-0000-000000000000'::uuid)) with =,
    (daterange(vigente_desde, vigente_hasta, '[]')) with &&
  )
);

-- tipo dice qué clase de pago es, sin importar cómo lo llame cada empresa. Los
-- motores lo usan para saber qué reglas aplican a cada medio.
create table public.medio_pago (
  id                     uuid primary key default gen_random_uuid(),
  empresa_id             uuid not null references public.empresa (id),
  codigo                 text not null,
  nombre                 text not null,
  tipo                   text not null
                           check (tipo in ('efectivo', 'tarjeta', 'transferencia', 'otro')),
  requiere_conciliacion  boolean not null default true,
  activo                 boolean not null default true,
  creado_en              timestamptz not null default now(),
  unique (empresa_id, codigo),
  unique (empresa_id, id)
);

-- Cada datáfono y a qué punto pertenece. Si cambia de punto, se cierra este
-- registro con activo_hasta y se crea otro.
create table public.terminal_datafono (
  id               uuid primary key default gen_random_uuid(),
  empresa_id       uuid not null references public.empresa (id),
  punto_id         uuid not null,
  proveedor        text not null check (proveedor in ('bold', 'redeban', 'otro')),
  codigo_terminal  text not null,
  activo_desde     date not null,
  activo_hasta     date,
  creado_en        timestamptz not null default now(),
  check (activo_hasta is null or activo_hasta >= activo_desde),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id)
);
-- Un mismo terminal no puede estar activo dos veces a la vez en la empresa.
create unique index terminal_activo_unico
  on public.terminal_datafono (empresa_id, codigo_terminal)
  where activo_hasta is null;

-- Cuentas donde llegan transferencias. Solo los últimos 4 dígitos, nunca el
-- número completo. punto_id vacío = cuenta general de la empresa.
create table public.cuenta_recaudo (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  punto_id        uuid,
  medio_pago_id   uuid not null,
  banco           text not null,
  ultimos4        text not null check (ultimos4 ~ '^[0-9]{4}$'),
  correo_aviso    text,
  activo          boolean not null default true,
  creado_en       timestamptz not null default now(),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id),
  foreign key (empresa_id, medio_pago_id) references public.medio_pago (empresa_id, id)
);

-- Código con el que el banco dice de qué punto es un pago, como el del QR o la
-- llave. Una cuenta puede recibir pagos de varios puntos: el punto no sale de la
-- cuenta sino de este código. El cruce usa sus últimos 4 dígitos, así que dos
-- códigos activos no pueden compartirlos: el pago caería en el punto equivocado.
-- Si un punto cambia de código, se cierra con activo_hasta y se crea otro.
create table public.codigo_recaudo (
  id            uuid primary key default gen_random_uuid(),
  empresa_id    uuid not null references public.empresa (id),
  punto_id      uuid not null,
  codigo        text not null check (codigo ~ '^[0-9]{4,}$'),
  activo_desde  date not null,
  activo_hasta  date,
  creado_en     timestamptz not null default now(),
  check (activo_hasta is null or activo_hasta >= activo_desde),
  foreign key (empresa_id, punto_id) references public.punto_venta (empresa_id, id)
);
create unique index codigo_recaudo_activo_unico
  on public.codigo_recaudo (empresa_id, right(codigo, 4))
  where activo_hasta is null;

-- Cómo leer los reportes de cada empresa. mapeo_columnas dice qué columna del
-- archivo es qué campo del sistema, por ejemplo:
--   {"fecha": "Fecha Transacción", "valor": "Valor Bruto", "referencia": "Ref"}
create table public.perfil_fuente (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  fuente          text not null
                    check (fuente in ('excel_dia', 'siigo', 'banco', 'bold', 'redeban', 'correo')),
  nombre          text not null,
  mapeo_columnas  jsonb not null default '{}'::jsonb,
  activo          boolean not null default true,
  creado_en       timestamptz not null default now(),
  unique (empresa_id, nombre)
);

-- Configuración de cada empresa: los valores que las reglas de docs/REGLAS/
-- marcan con ⚑. Una fila por empresa. Ningún valor de estos va fijo en el código.
create table public.empresa_config (
  empresa_id                   uuid primary key references public.empresa (id),
  -- Conciliación (docs/REGLAS/conciliacion.md)
  conc_minutos_datafono        int    not null default 10   check (conc_minutos_datafono > 0),
  conc_minutos_transferencia   int    not null default 30   check (conc_minutos_transferencia > 0),
  conc_tolerancia_valor        bigint not null default 1000 check (conc_tolerancia_valor >= 0),
  -- Qué parte del depósito de Bold se acepta como completa. Normal: solo 100. Si
  -- Bold le descuenta algo a la empresa, como la cuota de un préstamo, se agrega
  -- ese porcentaje, por ejemplo {100,90}.
  bold_porcentajes_deposito    int[]  not null default '{100}'
                                 check (cardinality(bold_porcentajes_deposito) > 0
                                        and 0 <= all (bold_porcentajes_deposito)
                                        and 100 >= all (bold_porcentajes_deposito)),
  -- Descuadres (docs/REGLAS/descuadres.md)
  desc_umbral                  bigint not null default 1000 check (desc_umbral >= 0),
  desc_confianza_min           numeric(3, 2) not null default 0.60
                                 check (desc_confianza_min between 0 and 1),
  -- Transferencias (docs/REGLAS/verificacion_transferencias.md)
  transf_minutos_sospecha      int    not null default 30   check (transf_minutos_sospecha > 0),
  transf_ventana_aviso         int    not null default 30   check (transf_ventana_aviso > 0),
  actualizado_en               timestamptz not null default now()
);

-- Toda empresa nace con su configuración: si faltara la fila, los motores no
-- tendrían valores que leer.
create or replace function app.crear_empresa_config()
returns trigger
language plpgsql security definer set search_path = ''
as $$
begin
  insert into public.empresa_config (empresa_id) values (new.id);
  return new;
end;
$$;

create or replace function app.tocar_actualizado_en()
returns trigger
language plpgsql set search_path = ''
as $$
begin
  new.actualizado_en := pg_catalog.now();
  return new;
end;
$$;

-- Ahora que existen asesora y punto_venta, se enlazan desde usuario.
alter table public.usuario
  add constraint usuario_asesora_fk foreign key (empresa_id, asesora_id)
    references public.asesora (empresa_id, id),
  add constraint usuario_punto_fk   foreign key (empresa_id, punto_id)
    references public.punto_venta (empresa_id, id);


-- -----------------------------------------------------------------------------
-- 5. Índices por empresa
-- RLS filtra por empresa_id en cada consulta; sin índice, se vuelve lento.
-- -----------------------------------------------------------------------------

create index punto_venta_empresa_idx       on public.punto_venta (empresa_id);
create index asesora_empresa_idx           on public.asesora (empresa_id);
create index asesora_alias_asesora_idx     on public.asesora_alias (asesora_id);
create index producto_empresa_idx          on public.producto (empresa_id);
create index producto_alias_producto_idx   on public.producto_alias (producto_id);
create index tipo_venta_empresa_idx        on public.tipo_venta (empresa_id);
-- precio_producto no necesita índice propio: el de precio_sin_vigencias_cruzadas
-- ya empieza por empresa_id.
create index precio_producto_producto_idx  on public.precio_producto (producto_id, vigente_desde);
create index medio_pago_empresa_idx        on public.medio_pago (empresa_id);
create index terminal_datafono_empresa_idx on public.terminal_datafono (empresa_id);
create index terminal_datafono_punto_idx   on public.terminal_datafono (punto_id);
create index cuenta_recaudo_empresa_idx    on public.cuenta_recaudo (empresa_id);
create index codigo_recaudo_empresa_idx    on public.codigo_recaudo (empresa_id);
create index codigo_recaudo_punto_idx      on public.codigo_recaudo (punto_id);
create index perfil_fuente_empresa_idx     on public.perfil_fuente (empresa_id);


-- -----------------------------------------------------------------------------
-- 6. Seguridad por filas (RLS)
--
-- Regla general:
--   * Leer: cualquier usuario activo de la misma empresa.
--   * Crear y cambiar: dueño, encargada o soporte (maestros);
--     dueño o soporte (perfiles de fuente).
--   * Borrar: nadie. No se crea política de DELETE (D-005).
-- -----------------------------------------------------------------------------

-- empresa: cada uno ve la suya; solo el dueño o soporte la cambian.
-- Las empresas nuevas se crean desde el servidor con la llave de servicio.
alter table public.empresa enable row level security;

create policy empresa_ver on public.empresa
  for select to authenticated
  using (id = app.empresa_actual());

create policy empresa_cambiar on public.empresa
  for update to authenticated
  using (id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']))
  with check (id = app.empresa_actual());

-- RLS filtra filas, no columnas. El plan, los puntos contratados y el estado son
-- del proveedor y solo cambian con la llave de servicio: un cliente no puede
-- subirse de plan ni reactivarse solo.
revoke update on public.empresa from anon, authenticated;
grant update (nombre, nit) on public.empresa to authenticated;

-- usuario: cada uno se ve a sí mismo; dueño, encargada y soporte ven a todos
-- los de su empresa; solo dueño y soporte crean o cambian usuarios.
alter table public.usuario enable row level security;

create policy usuario_ver on public.usuario
  for select to authenticated
  using (
    id = auth.uid()
    or (empresa_id = app.empresa_actual()
        and app.tiene_rol(array['dueno', 'encargada', 'soporte']))
  );

create policy usuario_crear on public.usuario
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']));

create policy usuario_cambiar on public.usuario
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']))
  with check (empresa_id = app.empresa_actual());

-- auditoria: solo lectura, para dueño y soporte. La escribe el trigger.
alter table public.auditoria enable row level security;

create policy auditoria_ver on public.auditoria
  for select to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']));

-- Maestros: las mismas tres políticas en cada tabla. El bloque las crea en un
-- ciclo para no repetir lo mismo once veces; el resultado es igual a
-- escribirlas una por una.
do $$
declare
  t text;
begin
  foreach t in array array[
    'punto_venta', 'asesora', 'asesora_alias', 'producto', 'producto_alias',
    'tipo_venta', 'precio_producto', 'medio_pago', 'terminal_datafono', 'cuenta_recaudo',
    'codigo_recaudo'
  ]
  loop
    execute format('alter table public.%I enable row level security', t);

    execute format($p$
      create policy %1$s_ver on public.%1$I
        for select to authenticated
        using (empresa_id = app.empresa_actual())
    $p$, t);

    execute format($p$
      create policy %1$s_crear on public.%1$I
        for insert to authenticated
        with check (empresa_id = app.empresa_actual()
                    and app.tiene_rol(array['dueno', 'encargada', 'soporte']))
    $p$, t);

    execute format($p$
      create policy %1$s_cambiar on public.%1$I
        for update to authenticated
        using (empresa_id = app.empresa_actual()
               and app.tiene_rol(array['dueno', 'encargada', 'soporte']))
        with check (empresa_id = app.empresa_actual())
    $p$, t);
  end loop;
end $$;

-- empresa_config: todos los de la empresa leen; solo dueño o soporte cambian.
alter table public.empresa_config enable row level security;

create policy empresa_config_ver on public.empresa_config
  for select to authenticated
  using (empresa_id = app.empresa_actual());

create policy empresa_config_crear on public.empresa_config
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']));

create policy empresa_config_cambiar on public.empresa_config
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']))
  with check (empresa_id = app.empresa_actual());

-- perfil_fuente: todos los de la empresa leen; solo dueño o soporte configuran.
alter table public.perfil_fuente enable row level security;

create policy perfil_fuente_ver on public.perfil_fuente
  for select to authenticated
  using (empresa_id = app.empresa_actual());

create policy perfil_fuente_crear on public.perfil_fuente
  for insert to authenticated
  with check (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']));

create policy perfil_fuente_cambiar on public.perfil_fuente
  for update to authenticated
  using (empresa_id = app.empresa_actual() and app.tiene_rol(array['dueno', 'soporte']))
  with check (empresa_id = app.empresa_actual());


-- -----------------------------------------------------------------------------
-- 7. Triggers de auditoría
-- -----------------------------------------------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array[
    'empresa', 'empresa_config', 'usuario', 'punto_venta', 'asesora', 'asesora_alias', 'producto',
    'producto_alias', 'tipo_venta', 'precio_producto', 'medio_pago',
    'terminal_datafono', 'cuenta_recaudo', 'codigo_recaudo', 'perfil_fuente'
  ]
  loop
    execute format(
      'create trigger %1$s_auditoria
         after insert or update or delete on public.%1$I
         for each row execute function app.registrar_auditoria()', t);
  end loop;
end $$;

create trigger empresa_crear_config
  after insert on public.empresa
  for each row execute function app.crear_empresa_config();

create trigger empresa_config_actualizado
  before update on public.empresa_config
  for each row execute function app.tocar_actualizado_en();


-- -----------------------------------------------------------------------------
-- 8. Sin TRUNCATE para usuarios
-- RLS no aplica a TRUNCATE. Sin esto, el permiso que Supabase da por defecto
-- podría vaciar una tabla entera y saltarse "nada se borra" (D-005).
-- -----------------------------------------------------------------------------

revoke truncate on all tables in schema public from anon, authenticated;
alter default privileges in schema public revoke truncate on tables from anon, authenticated;

-- =============================================================================
-- Fin de 0001. Siguiente: 0002_importacion.sql
-- =============================================================================
