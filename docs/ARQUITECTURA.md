# Arquitectura

Una sola base de datos (Supabase) es la fuente de verdad. Todo lo demás entra a
ella o lee de ella. Cada empresa cliente vive separada por permisos en la base.

## Flujo de datos

```mermaid
flowchart LR
  subgraph Fuentes
    X[Excels diarios]
    S[Reportes Siigo]
    B[Extractos bancarios]
    D[Bold y Redeban]
    C[Correos de aviso]
    A[App de asesoras]
  end
  subgraph Ingesta
    P[Perfiles de fuente]
    I[Importadores]
    N[Normalizador de nombres]
    L[Lector de correos]
  end
  DB[(Supabase<br/>Postgres + RLS)]
  subgraph Motores
    M1[Conciliador]
    M2[Verificador de transferencias]
    M3[Detector de descuadres]
  end
  subgraph Salidas
    O1[Panel web]
    O2[Excel y Sheets]
    O3[Alertas]
    O4[Respaldo nocturno]
  end
  X & S & B & D --> I
  P --> I --> N --> DB
  C --> L --> DB
  A --> DB
  DB --> M1 & M2 & M3 --> DB
  DB --> O1 & O2 & O3 & O4
```

## Piezas

| Pieza | Qué hace | Estado |
| --- | --- | --- |
| Perfiles de fuente | Dicen cómo leer el archivo de cada empresa: qué columna es qué | Nuevo |
| Importadores | Leen cada archivo con su perfil, validan y guardan con archivo y fila de origen | Lectores del conciliador ya existen |
| Normalizador | Une las distintas formas de escribir un nombre de asesora o producto | Nuevo |
| Lector de correos | Revisa el buzón de avisos del banco y crea movimientos | Nuevo |
| Conciliador | Cruza pagos reportados con movimientos reales | 80 % |
| Verificador de transferencias | Comprobante contra aviso del banco en minutos; el extracto confirma | Nuevo |
| Detector de descuadres | Diferencias por día, punto y medio de pago, con causa y pruebas | En progreso |
| Programa de escritorio | Las pantallas de `docs/DESIGN.md` con datos reales, en un `.exe` (D-023) | Diseñado |
| Panel web | Las mismas pantallas en la web | Fase posterior |
| Excel y Sheets | Copiar como números y pestañas que se llenan solas | Nuevo |
| Alertas | Descuadres grandes y transferencias sospechosas | Nuevo |
| Respaldo | Copia nocturna y prueba de restauración mensual | Nuevo |
| App de asesoras | Nativa, con respaldo local de su punto | Fase posterior |

## Tecnología

| Capa | Elección | Por qué |
| --- | --- | --- |
| Base de datos | Supabase (Postgres) | Ya la conoces; RLS para separar empresas; autenticación incluida |
| Programa de escritorio | Python con pywebview, empacado como `.exe` | Es como funciona el conciliador actual y no necesita servidor |
| Panel web (después) | Next.js con TypeScript en Vercel | Rápido de desplegar, buen soporte en Claude Code |
| Íconos | Lucide | Igual en todas las plataformas |
| App nativa (después) | Expo (React Native) con SQLite local | Un solo código para Android e iPhone; funciona sin señal |
| Importadores y motores | Python, con la lógica de la plata también en TypeScript | D-022; `motores/CONTRATO.md` exige que los dos den lo mismo |

## Entornos

- **Pruebas:** un proyecto de Supabase con los datos de Milagros. Aquí se
  desarrolla y se prueba todo.
- **Producción:** otro proyecto de Supabase, solo para clientes que pagan.
  Nunca se prueba aquí.
- Las migraciones se aplican primero en pruebas y, cuando pasan, en producción.

## Seguridad

- Autenticación con Supabase Auth. Cada usuario pertenece a una empresa y tiene
  un rol: dueño, encargada, finanzas, asesora o soporte.
- RLS en todas las tablas. Las funciones `app.empresa_actual()` y
  `app.rol_actual()` dicen a qué empresa y con qué rol entra cada usuario.
- La llave de servicio (que se salta RLS) solo la usan procesos del servidor,
  nunca el navegador ni la app.
- Auditoría automática de cada cambio en la tabla `auditoria`.
- Acceso al buzón de avisos: solo lectura, con autorización escrita del cliente.

## Rendimiento

- El panel lee vistas precalculadas (`v_*`), no miles de filas sueltas.
- Toda tabla tiene índice por `empresa_id`.
- Meta: cualquier pantalla abre en menos de 2 segundos en un celular.

## Respaldo

- Exportación nocturna de la base a un almacenamiento aparte.
- Una vez al mes se restaura un respaldo en un proyecto de prueba para comprobar
  que sirve.

## Estructura del repositorio

```
tino/
  CLAUDE.md
  docs/            visión, arquitectura, modelo, diseño, marca, reglas, fuentes
  tareas/          una tarea por paso del plan
  db/migrations/   SQL numerado, nunca se edita uno aplicado
  ingesta/         importadores y perfiles
  motores/         contrato, núcleo en Python y en TypeScript, conciliador actual
  panel/           pantallas: `.exe` primero, web después
  app/             Expo (fase posterior)
  tests/casos/     días reales anonimizados como casos de control
```
