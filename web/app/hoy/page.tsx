"use client";
// Hoy: frases que se tocan, ordenadas por urgencia (compromisos vencidos, quién necesita
// apoyo, lo que viene, las sesiones de la semana). Al lado, el resumen del período.
import Link from "next/link";
import { useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Avatar } from "@/components/Avatar";
import { AnilloMeta } from "@/components/AnilloMeta";
import { Icono } from "@/components/Iconos";
import { yaLoVio } from "@/components/Recorrido";
import { puntos as leerPuntos } from "@/lib/datos";
import { anterior, compromisos, correrDiasHoy, diasEntre, hoy, mesDe, metaDelPeriodo, metas, personas, porPersona,
  seguimientos, sesiones, ticket, totales, ultimaFecha, ventas,
  type Compromiso, type Meta, type Persona, type Sesion, type Seguimiento, type VentaDia } from "@/lib/equipo";
import { fecha, miles, pesos } from "@/lib/formato";

export default function PaginaHoy() {
  return <Marco><Hoy /></Marco>;
}

type Datos = {
  gente: Persona[]; puntos: Record<string, string>; desde: string; hasta: string; ultima: string | null;
  venta: VentaDia[]; ventaAntes: VentaDia[]; metas: Meta[]; abiertos: Compromiso[]; segs: Seguimiento[]; sesiones: Sesion[];
};

const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
const nombreMes = (f: string) => MESES[Number(f.slice(5, 7)) - 1];
const primerNombre = (n: string) => n.trim().split(/\s+/)[0];

function lunes(f: string) {
  const d = new Date(f + "T00:00:00Z");
  const dia = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dia);
  return d.toISOString().slice(0, 10);
}

function Hoy() {
  const { yo, config, version, verRecorrido } = useMarco();
  const t = config.textos;
  const [d, setD] = useState<Datos | null>(null);
  const [revisado, setRevisado] = useState(false);

  // La primera vez que alguien entra, el recorrido sale solo cuando Hoy ya tiene datos.
  useEffect(() => {
    if (!d || revisado) return;
    setRevisado(true);
    yaLoVio().then((visto) => { if (!visto) verRecorrido(); });
  }, [d, revisado, verRecorrido]);
  const [error, setError] = useState("");

  useEffect(() => {
    (async () => {
      try {
        const [gente, pts, ultima, abiertos, segs] = await Promise.all([
          personas(), leerPuntos(), ultimaFecha(), compromisos(), seguimientos(correrDiasHoy(-120)),
        ]);
        // El mes actual, o el último con ventas si el actual todavía no trae datos.
        const ref = ultima && ultima < mesDe(hoy())[0] ? ultima : hoy();
        const [desde, finMes] = mesDe(ref);
        // Un mes en curso se compara con el mismo número de días del período anterior.
        const hasta = finMes < hoy() ? finMes : hoy();
        const [ad, ah] = anterior(desde, hasta);
        const lun = lunes(hoy());
        const [venta, ventaAntes, ms, ses] = await Promise.all([
          ventas(desde, hasta), ventas(ad, ah), metas(desde, hasta), sesiones(lun, correrDiasHoy(6 - diasEntre(lun, hoy()))),
        ]);
        setD({ gente, puntos: pts, desde, hasta, ultima, venta, ventaAntes, metas: ms, abiertos, segs, sesiones: ses });
      } catch (e) {
        setError((e as Error).message);
      }
    })();
  }, [version]);

  const hoyF = hoy();
  return (
    <>
      <header className="m-encabezado">
        <h1>Hoy</h1>
        <p className="m-contexto">{fecha(hoyF)} · {yo.empresa}</p>
      </header>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!d && !error && <Esqueleto />}
      {d && (
        <div className="m-hoy">
          <Frases d={d} hoyF={hoyF} />
          <Resumen d={d} textos={t} />
        </div>
      )}
    </>
  );
}

function Esqueleto() {
  return (
    <div className="m-hoy" aria-busy="true" aria-label="Cargando">
      <div className="m-columna">{[0, 1, 2, 3].map((i) => <div key={i} className="m-esqueleto" style={{ height: 64 }} />)}</div>
      <div className="m-columna"><div className="m-esqueleto" style={{ height: 96 }} /><div className="m-esqueleto" style={{ height: 220 }} /></div>
    </div>
  );
}

type Frase = { clave: string; tono: "mal" | "rev" | "ok" | "neu"; icono: string; texto: React.ReactNode; detalle: string; ir?: string };

