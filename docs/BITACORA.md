# Bitácora

Una entrada por sesión de trabajo, la más reciente arriba. Corta: qué se hizo,
qué falta y qué dudas quedaron.

Plantilla:

```
## AAAA-MM-DD · [tema]
Hecho:
-
Falta:
-
Dudas:
-
```

## 2026-11-02 · Tablero de ventas con tarjeta
Hecho:
- Lector de Bold y Redeban en `ingesta/tarjetas.py`, en pesos enteros. Lo que no entiende
  no se cuenta y avisa. 6 pruebas con archivos inventados. Encontraron un error real:
  el archivo quedaba abierto y Windows lo bloqueaba.
- `estadisticas_ventas` en el contrato y en los dos lenguajes (D-028). 66 casos, y 0
  diferencias en la comparación entre Python y TypeScript.
- Tablero en `panel/tablero/`. Referencia con cifras inventadas:
  `docs/pantallas/tablero_ventas.html`. Revisado en Edge a 1280 y 375 px, con filtro por
  punto, avisos, punto sin hora, globo de cada barra y "Copiar como números".
Falta:
- Probarlo con reportes reales. Falta el permiso de Jacobo para usar `septiembre/`, y un
  `puntos.json` con qué datáfono es de cada punto.
- Solo muestra tarjetas: sin efectivo ni transferencias no son las ventas totales.
Dudas:
- Con reportes reales puede salir algo que el lector no espera: los encabezados se
  copiaron de `core.py`, no de un archivo. Las comisiones del generador de prueba son
  inventadas.
- Figtree se carga de internet. Dentro del `.exe` hay que incluir la fuente.

## 2026-11-02 · Códigos de pago y descuento de Bold
Hecho:
- 0001: nueva tabla `codigo_recaudo` (D-026) y
  `empresa_config.bold_porcentajes_deposito` (D-027). Cierra H-52 y H-57. 93 pruebas en
  verde, con 16 tablas, 45 políticas y 17 triggers. Se quitaron las protecciones nuevas
  en una copia y las pruebas lo detectaron.
Falta:
- Crear `tino-pruebas`, leer 0001 con Claude y aplicarla.
- Cuando se carguen los maestros (tarea 003): los 11 códigos en `codigo_recaudo` y
  `{100,90}` en la configuración de Milagros.
Dudas:
- Con el 90 %, ese 10 % debería verse como cuota del préstamo, no como plata perdida.
  Hoy el núcleo solo dice si el depósito coincide; falta definir cómo se muestra.

## 2026-11-02 · Núcleo de cálculo en Python y TypeScript
Hecho:
- Registradas las decisiones D-022 a D-025: dos lenguajes, `.exe` primero, fase 1 a la
  mañana siguiente, permisos de finanzas y soporte. Cierra P-001, H-05, H-06, H-27 y
  H-53. Documentos ajustados: arquitectura, modelo, visión y comandos.
- Tarea 005 hecha: `motores/CONTRATO.md`, núcleo en `motores/nucleo/` (Python) y
  `motores/nucleo_ts/` (TypeScript, escrito por un agente solo desde el contrato), 12
  funciones y 64 casos con datos inventados que corren los dos.
- Resultados: 0 diferencias en 300.000 comparaciones entre lenguajes, incluidas
  entradas raras a propósito. 0 diferencias en 120.000 comparaciones del Python contra
  las funciones reales del conciliador. TypeScript pasa `tsc --strict`, corrido desde
  una carpeta temporal porque el repositorio no lleva dependencias.
- Se metieron 7 errores a propósito en una copia y la comparación detectó los 7.
- El agente encontró 12 huecos del contrato. Quedaron definidos y en los dos lenguajes.
  Uno era un error heredado del conciliador: en `cruzar`, con montos repetidos, una
  fila salía dos veces y otra desaparecía. Los montos daban bien, pero señalaba la fila
  equivocada. Se corrigió en el núcleo; `motores/conciliador/` sigue igual.
- `tests/rls/0001_pruebas.sql` sube a 80 pruebas: finanzas no ve la lista de usuarios.

Falta:
- El `.exe` no existe todavía. Solo está la lógica: faltan los lectores (Excel, Bold,
  Redeban, PDF del banco, Siigo), las reglas de nivel 1, la conexión a Supabase y las
  pantallas.
