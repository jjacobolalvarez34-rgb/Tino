# Decisiones

Cada decisión con su fecha y su motivo. Una decisión no se cambia en silencio:
se agrega una nueva que reemplaza a la anterior y se marca la vieja como
reemplazada.

## Tomadas

### D-001 · Producto para muchas empresas; Milagros es el laboratorio
1 nov 2026. Milagros compró otro software, pero el problema del cuadre diario
por punto sigue sin resolver en el mercado. Se construye un producto vendible a
muchos negocios. Milagros aporta datos reales con permiso de su dueña.

### D-002 · La facturación sigue en Siigo
30 oct 2026. Facturar electrónicamente exige un proveedor autorizado y capital.
El sistema lee los reportes de Siigo; no factura.

### D-003 · Supabase es la fuente de verdad
30 oct 2026. Ya se conoce, trae autenticación y RLS, y responde rápido. La
lentitud de la app anterior venía de Apps Script y Google Sheets en medio, no de
Supabase.

### D-004 · Dinero en pesos enteros (`bigint`)
30 oct 2026. Evita errores de redondeo. Los pesos colombianos no usan centavos
en la práctica.

### D-005 · Nada se borra
30 oct 2026. Lo que se equivoca se anula, se ajusta o se desactiva. Así siempre
se puede reconstruir qué pasó, y el dueño confía en los números.

### D-006 · Una conciliación dudosa nunca se confirma sola
30 oct 2026. Un falso cruce confirmado destruye la confianza en el sistema. Lo
dudoso queda como `propuesta` hasta que una persona decide.

### D-007 · La verificación de transferencias es obligatoria y debe ser confiable
30 oct 2026. Es uno de los dolores más claros. Regla inicial: sin aviso del banco
en 30 minutos, la transferencia queda sospechosa. El tiempo es configurable por
empresa.

### D-008 · Diseño en ciruela
31 oct 2026. Cansa menos la vista en jornadas largas y no se confunde con el rojo
de error. Detalle en `DESIGN.md`.

### D-009 · Copiar como números
30 oct 2026. Los dueños viven en Excel. Todo reporte se copia como enteros puros,
sin formato, para pegarlo y sumarlo sin limpiar datos.

### D-010 · No se calculan impuestos oficiales
30 oct 2026. Eso es del contador y de Siigo. El sistema muestra comisiones y
retenciones tal como vienen en las liquidaciones.

### D-011 · Empresas separadas desde el día 1
1 nov 2026. Agregar separación por empresa después obliga a reescribir casi
todo. Toda tabla lleva `empresa_id` y RLS desde la primera migración.

### D-012 · Las migraciones aplicadas nunca se editan
2 nov 2026. Cada cambio a la base es un archivo nuevo y numerado. Así cualquier
base se reconstruye igual corriendo los archivos en orden.

### D-013 · Ventas por detalle o por total, según lo que traiga el reporte
2 nov 2026. Algunos negocios reportan venta por venta y otros solo totales por
asesora. La tabla `venta` acepta ambos; `venta_detalle` se llena solo cuando hay
detalle.

### D-014 · App nativa en una fase posterior
Reemplazada en parte por D-023: primero va el `.exe`. Sigue en pie que la app no se
construye todavía y que la venta inicial no depende de ella.
30 oct 2026. La app actual no convenció por lenta. La venta inicial no depende de
la app: el sistema lee los Excels que ya existen. La app nativa (Expo) guardará
en el celular los últimos días de su punto como respaldo.

### D-015 · El producto se llama Tino
2 nov 2026. "Tener tino" es acertar y tener buen juicio. Corto, fácil de decir
por teléfono y de recordar. Reemplaza el nombre de trabajo "Cuadre". Falta
confirmar dominio y que la marca esté libre en la SIC (clases 9 y 42).
Es un nombre de arranque: hay muchas empresas llamadas Tino en otros sectores y
una empresa de software en Estados Unidos. Se revisa si el producto escala o si
aparece un conflicto en Colombia. Para que cambiarlo sea barato: el código y la
base usan nombres neutros (nada se llama "tino" por dentro) y el logo del
chulito en la i sirve para cualquier nombre con i (Tilo, Pilo, Atino).

