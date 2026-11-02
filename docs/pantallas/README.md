# Pantallas de referencia

Así deben verse las pantallas. `demo.html` es un prototipo que funciona: se abre
en cualquier navegador y se puede tocar todo. Las cifras son inventadas.

Las reglas visuales (colores, tamaños, márgenes, componentes) están en
`docs/DESIGN.md`. Si el prototipo y DESIGN.md no coinciden, gana DESIGN.md.

## Panel web (dueño, encargada, finanzas)

| Pantalla | Qué muestra | Lo que no puede faltar |
| --- | --- | --- |
| Inicio | Ventas del día, pagos conciliados, descuadres abiertos, transferencias por verificar, ventas por punto | Lo que necesita atención arriba; tabla con totales; "Copiar como números" |
| Descuadres | Lista a un lado, detalle al otro: reportado contra lo que llegó, confianza, pruebas, acciones | "Sin causa clara" cuando no hay causa; nada se borra |
| Transferencias | Tabla filtrable y el recorrido de cada una: comprobante, aviso del banco, extracto | Acciones para la sospechosa: pedir comprobante, confirmar con nota, rechazar |
| Conciliación | Lo conciliado solo, lo que está por confirmar y lo que quedó sin pareja | Confirmar y "No es" en cada propuesta |
| Comisiones y retenciones | Mes por punto: vendido, comisión, retefuente, reteIVA, reteICA y neto | Filtro por Bold o Redeban; copiar como números |
| Archivos | Zona para subir reportes, historial con "Deshacer" y nombres por resolver | Aviso de archivo repetido; resolver un alias en un toque |
| Ventas con tarjeta | Vendido, neto, promedio por día, venta típica; tabla por punto; ventas por hora, día de la semana y día. Referencia: `tablero_ventas.html`, con cifras inventadas | Decir que no incluye efectivo ni transferencias; decir que la hora es solo de Bold; copiar como números |

## App de las asesoras

| Pantalla | Qué muestra | Lo que no puede faltar |
| --- | --- | --- |
| Cierre del día | Total del día por medio de pago, transferencias con su estado, subir comprobante, cerrar el día | Aviso si una transferencia no está confirmada antes de cerrar |
| Registrar factura | Número de factura Siigo, total, descuento, cobrado de verdad, medio de pago | Funciona sin señal y avisa que se guardó en el celular |

## Pantallas que faltan por diseñar

- Ventas y asesoras, metas y cumplimiento.
- Ajustes: puntos, asesoras, productos, datáfonos, usuarios y permisos.
- Perfiles de fuente (configurar qué columna es qué).
- Inventario y horarios, en fases posteriores.
