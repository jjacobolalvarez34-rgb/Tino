# Reglas de verificación de transferencias

Redactadas por Claude el 2 nov 2026. Los valores marcados ⚑ son supuestos que
Jacobo confirma con correos y extractos reales. El código los toma de
configuración por empresa.

## Supuestos a confirmar

| ⚑ | Supuesto | Valor inicial | Dónde se configura |
| --- | --- | --- | --- |
| T1 | Tiempo sin aviso del banco para marcar sospechosa | 30 minutos | `empresa_config.transf_minutos_sospecha` |
| T2 | Ventana para que un aviso coincida con un comprobante | ±30 minutos | `empresa_config.transf_ventana_aviso` |
| T3 | Bancolombia envía un correo de aviso por cada transferencia recibida | Sí | `perfil_fuente` tipo `correo` |
| T4 | El extracto del día siguiente trae la referencia de la transferencia | Sí | `docs/FUENTES/bancos.md` |
| T5 | Daviplata y Nequi | Fase posterior | — |

## Recorrido de una transferencia

1. **Comprobante:** la asesora sube la foto o el reporte del pago.
2. **Aviso del banco:** llega el correo del banco con valor, hora y referencia.
3. **Extracto:** al día siguiente, la línea del extracto confirma.

## Estados

| Estado | Cuándo |
| --- | --- |
| `pendiente` | Hay comprobante y aún no pasa T1 |
| `vista_en_correo` | Un aviso del banco coincide con el comprobante |
| `confirmada` | El extracto confirma el movimiento |
| `sospechosa` | Pasó T1 sin aviso, o el comprobante está repetido, o la referencia ya se usó |
| `rechazada` | Una persona revisó y no es válida; pasa a descuadres |

## Cuándo coincide un aviso

Todas deben cumplirse:
- Mismo valor exacto.
- Misma cuenta de recaudo (por los últimos 4 dígitos o por el buzón que recibió el aviso).
- Hora del aviso dentro de T2 respecto a la hora del comprobante.
- El aviso no está asignado ya a otro pago.

Si hay dos avisos que sirven, ninguno se asigna solo: la transferencia queda
`pendiente` y aparece para revisión.

## Reglas

- Un comprobante cuyo hash ya existe en la empresa queda `sospechoso` siempre,
  aunque llegue un aviso.
- Una misma referencia bancaria no puede verificar dos pagos.
- Nada pasa a `confirmada` sin el extracto, aunque el aviso haya llegado.
- Confirmar a mano exige una nota y queda en auditoría.
- Rechazar una transferencia crea el descuadre correspondiente en el punto.
- Una transferencia `sospechosa` que luego aparece en el extracto pasa a
  `confirmada`, con la nota "Confirmada por extracto después de sospecha".

## Lector de correos

- Acceso al buzón de solo lectura, con autorización escrita de la empresa.
- El remitente, el asunto y el formato del correo se documentan en
  `docs/FUENTES/correos_notificacion.md` a partir de correos reales, y se
  configuran en `perfil_fuente`. Nada de esto va fijo en el código.
- El lector revisa el buzón cada 5 minutos.
- Un correo que no se puede leer va a `error_importacion` y genera una alerta.

## Casos de control

Jacobo elige transferencias reales de octubre: varias normales, una que no llegó
y, si existe, un comprobante repetido. Cada caso va en
`tests/casos/transferencias/` con el comprobante anonimizado, el aviso, la línea
del extracto y el estado esperado.

Criterio: cero transferencias falsas aprobadas en los casos de control.
