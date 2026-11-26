"use client";
// Equipo abre con la formación (A5): lo que hay que hacer, cómo van los indicadores, en qué paso
// va cada persona, el calendario de la semana y al final la lista. Con ?p=<persona>, la ficha:
// en el computador, lista a la izquierda y ficha a la derecha; en el celular, la ficha sola.
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Avatar } from "@/components/Avatar";
import { AnilloMeta } from "@/components/AnilloMeta";
import { Icono } from "@/components/Iconos";
import { Tabla } from "@/components/Tabla";
import { yaLoVio } from "@/components/Recorrido";
import { Ayuda, AYUDA_TICKET } from "@/components/Ayuda";
import { puntos as leerPuntos } from "@/lib/datos";
import { base, mensaje, textoDeError } from "@/lib/supabase";
import { anterior, avanzarCompromiso, catalogo, compromisos, hoy, mesDe, metaDelPeriodo, metas, personas, seguimientos,
  ticket, totales, ultimaFecha, ventas, type Compromiso, type ItemCatalogo, type Meta, type Persona, type Seguimiento,
  type VentaDia } from "@/lib/equipo";
import { correrDias, diaBogota, fecha, miles, nombreMes, pesos } from "@/lib/formato";
import { cargarPendientes, Pendientes, type DatosPendientes } from "@/components/Pendientes";
import { CalendarioSemana, ComoVan, FranjaEtapas, type Periodo } from "@/components/Formacion";
import { cambiarPaso, etapas as leerEtapas, historiaPasos, indicadores as leerIndicadores, pasos as leerPasos,
  type Etapa, type HistoriaPaso, type Indicador, type Paso } from "@/lib/formacion";

export default function PaginaEquipo() {
  return <Marco><Suspense><Equipo /></Suspense></Marco>;
}

