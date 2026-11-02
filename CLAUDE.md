# Tino

Producto para negocios con varios puntos de venta en Colombia. Trae los datos de
los Excels diarios, Siigo, extractos bancarios, Bold, Redeban y avisos de
transferencia; concilia los pagos, detecta descuadres con su causa probable y lo
muestra claro, listo para copiar a Excel.

Milagros (11 puntos) es el laboratorio: datos reales, usados con permiso, solo en
el proyecto de pruebas.

Jacobo López dirige el proyecto y revisa todo. Trabaja como "vibe engineer":
quiere entender cada decisión, no solo recibir código.

## Antes de escribir código

1. Lee, en este orden: `docs/VISION.md`, `docs/ARQUITECTURA.md`,
   `docs/MODELO_DATOS.md`, `docs/DESIGN.md` y la tarea en `tareas/`.
2. Trabaja en modo plan. Propón el plan y espera la aprobación de Jacobo.
3. Si una regla de negocio no está en `docs/REGLAS/`, pregunta. No la inventes.
   Los valores marcados ⚑ en las reglas se leen de `empresa_config`; nunca se
   escriben fijos en el código.
4. Si algo de la tarea contradice estos documentos, dilo antes de empezar.

## Reglas que no se rompen

### Datos y seguridad
- Toda tabla de datos lleva `empresa_id`. Toda consulta pasa por RLS.
- Ninguna empresa puede ver ni tocar datos de otra. Cada cambio de permisos
  lleva pruebas con al menos dos empresas.
- Nada específico de un cliente en el código. Lo propio de cada empresa va en
  `perfil_fuente` o en tablas de configuración.
- Datos reales de Milagros solo en el proyecto de pruebas. Nunca en demos,
  capturas, ejemplos ni commits.
- Nunca credenciales, llaves ni datos personales en el repositorio.

### Dinero
- Pesos colombianos enteros (`bigint`). Nunca `float` ni `numeric` con decimales.
- Toda fila importada guarda `archivo_id` y `fila_origen`.
- Nada se borra: se anula, se ajusta o se desactiva. Las tablas no tienen
  política de DELETE para usuarios.
- Una conciliación dudosa queda como `propuesta`. Nunca se confirma sola.
- Si no hay causa clara de un descuadre, se dice "sin causa clara".
- No se calculan impuestos oficiales. Retenciones y comisiones se toman de las
  liquidaciones, no de tarifas.

### Base de datos
- Ningún cambio a la base sin una migración nueva en `db/migrations/`.
- Una migración aplicada nunca se edita. Si hay que corregir, se crea otra.
- Nombres en español, `snake_case`, sin tildes ni ñ en identificadores.

### Pantallas
- Solo tokens y componentes de `docs/DESIGN.md`.
- Para diseñar o revisar pantallas usa los plugins UI UX Pro Max (accesibilidad,
  estados y patrones) y Apple Design (componentes de la app en iPhone). Íconos:
  Lucide. Si un plugin contradice `docs/DESIGN.md`, gana DESIGN.md.
- Antes de construir una pantalla, ábrela en `docs/pantallas/demo.html` y lee lo
  que no puede faltar en `docs/pantallas/README.md`.
- "Copiar como números" entrega enteros sin `$` ni puntos, separados por
  tabulación.
- Ninguna pantalla carga más datos de los que muestra.

## Cómo trabajar con Jacobo

- Explica el porqué de cada decisión técnica en dos o tres frases.
- Señala los supuestos que hiciste.
- Si hay dos caminos razonables, muéstralos con sus ventajas y deja que él elija.
- Cuando termines, di qué probar y cómo, con un caso concreto.

## Pruebas

- Cada importador se prueba con archivos reales anonimizados en `tests/casos/`.
- Cada regla de dinero tiene al menos un día real como caso de control con el
  resultado esperado escrito a mano por Jacobo.
- Las pruebas de permisos simulan usuarios de dos empresas y de cada rol.

## Al terminar cada sesión

- Agrega una entrada a `docs/BITACORA.md`: qué se hizo, qué falta, dudas.
- Si se tomó una decisión, regístrala en `docs/DECISIONES.md` con fecha y motivo.
- Marca la tarea como hecha solo si se cumple su criterio de "hecho cuando".

## Comandos

- Probar migraciones y permisos en un Postgres local (nunca en Supabase):
  `./tests/rls/correr.sh "postgresql://postgres@localhost:5432/postgres"`
- Probar el núcleo en Python, desde `motores/`:
  `python -m unittest nucleo.test_casos`
- Probar el núcleo en TypeScript:
  `node --experimental-strip-types --test motores/nucleo_ts/test_casos.test.ts`
- Exigir que los dos lenguajes den lo mismo:
  `python motores/comparar_lenguajes.py`
- [POR COMPLETAR en la tarea 001: aplicar migraciones en Supabase y levantar el
  programa.]
