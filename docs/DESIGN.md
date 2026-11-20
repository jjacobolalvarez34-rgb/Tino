# DESIGN.md · Tino

Guía visual del panel web, el Sheet de control y la app nativa de las asesoras.
Claude Code debe leer este archivo antes de crear o cambiar cualquier pantalla.
Si algo no está aquí, se pregunta a Jacobo; no se inventa un color, tamaño o componente nuevo.

Estado: **propuesta D (Ciruela)**, elegida el 31 oct 2026 por cansar menos la vista en jornadas largas.

Pantallas de referencia: `docs/pantallas/demo.html` (prototipo que se puede tocar) y
`docs/pantallas/README.md` (qué lleva cada pantalla). Si el prototipo y este archivo
no coinciden, gana este archivo.

---

## 0. Marca

El logo es la palabra "tino" en trazo geométrico redondeado, con un chulito
ciruela en lugar del punto de la i: la caja revisada y aprobada (D-016).

Archivos en `docs/marca/` (usa siempre los SVG; los PNG son para donde no se
acepta SVG):

| Archivo | Cuándo |
| --- | --- |
| `tino-logo.svg` | Por defecto, sobre fondo claro |
| `tino-logo-blanco.svg` | Sobre fondo ciruela u oscuro |
| `tino-logo-negro.svg` | Impresión a una tinta, sellos, documentos en blanco y negro |
| `tino-icono.svg` | Ícono de la app, favicon y avatar (esquinas redondeadas incluidas) |
| `tino-icono-cuadrado.svg` | Tiendas de apps, que redondean las esquinas por su cuenta |
| `png/` | Logo de 1200 px en las tres versiones; ícono de 1024, 512, 192 y 32 px |

Reglas:

- Espacio libre alrededor del logo: como mínimo el alto de la "o".
- Tamaño mínimo: logo de 80 px de ancho; ícono de 16 px.
- El chulito solo va en ciruela (`#74305F`) sobre claro, o en rosa (`#E9C6DC`)
  sobre ciruela. En la versión a una tinta va del mismo color de las letras.
- No deformar, rotar, poner sombras, contornos ni degradados.
- No escribir "Tino" con otra fuente para reemplazar el logo. En texto corrido
  se escribe "Tino" con mayúscula inicial, en la fuente normal.
- En la app y el panel, el ícono va a la izquierda del nombre de la pantalla.

---

## 1. Principios

1. **Primero lo que necesita atención.** Arriba van los descuadres, las transferencias sospechosas y el total del día. El detalle va después.
2. **El estado se entiende sin leer números.** Cada estado tiene color, forma y palabra (● Cuadrado, ▲ Revisar, ■ Descuadre). Nunca solo color.
3. **Familiar para quien vive en Excel.** Tablas limpias, números alineados a la derecha, totales en negrita al final. Nada de gráficas que haya que interpretar.
4. **Rápido antes que bonito.** Ninguna pantalla carga más datos de los que muestra. Sin animaciones decorativas.
5. **El sistema nunca inventa.** Si no hay causa clara de un descuadre, la pantalla dice "Sin causa clara".
6. **Una acción principal por pantalla.**

## 2. Color

### Marca y neutros (propuesta D · Ciruela)

| Token | Hex | Uso |
|---|---|---|
| `--color-marca` | `#74305F` | Botón principal, enlaces, selección |
| `--color-marca-hover` | `#5A2449` | Botón principal presionado o con el cursor encima |
| `--color-marca-suave` | `#F3E4EE` | Fondo de botón suave, fila seleccionada |
| `--color-foco` | `#C99BBB` | Anillo de foco (3 px, separado 2 px) |
| `--color-fondo` | `#F7F5F7` | Fondo de la app y del panel |
| `--color-superficie` | `#FFFFFF` | Tarjetas, tablas, barras |
| `--color-texto` | `#22161F` | Texto principal |
| `--color-texto-suave` | `#5E5862` | Etiquetas, fechas, ayudas |
| `--color-borde` | `#E2DDE3` | Bordes de tarjetas y controles |
| `--color-divisor` | `#F0ECF0` | Líneas entre filas |
| `--color-deshabilitado-fondo` | `#E3E8E6` | Botón deshabilitado |
| `--color-deshabilitado-texto` | `#7C8A92` | Texto deshabilitado |

