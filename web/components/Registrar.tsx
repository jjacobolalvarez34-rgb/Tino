"use client";
// "+ Registrar": observación, compromiso, sesión o meta, cada uno en una sola pantalla y en
// menos de 30 segundos. Lo que se puede adivinar ya viene puesto (la persona, su punto, hoy).
import { useEffect, useMemo, useState } from "react";
import { base, mensaje } from "@/lib/supabase";
import { puntos as leerPuntos } from "@/lib/datos";
import { catalogo, correrDiasHoy, hoy, mesDe, personas as leerPersonas, registrarCompromiso, registrarObservacion,
  type ItemCatalogo, type Persona } from "@/lib/equipo";
import { HojaInferior } from "./HojaInferior";
import { Icono } from "./Iconos";
import { useMarco } from "./Marco";

type Tipo = "observacion" | "compromiso" | "evaluacion" | "objetivo" | "sesion" | "meta";
const TIPOS: { id: Tipo; titulo: string; detalle: string; icono: string }[] = [
  { id: "observacion", titulo: "Observación", detalle: "Lo que vio hoy: coaching, cliente incógnito…", icono: "ojo" },
  { id: "compromiso", titulo: "Compromiso", detalle: "Qué va a hacer, quién y para cuándo", icono: "bandera" },
  { id: "evaluacion", titulo: "Evaluación", detalle: "Un puntaje de 1 a 5 por cada criterio", icono: "chulo" },
  { id: "objetivo", titulo: "Diagnóstico u objetivo", detalle: "Cómo está y hacia dónde va", icono: "lapiz" },
  { id: "sesion", titulo: "Sesión", detalle: "Una formación con fecha y tema", icono: "birrete" },
  { id: "meta", titulo: "Meta", detalle: "Cuánto vender en un período", icono: "diana" },
];