### D-016 · Logo "Visto bueno"
2 nov 2026. Wordmark "tino" en trazo geométrico, con un chulito ciruela en vez
del punto de la i: la caja revisada y aprobada. Archivos y reglas de uso en
`docs/marca/` y en `DESIGN.md`.

### D-017 · Valores de las reglas configurables por empresa
2 nov 2026. Ventanas de hora, tolerancias de valor, umbral de descuadre y
tiempos de sospecha viven en `empresa_config`, con valores iniciales tomados de
`docs/REGLAS/`. Cada negocio es distinto y así no hay que tocar código para
ajustarlos. Reemplaza el pendiente P-005.

### D-018 · La migración 0001 se corrige antes de aplicarla
2 nov 2026. La revisión encontró huecos de separación entre empresas que las
pruebas no cubrían. Como 0001 no se ha aplicado en ningún lado, D-012 permite
corregir el mismo archivo. Así queda un solo archivo limpio y la numeración de
`docs/MODELO_DATOS.md` no cambia.

### D-019 · Un producto no tiene dos precios vigentes el mismo día
2 nov 2026. Decisión de Jacobo. La base lo impide por producto y tipo de venta,
porque dos precios a la vez dejarían sin saber cuál usar al medir descuentos.

### D-020 · El repositorio es público
2 nov 2026. Decisión de Jacobo: la dueña de Milagros dio permiso y no le preocupa
que sus datos queden expuestos. Reemplaza lo que pedía la tarea 001 (privado).
Aun así, los archivos reales y los nombres de personas no se suben: no hacen falta
en el repositorio, y el permiso de la dueña no cubre a las asesoras ni a quienes
transfieren. `.gitignore` los deja por fuera. Mientras se limpia, el código de
`motores/conciliador/` queda como excepción a "nada específico de un cliente en el
código": trae los puntos y sus códigos.

### D-021 · Primero solo `tino-pruebas`
2 nov 2026. Decisión de Jacobo. `tino-produccion` se crea después. Cambia lo que
pedía la tarea 001.

### D-022 · La lógica de la plata existe en Python y en TypeScript
2 nov 2026. Decisión de Jacobo, que cierra P-001. Python mueve el `.exe` y conserva
lo que ya funciona. TypeScript queda construido desde ya para que pasar a la web no
sea empezar de cero. El riesgo es que los dos lleguen a dar resultados distintos, y
por eso `motores/CONTRATO.md` define cada función, los dos corren los mismos casos
y `motores/comparar_lenguajes.py` exige que coincidan. Costo: cada cambio de lógica
se hace dos veces.

### D-023 · Primero un `.exe`; la web y el celular después
2 nov 2026. Decisión de Jacobo. Programa de escritorio en Python con pantallas
HTML, CSS y JavaScript, como el conciliador actual. Supabase sigue siendo la fuente
de verdad (D-003). La llave de servicio no va dentro del `.exe`: cualquiera podría
sacarla. El programa entra con el usuario de cada persona, así que RLS aplica
siempre. Se pierde por ahora: celular, Mac y que el cruce corra solo.

### D-024 · La fase 1 revisa a la mañana siguiente
2 nov 2026. Confirmado por Jacobo. Se revisa el día anterior con el Excel, el
extracto, Siigo, Bold y Redeban, como hace hoy el conciliador. Sin app y sin cierre
del día. La verificación en minutos llega con el lector de correos.

### D-025 · Permisos de finanzas y soporte
2 nov 2026. Decisión de Jacobo. Finanzas no ve la lista de usuarios. Soporte usa una
cuenta por empresa, y eso se cambia al llegar el segundo cliente (ver P-002).

### D-026 · El punto de un pago sale de su código, no de la cuenta
2 nov 2026. Decisión de Jacobo, que cierra H-52. Los 11 puntos de Milagros comparten
cuenta, así que el punto se reconoce por el código del QR o la llave. La tabla
`codigo_recaudo` los guarda con vigencia, porque un código puede cambiar. La base
impide que dos códigos activos compartan los últimos 4 dígitos, que es lo que usa el
cruce: si no, un pago caería en el punto equivocado sin que nadie lo note.

