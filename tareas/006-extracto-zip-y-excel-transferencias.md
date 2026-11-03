# 006 · Subir el .zip de Bancolombia y entregar el Excel de transferencias

Estado: por hacer (anotada el 3 nov 2026, a pedido de Jacobo).

## Objetivo

Que Tino haga con el extracto lo mismo que hoy hace el conciliador (7)
(`motores/conciliador/transferencias_core.py`), sin perder nada de lo que ya hace con
la base: subir el `.zip` tal como lo entrega Bancolombia y recibir el archivo con
nombre claro y el Excel de transferencias para pegar en el Google Sheet.

## Alcance

- En Archivos, aceptar `.zip` (y `.rar` si hay herramienta instalada) del banco: sacar
  el PDF solo, en una carpeta temporal de D:, nunca en C:. Varios PDF en un mismo
  `.zip` entran como archivos distintos.
- Guardar una copia del PDF con el nombre del conciliador:
  `Bancolombia movimientos 30 de agosto 2026.pdf` o
  `Bancolombia movimientos 30 de agosto a 31 de agosto del 2026.pdf`, sin pisar uno
  que ya exista (`(2)`, `(3)`…). Va en la carpeta de datos de la empresa (junto a
  `tino.json`), no en Documentos.
- Botón "Exportar transferencias" (en Archivos o en Transferencias) que arme
  `TRANSFERENCIAS {2026-08-30}.xlsx` con la misma forma: una hoja por fecha, cada punto
  con su código, TOTAL y los montos en columnas; fila DOMICILIOS; TOTAL GENERAL; y la
  sección "DATOS SIN ORIGEN" con descripción, punto para asignar a mano y valor. Los
  días seguidos se agrupan en el nombre (`2026-09-01 a 2026-09-30`).
- El orden de los puntos y su código salen de la base (`punto_venta`,
  `codigo_recaudo`), no de una lista en el código.

### Pagos sin origen (lo que le falta al apartado de transferencias, dijo Jacobo)

Hoy Tino solo cuenta como sin origen los PAGO QR y PAGO LLAVE cuyo código no reconoce.
El conciliador (`cierre/banco.py`, `SIN_CODIGO_RE`) también cuenta las líneas que
empiezan por `TRANSFERENCIA DESDE` (Nequi y otros) y `TRANSFERENCIA CTA`: Tino no las
lee, y esos pagos no aparecen en ningún lado. Hay que:

- Leer esas líneas del extracto como movimientos sin punto (en el contrato y en los
  dos lenguajes, como `leer_linea_transferencia`).
- Pantalla "Sin origen": cada pago sin punto, con fecha, descripción y valor, y
  "Asignar a un punto" con nota (`movimiento_externo.punto_id` ya se puede cambiar).
  Nunca se asigna solo (T2).
- Sugerir la pareja sin confirmarla: si ese día un punto tiene una transferencia que
  no llegó por el mismo monto, se muestra como posible.
- Señal de QR cambiado (T3): un punto anotó transferencias y no recibió ninguna con su
  código el mismo día que llegan pagos sin código.
- Al asignar, revisar otra vez ese día y el vecino, para que la transferencia pase de
  "no llegó" a "llegó" con la nota de quién la asignó.
- En el Excel exportado, la sección "DATOS SIN ORIGEN" con el punto ya asignado, si lo
  tiene.

Pregunta para Jacobo antes de empezar: ¿las consignaciones (`palabras_consignacion` del
conciliador) también van aquí, o se ven aparte?

## Fuera de alcance

- Cambiar cómo se reconoce el punto (últimos 4 dígitos, D-026): ya es igual en los dos.
- Escribir directo en el Google Sheet.

## Hecho cuando

- Con el `.zip` real de septiembre, Tino carga el extracto igual que con el PDF suelto
  (mismas 2.138 líneas y mismos resultados de la revisión).
- El Excel que exporta Tino para el 30 de agosto de 2026 tiene, punto por punto, los
  mismos totales que `TRANSFERENCIAS {2026-08-30}.xlsx` del conciliador (7).
- La copia del PDF queda con el nombre esperado y nada se escribe en C:.
- Con el extracto de septiembre, la lista de pagos sin origen de Tino tiene los mismos
  pagos que "DATOS SIN ORIGEN" del conciliador, incluidos los de Nequi. Al asignar uno a
  un punto, esa transferencia deja de salir como "no llegó".

## Cómo lo reviso yo (Jacobo)

Subo el `.zip` en Archivos, exporto el Excel del día y lo comparo con el del
conciliador (7) en la carpeta `D:\Admin\Downloads\conciliador (7)`.
