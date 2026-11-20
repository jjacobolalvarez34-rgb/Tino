// Chip de estado de DESIGN.md: símbolo + palabra + color. Sirve en servidor y en cliente.
import type { ReactNode } from "react";
import type { Estado } from "./ejemplo";
import s from "./presentacion.module.css";

const SIMBOLO: Record<Estado, string> = { ok: "●", revisar: "▲", mal: "■", espera: "—", neutro: "—" };
const CLASE: Record<Estado, string> = {
  ok: s.chipOk,
  revisar: s.chipRevisar,
  mal: s.chipMal,
  espera: s.chipEspera,
  neutro: s.chipNeutro,
};

export function Simbolo({ estado }: { estado: Estado }) {
  return (
    <span aria-hidden="true" className={s[`simbolo_${estado}`]}>
      {SIMBOLO[estado]}
    </span>
  );
}

export function Chip({ estado, children }: { estado: Estado; children: ReactNode }) {
  return (
    <span className={`${s.chip} ${CLASE[estado]}`}>
      <span aria-hidden="true">{SIMBOLO[estado]}</span>
      {children}
    </span>
  );
}