### D-027 · El descuento de Bold es configuración de cada empresa
Reemplazada por D-029: el porcentaje resultó innecesario.
2 nov 2026. Jacobo aclaró que el 10 % es la cuota de un préstamo de Milagros con Bold,
no una comisión. Por eso no va fijo en el código: vive en
`empresa_config.bold_porcentajes_deposito`, que por defecto solo acepta el 100 %.
Milagros usa `{100,90}` y lo quita cuando termine el préstamo. Cierra H-57.
Actualización del mismo día: el reporte de Bold trae la columna `DEDUCCIÓN DEL PRÉSTAMO`,
con el valor exacto de cada cobro, y `DEPOSITO EN SALDO DE VENTAS` ya viene descontado.
Si los depósitos coinciden contra el extracto, este porcentaje sobra y se quita de 0001
antes de aplicarla. Falta comprobarlo con el extracto de Bancolombia.

### D-028 · Tablero de ventas en vez de las hojas de Excel de Bold y Redeban
2 nov 2026. Decisión de Jacobo. Las hojas que arma el conciliador con su plantilla
las usa solo Milagros, así que no pasan a Tino. De esos reportes se aprovechan los
datos para un tablero con estadísticas descriptivas. `docs/DESIGN.md` pide evitar
gráficas que haya que interpretar: por eso son solo barras simples, cada una con su
tabla, y lo que no se entienda de un vistazo no entra.

### D-029 · El préstamo de Bold se lee del reporte, no se configura
2 nov 2026. Reemplaza a D-027. El reporte trae `DEDUCCIÓN DEL PRÉSTAMO` por cobro y su
depósito ya viene descontado. Contra el extracto de septiembre, ningún bloque necesitó
el 90 %. Por eso `empresa_config.bold_porcentajes_deposito` salió de 0001 antes de
aplicarla: era un parche para un dato que el reporte ya trae exacto.
Aclaración: el 90 % del conciliador sí tenía razón de ser. En mayo de 2026 el banco
recibió 10 % menos y el reporte de entonces no traía la columna del préstamo. Aplica
solo a reportes viejos: Tino no carga ese historial como dato de plata confirmado.

### D-030 · Tino asigna el código de cada asesora y sus nombres van por punto
2 nov 2026. Decisión de Jacobo. Si no llega código, la base asigna el siguiente de la
empresa. Pero los reportes solo traen el nombre, y dos asesoras de puntos distintos
pueden llamarse igual: por eso el alias vale para un punto. Va en 0002, porque 0001 ya
se aplicó. Si una asesora rota, su nombre se registra también en el otro punto.

### D-031 · Tipos de venta de Milagros
2 nov 2026. Decisión de Jacobo: detal, mayorista y regalo. Los tres se facturan en Siigo
y mueven inventario; el regalo se factura a $1. Son datos de Milagros en `tipo_venta`,
no reglas del código.

### D-032 · Los nombres que nadie puede resolver quedan por resolver
2 nov 2026. Decisión de Jacobo. Cuando el Excel dice solo un nombre corto y hay dos
personas posibles, y ni Jacobo sabe cuál es, Tino no adivina: esos días quedan por
resolver. Una asesora sin apellido conocido se carga con lo que se sabe. Pegarle ventas a
la persona equivocada sería peor que dejarlo pendiente.

### D-033 · La bodega no es un punto de venta
2 nov 2026. Decisión de Jacobo. La bodega hace salidas de producto y se maneja aparte, así
que no se carga como punto, aunque `punto_venta.tipo` lo permita. Se revisa cuando llegue
inventario.

### D-034 · El .exe es una carpeta, no un solo archivo
2 nov 2026. Un `.exe` de un solo archivo se descomprime en el TEMP del sistema cada vez
que se abre, y en este computador nada se escribe en C:. Empacado como carpeta, abre más
rápido y no escribe en ningún disco al arrancar. Se entrega la carpeta entera
(`Tino.exe` y `_internal`). Se revisa cuando haya instalador. Lo que el programa guarda
para sí (temporales y datos de la ventana) va en `tmp/` y `ventana/` junto al `.exe`.

