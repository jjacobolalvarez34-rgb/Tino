// Revisa Formación en la empresa de demostración y saca capturas a 390 y 1440 px.
//   * Como dueña: Equipo abre en el orden pedido (lo que hay que hacer, cómo van, pasos,
//     calendario, lista), la ficha con el paso del ciclo y los Ajustes.
//   * Como responsable del Punto Plaza, en el celular: llena el registro del día de dos personas
//     y lo guarda (cuenta los toques y el tiempo).
// Uso: node tests/demo/capturas_formacion.mjs <usuarios de prueba.json fuera del repo> <carpeta de salida>
import { readFileSync } from "node:fs";
import { abrir, espera } from "./navegador.mjs";

const [archivo, salida] = process.argv.slice(2);
const claves = JSON.parse(readFileSync(archivo, "utf8"));
const n = await abrir();
const fallas = [];
const revisar = (cond, que) => { console.log((cond ? "OK   " : "FALLA") + " " + que); if (!cond) fallas.push(que); };

try {
  // Dueña, computador
  await n.tamano(1440, 900, false);
  await n.entrar(claves["demo.dueno"].correo, claves["demo.dueno"].contrasena);
  await n.ir("/equipo", 9000);
  const t = await n.texto();
  const orden = ["Lo que hay que hacer", "Cómo van", "En qué paso va", "Calendario de la semana", "Todas las"].map((x) => t.indexOf(x));
  revisar(orden.every((x, i) => x >= 0 && (i === 0 || x > orden[i - 1])), "Equipo abre en el orden pedido: hacer, cómo van, pasos, calendario y lista");
  revisar(/Conversión/.test(t) && /Explicó el Club Puntos Demo/.test(t) && /Consultó puntos/.test(t), "Cómo van muestra conversión, programa y consulta de puntos");
  revisar(/Diagnóstico/.test(t) && /Compromisos/.test(t), "La franja trae las etapas del ciclo");
  await n.foto(salida, "equipo-1440");
  await n.tocar(".m-etapas a.m-carita");
  await espera(5000);
  const f = await n.texto();
  revisar(/Paso del ciclo/.test(f) && /Cómo va este mes/.test(f), "La ficha muestra el paso del ciclo y cómo va");
  await n.foto(salida, "ficha-1440");
  await n.ir("/equipo/ajustes", 7000);
  const a = await n.texto();
  revisar(/Usar plantilla sugerida/.test(a) && /Indicadores del registro del día/.test(a) && /Etapas del ciclo/.test(a), "Ajustes tiene plantilla, indicadores y etapas");
  await n.foto(salida, "ajustes-1440");

  // Dueña, celular
  await n.tamano(390, 844, true);
  await n.ir("/equipo", 9000);
  await n.foto(salida, "equipo-390");

  // Responsable de punto, celular: registro del día de dos personas
  await n.entrar(claves["demo.responsable"].correo, claves["demo.responsable"].contrasena);
  await n.ir("/equipo", 9000);
  await n.foto(salida, "equipo-responsable-390");
  const inicio = Date.now();
  let toques = 0;
  await n.tocar("button", "Registro del día"); toques++;
  await espera(3500);
  await n.foto(salida, "registro-vacio-390", false);
  // Dos personas: 6 clientes, 3 explicaciones, 2 consultas, 1 referido a la primera; 4 clientes y 2 explicaciones a la segunda.
  const sumar = async (persona, etiqueta, veces) => {
    for (let i = 0; i < veces; i++) {
      const ok = await n.js(`(() => { const f = document.querySelectorAll("dialog[open] .m-registro")[${persona}];
        const b = f && [...f.querySelectorAll("button")].find((x) => x.getAttribute("aria-label")?.startsWith("Sumar uno: " + ${JSON.stringify(etiqueta)}));
        if (!b) return false; b.click(); return true; })()`);
      if (!ok) throw new Error(`No encontré el + de «${etiqueta}»`);
      toques++;
      await espera(120);
    }
  };
  await sumar(0, "Clientes atendidos", 6); await sumar(0, "Explicó", 3); await sumar(0, "Consultó", 2); await sumar(0, "Referidos", 1);
  await sumar(1, "Clientes atendidos", 4); await sumar(1, "Explicó", 2);
  await n.foto(salida, "registro-lleno-390", false);
  await n.tocar("dialog[open] button[type=submit]"); toques++;
  await espera(1200);
  const g = await n.texto();
  const cerrada = await n.js("!document.querySelector('dialog[open]')");
  revisar(cerrada && /Registro del día guardado|No había nada que cambiar/.test(g), "La responsable guarda el registro del día de dos personas");
  console.log(`Toques: ${toques}. Tiempo del robot: ${Math.round((Date.now() - inicio) / 1000)} s (una persona tarda más: cuenta los toques).`);
  await n.foto(salida, "registro-guardado-390", false);
} catch (e) {
  fallas.push(String(e.message ?? e));
  console.log("FALLA " + (e.message ?? e));
  try { await n.foto(salida, "error"); } catch { /* nada */ }
} finally {
  n.cerrar();
}
console.log(fallas.length ? `${fallas.length} falla(s)` : "Todo bien");
process.exit(fallas.length ? 1 : 0);
