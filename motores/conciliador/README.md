# Suite Irina

Un solo programa con cuatro módulos:
1. **Bold / Redeban** — conciliador de reportes, con verificación contra Bancolombia.
2. **Transferencias por punto de venta** — extrae PAGO QR / PAGO LLAVE de los PDF de
   Bancolombia y arma el Excel por punto de venta.
3. **Cierre del día** — revisa el cierre de un día de los 11 puntos, encuentra los
   descuadres y explica sus causas probables con evidencia (ver abajo).
4. **Historial & diferencias** — cada vez que verificas contra Bancolombia, el
   resultado queda guardado; el panel te muestra cuántas transferencias fallaron
   (por punto de venta, Bold y Redeban por separado), cuántas veces no coincidió
   el banco con lo esperado, y la diferencia acumulada entre el total esperado y
   lo que no coincidió.

Al abrir, una pantalla de carga animada cubre los segundos en que se cargan los
motores (lectores de Excel y PDF, en segundo plano mientras arranca la ventana) y
se desvanece en 3 s cuando todo está listo.

## Instalación (modo desarrollo)
```
pip install -r requirements.txt
python main.py
```
Se abre una ventana nativa (no un navegador) con la interfaz. Usa la barra
lateral para moverte entre Inicio, Bold/Redeban, Transferencias e Historial.

## Empacar como app instalable (.exe)
```
pip install pyinstaller
pyinstaller --noconfirm SuiteIrina.spec
```
(`SuiteIrina.spec` ya incluye `webui/`, `cierre_config.json`, `mapeo_siigo.xlsx`
y los motores que `bridge.py` carga en segundo plano.)

El programa queda como **carpeta**: `dist/SuiteIrina/SuiteIrina.exe` (~150 MB en
total). Hay que llevar la carpeta completa; para abrirlo cómodo, crea un acceso
directo a `SuiteIrina.exe` en el Escritorio. Antes era un solo `.exe`, pero ese
formato descomprimía ~400 MB en `C:\...\Temp` en cada arranque: tardaba casi un
minuto y fallaba si el disco C: estaba lleno. En carpeta abre en unos segundos.
No necesita Python instalado. Los datos (`historial.db`, `cierre.db`, la caché y
la configuración propia) viven en `%APPDATA%\SuiteIrina\`, fuera de la carpeta del
programa, así que sobreviven a reinstalaciones o a mover/borrar el programa.

## Estructura del proyecto
```
main.py                    <- punto de entrada (ejecuta esto en desarrollo)
bridge.py                   <- API expuesta a la interfaz web (pywebview)
historial_db.py              <- registro histórico de verificaciones (SQLite)
core.py                      <- módulo Bold/Redeban (motor: lectura, tablas, fórmulas)
verify.py                    <- módulo Bold/Redeban (verificación contra Bancolombia)
transferencias_core.py       <- módulo Transferencias (motor de extracción/emparejamiento)
cierre_core.py               <- módulo Cierre del día (fachada: carga, revisar, estado)
cierre_config.json           <- umbrales, palabras clave y los 11 puntos (valores de fábrica)
cierre/                      <- motor de Cierre del día
  modelo.py                    "día normalizado" (DiaPunto) y Hallazgo
  lector_xlsx.py               Excel del punto -> DiaPunto (ubica todo por texto)
  formulas.py, plantilla.py    normaliza fórmulas y deduce la plantilla del mes
  reglas_n1.py                 reglas R01-R11 (solo el Excel)
  siigo.py                     mapeo Excel ↔ Siigo, kits y lector del reporte de Siigo
  reglas_n2.py                 R20 (unidades contra Siigo)
  banco.py                     lo que llegó al banco: PDF de Bancolombia o Sheet de transferencias
  lector_sheets.py             Google Sheets: conexión de solo lectura, carpetas y lectura
  tarjetas.py                  Bold/Redeban por punto y día (reutiliza core.py)
  reglas_n3.py                 R30-R33 (transferencias, referencias, consignaciones, tarjetas)
  db.py                        historial cierre.db (días, hallazgos, revisiones)
  asesoras.py                  une los nombres de asesoras
pruebas_cierre.py            <- pruebas de aceptación con el archivo de agosto
webui/                        <- interfaz (HTML/CSS/JS + anime.js), corre embebida
  index.html                   (incluye la pantalla de carga)
  css/styles.css, css/cierre.css
  js/app.js, js/cierre.js
  js/vendor/anime.min.js
legacy_tkinter/               <- interfaz anterior en Tkinter, de respaldo
  (ejecutar con: python legacy_tkinter/main.py)
