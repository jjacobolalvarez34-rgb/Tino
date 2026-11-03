# 003 · Cargar Milagros como empresa 1

Paso del plan: F1 · 1.4
Estado: hecha, salvo los nombres cortos de D-032

## Objetivo
Tener a Milagros completa en el proyecto de pruebas: puntos, asesoras,
productos, alias, tipos de venta, medios de pago, datáfonos y cuentas.

## Alcance
- Script de carga desde los Sheets maestros y `mapeo_siigo`.
- Todas las asesoras, activas e inactivas.
- Alias de los nombres que aparecen en septiembre y octubre.
- Cada datáfono asignado a su punto.

## Fuera de alcance
- Importar ventas o pagos (tarea de la fase 2).
- Datos de enero a abril.

## Documentos a leer
- `docs/MODELO_DATOS.md`, `docs/GLOSARIO.md`

## Hecho cuando
- Ningún nombre de asesora de septiembre u octubre queda sin alias.
- Cada datáfono que aparece en las liquidaciones tiene punto asignado.
- Los datos están solo en `tino-pruebas`.

## Cómo lo reviso yo (Jacobo)
- Comparo la lista de asesoras con la hoja de Cumplimiento.
- Reviso 10 alias al azar.

## Notas
- Pendiente: la lista oficial de tipos de venta de Milagros.

### Avance del 2 nov 2026
- Cargador genérico en `ingesta/maestros.py`, con simulacro por defecto y 7 pruebas sin red.
- Asesoras leídas de Drive, solo lectura. Tipos de venta y bodega decididos (D-031, D-033).
- Simulacro de Milagros limpio, sin avisos. El archivo queda en
  `D:\Repositorios\Tino-datos	rabajo\maestros\`, fuera del repositorio.
- Cargada en `tino-pruebas` el 2 nov 2026 por orden de Jacobo. Verificado leyendo la base:
  conteos, códigos de asesora, configuración y auditoría. Una empresa de prueba no ve nada de
  Milagros. Correr la carga otra vez no crea nada.
- Jacobo revisó los 10 alias. Los nombres cortos sin resolver quedan por fuera a propósito
  (D-032): aparecerán como pendientes al importar.
- Caja y Kit son productos distintos: se corrigió la carga sin borrar nada. Las Cajas no
  tienen código de Siigo todavía.
- Supuesto que queda: códigos de pago vigentes desde el 1 de enero de 2026.

### Plan propuesto (2 nov 2026): espera la aprobación de Jacobo

Los códigos H-xx son los hallazgos de la entrada del 2 nov en `docs/BITACORA.md`.

No se ha tocado ningún dato real. Esta tarea no puede empezar con datos hasta que
la 002 esté hecha y Jacobo dé acceso a las fuentes.

**Lo que falta saber antes de escribir el script** (Jacobo)
- Dónde están los Sheets maestros y `mapeo_siigo`, y qué columnas tienen. No están
  documentados en el repositorio. Tampoco la "hoja de Cumplimiento".
- La lista oficial de tipos de venta, y si alguno no se factura en Siigo.
- Qué código usar para cada asesora: `asesora.codigo` es obligatorio. ¿Hay códigos
  en el Excel o los asigna el sistema? La demo muestra `A07`.
- Desde cuándo está cada datáfono en su punto: `activo_desde` es obligatorio.
  Supuesto si no se sabe: la primera fecha en que aparece en una liquidación.
- Qué hacer con dos personas distintas que aparecen con el mismo nombre en puntos
  distintos (H-11).

**Paso 1 · Decidir dónde vive lo propio de Milagros** (Jacobo, H-39)
- A · Cargador genérico en `ingesta/maestros/` que lee un formato neutro, y un
  archivo de mapeo de Milagros fuera del repositorio. Ventaja: cumple "nada
  específico de un cliente en el código" y sirve para el siguiente cliente.
  Desventaja: toma un poco más al principio.
- B · Script hecho solo para Milagros, fuera del repositorio. Ventaja: es más
  rápido. Desventaja: no se revisa en git y se rehace con cada cliente.
- Recomendado: A.

**Paso 2 · Decidir el origen de los maestros** (Jacobo, H-38)
- `CLAUDE.md` pide `archivo_id` y `fila_origen` en toda fila importada, pero
  `archivo_importado` nace en 0002 y los maestros no tienen esas columnas.
  Propuesta: los maestros son configuración y no filas importadas; su origen se
  guarda en `fuente` y en `auditoria`. Si se aprueba, se aclara la regla.

**Paso 3 · Normalizador de nombres** (Claude)
- Una sola función, que usarán también los importadores: minúsculas, sin tildes,
  sin espacios de más. Se escribe primero porque si cada proceso normaliza distinto
  los alias dejan de coincidir.
- Parecidos como "CARO M" y Carolina M. solo se sugieren. El sistema no une nombres
  por su cuenta: la lista va a Jacobo y Jacobo decide.

**Paso 4 · Cargador con simulacro** (Claude)
- Orden de carga, por dependencias: empresa, `empresa_config`, `punto_venta`,
  `medio_pago`, `tipo_venta`, `asesora`, `asesora_alias`, `producto`,
  `producto_alias`, `terminal_datafono`, `cuenta_recaudo`.
- Por qué se agregan `empresa` y `empresa_config`: la tarea no las nombra, pero sin
  ellas no hay a qué colgar nada y los motores no tienen valores.
- Quedan fuera y hay que confirmarlo: `precio_producto`, `perfil_fuente` y `usuario`.
- Modo simulacro por defecto: dice qué crearía sin escribir nada. Para escribir de
  verdad hay que pedirlo de forma explícita.
- Se puede correr dos veces sin duplicar, buscando por `(empresa_id, codigo)`.
- Usa la llave de servicio, que se salta RLS: `empresa_id` se pasa siempre explícito
  y el script se niega a correr si la URL no es la de `tino-pruebas`.
- Nada se borra: una asesora que ya no está se desactiva.

**Paso 5 · Probar sin datos reales** (Claude)
- Armar en `tests/casos/maestros/` una empresa inventada con los casos difíciles:
  mismo nombre escrito de tres formas, asesora inactiva, datáfono que cambió de
  punto y cuenta general sin punto.
- Cargarla en un Postgres local y comprobar los conteos.

**Paso 6 · Cargar Milagros en `tino-pruebas`** (solo con Jacobo presente)
- Primero el simulacro, Jacobo revisa, después la carga real. Nunca en producción.
- Los reportes de esta corrida traen nombres reales: se guardan fuera del
  repositorio.

**Paso 7 · Cierre de pendientes** (Jacobo)
- Reporte de nombres de septiembre y octubre sin alias: debe quedar en cero.
- Reporte de datáfonos de las liquidaciones sin punto: debe quedar en cero. Para esto
  hay que leer las liquidaciones solo para sacar los códigos, sin importar pagos.

**Qué probar al final**
- Caso concreto: tomar 10 alias al azar y comparar cada uno con la hoja de
  Cumplimiento. Tomar un datáfono de una liquidación de octubre y ver que apunta al
  punto correcto. Correr la carga otra vez y comprobar que no crea ninguna fila.