function Equipo() {
  const { config, version, yo, registrar, verRecorrido } = useMarco();
  const t = config.textos;
  const params = useSearchParams();
  const router = useRouter();
  const elegida = params.get("p");
  const [gente, setGente] = useState<Persona[] | null>(null);
  const [puntos, setPuntos] = useState<Record<string, string>>({});
  const [buscar, setBuscar] = useState("");
  const [inactivas, setInactivas] = useState(false);
  const [nueva, setNueva] = useState(false);
  const [error, setError] = useState("");
  const [recarga, setRecarga] = useState(0);
  const [form, setForm] = useState<{ pend: DatosPendientes; ind: Indicador[]; et: Etapa[]; pasos: Paso[] } | null>(null);
  const [periodo, setPeriodo] = useState<Periodo>("mes");
  const [punto, setPunto] = useState(yo.rol === "responsable_punto" && yo.punto_id ? yo.punto_id : "");
  const [revisado, setRevisado] = useState(false);

  useEffect(() => {
    Promise.all([personas(), leerPuntos()]).then(([g, p]) => { setGente(g); setPuntos(p); })
      .catch((e) => setError(textoDeError(e)));
  }, [version, recarga]);

  // La portada de Equipo es la formación (A5): lo que hay que hacer, cómo van, los pasos y el
  // calendario. Se carga solo cuando no hay una ficha abierta.
  useEffect(() => {
    if (elegida) return;
    Promise.all([cargarPendientes(), leerIndicadores(), leerEtapas(), leerPasos()])
      .then(([pend, ind, et, ps]) => setForm({ pend, ind, et, pasos: ps }))
      .catch((e) => setError(textoDeError(e)));
  }, [elegida, version, recarga]);

  // La primera vez, el recorrido de Equipo sale cuando la formación ya tiene datos (A8).
  useEffect(() => {
    if (!form || revisado || elegida) return;
    setRevisado(true);
    yaLoVio("equipo").then((visto) => { if (!visto) verRecorrido("equipo"); });
  }, [form, revisado, elegida, verRecorrido]);

  const visibles = useMemo(() => {
    const q = buscar.trim().toLowerCase();
    return (gente ?? []).filter((g) => (inactivas ? !g.activa : g.activa)
      && (!q || g.nombre.toLowerCase().includes(q) || g.codigo.toLowerCase().includes(q)
          || g.puntos.some((a) => (puntos[a.punto_id] ?? "").toLowerCase().includes(q))));
  }, [gente, buscar, inactivas, puntos]);
  const persona = gente?.find((g) => g.id === elegida) ?? null;
  const puedeEditar = ["dueno", "encargada", "soporte", "lider"].includes(yo.rol);
  const llenaRegistro = ["dueno", "lider", "responsable_punto"].includes(yo.rol);
  const pasoDe = new Map(form?.pasos.map((x) => [x.asesora_id, x.etapa_id]) ?? []);
  const nombreEtapa = new Map(form?.et.map((e) => [e.id, e.nombre]) ?? []);
  const hoyF = hoy();
  const enPunto = (g: Persona) => !punto || g.puntos.some((a) => a.punto_id === punto && (!a.hasta || a.hasta >= hoyF));

  const lista = (
    <>
      <div className="m-filtros">
        <input type="search" aria-label={`Buscar ${t.persona} o ${t.punto}`} placeholder={`Buscar ${t.persona} o ${t.punto}`}
          value={buscar} onChange={(e) => setBuscar(e.target.value)} />
        <div className="m-segmentos m-segmentos-chicos" role="group" aria-label="Mostrar">
          <button className="m-segmento" aria-pressed={!inactivas} onClick={() => setInactivas(false)}>Activas</button>
          <button className="m-segmento" aria-pressed={inactivas} onClick={() => setInactivas(true)}>Inactivas</button>
        </div>
      </div>
      {puedeEditar && (
        <div className="m-pie-acciones">
          <button className="boton secundario" onClick={() => setNueva(true)}><Icono id="mas" />Nueva {t.persona}</button>
          <Link href="/equipo/ajustes" className="boton texto"><Icono id="ajustes" />Ajustes</Link>
        </div>
      )}
      {nueva && <NuevaPersona alCerrar={() => setNueva(false)} alCrear={(id) => { setNueva(false); setRecarga((r) => r + 1); router.push(`/equipo?p=${id}`); }} />}
      {!gente && !error && [0, 1, 2, 3, 4].map((i) => <div key={i} className="m-esqueleto" style={{ height: 60 }} />)}
      {gente && !visibles.length && (
        <p className="m-vacio">{buscar ? "Nadie coincide con esa búsqueda." : inactivas ? `No hay ${t.personas} inactivas.` : `Todavía no hay ${t.personas}. Cree la primera.`}</p>
      )}
      <ul className="m-lista">
        {visibles.map((g) => {
          const etapa = pasoDe.get(g.id);
          return (
            <li key={g.id}>
              <Link href={`/equipo?p=${g.id}`} className="m-fila" aria-current={g.id === elegida ? "true" : undefined}>
                <Avatar id={g.id} nombre={g.nombre} />
                <span className="m-fila-texto">
                  <b>{g.nombre}</b>
                  <span>{g.puntos.length ? g.puntos.map((a) => puntos[a.punto_id]).filter(Boolean).join(" · ") : `Sin ${t.punto}`}
                    {etapa && nombreEtapa.get(etapa) ? ` · Paso: ${nombreEtapa.get(etapa)}` : ""}</span>
                </span>
                <Icono id="derecha" />
              </Link>
            </li>
          );
        })}
      </ul>
    </>
  );

  // Con una persona elegida: lista a la izquierda y ficha a la derecha (en el celular, la ficha).
  if (elegida) {
    return (
      <div className="m-lista-detalle con-detalle">
        <section className="m-ld-lista" aria-labelledby="t-equipo" data-recorrido="lista-equipo">
          <header className="m-encabezado">
            <Link href="/equipo" className="m-volver" style={{ display: "inline-flex" }}><Icono id="izquierda" />Formación</Link>
            <h1 id="t-equipo">{t.Personas}</h1>
          </header>
          {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
          {lista}
        </section>
        <section className="m-ld-detalle" aria-label={`Ficha de la ${t.persona}`}>
          {persona
            ? <Ficha key={persona.id} persona={persona} puntos={puntos} puedeEditar={puedeEditar} alCambiar={() => setRecarga((r) => r + 1)} />
            : gente && <p className="m-vacio">No se encontró esa {t.persona}. <Link className="m-enlace" href="/equipo">Volver</Link></p>}
        </section>
      </div>
    );
  }

  const activas = (gente ?? []).filter((g) => g.activa);
  return (
    <div className="m-formacion">
      <header className="m-encabezado">
        <h1 id="t-equipo">{t.equipo}</h1>
        <p className="m-contexto">Formación y desempeño{gente ? ` · ${activas.length} ${t.personas} activas` : ""}</p>
      </header>
      <div className="m-formacion-controles">
        <div className="m-segmentos m-segmentos-chicos" role="group" aria-label="Período">
          <button className="m-segmento" aria-pressed={periodo === "mes"} onClick={() => setPeriodo("mes")}>Este mes</button>
          <button className="m-segmento" aria-pressed={periodo === "semana"} onClick={() => setPeriodo("semana")}>Esta semana</button>
        </div>
        {yo.rol !== "responsable_punto" && Object.keys(puntos).length > 1 && (
          <select aria-label={`Ver un ${t.punto}`} value={punto} onChange={(e) => setPunto(e.target.value)}>
            <option value="">Todo el {t.equipo.toLowerCase()}</option>
            {Object.entries(puntos).map(([id, n]) => <option key={id} value={id}>{n}</option>)}
          </select>
        )}
        {llenaRegistro && <button className="boton" data-recorrido="formacion-registro" onClick={() => registrar(undefined, "registro")}><Icono id="dia" />Registro del día</button>}
        {puedeEditar && <Link href="/equipo/ajustes" className="boton texto"><Icono id="ajustes" />Ajustes</Link>}
      </div>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!form && !error && [0, 1, 2].map((i) => <div key={i} className="m-esqueleto" style={{ height: 120 }} />)}
      {form && gente && (<>
        <section className="m-grupo" aria-labelledby="t-hacer" data-recorrido="formacion-hacer">
          <h2 id="t-hacer">Lo que hay que hacer</h2>
          <Pendientes d={form.pend} conProximos={false} conAccion={false} />
        </section>
        <section className="m-grupo" aria-labelledby="t-como" data-recorrido="formacion-como">
          <h2 id="t-como">Cómo van</h2>
          <p className="m-contexto">{punto ? puntos[punto] : `Todo el ${t.equipo.toLowerCase()}`}, {periodo === "mes" ? "este mes" : "esta semana"}. La flecha dice si mejoró o empeoró.</p>
          {!form.ind.length && (
            <p className="m-frase-nota">Todavía no hay indicadores del registro del día (explicó el programa, consultó puntos, referidos). <Link className="m-enlace" href="/equipo/ajustes#t-indicadores">Ponerlos en Ajustes</Link></p>
          )}
          <ComoVan indicadores={form.ind} punto={punto || undefined} periodo={periodo} />
        </section>
        <section className="m-grupo" aria-labelledby="t-pasos" data-recorrido="formacion-pasos">
          <h2 id="t-pasos">En qué paso va cada {t.persona}</h2>
          <p className="m-contexto">El ciclo de formación. Toque una cara para ver su ficha y cambiarle el paso.</p>
          <FranjaEtapas etapas={form.et} pasos={form.pasos} gente={activas.filter(enPunto)} />
        </section>
        <section className="m-grupo" aria-labelledby="t-calendario" data-recorrido="formacion-calendario">
          <h2 id="t-calendario">Calendario de la semana</h2>
          <p className="m-contexto">Sesiones de formación y compromisos que vencen, de lunes a domingo.</p>
          <CalendarioSemana compromisos={form.pend.abiertos.filter((c) => !punto || c.punto_id === punto)} gente={gente} puntos={puntos} />
        </section>
      </>)}
      <section className="m-grupo" aria-labelledby="t-todas" data-recorrido="lista-equipo">
        <h2 id="t-todas">Todas las {t.personas}</h2>
        {lista}
      </section>
    </div>
  );
}

