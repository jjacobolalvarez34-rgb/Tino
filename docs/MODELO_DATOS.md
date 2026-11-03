# Modelo de datos

39 tablas en 7 módulos, en Supabase (Postgres). Este documento dice qué guarda
cada tabla y por qué. El SQL exacto está en `db/migrations/`.

## Principios

1. **Toda tabla de datos lleva `empresa_id`.** RLS impide que una empresa vea o
   toque datos de otra.
2. **Dinero en `bigint`**, pesos enteros. Nunca decimales.
3. **Nada se borra.** Las tablas tienen `activo`, `estado` o `anulado`; no hay
   política de DELETE para usuarios.
4. **Todo dato importado sabe de dónde salió:** `archivo_id` y `fila_origen`.
5. **Todo cambio queda en `auditoria`:** quién, cuándo, antes y después.
6. **Códigos únicos por empresa**, no globales: dos empresas pueden tener un
   punto `P01`.
7. **Lo que cambia con el tiempo tiene vigencia** (`vigente_desde`,
   `vigente_hasta`): precios, costos, datáfonos.

## Relaciones

### A · Empresa, maestros y operación diaria

```mermaid
erDiagram
  empresa ||--o{ punto_venta : tiene
  empresa ||--o{ usuario : "da acceso a"
  empresa ||--o{ perfil_fuente : configura
  punto_venta ||--o{ jornada : tiene
  jornada ||--o{ turno : registra
  asesora ||--o{ turno : trabaja
  jornada ||--o{ venta : contiene
  asesora ||--o{ venta : vende
  tipo_venta ||--o{ venta : clasifica
  venta ||--o{ venta_detalle : incluye
  producto ||--o{ venta_detalle : "aparece en"
  jornada ||--o{ pago : recibe
  venta |o--o{ pago : "se paga con"
  medio_pago ||--o{ pago : "por medio de"
  jornada ||--o{ movimiento_caja : registra
  jornada ||--o{ observacion : anota
  asesora ||--o{ asesora_alias : "se escribe como"
  producto ||--o{ producto_alias : "se escribe como"
  producto ||--o{ precio_producto : precio
  producto ||--o{ costo_producto : costo
```

### B · Importación, conciliación, transferencias y descuadres

```mermaid
erDiagram
  perfil_fuente ||--o{ archivo_importado : "se lee con"
  archivo_importado ||--o{ movimiento_externo : origina
  archivo_importado ||--o{ venta : origina
  archivo_importado ||--o{ error_importacion : reporta
  punto_venta ||--o{ terminal_datafono : usa
  punto_venta |o--o{ cuenta_recaudo : "recauda en"
  punto_venta ||--o{ codigo_recaudo : "se reconoce por"
  terminal_datafono |o--o{ movimiento_externo : procesa
  cuenta_recaudo |o--o{ movimiento_externo : recibe
  pago ||--o{ conciliacion : "se cruza"
  movimiento_externo ||--o{ conciliacion : cubre
  pago ||--o| verificacion_transferencia : "se verifica"
  movimiento_externo |o--o{ verificacion_transferencia : "aviso o extracto"
  jornada ||--o{ descuadre : presenta
  causa_descuadre ||--o{ descuadre : explica
  descuadre ||--o{ descuadre_evidencia : "se sustenta"
```

### C · Inventario, personal y seguridad (fases posteriores)

```mermaid
erDiagram
  punto_venta ||--o{ movimiento_inventario : almacena
  producto ||--o{ movimiento_inventario : mueve
  punto_venta ||--o{ traslado : "origen y destino"
  traslado ||--|{ traslado_detalle : lleva
  punto_venta ||--o{ conteo_fisico : cuenta
  conteo_fisico ||--|{ conteo_detalle : registra
  asesora ||--o{ horario : programada
  punto_venta ||--o{ meta : tiene
  asesora |o--o| usuario : "entra como"
  usuario ||--o{ auditoria : "hace cambios"
```

## Tablas por módulo

La columna "Migración" dice en qué archivo nace cada tabla. Las que aún no existen
se corrieron un número con 0002: el plan de abajo manda.

### Empresa y seguridad

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `empresa` | Cada negocio cliente. Todo cuelga de aquí. | 0001 |
| `empresa_config` | Los valores ⚑ de `docs/REGLAS/` por empresa: ventanas de hora, tolerancias, umbral de descuadre. | 0001 |
| `usuario` | Quién entra, a qué empresa y con qué rol. Mismo id que `auth.users`. | 0001 |
| `auditoria` | Registro automático de cada cambio: tabla, acción, antes, después, quién. | 0001 |

### Maestros

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `punto_venta` | Los puntos y la bodega. Tipo: detal, mayorista o bodega. | 0001 |
| `asesora` | Todas las asesoras, activas o no. Nunca se borran. Si no llega código, la base asigna el siguiente (A001). | 0001 y 0002 |
| `asesora_alias` | Cada forma en que aparece escrito un nombre en un punto: el texto tal cual y el normalizado, que calcula la base. | 0001 y 0002 |
| `producto` | Catálogo con código propio y código de Siigo. | 0001 |
| `producto_alias` | Nombres de producto tal como vienen en los reportes, con su forma normalizada. | 0001 |
| `tipo_venta` | Tipos de venta configurables por empresa (detal, mayor, etc.). | 0001 |
| `precio_producto` | Precio de lista con vigencia, sin vigencias cruzadas. Permite medir descuentos. | 0001 |
| `medio_pago` | Efectivo, Bold, Redeban, transferencia… por empresa, cada uno con su tipo: efectivo, tarjeta, transferencia u otro. | 0001 |
| `terminal_datafono` | Cada datáfono y a qué punto pertenece, con vigencia. | 0001 |
| `cuenta_recaudo` | Cuentas donde llegan transferencias (solo últimos 4 dígitos). | 0001 |
| `codigo_recaudo` | Código de QR o llave de cada punto, con vigencia. Dice de qué punto es un pago cuando varios comparten cuenta. | 0001 |
| `costo_producto` | Costo con vigencia. Necesario para ganancia real. | Fase 2 |

