"use client";
// Cuánto pagaría con sus puntos: elige los puntos y si paga anual o es fundador.
import { useState } from "react";
import { CONDICIONES, PLANES, cotizar, pesosCortos } from "@/lib/precios";
import s from "./precios.module.css";

export function Calculadora() {
  const [puntos, setPuntos] = useState(5);
  const [anual, setAnual] = useState(false);
  const [fundador, setFundador] = useState(false);
  return (
    <section className={s.calculadora} aria-labelledby="t-calcular">
      <h2 id="t-calcular" className={s.subtitulo}>¿Cuánto sería con sus puntos?</h2>
      <div className={s.controles}>
        <label className={s.campo} htmlFor="c-puntos">
          <span>Puntos de venta: <b className={s.num}>{puntos}</b></span>
          <input id="c-puntos" type="range" min={CONDICIONES.minimoPuntos} max={40} value={puntos}
            onChange={(e) => setPuntos(Number(e.target.value))} />
        </label>
        <div className={s.opciones}>
          <label><input type="checkbox" checked={anual} onChange={(e) => setAnual(e.target.checked)} /> Pago anual (12 por {CONDICIONES.mesesPagadosAlAno})</label>
          <label><input type="checkbox" checked={fundador} onChange={(e) => setFundador(e.target.checked)} /> Precio de fundador (−{Math.round(CONDICIONES.descuentoFundador * 100)} %)</label>
        </div>
      </div>
      <div className={s.resultados} aria-live="polite">
        {PLANES.map((p) => {
          const c = cotizar(p, puntos, { anual, fundador });
          return (
            <div key={p.id} className={s.resultado}>
              <span className={s.resultadoPlan}>{p.nombre}</span>
              <span className={s.cifraMedia}>$ {pesosCortos(c.mensual)}<span className={s.unidad}> al mes</span></span>
              <span className={s.pequeno}>{anual ? `$ ${pesosCortos(c.alAno)} al año` : `Piloto de ${CONDICIONES.diasPiloto} días: $ ${pesosCortos(c.piloto)}`}</span>
            </div>
          );
        })}
      </div>
      <p className={s.pequeno}>Más la implementación, desde $ {pesosCortos(CONDICIONES.implementacionDesde)} una sola vez.</p>
    </section>
  );
}
