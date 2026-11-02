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
2 nov 2026. Jacobo aclaró que el 10 % es la cuota de un préstamo de Milagros con Bold,
no una comisión. Por eso no va fijo en el código: vive en
`empresa_config.bold_porcentajes_deposito`, que por defecto solo acepta el 100 %.
Milagros usa `{100,90}` y lo quita cuando termine el préstamo. Cierra H-57.

## Pendientes

### P-002 · ¿Un usuario en varias empresas?
Un contador podría atender a varias empresas. Hoy cada usuario pertenece a una
sola. Si las entrevistas muestran que los contadores son importantes, se agrega
una tabla `usuario_empresa`.

### P-003 · Modelo de precio
Por punto de venta, plan fijo o mixto. Se decide con las entrevistas y los
pilotos.

