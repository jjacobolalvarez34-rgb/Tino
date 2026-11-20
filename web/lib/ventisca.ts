"use client";
// La "ventisca" de la portada (pedido de Jacobo, 20 nov): al pulsar una sección del menú, lo que
// se ve se lo lleva el viento pedazo a pedazo (se corre a la derecha, gira y se desvanece),
// suena un soplido corto y aparece la sección elegida. Solo transform y opacity, con la Web
// Animations API: liviano en el celular. Corre siempre, aunque el sistema pida reducir
// movimiento (D-065, decisión de Jacobo). Dentro del programa no se usa.

const MAXIMO = 60;
const DURACION = 700;

export function sonidoActivo() {
  try { return localStorage.getItem("tino-sonido") !== "no"; } catch { return true; }
}
export function guardarSonido(si: boolean) {
  try { localStorage.setItem("tino-sonido", si ? "si" : "no"); } catch { /* sin almacenamiento: queda como está */ }
}

let audio: AudioContext | null = null;

// Un soplido de viento hecho con ruido filtrado: sin archivos de sonido que descargar.
export function soplar() {
  if (!sonidoActivo()) return;
  try {
    const Contexto = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
    audio = audio ?? new Contexto();
    const ahora = audio.currentTime;
    const segundos = 1.1;
    const buffer = audio.createBuffer(1, Math.floor(audio.sampleRate * segundos), audio.sampleRate);
    const datos = buffer.getChannelData(0);
    let ultimo = 0;
    for (let i = 0; i < datos.length; i++) {  // ruido "marrón": más grave y suave que el blanco
      ultimo = (ultimo + 0.02 * (Math.random() * 2 - 1)) / 1.02;
      datos[i] = ultimo * 3.5;
    }
    const fuente = audio.createBufferSource();
    fuente.buffer = buffer;
    const filtro = audio.createBiquadFilter();
    filtro.type = "bandpass";
    filtro.Q.value = 0.9;
    filtro.frequency.setValueAtTime(350, ahora);
    filtro.frequency.exponentialRampToValueAtTime(1600, ahora + 0.45);
    filtro.frequency.exponentialRampToValueAtTime(600, ahora + segundos);
    const volumen = audio.createGain();
    volumen.gain.setValueAtTime(0.0001, ahora);
    volumen.gain.exponentialRampToValueAtTime(0.5, ahora + 0.12);
    volumen.gain.exponentialRampToValueAtTime(0.0001, ahora + segundos);
    fuente.connect(filtro).connect(volumen).connect(audio.destination);
    fuente.start(ahora);
    fuente.stop(ahora + segundos);
  } catch { /* sin audio: la transición sigue sin sonido */ }
}

// Los pedazos que se lleva el viento: se baja por el árbol desde el contenedor y cada bloque
// visible que ocupe menos de una fracción de la pantalla vuela entero (una tarjeta, un título,
// un párrafo). Lo grande se parte en sus hijos. Así sirve sin conocer las clases de la página.
export function piezasVisibles(contenedor: HTMLElement, fraccion = 0.3): HTMLElement[] {
  const ancho = window.innerWidth, alto = window.innerHeight, pantalla = ancho * alto;
  const piezas: HTMLElement[] = [];
  const visitar = (e: HTMLElement) => {
    if (piezas.length >= MAXIMO) return;
    const r = e.getBoundingClientRect();
    const visible = Math.max(0, Math.min(r.right, ancho) - Math.max(r.left, 0)) * Math.max(0, Math.min(r.bottom, alto) - Math.max(r.top, 0));
    if (!visible) return;
    const hijos = [...e.children].filter((h): h is HTMLElement => h instanceof HTMLElement);
    if (visible / pantalla <= fraccion || !hijos.length) { piezas.push(e); return; }
    hijos.forEach(visitar);
  };
  [...contenedor.children].forEach((h) => { if (h instanceof HTMLElement) visitar(h); });
  return piezas;
}

// Se lleva el viento las piezas. Termina cuando ya no queda nada a la vista y devuelve con qué
// ponerlas de nuevo en su sitio (se cancelan las animaciones).
export async function llevarseConElViento(piezas: HTMLElement[]): Promise<() => void> {
  if (!piezas.length) return () => {};
  const ancho = window.innerWidth, alto = window.innerHeight;
  const animaciones = piezas.map((e) => {
    const r = e.getBoundingClientRect();
    // El viento llega desde la izquierda: lo de la izquierda sale primero.
    const espera = (Math.max(0, r.left) / ancho) * 160 + (Math.max(0, r.top) / alto) * 60 + Math.random() * 90;
    const lejos = ancho - r.left + 120 + Math.random() * 160;
    const sube = -(30 + Math.random() * 90);
    const giro = (Math.random() < 0.8 ? 1 : -1) * (25 + Math.random() * 140);
    return e.animate([
      { transform: "translate(0, 0) rotate(0deg)", opacity: 1 },
      { transform: `translate(${lejos * 0.25}px, ${sube * 0.4}px) rotate(${giro * 0.3}deg)`, opacity: 1, offset: 0.35 },
      { transform: `translate(${lejos}px, ${sube}px) rotate(${giro}deg)`, opacity: 0 },
    ], { duration: DURACION + Math.random() * 200, delay: espera, easing: "cubic-bezier(.5,0,.75,.25)", fill: "forwards" });
  });
  await Promise.race([
    Promise.all(animaciones.map((a) => a.finished)).then(() => undefined, () => undefined),
    new Promise<void>((r) => setTimeout(r, DURACION + 520)),
  ]);
  return () => animaciones.forEach((a) => a.cancel());
}

// La sección a la que se llega aparece en fade. Con la Web Animations API, que no apaga la regla
// global de "reducir movimiento" de globals.css (D-065).
export function aparecer(contenedor: HTMLElement | null) {
  contenedor?.animate([{ opacity: 0, transform: "translateX(-14px)" }, { opacity: 1, transform: "none" }],
    { duration: 340, easing: "ease-out" });
}
