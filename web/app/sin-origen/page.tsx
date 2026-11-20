"use client";
import { textoDeError } from "@/lib/supabase";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Decidir, Nota, Rango, type Pedido } from "@/components/Decidir";
import { asignar, sinOrigen } from "@/lib/datos";
import { ayer, correrDias, fecha, pesos } from "@/lib/formato";

type Datos = Awaited<ReturnType<typeof sinOrigen>>;

export default function SinOrigen() {
  const [desde, setDesde] = useState(correrDias(ayer(), -6));
  const [hasta, setHasta] = useState(ayer());
  const [d, setD] = useState<Datos | null>(null);
  const [error, setError] = useState("");
  const [pedido, setPedido] = useState<Pedido | null>(null);

  async function ver() {
    setD(null); setError("");
    try { setD(await sinOrigen(desde, hasta)); } catch (e) { setError(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function abrir(p: Datos["pendientes"][number], sugerido?: string) {
    if (!d) return;
    setPedido({
      titulo: "Asignar el pago a un punto", texto: `${fecha(p.fecha)} · ${pesos(p.valor)} · ${p.descripcion}`, boton: "Asignar",
      etiquetaOpciones: "Punto", opcionInicial: sugerido ?? p.punto_id ?? "",
      opciones: [{ valor: "", texto: "— Sin punto —" }, ...d.puntos.map((x) => ({ valor: x.id, texto: x.nombre }))],
      hacer: (nota, punto) => asignar(p.id, punto || null, nota),
    });
  }

  return (
    <Programa>
      <section className="tarjeta">
        <div><h2>Pagos sin origen</h2><p className="pequeno">Pagos de clientes que llegaron al banco sin el código de un punto. Tino no adivina: muestra la posible pareja y una persona asigna el punto, con nota. Al asignar, esos días se revisan otra vez.</p></div>
        <Rango desde={desde} hasta={hasta} setDesde={setDesde} setHasta={setHasta} ver={ver} />
        {error && <Nota clase="mal" titulo="No se pudieron cargar.">{error}</Nota>}
        {!d && !error && <Cargando />}
        {d && d.senales.length > 0 && (
          <Nota clase="aviso" titulo="Revisar si cambiaron el QR de un punto">
            {d.senales.map((s, i) => <span key={i}>{s.punto} el {fecha(s.fecha)}: anotó {s.anotadas} transferencia(s) y ninguna llegó con su código.<br /></span>)}
          </Nota>
        )}
        {d && (!d.pendientes.length ? <p className="vacio">No hay pagos sin punto en esas fechas.</p> : (
          <div className="caja"><table>
            <thead><tr><th>Día</th><th>Descripción</th><th className="d">Valor</th><th>Posible punto</th><th></th></tr></thead>
            <tbody>{d.pendientes.map((p) => (
              <tr key={p.id}>
                <td>{fecha(p.fecha)}</td><td>{p.descripcion}<div className="pequeno">{p.etiqueta}</div></td><td className="d"><b>{pesos(p.valor)}</b></td>
                <td>{p.sugerencias.length ? p.sugerencias.map((s: { punto: string; fecha: string }, i: number) => <div key={i}><span className="chip c-rev">▲ {s.punto}</span> <span className="pequeno">no le llegó una igual el {fecha(s.fecha)}</span></div>) : <span className="pequeno">Ninguno</span>}</td>
                <td className="d"><button className="boton texto compacto" onClick={() => abrir(p, p.sugerencias.length === 1 ? p.sugerencias[0].punto_id : undefined)}>Asignar</button></td>
              </tr>))}</tbody>
            <tfoot><tr><td colSpan={2}>{d.pendientes.length} pago(s) sin punto</td><td className="d">{pesos(d.pendientes.reduce((a, p) => a + p.valor, 0))}</td><td colSpan={2}></td></tr></tfoot>
          </table></div>
        ))}
        {d && d.asignados.length > 0 && (
          <>
            <h3>Asignados a mano</h3>
            <div className="caja"><table>
              <thead><tr><th>Día</th><th>Descripción</th><th className="d">Valor</th><th>Punto</th><th>Nota</th><th></th></tr></thead>
              <tbody>{d.asignados.map((p) => (
                <tr key={p.id}><td>{fecha(p.fecha)}</td><td>{p.descripcion}</td><td className="d">{pesos(p.valor)}</td><td>{p.punto}</td><td className="pequeno">{p.nota}</td>
                  <td className="d"><button className="boton texto compacto" onClick={() => abrir(p)}>Cambiar</button></td></tr>))}</tbody>
            </table></div>
          </>
        )}
      </section>
      <Decidir pedido={pedido} cerrar={(hecho) => { setPedido(null); if (hecho) ver(); }} />
    </Programa>
  );
}
