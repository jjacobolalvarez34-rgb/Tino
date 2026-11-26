"use client";
// Formación y desempeño en Equipo (A2–A5): cómo van los indicadores del registro del día, en
// qué paso del ciclo va cada persona y el calendario de la semana. Los datos de "Lo que hay que
// hacer" son los mismos de Hoy (Pendientes).
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import type { Compromiso, Persona, Sesion } from "@/lib/equipo";
import { anterior, sesiones as leerSesiones } from "@/lib/equipo";
import { calcular, diferencia, hoy, registros as leerRegistros, semanaDe, type Etapa, type Indicador, type Paso,
  type RegistroVista } from "@/lib/formacion";
import { correrDias, fecha, miles } from "@/lib/formato";
import { textoDeError } from "@/lib/supabase";
import { Avatar } from "./Avatar";
import { Icono } from "./Iconos";
import { useMarco } from "./Marco";

const PUEDEN_SESION = ["dueno", "encargada", "soporte", "lider", "responsable_punto"];
const LLENAN_REGISTRO = ["dueno", "lider", "responsable_punto"];
const redondo = (n: number | null) => (n == null ? "—" : `${Math.round(n)} %`);

// ---------------------------------------------------------------------------------
// Cómo van
// ---------------------------------------------------------------------------------

export type Periodo = "mes" | "semana";

export function rangos(periodo: Periodo): { desde: string; hasta: string; antesDesde: string; antesHasta: string; nombre: string; nombreAntes: string } {
  const h = hoy();
  if (periodo === "semana") {
    const [lun] = semanaDe(h);
    return { desde: lun, hasta: h, antesDesde: correrDias(lun, -7), antesHasta: correrDias(h, -7),
             nombre: "esta semana", nombreAntes: "los mismos días de la semana pasada" };
  }
  const desde = h.slice(0, 8) + "01";
  const [ad, ah] = anterior(desde, h);
  return { desde, hasta: h, antesDesde: ad, antesHasta: ah, nombre: "este mes", nombreAntes: "los mismos días del mes pasado" };
}

export function ComoVan({ indicadores, punto, persona, periodo }: {
  indicadores: Indicador[]; punto?: string; persona?: string; periodo: Periodo;
}) {
  const { config, registrar, yo, version } = useMarco();
  const t = config.textos;
  const r = rangos(periodo);
  const [datos, setDatos] = useState<{ ahora: RegistroVista[]; antes: RegistroVista[] } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    setDatos(null);
    Promise.all([leerRegistros(r.desde, r.hasta, persona), leerRegistros(r.antesDesde, r.antesHasta, persona)])
      .then(([ahora, antes]) => setDatos({ ahora, antes }))
      .catch((e) => setError(textoDeError(e)));
  }, [r.desde, r.hasta, r.antesDesde, r.antesHasta, persona, version]);

  if (error) return <div className="nota mal" role="alert"><b>{error}</b></div>;
  if (!datos) return <div className="m-esqueleto" style={{ height: 150 }} />;
  const filtro = (x: RegistroVista) => !punto || x.punto_id === punto;
  const ahora = calcular(datos.ahora.filter(filtro), indicadores);
  const antes = calcular(datos.antes.filter(filtro), indicadores);
  const hayAntes = antes.dias > 0;

  if (!ahora.dias) {
    return (
      <div className="nota">
        <span className="cuerpo">
          <b>Todavía no hay registros del día {r.nombre}.</b>
          <span>Los indicadores salen de lo que se anota al cerrar cada día: clientes atendidos y lo que hizo cada {t.persona}. Un día sin registro no cuenta como cero.</span>
          {LLENAN_REGISTRO.includes(yo.rol) && (
            <button className="boton secundario compacto" onClick={() => registrar(persona, "registro")}><Icono id="dia" />Llenar el registro del día</button>
          )}
        </span>
      </div>
    );
  }

  const tarjetas: { clave: string; nombre: string; valor: string; exp: string; dif: ReturnType<typeof diferencia> }[] = [
    { clave: "conversion", nombre: "Conversión", valor: redondo(ahora.conversion), exp: "de los atendidos compraron",
      dif: hayAntes ? diferencia(ahora.conversion, antes.conversion, true) : null },
    ...indicadores.map((i) => {
      const a = ahora.porIndicador.get(i.id)!, b = antes.porIndicador.get(i.id)!;
      return i.base === "conteo"
        ? { clave: i.id, nombre: i.nombre, valor: miles(a.valor), exp: r.nombre, dif: hayAntes ? diferencia(a.valor, b.valor, false) : null }
        : { clave: i.id, nombre: i.nombre, valor: redondo(a.porcentaje),
            exp: i.base === "atendidos" ? "de los clientes atendidos" : "de las ventas",
            dif: hayAntes ? diferencia(a.porcentaje, b.porcentaje, true) : null };
    }),
    { clave: "atendidos", nombre: "Clientes atendidos", valor: miles(ahora.atendidos), exp: `en ${ahora.dias} día${ahora.dias === 1 ? "" : "s"} con registro`,
      dif: hayAntes ? diferencia(ahora.atendidos, antes.atendidos, false) : null },
  ];

  return (
    <>
      <div className="m-indicadores">
        {tarjetas.map((x) => (
          <div key={x.clave} className="m-indicador">
            <span className="m-indicador-nombre">{x.nombre}</span>
            <span className="m-indicador-valor num">{x.valor}</span>
            <span className="m-indicador-exp">{x.exp}</span>
            <span className="m-indicador-dif">
              {x.dif ? <><b className={x.dif.signo > 0 ? "t-ok" : x.dif.signo < 0 ? "t-mal" : "t-neu"}>{x.dif.texto}</b> frente a {r.nombreAntes}</>
                : <span className="t-neu">Sin registros de {r.nombreAntes} para comparar</span>}
            </span>
          </div>
        ))}
      </div>
      <p className="m-contexto">
        Solo cuentan los días con registro: un día sin registro no es cero. La conversión usa las facturas del Excel del día de cada {t.persona}
        {ahora.facturas === 0 ? " (todavía no hay venta cargada para esos días)" : ""}.
        {ahora.compartidos > 0 && <> En {ahora.compartidos} día{ahora.compartidos === 1 ? "" : "s"} la venta se repartió entre varias {t.personas} (dos, tres o más): las facturas se dividen por partes iguales, así que la conversión de cada una en esos días es aproximada.</>}
      </p>
    </>
  );
}

