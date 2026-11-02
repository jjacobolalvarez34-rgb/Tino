# Reglas de descuadres

Redactadas por Claude el 2 nov 2026. Los valores marcados ⚑ son supuestos
razonables que Jacobo confirma contra el Excel diario real. El código los toma
de configuración por empresa.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| D1 | Diferencia mínima para marcar un descuadre | 1.000 pesos | `empresa_config.desc_umbral` |
| D2 | Confianza mínima para proponer una causa | 0,60 | `empresa_config.desc_confianza_min` |
| D3 | El efectivo esperado incluye la base de caja del día | Sí | Regla fija |
| D4 | Los descuadres se calculan al cerrar el día y se recalculan cuando llega el extracto | Sí | Regla fija |

## Qué es un descuadre

La diferencia entre lo esperado y lo reportado en una jornada, para un medio de
pago o para el total del día. Solo se marca si su valor absoluto supera D1.

| Medio | Esperado | Reportado |
| --- | --- | --- |
| Efectivo | Base + ventas en efectivo − gastos − consignaciones − retiros | Efectivo contado al cierre |
| Tarjeta | Pagos con tarjeta reportados por el punto | Bruto de las liquidaciones de Bold y Redeban del punto |
| Transferencia | Transferencias reportadas por el punto | Movimientos del extracto o avisos confirmados |
| Total del día | Suma de ventas netas (cobradas de verdad) | Suma de todo lo recibido por todos los medios |

Diferencia = reportado − esperado. Negativa: falta plata. Positiva: sobra.

## Causas y cómo se detectan

El motor evalúa todas las causas y se queda con la de mayor confianza. Si
ninguna llega a D2, la causa es `sin_causa_clara`.

| Código | Causa | Cómo se detecta | Confianza |
| --- | --- | --- | --- |
| `transf_no_llego` | La transferencia no llegó al banco | Hay comprobante del valor exacto sin aviso ni línea de extracto pasado el tiempo límite | 0,90 |
| `otro_medio` | Se pagó por otro medio del registrado | Sobra en un medio exactamente lo que falta en otro, mismo día y punto | 0,85 |
| `comision` | Comisión del datáfono no descontada | La diferencia es igual a la suma de comisiones y retenciones del día | 0,70 |
| `duplicado` | Pago registrado dos veces | Dos pagos iguales, mismo medio, menos de 5 minutos de diferencia | 0,80 |
| `digitacion` | Error al escribir un valor | La diferencia es 9 veces un dígito (dígitos invertidos) o un múltiplo de 10 de un pago (un cero de más o de menos) | 0,65 |
| `sin_factura` | Venta sin factura en Siigo | Pago recibido sin venta registrada que lo cubra | 0,60 |
| `faltante_efectivo` | Falta efectivo sin explicación | Diferencia solo en efectivo y ninguna causa anterior aplica | 0,60 |
| `sin_causa_clara` | No hay explicación | Ninguna causa llega a D2 | — |

## Reglas

- Cada causa propuesta guarda su confianza y al menos una evidencia: el pago,
  movimiento o venta concreto que la sustenta.
- Si dos causas explican lo mismo, se muestra la de mayor confianza y la otra se
  guarda como alternativa.
- Un descuadre no se borra. Termina en uno de estos estados, siempre con nota y
  con quién lo hizo:
  - `explicado`: una persona confirmó la causa.
  - `resuelto`: la plata apareció o se corrigió el registro.
  - `aceptado`: se asume la pérdida o la diferencia.
- Cuando llega el extracto del día siguiente (D4), los descuadres abiertos se
  recalculan. Si la diferencia desaparece, el descuadre pasa a `resuelto` solo,
  con la nota "Se resolvió con el extracto".
- Un día con descuadres abiertos se puede cerrar, pero queda marcado.

## Casos de control

Jacobo elige días de Milagros cuya causa real ya conoce, idealmente uno por
causa. Cada caso va en `tests/casos/descuadres/AAAA-MM-DD_punto.json`:

```json
{
  "fecha": "2026-10-14",
  "punto": "P09",
  "medio": "efectivo",
  "diferencia_esperada": -40000,
  "causa_esperada": "sin_causa_clara"
}
```

Criterio: el motor acierta la causa en los casos de control y nunca inventa una
causa donde el caso dice `sin_causa_clara`.
