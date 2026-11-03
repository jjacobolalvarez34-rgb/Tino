-- =============================================================================
-- 0006_descuadres.sql
-- El descuadre de cada jornada, su causa más probable y las pruebas, y los valores
-- con que se decide (⚑ D1 a D6 de docs/REGLAS/descuadres.md).
--
-- Paso 3.3 del plan. Ver docs/MODELO_DATOS.md.
--
-- Reglas que esta migración implementa:
--   * Si no hay causa clara, se dice "sin causa clara" (catálogo).
--   * Un descuadre no se borra. Termina explicado, resuelto o aceptado, siempre con
--     nota y con quién lo hizo; la base pone quién y cuándo.
--   * Cuando llega información nueva, se recalcula: las pruebas viejas no se borran,
--     dejan de estar vigentes.
--   * La asesora no ve descuadres en la fase 1 (D-036).
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Catálogo de causas
-- Es el mismo para todas las empresas: lo usan los motores. Cuánto pesa cada causa
-- sí es de cada empresa (desc_reglas_sin_peso).
-- -----------------------------------------------------------------------------

create table public.causa_descuadre (
  codigo       text primary key,
  regla        text not null,
  nombre       text not null,
  descripcion  text not null
);

insert into public.causa_descuadre (codigo, regla, nombre, descripcion) values
  ('transferencia_no_llego',     'R30', 'Transferencia que no llegó',
   'Anotada en el Excel y no está en el banco ese día ni los vecinos.'),
  ('transferencia_sin_anotar',   'R30', 'Transferencia sin anotar',
   'Está en el banco y no en el Excel.'),
  ('transferencia_mal_digitada', 'R30', 'Transferencia mal digitada',
   'Un monto anotado y uno real que parecen el mismo mal escrito.'),
  ('tarjeta_no_aparece',         'R33', 'Venta con tarjeta que no aparece',
   'Anotada y no está en el reporte de Bold o Redeban.'),
  ('tarjeta_sin_anotar',         'R33', 'Cobro con tarjeta sin anotar',
   'Está en el reporte de Bold o Redeban y no en el Excel.'),
  ('tarjeta_mal_digitada',       'R33', 'Tarjeta mal digitada',
   'Un monto anotado y uno cobrado que parecen el mismo mal escrito.'),
  ('compensacion',               'R03', 'Compensación entre días',
   'Un día sobra y el vecino falta un monto parecido.'),
  ('billete',                    'R04', 'Error de billete',
   'El descuadre es justo de uno a pocos billetes de la misma denominación.'),
  ('precios',                    'R05', 'Suma de precios',
   'El descuadre es lo que valen pocos productos del punto. Es pista, no explica.'),
  ('sin_causa_clara',            '-',   'Sin causa clara',
   'Nada lo explica lo suficiente. Se dice así, sin inventar.');

alter table public.causa_descuadre enable row level security;

create policy causa_descuadre_ver on public.causa_descuadre
  for select to authenticated
  using (true);

revoke truncate on public.causa_descuadre from anon, authenticated;


-- -----------------------------------------------------------------------------
-- 2. Descuadre: uno por jornada
-- estado_motor es lo que calculó Tino; estado es lo que decidió una persona.
-- -----------------------------------------------------------------------------

-- reporte_caja necesita (empresa_id, id) para que el descuadre apunte con la empresa.
alter table public.reporte_caja
  add constraint reporte_caja_empresa_id_id_key unique (empresa_id, id);

create table public.descuadre (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  jornada_id      uuid not null,
  reporte_id      uuid,
  monto           bigint not null,
  explicado       bigint not null default 0,
  sin_explicar    bigint not null default 0,
  estado_motor    text not null check (estado_motor in ('cuadra', 'explicado', 'sin_explicar')),
  causa_codigo    text references public.causa_descuadre (codigo),
  estado          text not null default 'abierto'
                    check (estado in ('abierto', 'explicado', 'resuelto', 'aceptado')),
  nota            text,
  decidido_por    uuid references public.usuario (id),
  decidido_en     timestamptz,
  calculado_en    timestamptz not null default now(),
  creado_en       timestamptz not null default now(),
  unique (empresa_id, jornada_id),
  unique (empresa_id, id),
  foreign key (empresa_id, jornada_id) references public.jornada (empresa_id, id),
  foreign key (empresa_id, reporte_id) references public.reporte_caja (empresa_id, id),
  check (explicado + sin_explicar = monto),
  -- Sin causa clara no lleva una causa inventada al lado.
  check (estado_motor <> 'sin_explicar' or causa_codigo is null or causa_codigo = 'sin_causa_clara'),
  -- Cerrar un descuadre siempre dice quién.
  check (estado = 'abierto' or decidido_por is not null)
);


