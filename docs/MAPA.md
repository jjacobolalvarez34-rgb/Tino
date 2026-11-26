# Mapa de Tino

Qué es cada sección, para qué sirve, quién la usa y de dónde salen sus datos. Sirve para que nada
quede repetido ni revuelto. Estado: 26 nov 2026. Lo marcado **(propuesta)** espera la aprobación de Jacobo.

## Las cinco secciones

| Sección | Para qué sirve (una frase) | Quién la usa |
|---|---|---|
| **Hoy** | Lo que necesita atención hoy, de todos los módulos, y cómo va el mes. | Dueño, encargada, líder, finanzas (cada uno ve lo suyo) |
| **Equipo** | Formar y acompañar a las personas: ciclo, registro del día, indicadores, compromisos. | Dueño, encargada, líder, responsable de punto |
| **Ventas** | Cuánto se vendió, quién y qué: ranking, metas, reportes por producto y punto. | Dueño, encargada, líder, finanzas; responsable y asesora (su punto) |
| **Caja** | Si la plata de cada punto cuadró y por qué no: cierre del día, conciliación, descuadres, datáfonos. | Dueño, encargada, finanzas; asesora y responsable (su punto) |
| **Configuración** | Lo que se pone una vez: puntos, productos, personas, usuarios, ajustes, archivos. | Dueño y soporte; la encargada y el líder lo de su área |

### Hoy
- **Pantallas:** Hoy.
- **Muestra:** compromisos vencidos, quién necesita apoyo, sesiones de la semana, el mes en números (venta, ticket, meta, ranking).
- **Datos:** `compromiso`, `seguimiento`, `sesion_formacion`, `meta_periodo`, `v_venta_asesora` (Excel del día).
- **(propuesta)** Sumarle lo urgente de Caja: días sin cerrar, descuadres sin causa clara, transferencias por confirmar. Hoy no muestra nada de Caja.

### Equipo
- **Pantallas:** Equipo (formación: lo que hay que hacer, cómo van, pasos, calendario, lista), ficha de cada persona, + Registrar (registro del día, observación, compromiso, evaluación, diagnóstico, sesión, meta), Ajustes de Equipo.
- **Datos:** `asesora`, `asesora_punto`, `registro_dia`, `indicador_dia`, `asesora_etapa`, `seguimiento`, `compromiso`, `sesion_formacion`, `equipo_catalogo`; las facturas de cada persona salen de `v_venta_asesora`.

### Ventas
- **Pantallas:** Ventas (ranking por persona o por punto, ticket, cumplimiento, Copiar como números).
- **Datos:** `v_venta_asesora` (Excel del día, venta por persona) y `meta_periodo`. Las facturas de Siigo (`venta` con `id_origen`, 0009) sirven para comparar.
- **(propuesta)** Los reportes nuevos (abajo): por producto y punto, y cumplimiento de meta de todas las asesoras.

### Caja
- **Pantallas:** Caja (un día, todos los puntos; cerrar y desbloquear), Transferencias, Sin origen, Por confirmar, Descuadres, «Lo que necesita atención».
- **Datos:** `jornada`, `reporte_caja`, `pago`, `movimiento_caja`, `movimiento_externo` (extractos, Bold, Redeban), `conciliacion`, `descuadre`, `jornada_cierre`.
- **(propuesta)** Los reportes nuevos (abajo): comisiones y retenciones de datáfonos, y el recopilado del cuadre para finanzas.

### Configuración (propuesta: hoy no existe como sección)
- **Pantallas que hoy están sueltas en «Más»:** Puntos de venta, Archivos (subir y ver la cola), Ajustes de Equipo, Usuarios.
- **Nuevas:** Productos con secciones (docs/PLAN_APP_MOVIL.md §4), Roles (docs/ROLES.md, cuando se apruebe).
- **Datos:** `punto_venta`, `producto`, `producto_alias`, `perfil_fuente`, `empresa_config`, `usuario`, `archivo_importado`, `archivo_en_cola`.

## Lo que hoy está repetido o en el lugar equivocado