- Nada se ha probado con datos reales: el núcleo solo ha visto datos inventados.
- `tino-pruebas` lo crea Jacobo. Mientras tanto no se aplica 0001.

Dudas:
- Siguen abiertas H-52 (tabla de código de pago por punto) y H-57 (el 10 % de Bold). El
  porcentaje 90 no está fijo en el núcleo: llega como parámetro.
- Cada cambio de lógica ahora se hace dos veces. Si TypeScript no se usa pronto, va a
  costar mantenerlo al día.

## 2026-11-02 · Corrección de 0001 y lectura del conciliador
Hecho:
- 0001 corregida con el visto bueno de Jacobo (D-018): llaves foráneas con empresa,
  plan y estado solo por llave de servicio, `on delete restrict` en usuarios,
  `medio_pago.tipo`, alias con texto normalizado, precios sin vigencias cruzadas
  (D-019), configuración automática por empresa y sin TRUNCATE. Cierra H-01, H-02,
  H-03, H-04, H-07 (falta confirmar en Supabase), H-08, H-09, H-10, H-13 y los precios
  de H-12.
- `tests/rls/correr.sh` ya corre en Windows y solo acepta un Postgres local. **79
  pruebas en verde** (antes 20), con los cinco roles en las dos empresas. Se quitó cada
  corrección en una copia y la suite la detectó. La excepción fue un índice de
  `precio_producto` que resultó sobrar, y se eliminó.
- Conciliador copiado a `motores/conciliador/` sin datos (detalle en la tarea 001).
  No se corrió, porque necesita datos reales.
- `.gitignore` y `.env.example` creados. Nombre real de punto quitado de la demo.
- Repositorio público (D-020) y solo `tino-pruebas` por ahora (D-021).
- Commit local en la rama `arranque`. No se subió nada a GitHub.

Falta (lo que necesito de Jacobo):
1. Elegir el lenguaje (P-001). Comparación abajo, en H-59.
2. Decidir H-05 y H-06.
3. Leer 0001 con Claude y decidir H-52 antes de aplicarla.
4. Crear `tino-pruebas` y decir si la rama `arranque` se sube a GitHub.
5. Confirmar los supuestos ⚑ contra lo que hace de verdad el conciliador (H-51 a H-58).
   Las reglas de `docs/REGLAS/` no se tocaron y hoy no describen lo que hace.

Dudas (siguen la numeración de la entrada anterior):
- **H-51 · Ni el Excel ni el extracto traen hora.** El Excel trae listas de montos por
  día y punto (transferencias, débito, crédito), y el extracto dice fecha, sin hora.
  Bold sí trae hora. Las ventanas C1, C2 y T2 y el cruce automático por hora no se
  pueden aplicar así. El conciliador cruza monto por monto en el día, contando cuántas
  veces aparece cada uno, y busca en el día vecino solo lo que sobra. Responde H-29: hay
  pagos sueltos, pero sin hora. Con la regla actual, el 95 % sería imposible.
- **H-52 · Una sola cuenta para los 11 puntos.** El punto sale de los últimos 4 dígitos
  de la referencia del QR o la llave. Nequi, PSE y otros no traen código y se asignan a
  mano. `cuenta_recaudo.punto_id` no sirve para esto, y las reglas de "mismo punto por
  cuenta" tampoco. Falta una tabla de código de pago por punto, con vigencia, porque
  ese código puede cambiar. Decidir antes de aplicar 0001.
- **H-53 · Hoy el flujo es a la mañana siguiente, no en minutos.** Se revisa el día
  anterior con el Excel, el extracto, Siigo, Bold y Redeban. No hay comprobantes ni
  correos, así que T1 de 30 minutos no aplica. Responde H-27: la fase 1 puede funcionar
  así, sin app y sin cierre, y la verificación en minutos llegaría con el lector de
  correos. Falta que Jacobo lo confirme.
- H-54 · El descuadre real sale del propio Excel: total menos valor teórico, del día y
  no por medio. Estados: cuadra (hasta 100 pesos), explicado (una causa explica el 80 %)
  o sin explicar. `docs/REGLAS/descuadres.md` usa 1.000 pesos y otras causas. El
  conciliador tiene compensación entre días, billete y combinación de precios, que no
  están en las reglas. Responde H-28 para Milagros: base y efectivo contado salen del Excel.
