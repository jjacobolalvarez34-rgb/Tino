"use client";
// Toda decisión lleva nota: confirmar, "no es", asignar un punto o cerrar un descuadre.
import { useEffect, useRef, useState } from "react";

export type Pedido = {
  titulo: string;
  texto: string;
  boton: string;
  peligro?: boolean;
  opciones?: { valor: string; texto: string }[];
  opcionInicial?: string;
  etiquetaOpciones?: string;
  hacer: (nota: string, opcion: string) => Promise<void>;
};

export function Decidir({ pedido, cerrar }: { pedido: Pedido | null; cerrar: (hecho: boolean) => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  const [nota, setNota] = useState("");
  const [opcion, setOpcion] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);

  useEffect(() => {
    if (pedido) {
      setNota(""); setError(""); setOpcion(pedido.opcionInicial ?? pedido.opciones?.[0]?.valor ?? "");
      ref.current?.showModal();
    } else ref.current?.close();
  }, [pedido]);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    if (!pedido) return;
    if (!nota.trim()) { setError("Escriba una nota: queda en el historial con su nombre."); return; }
    setOcupado(true);
    try { await pedido.hacer(nota.trim(), opcion); cerrar(true); }
    catch (err) { setError((err as Error).message); }
    finally { setOcupado(false); }
  }

  return (
    <dialog ref={ref} onCancel={() => cerrar(false)} aria-labelledby="decidir-titulo">
      <form className="dentro" onSubmit={enviar}>
        <h2 id="decidir-titulo">{pedido?.titulo}</h2>
        <p className="pequeno">{pedido?.texto}</p>
        {pedido?.opciones && (
          <div className="campo"><label htmlFor="decidir-opcion">{pedido.etiquetaOpciones ?? "Opción"}</label>
            <select id="decidir-opcion" value={opcion} onChange={(e) => setOpcion(e.target.value)}>
              {pedido.opciones.map((o) => <option key={o.valor} value={o.valor}>{o.texto}</option>)}
            </select></div>
        )}
        <div className="campo"><label htmlFor="decidir-nota">Nota (obligatoria)</label>
          <textarea id="decidir-nota" value={nota} onChange={(e) => setNota(e.target.value)} /></div>
        <p className="error-campo" role="alert">{error}</p>
        <div className="acciones" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="boton secundario" onClick={() => cerrar(false)}>Cancelar</button>
          <button type="submit" className={"boton" + (pedido?.peligro ? " peligro" : "")} aria-disabled={ocupado}>{ocupado ? "Guardando…" : pedido?.boton}</button>
        </div>
      </form>
    </dialog>
  );
}

export function Cargando({ texto = "Cargando…" }: { texto?: string }) {
  return <p className="estado-carga"><svg className="icono girando" aria-hidden="true"><use href="#i-cargando" /></svg>{texto}</p>;
}

export function Nota({ clase, titulo, children }: { clase: "ok" | "mal" | "aviso" | "info"; titulo: string; children?: React.ReactNode }) {
  return (
    <div className={`nota ${clase}`}>
      <svg className="icono" aria-hidden="true"><use href={clase === "ok" ? "#i-ok" : "#i-alerta"} /></svg>
      <div className="cuerpo"><b>{titulo}</b>{children && <span>{children}</span>}</div>
    </div>
  );
}

export function Rango({ desde, hasta, setDesde, setHasta, ver, ocupado }: {
  desde: string; hasta: string; setDesde: (v: string) => void; setHasta: (v: string) => void; ver: () => void; ocupado?: boolean;
}) {
  return (
    <div className="filtros">
      <div className="campo"><label htmlFor="desde">Desde</label><input type="date" id="desde" value={desde} onChange={(e) => setDesde(e.target.value)} /></div>
      <div className="campo"><label htmlFor="hasta">Hasta</label><input type="date" id="hasta" value={hasta} onChange={(e) => setHasta(e.target.value)} /></div>
      <button className="boton" onClick={ver} aria-disabled={ocupado}>Ver</button>
    </div>
  );
}
