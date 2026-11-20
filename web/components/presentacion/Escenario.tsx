"use client";
// Envuelve la página y prende las entradas al hacer scroll.
//
// Cómo funciona: sin JavaScript todo se ve en su estado final. Al montar, este
// componente marca con data-visto lo que ya está en pantalla (para que no parpadee),
// pone data-animar en la raíz y observa el resto. Cuando un elemento con data-revelar
// entra a la pantalla recibe data-visto y el CSS hace su entrada, una sola vez.
//
// Las animaciones corren siempre, también con "reducir movimiento" activo: lo decidió
// Jacobo. Por eso son cortas (150 a 600 ms), sin parallax y sin nada que se repita.
import { useEffect, useRef, type ReactNode } from "react";

export function Escenario({ className, children }: { className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const raiz = ref.current;
    if (!raiz || !("IntersectionObserver" in window)) return;

    const elementos = Array.from(raiz.querySelectorAll<HTMLElement>("[data-revelar]"));
    const alto = window.innerHeight;
    for (const el of elementos) {
      const caja = el.getBoundingClientRect();
      if (caja.top < alto && caja.bottom > 0) el.setAttribute("data-visto", "");
    }
    raiz.setAttribute("data-animar", "");

    const observador = new IntersectionObserver(
      (entradas) => {
        for (const entrada of entradas) {
          if (!entrada.isIntersecting) continue;
          entrada.target.setAttribute("data-visto", "");
          observador.unobserve(entrada.target);
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.2 },
    );
    for (const el of elementos) if (!el.hasAttribute("data-visto")) observador.observe(el);
    return () => observador.disconnect();
  }, []);

  return (
    <div ref={ref} className={className}>
      {children}
    </div>
  );
}