- H-55 · Tolerancias reales: 50 pesos con el banco y 100 para cuadrar, contra los 1.000
  de C3 y D1.
- H-56 · Bold deposita un solo valor por bloque, al siguiente día hábil, y el fin de
  semana junta varios días. Redeban va por punto, franquicia y fecha de canje. Los
  festivos se marcan a mano. Los grupos son por fecha, no pagos consecutivos como dice C4.
- H-57 · ¿Qué es el 10 %? `core.py` deduce el 10 % del depósito de Bold y `verify.py`
  acepta el total o el 90 %. Si es una tarifa, choca con "no se calcula con tarifas".
- H-58 · Faltan en documentos y modelo: ADDI, domicilios, sencillo, efectivo apartado,
  regalos, dañados, devoluciones y descuentos Idunn. Excel y Siigo tienen papeles
  distintos: el Excel es la verdad de los ingresos y Siigo solo se compara en unidades.
- H-59 · Lenguaje (P-001). Python: conserva 7.500 líneas probadas y buenas librerías de
  Excel y PDF, pero son dos lenguajes y necesita dónde correr. Todo en TypeScript: un
  solo lenguaje, pero hay que reescribir y volver a probar cada cruce. Recomendado:
  Python para ingesta y motores, y TypeScript para el panel. El programa actual es una
  app de escritorio y usa `float`: eso se corrige en cualquiera de los dos caminos.
- H-60 · Qué sirve de cada parte: Bold, Redeban y banco sirven para cualquier cliente,
  cambiando solo la configuración. El lector del Excel y las reglas de plantilla (R01,
  R10, R11) son de Milagros. Las reglas de descuadre (R03, R04, R05, R30, R33) son
  generales.
- H-61 · El alias debería poder ser por punto: el conciliador une nombres "en el mismo
  punto", y 0001 los deja únicos por empresa (H-11).

## 2026-11-02 · Revisión de documentos y preparación de tareas 001 a 003
Hecho:
- Se descomprimió `tino-repositorio.zip` en la raíz del repositorio, que es la raíz
  `tino/` de `docs/ARQUITECTURA.md`. El zip sigue ahí. Nada se pisó.
- Se leyeron `CLAUDE.md`, todo `docs/` y `tareas/`, la migración 0001 y las pruebas.
- Se ajustó la referencia a los plugins de diseño en `CLAUDE.md` y en
  `docs/DESIGN.md`, sección 13.
- Se crearon `ingesta/`, `motores/`, `panel/` y `app/` con un README corto en cada
  una.
- Se escribió el plan de las tareas 001, 002 y 003 en sus Notas. Son propuestas: no
  se ejecutó ningún paso que dependa de aprobación.
- Se corrió `tests/rls/correr.sh`. Resultado: **0001 migra sin errores y pasan las
  20 pruebas**, exit 0, en PostgreSQL 16.3. Quedan 15 tablas con RLS, 42 políticas
  (ninguna de DELETE) y 14 triggers.
  - Cómo se corrió: el servicio `postgresql-x64-16` está detenido y sin permisos de
    admin no se puede iniciar. Se usó un Postgres temporal aparte, en el puerto
    55432, ya apagado. El servicio instalado no se tocó.
  - El script no corre tal cual en Windows (H-13). Se corrió sin editarlo, con un
    envoltorio temporal que pone la URL al final.
- Se comprobaron los huecos de 0001 con una sonda aparte, con datos inventados. La
  sonda no quedó en el repositorio.
- No se tocó Supabase, ni datos reales, ni `db/migrations/`, ni `docs/REGLAS/`. No
  se hizo ningún commit.

Falta (lo que necesito de Jacobo, en este orden):
1. Decidir si 0001 se corrige antes de aplicarla (recomendado) o después, y aprobar
   los cambios de la tarea 002. Recomiendo no aplicarla todavía por H-01, H-02 y H-03.
2. Entregar el código del conciliador y un día de octubre con su resultado anterior.
   Sin eso no avanzan la tarea 001, P-001 ni la tarea 004.
3. Confirmar que el repositorio de GitHub es privado (`gh` no tiene sesión y no se
   pudo comprobar) y resolver H-43 antes del primer push.
