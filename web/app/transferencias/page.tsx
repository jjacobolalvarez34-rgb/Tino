"use client";
import { textoDeError } from "@/lib/supabase";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Decidir, Nota, Rango, type Pedido } from "@/components/Decidir";
import { decidirTransferencia, transferencias } from "@/lib/datos";
import { ayer, copiarComoNumeros, fecha, pesos } from "@/lib/formato";

const ESTADO: Record<string, [string, string]> = {
  confirmada: ["c-ok", "● Llegó"], propuesta: ["c-rev", "▲ Por confirmar"], sospechosa: ["c-mal", "■ No llegó"],
  pendiente: ["c-esp", "— Esperando banco"], rechazada: ["c-neu", "— No es"],
};
type Fila = Awaited<ReturnType<typeof transferencias>>[number];

export default function Transferencias() {
  const [desde, setDesde] = useState(ayer());
  const [hasta, setHasta] = useState(ayer());
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [error, setError] = useState("");
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [aviso, setAviso] = useState("");

  async function ver() {
    setFilas(null); setError("");
    try { setFilas(await transferencias(desde, hasta)); } catch (e) { setError(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const suma = (l: Fila[]) => l.reduce((a, t) => a + t.monto, 0);
  const sosp = (filas ?? []).filter((t) => t.estado === "sospechosa");

  return (
    <Programa>
      <section className="tarjeta">
        <div className="encabezado">
          <div><h2>Transferencias</h2><p className="pequeno">Cada transferencia anotada y si llegó al banco. Las que no llegaron van primero.</p></div>
          <button className="boton secundario compacto" onClick={async () => setAviso(await copiarComoNumeros([["Fecha", "Punto", "Monto", "Estado"], ...(filas ?? []).map((t) => [t.fecha, t.punto, t.monto, t.estado])]) ? "Copiado. Péguelo en Excel." : "No se pudo copiar.")}>Copiar como números</button>
        </div>
        <Rango desde={desde} hasta={hasta} setDesde={setDesde} setHasta={setHasta} ver={ver} />
        {aviso && <p className="pequeno" role="status">{aviso}</p>}
        {error && <Nota clase="mal" titulo="No se pudieron cargar las transferencias.">{error}</Nota>}
        {!filas && !error && <Cargando />}
        {filas && (
          <>
            <div className="cifras">
              <div className={"tarjeta cifra" + (sosp.length ? " alerta" : "")}><span className="etiqueta">No llegaron</span><span className="valor num">{sosp.length}</span><span className="pequeno">{sosp.length ? pesos(suma(sosp)) + " en total" : "Ninguna"}</span></div>
              <div className="tarjeta cifra"><span className="etiqueta">Llegaron</span><span className="valor num">{filas.filter((t) => t.estado === "confirmada").length}</span><span className="pequeno">de {filas.length} anotadas</span></div>
            </div>
            {!filas.length ? <p className="vacio">No hay transferencias anotadas en esas fechas.</p> : (
              <div className="caja"><table>
                <thead><tr><th>Día</th><th>Punto</th><th className="d">Monto</th><th>Estado</th><th>En el banco</th><th></th></tr></thead>
                <tbody>{filas.map((t) => (
                  <tr key={t.pago_id}>
                    <td>{fecha(t.fecha)}<div className="pequeno">fila {t.fila_origen}</div></td><td>{t.punto}</td><td className="d"><b>{pesos(t.monto)}</b></td>
                    <td><span className={"chip " + (ESTADO[t.estado]?.[0] ?? "c-neu")}>{ESTADO[t.estado]?.[1] ?? t.estado}</span></td>
                    <td>{t.fecha_banco ? <>{fecha(t.fecha_banco)}<div className="pequeno">ref {t.referencia}</div></> : <span className="pequeno">{t.nota}</span>}</td>
                    <td className="d">
                      {t.estado === "propuesta" && <button className="boton texto compacto" onClick={() => setPedido({ titulo: "Confirmar la transferencia", texto: `${t.punto}, ${fecha(t.fecha)}, ${pesos(t.monto)}.`, boton: "Confirmar", hacer: (n) => decidirTransferencia(t.pago_id, "confirmada", n) })}>Confirmar</button>}
                      {["sospechosa", "propuesta", "pendiente"].includes(t.estado) && <button className="boton peligro-texto compacto" onClick={() => setPedido({ titulo: "Marcar como \"No es\"", texto: `${t.punto}, ${fecha(t.fecha)}, ${pesos(t.monto)}. Queda como no recibida, con su nota.`, boton: "Marcar \"No es\"", peligro: true, hacer: (n) => decidirTransferencia(t.pago_id, "rechazada", n) })}>No es</button>}
                    </td>
                  </tr>))}</tbody>
                <tfoot><tr><td colSpan={2}>Total anotado</td><td className="d">{pesos(suma(filas))}</td><td colSpan={3}></td></tr></tfoot>
              </table></div>
            )}
          </>
        )}
      </section>
      <Decidir pedido={pedido} cerrar={(hecho) => { setPedido(null); if (hecho) ver(); }} />
    </Programa>
  );
}
