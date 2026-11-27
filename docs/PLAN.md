# Plan de Tino

El plan maestro que citan los demás documentos. Escrito el 20 nov 2026 a partir de la visión, la
arquitectura, las tareas 001 a 010, las pantallas de diseño, la revisión de la dueña y lo que Jacobo
pidió ese día. Se actualiza al cerrar cada fase. Estado: ✅ hecho · 🟡 en curso · ⏳ pendiente.

## 0. Rumbo desde el 27 nov 2026 (manda sobre todo lo de abajo)

**Qué pasó:** Milagros dejó de ser cliente: compró un POS con ERP y ya no usa el Excel (D-069). Lo
construido no se pierde: nada de Tino quedó amarrado a Milagros (§1). Lo que sí cambia: Tino deja de
depender del Excel de un cliente y pasa a **ser** lo que el cliente usa todos los días.

**Tino son tres caras sobre una sola base** (D-068):

| Cara | Para quién | Dónde | Qué hace | Estado |
|---|---|---|---|---|
| **Administración** | Dueño, encargada, finanzas, líder | Web (computador y celular) | Hoy, Equipo y formación, Ventas y reportes, Caja y conciliación, Configuración | ✅ funciona (tino-pruebas); falta producción |
| **Vender** (facturas) | Asesoras en puntos con computador | Web | Vender y cobrar, facturar por el programa de facturación del cliente (D-063), inventario del día, cuadre de caja y cierre | ⏳ por construir |
| **App** | Asesoras en el celular | App instalable que funciona sin internet | Lo mismo que Vender, guardado en el celular y sincronizado con la base (docs/PLAN_APP_MOVIL.md) | ⏳ por construir |

**El Excel** deja de ser una entrada: es una salida que Tino genera (Descargar Excel, Copiar como
números). Los lectores de Excel se quedan para **traer la historia** de un cliente nuevo al empezar.

**Código y ramas:**
- Un solo repositorio y una sola base. Se sigue trabajando en `main` y se sube igual a `arranque`
  (Vercel publica desde el fork de Jacobo, que sigue `arranque`).
- **Administración y Vender en la misma web** (`web/`), separadas por grupos de rutas: lo de hoy, y
  `/vender` para el punto. Mismo inicio de sesión y mismos componentes: un cambio sirve para las dos.
- **La App** empieza como versión instalable (PWA) de `/vender`, con su copia en el celular
  (IndexedDB) y una cola que sincroniza con `sincronizar(lote)`. Si hace falta tienda de apps, se
  empaca después con Capacitor, sin reescribir. Así no hay tres códigos que mantener.
- Por qué así: una persona sola no sostiene tres proyectos distintos; con una base y una web, cada
  arreglo llega a las tres caras.

**Orden para salir a buscar clientes:**
1. **Producción lista** (lo de Jacobo: conexión de producción, variable de Vercel, Site URL de Auth) y aplicar 0012–0015.
2. **Kit de venta:** la demo con datos inventados, la portada, /precios, el instructivo y videos tutoriales de cada sección (al final de todo, pedido de Jacobo).
3. **Administración completa:** los 4 reportes de docs/MAPA.md, ordenar el menú y Configuración, catálogo de productos con secciones.
4. **Vender (web):** venta, cobro por medio de pago, inventario del día, cuadre de caja y cierre en Tino; factura por Siigo (u otro programa del cliente) cuando haya empresa de pruebas.
5. **App:** Vender instalable y sin internet, con sincronización y choques sin pisarse.
6. **Roles configurables** (docs/ROLES.md) cuando un cliente lo necesite.
7. Unificar los demás proyectos de Jacobo dentro de Tino (por ejemplo, el conciliador de Redil como un banco más, D-060).

Lo de las fases de abajo que nombra a Milagros queda como historia; vale el orden de esta sección.

## 1. El principio que manda: Tino no depende de la estructura de un cliente

Tino es un solo producto multiempresa. Cada cliente llega con sus herramientas (un Excel, un Google
Sheet, un cuaderno) y **Tino las reemplaza**; no se construye alrededor de ellas (D-061).

Por eso cada fuente de datos entra por un **adaptador** configurado en el perfil de la empresa, y la
fuente propia, a la que se quiere llevar a cada cliente, es **Tino mismo**:

| Lo que hay que saber | Fuente general (cualquier empresa) | Lo que es solo de Milagros hoy |
| --- | --- | --- |
| Qué se vendió, en qué punto y con qué medio de pago | Programa de facturación por API (Siigo, después Alegra…) | El Excel del día con su plantilla |
| Cuánto efectivo había, gastos, consignaciones, base | **Cierre del día en Tino** (formulario por punto, en el celular) ⏳ | Las celdas de caja de cada hoja del Excel |
| Quién trabajó y cuánto vendió cada persona | Cierre del día en Tino, o el vendedor de la factura si el cliente lo registra bien | La hoja DESC FACT |
| Metas | Pantalla de metas de Tino ✅ | La hoja METAS |
| Qué llegó al banco | Extracto por perfil de banco (D-040), avisos del correo ⏳ | — (Bancolombia es solo el primer perfil) |
| Qué pagaron con tarjeta | Liquidaciones de los datáfonos por perfil | — (Bold y Redeban son los primeros) |
| Tableros y seguimiento | Pantallas y **reportes de Tino** ⏳ | El "Sheet de control" en Google Sheets |

