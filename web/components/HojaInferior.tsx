"use client";
// Hoja que sube desde abajo en el celular y panel a la derecha en el computador.
// Usa <dialog>: Esc cierra, el foco queda adentro y vuelve a donde estaba al cerrar.
import { useEffect, useRef } from "react";
import { Icono } from "./Iconos";

export function HojaInferior({ abierta, titulo, alCerrar, children, pie }: {
  abierta: boolean; titulo: string; alCerrar: () => void; children: React.ReactNode; pie?: React.ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierta && !d.open) d.showModal();
    if (!abierta && d.open) d.close();
  }, [abierta]);

  return (
    <dialog ref={ref} className="m-hoja" aria-labelledby="m-hoja-titulo"
      onCancel={(e) => { e.preventDefault(); alCerrar(); }}
      onClick={(e) => { if (e.target === ref.current) alCerrar(); }}>
      <div className="m-hoja-dentro">
        <header className="m-hoja-cabeza">
          <span className="m-hoja-agarre" aria-hidden="true" />
          <h2 id="m-hoja-titulo">{titulo}</h2>
          <button className="m-icono-boton" onClick={alCerrar} aria-label="Cerrar"><Icono id="cerrar" /></button>
        </header>
        <div className="m-hoja-cuerpo">{abierta && children}</div>
        {pie && <footer className="m-hoja-pie">{pie}</footer>}
      </div>
    </dialog>
  );
}
