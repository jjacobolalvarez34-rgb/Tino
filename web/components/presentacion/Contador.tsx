"use client";
// Un número que cuenta desde cero cuando entra a la pantalla (600 ms).
//
// El servidor escribe el valor final, así que sin JavaScript se lee bien. Si el número ya
// está en pantalla al cargar, no se reinicia (evita que se vea saltar a cero), salvo que
// sea de la portada (alCargar): esos están ocultos por su propia entrada mientras la
// página despierta, y cuentan cuando terminan de entrar. El lector de pantalla siempre lee
// el valor final; la cifra que se mueve está oculta para él, y una copia invisible del
// valor final reserva el ancho para que nada se corra.
import { useEffect, useRef, useState } from "react";
import { formatear, type Formato } from "./ejemplo";
import s from "./presentacion.module.css";

export function Contador({
  valor,
  formato = "pesos",
  retraso = 0,
  duracion = 600,
  alinear = "inicio",
  alCargar = false,
}: {
  valor: number;
  formato?: Formato;
  retraso?: number;
  duracion?: number;
  alinear?: "inicio" | "fin";
  alCargar?: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const [mostrado, setMostrado] = useState(valor);

  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) return;
    const caja = el.getBoundingClientRect();
    if (!alCargar && caja.top < window.innerHeight && caja.bottom > 0) return;

    const montado = performance.now();
    setMostrado(0);
    let cuadro = 0;
    let espera = 0;
    // Los montos grandes avanzan de mil en mil: se lee mejor que una ruleta de dígitos.
    const paso = Math.abs(valor) >= 10_000 ? 1_000 : 1;
    const observador = new IntersectionObserver(
      ([entrada]) => {
        if (!entrada?.isIntersecting) return;
        observador.disconnect();
        // En la portada el retraso cuenta desde que cargó la página, no desde que se ve.
        const falta = alCargar ? Math.max(0, retraso - (performance.now() - montado)) : retraso;
        espera = window.setTimeout(() => {
          const inicio = performance.now();
          const avanzar = (ahora: number) => {
            const t = Math.min(1, (ahora - inicio) / duracion);
            const suave = 1 - Math.pow(1 - t, 3);
            setMostrado(t === 1 ? valor : Math.round((valor * suave) / paso) * paso);
            if (t < 1) cuadro = requestAnimationFrame(avanzar);
          };
          cuadro = requestAnimationFrame(avanzar);
        }, falta);
      },
      { threshold: 0.6 },
    );
    observador.observe(el);
    return () => {
      observador.disconnect();
      window.clearTimeout(espera);
      cancelAnimationFrame(cuadro);
    };
  }, [valor, retraso, duracion, alCargar]);

  const final = formatear(valor, formato);
  return (
    <span ref={ref} className={`${s.contador} ${alinear === "fin" ? s.contadorFin : ""}`}>
      <span className={s.contadorFantasma} aria-hidden="true">{final}</span>
      <span aria-hidden="true">{formatear(mostrado, formato)}</span>
      <span className={s.oculto}>{final}</span>
    </span>
  );
}
