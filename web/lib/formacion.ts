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
import { hoyBogota } from "./formato";

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

// Los cálculos viven aparte (sin base de datos) para probarlos solos: formacion-calculo.test.ts.
export { calcular, diferencia, semanaDe, type Resultado } from "./formacion-calculo";

export const hoy = () => hoyBogota();