export function Registrar({ abierta, persona, tipo, alCerrar, alGuardar }: {
  abierta: boolean; persona?: string; tipo?: string; alCerrar: () => void; alGuardar: (texto: string) => void;
}) {
  const { yo, config } = useMarco();
  const t = config.textos;
  const [paso, setPaso] = useState<Tipo | null>(null);
  const [gente, setGente] = useState<Persona[] | null>(null);
  const [puntos, setPuntos] = useState<Record<string, string>>({});
  const [cat, setCat] = useState<ItemCatalogo[]>([]);
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);

  // Campos (uno solo para todos los formularios: se limpian al abrir).
  const [quien, setQuien] = useState("");
  const [punto, setPunto] = useState("");
  const [tipoObs, setTipoObs] = useState("");
  const [valor, setValor] = useState<"bien" | "a_mejorar" | "neutral">("bien");
  const [texto, setTexto] = useState("");
  const [fecha, setFecha] = useState(hoy());
  const [limite, setLimite] = useState(correrDiasHoy(7));
  const [prioridad, setPrioridad] = useState<"alta" | "media" | "baja">("media");
  const [hora, setHora] = useState("");
  const [desde, setDesde] = useState(mesDe(hoy())[0]);
  const [hasta, setHasta] = useState(mesDe(hoy())[1]);
  const [monto, setMonto] = useState("");
  const [puntajes, setPuntajes] = useState<Record<string, number>>({});
  const [clase, setClase] = useState<"diagnostico" | "objetivo">("diagnostico");

  useEffect(() => {
    if (!abierta) return;
    setPaso((tipo as Tipo) || null); setError(""); setQuien(persona ?? ""); setTexto(""); setTipoObs("");
    setValor("bien"); setFecha(hoy()); setLimite(correrDiasHoy(7)); setPrioridad("media"); setHora(""); setMonto(""); setPuntajes({}); setClase("diagnostico");
    const [d, h] = mesDe(hoy()); setDesde(d); setHasta(h);
    if (!gente) {
      Promise.all([leerPersonas(), leerPuntos(), catalogo()])
        .then(([g, p, c]) => { setGente(g.filter((x) => x.activa)); setPuntos(p); setCat(c); })
        .catch((e) => setError((e as Error).message));
    }
  }, [abierta, persona, tipo]); // eslint-disable-line react-hooks/exhaustive-deps

  const elegida = gente?.find((g) => g.id === quien);
  const puntosDe = useMemo(() => {
    const suyos = elegida?.puntos.map((a) => a.punto_id).filter((p) => p in puntos) ?? [];
    if (yo.rol === "responsable_punto" && yo.punto_id) return [yo.punto_id];
    return suyos.length ? suyos : Object.keys(puntos);
  }, [elegida, puntos, yo]);
  useEffect(() => { if (!puntosDe.includes(punto)) setPunto(puntosDe.length === 1 ? puntosDe[0] : ""); }, [puntosDe]); // eslint-disable-line react-hooks/exhaustive-deps

  const criterios = cat.filter((c) => c.clase === "criterio");

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    const falta = (m: string) => { setError(m); return true; };
    if (paso !== "sesion" && paso !== "meta" && !quien && falta(`Elija a la ${t.persona}.`)) return;
    if (paso === "evaluacion" && !criterios.length && falta("Primero agregue los criterios de evaluación.")) return;
    if (paso !== "sesion" && !punto && falta(`Elija el ${t.punto}.`)) return;
    setOcupado(true);
    try {
      if (paso === "observacion") {
        if (!tipoObs) throw new Error("Elija qué tipo de observación es.");
        if (texto.trim().length < 3) throw new Error("Escriba qué vio, aunque sea corto.");
        await registrarObservacion({ empresa_id: yo.empresa_id, asesora_id: quien, punto_id: punto,
          tipo_observacion_id: tipoObs, texto: texto.trim(), valoracion: valor, fecha });
        alGuardar("Observación guardada");
      } else if (paso === "compromiso") {
        if (texto.trim().length < 3) throw new Error("Escriba qué se compromete a hacer.");
        await registrarCompromiso({ empresa_id: yo.empresa_id, asesora_id: quien, punto_id: punto,
          que: texto.trim(), fecha_limite: limite, prioridad });
        alGuardar("Compromiso guardado");
      } else if (paso === "evaluacion") {
        const dados = Object.entries(puntajes);
        if (!dados.length) throw new Error("Califique al menos un criterio.");
        const { data, error: er } = await base().from("seguimiento").insert({ empresa_id: yo.empresa_id, asesora_id: quien,
          punto_id: punto, tipo: "evaluacion", texto: texto.trim(), fecha }).select("id");
        if (er) throw new Error(mensaje(er));
        const { error: er2 } = await base().from("seguimiento_criterio").insert(dados.map(([criterio_id, puntaje]) =>
          ({ empresa_id: yo.empresa_id, seguimiento_id: data![0].id, criterio_id, puntaje })));
        if (er2) throw new Error(mensaje(er2));
        alGuardar("Evaluación guardada");
      } else if (paso === "objetivo") {
        if (texto.trim().length < 3) throw new Error("Escriba el diagnóstico o el objetivo.");
        const { error: er } = await base().from("seguimiento").insert({ empresa_id: yo.empresa_id, asesora_id: quien,
          punto_id: punto, tipo: clase, texto: texto.trim(), fecha });
        if (er) throw new Error(mensaje(er));
        alGuardar(clase === "objetivo" ? "Objetivo guardado" : "Diagnóstico guardado");
      } else if (paso === "sesion") {
        if (texto.trim().length < 3) throw new Error("Escriba el tema o el título de la sesión.");
        const { error: er } = await base().from("sesion_formacion").insert({ empresa_id: yo.empresa_id,
          punto_id: punto || null, titulo: texto.trim(), fecha, hora: hora || null });
        if (er) throw new Error(mensaje(er));
        alGuardar("Sesión programada");
      } else if (paso === "meta") {
        const n = Number(monto.replace(/\D/g, ""));
        if (!n) throw new Error("Escriba el monto de la meta.");
        if (hasta < desde) throw new Error("La fecha final va después de la inicial.");
        const { error: er } = await base().from("meta_periodo").insert({ empresa_id: yo.empresa_id, punto_id: punto,
          asesora_id: quien || null, desde, hasta, monto: n });
        if (er) throw new Error(er.code === "23P01" ? "Ya hay una meta activa que se cruza con esas fechas." : mensaje(er));
        alGuardar("Meta guardada");
      }
    } catch (er) {
      setError((er as Error).message);
    } finally {
      setOcupado(false);
    }
  }

  const titulo = paso ? TIPOS.find((x) => x.id === paso)!.titulo : "Registrar";
  const tiposObs = cat.filter((c) => c.clase === "tipo_observacion");
  const listaPersonas = (opcional?: string) => (
    <div className="campo">
      <label htmlFor="r-quien">{t.Persona}</label>
      <select id="r-quien" value={quien} onChange={(e) => setQuien(e.target.value)}>
        <option value="">{opcional ?? `Elija una ${t.persona}`}</option>
        {gente?.map((g) => <option key={g.id} value={g.id}>{g.nombre}</option>)}
      </select>
    </div>
  );
  const listaPuntos = (todos?: string) => puntosDe.length === 1 && !todos
    ? <p className="m-contexto"><Icono id="tienda" />{puntos[puntosDe[0]]}</p>
    : (
      <div className="campo">
        <label htmlFor="r-punto">{t.Punto}</label>
        <select id="r-punto" value={punto} onChange={(e) => setPunto(e.target.value)}>
          <option value="">{todos ?? `Elija el ${t.punto}`}</option>
          {(todos ? Object.keys(puntos) : puntosDe).map((p) => <option key={p} value={p}>{puntos[p]}</option>)}
        </select>
      </div>
    );

  return (
    <HojaInferior abierta={abierta} titulo={titulo} alCerrar={alCerrar}
      pie={paso ? (
        <div className="m-pie-acciones">
          {!tipo && <button type="button" className="boton secundario" onClick={() => { setPaso(null); setError(""); }}>Atrás</button>}
          <button type="submit" form="r-form" className="boton" disabled={ocupado} aria-busy={ocupado}>
            {ocupado ? "Guardando…" : "Guardar"}
          </button>
        </div>
      ) : undefined}>
      {!paso && (
        <ul className="m-lista" aria-label="Qué quiere registrar">
          {TIPOS.map((x) => (
            <li key={x.id}>
              <button className="m-fila" onClick={() => setPaso(x.id)}>
                <span className="m-fila-icono"><Icono id={x.icono} /></span>
                <span className="m-fila-texto"><b>{x.titulo}</b><span>{x.detalle}</span></span>
                <Icono id="derecha" />
              </button>
            </li>
          ))}
        </ul>
      )}
      {paso && !gente && !error && <div className="m-esqueleto" style={{ height: 180 }} />}
      {paso && gente && (
        <form id="r-form" className="m-form" onSubmit={guardar} noValidate>
          {paso === "observacion" && <>
            {listaPersonas()}
            {listaPuntos()}
            <fieldset className="m-opciones">
              <legend>Tipo</legend>
              {tiposObs.map((c) => (
                <label key={c.id} className="m-opcion">
                  <input type="radio" name="tipo" value={c.id} checked={tipoObs === c.id} onChange={() => setTipoObs(c.id)} />{c.nombre}
                </label>
              ))}
            </fieldset>
            <fieldset className="m-segmentos">
              <legend>¿Cómo le fue?</legend>
              {([["bien", "● Bien"], ["a_mejorar", "▲ A mejorar"], ["neutral", "Neutral"]] as const).map(([v, n]) => (
                <label key={v} className={"m-segmento s-" + v}>
                  <input type="radio" name="valor" checked={valor === v} onChange={() => setValor(v)} />{n}
                </label>
              ))}
            </fieldset>
            <div className="campo">
              <label htmlFor="r-texto">Qué vio</label>
              <textarea id="r-texto" value={texto} onChange={(e) => setTexto(e.target.value)} rows={3} maxLength={600}
                placeholder="Ej.: ofreció el combo en cada venta y cerró dos más." />
            </div>
            <div className="campo m-campo-corto">
              <label htmlFor="r-fecha">Fecha</label>
              <input id="r-fecha" type="date" value={fecha} max={hoy()} onChange={(e) => setFecha(e.target.value)} />
            </div>
          </>}

          {paso === "compromiso" && <>
            {listaPersonas()}
            {listaPuntos()}
            <div className="campo">
              <label htmlFor="r-que">Qué se compromete a hacer</label>
              <input id="r-que" type="text" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={200}
                placeholder="Ej.: ofrecer el combo en cada venta" />
            </div>
            <fieldset className="m-opciones">
              <legend>Para cuándo</legend>
              {([[3, "En 3 días"], [7, "En una semana"], [14, "En dos semanas"]] as const).map(([d, n]) => (
                <label key={d} className="m-opcion">
                  <input type="radio" name="limite" checked={limite === correrDiasHoy(d)} onChange={() => setLimite(correrDiasHoy(d))} />{n}
                </label>
              ))}
              <input type="date" aria-label="Otra fecha" value={limite} min={hoy()} onChange={(e) => setLimite(e.target.value)} />
            </fieldset>
            <fieldset className="m-segmentos">
              <legend>Prioridad</legend>
              {(["alta", "media", "baja"] as const).map((p) => (
                <label key={p} className="m-segmento">
                  <input type="radio" name="prioridad" checked={prioridad === p} onChange={() => setPrioridad(p)} />
                  {p[0].toUpperCase() + p.slice(1)}
                </label>
              ))}
            </fieldset>
          </>}

          {paso === "evaluacion" && <>
            {listaPersonas()}
            {listaPuntos()}
            {!criterios.length ? (
              <p className="nota aviso"><span>La empresa todavía no tiene criterios de evaluación. Agréguelos en Más → Ajustes de {t.equipo}.</span></p>
            ) : criterios.map((c) => (
              <fieldset key={c.id} className="m-segmentos m-puntaje">
                <legend>{c.nombre}</legend>
                {[1, 2, 3, 4, 5].map((n) => (
                  <label key={n} className="m-segmento">
                    <input type="radio" name={"c-" + c.id} checked={puntajes[c.id] === n}
                      onChange={() => setPuntajes((x) => ({ ...x, [c.id]: n }))} />{n}
                  </label>
                ))}
              </fieldset>
            ))}
            <div className="campo">
              <label htmlFor="r-ecom">Comentario (opcional)</label>
              <textarea id="r-ecom" rows={2} value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={600} />
            </div>
          </>}

          {paso === "objetivo" && <>
            {listaPersonas()}
            {listaPuntos()}
            <fieldset className="m-segmentos">
              <legend>Qué es</legend>
              {([["diagnostico", "Diagnóstico"], ["objetivo", "Objetivo"]] as const).map(([v, n]) => (
                <label key={v} className="m-segmento">
                  <input type="radio" name="clase" checked={clase === v} onChange={() => setClase(v)} />{n}
                </label>
              ))}
            </fieldset>
            <div className="campo">
              <label htmlFor="r-obj">{clase === "objetivo" ? "Hacia dónde va" : "Cómo está hoy"}</label>
              <textarea id="r-obj" rows={3} value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={600}
                placeholder={clase === "objetivo" ? "Ej.: subir el ticket promedio a $ 120.000 este mes" : "Ej.: atiende bien pero no ofrece productos adicionales"} />
            </div>
          </>}

          {paso === "sesion" && <>
            <div className="campo">
              <label htmlFor="r-titulo">Tema</label>
              <input id="r-titulo" type="text" value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={120}
                placeholder="Ej.: Cierre de venta con el producto del mes" />
            </div>
            <div className="m-dos">
              <div className="campo"><label htmlFor="r-sfecha">Fecha</label>
                <input id="r-sfecha" type="date" value={fecha} onChange={(e) => setFecha(e.target.value)} /></div>
              <div className="campo"><label htmlFor="r-hora">Hora</label>
                <input id="r-hora" type="time" value={hora} onChange={(e) => setHora(e.target.value)} /></div>
            </div>
            {listaPuntos(`Todos los ${t.puntos}`)}
          </>}

          {paso === "meta" && <>
            {listaPuntos(undefined)}
            {listaPersonas(`Todo el ${t.punto}`)}
            <div className="m-dos">
              <div className="campo"><label htmlFor="r-desde">Desde</label>
                <input id="r-desde" type="date" value={desde} onChange={(e) => setDesde(e.target.value)} /></div>
              <div className="campo"><label htmlFor="r-hasta">Hasta</label>
                <input id="r-hasta" type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} /></div>
            </div>
            <div className="campo">
              <label htmlFor="r-monto">Cuánto vender</label>
              <input id="r-monto" type="text" inputMode="numeric" className="num" value={monto} placeholder="$ 0"
                onChange={(e) => { const n = e.target.value.replace(/\D/g, ""); setMonto(n ? "$ " + Number(n).toLocaleString("es-CO") : ""); }} />
            </div>
          </>}
        </form>
      )}
      {error && <p className="error-campo" role="alert">{error}</p>}
    </HojaInferior>
  );
}