4. Crear `tino-pruebas` y `tino-produccion` en Supabase.
5. Decidir las contradicciones de reglas H-14 a H-18 dentro de la tarea 004. El motor
   no se puede programar bien sin esas respuestas.
6. Decidir H-27 y H-29 antes de escribir 0003: cambian el diseño de `pago` y `jornada`.
7. Dar acceso a los Sheets maestros y a `mapeo_siigo`, y la lista oficial de tipos de
   venta (tarea 003).
8. Decir si se hace commit de lo de hoy. Antes de hacerlo hay que crear `.gitignore`
   (paso 1 de la tarea 001): hoy no existe y `git add .` subiría el zip.

Dudas: abajo, numeradas. Las citan los planes de las tareas.

### Seguridad de 0001 (comprobado en local, salvo H-04 y H-06, de lectura)
- **H-01 · Se pueden cruzar empresas por llave foránea.** El dueño de A creó un alias
  apuntando a una asesora de B y un datáfono apuntando a un punto de B, y le puso a un
  usuario de A un punto de B. RLS revisa el `empresa_id` de la fila, no a qué apunta.
  Además, un id inexistente da error y uno de B no, así que se puede averiguar si un
  id existe en otra empresa. Choca con "ninguna empresa puede ver ni tocar datos de
  otra". Las 20 pruebas no lo cubren.
- **H-02 · El dueño puede cambiar su `plan` y su `estado`.** Con la empresa
  suspendida pasó a `activa` y `completo` con un UPDATE. Y `suspendida` no hace nada:
  esa empresa sigue viendo sus datos. Falta definir qué significa.
- **H-03 · Borrar un usuario en Auth borra su fila en `usuario`** (`on delete
  cascade`). Choca con D-005 y con "nada se borra".
- H-04 · Las pruebas no cubren `finanzas` ni `soporte`, y en B solo hay dueño. `CLAUDE.md`
  y `docs/MODELO_DATOS.md` piden cada rol en dos empresas. Tampoco prueban `anon`, ni
  borrar con cada rol. En la sonda, `anon` no vio ni escribió nada, y un dueño no pudo
  alterar `auditoria`. Eso está bien, pero falta dejarlo como prueba.
- H-05 · Finanzas solo se ve a sí misma en `usuario`; la matriz de roles dice que ve
  "Todo" de su empresa. ¿Se corrige la matriz o la política?
- H-06 · Soporte es Jacobo, pero cada usuario pertenece a una sola empresa. Hoy
  soporte necesitaría una cuenta por cliente. P-002 lo aplaza para contadores, pero
  soporte lo necesita desde el segundo cliente.
- H-07 · A verificar en Supabase: creo que allá `authenticated` recibe todos los
  permisos en tablas nuevas, TRUNCATE incluido, y RLS no aplica a TRUNCATE. El simulador
  local no lo da, así que las pruebas no lo ven. No lo pude comprobar sin Supabase.

### Modelo de 0001
- H-08 · `medio_pago` no dice de qué tipo es. Las reglas hablan de efectivo, tarjeta y
  transferencia, y eligen C1 o C2 por medio, pero el glosario tiene Bold y Redeban como
  medios separados. Sin `tipo`, el motor tendría que conocer los códigos de cada empresa.
- H-09 · `precio_producto` y `terminal_datafono` no tienen índice completo por
  `empresa_id`. `docs/ARQUITECTURA.md` dice que toda tabla lo tiene.
- H-10 · `empresa_config`: nada crea su fila al crear una empresa; su auditoría queda
  con `registro_id` vacío porque no tiene columna `id`; `actualizado_en` no cambia con
  un UPDATE.
- H-11 · `asesora_alias.texto_original` se documenta en minúsculas y sin tildes, pero
  el nombre dice lo contrario y la base acepta `CARO M` y `caro m` a la vez. Además, un
  alias es único por empresa: dos Leidy de puntos distintos no caben. Igual en
  `producto_alias`.
- H-12 · La base acepta dos precios vigentes el mismo día. El principio 7 dice
  `vigente_desde` y `vigente_hasta`, pero `terminal_datafono` usa `activo_desde` y
  `activo_hasta`, y solo evita duplicados cuando `activo_hasta` está vacío.
