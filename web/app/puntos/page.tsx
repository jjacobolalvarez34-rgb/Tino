"use client";
import { textoDeError } from "@/lib/supabase";
import { useEffect, useState } from "react";
import { Programa } from "@/components/Programa";
import { Cargando, Nota } from "@/components/Decidir";
import { guardarPunto, listaPuntos } from "@/lib/datos";

const PROV: Record<string, string> = { bold: "Bold", redeban: "Redeban", otro: "Otro" };
type Punto = Awaited<ReturnType<typeof listaPuntos>>[number];

export default function Puntos() {
  const [lista, setLista] = useState<Punto[] | null>(null);
  const [error, setError] = useState("");
  const [nuevo, setNuevo] = useState({ codigo: "", nombre: "", tipo: "detal" });
  const [aviso, setAviso] = useState("");

  async function ver() {
    setLista(null); setError("");
    try { setLista(await listaPuntos()); } catch (e) { setError(textoDeError(e)); }
  }
  useEffect(() => { ver(); }, []);

  async function crear(e: React.FormEvent) {
    e.preventDefault(); setAviso("");
    try { await guardarPunto({ ...nuevo, activo: true }); setNuevo({ codigo: "", nombre: "", tipo: "detal" }); setAviso("Punto creado."); ver(); }
    catch (err) { setAviso(textoDeError(err)); }
  }
  async function activar(p: Punto) {
    try { await guardarPunto({ id: p.id, nombre: p.nombre, tipo: p.tipo, activo: !p.activo }); ver(); }
    catch (err) { setAviso(textoDeError(err)); }
  }

  return (
    <Programa>
      <section className="tarjeta">
        <div><h2>Puntos de venta</h2><p className="pequeno">Los puntos de la empresa. El código de pago, los datáfonos y los nombres en el Excel se ajustan desde el programa de escritorio (Ajustes).</p></div>
        <form className="filtros" onSubmit={crear}>
          <div className="campo"><label htmlFor="codigo">Código</label><input type="text" id="codigo" style={{ width: 110 }} value={nuevo.codigo} onChange={(e) => setNuevo({ ...nuevo, codigo: e.target.value })} /></div>
          <div className="campo"><label htmlFor="nombre">Nombre</label><input type="text" id="nombre" value={nuevo.nombre} onChange={(e) => setNuevo({ ...nuevo, nombre: e.target.value })} /></div>
          <div className="campo"><label htmlFor="tipo">Tipo</label><select id="tipo" value={nuevo.tipo} onChange={(e) => setNuevo({ ...nuevo, tipo: e.target.value })}><option value="detal">Detal</option><option value="mayorista">Mayorista</option></select></div>
          <button className="boton" type="submit">Agregar punto</button>
        </form>
        {aviso && <p className="pequeno" role="status">{aviso}</p>}
        {error && <Nota clase="mal" titulo="No se pudieron cargar los puntos.">{error}</Nota>}
        {!lista && !error && <Cargando />}
        {lista && (
          <div className="caja"><table>
            <thead><tr><th>Código</th><th>Punto</th><th>Código de pago</th><th>Datáfonos</th><th>Estado</th><th></th></tr></thead>
            <tbody>{lista.map((p) => (
              <tr key={p.id}>
                <td>{p.codigo}</td><td><b>{p.nombre}</b><div className="pequeno">{p.tipo === "mayorista" ? "Mayorista" : "Detal"}</div></td>
                <td className="num">{p.codigo_pago || <span className="chip c-rev">▲ Falta</span>}</td>
                <td className="pequeno">{p.datafonos.map((d: { id: string; proveedor: string; codigo_terminal: string }) => <div key={d.id}>{PROV[d.proveedor]}: {d.codigo_terminal}</div>)}</td>
                <td>{p.activo ? <span className="chip c-ok">● Activo</span> : <span className="chip c-neu">— Inactivo</span>}</td>
                <td className="d"><button className="boton texto compacto" onClick={() => activar(p)}>{p.activo ? "Desactivar" : "Activar"}</button></td>
              </tr>))}</tbody>
          </table></div>
        )}
      </section>
    </Programa>
  );
}
