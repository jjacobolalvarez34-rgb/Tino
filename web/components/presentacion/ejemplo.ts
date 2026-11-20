// Datos de ejemplo de la página de presentación. Todo es INVENTADO: puntos, personas y
// montos. Nunca se ponen aquí nombres ni cifras de un cliente real.

// "$ 1.510.000": punto de miles, sin decimales. Se arma a mano (sin Intl) para que el
// servidor y el navegador escriban exactamente lo mismo.
export function miles(n: number): string {
  return Math.abs(Math.round(n)).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export type Formato = "pesos" | "entero" | "porcentaje";

export function formatear(n: number, formato: Formato): string {
  const signo = n < 0 ? "−" : "";
  if (formato === "pesos") return `${signo}$ ${miles(n)}`;
  if (formato === "porcentaje") return `${signo}${miles(n)} %`;
  return signo + miles(n);
}

export type Estado = "ok" | "revisar" | "mal" | "espera" | "neutro";

// Cierre del día de la portada. Total = efectivo + tarjeta + transferencia.
export const CIERRE = {
  fecha: "Sábado 14 nov",
  revisado: "21:40",
  puntos: [
    { punto: "Punto Centro", efectivo: 1_900_000, tarjeta: 2_100_000, transferencia: 820_000, descuadre: 0, estado: "ok" as Estado, chip: "Cuadrado" },
    { punto: "Punto Norte", efectivo: 1_250_000, tarjeta: 1_400_000, transferencia: 500_000, descuadre: 0, estado: "ok" as Estado, chip: "Cuadrado" },
    { punto: "Punto Plaza", efectivo: 960_000, tarjeta: 1_080_000, transferencia: 420_000, descuadre: -85_000, estado: "mal" as Estado, chip: "Descuadre" },
    { punto: "Punto Estación", efectivo: 780_000, tarjeta: 900_000, transferencia: 300_000, descuadre: 0, estado: "revisar" as Estado, chip: "Revisar" },
  ],
};

export const totalPunto = (p: (typeof CIERRE.puntos)[number]) => p.efectivo + p.tarjeta + p.transferencia;
export const sumar = (campo: "efectivo" | "tarjeta" | "transferencia" | "descuadre") =>
  CIERRE.puntos.reduce((s, p) => s + p[campo], 0);
export const TOTAL_DIA = CIERRE.puntos.reduce((s, p) => s + totalPunto(p), 0);

// Lo que entrega "Copiar como números": enteros sin $ ni puntos, separados por tabulación.
export function comoNumeros(): string {
  const filas = [["Punto", "Efectivo", "Tarjeta", "Transferencia", "Total", "Descuadre"].join("\t")];
  for (const p of CIERRE.puntos) {
    filas.push([p.punto, p.efectivo, p.tarjeta, p.transferencia, totalPunto(p), p.descuadre].join("\t"));
  }
  filas.push(["Total", sumar("efectivo"), sumar("tarjeta"), sumar("transferencia"), TOTAL_DIA, sumar("descuadre")].join("\t"));
  return filas.join("\n");
}

// Pagos que se concilian solos en la sección de conciliación (una muestra del sábado).
export const PAGOS = [
  { hora: "09:12", medio: "Tarjeta · Bold", monto: 64_000, estado: "ok" as Estado, chip: "Verificada", prueba: "Bold, mismo valor y hora" },
  { hora: "11:30", medio: "Transferencia", monto: 120_000, estado: "ok" as Estado, chip: "Verificada", prueba: "Aviso del banco, 11:31" },
  { hora: "13:05", medio: "Tarjeta · Redeban", monto: 210_000, estado: "ok" as Estado, chip: "Verificada", prueba: "Redeban, lote del día" },
  { hora: "14:20", medio: "Consignación", monto: 900_000, estado: "ok" as Estado, chip: "Verificada", prueba: "Extracto del banco" },
  { hora: "15:40", medio: "Transferencia", monto: 85_000, estado: "mal" as Estado, chip: "Sospechosa", prueba: "El banco no la muestra ni hoy ni mañana" },
  { hora: "17:55", medio: "Transferencia", monto: 150_000, estado: "revisar" as Estado, chip: "Propuesta", prueba: "Llegó al día siguiente. La confirma usted" },
];

// Cifras del día de ejemplo: 137 + 4 + 1 = 142.
export const RESUMEN_PAGOS = { total: 142, solos: 137, propuestas: 4, sospechosas: 1 };

// Equipo: ranking del mes hasta el 14 de noviembre.
export const EQUIPO = [
  { nombre: "Laura", punto: "Punto Centro", ventas: 18_400_000, ticket: 68_000, meta: 104 },
  { nombre: "Andrés", punto: "Punto Norte", ventas: 15_900_000, ticket: 59_000, meta: 93 },
  { nombre: "Camila", punto: "Punto Plaza", ventas: 12_700_000, ticket: 71_000, meta: 85 },
  { nombre: "Felipe", punto: "Punto Estación", ventas: 9_800_000, ticket: 52_000, meta: 77 },
];