### D-035 · La ventana del .exe es HTML, en una ventana propia
2 nov 2026. Decisión de Jacobo. La primera ventana, en Tk, no tenía la estética de Tino.
Ahora es HTML con los tokens de DESIGN.md, dentro del motor de Edge (WebView2) que ya trae
Windows, en una ventana propia y no en el navegador. Así el `.exe` y la futura web usan
las mismas pantallas.

### D-036 · En la fase 1 la asesora no ve el banco, los cruces ni los descuadres
3 nov 2026. Tomada por Claude con autorización de Jacobo para decidir solo. La asesora ve
su jornada y su caja, no las del banco ni lo que dice "revisar". Una señal no debe llegarle
como acusación antes de que exista su app con el contexto completo (fase posterior). Es
más estricto que la tabla de roles de MODELO_DATOS, que decía "su punto".

### D-037 · Se guarda la lista de precios completa de cada día
3 nov 2026. Tomada por Claude. Del Excel del día entran todas las filas de producto con
precio, aunque no se movieran. La pista de "suma de precios" necesita todos los precios del
punto, y la base aún no tiene lista de precios (`precio_producto` está vacía).

### D-038 · Si la misma plata llega en dos archivos, cuenta uno solo
3 nov 2026. Tomada por Claude. El hash solo detecta archivos idénticos, y el mismo mes de
Bold o el mismo extracto suelen llegar varias veces. Por eso: en el Excel cuentan los pagos
del archivo cuyo reporte de caja está vigente; en el extracto, cada fecha sale del último
extracto cargado que la cubre; en Bold y Redeban, por proveedor y día, el reporte con
préstamo y más cobros (`unir_reportes`, como con archivos sueltos).

### D-039 · Deshacer un archivo deshace también lo que se decidió con él
3 nov 2026. Tomada por Claude. Si no, una línea del banco seguiría ocupada por un pago que
ya no cuenta y el archivo corregido no podría confirmarse. Sus cruces se rechazan, sus
transferencias se rechazan o vuelven a pendiente y sus errores se dan por resueltos, todo
con la nota "Se deshizo el archivo …" y en el historial.

### D-040 · El extracto se lee con reglas de cada empresa, no con un modo por cliente
13 nov 2026. Pedido de Jacobo: que funcione para cualquier empresa. Cada línea del
extracto se clasifica con `clasificar_linea_banco` (contrato y dos lenguajes): primero las
reglas del perfil del banco de la empresa (`perfil_fuente`), después las del formato del
banco (lo que escribe Bancolombia, igual para todos sus clientes). El extracto entra
completo, ordenado por tipo: transferencias con código, pagos sin código, depósitos de
datáfonos, consignaciones, abonos y cargos. Nada de un cliente va en el código.

### D-041 · Las facturas vienen del programa de facturación, con un conector por programa
13 nov 2026. Tomada por Claude con autorización de Jacobo. Siigo primero, por su API. Cada
conector entrega la misma forma (factura normalizada en pesos enteros, con su id de
origen), y la base no la repite al traerla otra vez (0009). De qué punto es cada factura
lo dice el perfil de la empresa (centro de costo, bodega, prefijo o tipo de documento).
Las credenciales de Siigo se guardan solo en el computador de la empresa, nunca en la
base ni en el repositorio. Ver docs/FUENTES/facturacion_api.md.

### D-042 · La web usa el mismo núcleo y la misma revisión, en TypeScript
13 nov 2026. Tomada por Claude. La web (web/, Next.js para Vercel) lee la base con la
sesión del usuario y corre la revisión con `motores/nucleo_ts`. `web/lib/revision.ts` debe
dar exactamente lo mismo que Python; lo exige `tests/web/comparar_revision.ts`. Subir
archivos sigue en el `.exe` hasta que los lectores existan en TypeScript o como función
de servidor.

