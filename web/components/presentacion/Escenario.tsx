"use client";
// Envuelve la página: entradas al hacer scroll, tarjetas que se inclinan con el cursor y
// el botón de pausa del movimiento continuo.
//
// Entradas: sin JavaScript todo se ve en su estado final. Al montar, se marca con
// data-visto lo que ya está en pantalla (para que no parpadee), se pone data-animar en la
// raíz y se observa el resto. Cuando un elemento con data-revelar entra a la pantalla
// recibe data-visto y el CSS hace su entrada, una sola vez.
//
// Las animaciones corren siempre, también con "reducir movimiento" activo: lo decidió
// Jacobo. Lo que se mueve solo y sin fin (los avisos de la portada, la franja, el vaivén
// de las capas) se puede pausar con un botón, como pide WCAG 2.2.2; la pausa se recuerda
// en este navegador.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

const CLAVE_PAUSA = "tino-presentacion-pausa";

const Pausa = createContext<{ pausado: boolean; alternar: () => void }>({ pausado: false, alternar: () => {} });
export const usePausa = () => useContext(Pausa);

export function Escenario({ className, children }: { className?: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pausado, setPausado] = useState(false);
  const pausadoRef = useRef(false);
  pausadoRef.current = pausado;

  useEffect(() => {
    try {
      if (window.localStorage.getItem(CLAVE_PAUSA) === "1") setPausado(true);
    } catch {
      /* Sin almacenamiento: arranca en movimiento. */
    }
  }, []);

  const alternar = useCallback(() => {
    setPausado((antes) => {
      const ahora = !antes;
      try {
        window.localStorage.setItem(CLAVE_PAUSA, ahora ? "1" : "0");
      } catch {
        /* Se pausa igual, solo que no se recuerda. */
      }
      return ahora;
    });
  }, []);

  // Entradas al hacer scroll.
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
      { rootMargin: "0px 0px -10% 0px", threshold: 0.15 },
    );
    for (const el of elementos) if (!el.hasAttribute("data-visto")) observador.observe(el);
    return () => observador.disconnect();
  }, []);

  // Tarjetas con data-inclinar: se inclinan hasta 1,5 grados hacia el cursor. Solo con
  // mouse (en el celular no hay cursor) y nunca con el movimiento en pausa.
  useEffect(() => {
    const raiz = ref.current;
    if (!raiz || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
    let actual: HTMLElement | null = null;
    let ultimo: PointerEvent | null = null;
    let cuadro = 0;

    const soltar = (el: HTMLElement) => {
      el.style.setProperty("--rx", "0deg");
      el.style.setProperty("--ry", "0deg");
    };
    const pintar = () => {
      cuadro = 0;
      if (!actual || !ultimo) return;
      const caja = actual.getBoundingClientRect();
      const x = (ultimo.clientX - caja.left) / caja.width - 0.5;
      const y = (ultimo.clientY - caja.top) / caja.height - 0.5;
      actual.style.setProperty("--ry", `${(x * 3).toFixed(2)}deg`);
      actual.style.setProperty("--rx", `${(-y * 3).toFixed(2)}deg`);
    };
    const mover = (e: PointerEvent) => {
      const el = pausadoRef.current ? null : ((e.target as Element).closest?.("[data-inclinar]") as HTMLElement | null);
      if (el !== actual) {
        if (actual) soltar(actual);
        actual = el;
      }
      if (!actual) return;
      ultimo = e;
      if (!cuadro) cuadro = requestAnimationFrame(pintar);
    };
    const salir = () => {
      if (actual) soltar(actual);
      actual = null;
    };
    raiz.addEventListener("pointermove", mover, { passive: true });
    raiz.addEventListener("pointerleave", salir);
    return () => {
      raiz.removeEventListener("pointermove", mover);
      raiz.removeEventListener("pointerleave", salir);
      cancelAnimationFrame(cuadro);
    };
  }, []);

  const valor = useMemo(() => ({ pausado, alternar }), [pausado, alternar]);

  return (
    <Pausa.Provider value={valor}>
      <div ref={ref} className={className} data-pausa={pausado ? "" : undefined}>
        {children}
      </div>
    </Pausa.Provider>
  );
}
