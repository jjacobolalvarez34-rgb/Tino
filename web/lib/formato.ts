// Números y fechas como en docs/DESIGN.md, secciones 9 y 10.
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DIAS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

export const miles = (n: number | null | undefined) => Math.abs(n ?? 0).toLocaleString("es-CO");
export const pesos = (n: number | null | undefined) => (n == null ? "" : (n < 0 ? "−" : "") + "$ " + miles(n));

// Todo se muestra en hora de Colombia, sin importar dónde esté el navegador ni que la base
// guarde las horas en UTC (un archivo subido el jueves a las 21:00 no es "viernes").
export const ZONA = "America/Bogota";

// El día (AAAA-MM-DD) en Bogotá de una fecha con hora.
export function diaBogota(t: string | Date): string {
  const d = typeof t === "string" ? new Date(t) : t;
  return new Intl.DateTimeFormat("en-CA", { timeZone: ZONA, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

export const hoyBogota = () => diaBogota(new Date());

export function horaBogota(t: string): string {
  return new Intl.DateTimeFormat("es-CO", { timeZone: ZONA, hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(new Date(t));
}

// "jue 19 nov · 21:40"
export const fechaHora = (t: string | null | undefined) => (t ? `${fecha(t)} · ${horaBogota(t)}` : "");

// Mes en minúscula, como se escribe en español: "octubre de 2026".
export function nombreMes(f: string, conAno = true): string {
  const [a, m] = f.slice(0, 7).split("-").map(Number);
  return MESES_LARGOS[m - 1] + (conAno ? ` de ${a}` : "");
}
const MESES_LARGOS = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
  "octubre", "noviembre", "diciembre"];

export function fecha(f: string | null | undefined): string {
  if (!f) return "";
  if (f.length > 10) f = diaBogota(f);
  const [a, m, d] = f.slice(0, 10).split("-").map(Number);
  return `${DIAS[new Date(Date.UTC(a, m - 1, d)).getUTCDay()]} ${d} ${MESES[m - 1]}`;
}

export function ayer(): string {
  return correrDias(hoyBogota(), -1);
}

export function correrDias(f: string, dias: number): string {
  const d = new Date(f + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

// "Copiar como números": enteros sin $ ni puntos, separados por tabulación.
export async function copiarComoNumeros(filas: (string | number)[][]): Promise<boolean> {
  const texto = filas.map((f) => f.join("\t")).join("\n");
  try {
    await navigator.clipboard.writeText(texto);
    return true;
  } catch {
    return false;
  }
}