### D-043 · El menú va al costado
13 nov 2026. Pedido de Jacobo. Con nueve pantallas, las pestañas arriba ya no caben bien.
En pantallas angostas el menú pasa arriba.

### D-044 · La web es la interfaz principal; el .exe solo sube archivos
19 nov 2026. Decisión de Jacobo. Todo lo nuevo se hace en la web, para celular y
computador. El programa de escritorio queda para subir archivos y no recibe pantallas nuevas.

### D-045 · Equipo va antes que la tarea 004
19 nov 2026. Decisión de Jacobo. Él cierra la 004 en paralelo.

### D-046 · Nueva dirección visual para la web (DESIGN.md §15)
19 nov 2026. Pedido de Jacobo. Riel angosto de íconos en el computador y barra inferior en el
celular, con "+ Registrar" siempre a la vista; "Hoy" en frases que se tocan, ordenadas por
urgencia; cifras grandes con una línea de contexto; personas primero (avatar, anillo de meta,
ranking con barras, ficha como línea de tiempo); menos cajas. Se aplica primero a Hoy y la
ficha (punto de control) y al resto solo cuando Jacobo lo apruebe. Reemplaza a D-043 cuando
se apruebe.

### D-047 · Todo en main; arranque queda igual a main
19 nov 2026. Pedido de Jacobo. Se trabaja en main, sin ramas por tarea. Vercel publica desde
un fork en otra cuenta que sigue la rama arranque; por eso cada subida va a main y a arranque.

### D-048 · La venta por persona va en su propia tabla, no en venta
19 nov 2026. Tomada por Claude. La tarea pedía `venta.asesora_id`, pero `venta` ya guarda la
venta del día que trae el Excel: poner ahí la venta por persona la contaría dos veces y
descuadraría la revisión de caja. `venta_asesora_dia` guarda una fila por persona y día con su
archivo y su fila de origen, y la vista `v_venta_asesora` aplica "cuenta el último archivo"
(D-038). Se lee con el perfil de la empresa (hoja y columnas), no con código de un cliente.

### D-049 · Un día de varias personas se reparte en partes iguales
19 nov 2026. Decisión de Jacobo. El reporte de Milagros trae una sola venta por día y punto,
a veces con dos nombres. Se reparte en partes iguales (lo que sobra de dividir va de a un
peso a las primeras) para que el ranking sume lo mismo que el punto. Es un valor de la
empresa (`empresa_config.equipo_reparto`), por si otra empresa lo quiere distinto.

### D-050 · La meta del mes puede venir en el Excel, pero se pone en Tino
19 nov 2026. Tomada por Claude, confirmada por Jacobo ("se debe poder hacer en el programa").
Las metas se escriben en la pantalla Metas (`meta_periodo`). Si el Excel trae la meta del mes
(Milagros: hoja METAS, celda K2), entra con su archivo y su fila, y no pisa una meta escrita a
mano para el mismo punto y período.

### D-051 · Observaciones y evaluaciones son privadas
19 nov 2026. Regla de la tarea de Equipo. Las ven dueño, encargada, lider y soporte; el
responsable de punto solo las de su punto; finanzas y la asesora, ninguna. Lo hace la base
(`app.ve_equipo`), con pruebas de dos empresas y cada rol (tests/rls/0011_pruebas.sql).

### D-052 · La página pública anima siempre, aunque el sistema pida reducir movimiento
19 nov 2026. Decisión de Jacobo, solo para la página de presentación ("que tenga las
animaciones esté eso activo o no"). Las animaciones son sobrias (opacidad y posición, sin
parpadeos). Dentro del programa se sigue respetando "reducir movimiento" (DESIGN.md §11).

### D-053 · Precios por punto de venta (cierra P-003)
19 nov 2026. Decisión de Jacobo. Equipo 30.000, Caja 45.000 y Completo 65.000 por punto al mes;
mínimo 3 puntos; implementación desde 400.000; anual 12 por 10; fundador 30 % menos por 12
meses para los primeros 5; piloto de 30 días a mitad de precio. Viven solo en
`web/lib/precios.ts`. IVA sin mencionar hasta confirmarlo. Ver docs/NEGOCIO/precios.md.

