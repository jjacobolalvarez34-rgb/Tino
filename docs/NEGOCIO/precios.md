# Precios de Tino

Decididos por Jacobo el 19 nov 2026 (cierran P-003, ver D-053). Los valores viven en un solo
archivo, `web/lib/precios.ts`; la página pública `/precios` los lee de ahí. Si un precio cambia,
se cambia allá y aquí.

Sin datos de clientes. **IVA: no se menciona en ninguna parte hasta que Jacobo lo confirme.**

## Planes

Por punto de venta al mes, en pesos colombianos.

| Plan | Precio | Qué incluye |
|---|---|---|
| Equipo | 30.000 | Personas por punto, venta por persona, ranking y ticket, metas y cumplimiento, observaciones, evaluaciones, sesiones, compromisos y alertas de apoyo |
| Caja | 45.000 | Conciliación de tarjetas y transferencias, descuadres con causa probable o "sin causa clara", extracto, datáfonos y Excel del día en un solo cuadre, copiar a Excel |
| Completo (Caja + Equipo) | 65.000 | Todo lo anterior |

Texto principal: "Desde 30.000 por punto al mes · Mínimo 3 puntos · Implementación desde 400.000".

## Condiciones

- Mínimo 3 puntos de venta.
- Implementación desde 400.000, una sola vez (puntos, banco, datáfonos y forma de sus Excel).
- Pago anual: 12 meses por el precio de 10.
- Precio de fundador: 30 % menos, fijo por 12 meses, para los primeros 5 clientes.
- Piloto de 30 días a mitad de precio.

Cómo calcula la página (`cotizar` en `web/lib/precios.ts`): precio del plan × puntos (mínimo 3);
con fundador, × 0,7; con pago anual, el año es 10 meses y el mensual que se muestra es el año ÷ 12.
El piloto es la mitad del precio base del mes.

## Ejemplos (sin fundador, mensual)

| Puntos | Equipo | Caja | Completo |
|---|---|---|---|
| 3 | 90.000 | 135.000 | 195.000 |
| 5 | 150.000 | 225.000 | 325.000 |
| 11 | 330.000 | 495.000 | 715.000 |

## Costos fijos estimados (al mes)

| Servicio | Plan | Costo aprox. | Por qué |
|---|---|---|---|
| Supabase | Pro (organización de producción) | ~25 USD | Respaldos diarios, no se pausa por inactividad, más capacidad |
| Vercel | Pro | ~20 USD por miembro | El plan gratis (Hobby) es solo para uso no comercial |
| Dominio | — | pendiente | Cuando se compre |

tino-pruebas puede seguir en el plan gratis de Supabase: es el laboratorio.

## Lo que no se promete todavía

En la página sale como "Próximamente": funcionar sin internet, leer solos los avisos de
transferencia del correo, más bancos y datáfonos, y subir los archivos desde el celular.