Lo propio de Milagros (su plantilla de Excel, la hoja DESC FACT, la celda de la meta, sus
encabezados mal escritos) vive en su perfil y en un lector que es **una transición**: sirve mientras
ella pasa al cierre del día en Tino. Nada nuevo se diseña a partir de esa plantilla.

**Revisión hecha el 20 nov:** el "Sheet de control" del plan original se reemplaza por reportes y
exportes de Tino (no se construye un Sheet que se llene solo). El lector del Excel del día queda como
adaptador de transición. Lo demás de este plan ya es general.

## 2. Lo que dice Siigo con datos reales (octubre 2026, solo lectura)

- 5.302 facturas, 0 anuladas, $432,7 millones. Cada una trae prefijo y centro de costo por punto,
  vendedor, ítems con bodega y medios de pago (transferencia, efectivo, débito, crédito, Addi…).
- **Venta sin facturar:** en casi todos los puntos el Excel dice más que Siigo (por ejemplo,
  $131,0 M contra $108,8 M en el punto 01). Tino puede medirla para cualquier empresa: venta del cierre
  contra venta facturada.
- **El vendedor de Siigo es el usuario de la caja del punto** (1 a 3 por punto), no la asesora: para
  ventas por persona, Siigo sirve solo si el cliente registra bien al vendedor; si no, el cierre del día.
- Hay una línea de mayoristas (prefijo MAY) que no está en el Excel de ningún punto.

**Alcance de la API de Siigo** (developers.siigo.com, 20 nov 2026):

| Recurso | Leer | Crear | Editar | Anular/borrar |
| --- | --- | --- | --- | --- |
| Facturas de venta | ✅ | ✅ | ✅ | ✅ anular y borrar; PDF y envío por correo |
| Notas crédito | ✅ | ✅ | — | — |
| Recibos de caja | ✅ | ✅ | — | — |
| Comprobantes contables | ✅ | ✅ | — | — |
| Compras, cotizaciones, documentos soporte, pagos | ✅ | ✅ | ✅ | ✅ |
| Clientes / productos | ✅ | ✅ | ✅ | productos sí |
| Informes (balance de prueba, cartera) | ✅ | — | — | — |
| Webhooks (avisos al instante de cambios) | — | suscribirse por tema | — | — |

Límite: 100 peticiones por minuto por empresa (10 en la de pruebas). `Partner-Id` es el nombre de la
aplicación (3 a 100 letras o números), no hace falta registrarlo.

**Lo que Tino hace con Siigo (D-063): leer y facturar a través de él.** La factura la emite Siigo con
la cuenta, la numeración y los impuestos del cliente. Reintentar no duplica (Idempotency-Key). Mandar
a la DIAN empieza apagado. Las pruebas, solo en una empresa de pruebas de Siigo. Siigo no acepta
facturas electrónicas con fecha anterior a hoy (importa para vender sin internet, D-064).

## 3. Fases

### Fase 1 · Dar acceso a la dueña de Milagros
| # | Qué | Estado |
| --- | --- | --- |
| 1.1 | Equipo: personas, ventas por persona, metas, acompañamiento, recorrido | ✅ (tarea 009) |
| 1.2 | Revisión de la dueña: correcciones, resolver en la web, usuarios, precios | ✅ (tarea 010) |
| 1.3 | Subir archivos desde la web por cola (D-057) | ✅ falta 0013 en Supabase |
| 1.4 | 0012 y 0013 en tino-pruebas; recargar octubre | ⏳ Jacobo aplica |
| 1.5 | Producción: migraciones, verificación, maestros, octubre, totales, respaldo probado | ⏳ llaves de Jacobo |
| 1.6 | Respaldos: Supabase Pro + copia propia cifrada fuera de GitHub (D-058) | ⏳ |
| 1.7 | **Siigo con facturas reales en Tino** (tarea 007): campo del punto = prefijo o centro de costo, traer octubre, comparar con el Excel | 🟡 leído; falta guardarlo |
| 1.8 | **Cerrar el día** (jornada abierta → cerrada → conciliada → bloqueada; desbloquear solo dueño o encargada) | ⏳ |
| 1.9 | Pantallas de caja con la dirección 2, incluida **Conciliación** completa (conciliado, por confirmar, sin pareja) | ⏳ aprobado |

