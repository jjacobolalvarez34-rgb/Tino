// Exige que web/lib/revision.ts dé lo mismo que Python con las mismas filas.
// Uso: node --experimental-strip-types tests/web/comparar_revision.ts <volcado.json de volcar_revision.py>
import { readFileSync } from "node:fs";
import { armar, paraGuardar, revisar } from "../../web/lib/revision.ts";

const v = JSON.parse(readFileSync(process.argv[2], "utf8"));
const { excel, banco, tarjetas } = armar(v.filas, v.nombre);

// Mismo orden de llaves en los dos lados para comparar texto con texto.
const canonico = (x: unknown): unknown =>
  Array.isArray(x) ? x.map(canonico)
    : x && typeof x === "object" ? Object.fromEntries(Object.keys(x).sort().map((k) => [k, canonico((x as Record<string, unknown>)[k])]))
      : x;

let distintos = 0;
for (const d of v.dias) {
  const r = revisar(d.fecha, excel, banco, tarjetas, v.config);
  const g = paraGuardar(r, excel);
  const a = JSON.stringify(canonico({ r, g }));
  const b = JSON.stringify(canonico({ r: d.revision, g: d.guardar }));
  if (a !== b) {
    distintos++;
    if (distintos <= 2) {
      let i = 0;
      while (a[i] === b[i]) i++;
      console.log(`distinto ${d.fecha}:\n  TS: ${a.slice(Math.max(0, i - 120), i + 120)}\n  PY: ${b.slice(Math.max(0, i - 120), i + 120)}`);
    }
  }
}
console.log(`${v.dias.length} días comparados, ${distintos} distintos`);
process.exit(distintos ? 1 : 0);
