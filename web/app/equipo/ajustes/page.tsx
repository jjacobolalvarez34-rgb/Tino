"use client";
// Ajustes de Equipo: lo que cambia de un negocio a otro (DESIGN.md §15, REGLAS/equipo.md).
// Tipos de observación, temas y criterios de evaluación; umbrales de "quién necesita apoyo";
// y las palabras de la pantalla (solo el dueño).
import Link from "next/link";
import { useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Icono } from "@/components/Iconos";
import { base, leer, mensaje, textoDeError } from "@/lib/supabase";
import { TEXTOS_BASE } from "@/lib/textos";

export default function PaginaAjustesEquipo() {
  return <Marco><Ajustes /></Marco>;
}

type Item = { id: string; clase: string; nombre: string; activo: boolean; orden: number };
const CLASES = [
  { clase: "tipo_observacion", titulo: "Tipos de observación", ayuda: "Lo que se elige al registrar una observación." },
  { clase: "tema", titulo: "Temas", ayuda: "De qué tratan las sesiones de formación." },
  { clase: "criterio", titulo: "Criterios de evaluación", ayuda: "Lo que se califica de 1 a 5 en una evaluación." },
];
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

  useEffect(() => {
    Promise.all([
      leer<Item>("equipo_catalogo", "id,clase,nombre,activo,orden", [], "orden"),
      leer<Record<string, unknown>>("empresa_config", UMBRALES.map((u) => u.clave).join(",") + ",textos", [], "empresa_id"),
    ]).then(([cat, [c]]) => {
      setItems(cat);
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

          {yo.rol === "dueno" && (
            <section className="m-grupo" aria-labelledby="t-palabras">
              <h2 id="t-palabras">Palabras de la pantalla</h2>
              <p className="m-contexto">Si en su negocio no dicen «asesora» o «punto», cámbielas aquí.</p>
              <form className="m-form" onSubmit={guardarPalabras}>
                <div className="m-dos">
                  {(["persona", "personas", "punto", "puntos"] as const).map((k) => (
                    <div key={k} className="campo">
                      <label htmlFor={"p-" + k}>En vez de «{TEXTOS_BASE[k]}»</label>
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