### D-054 · Primero se corrige en pruebas y después se pasa a producción
19 nov 2026. Decisión de Jacobo. tino-pruebas sigue siendo el laboratorio; los datos de uso
diario viven en tino-produccion (organización aparte en Supabase). Ninguno va a demos,
capturas ni al repositorio: las capturas se hacen con la empresa inventada de las pruebas.

### D-055 · Los Excel del cliente no se corrigen: Tino tolera sus variaciones
19 nov 2026. Decisión de Jacobo. El perfil acepta varios nombres por columna y textos de día
sin venta («No abrió»). Si en una hoja borraron un encabezado pero lo demás está donde en otra
hoja del mismo libro, se usa ese diseño y se avisa. Si la hoja del día y el resumen no
coinciden, es un problema del archivo: se avisa con su fila y no se cambia ningún valor.

### D-056 · Crear un usuario no lo invita
19 nov 2026. Pedido de Jacobo. La pantalla Usuarios (dueño y soporte) crea el acceso sin mandar
correo; «Invitar» lo manda cuando el dueño decida. La llave de servicio solo vive en el
servidor (/api/usuarios); lo que toca la tabla usuario va con la sesión de quien llama (RLS).

### D-057 · Subir desde la web: el archivo queda en cola y lo procesa el programa de escritorio
20 nov 2026. Decisión de Jacobo (camino B de docs/OPERACION/subir-desde-la-web.md). Desde el
celular o el computador, la web guarda el archivo en Supabase Storage (carpeta de la empresa)
y lo deja "en cola". El programa de escritorio lo procesa con los mismos lectores de Python y
la pantalla Archivos muestra "en cola", "cargado" o el error. Los archivos originales quedan
guardados. Se mantienen el aviso de archivo repetido y "Deshacer".

### D-058 · Dos respaldos: el de Supabase y uno nuestro
20 nov 2026. Decisión de Jacobo (opción C de docs/OPERACION/produccion.md). Supabase Pro en la
organización de producción (respaldo diario, 7 días) y una copia propia fuera de Supabase, cifrada.
La copia propia NO va a GitHub mientras el repositorio sea público.

### D-059 · Vercel Pro se paga con la primera venta
20 nov 2026. Decisión de Jacobo. Mientras tanto se sigue en Hobby, que no es para uso comercial:
no se le cobra a nadie sobre ese plan.

### D-060 · Más bancos, con lo aprendido en el conciliador de Redil
20 nov 2026. Decisión de Jacobo: no todos los clientes usan el mismo banco. Del conciliador de
Redil (D:\Redil proyecto) se toma la lógica, no los datos: la lectura de los extractos de Banco de
Bogotá y Coopcentral y las reglas por banco (desfase de días, fines de semana y festivos, débito y
crédito invertidos, neto del día, transacción o totales del día, conceptos excluidos, alias de
traslados, tolerancia). Entran a Tino como perfiles de banco por empresa (D-040), nada amarrado a
un cliente. Los archivos de Redil traen cédulas y nombres reales: nunca entran al repositorio.

### D-061 · Tino reemplaza las herramientas del cliente; no se construye alrededor de ellas
20 nov 2026. Preocupación y decisión de Jacobo. Cada fuente entra por un adaptador configurado en el
perfil de la empresa, y la fuente propia es Tino: el cierre del día en Tino reemplaza el Excel del día,
y los reportes de Tino reemplazan el "Sheet de control" del plan original, que no se construye. El
lector de la plantilla de Milagros queda como adaptador de transición. Ver docs/PLAN.md §1.

### D-062 · Con Siigo, Tino solo lee (reemplazada por D-063)
20 nov 2026. Tomada por Claude, a confirmar por Jacobo. La API de Siigo permite crear, editar y anular
facturas, notas crédito, recibos de caja y comprobantes, pero "Tino no factura" (VISION) y escribir
toca la contabilidad legal del cliente. Tino lee facturas, notas crédito, recibos, centros de costo y
productos. Escribir (por ejemplo, el recibo de caja de una consignación conciliada) se decide después,
con cada cliente.

