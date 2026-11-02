# 002 · Aplicar la migración 0001 (cimientos)

Paso del plan: F1 · 1.2 y 1.3
Estado: pendiente

## Objetivo
Crear en Supabase las tablas de empresas, configuración, usuarios, permisos, auditoría, maestros
y perfiles de fuente, con la separación entre empresas probada.

## Alcance
- Revisar `db/migrations/0001_cimientos.sql` línea por línea.
- Correr las pruebas locales (`tests/rls/correr.sh`) y confirmar que pasan.
- Aplicar la migración en `tino-pruebas`.
- Repetir las pruebas de permisos en Supabase con usuarios reales de prueba.

## Fuera de alcance
- Tablas de operación diaria, importación o conciliación (migraciones 0002 en
  adelante).
- Aplicar en producción.

## Documentos a leer
- `docs/MODELO_DATOS.md`, `db/migrations/0001_cimientos.sql`

## Hecho cuando
- Las 80 pruebas de `tests/rls/0001_pruebas.sql` pasan en local.
- En Supabase, un usuario de la empresa A no ve nada de la empresa B.
- Un cambio en un punto de venta aparece en `auditoria`.

## Cómo lo reviso yo (Jacobo)
- Leo cada bloque de la migración y me aseguro de entender qué hace.
- En el editor SQL de Supabase intento leer datos de otra empresa con un usuario
  de prueba.

## Notas
- Ya probada en un Postgres 16 local el 2 nov 2026: migra sin errores y las 20
  pruebas pasan (incluye `empresa_config`).

### Avance del 2 nov 2026
- Jacobo aprobó corregir 0001 antes de aplicarla (D-018). Pasos 1 a 3 hechos: 0001
  corregida y 80 pruebas en verde en Postgres 16.3. Quedan 15 tablas con RLS, 42
  políticas y 16 triggers.
- Se comprobó que las pruebas sirven: se quitó cada corrección, una por una, en una
  copia, y la suite falló cada vez.
- Sigue el paso 4 (Jacobo lee la migración) y después el paso 5 en `tino-pruebas`.
  H-05 y H-06 quedaron decididos (D-025) y 0001 ya funciona así.
- Abierto de 0001: el código de pago por punto (H-52) puede cambiar el modelo antes
  de aplicar. Conviene decidirlo en el paso 4.

### Plan propuesto (2 nov 2026): espera la aprobación de Jacobo

Los códigos H-xx son los hallazgos de la entrada del 2 nov en `docs/BITACORA.md`.

Corrida local del 2 nov, repetida en un Postgres 16.3 desechable: 15 tablas, las 15
con RLS, 42 políticas, ninguna de DELETE, 14 triggers y 20 pruebas OK. La migración
hace lo que sus pruebas revisan, pero las pruebas no revisan todo: una sonda aparte
encontró huecos reales (H-01 a H-03). Por eso **propongo no aplicarla todavía**.

Depende de la tarea 001: necesita `tino-pruebas` creado.

**Paso 1 · Decidir cómo corregir 0001** (Jacobo)
- A · Corregir el mismo archivo 0001 antes de aplicarlo. Ventaja: D-012 lo permite
  porque aún no se ha aplicado en ningún lado; queda un solo archivo limpio y la
  numeración de `docs/MODELO_DATOS.md` no cambia. Desventaja: hay que releer lo que
  ya se había revisado.
- B · Aplicar 0001 como está y corregir en una 0002. Ventaja: no se toca lo
  revisado. Desventaja: durante un tiempo hay una base con huecos conocidos y toda
  la numeración del plan se corre.
- Recomendado: A, porque corregir ahora no cuesta nada y aún no hay datos.

**Paso 2 · Cambios a 0001 si se aprueban** (Claude, solo con el visto bueno)

Este plan no toca `db/migrations/`. Cada cambio va con su prueba.

