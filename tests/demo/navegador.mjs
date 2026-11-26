// Un navegador de prueba para recorrer Tino como lo haría una persona, sin ventana y sin dejar
// nada corriendo: prende la web ya compilada (web/.next-build), abre Chrome sin ventana con el
// perfil en D:, entra con un usuario de prueba y al final apaga todo.
//
// Lo usan los guiones de tests/demo (capturas, el recorrido de la dueña y el instructivo).
// Solo con la empresa de demostración (datos inventados): nunca con datos reales de un cliente.
import { spawn, execSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const RAIZ = new URL("../../", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const DATOS = "D:/Repositorios/Tino-datos/trabajo";
const CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe";
export const espera = (ms) => new Promise((r) => setTimeout(r, ms));

function variables() {
  const t = readFileSync(join(RAIZ, "web/.env.local"), "utf8");
  const v = (k) => (t.match(new RegExp(`^${k}=(.*)$`, "m")) ?? [])[1]?.trim();
  return { url: v("NEXT_PUBLIC_SUPABASE_URL"), anon: v("NEXT_PUBLIC_SUPABASE_ANON_KEY") };
}

function matar(hijo) {
  if (!hijo?.pid) return;
  try { execSync(`taskkill /PID ${hijo.pid} /T /F`, { stdio: "ignore" }); } catch { /* ya no estaba */ }
}

// Abre la web en un puerto libre y Chrome sin ventana. Devuelve las acciones del guion.
export async function abrir({ puertoWeb = 6002, puertoChrome = 9333 } = {}) {
  const entorno = { ...process.env, NEXT_DIST_DIR: ".next-build", NEXT_TELEMETRY_DISABLED: "1", TEMP: `${DATOS}/tmp`, TMP: `${DATOS}/tmp` };
  const web = spawn(process.execPath, [join(RAIZ, "web/node_modules/next/dist/bin/next"), "start", "-p", String(puertoWeb)],
    { cwd: join(RAIZ, "web"), env: entorno, stdio: "ignore", windowsHide: true });
  const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${puertoChrome}`, `--user-data-dir=${DATOS}/chrome-perfil`,
    `--disk-cache-dir=${DATOS}/chrome-cache`, "--no-first-run", "--no-default-browser-check", "--hide-scrollbars",
    "--autoplay-policy=no-user-gesture-required", "about:blank"], { stdio: "ignore", windowsHide: true });
  const cerrarTodo = () => { matar(chrome); matar(web); };
  process.on("exit", cerrarTodo);

  const base = `http://localhost:${puertoWeb}`;
  for (let i = 0; ; i++) {
    try { if ((await fetch(base + "/entrar")).ok) break; } catch { /* todavía no */ }
    if (i > 90) { cerrarTodo(); throw new Error("La web no prendió"); }
    await espera(1000);
  }
  let objetivo;
  for (let i = 0; ; i++) {
    try { objetivo = await (await fetch(`http://127.0.0.1:${puertoChrome}/json/new?about:blank`, { method: "PUT" })).json(); break; }
    catch { if (i > 30) { cerrarTodo(); throw new Error("Chrome no abrió"); } await espera(500); }
  }
  const ws = new WebSocket(objetivo.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener("open", r, { once: true }));
  let n = 0;
  const pendientes = new Map();
  ws.addEventListener("message", (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pendientes.has(m.id)) { pendientes.get(m.id)(m); pendientes.delete(m.id); }
  });
  const cdp = (method, params = {}) => new Promise((r) => { const id = ++n; pendientes.set(id, r); ws.send(JSON.stringify({ id, method, params })); });
  const js = async (expr) => {
    const r = await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true });
    if (r.result?.exceptionDetails) throw new Error("En la página: " + (r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text));
    return r.result?.result?.value;
  };
  await cdp("Page.enable");
  await cdp("Runtime.enable");

  const sb = variables();
  const acciones = {
    base, js, cdp,
    async tamano(ancho, alto, movil) {
      await cdp("Emulation.setDeviceMetricsOverride", { width: ancho, height: alto, deviceScaleFactor: movil ? 2 : 1, mobile: movil });
    },
    async ir(ruta, ms = 6000) { await cdp("Page.navigate", { url: base + ruta }); await espera(ms); },
    // Entra como un usuario de prueba: la sesión queda en el navegador como la deja supabase-js.
    async entrar(correo, contrasena) {
      const r = await fetch(`${sb.url}/auth/v1/token?grant_type=password`, {
        method: "POST", headers: { apikey: sb.anon, "Content-Type": "application/json" }, body: JSON.stringify({ email: correo, password: contrasena }),
      });
      if (!r.ok) throw new Error("No pudo entrar con el usuario de prueba");
      const sesion = await r.json();
      const clave = `sb-${new URL(sb.url).hostname.split(".")[0]}-auth-token`;
      await acciones.ir("/entrar", 2500);
      await js(`localStorage.clear(); localStorage.setItem(${JSON.stringify(clave)}, ${JSON.stringify(JSON.stringify(sesion))}); true`);
    },
    async foto(carpeta, nombre, completa = true) {
      mkdirSync(carpeta, { recursive: true });
      const r = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: completa });
      writeFileSync(`${carpeta}/${nombre}.png`, Buffer.from(r.result.data, "base64"));
      return `${carpeta}/${nombre}.png`;
    },
    // Toca el primer elemento visible que cumpla el selector y, si se da, que tenga ese texto.
    async tocar(selector, texto) {
      const ok = await js(`(() => { const t = ${JSON.stringify(texto ?? "")};
        const e = [...document.querySelectorAll(${JSON.stringify(selector)})].find((x) => x.offsetParent !== null && (!t || x.textContent.includes(t)));
        if (!e) return false; e.scrollIntoView({ block: "center" }); e.click(); return true; })()`);
      if (!ok) throw new Error(`No encontré «${texto ?? selector}» en la pantalla`);
      await espera(900);
    },
    async elegir(selector, texto) {
      const ok = await js(`(() => { const s = [...document.querySelectorAll(${JSON.stringify(selector)})].find((x) => x.offsetParent !== null);
        if (!s) return false; const o = [...s.options].find((x) => x.textContent.includes(${JSON.stringify(texto)})); if (!o) return false;
        const set = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set; set.call(s, o.value);
        s.dispatchEvent(new Event("change", { bubbles: true })); return true; })()`);
      if (!ok) throw new Error(`No pude elegir «${texto}»`);
      await espera(1500);
    },
    texto: () => js("document.body.innerText"),
    cerrar() { try { ws.close(); } catch { /* nada */ } cerrarTodo(); },
  };
  return acciones;
}
