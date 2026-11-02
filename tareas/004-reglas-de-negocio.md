# 004 · Completar las reglas de negocio

Paso del plan: F1 · 1.1 (documentos)
Estado: en curso · reglas redactadas por Claude el 2 nov 2026
Quién: Jacobo (no se le delega a Claude Code)

## Objetivo
Que `docs/REGLAS/` diga con precisión cómo se concilia, cómo se detecta un
descuadre y cómo se verifica una transferencia, con las reglas reales del
conciliador actual.

## Alcance
- Confirmar o corregir los supuestos marcados ⚑ en los tres archivos de reglas,
  comparándolos con el conciliador actual y con archivos reales.
- Elegir 10 días de Milagros ya conciliados a mano como casos de control y
  escribir el resultado esperado de cada uno.

## Fuera de alcance
- Programar las reglas.

## Hecho cuando
- Cada supuesto ⚑ está confirmado o corregido (se quita la marca ⚑).
- Hay 10 casos de control con resultado esperado en `tests/casos/`.

## Cómo lo reviso yo (Jacobo)
- Le pido a Claude que lea las reglas y me haga preguntas sobre los casos raros.
