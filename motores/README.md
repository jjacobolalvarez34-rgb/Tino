# motores

Los procesos que leen de la base, deciden y escriben el resultado: conciliador,
verificador de transferencias y detector de descuadres.

Estado: `conciliador/` es el programa actual, copiado sin cambiar su lógica (tarea
001). Todavía es la app de escritorio de Milagros, no el motor del producto. El
lenguaje definitivo depende de P-001 (`docs/DECISIONES.md`).

## Reglas

- Las reglas de negocio están en `docs/REGLAS/`. Si una regla no está ahí, se
  pregunta; no se inventa.
- Los valores marcados ⚑ se leen de `empresa_config`. Nunca van fijos en el código.
- Lo dudoso queda como `propuesta`. Nada dudoso se confirma solo.
- Si no hay causa clara de un descuadre, se dice "sin causa clara".
- Dinero en pesos enteros. Comisiones y retenciones se toman de las liquidaciones.
- Estos procesos usan la llave de servicio, que se salta RLS: cada consulta filtra
  por `empresa_id` de forma explícita.

## Leer antes

`docs/REGLAS/`, `docs/MODELO_DATOS.md` y los casos de control de `tests/casos/`.