```

**Ninguno de los motores (`core.py`, `verify.py`, `transferencias_core.py`) fue
modificado en la migración de interfaz** — salvo un agregado en `core.py` que
adjunta el desglose por punto de venta a cada bloque verificado de Bold (necesario
para el panel de Historial); no toca ninguna fórmula ni el Excel de salida.
`bridge.py` es el único punto de contacto entre la interfaz y ese motor: diálogos
nativos de archivo/carpeta, y pegar los resultados al historial.

## Sobre el estilo visual
Interfaz oscura, tipo panel de control: fondo grafito con glows suaves,
tarjetas con borde sutil y sombra difusa, acentos violeta/celeste/lima
(un color por módulo, igual que antes), tipografía del sistema. Las
transiciones de pantalla, el conteo animado de los KPIs, las barras del
panel de Historial y la bitácora de Transferencias usan **anime.js**.
Sin dependencias externas de red: todo (fuentes, animación) corre local,
así que la app funciona sin internet.

## Módulo Historial — cómo se calculan las cifras
Cada vez que corres "Verificar contra Bancolombia" en el módulo Bold/Redeban,
se guarda una fila por punto de venta en `historial.db`:
- **Bold**: el depósito de Bold llega consolidado (una sola línea del banco por
  día/bloque, no por tienda), así que cuando un bloque no cuadra, el monto del
  bloque se **prorratea** entre las tiendas que tuvieron ventas ese bloque, para
  poder mostrar "fallidas por punto de venta" igual que en Redeban.
- **Redeban**: cada punto de venta + franquicia + fecha de canje ya se verifica
  por separado contra el banco, así que se guarda tal cual.

El panel de Historial muestra, para el rango de fechas que elijas:
- **Total esperado** = suma de Bold + Redeban (lo que el motor calculó que debía
  llegar).
- **Monto que no coincidió** = suma de lo esperado en las filas donde el banco
  no cuadró (rojo, sin contar los "cruces" ámbar, que sí cuadran pero repartidos
  en dos fechas).
- **Diferencia** = Total esperado − monto que no coincidió = lo que sí quedó
  confirmado contra el banco.
- **Fallidas por punto de venta**: cuántas veces cada tienda apareció en un
  bloque/fila que no coincidió, Bold y Redeban por separado.
- **Tendencia**: fallidas por fecha, para ver si va a la baja o al alza.

## Módulo Transferencias — qué se le agregó (sin tocar la lógica)
- **Formato de dinero** (`$#,##0.00`) en las columnas TOTAL, Reporte archivo,
  Diferencia, y cada transferencia individual.
- **Fila "TOTAL GENERAL"** al final de cada hoja, con la suma de todos los puntos
  de venta de esa fecha.
- **Carpeta de destino elegible**: si eliges una carpeta distinta, se respeta; si
  no eliges ninguna, usa Documentos/TRABAJO IRINA/TRANSFERENCIAS por defecto.
- **Sección "DATOS SIN ORIGEN" por día**: pagos sin código identificable (Nequi,
  PSE, etc.) aparecen día a día en su propio cuadrito de cada hoja, listos para
  asignarles el punto de venta a mano. La hoja global `SIN_IDENTIFICAR` se
  mantiene además, como respaldo para revisión general.
- **Pendiente para después**: lector de archivos de Daviplata.

## Módulo Bold / Redeban
Mismo motor de siempre (`core.py`, `verify.py`) — multi-archivo, fecha de entrada
por bloque, formato de dinero, verificación con detección de "cruces", manejo de
carpetas OneDrive, etc. Lo único nuevo es el desglose por punto de venta que
alimenta al Historial.

## Módulo Cierre del día (fases 1 y 2)
Especificación completa en `CIERRE_DEL_DIA.md`. Lo que hay hoy:

**Pestañas** (cada una responde una pregunta):
- **Hoy** — ¿qué pasó ayer? (detalle abajo). Cada hallazgo se puede marcar como
  *revisado*, *error confirmado* o *descartado*, con una nota.
- **Punto** — ¿cómo va este punto? Calendario del mes con cada día coloreado por
  estado, su descuadre y cuántos hallazgos le quedan pendientes; totales del mes.
  Clic en un día lleva a su detalle en Hoy.
