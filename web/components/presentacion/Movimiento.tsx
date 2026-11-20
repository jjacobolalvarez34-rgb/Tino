"use client";
// Piezas pequeñas de cliente: la línea de avance bajo la cabecera, el botón que pausa el
// movimiento continuo de la página (avisos, franja y vaivén de las capas), el botón de sonido y
// la ventisca entre secciones.
import { useEffect, useRef, useState } from "react";
import { usePausa } from "./Escenario";
import { Icono } from "./Lucide";
import s from "./presentacion.module.css";

// Una línea ciruela de 2 px que crece con lo que se ha recorrido de la página. Solo
// transform, en un requestAnimationFrame por scroll.
export function Avance() {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let cuadro = 0;
    const pintar = () => {
      cuadro = 0;
      const total = document.documentElement.scrollHeight - window.innerHeight;
      const p = total > 0 ? Math.min(1, Math.max(0, window.scrollY / total)) : 0;
      el.style.transform = `scaleX(${p.toFixed(4)})`;
    };
    const pedir = () => {
      if (!cuadro) cuadro = requestAnimationFrame(pintar);
    };
    pintar();
    window.addEventListener("scroll", pedir, { passive: true });
    window.addEventListener("resize", pedir);
    return () => {
      window.removeEventListener("scroll", pedir);
      window.removeEventListener("resize", pedir);
      cancelAnimationFrame(cuadro);
    };
  }, []);
  return <span ref={ref} className={s.avance} aria-hidden="true" />;
}

export function BotonPausa() {
  const { pausado, alternar } = usePausa();
  const texto = pausado ? "Reanudar movimiento" : "Pausar movimiento";
  return (
    <button type="button" className={s.pausa} onClick={alternar} aria-label={texto}>
      <Icono nombre={pausado ? "play" : "pause"} tamano={16} />
      <span className={s.pausaTexto} aria-hidden="true">
        {texto}
      </span>
    </button>
  );
}

// La ventisca entre secciones (pedido de Jacobo, 20 nov; D-065): al pulsar un enlace del menú
// o un "Ver cómo…", el viento se lleva lo que se ve, la página salta a la sección elegida y esta
// aparece. Con Ctrl, Mayús o clic del medio el enlace funciona normal. "Saltar al contenido" no
// sopla: es para el teclado y el lector de pantalla.
export function Ventisca() {
  useEffect(() => {
    let yendo = false;
    const alPulsar = async (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const enlace = (e.target as Element | null)?.closest?.("a");
      const href = enlace?.getAttribute("href") ?? "";
      if (!enlace || enlace.target === "_blank" || href === "#contenido") return;
      const interno = href.startsWith("#") && href.length > 1;
      if (!interno && href !== "/precios") return;
      const destino = interno ? document.getElementById(href.slice(1)) : null;
      if (interno && !destino) return;
      const principal = document.getElementById("contenido");
      if (!principal) return;
      e.preventDefault();
      if (yendo) return;
      yendo = true;
      const { soplar, llevarseConElViento, piezasVisibles, aparecer } = await import("@/lib/ventisca");
      soplar();
      const volver = await llevarseConElViento(piezasVisibles(principal));
      if (!destino) { window.location.assign(href); return; }
      history.pushState(null, "", href);
      destino.scrollIntoView({ behavior: "instant" as ScrollBehavior, block: "start" });
      volver();
      aparecer(destino);
      yendo = false;
    };
    document.addEventListener("click", alPulsar);
    return () => document.removeEventListener("click", alPulsar);
  }, []);
  return null;
}

// Sonido de la ventisca: apagado hasta que la persona lo active (la portada nunca suena sola).
// Al activarlo suena una vez, para que sepa cómo es.
export function BotonSonido() {
  const [activo, setActivo] = useState(false);
  useEffect(() => { import("@/lib/ventisca").then((v) => setActivo(v.sonidoActivo())); }, []);
  const texto = activo ? "Apagar el sonido" : "Activar el sonido";
  return (
    <button type="button" className={s.pausa} role="switch" aria-checked={activo} aria-label="Sonido del viento al cambiar de sección"
      title={texto}
      onClick={async () => {
        const v = await import("@/lib/ventisca");
        const nuevo = !activo;
        v.guardarSonido(nuevo);
        setActivo(nuevo);
        if (nuevo) v.soplar();
      }}>
      <Icono nombre={activo ? "volume-2" : "volume-x"} tamano={18} />
    </button>
  );
}