### D-063 · Tino factura a través del programa de facturación del cliente
20 nov 2026. Decisión de Jacobo (cambia lo de "Tino no factura" de la visión y D-062). La factura la
emite Siigo con la cuenta, la numeración y los impuestos del cliente: Tino no calcula impuestos, manda
los ids de impuesto de cada producto como están en Siigo. Cada venta lleva un id único y de ahí sale
la Idempotency-Key de Siigo, así reintentar nunca duplica. Por seguridad, mandar a la DIAN
(`stamp.send`) empieza apagado y lo enciende cada empresa. Las pruebas se hacen solo en una empresa
de pruebas de Siigo, nunca en la cuenta de un cliente (cada factura ahí es real).

### D-064 · Vender y facturar sin internet
20 nov 2026. Idea de Jacobo, opinión de Claude. La venta se guarda en el celular (IndexedDB en la
web, SQLite en la app) con su id único y se manda cuando vuelve la señal; si Siigo está caído, queda
en la base de Tino y se reintenta sola. No se inventa un formato de archivo: la base del celular y
la de Tino son el respaldo; Google Drive, si se quiere, como exportación opcional (lleva datos de
clientes). Siigo no acepta facturas electrónicas con fecha anterior a hoy: la venta sin conexión se
factura el día que se manda, con su fecha y hora reales en las observaciones. Qué se le entrega al
cliente mientras tanto (contingencia de la DIAN) lo confirma un contador antes de prometerlo.

### D-065 · La ventisca entre pantallas corre siempre
20 nov 2026. Decisión de Jacobo ("la idea es que se vea a pesar de eso"). Como en la página pública
(D-052), la transición de cambiar de pantalla corre aunque el sistema pida reducir movimiento. Es
corta (menos de un segundo) y solo mueve opacidad, posición y giro. El sonido se apaga en Más.

Corrección del mismo día: la ventisca va en la **portada** (la página de presentación), al pulsar
una sección del menú (Inicio, Conciliación, Descuadres, Excel, Equipo, Precios) o "Ver cómo
concilia". Dentro del programa se quitó, con el interruptor de sonido de Más. El sonido se oye si
el navegador no tiene guardado `tino-sonido = no`.

### D-066 · Roles configurables por empresa. Se construyen después del bloque A
26 nov 2026. Decisión de Jacobo (tarea 011, bloque C). Los roles dejan de estar fijos en la base: Tino
define una lista fija de permisos, cada empresa arma sus roles como paquetes de permisos con nombre,
y el alcance por puntos va aparte del rol. Plantillas: Gerencia, Coordinación, Responsable de punto y
Asesora. "Ver como" solo para mirar, solo Gerencia y soporte, auditado. La migración tiene que dejar
a cada usuario viendo exactamente lo mismo (prueba de equivalencia) y las pruebas actuales sin
cambios. Diseño completo en docs/ROLES.md. Sin código hasta que Jacobo apruebe el diseño.

### D-067 · Formación: registro del día manual o de integración, sin pisarse
26 nov 2026. Decisión de Jacobo (tarea 011, A1–A9). El registro del día guarda su origen (manual o
integración). Si los dos existen el mismo día, se guardan y se muestran los dos; para los
porcentajes cuenta el manual (propuesta de Claude que Jacobo no objetó). Hoy los usuarios solo
escriben "manual"; la integración queda preparada, sin construir. Un día sin registro no cuenta
como cero. Se corrige libre el mismo día (hora de Bogotá) y después solo con nota. Temas, criterios,
indicadores y etapas solo se llenan con el botón "Usar plantilla sugerida". La semana del
calendario va de lunes a domingo. Cuando un día lo comparten varias personas (dos, tres o más), la
conversión de cada una ese día es aproximada y la pantalla lo avisa.

## Pendientes

### P-002 · ¿Un usuario en varias empresas?
Un contador podría atender a varias empresas. Hoy cada usuario pertenece a una
sola. Si las entrevistas muestran que los contadores son importantes, se agrega
una tabla `usuario_empresa`.

### P-003 · Modelo de precio
Cerrada el 19 nov 2026 con D-053.