// ---------------------------------------------------------------------------------
// En qué paso va cada persona
// ---------------------------------------------------------------------------------

export function FranjaEtapas({ etapas, pasos, gente }: { etapas: Etapa[]; pasos: Paso[]; gente: Persona[] }) {
  const { config } = useMarco();
  const t = config.textos;
  if (!etapas.length) {
    return (
      <div className="nota">
        <span className="cuerpo">
          <b>La empresa todavía no tiene las etapas del ciclo de formación.</b>
          <span>Se ponen una vez en Ajustes de {t.equipo}: escríbalas o use la plantilla sugerida (Diagnóstico, Formación, Acompañamiento, Evaluación y Compromisos).</span>
          <Link href="/equipo/ajustes#t-etapa" className="boton secundario compacto">Ir a Ajustes</Link>
        </span>
      </div>
    );
  }
  const paso = new Map(pasos.map((p) => [p.asesora_id, p.etapa_id]));
  const activas = gente.filter((g) => g.activa);
  const sinPaso = activas.filter((g) => !paso.has(g.id) || !etapas.some((e) => e.id === paso.get(g.id)));
  const columnas = [...etapas.map((e, i) => ({ id: e.id, titulo: e.nombre, antetitulo: `Paso ${i + 1}`, gente: activas.filter((g) => paso.get(g.id) === e.id) })),
    ...(sinPaso.length ? [{ id: "sin", titulo: "Sin paso asignado", antetitulo: "Falta", gente: sinPaso }] : [])];
  return (
    <div className="m-etapas" role="list">
      {columnas.map((c) => (
        <div key={c.id} className={"m-etapa" + (c.id === "sin" ? " m-etapa-sin" : "")} role="listitem">
          <span className="m-etapa-paso">{c.antetitulo}</span>
          <b>{c.titulo}</b>
          <span className="m-contexto num">{c.gente.length} {c.gente.length === 1 ? t.persona : t.personas}</span>
          <div className="m-caritas">
            {c.gente.length ? c.gente.map((g) => (
              <Link key={g.id} href={`/equipo?p=${g.id}`} className="m-carita" title={g.nombre} aria-label={`Ver a ${g.nombre}`}>
                <Avatar id={g.id} nombre={g.nombre} tamano={36} />
              </Link>
            )) : <span className="m-contexto">Nadie</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------------
// Calendario de la semana (lunes a domingo)
// ---------------------------------------------------------------------------------

const DIAS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];

export function CalendarioSemana({ compromisos, gente, puntos }: {
  compromisos: Compromiso[]; gente: Persona[]; puntos: Record<string, string>;
}) {
  const { config, registrar, yo, version } = useMarco();
  const t = config.textos;
  const [lunes, setLunes] = useState(() => semanaDe(hoy())[0]);
  const [ses, setSes] = useState<Sesion[] | null>(null);
  const [error, setError] = useState("");
  const domingo = correrDias(lunes, 6);
  useEffect(() => {
    setSes(null);
    leerSesiones(lunes, domingo).then(setSes).catch((e) => setError(textoDeError(e)));
  }, [lunes, domingo, version]);

  const nombre = useMemo(() => new Map(gente.map((g) => [g.id, g.nombre])), [gente]);
  const dias = Array.from({ length: 7 }, (_, i) => correrDias(lunes, i));
  const puede = PUEDEN_SESION.includes(yo.rol);
  const hoyF = hoy();

  return (
    <div className="m-calendario">
      <div className="m-periodo" role="group" aria-label="Semana">
        <button className="m-icono-boton" onClick={() => setLunes(correrDias(lunes, -7))} aria-label="Semana anterior"><Icono id="izquierda" /></button>
        <span className="m-periodo-texto">Del {fecha(lunes)} al {fecha(domingo)}</span>
        <button className="m-icono-boton" onClick={() => setLunes(correrDias(lunes, 7))} aria-label="Semana siguiente"><Icono id="derecha" /></button>
        {lunes !== semanaDe(hoyF)[0] && <button className="boton texto compacto" onClick={() => setLunes(semanaDe(hoyF)[0])}>Esta semana</button>}
      </div>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!ses && !error && <div className="m-esqueleto" style={{ height: 160 }} />}
      {ses && (
        <ol className="m-semana">
          {dias.map((d, i) => {
            const delDia = ses.filter((s) => s.fecha === d && s.estado !== "cancelada");
            const vencen = compromisos.filter((c) => c.fecha_limite === d);
            const vacio = !delDia.length && !vencen.length;
            return (
              <li key={d} className={"m-dia" + (d === hoyF ? " m-dia-hoy" : "") + (vacio ? " m-dia-vacio" : "")}>
                <div className="m-dia-cabeza">
                  <span><b>{DIAS[i]}</b> <span className="num">{Number(d.slice(8))}</span>{d === hoyF && <span className="chip c-esp">Hoy</span>}</span>
                  {puede && d >= hoyF && (
                    <button className="m-icono-boton m-dia-mas" aria-label={`Programar una sesión el ${fecha(d)}`}
                      onClick={() => registrar(undefined, "sesion", d)}><Icono id="mas" /></button>
                  )}
                </div>
                {vacio && <span className="m-contexto">Nada programado</span>}
                {delDia.map((s) => (
                  <div key={s.id} className={"m-evento" + (s.estado === "hecha" ? " m-evento-hecho" : "")}>
                    <Icono id="birrete" />
                    <span><b>{s.titulo}</b><span>{s.hora ? s.hora.slice(0, 5) + " · " : ""}{s.punto_id ? puntos[s.punto_id] ?? "" : `Todos los ${t.puntos}`}{s.estado === "hecha" ? " · hecha" : ""}</span></span>
                  </div>
                ))}
                {vencen.map((c) => (
                  <Link key={c.id} href={`/equipo?p=${c.asesora_id}`} className={"m-evento m-evento-compromiso" + (d < hoyF ? " m-evento-vencido" : "")}>
                    <Icono id="bandera" />
                    <span><b>{d < hoyF ? "Venció: " : "Vence: "}«{c.que}»</b><span>{nombre.get(c.asesora_id) ?? `Una ${t.persona}`} · avance {c.avance} %</span></span>
                  </Link>
                ))}
              </li>
            );
          })}
        </ol>
      )}
      {puede && (
        <button className="boton secundario" style={{ alignSelf: "flex-start" }} onClick={() => registrar(undefined, "sesion")}>
          <Icono id="birrete" />Programar una sesión
        </button>
      )}
    </div>
  );
}
