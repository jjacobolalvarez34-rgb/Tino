# Contrato del núcleo de cálculo

La lógica que decide sobre la plata existe en dos lenguajes (D-022):
`motores/nucleo/` en Python y `motores/nucleo_ts/` en TypeScript. Este documento
dice qué debe hacer cada función. Ninguno de los dos es el original del otro: si
dan distinto, una de las dos está mal, o este documento está incompleto.

Lo que hace esta primera versión es el comportamiento del conciliador actual
(`motores/conciliador/`), sin Excel, sin PDF y sin interfaz. Donde el conciliador
difiere de `docs/REGLAS/`, aquí manda el conciliador hasta que Jacobo confirme las
reglas (tarea 004). Ver H-51 a H-56 en `docs/BITACORA.md`.

## Reglas generales

- **Dinero:** pesos enteros. Nunca decimales ni `float`, ni siquiera en un paso
  intermedio. Los porcentajes son enteros (80 significa 80 %) y se compara
  multiplicando, no dividiendo.
- **Límite de los montos:** ningún monto pasa de 90 billones de pesos
  (90.000.000.000.000). Así `100 × monto` sigue siendo exacto en los dos lenguajes:
  TypeScript pierde precisión con enteros de más de 9 mil billones. `a_pesos`
  devuelve `null` si el valor pasa ese límite.
- **Montos de las listas:** enteros mayores o iguales a cero.
- **Fechas imposibles:** como `2026-02-30`, dan error en `dia_habil_siguiente` y en
  `bloques_deposito`. El mensaje puede variar entre lenguajes; que falle, no.
- **Sin efectos:** ninguna función lee archivos, base de datos, reloj ni variables
  de entorno, y ninguna cambia lo que recibe.
- **Sin valores fijos:** tolerancias y porcentajes siempre llegan como parámetro.
- **Fechas:** texto `AAAA-MM-DD`. Sin horas ni zona horaria: en TypeScript se
  calcula en UTC para que el cambio de zona no corra un día.
- **Texto en expresiones regulares:** solo ASCII. `[0-9]`, no clases Unicode. `\s` y
  `\b` también son solo ASCII, `.` no incluye el salto de línea, y `$` significa el
  final exacto del texto: un salto de línea al final no cuenta como final.
  "Espacio" son estos seis: espacio, `\t`, `\n`, `\r`, `\f` y `\v`.
- **Orden:** el orden de las listas de salida es parte del contrato.
- **Nombres:** todo en `snake_case`, igual en los dos lenguajes.

Un **ítem** es `{"monto": entero, "id": texto}`. El `id` es único dentro de una
llamada. Dos ítems son el mismo si tienen el mismo `id`.

Cada lenguaje expone `ejecutar(funcion, entrada)`, que recibe el nombre y un objeto
con los parámetros, y devuelve la salida en JSON.

## Funciones

### `a_pesos` · `{texto}` → entero o `null`
Convierte el texto de un valor en pesos enteros, sin pasar por `float`.
- Válido si cumple `^-?[0-9,]*[0-9](\.[0-9]+)?$`. Si no, `null`.
- Las comas de miles se ignoran. El punto separa los decimales.
- Redondea por el primer decimal: 5 o más se aleja de cero, menos de 5 se queda.
  `2.5` da 3, `-2.5` da -3, `1234.49` da 1234.

### `restar` · `{a, b}` → `{sobran_a, sobran_b}`
Empareja dos listas de ítems monto por monto, contando repeticiones.
1. Agrupa `b` por monto. Cada grupo conserva el orden de `b`, y los grupos quedan en
   el orden en que apareció cada monto por primera vez.
2. Recorre `a` en orden. Si el grupo de su monto tiene ítems, quita **el último** de
   ese grupo. Si no, el ítem de `a` va a `sobran_a`.
3. `sobran_b` son los grupos restantes, uno tras otro, en ese mismo orden.

### `parecidos` · `{a, b}` → booleano
¿Pudo ser un error al digitar? Ambos son enteros mayores o iguales a cero.
- Si son iguales: falso.
- Si tienen la misma cantidad de dígitos: verdadero si tienen los mismos dígitos en
  otro orden, o si difieren en exactamente una posición.
- Si no: verdadero si uno es exactamente 10 veces el otro.

### `sobrantes_vecinos` · `{vecinos}` → `{ext_sobra, excel_sobra}`
Lo que le sobra a los días vecinos. Usar el día vecino entero daría falsos "llegó
otro día" con montos que se repiten a diario. Cada vecino es
`{cubre, tiene_excel, anotado, externo}`, y se recorren en el orden recibido:
- Si `cubre` es falso: si `tiene_excel`, todo `anotado` va a `excel_sobra`. Sigue.
- Si `tiene_excel` es falso: todo `externo` va a `ext_sobra`. Sigue.
- Si no: `restar(anotado, externo)`. Lo que sobra de `anotado` va a `excel_sobra` y
  lo que sobra de `externo` va a `ext_sobra`.

### `cruzar` · `{anotado, externo, ext_vecinos, excel_vecinos}` → resultado
Lo que el punto anotó en el día contra lo externo (banco o datáfono). Devuelve
`{no_llegaron, no_anotadas, otro_dia, mal_digitadas}`.
1. `no_llegaron`, `no_anotadas` = `restar(anotado, externo)`.
2. Si `no_llegaron` tiene ítems:
   `sigue` = sobran_a de `restar(no_llegaron, ext_vecinos)`.
   Cada ítem de `no_llegaron` cuyo `id` no esté en `sigue` va, en orden, a `otro_dia`
   como `{"donde": "externo_otro_dia", "monto": m, "id": i}`. Después
   `no_llegaron` = `sigue`. Se separa por `id`: el conciliador lo hacía por monto y, con
   montos repetidos, señalaba la fila equivocada.
