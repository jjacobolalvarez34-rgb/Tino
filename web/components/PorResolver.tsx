"use client";
// Lo que la importación no reconoció, agrupado (un mismo nombre en varios archivos sale una
// vez) y resuelto en un toque: el nombre se asigna a una persona de ese punto, el producto a un
// producto, y lo que no es ninguno se descarta con nota. Al asignar, la base crea el alias y
// reprocesa las filas (0012): la venta sin persona baja en esa cantidad.
import { useEffect, useMemo, useState } from "react";
import { base, leer, mensaje, textoDeError } from "@/lib/supabase";
import { puntos as leerPuntos } from "@/lib/datos";
import { pesos } from "@/lib/formato";
import { Icono } from "./Iconos";

type Pendiente = { id: string; tipo: string; texto: string; archivo_id: string; fila_origen: number | null };
type Grupo = { clave: string; tipo: string; texto: string; punto: string | null; ids: string[]; veces: number; venta: number };

const norm = (t: string) => t.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9%$]+/g, " ").trim();
const sinHoja = (t: string) => t.replace(/\s*\([^)]*\)\s*$/, "");
const TIPO: Record<string, string> = {
  nombre_sin_reconocer: "Nombre", producto_sin_reconocer: "Producto", archivo_inconsistente: "Problema del archivo",
  datafono_sin_punto: "Datáfono", fila_ilegible: "Fila", otro: "Otro",
};