-- -----------------------------------------------------------------------------
-- 3. Pruebas de cada causa
-- tipo: causa (explica), senal (para revisar) o pista (se muestra, no explica).
-- detalle guarda lo que la pantalla necesita: filas del Excel, fecha del día
-- vecino, billetes o combinaciones de precios.
-- -----------------------------------------------------------------------------

create table public.descuadre_evidencia (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references public.empresa (id),
  descuadre_id    uuid not null,
  causa_codigo    text not null references public.causa_descuadre (codigo),
  tipo            text not null check (tipo in ('causa', 'senal', 'pista')),
  monto           bigint not null default 0,
  total           bigint not null default 0,
  pago_id         uuid,
  movimiento_id   uuid,
  detalle         jsonb not null default '{}'::jsonb,
  vigente         boolean not null default true,
  creado_en       timestamptz not null default now(),
  foreign key (empresa_id, descuadre_id) references public.descuadre (empresa_id, id),
  foreign key (empresa_id, pago_id) references public.pago (empresa_id, id),
  foreign key (empresa_id, movimiento_id) references public.movimiento_externo (empresa_id, id),
  -- Una pista o una señal no explican plata.
  check (tipo = 'causa' or monto = 0)
);

create trigger descuadre_decision
  before insert or update on public.descuadre
  for each row execute function app.registrar_decision();


-- -----------------------------------------------------------------------------
-- 4. Valores de las reglas (⚑ D1 a D6)
-- D1 usa desc_umbral, que ya existía con 1.000: la regla dice 100 pesos.
-- -----------------------------------------------------------------------------

alter table public.empresa_config alter column desc_umbral set default 100;
update public.empresa_config set desc_umbral = 100 where desc_umbral = 1000;

alter table public.empresa_config
  add column desc_porcentaje_explicado  int      not null default 80
               check (desc_porcentaje_explicado between 0 and 100),
  add column desc_reglas_sin_peso       text[]   not null default array['R05'],
  add column desc_billetes              bigint[] not null default array[2000, 5000, 10000, 20000, 50000, 100000]::bigint[]
               check (0 < all (desc_billetes)),
  add column desc_max_billetes          int      not null default 3    check (desc_max_billetes >= 1),
  add column desc_comp_minimo           bigint   not null default 1000 check (desc_comp_minimo >= 0),
  add column desc_comp_tolerancia       bigint   not null default 500  check (desc_comp_tolerancia >= 0),
  add column desc_comp_porcentaje       int      not null default 25
               check (desc_comp_porcentaje between 0 and 100),
  add column desc_precios_minimo        bigint   not null default 1000 check (desc_precios_minimo >= 0),
  add column desc_precios_max_productos int      not null default 3    check (desc_precios_max_productos between 1 and 4),
  add column desc_precios_mostradas     int      not null default 3    check (desc_precios_mostradas >= 1);


-- -----------------------------------------------------------------------------
-- 5. Índices
-- -----------------------------------------------------------------------------

create index descuadre_empresa_idx          on public.descuadre (empresa_id, estado);
create index descuadre_evidencia_empresa_idx on public.descuadre_evidencia (empresa_id);
create index descuadre_evidencia_desc_idx   on public.descuadre_evidencia (descuadre_id) where vigente;


-- -----------------------------------------------------------------------------
-- 6. Seguridad por filas
-- Ver, calcular y resolver: dueño, encargada, finanzas o soporte. La asesora no.
-- -----------------------------------------------------------------------------

do $$
declare
  t text;
begin
  foreach t in array array['descuadre', 'descuadre_evidencia']
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

-- Recalcular cambia lo calculado; decidir cambia estado y nota. Quién y cuándo los
-- pone la base. Las pruebas no se reescriben: se dejan de usar.
revoke update on public.descuadre, public.descuadre_evidencia from anon, authenticated;
grant update (reporte_id, monto, explicado, sin_explicar, estado_motor, causa_codigo, calculado_en, estado, nota)
  on public.descuadre to authenticated;
grant update (vigente) on public.descuadre_evidencia to authenticated;

revoke truncate on public.descuadre, public.descuadre_evidencia from anon, authenticated;

-- =============================================================================
-- Fin de 0006. Siguiente: 0007_vistas_panel.sql
-- =============================================================================
