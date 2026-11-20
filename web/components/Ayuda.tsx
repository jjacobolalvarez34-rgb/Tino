"use client";
// Un "?" que explica un número. Se abre con el cursor, con el foco del teclado o tocándolo
// (en el celular no hay cursor); Esc lo cierra. El texto también lo lee el lector de pantalla.
import { useId, useState } from "react";

export function Ayuda({ texto, etiqueta = "Cómo se calcula" }: { texto: string; etiqueta?: string }) {
  const id = useId();
  const [abierta, setAbierta] = useState(false);
  return (
    <span className="m-ayuda" onMouseEnter={() => setAbierta(true)} onMouseLeave={() => setAbierta(false)}>
      <button type="button" className="m-ayuda-boton" aria-label={etiqueta} aria-describedby={id} aria-expanded={abierta}
        onClick={() => setAbierta((a) => !a)} onFocus={() => setAbierta(true)} onBlur={() => setAbierta(false)}
        onKeyDown={(e) => { if (e.key === "Escape") setAbierta(false); }}>?</button>
      <span id={id} role="tooltip" className={"m-ayuda-texto" + (abierta ? " ver" : "")}>{texto}</span>
    </span>
  );
}

export const AYUDA_TICKET = "Ticket promedio = venta de los días que traen el número de facturas ÷ esas facturas. "
  + "Los días sin número de facturas no cuentan, para no inflarlo. Incluye la venta que todavía no tiene persona, "
  + "así el total cuadra con los puntos.";