| Qué | Problema | Propuesta |
|---|---|---|
| «Caja» y «Caja del día» | Caja está en el menú principal **y** otra vez en Más | Quitarla de Más |
| «Lo que necesita atención» (`/resumen`) | Es el «Inicio» de la primera versión: repite el papel de Hoy pero solo de Caja | Sus alertas pasan a Hoy; la pantalla queda dentro de Caja como «Pendientes de caja» |
| Transferencias, Sin origen, Por confirmar, Descuadres | Son partes de Caja pero están sueltas en Más | Pestañas dentro de Caja: Día · Conciliación · Descuadres |
| Archivos, Puntos, Ajustes de Equipo, Usuarios | Configuración revuelta con trabajo diario en Más | Más → Configuración, con sus pestañas |
| «Lo que hay que hacer» en Hoy y en Equipo | Las mismas frases en dos lugares | Se deja: Hoy es el resumen de todo; Equipo solo lo de formación (ya sin «próximos»). Es a propósito, no un duplicado |
| Tablero y revisión en HTML del programa de escritorio (`panel/tablero`, `panel/revision`) | Reportes viejos fuera de la web | Quedan como herramienta interna; los reportes para la dueña van en la web |
| Pantallas de la primera dirección visual (Transferencias, Descuadres, Sin origen, Archivos, Puntos) | Se ven distintas al resto | Rehacerlas con el estilo nuevo al moverlas a Caja y Configuración |

## Reportes que faltan (propuesta)

Todos con **Copiar como números** (ya existe en el componente Tabla) y **Descargar Excel** (nuevo: un
.xlsx generado en el navegador, cargando la librería solo al tocar el botón). El Excel es una salida
que Tino genera (D-068).

| Reporte | Dónde | Qué existe | Qué falta | De dónde sale cada cifra |
|---|---|---|---|---|
| **Venta por producto y por punto, por mes** | Ventas | Los datos: `venta_detalle` (cantidad, precio, valor, descuento, regalos) del Excel del día | La pantalla y una vista por mes. Resolver los 17 productos sin reconocer de Milagros (si no, quedan como «producto sin reconocer» con su nombre) | Cantidad y valor: `venta_detalle` de los Excel del día; producto: `producto` + `producto_alias` |
| **Cumplimiento de meta por asesora, TODAS siempre** | Ventas | Ranking por persona (solo quien vendió) y metas por persona | Empezar de la lista completa de `asesora` (activas e inactivas), con su venta (o 0) y su meta (o «sin meta») | Venta: `v_venta_asesora`; meta: `meta_periodo` de la persona; % = venta ÷ meta |
| **Comisiones y retenciones por punto y mes, filtro Bold o Redeban** | Caja | `movimiento_externo` guarda bruto, comisión, retenciones (sumadas) y neto por transacción de datáfono | **Separar retefuente, reteIVA y reteICA**: el lector ya las lee por separado y hoy las suma. Una migración con tres columnas, el lector y volver a cargar las liquidaciones. Datáfonos sin punto: asignarlos | Vendido = bruto; comisión, retefuente, reteIVA, reteICA y neto: **las liquidaciones de Bold y Redeban, tal cual** (Tino no calcula impuestos) |
| **Recopilado del cuadre de caja por punto y por día** | Caja | Caja muestra un día; los datos de cada día están | Un rango de fechas, una fila por punto y día, con exportación | Venta del día, efectivo contado, descuadre: `reporte_caja`; pagos por medio: `pago`; gastos, consignaciones, base: `movimiento_caja`; estado (cerrado o no): `jornada` |

**Trabajo:** venta por producto 0,5–1 sesión · cumplimiento 0,5 · comisiones y retenciones 1 (con la
migración y recargar) · recopilado del cuadre 0,5–1 · Descargar Excel 0,5 · ordenar el menú y Configuración 0,5–1.
**Total: 3,5 a 5 sesiones.**

Para ver el formato exacto de los Excel que Jacobo hacía a mano, faltan las copias en
`D:\Repositorios\Tino-datos\referencia\` (todavía no existe esa carpeta).