- H-13 · `tests/rls/correr.sh` falla en Windows: `psql.exe` ignora las opciones después
  de la URL y sale con "database cuadre_test does not exist". Se arregla poniendo la
  URL al final. Tampoco limpia el prefijo `psql:D:/...`, y nada impide pasarle una URL de
  Supabase: solo lo dice un comentario, y el script borra y crea una base.

### Contradicciones en las reglas (no se tocó `docs/REGLAS/`)
- **H-14 · `sin_causa_clara` no puede salir en efectivo.** `faltante_efectivo` aplica
  cuando ninguna otra causa aplica y vale 0,60, igual a D2, así que siempre llega. Pero
  el caso de ejemplo (P09, −40.000) espera `sin_causa_clara`, igual que la demo. Con la
  tabla actual el motor falla ese caso y además dice una causa que no es causa.
- **H-15 · La causa `comision` no puede ocurrir.** Tarjeta compara pagos contra el
  bruto, y en bruto no hay comisión. La demo del punto 1 compara contra el neto, que la
  regla prohíbe. ¿Se compara también el neto contra el extracto? ¿Dónde?
- **H-16 · "Nada pasa a `confirmada` sin el extracto" choca con "Confirmar a mano".**
  La demo muestra "Confirmada a mano", estado que no existe en las reglas. ¿Es
  otro estado? Importa para "cero transferencias falsas aprobadas".
- **H-17 · Comprobante repetido.** `docs/MODELO_DATOS.md` pide hash único en la tabla;
  las reglas piden guardar el repetido como sospechoso. Con unicidad en la base, el
  segundo ni se guarda. Además, una foto nueva del mismo comprobante da otro hash, y el
  control no lo detecta. Falta el hash sobre datos: banco, referencia, valor y fecha.
- **H-18 · Dos avisos posibles.** Las reglas dicen que queda `pendiente`, pero
  `pendiente` solo dura hasta T1. Pasado T1 sin aviso asignado, ¿queda `sospechosa`?
- H-19 · `digitacion` está mal escrita. "9 veces un dígito" da de 9 a 81 pesos, por
  debajo de D1; debería incluir las potencias de 10. Y un cero de más da 9 veces el pago,
  no un múltiplo de 10. Corregida, sigue el riesgo: 1 de cada 9 valores redondos cumple
  por azar (45.000, 27.000) y a 0,65 pasa D2, o sea que inventaría causas.
- H-20 · El motivo de ejemplo "5 minutos de diferencia" no puede ser propuesta: con C1 y
  C2 ese cruce se confirma solo. La demo lo pone como propuesta (Redeban, 95.000).
- H-21 · "Referencia igual" tiene confianza 0,95, pero no dice cuándo es propuesta y
  cuándo automático, ni qué pasa con referencia igual y valor distinto. "Pago partido" es
  propuesta y no tiene confianza en la tabla. La demo usa 75 % y 78 %, y 82 % sin regla.
- H-22 · El 95 % no tiene denominador claro: ¿con efectivo? ¿por día o en total? El
  ejemplo de conciliación (41 de 45) da 91 % y no pasaría su propio criterio.
- H-23 · `CLAUDE.md` dice que todo lo ⚑ se lee de `empresa_config`, pero C4, D3 y D4 son
  "regla fija", y C5, T3, T4 y T5 viven en otro lado. Y hay valores sin ⚑ ni configuración:
  los 5 minutos de `duplicado`, las confianzas por causa y los 5 minutos del lector.
- H-24 · Transiciones sin definir: un aviso que llega después de T2 no coincide con
  nada y la transferencia sigue sospechosa aunque sea buena; una `rechazada` que aparece
  en el extracto no tiene salida.
- H-25 · "Reportado" cambia de sentido. En efectivo es lo contado; en tarjeta es lo que
  dice la liquidación, y lo que reportó el punto se llama "esperado". La demo usa "reportado"
  al revés. También: D1 es "mínima" pero la regla dice "supera" (¿y justo 1.000?), y
  `docs/DESIGN.md` usa Revisar para "diferencia pequeña", pero bajo D1 no se marca nada.
  ¿Ese punto sale Cuadrado o Revisar?
