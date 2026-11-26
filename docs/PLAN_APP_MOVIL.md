# App móvil sobre una sola base (plan)

Estado: **solo plan** (D-068). No hay código hasta que Jacobo lo apruebe.

## 1. La decisión

Tino tiene **una sola base de datos**. La app móvil es otra cara de esa base, como la web: los mismos
usuarios, roles, permisos, puntos, asesoras y productos. La única copia aparte es la del celular, para
trabajar sin internet, y se sincroniza con Tino. **El Excel es una salida que Tino genera, nunca una base.**

### Choque con la app vieja (hay que resolverlo con Jacobo)
La app vieja de registro de facturas («Milagros» / «Tino Lite») tiene como regla número 1 «el Excel
(Google Sheets) es la fuente oficial de verdad» y la gente (Alexandra, Irina) **edita el Excel a mano**.
La decisión nueva dice lo contrario. Mientras convivan, hay que acordar:
- Desde qué día y en qué puntos manda Tino y el Excel pasa a ser solo una salida.
- Qué pasa si alguien corrige el Excel a mano después: propuesta, ese cambio no entra solo; se anota
  en Tino como corrección con nota (así no hay dos verdades).

## 2. Qué necesita la base para la app móvil

**Usuarios:** cada persona con su propio usuario (la app vieja usa una sola cuenta compartida, así no
hay permisos por punto ni se sabe quién hizo qué). En el celular, después del primer ingreso, se
desbloquea con un PIN corto.

**Qué lee y escribe cada rol desde el celular** (todo pasa por RLS, igual que la web):

| Rol | Lee (lo guarda en el celular) | Escribe |
|---|---|---|
| Asesora | Catálogo por secciones y precios vigentes de su punto; inventario teórico y base del día; sus ventas y su meta | Del día de su punto, mientras no esté cerrado: inventario (OK o cantidad real), entradas, ventas en efectivo, descuentos y redenciones, regalos, pagos uno por uno, conteo de caja, gastos y observaciones; cerrar el día |
| Responsable de punto | Lo de la asesora + el equipo de su punto | Lo de la asesora + registro del día, observaciones, compromisos, sesiones de su punto |
| Líder | Equipo de todos los puntos | Acompañamiento y registro del día |
| Dueño, encargada | Todo (en el celular, sobre todo para mirar) | Lo mismo que en la web |

**Tablas que faltan en Tino** (hoy inventario y conteo de caja están en «fases posteriores»):
- `inventario_dia`: por punto, día y producto: inicial (teórico), real contado, OK, entradas, salidas
  Siigo, regalos, descuentos y venta en efectivo no facturada. Hace lo de `movimientos_inventario` de la app vieja.
- `conteo_caja`: billetes y monedas por denominación, sencillo recibido, ADDI. Se suma a `reporte_caja`.
- `pago` ya existe (0004): falta el subtipo (Bancolombia, Daviplata…) y el id del dispositivo.
- Para sincronizar: en cada tabla que se llena desde el celular, el `id` lo genera el celular
  (UUID), más `dispositivo_id`, `escrito_en` (hora del celular) y `recibido_en` (hora de la base).
- `sincronizacion_entrada`: copia tal cual de cada lote que llega del celular (como el `archivo_id`
  de lo importado). Así nada se pierde aunque algo se rechace.
- Una función `sincronizar(lote)` que recibe muchos cambios de una vez y responde qué entró, qué ya
  estaba y qué chocó.

## 3. Choques: dos personas cambian lo mismo sin internet

1. **Lo que se agrega nunca choca.** Pagos, entradas, gastos, observaciones, registros: cada uno trae
   su id del celular; si llega dos veces, entra una (sin duplicados), y si dos personas agregan, entran
   las dos.
2. **Lo que es un solo valor por día** (el conteo real de un producto, un campo del cuadre, el registro
   del día de una persona): si nadie lo cambió en la base desde que el celular lo leyó, entra. Si
   alguien sí lo cambió, **no se pisa**: queda como **choque** con los dos valores, quién y cuándo, y
   sale en «Lo que necesita atención» para que la encargada elija con un toque. Mientras tanto vale el
   que ya estaba en la base.
