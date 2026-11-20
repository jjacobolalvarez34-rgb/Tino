"use client";
// Ventas: ranking por persona y por punto, con ticket promedio, facturas, cumplimiento de
// la meta y la comparación con el período anterior del mismo largo.
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Avatar } from "@/components/Avatar";
import { Icono } from "@/components/Iconos";
import { Tabla } from "@/components/Tabla";
import { puntos as leerPuntos } from "@/lib/datos";
import { anterior, hoy, mesDe, metaDelPeriodo, metas, personas, porPersona, ticket, totales, ultimaFecha, ventas,
  type Meta, type Persona, type Totales, type VentaDia } from "@/lib/equipo";
import { fecha, pesos } from "@/lib/formato";

export default function PaginaVentas() {
  return <Marco><Ventas /></Marco>;
}

type Datos = { venta: VentaDia[]; antes: VentaDia[]; metas: Meta[] };
const pct = (a: number, b: number) => (b > 0 ? Math.round((a / b) * 100) : null);
const cambio = (a: number, b: number) => (b > 0 ? Math.round(((a - b) / b) * 100) : null);

function Variacion({ v }: { v: number | null }) {
  if (v == null) return <span className="t-neu">—</span>;
  return <span className={v >= 0 ? "t-ok" : "t-mal"}>{v >= 0 ? "▲ +" : "▼ −"}{Math.abs(v)} %</span>;
}