- H-26 · D4 calcula descuadres al cerrar y con el extracto, pero rechazar una
  transferencia crea uno en cualquier momento. ¿Y si el día ya está cerrado? El sistema
  recalcula sobre días que nadie puede editar sin permiso.

### Huecos del flujo (afectan 0002 en adelante)
- **H-27 · Sin app no hay comprobante ni cierre.** La app es de fase posterior (D-014),
  pero el recorrido empieza cuando la asesora sube el comprobante, y T1 corre desde ahí.
  Los descuadres se calculan al cerrar, y el panel no tiene cierre del día en
  `docs/pantallas/README.md`. Tampoco se dice quién saca valor y hora de la foto. ¿Cómo
  funciona la fase 1? ¿Sale del Excel diario?
- **H-28 · La base de caja y el efectivo contado no tienen dónde vivir.** Son la
  fórmula del efectivo (D3), pero no aparecen en `jornada` ni en `movimiento_caja`, y la
  pantalla de cierre de la demo no pide contar.
- **H-29 · Pagos agregados.** `pago` puede ser el total del día por medio, sin hora.
  Entonces no aplican C1 ni C2, ni `duplicado`, y todo termina como propuesta. Si Milagros
  reporta así, el 95 % es imposible. Depende de qué trae de verdad el Excel diario.
- H-30 · Las liquidaciones llegan después del cierre: al cerrar, toda la tarjeta saldría
  como descuadre. D4 solo recalcula con el extracto, no con la liquidación. Y "extracto del
  día siguiente" falla en domingos y festivos; la demo es un sábado.
- H-31 · Las consignaciones del punto salen en el extracto y podrían cruzarse con una
  transferencia del mismo valor. Falta decir cómo se clasifican.
- H-32 · Daviplata y Nequi son de fase posterior, pero si hoy se cobran así, cada pago
  quedaría `sospechosa` a los 30 minutos. ¿Qué se hace mientras tanto?
- H-33 · No se habla de zona horaria. Supabase trabaja en UTC y Colombia va 5 horas
  atrás: sin cuidado, las ventas de la noche caen en el día siguiente. Tampoco se resuelve
  un pago a las 23:55 con movimiento a las 00:03, por "misma fecha".
- H-34 · "Toda consulta pasa por RLS" no se cumple en dos casos. La llave de servicio de
  importadores y motores se la salta, y una vista normal corre con permisos de su dueño, salvo
  `security_invoker = true` en 0006. Si las `v_*` son materializadas, no tienen RLS.
- H-35 · "Deshacer" de la demo dice "sus datos se quitaron del sistema", contra D-005.
  Además, si el hash es único, un archivo deshecho no se puede volver a subir. Y ese hash
  debe ser único por empresa, no global.
- H-36 · `perfil_fuente` solo guarda columnas y no tiene vigencia, pero hace falta guardar
  hoja, fila de encabezado, codificación y filas a saltar. Para correos: remitente y asunto.
  `docs/VISION.md` dice que los formatos cambian de un día a otro.
- H-37 · Sin definir: diferencia entre `cerrada`, `conciliada` y `bloqueada`; umbral y
  canal de las alertas; estado inicial `abierto` del descuadre; `app.punto_actual()`,
  necesaria para "su punto", cuando una asesora rota de punto; y en la matriz de roles,
  quién cambia `empresa_config` y quién confirma o rechaza transferencias. La matriz
  deja a soporte confirmar conciliaciones de clientes. ¿Es lo que se quiere?

### Tareas
- H-38 · La tarea 003 corre antes de 0002: los maestros no pueden guardar `archivo_id`.
- H-39 · Un script de carga de Milagros choca con "nada específico de un cliente en el
  código". Los caminos están en el plan de la 003.
- H-40 · Los casos de control son días reales, y las reglas de datos prohíben datos
  reales en commits. Falta definir qué es "anonimizado": ¿se cambian también valores,
  fechas y puntos? Si los valores son reales, siguen siendo datos de Milagros.
- H-41 · La revisión de la tarea 002 usa el editor SQL de Supabase, que entra como
  `postgres` y se salta RLS. Ahí parecería que falla la separación. Hay que elegir el
  rol o probar con un inicio de sesión real.
- H-42 · La tarea 001 pide no cambiar el conciliador, pero si trae algo de Milagros
  adentro rompe las reglas de datos. Los caminos están en el plan de la 001.