### Importación

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `perfil_fuente` | Cómo leer los reportes de cada empresa: mapeo de columnas. | 0001 |
| `archivo_importado` | Cada archivo que entra; `hash` único evita duplicar plata. | 0002 |
| `error_importacion` | Filas que no se pudieron leer y nombres sin reconocer. | 0002 |

### Operación diaria

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `jornada` | Un día de un punto. Único por punto y fecha. Estados: abierta, cerrada, conciliada, bloqueada. | 0003 |
| `turno` | Quién trabajó realmente ese día. | 0003 |
| `venta` | Cada venta, o el total por asesora si el reporte no trae detalle (D-013). | 0003 |
| `venta_detalle` | Productos de cada venta, con precio de lista y precio cobrado. | 0003 |
| `pago` | Cómo se pagó: por venta o agregado del día por medio de pago. | 0003 |
| `movimiento_caja` | Gastos, consignaciones y retiros del punto. | 0003 |
| `observacion` | Notas del día. | 0003 |
| `meta` | Meta diaria por punto o por asesora. | 0003 |

### Bancos y conciliación

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `movimiento_externo` | Lo que realmente llegó: extracto, Bold, Redeban o aviso, con comisión y retenciones. | 0004 |
| `conciliacion` | Puente entre pagos y movimientos. Estados: propuesta, confirmada, rechazada. | 0004 |
| `verificacion_transferencia` | Comprobante, aviso y extracto de cada transferencia. Hash del comprobante único. | 0004 |

### Descuadres

| Tabla | Para qué | Migración |
| --- | --- | --- |
| `causa_descuadre` | Catálogo de causas, incluida "sin causa clara". | 0005 |
| `descuadre` | Diferencia esperada contra reportada, con causa, confianza y estado. | 0005 |
| `descuadre_evidencia` | Las pruebas de cada causa. | 0005 |

### Inventario y personal (fases posteriores)

| Tabla | Para qué |
| --- | --- |
| `movimiento_inventario` | Entradas y salidas. Las existencias son la suma; nada se edita. |
| `traslado`, `traslado_detalle` | Surtido entre bodega y puntos. |
| `conteo_fisico`, `conteo_detalle` | Conteos contra lo que dice el sistema. |
| `horario` | Horarios planeados y rotaciones. |

## Roles y permisos

| Acción | Dueño | Encargada | Finanzas | Asesora | Soporte |
| --- | --- | --- | --- | --- | --- |
| Ver datos de su empresa | Todo | Todo | Todo | Su punto y maestros | Todo |
| Ver la lista de usuarios | Sí | Sí | No | No | Sí |
| Editar maestros | Sí | Sí | No | No | Sí |
| Configurar perfiles de fuente | Sí | No | No | No | Sí |
| Subir archivos | Sí | Sí | Sí | No | Sí |
| Confirmar conciliaciones | Sí | Sí | Sí | No | Sí |
| Resolver descuadres | Sí | Sí | Sí | No | Sí |
| Cerrar el día | Sí | Sí | No | Su punto | No |
| Desbloquear un día cerrado | Sí | Sí | No | No | No |
| Ver auditoría | Sí | No | No | No | Sí |
| Gestionar usuarios | Sí | No | No | No | Sí |

"Soporte" es el proveedor del sistema (Jacobo). Su acceso a los datos de cada
cliente debe quedar autorizado en el contrato.

Las reglas se implementan con dos funciones de la base:
- `app.empresa_actual()`: la empresa del usuario que hace la consulta.
- `app.rol_actual()`: su rol.

## Plan de migraciones

| Archivo | Contenido | Paso del plan |
| --- | --- | --- |
| `0001_cimientos.sql` | Empresas, configuración, usuarios, permisos, auditoría, maestros y perfiles de fuente | 1.2 y 1.3 |
| `0002_asesoras.sql` | Código automático de asesora y alias por punto | 1.4 |
| `0003_importacion.sql` | Archivos importados y errores | 2.1 |
| `0004_operacion_diaria.sql` | Jornadas, ventas, pagos, caja, observaciones y metas | 2.2 |
| `0005_bancos_conciliacion.sql` | Movimientos externos, conciliación y verificación de transferencias | 3.1 y 3.2 |
| `0006_descuadres.sql` | Causas, descuadres y evidencia | 3.3 |
| `0007_vistas_panel.sql` | Vistas `v_*` para el panel y para copiar a Excel | 4.1 |
| Siguientes | Costos, inventario y personal, cuando los clientes los pidan | Fases posteriores |

## Cómo se prueba la separación entre empresas

Antes de aplicar cualquier migración con permisos:

1. Crear dos empresas de prueba, A y B, con un usuario de cada rol.
2. Con un usuario de A, intentar leer, crear y cambiar datos de B. Todo debe
   fallar o volver vacío.
3. Con una asesora, intentar editar maestros. Debe fallar.
4. Con cualquier usuario, intentar borrar una fila. Debe fallar.
5. Cambiar un dato y comprobar que aparece en `auditoria`.

## Preguntas abiertas

- ¿Un usuario puede pertenecer a varias empresas? Ver P-002.
- Cuántos días guarda la app nativa en cada celular. Se decide en la fase de la
  app.
