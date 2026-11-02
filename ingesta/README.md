# ingesta

Todo lo que trae datos de afuera hacia la base: importadores, perfiles de fuente,
normalizador de nombres y lector de correos.

Estado: `tarjetas.py` lee los reportes de Bold y Redeban. Solo se ha probado con
archivos inventados. Faltan el Excel diario, el PDF del banco y Siigo. Va en Python
(D-022).

## Reglas

- Cada importador lee con su `perfil_fuente`. Lo propio de cada empresa va en la
  base, nunca en el código.
- Toda fila importada guarda `archivo_id` y `fila_origen`.
- Un archivo repetido se detecta por su hash y no duplica la plata.
- Lo que no se puede leer va a `error_importacion`; no se descarta en silencio.
- Las pruebas usan archivos anonimizados de `tests/casos/`. Aquí no entra ningún
  archivo real ni ninguna llave.

## Leer antes

`docs/ARQUITECTURA.md`, `docs/MODELO_DATOS.md` y `docs/FUENTES/README.md`.
