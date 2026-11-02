# Módulo nuevo para Suite Irina: "Cierre del día" (detector de descuadres y control de riesgo)

## Contexto

Suite Irina (este repo) es una app de escritorio en Python + pywebview con tres módulos:
Bold/Redeban (`core.py`, `verify.py`), Transferencias (`transferencias_core.py`) e
Historial (`historial_db.py`). `bridge.py` conecta la interfaz `webui/` con los motores.

La empresa tiene **11 puntos de venta**. Cada punto lleva un Google Sheet por mes
(ej. "01. Plaza Imperial Agosto/26") con **una hoja por día** (`01`…`31`) y una hoja
resumen `DESC  FACT` (ojo: dos espacios). **El Excel es la fuente de verdad de los
ingresos.** Siigo se usa solo para facturar por temas legales: no registra descuentos
y no se usa para validar valores, solo unidades.

Hoy los descuadres se buscan a mano. Quiero un módulo que **cada mañana revise el día
anterior de los 11 puntos**, explique cada descuadre con causas probables, y lleve un
control acumulado por punto y por asesora para detectar patrones de posible robo.

## Reglas de trabajo

- **No modifiques** `core.py`, `verify.py` ni `transferencias_core.py`. Puedes
  importarlos y reutilizar funciones (en especial `extraer_transacciones` y `PUNTOS`
  de `transferencias_core.py`).
- **No reutilices el Historial actual**: el usuario lo encuentra desordenado y difícil
  de entender. Este módulo tiene su propio historial (ver abajo), pensado para
  responder preguntas concretas.
- Sigue el patrón existente: lógica en un motor nuevo (`cierre_core.py` + subcarpeta
  si crece), métodos en `bridge.py`, pantalla nueva en `webui/` con el mismo estilo.
- Antes de programar, lee el repo y propón un plan corto. Trabaja **por fases** y
  muéstrame cada fase funcionando antes de seguir.
- Todo umbral (tolerancias, montos mínimos) va en un archivo de configuración, no en
  el código.

## Arquitectura: "día normalizado"

El detector **no** trabaja sobre celdas. Un lector convierte cada hoja de día en una
estructura neutral, y las reglas trabajan sobre esa estructura. Así, cuando la app
móvil Milagros (Supabase) reemplace el Excel, solo cambia el lector.

```
DiaPunto:
  fecha, punto, asesoras[]
  productos[]: nombre, precio, inv_inicial, entradas, salidas_siigo (F),
               efectivo_cant (L), efectivo_desc_unit (M), salidas_tot (G),
               inv_final (E), valor (H), regalos_cant (I), regalos_valor (J),
               descuento (K), efectivo_total (N)
  pagos: transferencias[] (lista col S), debito[] (T), credito[] (U)
  caja: efectivo_contado, addi, consignacion, tarjetas, transferencias, gastos,
        descuentos, descuentos_idunn, regalos, regalos_idunn, danados,
        devoluciones, cambios, efectivo_apartado, base, sencillo_recibido,
        total, descuadre, cantidad_facturas, valor_teorico (H176)
  observaciones[] (texto libre)
  formulas: dict celda -> fórmula (para la regla de integridad)
```

### Lectores

1. **Google Sheets (principal)**: Drive API + Sheets API con permisos de **solo
   lectura**. Pedir valores (`UNFORMATTED_VALUE`) **y** fórmulas (`FORMULA`) de la
   hoja del día, de la hoja del día anterior y de `DESC  FACT`.
   - **Estructura en Drive**: una carpeta compartida con el usuario llamada
     "cierres 2026". Dentro hay una subcarpeta por mes (nombres tipo
     "cierres agosto", "cierres octubre"; el formato exacto puede variar). Dentro de
     cada mes hay **un Sheet por punto de venta** y **un Sheet aparte que empieza por
     un número y luego dice "transferencias"**, donde se lleva el control de
     transferencias.
   - **Autenticación**: la carpeta *se la compartieron* al usuario (no es dueño), así
     que probablemente no pueda compartirla con una cuenta de servicio. Usa **OAuth
     con la cuenta de Google del usuario** (scopes `drive.readonly` y
     `spreadsheets.readonly`), con el token guardado localmente para no pedir login
     cada día.
   - **Detección automática**: buscar "cierres 2026" → la subcarpeta del mes de la
     fecha revisada (comparar sin tildes ni mayúsculas, aceptando variaciones del
     nombre) → asignar cada Sheet a su punto por el nombre del archivo. Mostrar el
     resultado de la asignación en una pantalla de configuración para confirmarlo o
     corregirlo a mano, y recordarlo por mes. Si falta un punto o un nombre no se
     reconoce, avisar en vez de fallar.
   - **Sheet de transferencias**: identificarlo y no confundirlo con un punto.
     **Pendiente de revisar con el usuario** su estructura antes de usarlo; puede
     servir como fuente adicional para R30.
   - Pídeme permiso y guíame paso a paso antes de crear credenciales de Google.