function Frases({ d, hoyF }: { d: Datos; hoyF: string }) {
  const { config, registrar } = useMarco();
  const t = config.textos;
  const quien = new Map(d.gente.map((g) => [g.id, g]));
  const nombre = (id: string) => quien.get(id)?.nombre ?? `una ${t.persona}`;

  const vencidos = d.abiertos.filter((c) => c.fecha_limite < hoyF);
  const limiteProx = correrDiasHoy(config.dias_proximos);
  const proximos = d.abiertos.filter((c) => c.fecha_limite >= hoyF && c.fecha_limite <= limiteProx);

  // Quién necesita apoyo: solo con los umbrales que la empresa haya puesto.
  const venta = porPersona(d.venta);
  const ultimoSeg = new Map<string, string>();
  for (const s of d.segs) if (!ultimoSeg.has(s.asesora_id)) ultimoSeg.set(s.asesora_id, s.fecha);
  const hayUmbrales = config.umbral_cumplimiento != null || config.umbral_dias_sin_seguimiento != null
    || config.umbral_compromisos_vencidos != null;
  const apoyo: { id: string; razones: string[] }[] = [];
  if (hayUmbrales) {
    for (const g of d.gente.filter((x) => x.activa && x.puntos.length)) {
      const razones: string[] = [];
      const meta = metaDelPeriodo(d.metas, d.desde, d.hasta, (m) => m.asesora_id === g.id);
      if (config.umbral_cumplimiento != null && meta > 0) {
        const pct = Math.round(((venta.get(g.id)?.venta ?? 0) / meta) * 100);
        if (pct < config.umbral_cumplimiento) razones.push(`va en ${pct} % de su meta`);
      }
      if (config.umbral_dias_sin_seguimiento != null) {
        const u = ultimoSeg.get(g.id);
        const dias = u ? diasEntre(u, hoyF) : null;
        if (dias == null || dias > config.umbral_dias_sin_seguimiento)
          razones.push(dias == null ? "no tiene seguimiento reciente" : `lleva ${dias} días sin seguimiento`);
      }
      const venc = vencidos.filter((c) => c.asesora_id === g.id).length;
      if (config.umbral_compromisos_vencidos != null && venc >= config.umbral_compromisos_vencidos)
        razones.push(`${venc} compromiso${venc === 1 ? "" : "s"} vencido${venc === 1 ? "" : "s"}`);
      if (razones.length) apoyo.push({ id: g.id, razones });
    }
  }

  const frases: { titulo: string; filas: Frase[]; vacio?: React.ReactNode }[] = [
    {
      titulo: "Compromisos vencidos",
      filas: vencidos.map((c) => {
        const dias = diasEntre(c.fecha_limite, hoyF);
        return {
          clave: c.id, tono: "mal", icono: "bandera", ir: `/equipo?p=${c.asesora_id}`,
          texto: <><b>{primerNombre(nombre(c.asesora_id))}</b> tenía que «{c.que}»</>,
          detalle: `Venció hace ${dias} día${dias === 1 ? "" : "s"} · ${d.puntos[c.punto_id] ?? ""} · avance ${c.avance} %`,
        };
      }),
    },
    {
      titulo: `${t.Personas} que necesitan apoyo`,
      filas: apoyo.map((a) => ({
        clave: a.id, tono: "rev", icono: "salvavidas", ir: `/equipo?p=${a.id}`,
        texto: <><b>{nombre(a.id)}</b> {a.razones[0]}</>,
        detalle: a.razones.slice(1).join(" · ") || "Toque para ver su ficha",
      })),
      vacio: hayUmbrales ? undefined : (
        <p className="m-frase-nota">Cuando la empresa ponga sus umbrales (cumplimiento, días sin seguimiento), aquí sale quién necesita apoyo.</p>
      ),
    },
    {
      titulo: `Para los próximos ${config.dias_proximos} días`,
      filas: proximos.map((c) => {
        const dias = diasEntre(hoyF, c.fecha_limite);
        return {
          clave: c.id, tono: "neu", icono: "reloj", ir: `/equipo?p=${c.asesora_id}`,
          texto: <><b>{primerNombre(nombre(c.asesora_id))}</b>: «{c.que}»</>,
          detalle: `${dias === 0 ? "Vence hoy" : dias === 1 ? "Vence mañana" : `Vence el ${fecha(c.fecha_limite)}`} · avance ${c.avance} %`,
        };
      }),
    },
    {
      titulo: "Sesiones de esta semana",
      filas: d.sesiones.filter((s) => s.estado !== "cancelada").map((s) => ({
        clave: s.id, tono: s.estado === "hecha" ? "ok" : "neu", icono: "birrete",
        texto: <><b>{s.titulo}</b></>,
        detalle: `${fecha(s.fecha)}${s.hora ? " · " + s.hora.slice(0, 5) : ""} · ${s.punto_id ? d.puntos[s.punto_id] ?? "" : `Todos los ${t.puntos}`}`,
      })),
    },
  ];

  const nada = frases.every((f) => !f.filas.length);
  return (
    <section className="m-columna" aria-label="Pendientes" data-recorrido="pendientes">
      {nada && (
        <div className="m-frase m-frase-ok">
          <span className="m-frase-marca t-ok" aria-hidden="true">●</span>
          <span className="m-frase-texto"><b>Todo al día.</b><span>No hay compromisos vencidos ni pendientes esta semana.</span></span>
        </div>
      )}
      {frases.filter((f) => f.filas.length || f.vacio).map((f) => (
        <div key={f.titulo} className="m-grupo">
          <h2>{f.titulo}{f.filas.length > 0 && <span className="m-cuenta num">{f.filas.length}</span>}</h2>
          {f.filas.length ? (
            <ul className="m-lista">
              {f.filas.slice(0, 6).map((x) => {
                const cuerpo = (
                  <>
                    <span className={`m-frase-marca t-${x.tono}`} aria-hidden="true">
                      {x.tono === "mal" ? "■" : x.tono === "rev" ? "▲" : x.tono === "ok" ? "●" : <Icono id={x.icono} />}
                    </span>
                    <span className="m-frase-texto">{x.texto}<span>{x.detalle}</span></span>
                    {x.ir && <Icono id="derecha" />}
                  </>
                );
                return <li key={x.clave}>{x.ir ? <Link className="m-frase" href={x.ir}>{cuerpo}</Link> : <div className="m-frase">{cuerpo}</div>}</li>;
              })}
            </ul>
          ) : f.vacio}
          {f.filas.length > 6 && <Link className="m-ver-mas" href="/equipo">Ver los {f.filas.length}</Link>}
        </div>
      ))}
      <button className="m-frase m-frase-accion" onClick={() => registrar(undefined, "compromiso")}>
        <span className="m-frase-marca t-marca" aria-hidden="true"><Icono id="mas" /></span>
        <span className="m-frase-texto"><b>Registrar un compromiso</b><span>Qué, quién y para cuándo, en menos de 30 segundos</span></span>
      </button>
    </section>
  );
}