3. **Día cerrado:** si llega algo de un día ya cerrado (candado de 0014), no entra; queda como choque
   con la nota «llegó después del cierre», para desbloquear con nota o descartar.
4. **Nada se borra:** las correcciones y lo descartado quedan con su historia y en la auditoría.
5. La hora del celular puede estar mal: el orden lo pone `recibido_en`; `escrito_en` solo se muestra.

## 4. Catálogo de productos con secciones (va en Configuración)

**Qué ya sirve:** `producto` (código, código Siigo, nombre, categoría, activo), `producto_alias` (los
nombres que vienen en los reportes), y `venta_detalle` guarda el precio de cada venta (las ventas viejas
no cambian si cambia el precio).

**Qué hay que agregar:**
- `seccion_producto` (empresa, nombre, orden, activa): la crea cada empresa.
- En `producto`: `seccion_id` y `orden` dentro de su sección. La `categoria` de texto de hoy pasa a ser
  una sección (migración sin pérdida).
- `producto_precio` (producto, precio en pesos enteros, desde, hasta): sin cruces de fechas. Cambiar el
  precio cierra el anterior con su fecha.
- `producto_punto` (producto, punto, desde, hasta): **sí hace falta**. No todos los puntos tienen todo;
  la app vieja ya lo tiene, y sin esto la asesora vería productos que su punto no maneja.
- Nada se borra: producto y sección se desactivan, dejan de salir en la app y su historia queda.
- El código de Siigo y los alias se quedan como están.
- Para el celular: una «versión del catálogo» (la fecha del último cambio) para saber cuándo volver a
  bajarlo; la app lo guarda y lo muestra por secciones con buscador, sin internet.

**Pantalla:** Configuración → Productos. Buscar, ver por sección, crear, editar, ordenar (subir o bajar)
y desactivar; cambiar precio con fecha. Solo dueño y encargada (con roles configurables, el permiso
`editar_productos`).

**Trabajo:** base y pruebas 1 sesión · pantalla 1 sesión · catálogo en la app móvil con la app.

## 5. Pasar la app vieja a Tino sin perder nada

La app vieja tiene su propia base Supabase, un Apps Script y 11 Google Sheets por mes.

1. **Copia de seguridad** de la base vieja completa (como `tests/respaldo/respaldar.py`) y de los Sheets del mes.
2. **Mapa de tablas:** `puntos_venta` → `punto_venta` (por código), `productos` → `producto` +
   `producto_alias` (el `nombre_excel`), `mapeo_siigo` → `codigo_siigo` + alias, `producto_punto` →
   `producto_punto`, `reportes_diarios` → `jornada`, `cuadre_caja` → `reporte_caja` + `conteo_caja`,
   `movimientos_inventario` → `inventario_dia`, `ventas_pago_individual` → `pago`,
   `observaciones_reporte` → `observacion`. Auditoría y errores viejos: se guardan tal cual como archivo histórico.
3. **Importar como un archivo más** (fuente «app vieja»), con el id original de cada fila como
   `fila_origen`: se puede repetir sin duplicar y cada cifra dice de dónde vino.
4. **Comparar** por punto y día contra los Sheets (venta, pagos, descuadre) antes de dar nada por bueno.
5. **Convivencia por punto:** un punto piloto usa la app de Tino; los demás siguen igual. Mientras
   tanto Tino **genera** el Excel del día para quien lo siga mirando (salida, no base).
6. La base vieja queda **solo de lectura** unos meses y después se archiva.

## 6. Lo que necesito de Jacobo

1. Aprobar el plan (o cambiarlo).
2. El choque del §1: desde cuándo manda Tino y qué hacer con las correcciones hechas a mano en el Excel.
3. Acceso de lectura a la base vieja (solo para la migración y la comparación) cuando toque.
4. Las preguntas que quedaron abiertas en el traspaso: si el descuento de Leal va siempre sobre venta
   facturada, qué puntos tienen computador y cómo facturan hoy en el punto.