2. **Archivo .xlsx (respaldo y pruebas)**: mismo resultado leyendo un archivo
   descargado con openpyxl (fórmulas + `data_only=True`). Úsalo para desarrollar con
   el archivo de prueba de agosto.

### Estructura de la hoja de día (referencia: hoja `10` del archivo de agosto)

- **Ubicar columnas por el texto del encabezado (fila 7)**, nunca por letra. La hoja
  `17` tiene una columna extra insertada y todo está corrido una posición.
- Productos: desde la fila 8 hasta antes de la fila de totales (176 en la plantilla).
  Fórmulas de la plantilla: `C = E del día anterior`, `G = F + L`, `E = C + D − G`,
  `H = B × G`, `J = B × I`, `N = L × (B − M)`.
- Listas de pagos: columnas con encabezado "Transferencias", "Tarjeta Debito",
  "Tarjeta Credito", sumadas en la fila 176.
- Bloque de caja: filas ~176–207. Ubicar cada concepto por su etiqueta en la columna
  A y verificar contra la plantilla. Referencia hoja `10`: H176 valor teórico,
  B189 efectivo contado, B191 ADDI, B192 consignación, B193 tarjetas, B194
  transferencias, B195 gastos, B196 descuentos (= K176 − B197), B197 descuentos Idunn,
  B198 regalos, B199 regalos Idunn, B200 dañados, B201 devoluciones, B202 cambios,
  B203 efectivo apartado (= N176), B204 base (= B189 día anterior + H179), H179
  sencillo recibido, B205 total, B206 descuadre (= B205 − H176), B207 cantidad de
  facturas. Observaciones en la columna H de ese bloque.
- **Signo**: descuadre negativo = falta plata; positivo = sobra.
- Columnas D/E/F del bloque ("Cuadre caja Siigo") comparan medios de pago contra
  Siigo y no entran al descuadre.
- Columnas de impuestos (W, X, Z…) tienen `#REF!` hasta el día 21: ignorarlas.
- Dañados, devoluciones y préstamos entre puntos: se anotan como salida en F y su
  valor en B200–B202; el producto y la cantidad solo aparecen en observaciones
  (ej. "se envía a bodega 6 shampoo de cebolla en mal estado"). Con eso cuadra.
- Los regalos se facturan en Siigo a $1, por eso aparecen en F.
- Asesoras: ubicar la etiqueta en el encabezado (filas 1–6) y cruzar con la columna
  de asesora de `DESC  FACT`.

## Fuentes externas (opcionales; el módulo funciona sin ellas)

**Siigo — "Ventas por vendedor por producto" (.xlsx)**
- Encabezado en la fila que contiene "Nombre vendedor" (no siempre es la misma).
- Rango de fechas en el encabezado: verificar que sea exactamente el día revisado y
  avisar si no.
- Un solo archivo trae los 11 puntos; "Nombre vendedor" es el punto. Mapeo
  configurable: C.C Plaza Imperial, CC Salitre Plaza, CC Altavista, Punto Kennedy,
  CC Santa Fé, CC Plaza Claro, Portal Dorado, Portal Suba, Portal Americas,
  Jumbo Autop Sur (**confirmar con el usuario si es P SUR**), Portal Banderas.
  Ignorar "CATALIMA MOU S.A.S" y las filas de total o "Procesado en".
