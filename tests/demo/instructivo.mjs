// El "agente de prueba" de la dueña: recorre Tino en el celular como lo haría ella, revisa que
// cada botón haga lo que dice y escribe el instructivo docs/INSTRUCTIVO/duena.md con una captura
// por paso. Usa la empresa de demostración (datos inventados): nunca datos reales.
//
// Si un paso falla, el instructivo lo marca y el guion termina con error: así se sabe qué arreglar.
// Uso: node tests/demo/instructivo.mjs <usuarios de prueba.json fuera del repo>
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { abrir, espera } from "./navegador.mjs";

const [archivo] = process.argv.slice(2);
const claves = JSON.parse(readFileSync(archivo, "utf8"));
const RAIZ = new URL("../../", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const IMG = `${RAIZ}docs/INSTRUCTIVO/img`;
mkdirSync(IMG, { recursive: true });

const n = await abrir();
const secciones = [];
let fallas = 0;

// Un paso del instructivo: qué hacer, qué se ve, y la comprobación automática.
async function paso(seccion, titulo, pasos, accion, comprobar, foto) {
  let ok = true, detalle = "";
  try {
    await accion();
    const t = await n.texto();
    for (const [texto, que] of comprobar) {
      if (!t.includes(texto)) { ok = false; detalle += `No apareció «${texto}» (${que}). `; }
    }
  } catch (e) { ok = false; detalle = String(e.message ?? e); }
  if (!ok) fallas++;
  if (foto) { try { await n.foto(IMG, foto, false); } catch { /* sin captura */ } }
  console.log(`${ok ? "OK   " : "FALLA"} ${seccion} · ${titulo}${ok ? "" : " → " + detalle}`);
  secciones.push({ seccion, titulo, pasos, foto, ok, detalle });
}
const cerrarHoja = async () => { await n.js(`document.querySelector("dialog[open] .m-icono-boton")?.click(); true`); await espera(700); };

try {
  await n.tamano(390, 844, true);
  await n.ir("/entrar", 4000);
  await paso("Entrar", "Abrir Tino y entrar", [
    "Abra el enlace de Tino en el celular o en el computador. En la página de inicio toque **Ir a la demo** (o vaya directo a `/entrar`).",
    "Escriba su **correo** y su **clave**, y toque **Entrar**.",
    "Si es la primera vez con una clave temporal, Tino le pide poner una suya de al menos 10 caracteres.",
  ], async () => {}, [["Entrar", "el botón de entrar"], ["Correo", "el campo del correo"]], "01-entrar");

  await n.entrar(claves["demo.dueno"].correo, claves["demo.dueno"].contrasena);
  await n.ir("/hoy", 8000);
  await paso("Hoy", "Lo primero que ve", [
    "Al entrar llega a **Hoy**: arriba lo urgente (compromisos vencidos, quién necesita apoyo, sesiones de la semana) y abajo cómo va el mes.",
    "Cada frase se toca y lo lleva a la ficha de esa persona.",
    "Abajo está el menú: **Hoy**, **Equipo**, **+ Registrar**, **Ventas** y **Más**. En el computador está a la izquierda.",
  ], async () => {}, [["Hoy", "el título"], ["Registrar", "el botón + Registrar"]], "02-hoy");

  await n.ir("/equipo", 9000);
  await paso("Equipo", "La formación de su equipo", [
    "Toque **Equipo** en el menú. Abre con la formación, en este orden:",
    "1. **Lo que hay que hacer**: compromisos vencidos, quién necesita apoyo y las capacitaciones de la semana.",
    "2. **Cómo van**: conversión, cuántos clientes escucharon el programa de fidelización, a cuántos les consultaron los puntos y los referidos. La flecha dice si mejoró frente al mismo tramo del período anterior.",
    "3. **En qué paso va cada asesora** (Diagnóstico, Formación, Acompañamiento, Evaluación, Compromisos).",
    "4. **Calendario de la semana**, de lunes a domingo.",
    "5. **Todas las asesoras**, al final.",
    "Arriba cambia entre **Este mes** y **Esta semana**, y puede ver un solo punto.",
  ], async () => {}, [["Lo que hay que hacer", "la primera sección"], ["Cómo van", "los indicadores"], ["Calendario de la semana", "el calendario"]], "03-equipo");

  await paso("Equipo", "Cómo van, de cerca", [
    "Cada tarjeta dice el número, contra qué se mide y si subió (▲ verde) o bajó (▼ rojo).",
    "Solo cuentan los días que tienen **registro del día**: un día sin registro no es cero.",
    "Si un día lo atendieron dos, tres o más asesoras juntas, Tino lo avisa: la conversión de cada una ese día es aproximada.",
  ], async () => { await n.js(`document.querySelector('[data-recorrido="formacion-como"]').scrollIntoView(); true`); await espera(800); },
  [["Conversión", "la tarjeta de conversión"]], "04-como-van");

  await paso("Registro del día", "Anotar el día de cada asesora", [
    "En **Equipo** toque **Registro del día** (o **+ Registrar → Registro del día**).",
    "Elija el **punto** y el **día** (viene puesto hoy). La responsable de un punto no elige: ya sale el suyo.",
    "Por cada asesora que trabajó: **Clientes atendidos** y cada contador con **+** y **−**. También puede escribir el número.",
    "A quien no trabajó, no la toque: queda «sin registro», no en cero.",
    "Toque **Guardar**. El mismo día se puede corregir libre; un día que ya pasó pide escribir por qué.",
  ], async () => { await n.tocar("button", "Registro del día"); await espera(2500); await n.elegir("#rd-punto", "Punto Plaza"); await espera(2500); },
  [["Clientes atendidos", "el contador fijo"], ["Guardar", "el botón de guardar"]], "05-registro-dia");
  await cerrarHoja();

  await n.ir("/equipo", 8000);
  await paso("La ficha", "Ver a una asesora y cambiarle el paso", [
    "En la franja de pasos (o en la lista), toque la **cara** de una asesora: se abre su ficha.",
    "En **Paso del ciclo** ve en qué etapa va. Para moverla toque **Cambiar el paso**, elija la etapa y, si quiere, escriba una nota. Queda en la **Línea de tiempo**.",
    "**Cómo va este mes** muestra sus propios indicadores. Más abajo, sus ventas, sus compromisos y todo lo registrado.",
  ], async () => { await n.tocar(".m-etapas a.m-carita"); await espera(5000); await n.tocar("button", "Cambiar el paso"); await espera(800); },
  [["Paso del ciclo", "la sección del ciclo"], ["Guardar el paso", "el botón de guardar el paso"]], "06-ficha-paso");

  await paso("+ Registrar", "Observación, compromiso, evaluación, sesión o meta", [
    "Toque **+ Registrar** (abajo en el celular, a la izquierda en el computador).",
    "Elija qué anotar: **Registro del día**, **Observación**, **Compromiso**, **Evaluación**, **Diagnóstico u objetivo**, **Sesión** o **Meta**.",
    "Desde la ficha de una asesora, **Registrar** ya la trae elegida.",
  ], async () => { await n.ir("/equipo", 7000); await n.tocar('[data-recorrido="registrar"]'); await espera(1500); },
  [["Observación", "la opción observación"], ["Evaluación", "la opción evaluación"]], "07-registrar");

  await paso("+ Registrar", "Evaluar con criterios de 1 a 5", [
    "En **+ Registrar** toque **Evaluación**, elija la asesora y califique cada criterio de **1 a 5**. Puede dejar un comentario.",
    "Si la empresa todavía no tiene criterios, Tino le dice cómo crearlos (con un botón a Ajustes).",
  ], async () => { await n.tocar("dialog[open] .m-fila", "Evaluación"); await espera(2500); },
  [["Comentario", "el formulario de evaluación"]], "08-evaluacion");
  await cerrarHoja();

  await n.ir("/equipo", 8000);
  await paso("Calendario", "Programar una sesión", [
    "En **Calendario de la semana**, toque el **+** de un día (o **Programar una sesión**).",
    "Escriba el **tema**, la **hora** y el **punto** (o todos). La fecha ya viene puesta.",
    "Los compromisos que vencen ese día también salen en el calendario.",
  ], async () => { await n.tocar("button", "Programar una sesión"); await espera(2000); },
  [["Tema", "el formulario de la sesión"]], "09-sesion");
  await cerrarHoja();

  await n.ir("/equipo/ajustes", 7000);
  await paso("Ajustes", "Etapas, indicadores, criterios y plantilla", [
    "En **Equipo** toque **Ajustes** (o **Más → Ajustes de Equipo**).",
    "**Usar plantilla sugerida** llena de una vez etapas, temas, criterios e indicadores. No borra ni repite nada; después edita o desactiva lo que no use.",
    "En **Indicadores del registro del día** agrega los suyos y dice cómo se miden (% de atendidos, % de ventas o solo contar).",
    "En **Palabras de la pantalla** pone el **nombre de su programa de fidelización**.",
    "Nada se borra: lo que no use, se desactiva.",
  ], async () => {}, [["Usar plantilla sugerida", "el botón de la plantilla"], ["Indicadores del registro del día", "los indicadores"]], "10-ajustes");

  await n.ir("/ventas", 8000);
  await paso("Ventas", "Ventas por asesora y por punto", [
    "Toque **Ventas**: el ranking del mes, por asesora o por punto, comparado con los mismos días del mes anterior.",
    "Con las flechas cambia de mes. **Copiar como números** deja la tabla lista para pegar en Excel.",
  ], async () => {}, [["Ventas", "el título"]], "11-ventas");

  await n.ir("/hoy", 6000);
  await paso("Más", "Caja, archivos, usuarios y el recorrido", [
    "Toque **Más**: ahí están **Caja del día**, **Lo que necesita atención**, **Ajustes de Equipo**, **Usuarios** y **Salir**.",
    "**Ver el recorrido de esta pantalla** vuelve a mostrar la guía corta de la pantalla donde esté.",
  ], async () => { await n.tocar("button", "Más"); await espera(1500); }, [["Usuarios", "la entrada de usuarios"], ["Salir", "salir"]], "12-mas");
  await cerrarHoja();

  await n.ir("/usuarios", 7000);
  await paso("Usuarios", "Dar acceso a alguien", [
    "En **Más → Usuarios** toque **Nuevo usuario**: nombre, correo, rol y, si es responsable de punto o asesora, su punto.",
    "Tino muestra una **clave temporal una sola vez**: désela en persona o por un mensaje privado. Al entrar, la persona pone la suya.",
    "No se manda ningún correo. Si alguien pierde la clave: **Clave temporal nueva**.",
  ], async () => {}, [["Nuevo usuario", "el botón"]], "13-usuarios");
} finally {
  n.cerrar();
}

// El instructivo
const hoy = new Date().toLocaleDateString("es-CO", { timeZone: "America/Bogota", day: "numeric", month: "long", year: "numeric" });
let md = `# Instructivo de Tino para la dueña

Cómo se hace cada cosa, paso a paso, con una captura del celular. Las capturas son de la
**empresa de demostración** (nombres y números inventados).

Este instructivo lo escribe y lo comprueba un guion (\`tests/demo/instructivo.mjs\`): recorre
Tino como lo haría la dueña y revisa que cada botón haga lo que aquí se dice. Última revisión:
**${hoy}** · ${secciones.length - fallas} de ${secciones.length} pasos comprobados${fallas ? ` · **${fallas} con problema** (marcados ✘)` : ""}.

## Contenido
${[...new Set(secciones.map((s) => s.seccion))].map((s) => `- [${s}](#${s.toLowerCase().replace(/[^a-záéíóúñ0-9 ]/g, "").trim().replace(/ /g, "-")})`).join("\n")}
`;
let actual = "";
for (const s of secciones) {
  if (s.seccion !== actual) { md += `\n## ${s.seccion}\n`; actual = s.seccion; }
  md += `\n### ${s.ok ? "" : "✘ "}${s.titulo}\n\n${s.pasos.map((p) => (/^\d\./.test(p) ? `   ${p}` : `- ${p}`)).join("\n")}\n`;
  if (!s.ok) md += `\n> **Problema encontrado en la revisión:** ${s.detalle}\n`;
  if (s.foto) md += `\n<img src="img/${s.foto}.png" alt="${s.titulo}" width="300">\n`;
}
md += `
## Qué probar con la demo

1. Entre con el usuario de la dueña de la demo (está en el archivo de usuarios de prueba, fuera del repositorio).
2. Abra **Equipo** y revise que vea, en orden: lo que hay que hacer, cómo van, los pasos y el calendario.
3. Llene el **registro del día** de dos asesoras de Punto Plaza y guárdelo. Vuelva a abrirlo: salen con «Guardado».
4. Abra la ficha de una asesora y **cámbiele el paso**. Mire que quede en la línea de tiempo y en la franja de Equipo.
5. Haga una **evaluación** con criterios.
`;
writeFileSync(`${RAIZ}docs/INSTRUCTIVO/duena.md`, md, "utf8");
console.log(fallas ? `${fallas} paso(s) con problema` : "Instructivo escrito: todos los pasos comprobados");
process.exit(fallas ? 1 : 0);
