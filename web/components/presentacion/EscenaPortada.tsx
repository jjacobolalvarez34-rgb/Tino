"use client";
// La escena de la portada: el cierre del día como capa principal, el cierre de ayer detrás,
// un aviso de pago que llega y se concilia (uno tras otro) y el anillo de meta de una
// persona. Todo es de ejemplo e inventado.
//
// Movimiento:
// - Al cargar, cada capa entra escalonada (CSS).
// - Los avisos se turnan: llega uno, dice "Buscando" 1,3 s, se resuelve y la fila de su
//   punto en el cierre se ilumina; a los 3,9 s llega el siguiente. Se detiene si la escena
//   no se ve, si la pestaña está oculta, si el cursor está encima o si se pausó el
//   movimiento.
// - Las capas flotan despacio (CSS) y, con mouse, se corren unos píxeles hacia el cursor;
//   al bajar por la página se separan un poco (parallax suave). Solo transform, y en un
//   único requestAnimationFrame que se apaga cuando todo quedó quieto.
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { Chip } from "./Chip";
import { Contador } from "./Contador";
import { usePausa } from "./Escenario";
import { Icono } from "./Lucide";
import { Chulito } from "./Marcas";
import { AVISOS, CIERRE, META_PORTADA, TOTAL_DIA, formatear, totalPunto } from "./ejemplo";
import s from "./presentacion.module.css";

const v = (variables: Record<string, string | number>) => variables as CSSProperties;
const pesos = (n: number) => formatear(n, "pesos");
const limitar = (n: number, min = -1, max = 1) => Math.min(max, Math.max(min, n));

