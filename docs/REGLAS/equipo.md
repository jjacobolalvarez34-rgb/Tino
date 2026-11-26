# Reglas de Equipo

Quién trabaja dónde, cuánto vende cada persona, sus metas y el acompañamiento. Los valores
marcados ⚑ se leen de `empresa_config` y nunca se escriben fijos en el código.

## Personas y puntos

- Cada persona tiene un código que pone Tino (A001, A002…). No se cambia ni se reutiliza.
- Una persona puede estar en varios puntos a la vez. Cada asignación tiene fecha de inicio y,
  cuando sale, fecha de fin. No se borra: se cierra.
- Una persona no se borra: se desactiva.

## Venta por persona

- Sale del reporte del día de cada punto, con el perfil de la empresa (qué hoja y qué columnas).
  En Milagros, la hoja DESC FACT: FECHA, ASESOR, VENTA DIA, FACTURAS.
- Si un día trae varias personas ("Ana y Luisa"), la venta y las facturas se reparten según
  ⚑ `equipo_reparto`. Hoy la única regla es `partes_iguales`: lo que sobra de dividir va de a
  un peso a las primeras, así el ranking suma lo mismo que el punto.
- Un nombre que no se reconoce entra sin persona y queda como error por resolver. No se adivina.
- Si dos archivos traen el mismo punto y día, cuenta el último que se cargó (D-038).
- **Ticket promedio** = venta de los días que traen facturas ÷ facturas de esos días. Los días
  sin número de facturas no cuentan para el ticket, para no inflarlo.
- **Comparación**: con el período anterior del mismo largo, pegado antes. Un mes en curso se
  compara con los mismos días.

## Metas

- Se ponen en Tino (pantalla Registrar → Meta), por punto o por persona dentro de un punto, para
  cualquier período. No puede haber dos metas activas que se crucen para lo mismo.
- Si el Excel trae la meta del mes (perfil `meta_mes`), entra con su archivo y su fila; no pisa
  una meta que ya exista para ese punto y período.
- **Cumplimiento** = venta del período ÷ meta del período. Si la meta cubre más días que el
  período que se mira, cuenta la parte proporcional por días.
- Sin meta, la pantalla dice "Sin meta"; no se inventa una.

## Acompañamiento

- Registros: diagnóstico, objetivo, observación (con su tipo) y evaluación (puntaje de 1 a 5 por
  criterio). Compromiso: qué, quién responde (vacío = la misma persona), fecha límite, prioridad,
  estado y avance. Sesión de formación: tema, fecha, punto (o todos) y asistentes.
- Tipos de observación de la plantilla: Coaching, Cliente incógnito, Presentación personal, Uso
  del celular, Puntualidad, Novedad operativa, Otro. Temas y criterios empiezan vacíos: los pone
  cada empresa.
- Nada se reescribe: un registro se anula con nota; un compromiso se cierra cumplido o no
  cumplido, o se anula con nota.
- **Privacidad**: observaciones, evaluaciones y compromisos los ven dueño, encargada, lider y
  soporte. El responsable de punto, solo los de su punto. Finanzas y la asesora, ninguno.

## Pendientes (pantalla Hoy)

- **Compromisos vencidos**: abiertos o en curso con fecha límite antes de hoy.
- **Próximos**: los que vencen entre hoy y ⚑ `equipo_dias_proximos` días (7 por defecto).
- **Quién necesita apoyo**: solo con los umbrales que la empresa haya puesto (empiezan vacíos):
  - ⚑ `equipo_umbral_cumplimiento`: va por debajo de ese porcentaje de su meta personal.
  - ⚑ `equipo_umbral_dias_sin_seguimiento`: lleva más de esos días sin ningún registro.
  - ⚑ `equipo_umbral_compromisos_vencidos`: tiene esa cantidad o más de compromisos vencidos.
- **Sesiones de la semana**: de lunes a domingo de la semana actual.

## Formación (tarea 011, D-067)

- **Registro del día**: por persona, punto y día, los clientes atendidos (fijo: es la base de la
  conversión) y un contador por cada indicador de la empresa. Una sola fila por persona, punto,
  día y origen. Lo llenan el responsable de punto (solo su punto), el lider y el dueño.
- **Origen**: "manual" o "integracion" (otra aplicación, en el futuro). Si el mismo día hay
  de los dos, se guardan y se muestran los dos; para los porcentajes cuenta el manual.
- **Correcciones**: libres el mismo día (hora de Bogotá); después, solo con nota. Nada se borra:
  un registro se anula con nota.
- **Un día sin registro no cuenta como cero**: no entra en ninguna cuenta y la pantalla lo dice.
- **Indicadores** ⚑ (`indicador_dia`): cada uno dice contra qué se mide.
  - Sobre atendidos: valor ÷ clientes atendidos (ej.: explicó el programa de fidelización). No
    puede pasar de los atendidos.
  - Sobre facturas: valor ÷ facturas de esa persona ese día (ej.: consultó puntos antes de cobrar).
  - Conteo: se suma (ej.: referidos).
- **Conversión** = facturas ÷ clientes atendidos, solo en los días con registro y con venta de esa
  persona en el Excel del día. Si el día lo compartieron varias personas (dos, tres o más), las
  facturas se reparten por partes iguales (D-049) y la conversión de cada una ese día es
  aproximada; la pantalla avisa cuántos días fueron así.
- **Comparación**: con los mismos días del período anterior (mes o semana).
- **Etapas del ciclo** ⚑ (clase `etapa`): las define cada empresa. El paso de cada persona lo
  cambia una persona (no es automático) y queda la historia.
- **Plantilla sugerida**: temas, criterios, etapas e indicadores; solo con el botón "Usar plantilla
  sugerida", sin pisar lo que la empresa ya tenga. El nombre del programa sale de
  `textos.programa` ⚑.
- **Calendario**: sesiones y compromisos que vencen, de lunes a domingo.