| Hallazgo | Cambio propuesto | Por qué |
| --- | --- | --- |
| H-01 | Llaves foráneas compuestas `(empresa_id, x_id)` en alias, precios, datáfonos, cuentas y usuario | RLS no revisa a qué apunta una llave foránea; la base debe impedir el cruce |
| H-02 | Quitar a usuarios el permiso de cambiar `plan` y `estado` | El cliente no debe poder subirse de plan ni reactivarse solo |
| H-03 | `on delete restrict` en `usuario.id` | Borrar en Auth no debe borrar la fila; se desactiva |
| H-08 | `medio_pago.tipo`: efectivo, tarjeta, transferencia, otro | Sin esto el motor no sabe qué ventana usar sin escribir códigos de una empresa |
| H-09 | Índice por `empresa_id` en `precio_producto` y `terminal_datafono` | Lo pide `docs/ARQUITECTURA.md`; hoy no lo tienen |
| H-10 | Crear `empresa_config` al crear la empresa, llenar `registro_id` y mantener `actualizado_en` | Sin esa fila los motores no tienen valores que leer |
| H-11 | Separar texto original y texto normalizado en los alias | Hoy el nombre de la columna no dice lo que guarda |

Faltan decisiones de Jacobo sobre H-05 (¿finanzas ve usuarios?), H-06 (cómo entra
soporte a cada cliente) y H-12 (¿la base impide vigencias cruzadas?).

**Paso 3 · Completar las pruebas** (Claude)
- Agregar usuarios `finanzas` y `soporte`, y más roles en la empresa B. Hoy son 3
  roles en A y 1 en B; `CLAUDE.md` exige cada rol en dos empresas (H-04).
- Agregar: `anon` no ve ni escribe, cada rol intenta borrar, nadie escribe en
  `auditoria`, una llave foránea no cruza empresas y el dueño no cambia su plan.
- Actualizar "Hecho cuando", que dice 20 pruebas: el número va a subir. Corregir
  también `tests/rls/correr.sh` para Windows (H-13).

**Paso 4 · Revisión línea por línea** (Jacobo, con Claude al lado)

| Bloque de 0001 | Qué mirar |
| --- | --- |
| 1 y 2 · Empresa, usuario, funciones | Por qué `security definer` y `search_path` vacío |
| 3 · Auditoría | Qué guarda y quién no puede tocarla |
| 4 · Maestros | Si cada columna cabe con lo que Milagros tiene de verdad |
| 5 · Índices | Que estén todos los de `empresa_id` |
| 6 · RLS | Comparar con la matriz de roles de `docs/MODELO_DATOS.md`, fila por fila |
| 7 · Triggers | Que estén las 14 tablas |

**Paso 5 · Aplicar en `tino-pruebas`** (Jacobo, o Claude si lo autoriza entonces)
- Solo después de pasos 1 a 4 y con la suite local en verde. Una sola vez, sin
  `00_supabase_simulado.sql`, que allá ya existe.
- Comprobar justo después: 15 tablas con RLS, 42 políticas, 14 triggers. Los
  números cambian si se aprueban los cambios del paso 2.
- Revisar si `authenticated` tiene TRUNCATE en Supabase (H-07) y quitarlo si lo
  tiene: RLS no aplica a TRUNCATE y el simulador local no refleja eso.

**Paso 6 · Repetir permisos en Supabase** (Jacobo y Claude)
- Crear "Prueba A" y "Prueba B" con usuarios de Auth de cada rol. No se usan datos
  de Milagros. Como nada se borra, estas empresas se quedan con `estado = 'prueba'`.
- Probar con un inicio de sesión real y la llave pública, que es el camino que
  usará el panel.
- Ojo: el editor SQL de Supabase entra como `postgres` y se salta RLS. Si Jacobo
  prueba ahí sin cambiar de rol, va a ver todo y parecerá una falla (H-41).

**Qué probar al final**
- Caso concreto: entrar con el dueño de Prueba A, consultar `punto_venta` y ver solo
  los puntos de A. Cambiar el nombre de un punto y buscar en `auditoria` esa fila
  con el antes y el después. Crear un datáfono de A con el punto de B: debe fallar.
