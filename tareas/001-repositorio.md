# 001 · Repositorio único y documentos base

Paso del plan: F1 · 1.1
Estado: pendiente

## Objetivo
Tener un solo repositorio con la estructura de carpetas, los documentos base y el
conciliador actual adentro, funcionando igual que antes.

## Alcance
- Crear el repositorio `tino` en GitHub (privado) con esta estructura.
- Copiar el código del conciliador actual a `motores/conciliador/` sin cambiar
  su lógica.
- Crear dos proyectos de Supabase: `tino-pruebas` y `tino-produccion`.
- Llenar la sección "Comandos" de `CLAUDE.md`.

## Fuera de alcance
- Cambiar cómo concilia el conciliador.
- Aplicar migraciones (eso es la tarea 002).

## Documentos a leer
- `CLAUDE.md`, `docs/ARQUITECTURA.md`

## Hecho cuando
- El conciliador, corrido desde el repositorio nuevo sobre un día de octubre,
  da exactamente el mismo resultado que antes.
- Las llaves de Supabase están en variables de entorno, no en el código.

## Cómo lo reviso yo (Jacobo)
- Corro el conciliador con el mismo archivo de antes y comparo resultados.
- Busco en el repositorio que no haya llaves ni datos reales.

## Notas
- Aquí se decide P-001 (lenguaje de importadores y motores) según el lenguaje
  del conciliador.

### Avance del 2 nov 2026
- Paso 1 hecho: `.gitignore` y `.env.example` creados.
- Paso 2 resuelto: el repositorio queda público (D-020).
- Paso 3 hecho: el código del conciliador está en `motores/conciliador/`, sin
  datos, sin compilados y sin `legacy_tkinter/`. Todos los `.py` quedaron idénticos
  al original, salvo `cierre/asesoras.py`, donde se cambió el nombre de una asesora
  real en un comentario. También en `README.md`, `cierre_config.json` y un texto de
  `webui/js/cierre.js`.
- `pruebas_cierre.py` está en la carpeta pero fuera de git: depende del archivo real
  de agosto y de ese nombre.
- Falta el paso 4: Jacobo elige el lenguaje (P-001). El paso 6 se reduce a
  `tino-pruebas` (D-021).

### Plan propuesto (2 nov 2026): espera la aprobación de Jacobo

Los códigos H-xx son los hallazgos de la entrada del 2 nov en `docs/BITACORA.md`.

Ya está hecho (local, sin commit):
- El contenido del zip quedó en la raíz del repositorio, que es la raíz `tino/` de
  `docs/ARQUITECTURA.md`.
- `ingesta/`, `motores/`, `panel/` y `app/` existen con un README corto.

Bloqueos: falta el código del conciliador y un día de octubre con su resultado
anterior. Crear los proyectos de Supabase es de Jacobo.

**Paso 1 · Blindar el repositorio antes del primer commit** (Claude)
- Crear `.gitignore`: `.env*` (menos `.env.example`), `*.zip`, `node_modules/`,
  `.next/`, `__pycache__/`, `.venv/`. Hoy no existe, y un `git add .` subiría el
  zip y cualquier `.env`. Por eso va primero.
- Crear `.env.example` solo con nombres: `SUPABASE_URL`, `SUPABASE_ANON_KEY`,
  `SUPABASE_SERVICE_ROLE_KEY`.

**Paso 2 · Revisar qué se sube** (Jacobo)
- Confirmar que `Tino` en GitHub es privado. No se pudo comprobar porque `gh` no
  tiene sesión iniciada. La tarea dice `tino` en minúscula; se deja `Tino` salvo
  que Jacobo prefiera cambiarlo.
- Decidir H-43 (nombres de `demo.html` que podrían ser reales) antes del primer
  push. Lo que entra a un commit queda en el historial aunque se borre después.

**Paso 3 · Traer el conciliador** (Claude, con el código que entregue Jacobo)
- Copiar solo el código a `motores/conciliador/`, sin su historial ni archivos de
  datos. Antes de copiar, buscar llaves, rutas personales y nombres de Milagros.
- Dos caminos si el código trae cosas de Milagros escritas adentro (H-42):
  - A · Copiarlo tal cual y anotar la deuda. Ventaja: el resultado queda idéntico
    y es fácil de comparar. Desventaja: rompe por un tiempo "nada específico de un
    cliente en el código".
  - B · Sacar esos valores a un archivo de configuración fuera del repositorio.
    Ventaja: cumple la regla desde el día 1. Desventaja: toca el código en una
    tarea que pide no tocarlo.
  - Recomendado: B solo para llaves y datos personales, que nunca pueden entrar;
    A para el resto, que se limpia en una tarea aparte.

**Paso 4 · Decidir P-001** (Jacobo elige, Claude registra)
- Según el lenguaje real del conciliador, registrar la decisión en
  `docs/DECISIONES.md`, moverla de pendientes a tomadas y llenar la fila "Por
  decidir" de `docs/ARQUITECTURA.md`.

**Paso 5 · Probar que da lo mismo** (Jacobo corre, o autoriza a Claude)
- Los archivos reales viven en una carpeta fuera del repositorio; nada de ese día
  entra a un commit.
- Correr el conciliador viejo y el nuevo sobre el mismo día y guardar las dos
  salidas. Ordenarlas igual y comparar fila por fila. Se espera diferencia cero,
  salvo marcas de tiempo si las hay.

**Paso 6 · Crear los proyectos de Supabase** (Jacobo)
- `tino-pruebas` y `tino-produccion`, en la región más cercana a Colombia. Supuesto:
  São Paulo, porque es la más cercana de las que suele ofrecer Supabase.
- Las llaves van en un `.env` local y en Vercel, nunca en el repositorio.

**Paso 7 · Llenar "Comandos" en `CLAUDE.md`** (Claude)
- Dos caminos para aplicar migraciones en Supabase:
  - A · `psql -f` con la URL de `tino-pruebas` y un script que aplica en orden.
    Ventaja: conserva `db/migrations/0001_...` y es igual a las pruebas locales.
    Desventaja: hay que llevar el registro de qué se aplicó.
  - B · Supabase CLI. Ventaja: lleva ese registro sola. Desventaja: espera sus
    propias carpetas y nombres con fecha, y habría que reorganizar. A verificar.
  - Recomendado: A, porque ya existe la numeración que usa `docs/MODELO_DATOS.md`.
- Para Windows, corregir `tests/rls/correr.sh` (H-13) y anotar que `psql` no está
  en el PATH: vive en `C:\Program Files\PostgreSQL\16\bin`.
- "Levantar el panel" queda sin llenar: el proyecto de Next.js no existe aún y esta
  tarea no lo crea. Propongo mover esa línea a la tarea que lo cree.

**Qué probar al final**
- Caso concreto: correr el conciliador con el día de octubre del paso 5 y comparar
  con el resultado de antes; debe dar cero diferencias.
- Buscar en todo el repositorio `eyJ` (inicio de las llaves de Supabase), `.env`,
  el nombre de una asesora real y el de un punto real; no debe aparecer nada.
