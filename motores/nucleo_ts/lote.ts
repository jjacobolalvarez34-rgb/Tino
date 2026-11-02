// Corre una lista de llamadas: lote.ts entrada.json salida.json
import { readFileSync, writeFileSync } from "node:fs";
import { ejecutar } from "./logica.ts";

type Llamada = { funcion: string; entrada: object };

function correr(llamada: Llamada): unknown {
  try {
    return ejecutar(llamada.funcion, llamada.entrada);
  } catch (error) {
    return { error: error instanceof Error ? error.message : String(error) };
  }
}

const [ruta_entrada, ruta_salida] = process.argv.slice(2);
if (ruta_entrada === undefined || ruta_salida === undefined) {
  console.error("Uso: node --experimental-strip-types lote.ts entrada.json salida.json");
  process.exit(2);
}

const llamadas = JSON.parse(readFileSync(ruta_entrada, "utf-8")) as Llamada[];
writeFileSync(ruta_salida, JSON.stringify(llamadas.map(correr)), "utf-8");
