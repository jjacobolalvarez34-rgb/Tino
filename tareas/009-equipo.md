# 009 · Equipo: personas, ventas por persona, metas y acompañamiento

Paso del plan: Equipo (antes de la 004, D-045)
Estado: en curso · todo construido; falta lo que depende de producción

## Objetivo
Que el dueño, la encargada y la líder vean quién vende cómo en cada punto y acompañen a cada
persona (observaciones, evaluaciones, compromisos), en el celular y en el computador.

## Alcance
- Bloque 0 y 0B: web conectada, nueva dirección visual (DESIGN.md §15), Hoy y la ficha.
- Bloque 1: personas, persona en varios puntos con vigencia, roles lider y responsable_punto.
- Bloque 2: venta por persona por perfil, octubre de Milagros, Ventas y Metas.
- Bloque 3: configuración por empresa, registros, compromisos, privacidad.
- Bloque 4 y 4B: Pendientes en Hoy y recorrido guiado.
- Segunda empresa inventada.

## Fuera de alcance
Indicadores escritos en el punto, horarios, calendario completo, rediseño del .exe. La etapa sin
internet va al final, aparte.

## Hecho cuando
1. ✅ Se ven los 11 puntos y las personas (tino-pruebas; producción pendiente, ver 010).
2. ✅ Una persona queda en 2 puntos (pantalla Equipo; pruebas 0011 y probar_equipo_supabase.py).
3. ✅ Ranking de octubre con ticket promedio y cumplimiento (Ventas). punto 02 se recarga cuando
   esté 0012 en pruebas.
4. ✅ Observación de coaching y compromiso vencido que sale en Pendientes (probado en Supabase y
   en la empresa demo).
5. ✅ Recorrido guiado que termina en registrar un compromiso (Hoy; también Equipo y Ventas).
6. ✅ La segunda empresa funciona: 30 de 30 en probar_equipo_supabase.py.
7. ✅ Pruebas en verde: 381 de permisos, 66 + 30 en Supabase, 14 del lector, 12 de Usuarios.
Falta para cerrarla: que funcione con la web publicada contra producción (tarea 010).

## Cómo lo reviso yo (Jacobo)
- http://localhost:6001/hoy, /equipo, /ventas con Milagros (pruebas) o con la empresa demo.
- `./tests/rls/correr.sh "postgresql://postgres@localhost:55433/postgres"` → 381 OK.
- `python tests/rls/probar_equipo_supabase.py <contraseñas>` → 30 de 30.

## Notas
Decisiones D-044 a D-052. Reglas en docs/REGLAS/equipo.md.
