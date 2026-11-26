// Pruebas de los cálculos de Formación, con números escritos a mano (datos inventados).
// Uso, desde web/: node --experimental-strip-types --test lib/formacion-calculo.test.ts
import { test } from "node:test";
import assert from "node:assert/strict";
import { calcular, diferencia, semanaDe } from "./formacion-calculo.ts";

const IND = [
  { id: "exp", nombre: "Explicó el programa", base: "atendidos" as const, orden: 1, activo: true },
  { id: "con", nombre: "Consultó puntos", base: "facturas" as const, orden: 2, activo: true },
  { id: "ref", nombre: "Referidos", base: "conteo" as const, orden: 3, activo: true },
];
const fila = (fecha: string, atendidos: number, valores: Record<string, number>, facturas: number | null, personas = 1) => ({
  id: fecha, asesora_id: "a", punto_id: "p", fecha, origen: "manual" as const, clientes_atendidos: atendidos, valores,
  hay_otro_origen: false, facturas, personas_dia: facturas == null ? null : personas,
});

test("conversión y porcentajes con dos días", () => {
  // Día 1: 20 atendidos, 10 facturas, explicó 8, consultó 5, 2 referidos. Día 2: 30, 12, 9, 6, 1.
  const r = calcular([fila("2026-11-02", 20, { exp: 8, con: 5, ref: 2 }, 10), fila("2026-11-03", 30, { exp: 9, con: 6, ref: 1 }, 12)], IND);
  assert.equal(r.dias, 2);
  assert.equal(r.atendidos, 50);
  assert.equal(r.conversion, (22 / 50) * 100);            // 44 %
  assert.equal(r.porIndicador.get("exp")!.porcentaje, (17 / 50) * 100);   // 34 %
  assert.equal(r.porIndicador.get("con")!.porcentaje, (11 / 22) * 100);   // 50 %
  assert.equal(r.porIndicador.get("ref")!.valor, 3);
  assert.equal(r.porIndicador.get("ref")!.porcentaje, null);
});

test("un día sin registro no cuenta como cero", () => {
  const conUno = calcular([fila("2026-11-02", 20, { exp: 10 }, 10)], IND);
  assert.equal(conUno.conversion, 50);
  assert.equal(conUno.porIndicador.get("exp")!.porcentaje, 50);
  assert.equal(calcular([], IND).conversion, null);       // sin registros: sin dato, no 0 %
});

test("un día sin venta cargada no entra en la conversión ni en lo que va sobre facturas", () => {
  const r = calcular([fila("2026-11-02", 20, { exp: 10, con: 5 }, 10), fila("2026-11-03", 40, { exp: 10, con: 9 }, null)], IND);
  assert.equal(r.conversion, 50);                          // 10 ÷ 20: el segundo día no tiene facturas
  assert.equal(r.porIndicador.get("exp")!.porcentaje, (20 / 60) * 100);   // sobre atendidos sí cuentan los dos
  assert.equal(r.porIndicador.get("con")!.porcentaje, 50); // 5 ÷ 10
});

test("los días compartidos (2, 3 o 4 personas) se cuentan para avisar", () => {
  const r = calcular([fila("2026-11-02", 10, {}, 2.5, 4), fila("2026-11-03", 10, {}, 3.33, 3), fila("2026-11-04", 10, {}, 5, 1)], IND);
  assert.equal(r.compartidos, 2);
});

test("diferencia: puntos para porcentajes, % para cantidades", () => {
  assert.deepEqual(diferencia(54, 48, true), { texto: "▲ 6 puntos", signo: 1 });
  assert.deepEqual(diferencia(30, 40, false), { texto: "▼ 25 %", signo: -1 });
  assert.equal(diferencia(10, 0, false), null);
  assert.equal(diferencia(null, 40, true), null);
});

test("la semana va de lunes a domingo", () => {
  assert.deepEqual(semanaDe("2026-11-26"), ["2026-11-23", "2026-11-29"]);   // jueves
  assert.deepEqual(semanaDe("2026-11-29"), ["2026-11-23", "2026-11-29"]);   // domingo
});
