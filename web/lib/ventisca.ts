"use client";
// La "ventisca" al cambiar de pantalla (pedido de Jacobo, 20 nov): los elementos de la pantalla
// actual se los lleva el viento uno por uno (se corren a la derecha, giran y se desvanecen) y
// suena un soplido corto. Solo transform y opacity, con la Web Animations API: liviano en el
// celular. Dentro del programa se respeta "reducir movimiento" (DESIGN.md §11).

const ELEMENTOS = [
  "h1", ".m-contexto", ".m-cifra", ".m-frase", ".m-fila", ".m-ranking li", ".m-grupo > h2", ".m-linea li",
  ".m-punto", ".chip", ".boton", "tr", ".m-anillo", ".m-avatar", ".m-esqueleto", ".tarjeta > *",
].join(",");
const MAXIMO = 48;
const DURACION = 700;

export const sinMovimiento = () =>
  typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

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

// Se lleva el viento lo que se ve de la pantalla. Termina cuando ya no queda nada a la vista.
export function llevarseConElViento(contenedor: HTMLElement | null): Promise<void> {
  if (!contenedor || sinMovimiento()) return Promise.resolve();
  const alto = window.innerHeight;
  const vistos = [...contenedor.querySelectorAll<HTMLElement>(ELEMENTOS)]
    .filter((e) => { const r = e.getBoundingClientRect(); return r.bottom > 0 && r.top < alto && r.width > 0; })
    // Solo los de más afuera: si un padre ya vuela, sus hijos van con él.
    .filter((e, _, todos) => !todos.some((o) => o !== e && o.contains(e)))
    .slice(0, MAXIMO);
  if (!vistos.length) return Promise.resolve();
  const ancho = window.innerWidth;
  const animaciones = vistos.map((e) => {
    const r = e.getBoundingClientRect();
    // El viento llega desde la izquierda: lo de la izquierda sale primero.
    const espera = (r.left / ancho) * 160 + (r.top / alto) * 60 + Math.random() * 90;
    const lejos = ancho - r.left + 120 + Math.random() * 160;
    const sube = -(30 + Math.random() * 90);
    const giro = (Math.random() < 0.8 ? 1 : -1) * (25 + Math.random() * 140);
    return e.animate([
      { transform: "translate(0, 0) rotate(0deg)", opacity: 1 },
      { transform: `translate(${lejos * 0.25}px, ${sube * 0.4}px) rotate(${giro * 0.3}deg)`, opacity: 1, offset: 0.35 },
      { transform: `translate(${lejos}px, ${sube}px) rotate(${giro}deg)`, opacity: 0 },
    ], { duration: DURACION + Math.random() * 200, delay: espera, easing: "cubic-bezier(.5,0,.75,.25)", fill: "forwards" });
  });
  return Promise.race([
    Promise.all(animaciones.map((a) => a.finished)).then(() => undefined),
    new Promise<void>((r) => setTimeout(r, DURACION + 520)),
  ]);
}
