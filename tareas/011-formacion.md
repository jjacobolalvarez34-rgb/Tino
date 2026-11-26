# 011 · Formación y desempeño, arreglos de la portada y diseño de roles

Paso del plan: Equipo (después de la revisión de la dueña)
Estado: A y B hechos; C diseñado (espera aprobación para construirlo).

## Objetivo
La dueña revisó Tino y dijo "no vi lo que necesito": pidió el ciclo de formación de sus asesoras.
Equipo abre con la formación; las ventas siguen en Ventas y en la ficha.

## Alcance
- **A1** Registro del día por persona (clientes atendidos fijo + indicadores de la empresa), con + y −.
- **A2** Indicadores: conversión, % del programa, % consultó puntos, referidos, contra el período anterior.
- **A3** Etapas del ciclo configurables y paso de cada persona, con su historia.
- **A4** Calendario de la semana (lunes a domingo; en el celular, una lista por día).
- **A5** Equipo abre en este orden: lo que hay que hacer, cómo van, pasos, calendario, lista.
- **A6** Temas, criterios, etapas e indicadores con "Usar plantilla sugerida"; evaluación sin criterios explica cómo crearlos.
- **A7** Usuarios del equipo de Milagros sin invitar (cuando Jacobo pase los correos).
- **A8** Recorrido guiado de Equipo: primero la formación.
- **A9** Registro preparado para que otra aplicación lo llene (origen manual o integración), sin construir la integración.
- **B** Portada: causa sin encimarse, resaltado en Punto Plaza, tres planes en /precios.
- **C** Roles configurables: solo diseño (docs/ROLES.md, D-066).

## Fuera de alcance
- La integración con una app de fidelización (solo queda preparada).
- Código de roles configurables.

## Documentos a leer
- docs/pantallas/maqueta-formacion.html (copia con nombres genéricos), docs/REGLAS/equipo.md (Formación),
  docs/ROLES.md, D-066 y D-067.

## Hecho cuando
- Como responsable de punto, en el celular, registro el día de 2 asesoras en menos de 2 minutos.
  → Comprobado con `tests/demo/capturas_formacion.mjs`: 20 toques.
- Como dueña, al abrir Equipo veo en orden: lo que hay que hacer, cómo van (programa, consulta de
  puntos y conversión), el paso de cada asesora y el calendario. → Comprobado por el mismo guion.
- Puedo evaluar a una asesora con criterios. → Sí (con la plantilla o criterios propios).
- La segunda empresa de prueba funciona con sus propios indicadores y etapas. → Pruebas de 0015
  (empresa B con "Ofreció garantía extendida" y la etapa "Inducción").
- Todas las pruebas en verde: 467 de permisos, 6 del cálculo.
- A7: 2 de coordinación (lider) y 11 encargadas (responsable_punto, una por punto) creados en tino-pruebas el
  26 nov, con correos inventados, sin invitar y con clave temporal (claves fuera del repositorio).

## Cómo lo reviso yo (Jacobo)
- Seguir el instructivo `docs/INSTRUCTIVO/duena.md` con el usuario de la demo.
- `./tests/rls/correr.sh "postgresql://postgres@localhost:55433/postgres"`
- `node --experimental-strip-types --test web/lib/formacion-calculo.test.ts`
- `node tests/demo/capturas_formacion.mjs <usuarios de prueba> <carpeta>` y `capturas_portada.mjs <carpeta>`

## Notas
- Pendiente de Jacobo: ¿la encargada también llena el registro del día? Hoy no (como dice el brief).
