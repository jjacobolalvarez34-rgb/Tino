"use client";
// Caja: un día, todos los puntos. Cuánto se vendió, si cuadró (con su causa o «sin causa
// clara»), cómo van las transferencias y si el día está abierto o cerrado. Cerrar el día y
// desbloquearlo (0014): un día cerrado ya no se edita sin permiso del dueño o la encargada.
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Icono } from "@/components/Iconos";
import { Tabla } from "@/components/Tabla";
import { cerrar, desbloquear, dia, type DiaPunto } from "@/lib/caja";
import { ayer, correrDias, fecha, fechaHora, pesos } from "@/lib/formato";
import { hoy } from "@/lib/equipo";

export default function PaginaCaja() {
  return <Marco><Caja /></Marco>;
}

function Cuadre({ f }: { f: DiaPunto }) {
  if (!f.jornada_id || f.venta == null) return <span className="chip c-neu">— Sin datos</span>;
  if (f.estado_motor === "cuadra") return <span className="chip c-ok">● Cuadrado</span>;
  if (f.estado_motor === "explicado") return <span className="chip c-rev">▲ Revisar</span>;
  if (f.estado_motor === "sin_explicar") return <span className="chip c-mal">■ Descuadre</span>;
  return <span className="chip c-esp">— Sin revisar</span>;
}