function NuevaPersona({ alCerrar, alCrear }: { alCerrar: () => void; alCrear: (id: string) => void }) {
  const { yo, config } = useMarco();
  const [nombre, setNombre] = useState("");
  const [error, setError] = useState("");
  async function crear(e: React.FormEvent) {
    e.preventDefault();
    if (nombre.trim().split(/\s+/).length < 2) { setError("Escriba nombre y apellido."); return; }
    const { data, error: er } = await base().from("asesora")
      .insert({ empresa_id: yo.empresa_id, nombre_completo: nombre.trim(), fecha_ingreso: hoy() }).select("id");
    if (er) { setError(mensaje(er)); return; }
    alCrear(data![0].id);
  }
  return (
    <form className="m-form m-tarjeta-suave" onSubmit={crear}>
      <div className="campo">
        <label htmlFor="n-nombre">Nombre completo</label>
        <input id="n-nombre" type="text" autoFocus value={nombre} onChange={(e) => setNombre(e.target.value)} maxLength={120} />
      </div>
      <p className="m-contexto">El código lo pone Tino. Después la asigna a sus {config.textos.puntos}.</p>
      {error && <p className="error-campo" role="alert">{error}</p>}
      <div className="m-pie-acciones">
        <button type="button" className="boton secundario" onClick={alCerrar}>Cancelar</button>
        <button type="submit" className="boton">Crear</button>
      </div>
    </form>
  );
}

