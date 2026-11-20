"use client";
import { textoDeError } from "@/lib/supabase";
// Inicio: lo que necesita atención primero (DESIGN.md, principio 1).
import Link from "next/link";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Nota, Rango } from "@/components/Decidir";
import { resumen, revisarRango } from "@/lib/datos";
import { ayer, correrDias, fecha, pesos } from "@/lib/formato";

type Resumen = Awaited<ReturnType<typeof resumen>>;

export default function Inicio() {
  const [desde, setDesde] = useState(correrDias(ayer(), -6));
  const [hasta, setHasta] = useState(ayer());
  const [r, setR] = useState<Resumen | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");

  async function ver() {
    setR(null); setError("");
    try { setR(await resumen(desde, hasta)); } catch (e) { setError(textoDeError(e)); }
  }
  async function revisarDeNuevo() {
    setAviso("Revisando…");
    try { const n = await revisarRango(desde, hasta); setAviso(`Listo: se revisaron ${n} día(s) con Excel.`); ver(); }
    catch (e) { setAviso(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <Programa>
      <section className="tarjeta">
        <div className="encabezado">
          <div><h2>Lo que necesita atención</h2><p className="pequeno">Con lo que ya está subido. Los archivos se suben desde el programa de escritorio.</p></div>
          <button className="boton secundario compacto" onClick={revisarDeNuevo}>Revisar otra vez estos días</button>
        </div>
        <Rango desde={desde} hasta={hasta} setDesde={setDesde} setHasta={setHasta} ver={ver} />
        {aviso && <p className="pequeno" role="status">{aviso}</p>}
        {error && <Nota clase="mal" titulo="No se pudo cargar.">{error}</Nota>}
        {!r && !error && <Cargando />}
        {r && (
          <>
            <div className="cifras">
              <Link href="/descuadres" className={"tarjeta cifra" + (r.sinCausa.length ? " alerta" : "")} style={{ textDecoration: "none", color: "inherit" }}>
                <span className="etiqueta">Descuadres sin causa clara</span><span className="valor num">{r.sinCausa.length}</span>
                <span className="pequeno">{r.sinCausa.length ? pesos(r.sinCausa.reduce((a, d) => a + d.descuadre, 0)) + " en total" : "Ninguno"}</span></Link>
              <Link href="/transferencias" className={"tarjeta cifra" + (r.noLlegaron.length ? " alerta" : "")} style={{ textDecoration: "none", color: "inherit" }}>
                <span className="etiqueta">Transferencias que no llegaron</span><span className="valor num">{r.noLlegaron.length}</span>
                <span className="pequeno">{r.noLlegaron.length ? pesos(r.noLlegaron.reduce((a, t) => a + t.monto, 0)) + " en total" : "Ninguna"}</span></Link>
              <Link href="/sin-origen" className="tarjeta cifra" style={{ textDecoration: "none", color: "inherit" }}>
                <span className="etiqueta">Pagos sin punto</span><span className="valor num">{r.sinOrigen}</span><span className="pequeno">Por asignar</span></Link>
              <Link href="/por-confirmar" className="tarjeta cifra" style={{ textDecoration: "none", color: "inherit" }}>
                <span className="etiqueta">Por confirmar</span><span className="valor num">{r.porConfirmar}</span><span className="pequeno">Otro día o monto mal escrito</span></Link>
            </div>
            {r.sinCausa.length > 0 && (
              <div className="caja"><table>
                <thead><tr><th>Día</th><th>Punto</th><th className="d">Descuadre</th><th>Estado</th></tr></thead>
                <tbody>{r.sinCausa.map((d, i) => <tr key={i}><td>{fecha(d.fecha)}</td><td>{d.punto}</td><td className="d"><b>{pesos(d.descuadre)}</b></td><td><span className="chip c-mal">■ Sin causa clara</span></td></tr>)}</tbody>
              </table></div>
            )}
          </>
        )}
      </section>
    </Programa>
  );
}
