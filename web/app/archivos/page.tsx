"use client";
import { useEffect, useState } from "react";
import { Programa, useYo } from "@/components/Programa";
import { SubirArchivos } from "@/components/SubirArchivos";
import { Cargando, Decidir, Nota, type Pedido } from "@/components/Decidir";
import { archivos, deshacer } from "@/lib/datos";
import { PorResolver } from "@/components/PorResolver";
import { fecha, fechaHora, miles } from "@/lib/formato";

const FUENTE: Record<string, string> = { excel_dia: "Excel del día", banco: "Extracto del banco", bold: "Reporte de Bold", redeban: "Reporte de Redeban", siigo: "Siigo", correo: "Correo" };
type Archivo = Awaited<ReturnType<typeof archivos>>[number];

export default function Archivos() {
  const [lista, setLista] = useState<Archivo[] | null>(null);
  const [aviso, setAviso] = useState("");
  const [recarga, setRecarga] = useState(0);
  const [error, setError] = useState("");
  const [pedido, setPedido] = useState<Pedido | null>(null);

  async function ver() {
    setLista(null); setError("");
    try { setLista((await archivos()).slice(0, 200)); setRecarga((r) => r + 1); }
    catch (e) { setError((e as Error).message); }
  }
  useEffect(() => { ver(); }, []);

  return (
    <Programa>
      <section className="tarjeta">
        <div><h2>Archivos</h2><p className="pequeno">Lo que se ha subido. Desde aquí se suben (quedan en cola para el programa de escritorio), se ven y se pueden deshacer.</p></div>
        <SubirDesdeAqui alCambiar={ver} />
        <PorResolver key={recarga} alCambiar={() => undefined} avisar={(t) => { setAviso(t); setTimeout(() => setAviso(""), 3000); }} />
        {aviso && <p className="nota ok" role="status"><span>{aviso}</span></p>}
        {error && <Nota clase="mal" titulo="No se pudo cargar el historial.">{error}</Nota>}
        {!lista && !error && <Cargando />}
        {lista && (!lista.length ? <p className="vacio">Todavía no hay archivos subidos.</p> : (
          <div className="caja"><table>
            <thead><tr><th>Archivo</th><th>Qué es</th><th>Días</th><th className="d">Filas</th><th>Estado</th><th></th></tr></thead>
            <tbody>{lista.map((a) => (
              <tr key={a.id}>
                <td>{a.nombre}<div className="pequeno">Subido {fechaHora(a.creado_en)}</div></td><td>{FUENTE[a.fuente] ?? a.fuente}</td>
                <td>{a.desde ? (a.desde === a.hasta ? fecha(a.desde) : `${fecha(a.desde)} a ${fecha(a.hasta)}`) : ""}</td>
                <td className="d">{miles(a.filas)}</td>
                <td>{a.estado === "cargado" ? <span className="chip c-ok">● Cargado</span> : <span className="chip c-neu">— Deshecho</span>}</td>
                <td className="d">{a.estado === "cargado" && <button className="boton peligro-texto compacto" onClick={() => setPedido({
                  titulo: "Deshacer este archivo", texto: `${a.nombre} deja de contar en todas las pantallas. No se borra: queda en el historial y se puede volver a subir corregido.`,
                  boton: "Deshacer el archivo", peligro: true, hacer: () => deshacer(a.id) })}>Deshacer</button>}</td>
              </tr>))}</tbody>
          </table></div>
        ))}
      </section>
      <Decidir pedido={pedido} cerrar={(hecho) => { setPedido(null); if (hecho) ver(); }} />
    </Programa>
  );
}

function SubirDesdeAqui({ alCambiar }: { alCambiar: () => void }) {
  const yo = useYo();
  if (!yo || !["dueno", "encargada", "finanzas", "soporte"].includes(yo.rol)) return null;
  return <SubirArchivos empresaId={yo.empresa_id} alCambiar={alCambiar} />;
}
