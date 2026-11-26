"use client";
// Ajustes de Equipo: lo que cambia de un negocio a otro (DESIGN.md §15, REGLAS/equipo.md).
// Etapas del ciclo, temas, criterios de evaluación, tipos de observación e indicadores del
// registro del día; la plantilla sugerida (solo con el botón: nada se llena solo); umbrales de
// "quién necesita apoyo"; y las palabras de la pantalla con el nombre del programa (dueño y soporte).
import Link from "next/link";
import { useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Icono } from "@/components/Iconos";
import { base, leer, mensaje, textoDeError } from "@/lib/supabase";
import { TEXTOS_BASE } from "@/lib/textos";
import { indicadores as leerIndicadores, usarPlantilla, type Indicador } from "@/lib/formacion";

export default function PaginaAjustesEquipo() {
  return <Marco><Ajustes /></Marco>;
}

type Item = { id: string; clase: string; nombre: string; activo: boolean; orden: number };
const CLASES = [
  { clase: "etapa", titulo: "Etapas del ciclo de formación", ayuda: "Los pasos por los que va cada persona, en orden. El paso de cada una lo cambia alguien desde su ficha." },
  { clase: "tema", titulo: "Temas", ayuda: "De qué tratan las sesiones de formación." },
  { clase: "criterio", titulo: "Criterios de evaluación", ayuda: "Lo que se califica de 1 a 5 en una evaluación." },
  { clase: "tipo_observacion", titulo: "Tipos de observación", ayuda: "Lo que se elige al registrar una observación." },
];
const BASES: Record<Indicador["base"], string> = {
  atendidos: "% de los clientes atendidos", facturas: "% de las ventas (facturas)", conteo: "Solo se cuenta",
};
const UMBRALES = [
  { clave: "equipo_umbral_cumplimiento", titulo: "Cumplimiento mínimo de la meta", unidad: "%", ayuda: "Si va por debajo, sale en «necesita apoyo»." },
  { clave: "equipo_umbral_dias_sin_seguimiento", titulo: "Días sin seguimiento", unidad: "días", ayuda: "Si pasan más días sin ningún registro, sale en «necesita apoyo»." },
  { clave: "equipo_umbral_compromisos_vencidos", titulo: "Compromisos vencidos", unidad: "o más", ayuda: "Con esa cantidad de vencidos, sale en «necesita apoyo»." },
  { clave: "equipo_dias_proximos", titulo: "Ventana de próximos", unidad: "días", ayuda: "Hoy muestra los compromisos que vencen en estos días." },
];