- **Asesora** — ¿cómo va esta persona? Días trabajados (y cuántos compartidos),
  faltantes y sobrantes sin explicar, hallazgos pendientes y señales para revisar
  (faltantes sin explicar repetidos; descuentos, regalos o dañados/devoluciones por
  encima del promedio del punto). Los nombres se unen solos ("Ana" = "Ana
  Pérez" en el mismo punto); se pueden corregir en `asesoras_alias`.
- **Pendientes** — hallazgos sin revisar, del más antiguo al más reciente. Los
  avisos menores de la planilla (errores de fórmula que se repiten cada día) se
  muestran solo si se piden.

**Historial:** `%APPDATA%\SuiteIrina\cierre.db`, aparte del Historial de Bold/Redeban.
Revisar un día otra vez reemplaza el resultado de ese día y punto (no duplica) y
conserva la revisión y la nota de los hallazgos que vuelven a salir igual. Sin el
archivo cargado, Hoy muestra lo guardado. "Revisar todo el mes" llena de una vez
Punto y Asesora con todos los días que traen los archivos.

**Cómo se usa:** carga el Excel del mes de cada punto (descargado del Google Sheet;
el punto se reconoce solo por la celda "PUNTO DE VENTA" o el nombre del archivo),
elige el día y dale **Revisar**. La pantalla **Hoy** muestra una fila por punto con
asesoras, venta, descuadre (+ sobra / − falta), estado y causa principal. Clic en
un punto: todos sus hallazgos, agrupados en *causas del descuadre*, *señales para
revisar* y *planilla*, cada uno con la evidencia (hoja!celda, valor, fórmula
encontrada vs. esperada).

**Estados:** *cuadra* (|descuadre| ≤ tolerancia), *explicado* (una causa explica al
menos el 80 %) o *sin explicar*. Las causas son hipótesis alternativas: cuenta la
que más explica, no la suma. R05 (combinación de precios) se muestra pero no da
el día por explicado sola.

**Reglas de nivel 1 (solo el Excel):** R01 fórmulas contra la plantilla (la
plantilla se deduce del propio mes; los errores que ya venían del día anterior se
juntan en un aviso aparte para no tapar los nuevos) · R02 continuidad (inventario,
base, fecha de la hoja) · R03 compensación entre días seguidos · R04 billete ·
R05 combinación de precios · R06 regalos > salidas · R07 observaciones vs.
dañados/devoluciones/cambios · R08 ajustes que no son múltiplo del precio · R09
descuentos · R10 errores conocidos de plantilla · R11 DESC FACT.

**Configuración:** todos los umbrales están en `cierre_config.json`. La copia que
se edita es `%APPDATA%\SuiteIrina\cierre_config.json` (se crea sola la primera
vez y sirve también con el .exe).

**Rendimiento:** leer un libro mensual tarda ~40 s la primera vez; queda en caché
en `%APPDATA%\SuiteIrina\cache_cierre\` y las siguientes veces es instantáneo
(si el archivo cambia, se vuelve a leer).

**Pruebas:** `python pruebas_cierre.py` corre la lista de aceptación del archivo
de agosto de Plaza Imperial, las del historial, Siigo, banco, Google Sheets y
Bold/Redeban (47/47). Siigo, banco y Bold/Redeban usan datos sintéticos, salvo el Sheet de transferencias de
septiembre, que es real; Google se prueba sin conexión (respuestas con el mismo
formato que la API). Usa una base temporal: nunca toca el `cierre.db` real.

**Siigo (fase 3, opcional):** en Hoy → "Fuentes opcionales" se carga el reporte
"Ventas por vendedor por producto" del día (uno para los 11 puntos; debe ser de un
solo día). R20 compara las unidades por producto contra SALIDAS SIIGO del Excel:
- descuenta lo que las observaciones dicen que se devolvió/dañó/prestó (sale en F
  pero no se factura);
- usa `mapeo_siigo.xlsx` (nombre Excel ↔ nombre/código Siigo y los kits, que se
  desarman en sus componentes); los grupos (Empaque Milagros, Sachet Obsequio,
  Doy Pack Regalo) están en `cierre_config.json` → `siigo.grupos`;
- facturado en Siigo y no en el Excel = señal alta (si la caja cuadra, esa plata
  tampoco entró); en el Excel y no en Siigo = revisar si falta la factura.
El mapeo se puede cambiar desde la pantalla ("cambiar mapeo"); se guarda en
`%APPDATA%\SuiteIrina\mapeo_siigo.xlsx`. **El lector del reporte es provisional**
(armado con la descripción, probado con reportes sintéticos) hasta probarlo con un
reporte real de Siigo.

**Bancolombia (fase 4, opcional):** en "Fuentes opcionales" → "Cargar banco" se
carga el **PDF de movimientos** (leído con el mismo lector del módulo
Transferencias: PAGO QR / PAGO LLAVE, punto por los últimos 4 dígitos) y/o el
**Sheet de control "N. Transferencias &lt;mes&gt;"** descargado como .xlsx (una hoja por
día, cada transferencia del banco por punto desde la columna TRANSACCIONES, y
"Datos Sin origen"; el mes sale del nombre del archivo). Si un mismo día viene de
las dos fuentes, se usa la primera que se cargó.
- **R30** compara la lista "Transferencias" del punto contra lo que llegó, monto
  por monto; antes de reportar busca en el día anterior y el siguiente (pagos de
  la noche). Reporta *anotadas que no llegaron* (señal alta), *llegaron sin anotar*
  y *posibles montos mal digitados* (dígitos cambiados de lugar, un dígito
  distinto o un cero de más/menos).
- **R31** si ese día hubo pagos sin código y al punto le faltan transferencias
  (sobre todo si coinciden en monto): posible cambio del código del QR.
- **R32** la consignación del Excel debe aparecer en el extracto ese día o el
  siguiente (solo con el PDF; el Sheet no trae consignaciones). Las palabras que
  marcan una consignación están en `banco.palabras_consignacion`.
El lector del PDF reutiliza `transferencias_core` sin modificarlo; la búsqueda de
consignaciones es **provisional** hasta probarla con un extracto real.

**Google Sheets (fase 5):** en el paso 1 de Hoy, "Directo desde Google Sheets".
- Una sola vez: crear credenciales en Google Cloud (la guía paso a paso está en la
  misma pantalla) y "Cargar credenciales (JSON)" → "Conectar con Google" (se abre
  el navegador; permiso **solo de lectura**: `drive.metadata.readonly` para ver
  nombres de carpetas/archivos y `spreadsheets.readonly` para leer los Sheets).
- Cada vez: elegir el mes → "Buscar los Sheets del mes". El programa busca
  "cierres &lt;año&gt;" → la subcarpeta del mes → asigna cada Sheet a su punto por el
  nombre (y completa con la hoja URL del Sheet de transferencias). Se revisa la
  tabla, se corrige lo que haga falta y "Guardar y cargar"; la asignación se
  recuerda por mes en `%APPDATA%\SuiteIrina\asignacion_sheets.json`.
- Los Sheets se leen con la misma interpretación que el .xlsx (probado: resultados
  idénticos los 31 días de agosto) y quedan en caché según su fecha de
  modificación: un Sheet que no cambió no se vuelve a descargar.
- Credenciales y permiso: `%APPDATA%\SuiteIrina\google_cliente.json` y
  `google_permiso.json` ("desconectar" borra el permiso).

**Siigo "Movimiento ventas y compras" (recomendado):** el mismo botón de Siigo lo
reconoce solo. Trae factura por factura, así que **un reporte del mes entero sirve
para revisar día por día** (se reparte por la FECHA ELABORACIÓN de cada factura).
Con él corren R20 (unidades) y **R21 (formas de pago)**: transferencias facturadas
contra la lista S, tarjetas contra T + U, ADDI contra la caja, y avisa de facturas
creadas otro día a las que les cambiaron la fecha. Solo cubre los puntos cuyas
facturas trae (centro de costo): se puede sacar uno por punto o uno con todos; si
se cargan varios, se suman. Las formas de pago se configuran en
`siigo.formas_pago`.

**Bold / Redeban (fase 6, opcional):** en "Fuentes opcionales" → "Cargar Bold /
Redeban" se cargan los **reportes vírgenes** (.xlsx), los mismos del módulo
Bold / Redeban; se leen con `core.load_bold` / `core.load_redeban` sin
modificarlos y se detecta solo cuál es cada uno.
- Bold: el punto sale del NOMBRE DEL DATÁFONO; se usa la fecha y hora de la
  transacción. En el formato nuevo solo cuentan los "COBRO EXITOSO".
- Redeban: el punto sale de los 2 últimos dígitos del CODIGO ESTABLECIMIENTO; se
  usa la FECHA DE TRANSACCION (no la de canje).
- Un reporte cubre, para todos los puntos de su procesador, los días entre su
  primera y su última transacción (un punto sin cobros ese día = no pasó tarjetas).
- **R33** compara la suma de las listas **T (débito) + U (crédito)** contra lo
  cobrado, monto por monto, igual que R30: *anotadas que no aparecen* (señal alta),
  *cobradas sin anotar*, *montos mal digitados* y ventas cobradas el día vecino
  (p. ej. pasada la medianoche) como aviso informativo. Los reportes no distinguen
  débito de crédito, así que no se revisa si una venta quedó en la columna
  equivocada.

En R30 y R33, la búsqueda en el día vecino usa solo lo que **le sobra** a ese día
(lo que no cuadra con su propio Excel): montos como $72.800 se repiten a diario y
usar el día completo escondía faltantes reales.

## Notas de robustez
Los tres módulos comparten el mismo patrón para carpetas de destino: intentan
crearlas si no existen (`os.makedirs`), y si de plano no se puede escribir ahí
(por ejemplo carpetas de OneDrive no sincronizadas), avisan con un mensaje claro
en vez de fallar en silencio.
