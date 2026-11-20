"use client";
import { textoDeError } from "@/lib/supabase";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Decidir, Nota, Rango, type Pedido } from "@/components/Decidir";
import { cerrarDescuadre, descuadres, pruebas } from "@/lib/datos";
import { ayer, copiarComoNumeros, correrDias, fecha, pesos } from "@/lib/formato";

const MOTOR: Record<string, [string, string]> = { cuadra: ["c-ok", "● Cuadra"], explicado: ["c-rev", "▲ Explicado"], sin_explicar: ["c-mal", "■ Sin causa clara"] };
const TIPO_P: Record<string, string> = { causa: "Explica", senal: "Para revisar", pista: "Pista, no explica" };
type Fila = Awaited<ReturnType<typeof descuadres>>[number];

export default function Descuadres() {
  const [desde, setDesde] = useState(correrDias(ayer(), -6));
  const [hasta, setHasta] = useState(ayer());
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [abiertas, setAbiertas] = useState<Record<string, Awaited<ReturnType<typeof pruebas>> | null>>({});
  const [error, setError] = useState("");
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [aviso, setAviso] = useState("");

  async function ver() {
    setFilas(null); setError(""); setAbiertas({});
    try { setFilas(await descuadres(desde, hasta)); } catch (e) { setError(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function verPruebas(id: string) {
    if (id in abiertas) { const c = { ...abiertas }; delete c[id]; setAbiertas(c); return; }
    setAbiertas({ ...abiertas, [id]: null });
    const p = await pruebas(id);
    setAbiertas((a) => ({ ...a, [id]: p }));
  }

  const sinCausa = (filas ?? []).filter((d) => d.descuadre_estado === "abierto" && d.estado_motor === "sin_explicar");
  return (
    <Programa>
      <section className="tarjeta">
        <div className="encabezado">
          <div><h2>Descuadres</h2><p className="pequeno">Lo que faltó o sobró cada día, con la causa más probable. Si no hay causa, dice "Sin causa clara".</p></div>
          <button className="boton secundario compacto" onClick={async () => setAviso(await copiarComoNumeros([["Fecha", "Punto", "Descuadre", "Explicado", "Sin explicar", "Estado"], ...(filas ?? []).map((d) => [d.fecha, d.punto, d.descuadre, d.explicado, d.sin_explicar, d.estado_motor])]) ? "Copiado. Péguelo en Excel." : "No se pudo copiar.")}>Copiar como números</button>
        </div>
        <Rango desde={desde} hasta={hasta} setDesde={setDesde} setHasta={setHasta} ver={ver} />
        {aviso && <p className="pequeno" role="status">{aviso}</p>}
        {error && <Nota clase="mal" titulo="No se pudieron cargar.">{error}</Nota>}
        {!filas && !error && <Cargando />}
        {filas && (
          <>
            <div className="cifras">
              <div className={"tarjeta cifra" + (sinCausa.length ? " alerta" : "")}><span className="etiqueta">Sin causa clara, abiertos</span><span className="valor num">{sinCausa.length}</span><span className="pequeno">{sinCausa.length ? pesos(sinCausa.reduce((a, d) => a + d.descuadre, 0)) + " en total" : "Ninguno"}</span></div>
              <div className="tarjeta cifra"><span className="etiqueta">Días revisados</span><span className="valor num">{filas.length}</span><span className="pequeno">{filas.filter((d) => d.estado_motor === "cuadra").length} cuadran</span></div>
            </div>
            {!filas.length ? <p className="vacio">No hay días revisados en esas fechas.</p> : (
              <div className="caja"><table>
                <thead><tr><th>Día</th><th>Punto</th><th>Asesora</th><th className="d">Descuadre</th><th className="d">Explicado</th><th>Estado</th><th>Causa</th><th></th></tr></thead>
                <tbody>{filas.flatMap((d) => [
                  <tr key={d.descuadre_id}>
                    <td>{fecha(d.fecha)}</td><td>{d.punto}</td><td>{d.asesoras_texto}</td><td className="d"><b>{pesos(d.descuadre)}</b></td><td className="d">{pesos(d.explicado)}</td>
                    <td><span className={"chip " + (MOTOR[d.estado_motor]?.[0] ?? "c-neu")}>{MOTOR[d.estado_motor]?.[1]}</span>{d.descuadre_estado !== "abierto" && <div className="pequeno">Cerrado: {d.descuadre_estado}</div>}</td>
                    <td>{d.causa}</td>
                    <td className="d">
                      <button className="boton texto compacto" onClick={() => verPruebas(d.descuadre_id)}>Pruebas</button>
                      {d.descuadre_estado === "abierto" && d.estado_motor !== "cuadra" && <button className="boton texto compacto" onClick={() => setPedido({
                        titulo: "Cerrar el descuadre", texto: `${d.punto}, ${fecha(d.fecha)}: ${pesos(d.descuadre)}. No se borra: queda cerrado con su nota.`, boton: "Cerrar el descuadre",
                        etiquetaOpciones: "Cómo se cierra", opciones: [{ valor: "explicado", texto: "Explicado: se confirmó la causa" }, { valor: "resuelto", texto: "Resuelto: la plata apareció o se corrigió" }, { valor: "aceptado", texto: "Aceptado: se asume la diferencia" }],
                        hacer: (n, estado) => cerrarDescuadre(d.descuadre_id, estado as "explicado", n) })}>Cerrar</button>}
                    </td>
                  </tr>,
                  d.descuadre_id in abiertas && (
                    <tr key={d.descuadre_id + "-p"}><td colSpan={8}>
                      {abiertas[d.descuadre_id] === null ? <Cargando /> : !abiertas[d.descuadre_id]!.length ? <span className="pequeno">Sin pruebas: nada lo explica.</span> :
                        <ul className="pequeno">{abiertas[d.descuadre_id]!.map((x, i) => <li key={i}><b>{x.causa}</b> · {TIPO_P[x.tipo]}{x.tipo === "causa" ? ` · ${pesos(x.monto)}` : ""}</li>)}</ul>}
                    </td></tr>
                  ),
                ])}</tbody>
                <tfoot><tr><td colSpan={3}>Total</td><td className="d">{pesos(filas.reduce((a, d) => a + d.descuadre, 0))}</td><td className="d">{pesos(filas.reduce((a, d) => a + d.explicado, 0))}</td><td colSpan={3}></td></tr></tfoot>
              </table></div>
            )}
          </>
        )}
      </section>
      <Decidir pedido={pedido} cerrar={(hecho) => { setPedido(null); if (hecho) ver(); }} />
    </Programa>
  );
}