function Ventas() {
  const { config, avisar, version } = useMarco();
  const t = config.textos;
  const router = useRouter();
  const [rango, setRango] = useState<[string, string] | null>(null);
  const [vista, setVista] = useState<"personas" | "puntos">("personas");
  const [gente, setGente] = useState<Persona[]>([]);
  const [puntos, setPuntos] = useState<Record<string, string>>({});
  const [d, setD] = useState<Datos | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([personas(), leerPuntos(), ultimaFecha()]).then(([g, p, u]) => {
      setGente(g); setPuntos(p);
      const [desde, fin] = mesDe(u && u < mesDe(hoy())[0] ? u : hoy());
      setRango([desde, fin < hoy() ? fin : hoy()]);
    }).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (!rango) return;
    const [ad, ah] = anterior(...rango);
    setD(null);
    Promise.all([ventas(...rango), ventas(ad, ah), metas(...rango)])
      .then(([venta, antes, ms]) => setD({ venta, antes, metas: ms })).catch((e) => setError((e as Error).message));
  }, [rango, version]);

  function mes(n: number) {
    if (!rango) return;
    const [a, m] = rango[0].split("-").map(Number);
    const ini = new Date(Date.UTC(a, m - 1 + n, 1)).toISOString().slice(0, 10);
    const [desde, fin] = mesDe(ini);
    setRango([desde, fin < hoy() ? fin : hoy()]);
  }

  const nombre = useMemo(() => new Map(gente.map((g) => [g.id, g])), [gente]);
  const filasPersonas = useMemo(() => {
    if (!d || !rango) return [];
    const ahora = porPersona(d.venta), antes = porPersona(d.antes);
    return [...ahora].map(([id, v]) => {
      const meta = metaDelPeriodo(d.metas, rango[0], rango[1], (m) => m.asesora_id === id);
      return { id, nombre: nombre.get(id)?.nombre ?? "Sin nombre", ...v, ticket: ticket(v),
        cumplimiento: meta ? pct(v.venta, meta) : null, cambio: cambio(v.venta, antes.get(id)?.venta ?? 0) };
    }).sort((a, b) => b.venta - a.venta);
  }, [d, rango, nombre]);
  const filasPuntos = useMemo(() => {
    if (!d || !rango) return [];
    const agrupar = (filas: VentaDia[]) => {
      const m = new Map<string, VentaDia[]>();
      for (const f of filas) m.set(f.punto_id, [...(m.get(f.punto_id) ?? []), f]);
      return new Map([...m].map(([k, v]) => [k, totales(v)]));
    };
    const ahora = agrupar(d.venta), antes = agrupar(d.antes);
    return [...ahora].map(([id, v]) => {
      const meta = metaDelPeriodo(d.metas, rango[0], rango[1], (m) => m.punto_id === id && !m.asesora_id);
      return { id, nombre: puntos[id] ?? t.Punto, ...v, ticket: ticket(v), meta,
        cumplimiento: meta ? pct(v.venta, meta) : null, cambio: cambio(v.venta, antes.get(id)?.venta ?? 0) };
    }).sort((a, b) => b.venta - a.venta);
  }, [d, rango, puntos, t.Punto]);

  const tot: Totales | null = d ? totales(d.venta) : null;
  const totAntes = d ? totales(d.antes) : null;
  const metaTotal = d && rango ? metaDelPeriodo(d.metas, rango[0], rango[1], (m) => !m.asesora_id) : 0;
  const sinPersona = d ? d.venta.filter((v) => !v.asesora_id).reduce((s, v) => s + v.venta, 0) : 0;
  const mesTexto = rango ? new Date(rango[0] + "T12:00:00").toLocaleDateString("es-CO", { month: "long", year: "numeric" }) : "";
  const max = filasPersonas[0]?.venta ?? 1;

  return (
    <>
      <header className="m-encabezado">
        <h1>Ventas</h1>
        <div className="m-periodo" role="group" aria-label="Período">
          <button className="m-icono-boton" onClick={() => mes(-1)} aria-label="Mes anterior"><Icono id="izquierda" /></button>
          <span className="m-periodo-texto">{mesTexto}</span>
          <button className="m-icono-boton" onClick={() => mes(1)} aria-label="Mes siguiente"
            disabled={!!rango && rango[1] >= hoy()}><Icono id="derecha" /></button>
          {rango && <span className="m-contexto">{fecha(rango[0])} a {fecha(rango[1])}, comparado con los mismos días antes</span>}
        </div>
      </header>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!d && !error && <div className="m-esqueleto" style={{ height: 120 }} />}
      {d && tot && totAntes && (<>
        <div className="m-cifras">
          <div className="m-cifra">
            <span className="m-cifra-valor num">{pesos(tot.venta)}</span>
            <span className="m-cifra-contexto"><Variacion v={cambio(tot.venta, totAntes.venta)} /> frente a {pesos(totAntes.venta)} antes</span>
          </div>
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{ticket(tot) ? pesos(ticket(tot)) : "—"}</span>
            <span className="m-cifra-contexto">ticket promedio · antes {ticket(totAntes) ? pesos(ticket(totAntes)) : "—"}</span>
          </div>
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{metaTotal ? `${pct(tot.venta, metaTotal)} %` : "—"}</span>
            <span className="m-cifra-contexto">{metaTotal ? <>de la meta de <b className="num">{pesos(metaTotal)}</b></> : "Sin metas para este período"}</span>
          </div>
        </div>
        {sinPersona > 0 && (
          <p className="nota aviso"><span>▲ {pesos(sinPersona)} de venta no tienen {t.persona}: el nombre del reporte no se reconoció. Resuélvalo en Archivos.</span></p>
        )}
        <div className="m-segmentos m-segmentos-chicos" role="group" aria-label="Ver por">
          <button className="m-segmento" aria-pressed={vista === "personas"} onClick={() => setVista("personas")}>Por {t.persona}</button>
          <button className="m-segmento" aria-pressed={vista === "puntos"} onClick={() => setVista("puntos")}>Por {t.punto}</button>
        </div>
        {vista === "personas" ? (
          <Tabla titulo={`Ranking por ${t.persona}`} avisar={avisar} clave={(f) => f.id} filas={filasPersonas}
            alTocar={(f) => router.push(`/equipo?p=${f.id}`)} columnas={[
              { clave: "nombre", titulo: t.Persona, valor: (f) => f.nombre,
                mostrar: (f) => (
                  <span className="m-celda-persona">
                    <Avatar id={f.id} nombre={f.nombre} tamano={32} />
                    <span><b>{f.nombre}</b>
                      <span className="m-barra-dato" aria-hidden="true"><span style={{ width: `${Math.max(3, (f.venta / max) * 100)}%` }} /></span>
                    </span>
                  </span>) },
              { clave: "venta", titulo: "Venta", tipo: "pesos", valor: (f) => f.venta, total: "suma" },
              { clave: "dias", titulo: "Días", tipo: "numero", valor: (f) => f.dias, total: "suma" },
              { clave: "facturas", titulo: "Facturas", tipo: "numero", valor: (f) => Math.round(f.facturas), total: "suma" },
              { clave: "ticket", titulo: "Ticket", tipo: "pesos", valor: (f) => f.ticket, total: () => ticket(tot) },
              { clave: "cumplimiento", titulo: "Meta", tipo: "porcentaje", valor: (f) => f.cumplimiento },
              { clave: "cambio", titulo: "Vs. antes", tipo: "porcentaje", valor: (f) => f.cambio, mostrar: (f) => <Variacion v={f.cambio} /> },
            ]} />
        ) : (
          <Tabla titulo={`Ventas por ${t.punto}`} avisar={avisar} clave={(f) => f.id} filas={filasPuntos} columnas={[
            { clave: "nombre", titulo: t.Punto, valor: (f) => f.nombre },
            { clave: "venta", titulo: "Venta", tipo: "pesos", valor: (f) => f.venta, total: "suma" },
            { clave: "meta", titulo: "Meta", tipo: "pesos", valor: (f) => f.meta || null, total: "suma" },
            { clave: "cumplimiento", titulo: "Cumpl.", tipo: "porcentaje", valor: (f) => f.cumplimiento,
              total: () => (metaTotal ? pct(tot.venta, metaTotal) : null) },
            { clave: "facturas", titulo: "Facturas", tipo: "numero", valor: (f) => Math.round(f.facturas), total: "suma" },
            { clave: "ticket", titulo: "Ticket", tipo: "pesos", valor: (f) => f.ticket, total: () => ticket(tot) },
            { clave: "cambio", titulo: "Vs. antes", tipo: "porcentaje", valor: (f) => f.cambio, mostrar: (f) => <Variacion v={f.cambio} /> },
          ]} />
        )}
        <p className="m-contexto">El ticket promedio solo cuenta los días que traen el número de facturas.</p>
      </>)}
    </>
  );
}
