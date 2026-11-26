// Capturas de la página pública (portada y /precios) a 390 y 1440 px, con y sin «reducir
// movimiento». Revisa lo del bloque B: que «Causa probable» y «Buscando la causa…» no queden
// encimados, que el resaltado del cierre esté en el punto del descuadre y que /precios muestre
// los tres planes.
// Uso: node tests/demo/capturas_portada.mjs <carpeta de salida>
import { abrir, espera } from "./navegador.mjs";

const [salida] = process.argv.slice(2);
const n = await abrir();
const fallas = [];
const revisar = (cond, que) => { console.log((cond ? "OK   " : "FALLA") + " " + que); if (!cond) fallas.push(que); };

// ¿Se ven a la vez los dos textos de la causa? (los dos visibles y con opacidad)
const encimados = `(() => {
  const vis = (e) => { if (!e) return false; const c = getComputedStyle(e); return c.visibility !== "hidden" && Number(c.opacity) > 0.05; };
  const b = [...document.querySelectorAll("p")].find((p) => p.textContent.trim() === "Buscando la causa…");
  const c = [...document.querySelectorAll("p")].find((p) => p.textContent.trim() === "Causa probable");
  return vis(b) && vis(c);
})()`;

try {
  for (const reducir of [false, true]) {
    await n.cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: reducir ? "reduce" : "no-preference" }] });
    for (const [ancho, alto, movil] of [[390, 844, true], [1440, 900, false]]) {
      const sufijo = `${ancho}${reducir ? "-reducido" : ""}`;
      await n.tamano(ancho, alto, movil);
      await n.ir("/", 6000);
      const destacado = await n.js(`[...document.querySelectorAll("li")].find((li) => [...li.classList].some((c) => c.includes("puntoDestacado")))?.querySelector("strong")?.textContent ?? ""`);
      revisar(destacado === "Punto Plaza", `(${sufijo}) el resaltado del cierre está en Punto Plaza`);
      await n.foto(salida, `portada-${sufijo}`, false);
      await n.js(`document.getElementById("descuadres").scrollIntoView(); true`);
      await espera(4500);   // la animación de la causa dura menos de 3 s
      revisar(!(await n.js(encimados)), `(${sufijo}) «Buscando la causa…» y «Causa probable» no quedan encimados`);
      await n.foto(salida, `descuadres-${sufijo}`, false);
      if (!reducir) {
        await n.ir("/precios", 5000);
        const t = await n.texto();
        revisar(/Equipo/.test(t) && /30\.000/.test(t) && /Caja/.test(t) && /45\.000/.test(t) && /Completo/.test(t) && /65\.000/.test(t),
          `(${sufijo}) /precios muestra Equipo 30.000, Caja 45.000 y Completo 65.000`);
        const visibles = await n.js(`[...document.querySelectorAll("h2,h3")].filter((h) => /^(Equipo|Caja|Completo)$/.test(h.textContent.trim()))
          .filter((h) => { const r = h.getBoundingClientRect(); return r.width > 0 && getComputedStyle(h).visibility !== "hidden"; }).length`);
        revisar(visibles >= 3, `(${sufijo}) los tres planes se ven en la página (${visibles})`);
        await n.foto(salida, `precios-${sufijo}`);
      }
    }
  }
} catch (e) {
  fallas.push(String(e.message ?? e));
  console.log("FALLA " + (e.message ?? e));
} finally {
  n.cerrar();
}
console.log(fallas.length ? `${fallas.length} falla(s)` : "Todo bien");
process.exit(fallas.length ? 1 : 0);
