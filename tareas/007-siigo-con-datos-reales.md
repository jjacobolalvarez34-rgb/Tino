# 007 · Siigo con los datos reales de Milagros

Estado: lista para probar en cuanto haya credenciales (13 nov 2026).

## Objetivo

Que las facturas de Milagros lleguen solas desde Siigo, cada una en su punto, y que Tino
pueda compararlas con el Excel del día.

## Alcance

- Probar el conector (`ingesta/siigo.py`) con Siigo real: usuario API, llave de acceso y
  Partner-Id de Milagros, guardados solo en `D:\Repositorios\Tino-datos\siigo.json`.
- Elegir en Ajustes de dónde sale el punto de cada factura en Milagros (centro de costo,
  bodega o prefijo) y asignar cada valor a su punto.
- Revisar con Jacobo un día real: facturas de Siigo contra el Excel de ese día.

## Fuera de alcance

- Crear o anular facturas en Siigo. Tino solo lee.

## Hecho cuando

- Un mes de Milagros entra desde Siigo sin repetir facturas al traerlo dos veces.
- Ninguna factura queda sin punto, o las que quedan están en "nombres por resolver" con su
  número.
- El total de facturas de un día de un punto coincide con lo que Jacobo ve en Siigo.

## Cómo lo reviso yo (Jacobo)

En Tino.exe → Ajustes → Siigo: guardar las credenciales, "Ver qué trae", asignar puntos y
"Traer facturas". Comparar el resumen por día y punto con Siigo Nube.

## Lo que necesito

- En Siigo Nube → Alianzas → Mi credencial API: el usuario y la llave de acceso.
- El Partner-Id: desde mayo de 2025 Siigo pediría registrar la aplicación (sin confirmar);
  si no lo tienes, se pide a soporte de Siigo para "Tino".