- **Comparar solo unidades** ("Cantidad vendida") contra F. Algunos códigos agrupan
  varias filas del Excel (ej. "Empaque Milagros" = Empaque 3 + Empaque 4; "Sachet
  Obsequio" = todos los sachets): mapeo producto Excel ↔ código Siigo configurable,
  sumando cuando aplique.

**Bancolombia — PDF de movimientos**
- Reutilizar `transferencias_core.extraer_transacciones` (identifica el punto por los
  últimos 4 dígitos de la referencia y separa lo no identificado).
- Una sola cuenta para todos los puntos. El extracto trae fecha pero no hora.

**Bold / Redeban**
- Fase posterior: reutilizar `core.py` para obtener transacciones por punto y día, y
  cruzar contra las listas de tarjeta débito y crédito del Excel.

## Reglas del detector

Cada regla produce **hallazgos** con: punto, fecha, regla, severidad, monto
explicado, texto claro en español y evidencia (celdas, filas del banco, líneas de
Siigo). El panel ordena las causas por cuánto del descuadre explican.

### Nivel 1: solo el Excel
- **R01 Integridad de fórmulas**: comparar contra la plantilla, normalizando la
  referencia al día anterior. Reportar fórmulas faltantes, valores escritos a mano
  donde debe ir fórmula y referencias corridas.
- **R02 Continuidad**: inventario inicial = inventario final del día anterior por
  producto; base = efectivo contado del día anterior + sencillo; fecha de la hoja
  coherente con el nombre; el día 1 se marca como "base e inventario manuales, revisar
  contra el cierre del mes anterior".
- **R03 Compensación**: descuadres de signo contrario y monto parecido en días
  seguidos del mismo punto. Típico de un error de conteo o de base.
- **R04 Billete**: descuadre igual a una denominación (2.000, 5.000, 10.000, 20.000,
  50.000, 100.000) o múltiplo de ella.
- **R05 Combinación de precios**: descuadre igual a la suma de 1 a 3 precios de
  productos del punto. Si es positivo, sugerir efectivo apartado sin anotar; si es
  negativo, facturación de unidades o regalo.
- **R06 Regalos**: unidades en I mayores que las salidas en F.
- **R07 Observaciones sin valor**: texto con "dañado", "cambio", "devolución",
  "presta" o "bodega" y B200–B202 vacíos, o al revés.
- **R08 Valores de ajustes**: dañados, devoluciones o cambios que no son múltiplo del
  precio de ningún producto mencionado en observaciones.
- **R09 Descuentos**: descuento sin observación, o descuento por unidad en M (hoy la
  plantilla no lo suma a caja: genera descuadre de −L×M).
- **R10 Errores conocidos de plantilla**: regalos Idunn contados doble (B198 = J176
  ya incluye J101:J107 y B199 los vuelve a sumar); productos fuera del rango de la
  suma H176.
- **R11 DESC FACT**: cada fila debe apuntar a la hoja de su día (agosto tenía el día 4
  mezclando `'04 antiguo'` y `'04'`); falta cantidad de facturas; saldo de efectivo
  sin facturar que crece sin entregas.

### Nivel 2: con Siigo
- **R20 Unidades**: por producto, F del Excel menos unidades de Siigo, descontando
  dañados y devoluciones de observaciones cuando se puedan leer. Diferencia × precio =
  impacto. **Revisar también los días que cuadran**: una venta facturada en Siigo que
  no está en el Excel, y cuya plata no está, deja el descuadre en 0.

### Nivel 3: con Bancolombia (y luego Bold/Redeban)
- **R30 Transferencias**: comparar la lista S del punto contra los pagos del banco
  con su referencia, contando cuántas veces aparece cada monto en cada lado. Si algo
  no aparece, buscar en el día anterior y el siguiente antes de reportarlo. Reportar
  anotadas no recibidas, recibidas no anotadas y posibles montos mal digitados.
- **R31 Referencias**: pagos con referencia desconocida el mismo día que un punto
  queda sin transferencias → avisar posible cambio de código de QR.
- **R32 Consignaciones**: consignación del Excel contra las consignaciones del
  extracto.
- **R33 Tarjetas** (fase Bold/Redeban): total y lista por punto y día contra T/U.

## Señales de riesgo (control de robo)

Separar **descuadre** (la plata no cuadra) de **señal** (algo para revisar aunque
cuadre). El texto siempre dice "revisar", nunca acusa.

- Transferencia anotada en el Excel que no llegó al banco.
- Unidades facturadas en Siigo que no están en el Excel.
- Faltantes sin explicar repetidos con la misma asesora.
- Descuentos, regalos, dañados o devoluciones por encima del promedio del punto o de
  la asesora.
- Efectivo apartado acumulándose sin entregas.

## Historial nuevo (claro y ordenado)

SQLite propio, en la misma carpeta de datos que la Suite (`%APPDATA%\SuiteIrina\`),
archivo separado `cierre.db`. Revisar un día otra vez **reemplaza** el resultado
anterior de ese día y punto (no duplica).

Tablas sugeridas:
- `dias`: fecha, punto, asesoras, venta, descuadre, monto_explicado,
  monto_sin_explicar, estado (cuadra / explicado / sin explicar), fuentes usadas.
- `hallazgos`: fecha, punto, regla, severidad, monto, texto, evidencia (JSON),
  revision (pendiente / revisado / error confirmado / descartado), nota, fecha de
  revisión.
- `asesoras_dia`: fecha, punto, asesora.

Pantallas, cada una responde una pregunta:
1. **Hoy** ("¿qué pasó ayer?"): 11 filas, una por punto, con asesoras, venta,
   descuadre, estado con color y la causa principal. Clic → detalle con todos los
   hallazgos y su evidencia. Cada hallazgo se puede marcar como revisado con una nota.
2. **Punto** ("¿cómo va este punto?"): calendario del mes con cada día coloreado por
   estado y totales del mes.
3. **Asesora** ("¿cómo va esta persona?"): días trabajados, descuadres sin explicar
   (cantidad y monto), señales de riesgo y hallazgos pendientes, por mes.
4. **Pendientes**: hallazgos sin revisar, del más antiguo al más reciente.

Nada de gráficos que no respondan una de estas preguntas.

## Flujo diario esperado

1. Por la mañana, descargar el extracto de Bancolombia y el reporte de Siigo del día
   anterior (uno de cada uno para todos los puntos).
2. Abrir "Cierre del día", elegir la fecha, cargar los archivos y dar "Revisar".
3. La Suite lee los 11 Sheets, aplica las reglas con las fuentes disponibles y
   muestra la pantalla Hoy en pocos minutos.

## Fases

1. Lector .xlsx + día normalizado + reglas de nivel 1 + pantalla Hoy, probado con el
   archivo de agosto de Plaza Imperial.
2. Historial nuevo y pantallas Punto, Asesora y Pendientes.
3. Siigo (R20).
4. Bancolombia (R30–R32) reutilizando `transferencias_core`.
5. Lector de Google Sheets: OAuth, detección de la carpeta del mes y asignación de
   los 11 Sheets a sus puntos.
6. Bold/Redeban (R33).

## Pruebas de aceptación con el archivo de agosto (Plaza Imperial)

- Días 21 (+30.100) y 22 (−29.450), y 26 (+26.050) y 27 (−21.100): R03 compensación.
- Día 01 descuadre 2.000: R04 billete.
- Hoja 04 con fecha 3/8/2026: R02.
- `DESC  FACT` fila del día 4 leyendo `'04 antiguo'`: R11.
- Días 05 y 06: base sin `+H179`: R01.
- Día 13, filas 57–78: G y N apuntan a L dos filas abajo: R01.
- Hojas 05 y 06: Bio Advance (fila 26) sin fórmulas: R01.
- Regalos Idunn contados doble en la plantilla: R10.
- Día 14: devolución de 6 shampoo de cebolla con descuadre 0 → **no** debe generar
  falso positivo.
- Día 17: la columna extra no debe romper la lectura.
- Días 25 (+220.200) y 15: deben salir con causas probables o como "sin explicar",
  nunca con error de lectura.
