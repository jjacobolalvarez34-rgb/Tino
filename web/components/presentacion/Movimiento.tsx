"use client";
// Dos piezas pequeñas de cliente: la línea de avance bajo la cabecera y el botón que pausa
// el movimiento continuo de la página (avisos, franja y vaivén de las capas).
import { useEffect, useRef } from "react";
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