function Ajustes() {
  const { yo, avisar, config } = useMarco();
  const t = config.textos;
  const puede = ["dueno", "encargada", "soporte", "lider"].includes(yo.rol);
  const [items, setItems] = useState<Item[] | null>(null);
  const [umbral, setUmbral] = useState<Record<string, string>>({});
  const [palabras, setPalabras] = useState<Record<string, string>>({});
  const [nuevo, setNuevo] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [recarga, setRecarga] = useState(0);
  const [inds, setInds] = useState<Indicador[]>([]);
  const [nuevoInd, setNuevoInd] = useState("");
  const [baseInd, setBaseInd] = useState<Indicador["base"]>("atendidos");
  const [usando, setUsando] = useState(false);
  const editaTextos = ["dueno", "soporte"].includes(yo.rol);

  useEffect(() => {
    Promise.all([
      leer<Item>("equipo_catalogo", "id,clase,nombre,activo,orden", [], "orden"),
      leer<Record<string, unknown>>("empresa_config", UMBRALES.map((u) => u.clave).join(",") + ",textos", [], "empresa_id"),
      leerIndicadores(true),
    ]).then(([cat, [c], ind]) => {
      setItems(cat);
      setInds(ind);
      setUmbral(Object.fromEntries(UMBRALES.map((u) => [u.clave, c?.[u.clave] == null ? "" : String(c[u.clave])])));
      setPalabras((c?.textos as Record<string, string>) ?? {});
    }).catch((e) => setError(textoDeError(e)));
  }, [recarga]);

  async function agregar(clase: string) {
    const nombre = (nuevo[clase] ?? "").trim();
    if (!nombre) return;
    const orden = Math.max(0, ...(items ?? []).filter((i) => i.clase === clase).map((i) => i.orden)) + 1;
    const { error: er } = await base().from("equipo_catalogo").insert({ empresa_id: yo.empresa_id, clase, nombre, orden });
    if (er) { avisar(er.code === "23505" ? "Ese nombre ya está." : mensaje(er)); return; }
    setNuevo((n) => ({ ...n, [clase]: "" })); avisar("Agregado"); setRecarga((r) => r + 1);
  }
  async function alternar(i: Item) {
    const { error: er } = await base().from("equipo_catalogo").update({ activo: !i.activo }).eq("id", i.id);
    if (er) { avisar(mensaje(er)); return; }
    avisar(i.activo ? "Desactivado: ya no sale para elegir" : "Activado"); setRecarga((r) => r + 1);
  }
  async function plantilla() {
    setUsando(true);
    try {
      const n = await usarPlantilla();
      avisar(n ? `Listo: ${n} agregados. Edítelos o desactive lo que no use.` : "Ya tenía todo lo de la plantilla: no se repitió nada.");
      setRecarga((r) => r + 1);
    } catch (e) { avisar(textoDeError(e)); } finally { setUsando(false); }
  }
  async function agregarIndicador(e: React.FormEvent) {
    e.preventDefault();
    const nombre = nuevoInd.trim();
    if (!nombre) return;
    const orden = Math.max(0, ...inds.map((i) => i.orden)) + 1;
    const { error: er } = await base().from("indicador_dia").insert({ empresa_id: yo.empresa_id, nombre, base: baseInd, orden });
    if (er) { avisar(er.code === "23505" ? "Ese indicador ya está." : mensaje(er)); return; }
    setNuevoInd(""); avisar("Indicador agregado"); setRecarga((r) => r + 1);
  }
  async function alternarIndicador(i: Indicador) {
    const { error: er } = await base().from("indicador_dia").update({ activo: !i.activo }).eq("id", i.id);
    if (er) { avisar(mensaje(er)); return; }
    avisar(i.activo ? "Desactivado: ya no sale en el registro del día" : "Activado"); setRecarga((r) => r + 1);
  }
  async function guardarUmbrales(e: React.FormEvent) {
    e.preventDefault();
    const p = Object.fromEntries(UMBRALES.map((u) => [u.clave, umbral[u.clave] === "" ? null : Number(umbral[u.clave])]));
    if (p.equipo_dias_proximos == null) p.equipo_dias_proximos = 7;
    const { error: er } = await base().rpc("guardar_config_equipo", { p });
    if (er) { avisar(er.code === "23514" ? "Algún valor está fuera de rango." : mensaje(er)); return; }
    avisar("Umbrales guardados. Se ven en Hoy al recargar.");
  }
  async function guardarPalabras(e: React.FormEvent) {
    e.preventDefault();
    const limpias = Object.fromEntries(Object.entries(palabras).filter(([, v]) => v && v.trim()).map(([k, v]) => [k, v.trim()]));
    const { error: er } = await base().from("empresa_config").update({ textos: limpias }).eq("empresa_id", yo.empresa_id);
    if (er) { avisar(mensaje(er)); return; }
    avisar("Palabras guardadas. Recargue para verlas.");
  }

  return (
    <>
      <header className="m-encabezado">
        <Link href="/equipo" className="m-volver" style={{ display: "inline-flex" }}><Icono id="izquierda" />{t.equipo}</Link>
        <h1>Ajustes de {t.equipo}</h1>
        <p className="m-contexto">Lo propio de su empresa. Nada se borra: lo que no use, desactívelo.</p>
      </header>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!items && !error && <div className="m-esqueleto" style={{ height: 200 }} />}
      {items && (
        <div className="m-ajustes">
          {puede && (
            <section className="m-grupo m-plantilla" aria-labelledby="t-plantilla">
              <h2 id="t-plantilla">Plantilla sugerida</h2>
              <p className="m-contexto">Llena de una vez las etapas del ciclo (Diagnóstico, Formación, Acompañamiento, Evaluación y Compromisos), los temas, los criterios de evaluación y los indicadores del registro del día (explicó el {t.programa}, consultó puntos antes de cobrar y referidos). No borra ni repite lo que ya tenga; después puede editar o desactivar cada cosa.</p>
              <button className="boton secundario" style={{ alignSelf: "flex-start" }} disabled={usando} onClick={plantilla}>
                {usando ? "Agregando…" : "Usar plantilla sugerida"}</button>
            </section>
          )}

          <section className="m-grupo" aria-labelledby="t-indicadores">
            <h2 id="t-indicadores">Indicadores del registro del día</h2>
            <p className="m-contexto">Lo que se cuenta al cerrar el día, además de los clientes atendidos (ese siempre está: es la base de la conversión).</p>
            {!inds.length && <p className="m-frase-nota">Todavía no hay ninguno.</p>}
            <ul className="m-lista">
              {inds.map((i) => (
                <li key={i.id} className="m-fila">
                  <span className="m-fila-texto"><b className={i.activo ? "" : "t-neu"}>{i.nombre}</b><span>{BASES[i.base]}{i.activo ? "" : " · Desactivado"}</span></span>
                  {puede && <button className="boton texto compacto" onClick={() => alternarIndicador(i)}>{i.activo ? "Desactivar" : "Activar"}</button>}
                </li>
              ))}
            </ul>
            {puede && (
              <form className="m-agregar m-agregar-indicador" onSubmit={agregarIndicador}>
                <input type="text" aria-label="Nuevo indicador" placeholder="Ej.: Ofreció el producto del mes" maxLength={80}
                  value={nuevoInd} onChange={(e) => setNuevoInd(e.target.value)} />
                <select aria-label="Cómo se mide" value={baseInd} onChange={(e) => setBaseInd(e.target.value as Indicador["base"])}>
                  {Object.entries(BASES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                </select>
                <button className="boton secundario compacto" type="submit"><Icono id="mas" />Agregar</button>
              </form>
            )}
            {puede && <p className="m-contexto">Cómo se mide no se cambia después: cambiaría el sentido de lo ya registrado. Si se equivocó, desactívelo y cree otro.</p>}
          </section>

          {CLASES.map((c) => {
            const lista = items.filter((i) => i.clase === c.clase);
            return (
              <section key={c.clase} className="m-grupo" aria-labelledby={"t-" + c.clase}>
                <h2 id={"t-" + c.clase}>{c.titulo}</h2>
                <p className="m-contexto">{c.ayuda}</p>
                {!lista.length && <p className="m-frase-nota">Todavía no hay ninguno.</p>}
                <ul className="m-lista">
                  {lista.map((i) => (
                    <li key={i.id} className="m-fila">
                      <span className="m-fila-texto"><b className={i.activo ? "" : "t-neu"}>{i.nombre}</b>{!i.activo && <span>Desactivado</span>}</span>
                      {puede && <button className="boton texto compacto" onClick={() => alternar(i)}>{i.activo ? "Desactivar" : "Activar"}</button>}
                    </li>
                  ))}
                </ul>
                {puede && (
                  <form className="m-agregar" onSubmit={(e) => { e.preventDefault(); agregar(c.clase); }}>
                    <input type="text" aria-label={`Nuevo: ${c.titulo}`} placeholder="Agregar…" maxLength={80}
                      value={nuevo[c.clase] ?? ""} onChange={(e) => setNuevo((n) => ({ ...n, [c.clase]: e.target.value }))} />
                    <button className="boton secundario compacto" type="submit"><Icono id="mas" />Agregar</button>
                  </form>
                )}
              </section>
            );
          })}

          <section className="m-grupo" aria-labelledby="t-umbrales">
            <h2 id="t-umbrales">Quién necesita apoyo</h2>
            <p className="m-contexto">Vacío = no se usa. Empiezan vacíos: póngalos cuando sepa qué es normal en su negocio.</p>
            <form className="m-form" onSubmit={guardarUmbrales}>
              {UMBRALES.map((u) => (
                <div key={u.clave} className="campo">
                  <label htmlFor={u.clave}>{u.titulo}</label>
                  <span className="m-con-unidad">
                    <input id={u.clave} type="number" inputMode="numeric" min={1} className="num" value={umbral[u.clave] ?? ""}
                      disabled={!puede} onChange={(e) => setUmbral((x) => ({ ...x, [u.clave]: e.target.value }))} />
                    <span>{u.unidad}</span>
                  </span>
                  <span className="m-contexto">{u.ayuda}</span>
                </div>
              ))}
              {puede && <button className="boton" type="submit">Guardar umbrales</button>}
            </form>
          </section>

          {editaTextos && (
            <section className="m-grupo" aria-labelledby="t-palabras">
              <h2 id="t-palabras">Palabras de la pantalla</h2>
              <p className="m-contexto">Si en su negocio no dicen «asesora» o «punto», cámbielas aquí.</p>
              <form className="m-form" onSubmit={guardarPalabras}>
                <div className="m-dos">
                  {(["persona", "personas", "punto", "puntos", "programa"] as const).map((k) => (
                    <div key={k} className="campo">
                      <label htmlFor={"p-" + k}>{k === "programa" ? "Nombre del programa de fidelización" : `En vez de «${TEXTOS_BASE[k]}»`}</label>
                      <input id={"p-" + k} type="text" maxLength={30} placeholder={TEXTOS_BASE[k]} value={palabras[k] ?? ""}
                        onChange={(e) => setPalabras((x) => ({ ...x, [k]: e.target.value }))} />
                    </div>
                  ))}
                </div>
                <button className="boton secundario" type="submit">Guardar palabras</button>
              </form>
            </section>
          )}
        </div>
      )}
    </>
  );
}
