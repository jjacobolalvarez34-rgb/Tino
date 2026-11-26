// Formación y desempeño (0015): el registro del día de cada persona, los indicadores de la
// empresa, las etapas del ciclo y los cálculos de "Cómo van".
//
// Reglas de los cálculos (docs/REGLAS/equipo.md, "Formación"):
//   * Un día sin registro no es cero: no entra en ninguna cuenta.
//   * Conversión = facturas ÷ clientes atendidos, solo en los días que tienen registro y
//     facturas de esa persona (si el Excel de ese día no trae su venta, ese día no entra).
//   * Indicador sobre atendidos: valor ÷ clientes atendidos. Sobre facturas: valor ÷ facturas
//     (de los mismos días). De conteo: se suma.
//   * Si un día lo compartieron varias personas, las facturas se reparten por partes iguales: la
//     conversión de cada una ese día es aproximada. Se cuenta y se avisa.
import { base, leer, mensaje } from "./supabase";
import { correrDias, hoyBogota } from "./formato";

export type Indicador = { id: string; nombre: string; base: "atendidos" | "facturas" | "conteo"; orden: number; activo: boolean };
export type Etapa = { id: string; nombre: string; orden: number; activo: boolean };
export type Paso = { asesora_id: string; etapa_id: string; desde: string };
export type HistoriaPaso = { id: string; asesora_id: string; etapa_id: string; desde: string; nota: string | null; creado_en: string };
export type RegistroVista = {
  id: string; asesora_id: string; punto_id: string; fecha: string; origen: "manual" | "integracion";
  clientes_atendidos: number; valores: Record<string, number>; hay_otro_origen: boolean;
  facturas: number | null; personas_dia: number | null;
};
export type RegistroGuardado = {
  id: string; asesora_id: string; punto_id: string; fecha: string; origen: "manual" | "integracion"; fuente: string | null;
  clientes_atendidos: number; nota_correccion: string | null; valores: Record<string, number>;
};

export async function indicadores(todos = false): Promise<Indicador[]> {
  return leer<Indicador>("indicador_dia", "id,nombre,base,orden,activo", todos ? [] : [["activo", "eq", "true"]], "orden");
}

export async function etapas(): Promise<Etapa[]> {
  return leer<Etapa>("equipo_catalogo", "id,nombre,orden,activo", [["clase", "eq", "etapa"], ["activo", "eq", "true"]], "orden");
}

export async function pasos(): Promise<Paso[]> {
  return leer<Paso>("v_asesora_etapa", "asesora_id,etapa_id,desde", [], "asesora_id");
}

export async function historiaPasos(persona: string): Promise<HistoriaPaso[]> {
  return leer<HistoriaPaso>("asesora_etapa", "id,asesora_id,etapa_id,desde,nota,creado_en", [["asesora_id", "eq", persona]], "creado_en.desc");
}

export async function cambiarPaso(f: { empresa_id: string; asesora_id: string; etapa_id: string; nota?: string }) {
  const { data: u } = await base().auth.getUser();
  const { error } = await base().from("asesora_etapa").insert({ ...f, nota: f.nota?.trim() || null, autor_id: u.user?.id });
  if (error) throw new Error(mensaje(error));
}

// Lo que cuenta de cada día (manual primero) entre dos fechas, opcionalmente de una persona.
export async function registros(desde: string, hasta: string, persona?: string): Promise<RegistroVista[]> {
  const filtros: [string, "gte" | "lte" | "eq", string][] = [["fecha", "gte", desde], ["fecha", "lte", hasta]];
  if (persona) filtros.push(["asesora_id", "eq", persona]);
  return leer<RegistroVista>("v_registro_dia",
    "id,asesora_id,punto_id,fecha,origen,clientes_atendidos,valores,hay_otro_origen,facturas,personas_dia", filtros, "fecha");
}

// Los registros guardados de un punto y día, de los dos orígenes: para llenar o corregir.
export async function registrosDelDia(punto: string, dia: string): Promise<RegistroGuardado[]> {
  const filas = await leer<Omit<RegistroGuardado, "valores">>("registro_dia",
    "id,asesora_id,punto_id,fecha,origen,fuente,clientes_atendidos,nota_correccion",
    [["punto_id", "eq", punto], ["fecha", "eq", dia], ["anulado", "eq", "false"]], "creado_en");
  if (!filas.length) return [];
  const { data, error } = await base().from("registro_dia_valor").select("registro_id,indicador_id,valor")
    .in("registro_id", filas.map((f) => f.id));
  if (error) throw new Error(mensaje(error));
  return filas.map((f) => ({
    ...f,
    valores: Object.fromEntries((data ?? []).filter((v) => v.registro_id === f.id).map((v) => [v.indicador_id, v.valor])),
  }));
}