export function EscenaPortada() {
  const { pausado } = usePausa();
  const ref = useRef<HTMLDivElement>(null);
  const pausadoRef = useRef(pausado);
  pausadoRef.current = pausado;
  const reiniciar = useRef<() => void>(() => {});

  // paso par: el aviso llega y busca; paso impar: el aviso quedó resuelto. El servidor pinta
  // el paso 1 (primer aviso ya resuelto), que es lo que se ve sin JavaScript.
  const [paso, setPaso] = useState(1);
  const [enVista, setEnVista] = useState(true);
  // Con el cursor encima los avisos se quedan quietos, para poder leerlos.
  const [encima, setEncima] = useState(false);

  useEffect(() => setPaso(0), []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let visible = true;
    let pestana = !document.hidden;
    const actualizar = () => setEnVista(visible && pestana);
    const observador =
      "IntersectionObserver" in window
        ? new IntersectionObserver(([e]) => {
            visible = !!e?.isIntersecting;
            actualizar();
          })
        : null;
    observador?.observe(el);
    const alCambiarPestana = () => {
      pestana = !document.hidden;
      actualizar();
    };
    document.addEventListener("visibilitychange", alCambiarPestana);
    return () => {
      observador?.disconnect();
      document.removeEventListener("visibilitychange", alCambiarPestana);
    };
  }, []);

  useEffect(() => {
    if (pausado || !enVista || encima) return;
    const dura = paso % 2 === 0 ? (paso === 0 ? 2200 : 1300) : 3900;
    const t = window.setTimeout(() => setPaso((p) => p + 1), dura);
    return () => window.clearTimeout(t);
  }, [paso, pausado, enVista, encima]);

  // Cursor y scroll: variables --px, --py (de −1 a 1) y --sy (de 0 a 1) en la escena.
  useEffect(() => {
    const escena = ref.current;
    const seccion = escena?.closest("section");
    if (!escena || !seccion) return;
    const objetivo = { x: 0, y: 0, s: 0 };
    const actual = { x: 0, y: 0, s: 0 };
    let cuadro = 0;

    const pintar = () => {
      cuadro = 0;
      let sigue = false;
      for (const k of ["x", "y", "s"] as const) {
        const d = objetivo[k] - actual[k];
        actual[k] = Math.abs(d) < 0.002 ? objetivo[k] : actual[k] + d * 0.12;
        if (actual[k] !== objetivo[k]) sigue = true;
      }
      escena.style.setProperty("--px", actual.x.toFixed(3));
      escena.style.setProperty("--py", actual.y.toFixed(3));
      escena.style.setProperty("--sy", actual.s.toFixed(3));
      if (sigue) cuadro = requestAnimationFrame(pintar);
    };
    const pedir = () => {
      if (!cuadro) cuadro = requestAnimationFrame(pintar);
    };
    const alMover = (e: PointerEvent) => {
      if (pausadoRef.current || e.pointerType !== "mouse") return;
      const c = escena.getBoundingClientRect();
      objetivo.x = limitar((e.clientX - c.left - c.width / 2) / (c.width / 2));
      objetivo.y = limitar((e.clientY - c.top - c.height / 2) / (c.height / 2));
      pedir();
    };
    const alSalir = () => {
      objetivo.x = 0;
      objetivo.y = 0;
      pedir();
    };
    const alDesplazar = () => {
      const c = seccion.getBoundingClientRect();
      objetivo.s = pausadoRef.current ? 0 : limitar(-c.top / c.height, 0, 1);
      pedir();
    };
    reiniciar.current = () => {
      if (pausadoRef.current) alSalir();
      alDesplazar();
    };

    seccion.addEventListener("pointermove", alMover, { passive: true });
    seccion.addEventListener("pointerleave", alSalir);
    window.addEventListener("scroll", alDesplazar, { passive: true });
    alDesplazar();
    return () => {
      seccion.removeEventListener("pointermove", alMover);
      seccion.removeEventListener("pointerleave", alSalir);
      window.removeEventListener("scroll", alDesplazar);
      cancelAnimationFrame(cuadro);
    };
  }, []);

  useEffect(() => reiniciar.current(), [pausado]);

  const n = AVISOS.length;
  const indice = Math.floor(paso / 2) % n;
  const resuelto = paso % 2 === 1;
  const anterior = (indice - 1 + n) % n;
  const destacado = resuelto ? AVISOS[indice].punto : null;

  return (
    <div
      ref={ref}
      className={s.escena}
      onPointerEnter={(e) => e.pointerType === "mouse" && setEncima(true)}
      onPointerLeave={() => setEncima(false)}
    >
      <div className={`${s.capa} ${s.capaPila}`} style={v({ "--k": 0.35 })}>
        <div className={s.pila}>
          {/* El cierre de ayer, detrás: da la idea de una pila de días ya revisados. */}
          <div className={`${s.capa} ${s.capaFantasma}`} style={v({ "--k": -0.5 })} aria-hidden="true">
            <div className={`${s.fantasma} ${s.entra}`} style={v({ "--d": "40ms" })}>
              <span className={s.pequeno}>Cierre del día · Viernes 13 nov</span>
              {[72, 58, 66, 50].map((ancho, i) => (
                <span key={i} className={s.rayaFantasma} style={{ width: `${ancho}%` }} />
              ))}
            </div>
          </div>

          <div
            className={`${s.tarjeta} ${s.cierre} ${s.entra}`}
            style={v({ "--d": "120ms" })}
            role="group"
            aria-label="Ejemplo de cierre del día con cuatro puntos"
          >
            <div className={s.tarjetaCabeza}>
              <div>
                <p className={s.subtitulo}>Cierre del día</p>
                <p className={s.pequeno}>{CIERRE.fecha} · 4 puntos · ejemplo</p>
              </div>
            </div>
            <ul className={s.puntos}>
              {CIERRE.puntos.map((p, i) => (
                <li
                  key={p.punto}
                  className={`${s.punto} ${destacado === p.punto ? s.puntoDestacado : ""}`}
                  style={v({ "--i": i })}
                >
                  <span className={s.puntoNombre}>
                    <strong>{p.punto}</strong>
                    <span className={s.pequeno}>
                      {p.estado === "mal"
                        ? `Falta ${pesos(-p.descuadre)}`
                        : p.estado === "revisar"
                          ? "Una transferencia por confirmar"
                          : "Todo coincide"}
                    </span>
                    {p.estado === "mal" && (
                      <span className={s.puntoCausa}>
                        <span>Causa probable: transferencia que no llegó</span>
                      </span>
                    )}
                  </span>
                  <span className={s.puntoValor}>
                    <span className={s.num}>{pesos(totalPunto(p))}</span>
                    <span className={s.puntoChip}>
                      <Chip estado={p.estado}>{p.chip}</Chip>
                    </span>
                  </span>
                </li>
              ))}
            </ul>
            <div className={s.totalDia}>
              <span className={s.pequeno}>Total del día</span>
              <span className={`${s.cifraGrande} ${s.num}`}>
                <Contador valor={TOTAL_DIA} alCargar retraso={1350} alinear="fin" />
              </span>
            </div>
            <div className={s.revisado}>
              <span className={s.revisadoMarca}>
                <Chulito clase={s.trazoRevisado} />
              </span>
              <span>
                <strong>Revisado a las {CIERRE.revisado}</strong>
                <span className={s.pequeno}>1 descuadre, con su causa probable</span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Avisos de pago: decorativos, repiten lo que ya dice el cierre. */}
      <div className={`${s.capa} ${s.capaAviso}`} style={v({ "--k": 1 })} aria-hidden="true">
        <div className={s.flota} style={v({ "--f": "-2s" })}>
          <div className={`${s.avisos} ${s.entra}`} style={v({ "--d": "900ms" })}>
            {AVISOS.map((a, i) => {
              const activo = i === indice;
              return (
                <div
                  key={a.hora}
                  className={`${s.aviso} ${activo ? s.avisoActivo : i === anterior ? s.avisoSale : ""}`}
                >
                  <span className={s.avisoIcono}>
                    <Icono nombre={a.icono} />
                  </span>
                  <span className={s.avisoCuerpo}>
                    <span className={s.pequeno}>
                      {a.origen} · {a.hora}
                    </span>
                    <strong className={s.num}>{a.que}</strong>
                    <span className={s.avisoPie}>
                      <span className={s.pequeno}>{a.punto}</span>
                      <span className={s.avisoEstado}>
                        <span className={`${s.avisoChip} ${activo && !resuelto ? s.visible : ""}`}>
                          <Chip estado="espera">Buscando</Chip>
                        </span>
                        <span className={`${s.avisoChip} ${activo && resuelto ? s.visible : ""}`}>
                          <Chip estado={a.estado}>{a.chip}</Chip>
                        </span>
                      </span>
                    </span>
                    <span className={`${s.avisoDetalle} ${activo && resuelto ? s.visible : ""}`}>{a.detalle}</span>
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Anillo de meta de una persona del equipo. */}
      <div className={`${s.capa} ${s.capaMeta}`} style={v({ "--k": 0.8 })} aria-hidden="true">
        <div className={s.flota} style={v({ "--f": "-5s" })}>
          <div className={`${s.metaTarjeta} ${s.entra}`} style={v({ "--d": "1250ms" })}>
            <span className={s.anillo}>
              <svg viewBox="0 0 48 48" focusable="false">
                <circle className={s.anilloFondo} cx="24" cy="24" r="20" />
                <circle
                  className={s.anilloTrazo}
                  cx="24"
                  cy="24"
                  r="20"
                  pathLength={1}
                  transform="rotate(-90 24 24)"
                  style={v({ "--meta": META_PORTADA.meta / 100 })}
                />
              </svg>
              <span className={`${s.anilloCifra} ${s.num}`}>
                <Contador valor={META_PORTADA.meta} formato="entero" alCargar retraso={1500} />
              </span>
            </span>
            <span className={s.metaCuerpo}>
              <strong>
                {META_PORTADA.nombre} · {META_PORTADA.punto}
              </strong>
              <span className={s.pequeno}>
                {META_PORTADA.meta} % de la meta · quedan {META_PORTADA.dias} días
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