Por qué ciruela y no vino: el vino (`#8A2D4E`) está casi en el mismo tono que el rojo de error y se confundían. La ciruela se corre hacia el morado y el error se corre hacia el naranja (rojo ladrillo), así quedan lejos.

### Para no cansar la vista

- El color de marca ocupa poco espacio: botón principal, logo, selección y enlaces. Nunca fondos grandes, encabezados completos ni tablas.
- Fondo gris muy suave (`#F7F5F7`) en vez de blanco puro; las tarjetas blancas encima dan el contraste justo.
- Texto casi negro (`#22161F`), no negro puro.
- Los colores de estado aparecen solo donde hay algo que mirar. Un día sin problemas se ve casi todo neutro.
- Los fondos de colores fuertes se reservan para la tarjeta de "Descuadres abiertos" cuando hay alguno.

Alternativas descartadas (por si se reabre la decisión; solo cambian estos cuatro tokens):

| Propuesta | Marca | Marca suave | Fondo | Texto |
|---|---|---|---|---|
| A · Verde cuenta | `#0B6E5F` | `#DDEFEA` | `#F3F5F4` | `#16232B` |
| E · Vino y grafito | `#2B3038` (botones), `#8A2D4E` (solo logo) | `#ECEEF1` | `#F5F5F6` | `#1A1D22` |
| G · Azul petróleo | `#1D5A73` | `#DFEDF2` | `#F3F6F7` | `#14232B` |

### Estados (iguales en cualquier propuesta)

| Estado | Texto | Fondo | Símbolo | Cuándo |
|---|---|---|---|---|
| Cuadrado / Verificada | `#1C7638` | `#E1F2E5` | ● | Todo coincide |
| Revisar | `#7A5A00` | `#FBF1CC` | ▲ | Diferencia pequeña o confianza media |
| Descuadre / Sospechosa | `#9A2A0A` | `#FDE5DA` | ■ | Falta plata o el banco no confirma |
| Esperando banco | `#2557A7` | `#E3ECFA` | — | Pendiente, aún dentro del tiempo |
| Cerrado / Neutro | `#4F4853` | `#F0ECF0` | — | Día cerrado, sin acción |
| Peligro (botón) | `#FFFFFF` sobre `#C2410C` | — | — | Anular, borrar |

Revisar es amarillo mostaza y Descuadre es rojo ladrillo: además del color se diferencian por símbolo (▲ / ■) y palabra.

Reglas:
- Todo texto cumple contraste 4.5:1 sobre su fondo. No usar el color de marca como fondo de texto pequeño gris.
- El rojo se reserva para dinero que falta y para acciones de peligro. No se usa como decoración.

### Modo oscuro

Fase posterior. Cuando se haga, los estados conservan la misma lógica de colores con fondos oscuros; ningún color se define solo para un modo.

## 3. Tipografía

- **Fuente:** Figtree (Google Fonts) en el panel web.
- **App nativa:** la fuente del sistema (SF Pro en iPhone, Roboto en Android), para respetar el tamaño de letra que la asesora tenga configurado en su celular.
- **Números:** siempre con `font-variant-numeric: tabular-nums` para que las columnas de plata queden alineadas.

| Nombre | Tamaño / peso | Uso |
|---|---|---|
| Título de pantalla | 28 / 800 | "Cierre del día" |
| Cifra principal | 30 / 800 | Total del día en tarjetas |
| Sección | 22 / 700 | En móvil; 18 / 700 en el panel |
| Subtítulo | 17 / 600 | Nombre del punto, título de tarjeta |
| Cuerpo | 15 / 400 | Texto normal |
| Pequeño | 13 / 500 | Fechas, ayudas, etiquetas |
| Etiqueta de tabla | 12 / 600, mayúsculas, espaciado 0.05em | Encabezados de columnas |

