# Reglas de descuadres

Borrador del 2 nov 2026, reescrito con lo que hace el conciliador actual sobre el Excel
diario de Milagros y lo que mostraron los datos reales. Reemplaza el borrador anterior,
que tenía causas que nunca podían ocurrir. Jacobo lo revisa: lo que lleva ⚑ todavía es un
supuesto.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| D1 | Hasta cuánto se considera que el día cuadra | 100 pesos | `empresa_config` (cambia el actual) |
| D2 | Qué parte del descuadre debe explicar una causa para dar el día por explicado | 80 % | `empresa_config` (nuevo) |
| D3 | El descuadre del día es el que calcula el Excel del punto | Sí | Regla fija |
| D4 | Billetes que se revisan para un error de conteo | 2.000 a 100.000, hasta 3 | `empresa_config` (nuevo) |
| D5 | Cuándo dos días seguidos se compensan | Desde 1.000 pesos; la suma de los dos queda en 500 pesos o en el 25 % del mayor | `empresa_config` (nuevo) |
| D6 | Suma de precios que se muestra como pista | Desde 1.000 pesos, de 1 a 3 productos, hasta 3 combinaciones | `empresa_config` (nuevo) |

Los valores salen del conciliador actual.

## Qué es un descuadre

La diferencia entre lo que el punto **tiene** y lo que **debía tener** en el día:
total de caja menos valor de lo vendido. **Negativo: falta plata. Positivo: sobra.** Se
calcula por día y por punto (D3). Si es de D1 o menos, el día **cuadra**.

## Estados del día

| Estado | Cuándo |
| --- | --- |
| Cuadra | El descuadre es de D1 o menos |
| Explicado | La causa más fuerte explica al menos D2 del descuadre |
| **Sin causa clara** | Nada lo explica lo suficiente. Se dice así, sin inventar |

**Las causas no se suman.** Son explicaciones alternativas del mismo faltante: cuenta la
que más explica. Sumarlas daría una explicación que no existe.

## Causas

Una causa trae siempre su prueba: la celda, el cobro o la línea del banco.

| Causa | Cómo se detecta | ¿Cuenta para explicar? |
| --- | --- | --- |
| Transferencia que no llegó | Anotada en el Excel y no está en el banco ese día ni los vecinos | Sí |
| Cobrada sin anotar | Está en el banco o el datáfono y no en el Excel | Sí, si falta plata |
| Venta con tarjeta que no aparece | Anotada y no está en el reporte de Bold o Redeban | Sí |
| Monto mal digitado | Un monto anotado y uno real que parecen el mismo mal escrito | Sí |
| Compensación entre días | Un día sobra y el anterior o el siguiente falta un monto parecido (D5). Vecino es la hoja anterior o siguiente del libro | Sí |
| Error de billete | El descuadre es de 1 a 3 billetes de la misma denominación (D4) | Sí |
| Combinación de precios | El descuadre es la suma de 1 a 3 precios de productos del punto | **No**: casi cualquier monto redondo cuadra así; se muestra como pista |

## Señales (algo para revisar, aunque el día cuadre)

- Consignación anotada que no aparece en el extracto de ese día ni del siguiente.
- Unidades facturadas en Siigo que no están en el Excel, o al revés.
- Formas de pago en Siigo que no coinciden con lo anotado.
- Fórmulas del Excel cambiadas o corridas, y errores de planilla que se repiten. Esto es
  propio del Excel de cada empresa: va en su lector, no en el motor.
- Faltantes sin causa clara repetidos con la misma asesora, o descuentos, regalos y
  devoluciones muy por encima del promedio. **Una señal dice "revisar", nunca acusa.**

## Quién trabajó el día

Sale del Excel. Si dice solo un nombre corto que puede ser de dos personas, el día queda
**por resolver**, sin pegárselo a nadie (D-032). Los días con "Domingo", "Festivo" o "No
abrió" no tienen asesora.

## Reglas

- Un descuadre no se borra. Termina en uno de estos estados, siempre con nota y con quién
  lo hizo: **explicado** (una persona confirmó la causa), **resuelto** (la plata apareció o
  se corrigió el registro) o **aceptado** (se asume la diferencia).
- Cuando llega información nueva, como el extracto o un reporte, los descuadres abiertos
  se recalculan. Si la diferencia desaparece, pasa a resuelto con la nota "Se resolvió con
  datos nuevos".
- Un día con descuadres abiertos se puede cerrar, pero queda marcado.

## Casos de control

Jacobo elige días de Milagros cuya causa ya conoce, idealmente uno por causa, y al menos
uno sin causa clara. Cada caso va en `tests/casos/descuadres/AAAA-MM-DD_punto.json`:

```json
{
  "fecha": "2026-10-14",
  "punto": "P09",
  "descuadre": -40000,
  "estado_esperado": "sin_causa_clara",
  "causa_esperada": null
}
```

Criterio: el motor acierta el estado y la causa en los casos de control, y nunca inventa
una causa donde el caso dice "sin causa clara".
