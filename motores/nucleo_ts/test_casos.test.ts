import assert from "node:assert";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { ejecutar } from "./logica.ts";

type Caso = { funcion: string; nombre: string; entrada: object; esperado: unknown };

const ruta = fileURLToPath(new URL("../../tests/casos/motor/casos.json", import.meta.url));
const casos = JSON.parse(readFileSync(ruta, "utf-8")) as Caso[];

for (const { funcion, nombre, entrada, esperado } of casos) {
  test(`${funcion}: ${nombre}`, () => {
    assert.deepStrictEqual(ejecutar(funcion, entrada), esperado);
  });
}