Nunca menos de 12 px. El texto corrido no pasa de unos 65 caracteres por línea.

## 4. Espaciado, márgenes y esquinas

Escala de 4 px. Solo se usan estos valores:

| Token | px | Uso típico |
|---|---|---|
| `--esp-1` | 4 | Ícono y su texto |
| `--esp-2` | 8 | Entre chips o botones juntos |
| `--esp-3` | 12 | Entre tarjetas en el celular |
| `--esp-4` | 16 | Relleno de tarjeta en el celular; entre tarjetas del panel |
| `--esp-5` | 20 | Margen lateral del celular; relleno de tarjeta del panel |
| `--esp-6` | 24 | Margen lateral del panel; entre bloques |
| `--esp-8` | 32 | Entre secciones |
| `--esp-12` | 48 | Bordes de páginas grandes |

| Elemento | Celular | Panel PC |
|---|---|---|
| Margen lateral | 20 | 24 |
| Relleno de tarjeta | 16 | 20 |
| Separación entre tarjetas | 12 | 16–24 |
| Ancho máximo del contenido | — | 1232 |

Esquinas: 8 (chips cuadrados, controles pequeños), 10 (botones), 12 (tarjetas y tablas), 14 (tarjetas en el celular), 999 (chips de estado).

Separación entre elementos con `gap` de flex o grid; no con márgenes sueltos.

## 5. Botones

| Tipo | Aspecto | Uso |
|---|---|---|
| Principal | Fondo marca, texto blanco | Una por pantalla. La acción que termina la tarea ("Cerrar el día") |
| Secundario | Fondo blanco, borde y texto marca | Acciones de apoyo ("Subir comprobante") |
| Texto | Sin fondo, texto marca | Navegar, ver más |
| Peligro | Fondo `#C2410C`, texto blanco | Anular o borrar. Siempre pide confirmación |

| Tamaño | Alto | Relleno lateral | Letra | Esquina | Dónde |
|---|---|---|---|---|---|
| Grande | 52 | 22 | 17 / 700 | 12 | Acción principal en el celular |
| Normal | 44 | 18 | 15 / 700 | 10 | Por defecto |
| Compacto | 36 | 14 | 14 / 700 | 8 | Solo en el panel de PC, nunca en el celular |

Estados: normal, presionado (`--color-marca-hover`), foco (anillo `--color-foco` de 3 px), deshabilitado (grises de la tabla de color; al tocarlo explica por qué), cargando (texto "Guardando…", el botón no se puede tocar dos veces).

Reglas:
- Área tocable mínima de 44 × 44 px en el celular (guía de Apple), aunque el ícono sea más pequeño.
- El texto del botón dice exactamente lo que pasa: "Cerrar el día", no "Aceptar".
- Botón solo con ícono: lleva `aria-label` / etiqueta de accesibilidad.

## 6. Chips de estado

- Forma de píldora, letra 12.5–13 / 600, relleno 3–4 × 9–10 px, sin salto de línea (`white-space: nowrap`).
- Símbolo + palabra + color de la tabla de estados.
- No se pueden tocar. Si llevan a algo, la fila completa es la que se toca.

## 7. Tarjetas, tablas y listas

- **Tarjeta:** superficie blanca, borde `--color-borde`, esquina 12, sin sombra. La sombra se reserva para elementos flotantes (menús, avisos).
- **Tarjeta de alerta:** fondo del estado (por ejemplo `#FDE5DA`) solo cuando el número es el centro de la tarjeta, como "Descuadres abiertos".
- **Tabla:** encabezados pequeños en mayúsculas, números alineados a la derecha, filas de 40–44 px, divisor `--color-divisor`, fila de totales en negrita al final. Si no cabe, se desplaza dentro de su caja; la página nunca se desplaza de lado.
- **Lista en el celular:** filas de mínimo 44 px, ícono a la izquierda, dato principal en negrita y detalle en pequeño debajo.

