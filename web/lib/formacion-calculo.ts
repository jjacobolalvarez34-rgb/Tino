// Cálculos de Formación, sin base de datos (los usa lib/formacion.ts y se prueban en
// formacion-calculo.test.ts). Las reglas están arriba de lib/formacion.ts.
import type { Indicador, RegistroVista } from "./formacion";

function correrDias(f: string, dias: number): string {
  const d = new Date(f + "T12:00:00Z");
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

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