function Caja() {
  const { yo, avisar, version } = useMarco();
  const [dia_, setDia] = useState(ayer());
  const [filas, setFilas] = useState<DiaPunto[] | null>(null);
  const [error, setError] = useState("");
  const [abriendo, setAbriendo] = useState<string | null>(null);
  const [nota, setNota] = useState("");
  const [ocupado, setOcupado] = useState(false);

  const ver = useCallback(() => {
    setFilas(null); setError("");
    dia(dia_).then(setFilas).catch((e) => setError((e as Error).message));
  }, [dia_]);
  useEffect(() => { ver(); }, [ver, version]);

  const puedeCerrar = (f: DiaPunto) => ["dueno", "encargada"].includes(yo.rol)
    || (["asesora", "responsable_punto"].includes(yo.rol) && yo.punto_id === f.punto_id);
  const puedeDesbloquear = ["dueno", "encargada"].includes(yo.rol);
  const abiertos = (filas ?? []).filter((f) => f.jornada_id && f.estado === "abierta" && puedeCerrar(f));

  async function cerrarDias(ids: string[]) {
    setOcupado(true);
    try { const n = await cerrar(ids); avisar(n === 1 ? "Día cerrado" : `${n} días cerrados`); ver(); }
    catch (e) { avisar((e as Error).message); }
    finally { setOcupado(false); }
  }
  async function abrir(f: DiaPunto) {
    setOcupado(true);
    try { await desbloquear(f.jornada_id!, nota); avisar("Día desbloqueado"); setAbriendo(null); setNota(""); ver(); }
    catch (e) { avisar((e as Error).message); }
    finally { setOcupado(false); }
  }

  const conVenta = (filas ?? []).filter((f) => f.venta != null);
  const venta = conVenta.reduce((s, f) => s + (f.venta ?? 0), 0);
  const descuadre = conVenta.filter((f) => f.estado_motor === "sin_explicar").reduce((s, f) => s + (f.descuadre ?? 0), 0);
  const cerrados = (filas ?? []).filter((f) => f.estado && f.estado !== "abierta").length;
  const noLlegaron = (filas ?? []).reduce((s, f) => s + f.transf.no, 0);

  return (
    <>
      <header className="m-encabezado">
        <h1>Caja</h1>
        <div className="m-periodo" role="group" aria-label="Día">
          <button className="m-icono-boton" onClick={() => setDia(correrDias(dia_, -1))} aria-label="Día anterior"><Icono id="izquierda" /></button>
          <span className="m-periodo-texto">{fecha(dia_)}</span>
          <button className="m-icono-boton" onClick={() => setDia(correrDias(dia_, 1))} aria-label="Día siguiente"
            disabled={dia_ >= hoy()}><Icono id="derecha" /></button>
          <input type="date" aria-label="Ir a una fecha" value={dia_} max={hoy()} onChange={(e) => e.target.value && setDia(e.target.value)} />
        </div>
      </header>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!filas && !error && <div className="m-esqueleto" style={{ height: 200 }} />}
      {filas && (<>
        <div className="m-cifras">
          <div className="m-cifra">
            <span className="m-cifra-valor num">{conVenta.length ? pesos(venta) : "—"}</span>
            <span className="m-cifra-contexto">{conVenta.length ? `vendidos en ${conVenta.length} de ${filas.length} puntos` : "Todavía no hay Excel ni cierre de este día"}</span>
          </div>
          <div className="m-cifra">
            <span className={"m-cifra-valor m-cifra-media num" + (descuadre ? " t-mal" : "")}>{descuadre ? pesos(descuadre) : "$ 0"}</span>
            <span className="m-cifra-contexto">en descuadres sin explicar{noLlegaron ? ` · ${noLlegaron} transferencia(s) no llegaron` : ""}</span>
          </div>
          <div className="m-cifra">
            <span className="m-cifra-valor m-cifra-media num">{cerrados} de {filas.filter((f) => f.jornada_id).length}</span>
            <span className="m-cifra-contexto">días cerrados</span>
          </div>
        </div>
        {abiertos.length > 0 && (
          <button className="boton" style={{ alignSelf: "flex-start" }} disabled={ocupado}
            onClick={() => cerrarDias(abiertos.map((f) => f.jornada_id!))}>
            <Icono id="chulo" />{abiertos.length === 1 ? "Cerrar el día" : `Cerrar los ${abiertos.length} días abiertos`}
          </button>
        )}
        <Tabla titulo={`Caja del ${fecha(dia_)}`} avisar={avisar} clave={(f) => f.punto_id} filas={filas} columnas={[
          { clave: "punto", titulo: "Punto", valor: (f) => f.punto },
          { clave: "venta", titulo: "Venta", tipo: "pesos", valor: (f) => f.venta, total: "suma" },
          { clave: "cuadre", titulo: "Cuadre", valor: (f) => f.estado_motor, mostrar: (f) => <Cuadre f={f} /> },
          { clave: "descuadre", titulo: "Descuadre", tipo: "pesos", valor: (f) => (f.estado_motor === "cuadra" ? 0 : f.descuadre),
            mostrar: (f) => (f.descuadre && f.estado_motor !== "cuadra" ? <span className="num">{pesos(f.descuadre)}</span> : "—") },
          { clave: "causa", titulo: "Causa probable", valor: (f) => f.causa ?? (f.estado_motor === "sin_explicar" ? "Sin causa clara" : null),
            mostrar: (f) => f.estado_motor === "sin_explicar" && !f.causa ? <span>Sin causa clara</span>
              : f.causa ? <Link className="m-enlace" href="/descuadres">{f.causa}</Link> : "—" },
          { clave: "transf", titulo: "Transferencias", valor: (f) => f.transf.no,
            mostrar: (f) => {
              const t = f.transf;
              if (!t.llegaron && !t.no && !t.confirmar && !t.esperando) return "—";
              return <Link className="m-enlace" href="/transferencias">{[t.llegaron && `● ${t.llegaron}`, t.no && `■ ${t.no} no llegó`,
                t.confirmar && `▲ ${t.confirmar} por confirmar`, t.esperando && `${t.esperando} esperando`].filter(Boolean).join(" · ")}</Link>;
            } },
          { clave: "dia", titulo: "Día", valor: (f) => f.estado,
            mostrar: (f) => {
              if (!f.jornada_id) return "—";
              if (f.estado === "abierta") return puedeCerrar(f)
                ? <button className="boton secundario compacto" disabled={ocupado} onClick={() => cerrarDias([f.jornada_id!])}>Cerrar</button>
                : <span className="chip c-esp">Abierto</span>;
              return (
                <span className="m-dia-cerrado">
                  <span className="chip c-ok" title={f.cierre ? `Cerrado ${fechaHora(f.cierre.creado_en)}` : undefined}>● Cerrado</span>
                  {f.cierre && f.cierre.descuadres_abiertos > 0 && <span className="chip c-rev">▲ con {f.cierre.descuadres_abiertos} descuadre abierto</span>}
                  {puedeDesbloquear && (abriendo === f.jornada_id ? (
                    <form className="m-agregar" onSubmit={(e) => { e.preventDefault(); abrir(f); }}>
                      <input type="text" autoFocus aria-label="Por qué se desbloquea" placeholder="¿Por qué se desbloquea?"
                        value={nota} onChange={(e) => setNota(e.target.value)} />
                      <button className="boton compacto" type="submit" disabled={ocupado}>Desbloquear</button>
                    </form>
                  ) : <button className="boton texto compacto" onClick={() => { setAbriendo(f.jornada_id); setNota(""); }}>Desbloquear</button>)}
                </span>
              );
            } },
        ]} />
        <p className="m-contexto">Un día cerrado no recibe caja, pagos ni ventas nuevas y no se le deshace un archivo. Se puede cerrar con descuadres abiertos: queda marcado. Desbloquear lo hacen el dueño o la encargada, con nota.</p>
      </>)}
    </>
  );
}
