// Capturas de las pantallas con la empresa de demostración (datos inventados), a 390 y 1440 px.
// Usa Chrome sin ventana por el protocolo de depuración: no toca la pantalla de nadie.
// Uso: node tests/demo/capturas.mjs <web> <puerto de depuración> <sesión.json> <carpeta de salida>
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";

const [web, puerto, archivoSesion, salida] = process.argv.slice(2);
const sesion = JSON.parse(readFileSync(archivoSesion, "utf8"));
mkdirSync(salida, { recursive: true });
const espera = (ms) => new Promise((r) => setTimeout(r, ms));

const objetivo = await (await fetch(`http://127.0.0.1:${puerto}/json/new?about:blank`, { method: "PUT" })).json();
const ws = new WebSocket(objetivo.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener("open", r, { once: true }));
let n = 0;
const pendientes = new Map();
ws.addEventListener("message", (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pendientes.has(m.id)) { pendientes.get(m.id)(m); pendientes.delete(m.id); }
});
const cdp = (method, params = {}) => new Promise((r) => { const id = ++n; pendientes.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
const js = async (expresion) => (await cdp("Runtime.evaluate", { expression: expresion, awaitPromise: true, returnByValue: true })).result?.result?.value;

await cdp("Page.enable");
await cdp("Runtime.enable");
async function ir(ruta) { await cdp("Page.navigate", { url: web + ruta }); await espera(7000); }
async function foto(nombre, completa = true) {
  const r = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: completa });
  writeFileSync(`${salida}/${nombre}.png`, Buffer.from(r.result.data, "base64"));
  console.log("captura:", nombre);
}

// La sesión va al almacenamiento del navegador, como la deja supabase-js al entrar.
await ir("/entrar");
await js(`localStorage.setItem(${JSON.stringify(sesion.clave)}, ${JSON.stringify(JSON.stringify(sesion.valor))}); true`);

for (const [ancho, alto, movil, sufijo] of [[390, 844, true, "390"], [1440, 900, false, "1440"]]) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: ancho, height: alto, deviceScaleFactor: movil ? 2 : 1, mobile: movil });
  await ir("/hoy"); await foto(`hoy-${sufijo}`);
  await ir("/ventas"); await foto(`ventas-${sufijo}`);
  const primera = await js(`(async () => { const r = await fetch('${web}/'); return true })()`);
  void primera;
  await ir("/equipo"); await espera(2000);
  if (movil) {
    await foto(`equipo-lista-${sufijo}`);
    await js(`document.querySelector('.m-ld-lista a.m-fila')?.click(); true`); await espera(5000);
  }
  await foto(`equipo-ficha-${sufijo}`);
  await js(`[...document.querySelectorAll('[data-recorrido="registrar"]')].find(e => e.offsetParent !== null)?.click(); true`);
  await espera(1500);
  await js(`[...document.querySelectorAll('.m-hoja .m-fila')].find(e => e.textContent.includes('Compromiso'))?.click(); true`);
  await espera(3500);
  await foto(`registrar-compromiso-${sufijo}`, false);
  await js(`document.querySelector('dialog[open] .m-icono-boton')?.click(); true`);
}
await ir("/precios");
for (const [ancho, alto, movil, sufijo] of [[390, 844, true, "390"], [1440, 900, false, "1440"]]) {
  await cdp("Emulation.setDeviceMetricsOverride", { width: ancho, height: alto, deviceScaleFactor: movil ? 2 : 1, mobile: movil });
  await ir("/precios"); await foto(`precios-${sufijo}`);
}
ws.close();
process.exit(0);
