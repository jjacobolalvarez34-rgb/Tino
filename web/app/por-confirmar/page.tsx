"use client";
import { textoDeError } from "@/lib/supabase";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Decidir, Nota, type Pedido } from "@/components/Decidir";
import { decidirCruce, porConfirmar } from "@/lib/datos";
import { fecha, pesos } from "@/lib/formato";

const TIPO: Record<string, string> = { otro_dia: "Llegó otro día", mal_digitado: "Monto mal escrito", junto_con: "Cuadra junto con otra fecha", dia_tarde: "Llegó un día tarde", manual: "Manual" };
type Fila = Awaited<ReturnType<typeof porConfirmar>>[number];

export default function PorConfirmar() {
  const [filas, setFilas] = useState<Fila[] | null>(null);
  const [error, setError] = useState("");
  const [pedido, setPedido] = useState<Pedido | null>(null);

  async function ver() {
    setFilas(null); setError("");
    try { setFilas(await porConfirmar()); } catch (e) { setError(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []);

  return (
    <Programa>
      <section className="tarjeta">
        <div><h2>Por confirmar</h2><p className="pequeno">Parejas que Tino propone y no confirma solo. Una persona decide, con nota.</p></div>
        {error && <Nota clase="mal" titulo="No se pudo cargar.">{error}</Nota>}
        {!filas && !error && <Cargando />}
        {filas && (!filas.length ? <p className="vacio">No hay nada por confirmar.</p> : (
          <div className="caja"><table>
            <thead><tr><th>Qué pasó</th><th>Punto</th><th>Anotado</th><th>Lo que llegó</th><th></th></tr></thead>
            <tbody>{filas.map((c) => (
              <tr key={c.id}>
                <td><span className="chip c-rev">▲ {TIPO[c.tipo] ?? c.tipo}</span></td><td>{c.punto}</td>
                <td><b className="num">{pesos(c.monto_anotado)}</b><div className="pequeno">{fecha(c.fecha_anotada)} · {c.medio_tipo} · fila {c.fila_origen}</div></td>
                <td><b className="num">{pesos(c.monto_externo)}</b><div className="pequeno">{fecha(c.fecha_externa)} · {c.fuente}</div></td>
                <td className="d">
                  <button className="boton texto compacto" onClick={() => setPedido({ titulo: "Confirmar la pareja", texto: `Anotado ${pesos(c.monto_anotado)}; llegó ${pesos(c.monto_externo)}.`, boton: "Confirmar", hacer: (n) => decidirCruce(c.id, "confirmada", n) })}>Confirmar</button>
                  <button className="boton peligro-texto compacto" onClick={() => setPedido({ titulo: "No es la misma", texto: `Anotado ${pesos(c.monto_anotado)}; llegó ${pesos(c.monto_externo)}.`, boton: "Marcar \"No es\"", peligro: true, hacer: (n) => decidirCruce(c.id, "rechazada", n) })}>No es</button>
                </td>
              </tr>))}</tbody>
          </table></div>
        ))}
      </section>
      <Decidir pedido={pedido} cerrar={(hecho) => { setPedido(null); if (hecho) ver(); }} />
    </Programa>
  );
}
