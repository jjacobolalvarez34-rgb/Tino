"use client";
// Registro del día (A1): todas las personas del punto en una sola pantalla, con contadores
// de + y −. Se llena en menos de un minuto por persona, en el celular.
//
// Una persona que no se toca no se guarda: queda "sin registro" ese día, no en cero (un día sin
// registro no cuenta). Lo que ya estaba guardado sale puesto para corregirlo; si el día ya pasó,
// corregirlo pide una nota. Si otra aplicación trajo datos del mismo día, se muestran aparte.
import { useEffect, useMemo, useState } from "react";
import type { Persona } from "@/lib/equipo";
import { guardarRegistros, hoy, indicadores as leerIndicadores, registrosDelDia, type FilaRegistro, type Indicador,
  type RegistroGuardado } from "@/lib/formacion";
import { fecha as fechaTexto } from "@/lib/formato";
import { textoDeError } from "@/lib/supabase";
import { Avatar } from "./Avatar";
import { Icono } from "./Iconos";
import { useMarco } from "./Marco";

type Fila = { clientes: number; valores: Record<string, number>; tocada: boolean };

export function RegistroDia({ formId, gente, puntos, alGuardar, alError }: {
  formId: string; gente: Persona[]; puntos: Record<string, string>;
  alGuardar: (texto: string) => void; alError: (texto: string) => void;
}) {
  const { yo, config } = useMarco();
  const t = config.textos;
  const fijo = yo.rol === "responsable_punto" ? yo.punto_id : null;
  const [punto, setPunto] = useState(fijo ?? (Object.keys(puntos).length === 1 ? Object.keys(puntos)[0] : ""));
  const [dia, setDia] = useState(hoy());
  const [lista, setLista] = useState<Indicador[] | null>(null);
  const [guardados, setGuardados] = useState<RegistroGuardado[] | null>(null);
  const [filas, setFilas] = useState<Record<string, Fila>>({});
  const [nota, setNota] = useState("");

  useEffect(() => { leerIndicadores().then(setLista).catch((e) => alError(textoDeError(e))); }, [alError]);

  // Las personas que estaban en ese punto ese día.
  const delPunto = useMemo(() => gente.filter((g) => g.activa && g.puntos.some((a) =>
    a.punto_id === punto && a.desde <= dia && (!a.hasta || a.hasta >= dia))), [gente, punto, dia]);

  useEffect(() => {
    if (!punto || !dia) return;
    setGuardados(null);
    registrosDelDia(punto, dia).then((g) => {
      setGuardados(g);
      const inicio: Record<string, Fila> = {};
      for (const r of g.filter((x) => x.origen === "manual"))
        inicio[r.asesora_id] = { clientes: r.clientes_atendidos, valores: { ...r.valores }, tocada: false };
      setFilas(inicio);
      setNota("");
    }).catch((e) => alError(textoDeError(e)));
  }, [punto, dia, alError]);

  const manual = new Map((guardados ?? []).filter((r) => r.origen === "manual").map((r) => [r.asesora_id, r]));
  const integracion = new Map((guardados ?? []).filter((r) => r.origen === "integracion").map((r) => [r.asesora_id, r]));
  const diaPasado = dia < hoy();
  const corrige = diaPasado && Object.entries(filas).some(([id, f]) => f.tocada && manual.has(id));

  function poner(id: string, cambio: (f: Fila) => Fila) {
    setFilas((x) => ({ ...x, [id]: { ...cambio(x[id] ?? { clientes: 0, valores: {}, tocada: false }), tocada: true } }));
  }

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    alError("");
    if (!punto) { alError(`Elija el ${t.punto}.`); return; }
    const enviar: FilaRegistro[] = Object.entries(filas).filter(([id, f]) => f.tocada || manual.has(id))
      .map(([id, f]) => ({ asesora_id: id, clientes_atendidos: f.clientes, valores: f.valores }));
    if (!enviar.some((f) => filas[f.asesora_id].tocada)) { alError("No cambió nada. Toque los + y − de cada persona."); return; }
    for (const f of enviar) {
      const p = gente.find((g) => g.id === f.asesora_id)?.nombre ?? `Una ${t.persona}`;
      for (const i of lista ?? []) {
        if (i.base === "atendidos" && (f.valores[i.id] ?? 0) > f.clientes_atendidos) {
          alError(`${p}: «${i.nombre}» no puede ser mayor que los clientes atendidos.`); return;
        }
      }
    }
    if (corrige && nota.trim().length < 3) { alError("Ese día ya pasó: escriba por qué lo corrige."); return; }
    try {
      const n = await guardarRegistros(punto, dia, enviar, corrige ? nota : undefined);
      alGuardar(n ? `Registro del día guardado (${n} ${n === 1 ? t.persona : t.personas})` : "No había nada que cambiar");
    } catch (er) {
      alError(textoDeError(er));
    }
  }

  return (
    <form id={formId} className="m-form" onSubmit={guardar} noValidate>
      {fijo ? <p className="m-contexto"><Icono id="tienda" />{puntos[fijo] ?? t.Punto}</p> : (
        <div className="campo">
          <label htmlFor="rd-punto">{t.Punto}</label>
          <select id="rd-punto" value={punto} onChange={(e) => setPunto(e.target.value)}>
            <option value="">Elija el {t.punto}</option>
            {Object.entries(puntos).map(([id, n]) => <option key={id} value={id}>{n}</option>)}
          </select>
        </div>
      )}
      <div className="campo m-campo-corto">
        <label htmlFor="rd-dia">Día</label>
        <input id="rd-dia" type="date" value={dia} max={hoy()} onChange={(e) => e.target.value && setDia(e.target.value)} />
      </div>
      <p className="m-contexto">Llene solo a quienes trabajaron. Quien no se toque queda «sin registro» ese día, no en cero.</p>

      {punto && (!lista || !guardados) && <div className="m-esqueleto" style={{ height: 160 }} />}
      {punto && lista && guardados && !delPunto.length && (
        <p className="nota aviso"><span>Nadie estaba asignado a {puntos[punto]} el {fechaTexto(dia)}. Asigne las {t.personas} al {t.punto} desde su ficha en {t.equipo}.</span></p>
      )}
      {punto && lista && guardados && delPunto.map((g) => {
        const f = filas[g.id] ?? { clientes: 0, valores: {}, tocada: false };
        const otra = integracion.get(g.id);
        const estado = f.tocada ? "Sin guardar" : manual.has(g.id) ? "Guardado" : "Sin registro";
        return (
          <fieldset key={g.id} className="m-registro">
            <legend className="m-registro-quien">
              <Avatar id={g.id} nombre={g.nombre} tamano={32} />
              <b>{g.nombre}</b>
              <span className={"chip " + (f.tocada ? "c-esp" : manual.has(g.id) ? "c-ok" : "c-neu")}>{estado}</span>
            </legend>
            <Contador etiqueta="Clientes atendidos" valor={f.clientes} fuerte
              cambiar={(v) => poner(g.id, (x) => ({ ...x, clientes: v }))} />
            {lista.map((i) => (
              <Contador key={i.id} etiqueta={i.nombre} valor={f.valores[i.id] ?? 0}
                tope={i.base === "atendidos" ? f.clientes : undefined}
                cambiar={(v) => poner(g.id, (x) => ({ ...x, valores: { ...x.valores, [i.id]: v } }))} />
            ))}
            {otra && (
              <p className="m-registro-otra">
                <Icono id="transf" />También llegó de {otra.fuente ?? "otra aplicación"}: {otra.clientes_atendidos} atendidos
                {lista.filter((i) => otra.valores[i.id] != null).map((i) => ` · ${i.nombre}: ${otra.valores[i.id]}`).join("")}. No se mezcla con lo de aquí.
              </p>
            )}
          </fieldset>
        );
      })}
      {lista && !lista.length && punto && (
        <p className="m-contexto">Por ahora solo se cuentan los clientes atendidos. Los indicadores (explicó el programa, consultó puntos, referidos) se ponen en Ajustes de {t.equipo}.</p>
      )}
      {corrige && (
        <div className="campo">
          <label htmlFor="rd-nota">Ese día ya pasó: ¿por qué lo corrige?</label>
          <input id="rd-nota" type="text" maxLength={200} value={nota} onChange={(e) => setNota(e.target.value)}
            placeholder="Ej.: se contaron mal los clientes de la tarde" />
        </div>
      )}
    </form>
  );
}

// Un contador con − y + de 44 px. También se puede escribir el número.
function Contador({ etiqueta, valor, cambiar, tope, fuerte }: {
  etiqueta: string; valor: number; cambiar: (v: number) => void; tope?: number; fuerte?: boolean;
}) {
  const pasa = tope != null && valor > tope;
  return (
    <div className={"m-contador" + (fuerte ? " m-contador-fuerte" : "")}>
      <span className="m-contador-etiqueta">{etiqueta}{pasa && <span className="t-mal"> · más que los atendidos</span>}</span>
      <span className="m-contador-control">
        <button type="button" className="m-icono-boton" aria-label={`Quitar uno: ${etiqueta}`} disabled={valor <= 0}
          onClick={() => cambiar(Math.max(0, valor - 1))}>−</button>
        <input type="number" inputMode="numeric" min={0} className="num" aria-label={etiqueta} value={valor}
          onChange={(e) => cambiar(Math.max(0, Math.floor(Number(e.target.value) || 0)))} />
        <button type="button" className="m-icono-boton" aria-label={`Sumar uno: ${etiqueta}`}
          onClick={() => cambiar(valor + 1)}>+</button>
      </span>
    </div>
  );
}
