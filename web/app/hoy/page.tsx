"use client";
import { textoDeError } from "@/lib/supabase";
// Hoy: frases que se tocan, ordenadas por urgencia (compromisos vencidos, quién necesita
// apoyo, lo que viene, las sesiones de la semana). Al lado, el resumen del período.
import Link from "next/link";
import { useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Avatar } from "@/components/Avatar";
import { AnilloMeta } from "@/components/AnilloMeta";
import { Icono } from "@/components/Iconos";
import { yaLoVio } from "@/components/Recorrido";
import { Ayuda, AYUDA_TICKET } from "@/components/Ayuda";
import { Pendientes } from "@/components/Pendientes";
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
    yaLoVio("inicio").then((visto) => { if (!visto) verRecorrido("inicio"); });
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
        setError(textoDeError(e));
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
          <Pendientes d={d} />
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
  const mesAntes = nombreMes(anterior(d.desde, d.hasta)[1]);
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
            {cambio == null ? `Sin datos de ${mesAntes} para comparar` : (
              <><span className={cambio >= 0 ? "t-ok" : "t-mal"}><Icono id={cambio >= 0 ? "sube" : "baja"} />
                {cambio >= 0 ? "+" : "−"}{Math.abs(cambio)} %</span> frente a {mesAntes}</>
            )}
          </span>
        </div>
        <div className="m-par">
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{tk ? pesos(tk) : "—"}</span>
            <span className="m-cifra-contexto">ticket promedio en {miles(Math.round(tot.facturas))} facturas<Ayuda texto={AYUDA_TICKET} /></span>
          </div>
          <div className="m-cifra m-cifra-anillo">
            <AnilloMeta valor={tot.venta} meta={meta || null} tamano={64} etiqueta="Cumplimiento" />
            <span className="m-cifra-contexto">{meta ? <>{enCurso ? "de la meta a la fecha:" : "de una meta de"} <b className="num">{pesos(meta)}</b></> : "Sin meta para este período"}</span>
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
