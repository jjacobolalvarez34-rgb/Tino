# motores

Los procesos que leen de la base, deciden y escriben el resultado: conciliador,
verificador de transferencias y detector de descuadres.

- `CONTRATO.md`: qué debe hacer cada función de cálculo. Se cambia primero.
- `nucleo/`: la lógica de la plata en Python. La usa el `.exe`.
- `nucleo_ts/`: la misma lógica en TypeScript, lista para la web (D-022).
- `comparar_lenguajes.py`: exige que los dos den exactamente lo mismo.
- `conciliador/`: el programa actual de Milagros, copiado sin cambiar su lógica
  (tarea 001). Es la referencia, no el motor del producto.

## Reglas

- Las reglas de negocio están en `docs/REGLAS/`. Si una regla no está ahí, se
  pregunta; no se inventa.
- Los valores marcados ⚑ se leen de `empresa_config`. Nunca van fijos en el código.
- Lo dudoso queda como `propuesta`. Nada dudoso se confirma solo.
- Si no hay causa clara de un descuadre, se dice "sin causa clara".
- Dinero en pesos enteros. Comisiones y retenciones se toman de las liquidaciones.
- El `.exe` entra con el usuario de cada persona, nunca con la llave de servicio
  (D-023). Un proceso de servidor que la use debe filtrar por `empresa_id` de forma
  explícita, porque esa llave se salta RLS.

## Leer antes

`docs/REGLAS/`, `docs/MODELO_DATOS.md` y los casos de control de `tests/casos/`.