export function PorResolver({ alCambiar, avisar }: { alCambiar: () => void; avisar: (t: string) => void }) {
  const [grupos, setGrupos] = useState<Grupo[] | null>(null);
  const [puntos, setPuntos] = useState<Record<string, string>>({});
  const [gente, setGente] = useState<{ id: string; nombre: string; puntos: string[] }[]>([]);
  const [productos, setProductos] = useState<{ id: string; nombre: string }[]>([]);
  const [eleccion, setEleccion] = useState<Record<string, string>>({});
  const [nota, setNota] = useState<Record<string, string>>({});
  const [descartando, setDescartando] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const errores = await leer<Pendiente>("error_importacion", "id,tipo,texto,archivo_id,fila_origen", [["resuelto", "eq", "false"]], "creado_en");
        const archivosIds = [...new Set(errores.map((e) => e.archivo_id))];
        // De qué punto es cada archivo: por su venta por persona o por su caja del día.
        const [vpa, rep, sinPersona, pts, ases, asig, prods] = await Promise.all([
          archivosIds.length ? base().from("venta_asesora_dia").select("archivo_id,punto_id").in("archivo_id", archivosIds).then((r) => r.data ?? []) : [],
          archivosIds.length ? base().from("reporte_caja").select("archivo_id,jornada_id").in("archivo_id", archivosIds).then((r) => r.data ?? []) : [],
          leer<{ punto_id: string; texto_original: string; venta: number }>("v_venta_asesora", "punto_id,texto_original,venta", [["asesora_id", "is", null]], "fecha"),
          leerPuntos(),
          leer<{ id: string; nombre_completo: string; activa: boolean }>("asesora", "id,nombre_completo,activa", [], "nombre_completo"),
          leer<{ asesora_id: string; punto_id: string }>("asesora_punto", "asesora_id,punto_id", [["hasta", "is", null]], "desde"),
          leer<{ id: string; nombre: string }>("producto", "id,nombre", [["activo", "eq", "true"]], "nombre"),
        ]);
        const jornadas = rep.length ? (await base().from("jornada").select("id,punto_id").in("id", [...new Set(rep.map((r) => r.jornada_id))])).data ?? [] : [];
        const puntoJornada = new Map(jornadas.map((j) => [j.id, j.punto_id]));
        const puntoArchivo = new Map<string, string>();
        for (const v of vpa) puntoArchivo.set(v.archivo_id, v.punto_id);
        for (const r of rep) if (!puntoArchivo.has(r.archivo_id) && puntoJornada.get(r.jornada_id)) puntoArchivo.set(r.archivo_id, puntoJornada.get(r.jornada_id)!);

        const mapa = new Map<string, Grupo>();
        for (const e of errores) {
          const texto = sinHoja(e.texto);
          const punto = e.tipo === "nombre_sin_reconocer" ? puntoArchivo.get(e.archivo_id) ?? null : null;
          const clave = e.tipo === "archivo_inconsistente" ? e.id : `${e.tipo}|${norm(texto)}|${punto ?? ""}`;
          const g = mapa.get(clave) ?? { clave, tipo: e.tipo, texto, punto, ids: [], veces: 0, venta: 0 };
          g.ids.push(e.id); g.veces += 1;
          mapa.set(clave, g);
        }
        for (const g of mapa.values()) {
          if (g.tipo === "nombre_sin_reconocer")
            g.venta = sinPersona.filter((v) => v.punto_id === g.punto && norm(v.texto_original) === norm(g.texto)).reduce((s, v) => s + v.venta, 0);
        }
        const orden: Record<string, number> = { nombre_sin_reconocer: 0, archivo_inconsistente: 1, producto_sin_reconocer: 2 };
        setGrupos([...mapa.values()].sort((a, b) => (orden[a.tipo] ?? 9) - (orden[b.tipo] ?? 9) || b.venta - a.venta || a.texto.localeCompare(b.texto, "es")));
        setPuntos(pts);
        setGente(ases.filter((a) => a.activa).map((a) => ({ id: a.id, nombre: a.nombre_completo, puntos: asig.filter((x) => x.asesora_id === a.id).map((x) => x.punto_id) })));
        setProductos(prods);
      } catch (e) {
        setError(textoDeError(e));
      }
    })();
  }, [recarga]);

  async function hacer(g: Grupo, accion: () => PromiseLike<{ data: unknown; error: { code?: string; message?: string } | null }>, ok: (n: number) => string) {
    setOcupado(g.clave);
    const { data, error: er } = await accion();
    setOcupado(null);
    if (er) { avisar(er.code === "23505" ? (er.message ?? "Ya estaba asignado a otro.") : mensaje(er)); return; }
    avisar(ok(Number(data) || 0)); setDescartando(null); setRecarga((r) => r + 1); alCambiar();
  }

  const opcionesPersona = useMemo(() => (punto: string | null) => {
    const delPunto = gente.filter((p) => punto && p.puntos.includes(punto));
    const otras = gente.filter((p) => !punto || !p.puntos.includes(punto));
    return { delPunto, otras };
  }, [gente]);

  if (error) return <div className="nota mal"><b>No se pudo cargar lo pendiente.</b> {error}</div>;
  if (!grupos) return <p className="estado-carga"><Icono id="cargando" girando />Buscando lo que falta por resolver…</p>;
  if (!grupos.length) return <div className="nota ok"><span>● No hay nombres ni productos por resolver.</span></div>;

  return (
    <section id="por-resolver" className="m-resolver" aria-labelledby="t-resolver">
      <div><h3 id="t-resolver">Por resolver ({grupos.length})</h3>
        <p className="pequeno">Tino no adivina. Asigne cada uno una vez: queda aprendido para los próximos archivos y las filas ya cargadas se corrigen solas.</p></div>
      <ul className="m-lista">
        {grupos.map((g) => (
          <li key={g.clave} className="m-resolver-fila">
            <div className="m-resolver-texto">
              <span className={"chip " + (g.tipo === "archivo_inconsistente" ? "c-mal" : g.tipo === "nombre_sin_reconocer" ? "c-rev" : "c-esp")}>
                {g.tipo === "archivo_inconsistente" ? "■ " : g.tipo === "nombre_sin_reconocer" ? "▲ " : ""}{TIPO[g.tipo] ?? g.tipo}
              </span>
              <b>{g.tipo === "archivo_inconsistente" ? g.texto : `«${g.texto}»`}</b>
              <span className="pequeno">
                {g.punto ? `${puntos[g.punto] ?? "Punto"} · ` : ""}{g.veces > 1 ? `aparece ${g.veces} veces` : "aparece una vez"}
                {g.venta > 0 ? ` · ${pesos(g.venta)} de venta sin persona` : ""}
              </span>
            </div>
            <div className="m-resolver-acciones">
              {g.tipo === "nombre_sin_reconocer" && g.punto && (() => {
                const { delPunto, otras } = opcionesPersona(g.punto);
                return <>
                  <select aria-label={`Quién es «${g.texto}»`} value={eleccion[g.clave] ?? ""} onChange={(e) => setEleccion((x) => ({ ...x, [g.clave]: e.target.value }))}>
                    <option value="">¿Quién es?</option>
                    {delPunto.length > 0 && <optgroup label={`En ${puntos[g.punto] ?? "este punto"}`}>{delPunto.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</optgroup>}
                    <optgroup label="Otras personas">{otras.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}</optgroup>
                  </select>
                  <button className="boton compacto" disabled={!eleccion[g.clave] || ocupado === g.clave}
                    onClick={() => hacer(g, () => base().rpc("resolver_nombre", { p_texto: g.texto, p_punto: g.punto, p_asesora: eleccion[g.clave] }),
                      (n) => `Asignado. ${n} día(s) de venta pasaron a esa persona.`)}>{ocupado === g.clave ? "Guardando…" : "Asignar"}</button>
                </>;
              })()}
              {g.tipo === "producto_sin_reconocer" && <>
                <select aria-label={`Qué producto es «${g.texto}»`} value={eleccion[g.clave] ?? ""} onChange={(e) => setEleccion((x) => ({ ...x, [g.clave]: e.target.value }))}>
                  <option value="">¿Qué producto es?</option>
                  {productos.map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
                </select>
                <button className="boton compacto" disabled={!eleccion[g.clave] || ocupado === g.clave}
                  onClick={() => hacer(g, () => base().rpc("resolver_producto", { p_texto: g.texto, p_producto: eleccion[g.clave] }),
                    (n) => `Asignado. ${n} fila(s) quedaron con ese producto.`)}>{ocupado === g.clave ? "Guardando…" : "Asignar"}</button>
              </>}
              {descartando === g.clave ? (
                <form className="m-agregar" onSubmit={(e) => { e.preventDefault();
                  hacer(g, () => base().rpc("descartar_error", { p_error: g.ids[0], p_nota: nota[g.clave] ?? "" }), () => "Listo, quedó con su nota."); }}>
                  <input type="text" autoFocus placeholder={g.tipo === "archivo_inconsistente" ? "Ej.: revisado con el punto" : "Ej.: el punto no abrió"}
                    aria-label="Por qué" value={nota[g.clave] ?? ""} onChange={(e) => setNota((x) => ({ ...x, [g.clave]: e.target.value }))} />
                  <button className="boton secundario compacto" type="submit">Guardar</button>
                </form>
              ) : (
                <button className="boton texto compacto" onClick={() => setDescartando(g.clave)}>
                  {g.tipo === "archivo_inconsistente" ? "Ya lo revisé" : g.tipo === "nombre_sin_reconocer" ? "No es una persona" : "No es un producto"}
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