function Resumen({ d, textos: t }: { d: Datos; textos: { persona: string; puntos: string; Personas: string } }) {
  const tot = totales(d.venta);
  const antes = totales(d.ventaAntes);
  const cambio = antes.venta > 0 ? Math.round(((tot.venta - antes.venta) / antes.venta) * 100) : null;
  const meta = metaDelPeriodo(d.metas, d.desde, d.hasta, (m) => !m.asesora_id);
  const tk = ticket(tot);
  const ranking = [...porPersona(d.venta)].sort((a, b) => b[1].venta - a[1].venta).slice(0, 5);
  const max = ranking[0]?.[1].venta ?? 1;
  const quien = new Map(d.gente.map((g) => [g.id, g]));
  const mes = nombreMes(d.desde);
  const mesAntes = nombreMes(anterior(d.desde, d.hasta)[0]);
  const enCurso = d.hasta >= hoy();  // hasta llega a hoy solo en el mes en curso

  return (
    <section className="m-columna m-resumen" aria-labelledby="t-resumen" data-recorrido="resumen">
      <h2 id="t-resumen">{enCurso ? `Lo que va de ${mes}` : `Así cerró ${mes}`}</h2>
      {!d.venta.length ? (
        <p className="m-vacio">Todavía no hay ventas por {t.persona} de {mes}. Suba los Excel del mes en Archivos.</p>
      ) : (<>
        <div className="m-cifra">
          <span className="m-cifra-valor num">{pesos(tot.venta)}</span>
          <span className="m-cifra-contexto">
            {cambio == null ? `vendidos en ${tot.dias} días de ${t.puntos}` : (
              <><span className={cambio >= 0 ? "t-ok" : "t-mal"}><Icono id={cambio >= 0 ? "sube" : "baja"} />
                {cambio >= 0 ? "+" : "−"}{Math.abs(cambio)} %</span> frente a {mesAntes}</>
            )}
          </span>
        </div>
        <div className="m-par">
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{tk ? pesos(tk) : "—"}</span>
            <span className="m-cifra-contexto">ticket promedio en {miles(Math.round(tot.facturas))} facturas</span>
          </div>
          <div className="m-cifra m-cifra-anillo">
            <AnilloMeta valor={tot.venta} meta={meta || null} tamano={64} etiqueta="Cumplimiento" />
            <span className="m-cifra-contexto">{meta ? <>de una meta de <b className="num">{pesos(meta)}</b></> : "Sin meta para este período"}</span>
          </div>
        </div>
        <div className="m-grupo">
          <h2>Quién más vendió</h2>
          <ol className="m-ranking">
            {ranking.map(([id, v], i) => {
              const p = quien.get(id);
              return (
                <li key={id}>
                  <Link href={`/equipo?p=${id}`} className="m-ranking-fila">
                    <span className="m-ranking-pos num" aria-hidden="true">{i + 1}</span>
                    <Avatar id={id} nombre={p?.nombre ?? "?"} tamano={36} />
                    <span className="m-ranking-texto">
                      <b>{p?.nombre ?? "Sin nombre"}</b>
                      <span className="m-barra-dato" aria-hidden="true"><span style={{ width: `${Math.max(4, (v.venta / max) * 100)}%` }} /></span>
                    </span>
                    <span className="m-ranking-valor num">{pesos(v.venta)}</span>
                  </Link>
                </li>
              );
            })}
          </ol>
          <Link className="m-ver-mas" href="/ventas">Ver el ranking completo <Icono id="derecha" /></Link>
        </div>
        {!enCurso && d.ultima && <p className="m-contexto">Último dato cargado: {fecha(d.ultima)}.</p>}
      </>)}
    </section>
  );
}
