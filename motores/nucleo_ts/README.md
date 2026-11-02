# nucleo_ts

El núcleo de cálculo en TypeScript: las mismas 12 funciones de `motores/nucleo/`,
sin dependencias. Las dos implementaciones deben dar exactamente lo mismo: si dan
distinto, una está mal o el contrato está incompleto.

Estado: `logica.ts` tiene las funciones y `ejecutar`. `lote.ts` corre una lista de
llamadas para compararlas con Python.

## Reglas

- La especificación es `motores/CONTRATO.md`. Si algo no está ahí, se pregunta; no
  se copia de Python.
- Solo Node 22 o más, sin `npm install`. Node quita los tipos y no compila: nada de
  `enum`, `namespace` ni parámetros de propiedad.
- Dinero en pesos enteros y fechas en UTC.

## Pruebas

Desde la raíz del repositorio:

```
node --experimental-strip-types --test motores/nucleo_ts/test_casos.test.ts
```

Corre todos los casos de `tests/casos/motor/casos.json`.

Para correr un lote:

```
node --experimental-strip-types motores/nucleo_ts/lote.ts entrada.json salida.json
```

`entrada.json` es una lista de `{"funcion", "entrada"}` y `salida.json` la lista de
resultados en el mismo orden. Si una llamada falla, en su posición queda
`{"error": "mensaje"}` y el lote sigue.