### Fase 2 · Tino reemplaza las herramientas del cliente
| # | Qué | Estado |
| --- | --- | --- |
| 2.1 | **Cierre del día en Tino**: formulario por punto en el celular (efectivo contado, gastos, consignaciones, base, quién trabajó, venta sin factura). Reemplaza el Excel del día | ⏳ |
| 2.2 | Siigo como fuente de ventas y medios de pago; **venta sin facturar** por punto (cierre contra Siigo) | ⏳ |
| 2.3 | **Reportes estadísticos con gráficas**: mes por punto y por persona, ticket, cumplimiento, medios de pago, comparación con el período anterior, descuadres y sus causas, transferencias. Descargar en **PDF** (con gráficas) y **Excel**; enviar por correo cada semana o mes | ⏳ |
| 2.4 | Facturas en la web (lista, filtros, anuladas, por punto y vendedor) | ⏳ |
| 2.5 | Ventas con tarjeta en la web (hoy solo en el .exe) | ⏳ |
| 2.6 | Comisiones y retenciones por punto, de las liquidaciones | ⏳ |
| 2.7 | **Alertas**: descuadres grandes y transferencias sospechosas, por correo o WhatsApp | ⏳ |
| 2.8 | **Avisos de transferencia del correo**: verificar en minutos (lector de correos, con autorización escrita del cliente) | ⏳ |
| 2.9 | Comprobante de transferencia (foto) contra el aviso | ⏳ |
| 2.10 | Auditoría visible: quién cambió qué y cuándo (dueño y soporte) | ⏳ |
| 2.11 | **Facturar desde Tino a través de Siigo** (D-063): armar la factura, mandarla sin duplicar, pantalla de venta en el celular | 🟡 motor y 13 pruebas listos; falta la empresa de pruebas de Siigo |
| 2.12 | **Vender sin internet** (D-064): venta guardada en el celular con id único, se manda al volver la señal; si Siigo está caído, espera en la base de Tino | ⏳ (después de 2.11; contingencia DIAN con el contador) |

### Fase 3 · Configurar un cliente sin depender de Claude
| # | Qué | Estado |
| --- | --- | --- |
| 3.1 | Crear una empresa nueva desde Tino (soporte) | ⏳ |
| 3.2 | Pantalla de **perfiles de fuente**: qué columna es qué, qué banco, qué campo de Siigo dice el punto | ⏳ |
| 3.3 | Datos fijos en la web: productos, datáfonos, códigos de pago, cuentas | ⏳ (puntos, personas y usuarios ✅) |
| 3.4 | **Más bancos** (D-060): Banco de Bogotá y Coopcentral, con lo aprendido en Redil | ⏳ |
| 3.5 | Otros programas de facturación (Alegra, World Office, Loggro) con la misma salida | ⏳ |
| 3.6 | Siigo automático: traer cada día solo, o al instante con webhooks | ⏳ |
| 3.7 | Correo propio para invitar (SMTP) y dominio | ⏳ Jacobo |

### Fase 4 · Calidad y reglas
| # | Qué | Estado |
| --- | --- | --- |
| 4.1 | Tarea 004: confirmar los valores ⚑ y 10 casos de control escritos a mano por Jacobo | ⏳ Jacobo, con preguntas de Claude |
| 4.2 | Tarea 003: alias pendientes y nombres cortos (D-032) | 🟡 se resuelven en la web |
| 4.3 | Archivos reales anonimizados en `tests/casos/` para cada lector | ⏳ |
| 4.4 | Tarea 001: comprobar que el conciliador del repositorio da lo mismo que antes; marcar 001 y 008 | ⏳ |

### Fase 5 · Lo que el plan ya preveía para después
| # | Qué |
| --- | --- |
| 5.1 | Inventario y costos (entradas, traslados, conteos) y con eso la **ganancia real** |
| 5.2 | Horarios de las personas |
| 5.3 | App de asesoras (cierre del día, registrar factura) y **sin internet** (rama aparte, al final) |
| 5.4 | Modo oscuro |
| 5.5 | Un usuario en varias empresas (P-002), por ejemplo un contador |
| 5.6 | Conciliación contable (auxiliar contra extracto), el problema de Redil, como módulo aparte |
| 5.7 | Indicadores comerciales por asesora (atención, fidelización, referidos): espera conversación con la dueña |

### Negocio (no es código)
- Datos personales (Ley 1581): autorización y aviso de privacidad por cliente y sus trabajadores;
  contrato que diga qué puede ver soporte. Revisión de un abogado.
- IVA en los precios (pendiente de Jacobo), dirección web de Mamut Herd, 5 clientes fundadores.
- Vercel Pro con la primera venta (D-059).

## 4. Orden recomendado para seguir (reemplazado por §0 el 27 nov 2026)
1. 1.4 y 1.5 (en cuanto Jacobo aplique 0012/0013 y ponga las llaves).
2. 1.7 Siigo real guardado en Tino, y 2.2 venta sin facturar.
3. 1.8 Cerrar el día y 1.9 pantallas de caja con Conciliación.
4. 2.3 Reportes con gráficas.
5. 2.1 Cierre del día en Tino (el paso que suelta el Excel).
6. 2.7 Alertas y 2.8 avisos del correo.
7. Fase 3, empezando por 3.2 perfiles y 3.4 más bancos.
