"use client";
// Datos del módulo Equipo, con la sesión de quien entra: RLS decide qué ve cada rol
// (el responsable de punto, solo su punto; observaciones y evaluaciones, solo quien puede).
// Cada consulta pide solo las columnas que la pantalla muestra.
import { base, leer, mensaje } from "./supabase";
import { correrDias, hoyBogota } from "./formato";
import { textosDe, type Textos } from "./textos";

export type Asignacion = { punto_id: string; desde: string; hasta: string | null };
export type Persona = { id: string; codigo: string; nombre: string; activa: boolean; puntos: Asignacion[] };
export type VentaDia = { punto_id: string; fecha: string; asesora_id: string | null; venta: number; facturas: number | null };
export type Meta = { id: string; punto_id: string; asesora_id: string | null; desde: string; hasta: string; monto: number };
export type Compromiso = {
  id: string; asesora_id: string; punto_id: string; que: string; fecha_limite: string; prioridad: "alta" | "media" | "baja";
  estado: "abierto" | "en_curso" | "cumplido" | "no_cumplido" | "anulado"; avance: number; creado_en: string; cerrado_en: string | null;
};
export type Seguimiento = {
  id: string; asesora_id: string; punto_id: string; tipo: "diagnostico" | "objetivo" | "observacion" | "evaluacion";
  tipo_observacion_id: string | null; fecha: string; texto: string; valoracion: "bien" | "a_mejorar" | "neutral" | null;
  creado_en: string;
};
export type Sesion = { id: string; punto_id: string | null; titulo: string; fecha: string; hora: string | null; estado: string };
export type ItemCatalogo = { id: string; clase: string; nombre: string };
export type Config = {
  umbral_cumplimiento: number | null; umbral_dias_sin_seguimiento: number | null;
  umbral_compromisos_vencidos: number | null; dias_proximos: number; textos: Textos;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Libre = Record<string, any>;

export const hoy = () => hoyBogota();
const ABIERTOS = new Set(["abierto", "en_curso"]);

export async function config(): Promise<Config> {
  const [c] = await leer<Libre>("empresa_config",
    "equipo_umbral_cumplimiento,equipo_umbral_dias_sin_seguimiento,equipo_umbral_compromisos_vencidos,equipo_dias_proximos,textos",
    [], "empresa_id");
  return {
    umbral_cumplimiento: c?.equipo_umbral_cumplimiento ?? null,
    umbral_dias_sin_seguimiento: c?.equipo_umbral_dias_sin_seguimiento ?? null,
    umbral_compromisos_vencidos: c?.equipo_umbral_compromisos_vencidos ?? null,
    dias_proximos: c?.equipo_dias_proximos ?? 7,
    textos: textosDe(c?.textos),
  };
}

export async function personas(): Promise<Persona[]> {
  const [gente, asign] = await Promise.all([
    leer<Libre>("asesora", "id,codigo,nombre_completo,activa", [], "nombre_completo"),
    leer<Libre>("asesora_punto", "asesora_id,punto_id,desde,hasta", [], "desde"),
  ]);
  const h = hoy();
  return gente.map((a) => ({
    id: a.id, codigo: a.codigo, nombre: a.nombre_completo, activa: a.activa,
    puntos: asign.filter((x) => x.asesora_id === a.id && (!x.hasta || x.hasta >= h))
      .map((x) => ({ punto_id: x.punto_id, desde: x.desde, hasta: x.hasta })),
  }));
}

// El último día con venta por persona: "Hoy" muestra ese mes si el actual aún no tiene datos.
export async function ultimaFecha(): Promise<string | null> {
  const { data, error } = await base().from("v_venta_asesora").select("fecha").order("fecha", { ascending: false }).limit(1);
  if (error) throw new Error(mensaje(error));
  return data?.[0]?.fecha ?? null;
}

export async function ventas(desde: string, hasta: string, persona?: string): Promise<VentaDia[]> {
  const filtros: [string, "gte" | "lte" | "eq", string][] = [["fecha", "gte", desde], ["fecha", "lte", hasta]];
  if (persona) filtros.push(["asesora_id", "eq", persona]);
  return leer<VentaDia>("v_venta_asesora", "punto_id,fecha,asesora_id,venta,facturas", filtros, "fecha");
}

export async function metas(desde: string, hasta: string): Promise<Meta[]> {
  return leer<Meta>("meta_periodo", "id,punto_id,asesora_id,desde,hasta,monto",
    [["activo", "eq", "true"], ["desde", "lte", hasta], ["hasta", "gte", desde]], "desde");
}

export async function compromisos(persona?: string): Promise<Compromiso[]> {
  const filtros: [string, "eq", string][] = persona ? [["asesora_id", "eq", persona]] : [];
  const todos = await leer<Compromiso>("compromiso",
    "id,asesora_id,punto_id,que,fecha_limite,prioridad,estado,avance,creado_en,cerrado_en", filtros, "fecha_limite");
  return persona ? todos.filter((c) => c.estado !== "anulado") : todos.filter((c) => ABIERTOS.has(c.estado));
}

export async function seguimientos(desde: string, persona?: string): Promise<Seguimiento[]> {
  const filtros: [string, "gte" | "eq", string][] = [["fecha", "gte", desde], ["anulado", "eq", "false"]];
  if (persona) filtros.push(["asesora_id", "eq", persona]);
  return leer<Seguimiento>("seguimiento",
    "id,asesora_id,punto_id,tipo,tipo_observacion_id,fecha,texto,valoracion,creado_en", filtros, "fecha.desc");
}

export async function sesiones(desde: string, hasta: string): Promise<Sesion[]> {
  return leer<Sesion>("sesion_formacion", "id,punto_id,titulo,fecha,hora,estado",
    [["fecha", "gte", desde], ["fecha", "lte", hasta]], "fecha");
}

export async function catalogo(): Promise<ItemCatalogo[]> {
  return leer<ItemCatalogo>("equipo_catalogo", "id,clase,nombre", [["activo", "eq", "true"]], "orden");
}

// --- Escribir -----------------------------------------------------------------------

async function crear(tabla: string, fila: Libre) {
  const { data, error } = await base().from(tabla).insert(fila).select("id");
  if (error) throw new Error(mensaje(error));
  return data?.[0]?.id as string;
}

export const registrarObservacion = (f: {
  empresa_id: string; asesora_id: string; punto_id: string; tipo_observacion_id: string; texto: string;
  valoracion: "bien" | "a_mejorar" | "neutral"; fecha: string;
}) => crear("seguimiento", { ...f, tipo: "observacion" });

export const registrarCompromiso = (f: {
  empresa_id: string; asesora_id: string; punto_id: string; que: string; fecha_limite: string;
  prioridad: "alta" | "media" | "baja";
}) => crear("compromiso", f);

export async function avanzarCompromiso(id: string, valores: Partial<Pick<Compromiso, "estado" | "avance">>) {
  const { data, error } = await base().from("compromiso").update(valores).eq("id", id).select("id");
  if (error) throw new Error(mensaje(error));
  if (!data?.length) throw new Error("No se encontró, o su usuario no puede cambiarlo.");
}

// --- Cálculos -----------------------------------------------------------------------

export type Totales = { venta: number; facturas: number; ventaConFacturas: number; dias: number };

// El ticket promedio solo usa los días que traen facturas: si no, saldría inflado.
export function totales(filas: VentaDia[]): Totales {
  const t = { venta: 0, facturas: 0, ventaConFacturas: 0, dias: 0 };
  const dias = new Set<string>();
  for (const f of filas) {
    t.venta += f.venta;
    if (f.facturas != null) { t.facturas += Number(f.facturas); t.ventaConFacturas += f.venta; }
    dias.add(f.punto_id + f.fecha);
  }
  t.dias = dias.size;
  return t;
}

export const ticket = (t: Totales) => (t.facturas > 0 ? Math.round(t.ventaConFacturas / t.facturas) : null);

export function porPersona(filas: VentaDia[]): Map<string, Totales> {
  const grupos = new Map<string, VentaDia[]>();
  for (const f of filas) {
    if (!f.asesora_id) continue;
    grupos.set(f.asesora_id, [...(grupos.get(f.asesora_id) ?? []), f]);
  }
  return new Map([...grupos].map(([k, v]) => [k, totales(v)]));
}

// El período anterior de igual largo, pegado antes del actual.
export function anterior(desde: string, hasta: string): [string, string] {
  const largo = Math.round((Date.parse(hasta) - Date.parse(desde)) / 86400000) + 1;
  return [correrDias(desde, -largo), correrDias(desde, -1)];
}

export function mesDe(f: string): [string, string] {
  const [a, m] = f.split("-").map(Number);
  const fin = new Date(Date.UTC(a, m, 0)).getUTCDate();
  return [`${a}-${String(m).padStart(2, "0")}-01`, `${a}-${String(m).padStart(2, "0")}-${String(fin).padStart(2, "0")}`];
}

// La meta que corresponde a un período: la parte proporcional de cada meta que se cruza
// con él, por días. Así una meta de mes sirve para ver media quincena.
export function metaDelPeriodo(lista: Meta[], desde: string, hasta: string, filtro: (m: Meta) => boolean): number {
  let total = 0;
  for (const m of lista.filter(filtro)) {
    const ini = m.desde > desde ? m.desde : desde;
    const fin = m.hasta < hasta ? m.hasta : hasta;
    if (fin < ini) continue;
    const dias = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000) + 1;
    total += Math.round((m.monto * dias(ini, fin)) / dias(m.desde, m.hasta));
  }
  return total;
}

export const diasEntre = (a: string, b: string) => Math.round((Date.parse(b) - Date.parse(a)) / 86400000);

export const correrDiasHoy = (dias: number) => correrDias(hoy(), dias);
