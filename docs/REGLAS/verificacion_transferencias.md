# Reglas de verificación de transferencias

Borrador del 2 nov 2026, reescrito con lo que mostraron los datos reales de Milagros.
Reemplaza el borrador anterior, que suponía comprobantes con hora y una cuenta por punto.
Jacobo lo revisa: lo que lleva ⚑ todavía es un supuesto.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| T1 | Días vecinos donde se busca una transferencia antes de decir que no llegó | 1 antes y 1 después | `empresa_config` (nuevo) |
| T2 | Los pagos sin código (Nequi, PSE, interbancarios) se asignan a mano | Sí | Regla fija |
| T3 | Un punto que anotó transferencias y no tiene ninguna en el banco, el mismo día que llegan pagos sin código, puede tener el QR cambiado | Sí | Regla fija |
| T4 | Verificación en minutos con los correos del banco | Fase posterior | — |

## Cómo funciona hoy (fase 1, D-024)

Se revisa **a la mañana siguiente**, con dos fuentes:

1. **Lo anotado:** la lista de transferencias de cada punto en el Excel del día. Trae
   montos, sin hora ni referencia.
2. **Lo que llegó:** el extracto de Bancolombia. Hay **una sola cuenta para todos los
   puntos**. Cada pago con QR o llave trae una referencia, y sus **últimos 4 dígitos dicen
   de qué punto es** (`codigo_recaudo`, D-026).

## El cruce

- Por punto y por día, **monto por monto**, contando repeticiones. Es el mismo cruce de
  las tarjetas, sin horas.
- Lo que no cruza se busca en el día anterior y el siguiente (T1), solo entre lo que le
  sobra a esos días: los pagos de la noche suelen caer en otra fecha.
- Un monto anotado y uno recibido que parecen el mismo mal escrito se proponen como mal
  digitado.

## Resultados por transferencia

| Resultado | Qué significa | Qué hace Tino |
| --- | --- | --- |
| Llegó | Está en el extracto del mismo día | Confirmada |
| Llegó otro día | Está el día anterior o el siguiente | Propuesta |
| Mal digitada | Parece la misma con un número distinto | Propuesta |
| **No llegó** | No está en ninguno de los tres días | **Sospechosa**: pasa a descuadres |
| Llegó sin anotar | Está en el banco y no en el Excel | Señal para revisar |

## Pagos sin código

- Nequi, PSE e interbancarios llegan **sin referencia de punto**. Tino no adivina de qué
  punto son: quedan como "sin origen" hasta que alguien los asigne (T2).
- Si ese día un punto tiene transferencias que no llegaron por el mismo monto que un pago
  sin código, Tino lo sugiere como posible pareja, sin confirmarlo.
- Si un punto anotó transferencias y no recibió ninguna con su código, el mismo día que
  llegan pagos sin código, puede que le hayan cambiado el QR (T3).

## Reglas
- Una misma línea del banco no verifica dos transferencias.
- Nada pasa a confirmada sin el extracto.
- Confirmar a mano exige una nota y queda en auditoría.
- Una transferencia sospechosa que aparece después en el extracto pasa a confirmada, con
  la nota "Confirmada por extracto después de sospecha".

## Fase posterior: verificación en minutos
Con acceso de solo lectura al buzón de avisos del banco, autorizado por escrito, Tino
podría verificar en minutos y no al día siguiente (T4). Necesita correos reales para
definir formato y tiempos. Daviplata y Nequi directos también van ahí.

## Casos de control
Jacobo elige transferencias reales: varias normales, una que llegó al día siguiente, una
que no llegó y, si existe, un pago sin código que era de un punto. Van en
`tests/casos/transferencias/` con el resultado esperado.

Criterio: cero transferencias que no llegaron marcadas como confirmadas.