### Documentos
- H-43 · Resuelto el 2 nov: `docs/pantallas/demo.html` traía el nombre de un punto real
  de Milagros, confirmado en el código del conciliador. Se cambió por "Punto 1". Jacobo
  confirmó que los demás datos de la demo no son reales.
- H-44 · Faltan cosas que los documentos citan: el plan maestro (`docs/VISION.md`, y los
  "pasos del plan" de tareas y modelo), los cinco archivos de `docs/FUENTES/`, y P-004 y
  P-005. D-017 reemplaza P-005, que no aparece en ningún lado, y P-004 tampoco.
- H-45 · `docs/MODELO_DATOS.md` dice 38 tablas en 9 módulos. Las 38 están bien; los
  módulos son 7. El diagrama C se titula "fases posteriores" e incluye `meta` (0003) y
  `auditoria` y `usuario` (0001).
- H-46 · La demo se aparta de `docs/DESIGN.md`, que gana: varios botones principales por
  pantalla, un tipo de botón `plain` y un tamaño de 40 px que no existen, título de 24 y
  cifra de 28 en vez de 28 y 30, y margen de 16 en vez de 24. Dice "entre 14:00 y 16:30"
  donde T2 daría 14:02 a 15:02.
- H-47 · Los estados de transferencia no coinciden. Reglas: `pendiente`, `vista_en_correo`,
  `confirmada`. Demo: Esperando banco, Verificada (con solo el aviso). Falta una tabla que
  los relacione. El glosario no incluye "referencia ya usada" como sospechosa.
- H-48 · Menores: `excel_dia` contra `excel_diario.md`; T3 dice `perfil_fuente` tipo
  `correo` y la columna es `fuente`; `DESIGN.md` habla de "borrar" en el botón de peligro;
  el botón deshabilitado tiene contraste 2,87 contra los 4,5 pedidos (los demás pares
  revisados cumplen); `tipo_venta` "mayor" contra `punto_venta` "mayorista"; agregar un
  proveedor de datáfono exige migración, por el `check` de `bold` y `redeban`.
- H-49 · Datos personales: `CLAUDE.md` dice "con permiso", pero no dónde consta. Hay
  nombres de asesoras y de quienes transfieren, en un servicio que quizá esté fuera de
  Colombia. Vale la pena confirmar por escrito el permiso de Milagros (Ley 1581). No es
  una opinión legal, solo una duda para revisar.
- H-50 · Resuelto el 2 nov: Apple Design quedó instalado a nivel de usuario, con el
  binario que trae la extensión de VS Code, porque `/plugin` no funciona en el chat de
  esa extensión. UI UX Pro Max ya estaba como skill en `~/.claude/skills/`. Sigue
  pendiente aclarar en `docs/DESIGN.md`, sección 13, que los comandos van en el CLI.

## 2026-11-02 · Reglas de negocio
Hecho:
- Reglas de conciliación, descuadres y transferencias redactadas completas, con
  los supuestos marcados ⚑.
- Nueva tabla `empresa_config` en 0001 para esos valores (D-017). 20 pruebas pasan.
Falta:
- Jacobo confirma los supuestos ⚑ y arma los casos de control (tarea 004).
Dudas:
- Formato real de las liquidaciones de Bold y Redeban y de los correos de aviso.

## 2026-11-02 · Nombre y logo
Hecho:
- El producto se llama Tino (D-015). Repositorio renombrado.
- Logo "Visto bueno" elegido (D-016). SVG y PNG en `docs/marca/`; reglas de uso en
  `DESIGN.md`, sección 0.
Falta:
- Confirmar dominio y marca libre en la SIC.
Dudas:
- Ninguna.

## 2026-11-02 · Arranque del repositorio
Hecho:
- Visión, arquitectura, modelo de datos, glosario, decisiones y diseño escritos.
- Primera migración propuesta: empresas, usuarios, permisos, auditoría y
  maestros.
- Tareas de la fase 1 escritas.
Falta:
- Revisar y aprobar la migración 0001 antes de aplicarla.
- Traer el conciliador actual al repositorio.
- Completar `docs/REGLAS/` con las reglas reales.
Dudas:
- Lenguaje de importadores y motores (P-001).