3. Igual con `no_anotadas` y `excel_vecinos`, usando `"anotado_otro_dia"`.
4. Parejas mal digitadas: por cada ítem de `no_llegaron`, en orden, se busca el
   primero de `no_anotadas` que sea `parecidos`. Si hay, se quitan los dos y se
   agrega `{"anotado": ítem, "externo": ítem}` a `mal_digitadas`.

### `dia_habil_siguiente` · `{fecha, festivos}` → fecha
El primer día después de `fecha` que no sea sábado, domingo ni esté en `festivos`.

### `bloques_deposito` · `{fechas, festivos}` → lista
Agrupa días de venta por el día en que se consignan. Primero quita las fechas
repetidas. Para cada fecha, su consignación es `dia_habil_siguiente`. Devuelve `{"consignacion", "dias", "grande"}` ordenado por
consignación, con `dias` ordenados y `grande` verdadero si hay más de un día.

### `coincide_deposito` · `{banco, esperado, tolerancia, porcentajes}` → booleano
Verdadero si para algún `p` de `porcentajes` se cumple
`abs(100 × banco − p × esperado) ≤ 100 × tolerancia`. Enteros, sin dividir. Cada `p`
va de 0 a 100, para que el cálculo siga siendo exacto en los dos lenguajes.

### `cruces_redeban` · `{filas, tolerancia, max_cruce}` → lista
Cada fila es `{codigo, franquicia, fecha, esperado, banco}`. Devuelve las mismas
filas, en el mismo orden, con cuatro campos más:
1. `coincide`: `abs(banco − esperado) ≤ tolerancia`.
   `sin_datos`: `banco` y `esperado` son 0. `cruzado`: falso. `cruza_con`: `[]`.
2. Agrupa por `(codigo, franquicia)`, en orden de aparición, las filas sin `coincide`
   y sin `sin_datos`. Los grupos de menos de 2 filas se saltan.
3. Para `n` de 2 hasta `min(max_cruce, tamaño del grupo)`, y para cada combinación de
   `n` filas del grupo en orden lexicográfico: se salta si alguna ya está `cruzado`.
   Si `abs(suma de banco − suma de esperado) ≤ tolerancia`, todas quedan `cruzado` y
   su `cruza_con` es la lista de fechas de la combinación, en su orden.

### `estado_dia` · `{descuadre, causas, tolerancia_cuadra, porcentaje_explicado, reglas_sin_peso}` → resultado
Cada causa es `{regla, monto}`. Devuelve `{estado, explicado, sin_explicar}`.
Las causas son hipótesis alternativas: cuenta la que más explica, no la suma.
1. `e` = el mayor `abs(monto)` entre causas con monto distinto de 0 y regla fuera de
   `reglas_sin_peso`, o 0 si no hay. Luego `e` = `min(abs(descuadre), e)`.
2. Si `abs(descuadre) ≤ tolerancia_cuadra`: `cuadra`.
   Si no, si `100 × e ≥ porcentaje_explicado × abs(descuadre)`: `explicado`.
   Si no: `sin_explicar`.
3. `signo` = 1 si `descuadre ≥ 0`, si no -1. `explicado` = `signo × e`.
   `sin_explicar` = `descuadre − signo × e`.

### `leer_linea_transferencia` · `{linea}` → objeto o `null`
Lee una línea del movimiento de Bancolombia.
1. Quita espacios de los extremos. Debe cumplir
   `^(?P<fecha>[0-9]{4}/[0-9]{2}/[0-9]{2})\s+(?P<tipo>PAGO QR|PAGO LLAVE)\s+(?P<resto>.*)$`.
   Si no, `null`.
2. Valor: busca en `resto`
   `(-?[0-9.]*[0-9],[0-9]{3}(?:,[0-9]{3})*\.[0-9]{2}|-?[0-9]+\.[0-9]{2})\s*$`.
   Si no aparece, `null`. Se convierte con `a_pesos`; si eso da `null`, también `null`.
3. Referencia: la primera coincidencia de `\b([0-9]{7,10})\b` en lo que hay antes del
   valor, o `null`.
4. Devuelve `{"fecha": "AAAA-MM-DD", "tipo", "referencia", "valor"}`.

### `punto_por_referencia` · `{referencia, puntos}` → texto o `null`
Cada punto es `{punto, codigo}`. Compara los últimos 4 caracteres de `referencia`
contra los últimos 4 de cada `codigo`. Si dos puntos comparten esos dígitos, gana el
último de la lista. Sin coincidencia, `null`. `referencia` es texto: una línea sin
referencia (`null`) no se manda aquí, va directo a "sin identificar".

## Cómo se prueba

- `tests/casos/motor/casos.json`: casos escritos a mano, con datos inventados. Cada
  uno es `{"funcion", "nombre", "entrada", "esperado"}`. Los dos lenguajes corren este
  mismo archivo.
- `motores/comparar_lenguajes.py`: genera miles de entradas al azar y exige que los
  dos lenguajes den exactamente lo mismo.

Una función nueva se agrega aquí primero, con sus casos, y después en los dos
lenguajes.