type DatosFicha = {
  desde: string; hasta: string; venta: VentaDia[]; antes: VentaDia[]; metas: Meta[]; comps: Compromiso[];
  segs: Seguimiento[]; cat: ItemCatalogo[]; etapas: Etapa[]; historia: HistoriaPaso[]; indicadores: Indicador[];
};

const VALOR: Record<string, [string, string]> = { bien: ["● Bien", "c-ok"], a_mejorar: ["▲ A mejorar", "c-rev"], neutral: ["Neutral", "c-neu"] };
const ESTADO: Record<string, [string, string]> = {
  abierto: ["Abierto", "c-esp"], en_curso: ["En curso", "c-esp"], cumplido: ["● Cumplido", "c-ok"],
  no_cumplido: ["■ No cumplido", "c-mal"], anulado: ["Anulado", "c-neu"],
};
const TIPO_SEG: Record<string, [string, string]> = {
  // [nombre, ícono]
  observacion: ["Observación", "ojo"], objetivo: ["Objetivo", "diana"], diagnostico: ["Diagnóstico", "lapiz"], evaluacion: ["Evaluación", "chulo"],
};

function Ficha({ persona, puntos, puedeEditar, alCambiar }: {
  persona: Persona; puntos: Record<string, string>; puedeEditar: boolean; alCambiar: () => void;
}) {
  const { config, registrar, avisar, version, verRecorrido } = useMarco();
  const t = config.textos;
  const [mes, setMes] = useState<string | null>(null);
  const [revisado, setRevisado] = useState(false);
  const [d, setD] = useState<DatosFicha | null>(null);
  const [error, setError] = useState("");
  const [recarga, setRecarga] = useState(0);

  useEffect(() => {
    if (mes) return;
    ultimaFecha().then((u) => setMes(u && u < mesDe(hoy())[0] ? u.slice(0, 7) : hoy().slice(0, 7)))
      .catch(() => setMes(hoy().slice(0, 7)));
  }, [mes]);

  useEffect(() => {
    if (!mes) return;
    const [desde, finMes] = mesDe(mes + "-01");
    const hasta = finMes < hoy() ? finMes : hoy();
    const [ad, ah] = anterior(desde, hasta);
    setD(null);
    Promise.all([ventas(desde, hasta, persona.id), ventas(ad, ah, persona.id), metas(desde, hasta), compromisos(persona.id),
      seguimientos(correrDias(hoy(), -365), persona.id), catalogo(), leerEtapas(), historiaPasos(persona.id), leerIndicadores()])
      .then(([venta, antes, ms, comps, segs, cat, etapas, historia, indicadores]) =>
        setD({ desde, hasta, venta, antes, metas: ms, comps, segs, cat, etapas, historia, indicadores }))
      .catch((e) => setError(textoDeError(e)));
  }, [mes, persona.id, version, recarga]);

  // La primera vez, el recorrido de Equipo sale cuando la ficha ya tiene datos.
  useEffect(() => {
    if (!d || revisado) return;
    setRevisado(true);
    yaLoVio("equipo").then((visto) => { if (!visto) verRecorrido("equipo"); });
  }, [d, revisado, verRecorrido]);

  function moverMes(n: number) {
    if (!mes) return;
    const [a, m] = mes.split("-").map(Number);
    const f = new Date(Date.UTC(a, m - 1 + n, 1));
    setMes(f.toISOString().slice(0, 7));
  }

  async function cerrar(c: Compromiso, estado: "cumplido" | "no_cumplido") {
    try { await avanzarCompromiso(c.id, { estado }); avisar(estado === "cumplido" ? "Marcado como cumplido" : "Marcado como no cumplido"); setRecarga((r) => r + 1); }
    catch (e) { avisar(textoDeError(e)); }
  }
  async function avance(c: Compromiso, valor: number) {
    try { await avanzarCompromiso(c.id, { avance: valor, estado: valor > 0 ? "en_curso" : c.estado }); setRecarga((r) => r + 1); }
    catch (e) { avisar(textoDeError(e)); }
  }

  const tot = d ? totales(d.venta) : null;
  const antes = d ? totales(d.antes) : null;
  const cambio = tot && antes && antes.venta > 0 ? Math.round(((tot.venta - antes.venta) / antes.venta) * 100) : null;
  const meta = d ? metaDelPeriodo(d.metas, d.desde, d.hasta, (m) => m.asesora_id === persona.id) : 0;
  const nombreCat = new Map(d?.cat.map((c) => [c.id, c.nombre]) ?? []);
  const abiertos = d?.comps.filter((c) => c.estado === "abierto" || c.estado === "en_curso") ?? [];
  const mesTexto = mes ? nombreMes(mes) : "";
  const mesAntes = d ? nombreMes(anterior(d.desde, d.hasta)[1], false) : "";

  // Línea de tiempo: registros, compromisos y cambios de punto, lo más nuevo arriba.
  const linea = useMemo(() => {
    if (!d) return [];
    const items: { clave: string; fecha: string; icono: string; titulo: React.ReactNode; texto?: string; chip?: [string, string]; donde?: string }[] = [];
    for (const s of d.segs) {
      const [nom, ic] = TIPO_SEG[s.tipo];
      items.push({ clave: s.id, fecha: s.fecha, icono: ic,
        titulo: <>{nom}{s.tipo_observacion_id ? ` · ${nombreCat.get(s.tipo_observacion_id) ?? ""}` : ""}</>,
        texto: s.texto, chip: s.valoracion ? VALOR[s.valoracion] : undefined, donde: puntos[s.punto_id] });
    }
    for (const c of d.comps) {
      items.push({ clave: c.id + "a", fecha: diaBogota(c.creado_en), icono: "bandera", titulo: <>Compromiso: «{c.que}»</>,
        texto: `Para el ${fecha(c.fecha_limite)} · prioridad ${c.prioridad}`, chip: ESTADO[c.estado], donde: puntos[c.punto_id] });
      if (c.cerrado_en && c.estado !== "anulado")
        items.push({ clave: c.id + "b", fecha: diaBogota(c.cerrado_en), icono: c.estado === "cumplido" ? "chulo" : "bandera",
          titulo: <>{c.estado === "cumplido" ? "Cumplió" : "No cumplió"} «{c.que}»</> });
    }
    const etapa = new Map(d.etapas.map((e) => [e.id, e.nombre]));
    for (const h of d.historia)
      items.push({ clave: "e" + h.id, fecha: h.desde, icono: "sube", titulo: <>Pasó a «{etapa.get(h.etapa_id) ?? "otra etapa"}»</>,
        texto: h.nota ?? undefined });
    for (const a of persona.puntos)
      items.push({ clave: "p" + a.punto_id + a.desde, fecha: a.desde, icono: "tienda", titulo: <>Empezó en {puntos[a.punto_id] ?? `un ${t.punto}`}</> });
    return items.sort((x, y) => (x.fecha < y.fecha ? 1 : -1));
  }, [d, persona, puntos]); // eslint-disable-line react-hooks/exhaustive-deps

  const porPunto = useMemo(() => {
    if (!d) return [];
    const m = new Map<string, VentaDia[]>();
    for (const v of d.venta) m.set(v.punto_id, [...(m.get(v.punto_id) ?? []), v]);
    return [...m].map(([p, filas]) => ({ punto: p, ...totales(filas) }));
  }, [d]);

  return (
    <article className="m-ficha">
      <Link href="/equipo" className="m-volver m-solo-celular"><Icono id="izquierda" />{t.equipo}</Link>
      <header className="m-ficha-cabeza" data-recorrido="ficha-cabeza">
        <Avatar id={persona.id} nombre={persona.nombre} tamano={64} />
        <div className="m-ficha-nombre">
          <h2>{persona.nombre}</h2>
          <p className="m-contexto">{persona.codigo}{persona.activa ? "" : " · Inactiva"}</p>
        </div>
        <button className="boton" onClick={() => registrar(persona.id)}><Icono id="mas" />Registrar</button>
      </header>
      {puedeEditar && <EditarPersona persona={persona} alCambiar={alCambiar} />}

      <Puntos persona={persona} puntos={puntos} puedeEditar={puedeEditar} alCambiar={alCambiar} />

      {d && <PasoDelCiclo persona={persona} etapas={d.etapas} historia={d.historia} alCambiar={() => setRecarga((r) => r + 1)} />}
      {d && (
        <div className="m-grupo" data-recorrido="ficha-como-va">
          <h2>Cómo va este mes</h2>
          <ComoVan indicadores={d.indicadores} persona={persona.id} periodo="mes" />
        </div>
      )}

      <div className="m-periodo" role="group" aria-label="Período">
        <button className="m-icono-boton" onClick={() => moverMes(-1)} aria-label="Mes anterior"><Icono id="izquierda" /></button>
        <span className="m-periodo-texto">{mesTexto}</span>
        <button className="m-icono-boton" onClick={() => moverMes(1)} aria-label="Mes siguiente"
          disabled={!!mes && mes >= hoy().slice(0, 7)}><Icono id="derecha" /></button>
      </div>

      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!d && !error && <div className="m-esqueleto" style={{ height: 140 }} />}
      {d && tot && (<>
        <div className="m-cifras" data-recorrido="ficha-cifras">
          <div className="m-cifra">
            <span className="m-cifra-valor num">{pesos(tot.venta)}</span>
            <span className="m-cifra-contexto">
              {!tot.venta ? `Sin ventas a su nombre en ${mesTexto}` : cambio == null ? `Sin datos de ${mesAntes} para comparar · ${tot.dias} días` : (
                <><span className={cambio >= 0 ? "t-ok" : "t-mal"}><Icono id={cambio >= 0 ? "sube" : "baja"} />
                  {cambio >= 0 ? "+" : "−"}{Math.abs(cambio)} %</span> frente al mes anterior · {tot.dias} días</>
              )}
            </span>
          </div>
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{ticket(tot) ? pesos(ticket(tot)) : "—"}</span>
            <span className="m-cifra-contexto">ticket promedio{tot.facturas ? ` en ${miles(Math.round(tot.facturas))} facturas` : ""}<Ayuda texto={AYUDA_TICKET} /></span>
          </div>
          <div className="m-cifra m-cifra-anillo">
            <AnilloMeta valor={tot.venta} meta={meta || null} tamano={64} etiqueta="Meta personal" />
            <span className="m-cifra-contexto">
              {meta ? <>de su meta de <b className="num">{pesos(meta)}</b></> : <>Sin meta personal. <button className="m-enlace" onClick={() => registrar(persona.id, "meta")}>Poner meta</button></>}
            </span>
          </div>
        </div>

        {porPunto.length > 1 && (
          <Tabla titulo={`Venta por ${t.punto}`} avisar={avisar} clave={(f) => f.punto} filas={porPunto} columnas={[
            { clave: "punto", titulo: t.Punto, valor: (f) => puntos[f.punto] ?? "" },
            { clave: "dias", titulo: "Días", tipo: "numero", valor: (f) => f.dias, total: "suma" },
            { clave: "venta", titulo: "Venta", tipo: "pesos", valor: (f) => f.venta, total: "suma" },
            { clave: "ticket", titulo: "Ticket", tipo: "pesos", valor: (f) => ticket(f),
              total: (fs) => ticket(totales(d.venta)) ?? (fs.length ? null : null) },
          ]} />
        )}

        <div className="m-grupo" data-recorrido="ficha-compromisos">
          <h2>Compromisos abiertos{abiertos.length > 0 && <span className="m-cuenta num">{abiertos.length}</span>}</h2>
          {!abiertos.length ? (
            <p className="m-frase-nota">No tiene compromisos abiertos. <button className="m-enlace" onClick={() => registrar(persona.id, "compromiso")}>Registrar uno</button></p>
          ) : (
            <ul className="m-lista">
              {abiertos.map((c) => {
                const vencido = c.fecha_limite < hoy();
                return (
                  <li key={c.id} className="m-compromiso">
                    <div className="m-compromiso-texto">
                      <b>{c.que}</b>
                      <span className={vencido ? "t-mal" : ""}>{vencido ? "■ Venció el " : "Para el "}{fecha(c.fecha_limite)} · prioridad {c.prioridad}</span>
                      <span className="m-barra-dato" role="img" aria-label={`Avance ${c.avance} %`}><span style={{ width: `${c.avance}%` }} /></span>
                    </div>
                    <div className="m-compromiso-acciones">
                      <select aria-label="Avance" value={[0, 25, 50, 75].includes(c.avance) ? c.avance : ""} onChange={(e) => avance(c, Number(e.target.value))}>
                        {!([0, 25, 50, 75].includes(c.avance)) && <option value="">{c.avance} %</option>}
                        {[0, 25, 50, 75].map((n) => <option key={n} value={n}>{n} %</option>)}
                      </select>
                      <button className="boton secundario compacto" onClick={() => cerrar(c, "cumplido")}><Icono id="chulo" />Cumplido</button>
                      <button className="boton texto compacto" onClick={() => cerrar(c, "no_cumplido")}>No cumplió</button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="m-grupo" data-recorrido="ficha-linea">
          <h2>Línea de tiempo</h2>
          {!linea.length ? <p className="m-frase-nota">Todavía no hay registros. Lo que registre aparece aquí, lo más nuevo arriba.</p> : (
            <ol className="m-linea">
              {linea.map((x) => (
                <li key={x.clave}>
                  <span className="m-linea-icono" aria-hidden="true"><Icono id={x.icono} /></span>
                  <div className="m-linea-cuerpo">
                    <span className="m-linea-fecha">{fecha(x.fecha)}{x.donde ? ` · ${x.donde}` : ""}</span>
                    <b>{x.titulo}</b>
                    {x.texto && <p>{x.texto}</p>}
                    {x.chip && <span className={"chip " + x.chip[1]}>{x.chip[0]}</span>}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      </>)}
    </article>
  );
}

// El paso del ciclo de formación: lo cambia una persona (no es automático) y queda en la línea
// de tiempo. Lo cambian quienes ven el acompañamiento; el responsable, solo en su punto.
function PasoDelCiclo({ persona, etapas, historia, alCambiar }: {
  persona: Persona; etapas: Etapa[]; historia: HistoriaPaso[]; alCambiar: () => void;
}) {
  const { yo, avisar, config } = useMarco();
  const t = config.textos;
  const [abierto, setAbierto] = useState(false);
  const [etapa, setEtapa] = useState("");
  const [nota, setNota] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const actual = historia[0];
  const nombre = new Map(etapas.map((e) => [e.id, e.nombre]));
  const hoyF = hoy();
  const puede = ["dueno", "encargada", "soporte", "lider"].includes(yo.rol)
    || (yo.rol === "responsable_punto" && persona.puntos.some((a) => a.punto_id === yo.punto_id && (!a.hasta || a.hasta >= hoyF)));

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    if (!etapa) { avisar("Elija el paso."); return; }
    setOcupado(true);
    try {
      await cambiarPaso({ empresa_id: yo.empresa_id, asesora_id: persona.id, etapa_id: etapa, nota });
      avisar(`Ahora va en «${nombre.get(etapa)}»`); setAbierto(false); setNota(""); alCambiar();
    } catch (er) { avisar(textoDeError(er)); } finally { setOcupado(false); }
  }

  return (
    <div className="m-grupo" data-recorrido="ficha-paso">
      <h2>Paso del ciclo</h2>
      {!etapas.length ? (
        <p className="m-frase-nota">La empresa todavía no tiene las etapas del ciclo. <Link className="m-enlace" href="/equipo/ajustes#t-etapa">Ponerlas en Ajustes</Link></p>
      ) : (
        <>
          <ol className="m-pasos" aria-label="Etapas del ciclo">
            {etapas.map((x, i) => {
              const es = actual?.etapa_id === x.id;
              return <li key={x.id} className={es ? "m-paso-actual" : ""} aria-current={es ? "step" : undefined}><span className="num">{i + 1}</span>{x.nombre}</li>;
            })}
          </ol>
          <p className="m-contexto">{actual && nombre.has(actual.etapa_id)
            ? <>Va en <b>{nombre.get(actual.etapa_id)}</b> desde el {fecha(actual.desde)}.</>
            : `Todavía no tiene paso asignado.`}</p>
          {puede && !abierto && <button className="boton secundario compacto" style={{ alignSelf: "flex-start" }} onClick={() => { setEtapa(""); setAbierto(true); }}>Cambiar el paso</button>}
          {abierto && (
            <form className="m-form" onSubmit={guardar}>
              <fieldset className="m-opciones">
                <legend>¿En qué paso va {persona.nombre.split(" ")[0]}?</legend>
                {etapas.map((x) => (
                  <label key={x.id} className="m-opcion">
                    <input type="radio" name="etapa" checked={etapa === x.id} disabled={actual?.etapa_id === x.id}
                      onChange={() => setEtapa(x.id)} />{x.nombre}{actual?.etapa_id === x.id ? " (actual)" : ""}
                  </label>
                ))}
              </fieldset>
              <div className="campo">
                <label htmlFor="paso-nota">Nota (opcional)</label>
                <input id="paso-nota" type="text" maxLength={200} value={nota} onChange={(e) => setNota(e.target.value)}
                  placeholder={`Ej.: terminó la formación de venta consultiva`} />
              </div>
              <div className="m-pie-acciones">
                <button type="button" className="boton secundario" onClick={() => setAbierto(false)}>Cancelar</button>
                <button type="submit" className="boton" disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar el paso"}</button>
              </div>
              <p className="m-contexto">El cambio queda en la línea de tiempo de la {t.persona}; no se borra.</p>
            </form>
          )}
        </>
      )}
    </div>
  );
}

function Puntos({ persona, puntos, puedeEditar, alCambiar }: {
  persona: Persona; puntos: Record<string, string>; puedeEditar: boolean; alCambiar: () => void;
}) {
  const { yo, config, avisar } = useMarco();
  const t = config.textos;
  const [agregar, setAgregar] = useState("");
  const libres = Object.keys(puntos).filter((p) => !persona.puntos.some((a) => a.punto_id === p));

  async function asignar() {
    if (!agregar) return;
    const { error } = await base().from("asesora_punto").insert({ empresa_id: yo.empresa_id, asesora_id: persona.id, punto_id: agregar, desde: hoy() });
    if (error) { avisar(mensaje(error)); return; }
    setAgregar(""); avisar(`Asignada a ${puntos[agregar]}`); alCambiar();
  }
  async function sacar(punto: string) {
    const { error } = await base().from("asesora_punto").update({ hasta: hoy() })
      .eq("asesora_id", persona.id).eq("punto_id", punto).is("hasta", null);
    if (error) { avisar(mensaje(error)); return; }
    avisar(`Ya no está en ${puntos[punto]} desde hoy`); alCambiar();
  }

  return (
    <div className="m-puntos" data-recorrido="ficha-puntos">
      {persona.puntos.length === 0 && <span className="m-contexto">Sin {t.punto} asignado.</span>}
      {persona.puntos.map((a) => (
        <span key={a.punto_id} className="m-punto">
          <Icono id="tienda" />{puntos[a.punto_id] ?? t.Punto}<span className="m-punto-desde">desde {fecha(a.desde)}</span>
          {puedeEditar && <button className="m-icono-boton" onClick={() => sacar(a.punto_id)} aria-label={`Sacar de ${puntos[a.punto_id]}`}><Icono id="cerrar" /></button>}
        </span>
      ))}
      {puedeEditar && libres.length > 0 && (
        <span className="m-punto-agregar">
          <select aria-label={`Asignar a otro ${t.punto}`} value={agregar} onChange={(e) => setAgregar(e.target.value)}>
            <option value="">Asignar a otro {t.punto}…</option>
            {libres.map((p) => <option key={p} value={p}>{puntos[p]}</option>)}
          </select>
          {agregar && <button className="boton compacto" onClick={asignar}>Asignar</button>}
        </span>
      )}
    </div>
  );
}

function EditarPersona({ persona, alCambiar }: { persona: Persona; alCambiar: () => void }) {
  const { avisar, config } = useMarco();
  const [abierto, setAbierto] = useState(false);
  const [nombre, setNombre] = useState(persona.nombre);
  const [confirmar, setConfirmar] = useState(false);

  async function cambiar(valores: Record<string, unknown>, texto: string) {
    const { data, error } = await base().from("asesora").update(valores).eq("id", persona.id).select("id");
    if (error || !data?.length) { avisar(error ? mensaje(error) : "Su usuario no puede cambiarla."); return; }
    avisar(texto); setAbierto(false); setConfirmar(false); alCambiar();
  }

  return (
    <div className="m-editar">
      {!abierto && !confirmar && (
        <div className="m-compromiso-acciones">
          <button className="boton texto compacto" onClick={() => setAbierto(true)}><Icono id="lapiz" />Editar nombre</button>
          {persona.activa
            ? <button className="boton texto compacto" onClick={() => setConfirmar(true)}>Desactivar</button>
            : <button className="boton texto compacto" onClick={() => cambiar({ activa: true, fecha_retiro: null }, "Activa otra vez")}>Activar</button>}
        </div>
      )}
      {confirmar && (
        <div className="nota aviso" role="alert">
          <span className="cuerpo">
            <b>¿Desactivar a {persona.nombre}?</b>
            <span>Deja de salir en las listas y para registrar. Su historial se queda; puede activarla otra vez.</span>
            <span className="m-compromiso-acciones">
              <button className="boton compacto" onClick={() => cambiar({ activa: false, fecha_retiro: hoy() }, "Desactivada")}>Sí, desactivar</button>
              <button className="boton secundario compacto" onClick={() => setConfirmar(false)}>Cancelar</button>
            </span>
          </span>
        </div>
      )}
      {abierto && (
        <form className="m-agregar" onSubmit={(e) => { e.preventDefault();
          if (nombre.trim().split(/\s+/).length < 2) { avisar("Escriba nombre y apellido."); return; }
          cambiar({ nombre_completo: nombre.trim() }, "Nombre cambiado"); }}>
          <input type="text" aria-label={`Nombre de la ${config.textos.persona}`} value={nombre} autoFocus maxLength={120}
            onChange={(e) => setNombre(e.target.value)} />
          <button className="boton compacto" type="submit">Guardar</button>
          <button className="boton secundario compacto" type="button" onClick={() => { setAbierto(false); setNombre(persona.nombre); }}>Cancelar</button>
        </form>
      )}
    </div>
  );
}
