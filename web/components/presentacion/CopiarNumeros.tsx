"use client";
// Botón "Copiar como números" de verdad: copia la tabla de ejemplo como enteros sin $ ni
// puntos, separados por tabulación, igual que en el programa. Si el navegador no deja
// copiar, selecciona el texto para copiarlo con Ctrl+C.
import { useEffect, useRef, useState } from "react";
import { Icono } from "./Lucide";
import s from "./presentacion.module.css";

export function CopiarNumeros({ texto }: { texto: string }) {
  const [estado, setEstado] = useState<"" | "copiado" | "manual">("");
  const vista = useRef<HTMLPreElement>(null);

  useEffect(() => {
    if (estado !== "copiado") return;
    const t = window.setTimeout(() => setEstado(""), 6000);
    return () => window.clearTimeout(t);
  }, [estado]);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setEstado("copiado");
    } catch {
      const el = vista.current;
      const seleccion = window.getSelection();
      if (el && seleccion) {
        const rango = document.createRange();
        rango.selectNodeContents(el);
        seleccion.removeAllRanges();
        seleccion.addRange(rango);
      }
      setEstado("manual");
    }
  }

  return (
    <div className={s.copiar}>
      <div className={s.copiarFila}>
        <button type="button" className={`${s.boton} ${s.secundario}`} onClick={copiar}>
          <span className={s.copiarIcono} key={estado === "copiado" ? "ok" : "copiar"}>
            <Icono nombre={estado === "copiado" ? "check" : "copy"} />
          </span>
          Copiar como números
        </button>
        <p className={s.copiarEstado} role="status" aria-live="polite">
          {estado === "copiado" && "Copiado. Péguelo en una hoja de Excel: las columnas se pueden sumar."}
          {estado === "manual" && "El navegador no dejó copiar. Ya quedó seleccionado: cópielo con Ctrl+C."}
        </p>
      </div>
      <p className={s.etiqueta} id="vista-numeros">
        Así llega a Excel
      </p>
      {/* La caja se puede enfocar para desplazarla con el teclado si no cabe a lo ancho. */}
      <div className={s.caja} role="region" aria-labelledby="vista-numeros" tabIndex={0}>
        <pre className={s.vistaNumeros} ref={vista}>
          {texto}
        </pre>
      </div>
    </div>
  );
}