export type FilaRegistro = { asesora_id: string; clientes_atendidos: number; valores: Record<string, number> };

export async function guardarRegistros(punto: string, dia: string, filas: FilaRegistro[], nota?: string): Promise<number> {
  const { data, error } = await base().rpc("guardar_registros_dia", {
    p: { punto_id: punto, fecha: dia, nota: nota?.trim() || null, filas },
  });
  if (error) throw new Error(mensaje(error));
  return Number(data) || 0;
}

export async function usarPlantilla(): Promise<number> {
  const { data, error } = await base().rpc("usar_plantilla_formacion");
  if (error) throw new Error(mensaje(error));
  return Number((data as { agregados?: number })?.agregados ?? 0);
}

// ---------------------------------------------------------------------------------
// Cálculos
// ---------------------------------------------------------------------------------

export type Resultado = {
  dias: number;                 // días-persona con registro
  atendidos: number;
  facturas: number;             // de los días con registro y con venta de esa persona
  atendidosConVenta: number;    // atendidos de esos mismos días
  conversion: number | null;    // %
  compartidos: number;          // días con registro que la venta se repartió entre varias
  porIndicador: Map<string, { valor: number; porcentaje: number | null }>;
};

export function calcular(filas: RegistroVista[], lista: Indicador[]): Resultado {
  let atendidos = 0, facturas = 0, atendidosConVenta = 0, compartidos = 0;
  const suma = new Map<string, number>();
  const sumaConVenta = new Map<string, number>();
  for (const r of filas) {
    atendidos += r.clientes_atendidos;
    const conVenta = r.facturas != null;
    if (conVenta) {
      facturas += Number(r.facturas);
      atendidosConVenta += r.clientes_atendidos;
      if ((r.personas_dia ?? 1) > 1) compartidos += 1;
    }
    for (const [id, v] of Object.entries(r.valores ?? {})) {
      suma.set(id, (suma.get(id) ?? 0) + Number(v));
      if (conVenta) sumaConVenta.set(id, (sumaConVenta.get(id) ?? 0) + Number(v));
    }
  }
  const pct = (a: number, b: number) => (b > 0 ? (a / b) * 100 : null);
  const porIndicador = new Map<string, { valor: number; porcentaje: number | null }>();
  for (const i of lista) {
    const valor = suma.get(i.id) ?? 0;
    porIndicador.set(i.id, {
      valor,
      porcentaje: i.base === "atendidos" ? pct(valor, atendidos)
        : i.base === "facturas" ? pct(sumaConVenta.get(i.id) ?? 0, facturas) : null,
    });
  }
  return { dias: filas.length, atendidos, facturas, atendidosConVenta, conversion: pct(facturas, atendidosConVenta), compartidos, porIndicador };
}

// Diferencia frente al período anterior: en puntos para porcentajes, en % para cantidades.
export function diferencia(ahora: number | null, antes: number | null, esPorcentaje: boolean): { texto: string; signo: number } | null {
  if (ahora == null || antes == null) return null;
  if (esPorcentaje) {
    const d = Math.round(ahora - antes);
    return { texto: d === 0 ? "Igual" : `${d > 0 ? "▲" : "▼"} ${Math.abs(d)} punto${Math.abs(d) === 1 ? "" : "s"}`, signo: Math.sign(d) };
  }
  if (antes === 0) return null;
  const d = Math.round(((ahora - antes) / antes) * 100);
  return { texto: d === 0 ? "Igual" : `${d > 0 ? "▲" : "▼"} ${Math.abs(d)} %`, signo: Math.sign(d) };
}

// Semana de lunes a domingo que contiene una fecha.
export function semanaDe(f: string): [string, string] {
  const d = new Date(f + "T12:00:00Z").getUTCDay();          // 0 = domingo
  const lunes = correrDias(f, d === 0 ? -6 : 1 - d);
  return [lunes, correrDias(lunes, 6)];
}

export const hoy = () => hoyBogota();
