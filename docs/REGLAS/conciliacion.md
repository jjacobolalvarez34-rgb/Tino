# Reglas de conciliación

Redactadas por Claude el 2 nov 2026 con lo que se sabe del conciliador actual.
Los valores marcados ⚑ son supuestos razonables: Jacobo los confirma o corrige
contra el conciliador y un archivo real. Hasta entonces, el código los toma de
configuración por empresa, nunca escritos a mano en el código.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| C1 | Diferencia máxima de hora para cruce automático con datáfono | 10 minutos | `empresa_config.conc_minutos_datafono` |
| C2 | Diferencia máxima de hora para cruce automático con transferencia | 30 minutos | `empresa_config.conc_minutos_transferencia` |
| C3 | Diferencia máxima de valor para proponer un cruce dudoso | 1.000 pesos | `empresa_config.conc_tolerancia_valor` |
| C4 | Una liquidación de Bold o Redeban puede agrupar varios pagos en un solo abono | Sí | Regla fija |
| C5 | Cada línea de la liquidación trae bruto, comisión, retenciones y neto | Sí | `docs/FUENTES/datafonos.md` |

## Qué es conciliar

Cruzar cada pago reportado por un punto con uno o varios movimientos externos
(extracto, liquidación de Bold o Redeban, aviso de transferencia) que prueban que
la plata llegó.

## Estados

| Estado | Significado |
| --- | --- |
| `propuesta` | El sistema cree que coinciden, pero una persona debe confirmar. |
| `confirmada` | Una persona confirmó, o el cruce es exacto según las reglas automáticas. |
| `rechazada` | Una persona dijo que no coinciden. El pago queda sin pareja. |

## Orden de cruce

El motor recorre los pagos del día de cada punto en este orden, y un movimiento
ya asignado no se vuelve a usar por encima de su valor:

1. **Por referencia:** misma referencia bancaria o de datáfono → candidato fuerte.
2. **Por terminal o cuenta:** el movimiento salió del datáfono o llegó a la cuenta
   del mismo punto.
3. **Por valor y hora:** mismo valor dentro de la ventana de hora (C1 o C2).
4. **Agrupado:** un abono cuyo valor es la suma exacta de varios pagos del mismo
   punto y día (C4). Se prueba con los pagos ordenados por hora, sin combinaciones
   arbitrarias: como máximo grupos de pagos consecutivos.

## Cruce automático (queda `confirmada`)

Solo cuando se cumplen todas:
- Mismo valor exacto, comparado contra el **bruto** del movimiento.
- Mismo punto, por datáfono o por cuenta de recaudo.
- Misma fecha y hora dentro de la ventana (C1 datáfono, C2 transferencia).
- Un solo candidato posible. Si hay dos movimientos que sirven, ninguno se
  confirma solo.

## Cruce sugerido (queda `propuesta`)

Cualquiera de estos casos:
- Mismo valor, pero hora fuera de la ventana y dentro del mismo día.
- Mismo valor y hora, pero el punto no se puede saber (cuenta general).
- Diferencia de valor menor o igual a C3.
- Abono agrupado que cubre varios pagos (C4).
- Un pago partido en dos o más movimientos que suman su valor.

Cada propuesta guarda su `confianza` (0 a 1) y el motivo en palabras, por
ejemplo "5 minutos de diferencia" o "el abono agrupa 3 pagos".

Confianza sugerida:

| Situación | Confianza |
| --- | --- |
| Referencia igual | 0,95 |
| Valor y punto iguales, hora fuera de ventana | 0,80 |
| Abono agrupado exacto | 0,75 |
| Diferencia de valor ≤ C3 | 0,70 |
| Punto desconocido | 0,60 |

## Comisiones y retenciones

- Bold y Redeban abonan el neto: bruto − comisión − retefuente − reteIVA − reteICA.
- El cruce siempre es contra el **bruto**. El neto solo sirve para cuadrar contra
  el extracto bancario.
- Comisión y retenciones se guardan tal como vienen en la liquidación. No se
  calculan con tarifas.

## Lo que nunca se hace

- Confirmar sola una propuesta.
- Asignar un mismo movimiento a pagos que suman más que su valor.
- Cruzar pagos y movimientos de empresas distintas.
- Borrar una conciliación: se rechaza y queda en el historial.

## Casos de control

Antes de dar por terminado el motor, se prueba con 10 días reales de Milagros ya
conciliados a mano por Jacobo. Cada caso va en
`tests/casos/conciliacion/AAAA-MM-DD_punto.json` con este formato:

```json
{
  "fecha": "2026-10-14",
  "punto": "P04",
  "archivos": ["excel_dia.xlsx", "bold.xlsx", "bancolombia.csv"],
  "esperado": {
    "confirmadas": 41,
    "propuestas": 3,
    "sin_pareja": 1,
    "notas": "La transferencia de 85.000 de las 14:32 no llegó."
  }
}
```

Criterio: el motor no puede confirmar ningún cruce que Jacobo marcó como
incorrecto, y debe confirmar solo al menos el 95 % de los pagos.
