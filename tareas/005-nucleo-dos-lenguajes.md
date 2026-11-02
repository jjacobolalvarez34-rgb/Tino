# 005 · Núcleo de cálculo en Python y TypeScript

Paso del plan: F1 · sin número (decisión D-022)
Estado: hecha

## Objetivo
Tener la lógica que decide sobre la plata en dos lenguajes que siempre den lo mismo,
sin Excel, sin PDF y sin interfaz, para que el `.exe` y la futura web usen lo mismo.

## Alcance
- Cruce monto por monto, días vecinos, montos mal digitados, bloques de consignación,
  comparación contra el banco, estado del día y lectura de líneas del banco.
- Contrato común, casos con datos inventados y comparación entre lenguajes.

## Fuera de alcance
- Leer el Excel de Milagros y los reportes de Bold, Redeban y Siigo.
- Conectar con Supabase: `tino-pruebas` aún no existe.
- Reglas de nivel 1 (fórmulas, billete, compensación, precios).
- Cambiar `docs/REGLAS/`: el núcleo copia al conciliador hasta la tarea 004.

## Documentos a leer
- `motores/CONTRATO.md`, `docs/BITACORA.md` (H-51 a H-61)

## Hecho cuando
- Python y TypeScript pasan todos los casos de `tests/casos/motor/casos.json`.
- `python motores/comparar_lenguajes.py` termina con 0 diferencias.
- El núcleo en Python da lo mismo que las funciones del conciliador actual.

## Cómo lo reviso yo (Jacobo)
- Corro los tres comandos de la sección "Comandos" de `CLAUDE.md`.
- Abro `tests/casos/motor/casos.json` y reviso que cada resultado esperado tenga
  sentido, sobre todo "un dia con todo mezclado".

## Notas
- Si una regla cambia en la tarea 004, cambia primero el contrato y sus casos.