## 8. Íconos

- **Librería:** [Lucide](https://lucide.dev) (licencia ISC).
  - Panel web: `lucide-react`.
  - App nativa: `lucide-react-native` (con `react-native-svg`).
- Tamaño 20 o 24 px, trazo 2 px, color heredado del texto (`currentColor`).
- Íconos decorativos ocultos para lectores de pantalla; íconos que funcionan como botón llevan etiqueta.
- Nunca emojis como íconos.

| Concepto | Ícono Lucide |
|---|---|
| Copiar como números | `copy` |
| Verificada / cuadrado | `circle-check` |
| Revisar / alerta | `triangle-alert` |
| Esperando | `clock` |
| Subir comprobante | `camera` |
| Buscar | `search` |
| Ver más | `arrow-right` / `chevron-right` |
| Punto de venta | `store` |
| Efectivo | `banknote` |
| Tarjeta | `credit-card` |
| Transferencia | `arrow-left-right` |
| Inventario | `package` |
| Horarios | `calendar-days` |
| Asesora | `user` |

## 9. Números y dinero

- En pantalla: `$ 1.510.000` (punto de miles, sin decimales, formato es-CO).
- Negativos: signo menos real `−85.000` en el color del estado.
- **Al copiar o exportar:** solo el entero, sin `$` ni puntos (`1510000`), separado por tabulaciones, para pegar directo en Excel y poder sumarlo.
- En el Sheet de control: el valor de la celda es el número puro; el `$` es solo formato visual de la celda.

## 10. Textos

- Español claro, tuteo con las asesoras, usted en las pantallas de la jefe.
- Botones con verbo: "Cerrar el día", "Subir comprobante", "Copiar como números".
- Errores que dicen qué pasó y qué hacer: "El banco no ha confirmado esta transferencia. Revisa el comprobante o avisa a la encargada."
- Fechas: "Sábado 31 oct", horas en 24 h ("14:32").

## 11. Movimiento

- Transiciones de 150–200 ms solo para cambios de estado (presionar, abrir, cerrar).
- Respetar la opción de "reducir movimiento" del sistema.
- Nada que se mueva solo en pantalla.

## 12. Plataformas

- **App nativa (Expo / React Native):** seguir la guía de interfaz de Apple en iPhone y Material en Android en lo que toca a navegación y controles del sistema; estos tokens definen el color, el espaciado y los componentes propios.
- **Panel web:** funciona desde 375 px de ancho (celular de la jefe) hasta 1440 px.
- **Sheet de control:** mismos colores de estado en el formato condicional.

## 13. Herramientas de diseño para Claude Code

Se instalan una vez en Claude Code, escribiendo estos comandos en la terminal
de Claude Code (no en la de Windows/Mac):

```
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill

/plugin marketplace add https://github.com/NutshellEngineering/apple-design-skill
/plugin install apple-design-skill@apple-design-skill-marketplace
```

- **UI UX Pro Max:** úsala para revisar accesibilidad, estados y patrones de UX. Sus paletas y fuentes sugeridas **no** reemplazan las de este archivo.
- **Apple Design (HIG):** úsala para decidir componentes y navegación de la app nativa en iPhone.
- Si una de esas guías contradice este archivo, gana este archivo y se le pregunta a Jacobo.

## 14. Lista de revisión antes de aprobar una pantalla

- [ ] Una sola acción principal.
- [ ] Todo toque en el celular mide 44 px o más.
- [ ] Cada estado tiene símbolo y palabra, no solo color.
- [ ] Contraste 4.5:1 en todo el texto.
- [ ] Números alineados con `tabular-nums` y totales al final.
- [ ] "Copiar como números" da enteros que Excel puede sumar.
- [ ] Funciona a 375 px de ancho sin desplazarse de lado.
- [ ] Carga en menos de 2 segundos en un celular.
- [ ] Solo usa tokens de este archivo.

## 15. Dirección 2 (web, nov 2026)

Pedida por Jacobo el 19 nov 2026 (D-046). Se aplicó primero a Hoy, Equipo y Ventas; el resto
de pantallas pasa a esta dirección cuando él la apruebe. Los estilos están en
`web/app/marco.css`, con prefijo `m-`. Los tokens de color, estados y espaciado de las
secciones anteriores siguen valiendo.

**Navegación**
- Computador: riel angosto de 88 px a la izquierda, con íconos y su nombre debajo. Arriba el
  logo y "+ Registrar" (botón ciruela de 52 px). Nada de barra lateral blanca ancha.
- Celular: barra inferior de 64 px con Hoy, Equipo, **+ Registrar** (al centro, levantado),
  Ventas y Más. "Más" abre una hoja con el resto de pantallas y Salir.

**Hoy**: frases que se tocan, ordenadas por urgencia (■ vencido, ▲ apoyo, próximos, sesiones).
Una columna en el celular; en el computador, frases a la izquierda y el resumen del período a la
derecha. Nada de cuadrícula de tarjetas con números.

**Lista y detalle**: en el computador, la lista a la izquierda (300–380 px) y la ficha a la
derecha; en el celular la ficha abre a pantalla completa con "‹ Equipo" para volver.

**Cifras**: número de 40 px (34 en el celular) o 32 px (28), peso 800, tabular, con **una línea
de contexto** debajo en 15 px ("+8 % frente a septiembre"). Sin etiqueta gris pequeña encima.

**Personas primero**
- Avatar: iniciales en un círculo; el color sale del id de la persona (seis pares, todos AA):

| Token | Fondo | Texto |
|---|---|---|
| `--av0` | `#F3E4EE` | `#5A2449` |
| `--av1` | `#E1F0EE` | `#1F5C55` |
| `--av2` | `#FBEBD9` | `#7A4210` |
| `--av3` | `#E5ECF8` | `#2B4C86` |
| `--av4` | `#EEE9F7` | `#4B3A82` |
| `--av5` | `#F6E3E1` | `#8A2F28` |

- Anillo de meta: trazo ciruela; verde de "Cuadrado" al llegar a 100 %. Sin meta dice "Sin meta".
- Ranking: lista con posición, avatar, nombre, barra de 6 px y monto.
- Ficha: cabeza (avatar 64, nombre 28/800, código), puntos como píldoras, cifras, compromisos
  abiertos y **línea de tiempo** (lo más nuevo arriba).

**Menos cajas**: filas separadas por `--color-divisor` en vez de tarjetas. La ciruela solo en
"+ Registrar", la selección, los enlaces y las barras de datos.

**Contraste**: texto secundario `--color-texto-medio` `#4A4350` (más oscuro que
`--color-texto-suave`), títulos en 800.

**Registrar**: hoja que sube desde abajo en el celular y panel de 460 px a la derecha en el
computador (`HojaInferior`, con `<dialog>`: Esc cierra, el foco queda adentro). Observación,
Compromiso, Sesión y Meta; cada formulario cabe en una pantalla y lo que se puede adivinar ya
viene puesto.

**Tablas**: componente `Tabla` con total al final, orden por columna (`aria-sort`) y "Copiar
como números". Por debajo de 700 px se vuelve lista.

**Estados y movimiento**: esqueletos mientras carga, aviso corto al guardar ("Compromiso
guardado"), transiciones de 150–200 ms (`--dur`), toques de 44 px, Tab/Enter/Esc. Se sigue
respetando "reducir movimiento" (§11). La página pública es la única excepción (D-052).

**Textos que cambian por empresa**: "asesora", "punto" y similares salen de `web/lib/textos.ts`
y se pueden cambiar por empresa en `empresa_config.textos`.

**Íconos nuevos (Lucide)**: sun (Hoy), users (Equipo), plus (Registrar), ellipsis (Más),
store (punto), eye (observación), flag (compromiso), graduation-cap (sesión), target (meta),
life-buoy (apoyo), clock (próximo), trending-up / trending-down (comparación).
