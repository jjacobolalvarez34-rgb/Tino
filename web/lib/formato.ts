// Números y fechas como en docs/DESIGN.md, secciones 9 y 10.
const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const DIAS = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"];

export const miles = (n: number | null | undefined) => Math.abs(n ?? 0).toLocaleString("es-CO");
export const pesos = (n: number | null | undefined) => (n == null ? "" : (n < 0 ? "−" : "") + "$ " + miles(n));

export function fecha(f: string | null | undefined): string {
  if (!f) return "";
  const [a, m, d] = f.slice(0, 10).split("-").map(Number);
  return `${DIAS[new Date(Date.UTC(a, m - 1, d)).getUTCDay()]} ${d} ${MESES[m - 1]}`;
}

export function ayer(): string {
  const d = new Date();
  d.setDate(d.getDate() - 1);
  return d.toISOString().slice(0, 10);
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
