# Reglas de conciliación con tarjetas y banco

Borrador del 2 nov 2026, reescrito con lo que mostraron los datos reales de Milagros
(reportes de mayo de 2025 a septiembre de 2026 y extractos de mayo a septiembre de
2026). Reemplaza el borrador anterior, que suponía horas y cuentas por punto que los
datos no tienen. Jacobo lo revisa: lo que lleva ⚑ todavía es un supuesto.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| C1 | Diferencia máxima entre lo que dice el reporte y lo que llegó al banco | 50 pesos | `empresa_config` (nuevo) |
| C2 | Cuántos días hábiles después puede llegar un depósito sin que sea un error | 1 | `empresa_config` (nuevo) |
| C3 | Cuántas fechas de Redeban pueden juntarse para cuadrar un abono partido | 3 | `empresa_config` (nuevo) |
| C4 | Los festivos son los de Colombia | Lista por año | Tabla de festivos (nueva) |

Los valores salen del conciliador actual, que los usaba fijos. En Tino van por empresa.

## Las dos preguntas que responde

1. **¿Se cobró lo que el punto anotó?** El Excel del día contra el reporte de Bold o
   Redeban del mismo punto.
2. **¿Llegó al banco lo que dice el reporte?** El reporte de Bold o Redeban contra el
   extracto.

Son dos cruces distintos, porque fallan por razones distintas: el primero encuentra
errores del punto, y el segundo, errores o descuentos del proveedor.

## 1. Lo anotado en el punto contra lo cobrado en el datáfono

- El Excel trae, por día, la lista de montos cobrados con tarjeta (débito y crédito) y no
  trae la hora. Por eso el cruce es **monto por monto dentro del mismo día**, contando
  cuántas veces aparece cada monto en cada lado.
- Lo que no cruza ese día se busca en el día anterior y el siguiente, pero solo entre lo
  que le **sobra** a esos días. Usar el día vecino entero inventaría cruces con montos
  que se repiten a diario.
- Un monto anotado y uno cobrado que parecen el mismo mal escrito se proponen como
  **mal digitado**: dígitos cambiados de lugar (35.900 y 39.500), un dígito distinto
  (35.900 y 36.900) o un cero de más o de menos (3.590 y 35.900).
- Los reportes de Bold traen débito o crédito, y los de Redeban tienen una columna
  `TIPO TARJETA` que parece decirlo ⚑. Hasta confirmarlo, débito y crédito se suman antes
  de cruzar, como hacía el conciliador. Separarlos encontraría ventas anotadas en la
  columna equivocada.
- Las **reversiones** de Redeban son ventas devueltas: restan.
- Un cobro de Bold `NO REALIZADO` no es una venta. El conciliador viejo los contaba en
  los reportes antiguos; Tino no.

## 2. Lo que dice el reporte contra lo que llegó al banco

### Bold
- Bold deposita en bloque: todo lo vendido en un día se consigna el **siguiente día
  hábil**. Lo de viernes, sábado, domingo y festivo llega junto.
- Se compara lo que el reporte dice que debía llegar con los abonos `PAGO INTERBANC`
  de Bold de ese día. Si la diferencia es de C1 o menos, coincide.
- Si no llegó ese día pero sí el siguiente hábil, es **"llegó un día tarde"**, no un
  faltante (C2). Pasó en julio de 2026.
- Si Bold descuenta un préstamo, el reporte lo trae en `DEDUCCIÓN DEL PRÉSTAMO`, y el
  depósito ya viene sin él. Ese valor **no es plata perdida**: se muestra aparte (D-029).
  Es propio de cada empresa y nunca va fijo.

### Redeban
- Redeban consigna por punto, franquicia y **fecha de canje**, no de venta.
- A veces parte un abono en dos o tres fechas. Si varias filas de la misma franquicia y
  el mismo punto no cuadran solas pero sí juntas, se proponen como **"cuadra junto con"**
  (C3).

## Estados de un cruce

| Estado | Cuándo |
| --- | --- |
| `confirmada` | Coincide el mismo día, sin dudas |
| `propuesta` | Llegó otro día, parece mal digitado, cuadra junto con otras fechas, o llegó un día tarde |
| `rechazada` | Una persona dijo que no corresponde |
| sin pareja | No apareció en ningún lado: pasa a descuadres |

Una propuesta nunca se confirma sola (D-006).

## Lo que nunca se hace
- Inventar la hora de un cobro que no la trae.
- Usar el conciliador viejo como la verdad en Bold: el que decide es el **extracto**.
- Contar como venta un cobro no realizado, o como faltante un descuento del préstamo.
- Cruzar datos de empresas distintas, o borrar un cruce: se rechaza y queda en el historial.

## Lo que se vio y falta explicar
- En agosto y septiembre de 2026, tres bloques de Bold llegaron unos miles de pesos por
  debajo de lo que dice el reporte. Julio no tuvo esa diferencia. Hay que preguntarle a
  Bold.

## Casos de control
Jacobo elige 10 días ya conciliados a mano, idealmente con un fin de semana, un festivo,
un día con préstamo y una reversión. Cada caso va en
`tests/casos/conciliacion/AAAA-MM-DD_punto.json` con el resultado esperado.

Criterio: ningún cruce que Jacobo marcó como incorrecto sale confirmado, y todo lo que el
banco confirma queda conciliado sin intervención.
