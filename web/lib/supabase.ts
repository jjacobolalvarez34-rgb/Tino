"use client";
// Cliente de Supabase con la sesión de quien entra. RLS decide qué ve y qué cambia,
// igual que en el programa de escritorio. La llave de servicio nunca llega aquí.
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let cliente: SupabaseClient | null = null;

export function base(): SupabaseClient {
  if (cliente) return cliente;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const llave = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !llave) {
    throw new Error("Faltan NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY (ver web/.env.example).");
  }
  cliente = createClient(url, llave, { auth: { persistSession: true, autoRefreshToken: true } });
  return cliente;
}

// Lo que la base responde, dicho para una persona (mismos códigos que el programa).
const MENSAJES: Record<string, string> = {
  "23505": "Eso ya estaba: no se repite.",
  "23503": "Hay un dato que apunta a algo que no existe o es de otra empresa.",
  "23514": "Hay un dato que no cumple las reglas.",
  "42501": "Su usuario no tiene permiso para esto.",
  P0002: "No se encontró, o ya se había hecho.",
};

const SIN_PREPARAR = "Esta parte de Tino todavía no está lista en la base de datos. Avísele a soporte.";
const GENERICO = "Algo salió mal. Intente de nuevo; si sigue pasando, avísele a soporte.";
Object.assign(MENSAJES, {
  PGRST205: SIN_PREPARAR, PGRST202: SIN_PREPARAR, "42P01": SIN_PREPARAR, "42883": SIN_PREPARAR, "42703": SIN_PREPARAR,
  "23P01": "Se cruza con otro registro de las mismas fechas.",
  PGRST301: "Su sesión venció. Vuelva a entrar.", "401": "Su sesión venció. Vuelva a entrar.",
});

// Los mensajes que escribe Tino (en la base o en la web) están en español y se muestran tal cual.
// Los que vienen en inglés (de Postgres, de Supabase o del navegador) no se le muestran a nadie:
// se cambian por uno sencillo y el detalle queda en el registro (la consola del navegador).
const INGLES = /\b(the|could not|couldn't|violates|permission denied|not found|schema cache|failed to fetch|network|relation|column|function|invalid|unexpected|does not exist|duplicate|unauthorized|forbidden|timeout|error)\b/i;

function registrar(origen: string, detalle: unknown) {
  // eslint-disable-next-line no-console
  console.error("[Tino]", origen, detalle);
}

export function mensaje(error: { code?: string; message?: string; details?: string } | null): string {
  if (!error) return "";
  const propio = error.message && !INGLES.test(error.message) ? error.message : null;
  if (!propio) registrar(error.code ?? "sin código", error);
  return (error.code && MENSAJES[error.code]) || propio || GENERICO;
}

// Para los catch: cualquier error, dicho en español sencillo.
export function textoDeError(e: unknown): string {
  const m = e instanceof Error ? e.message : String(e ?? "");
  if (/failed to fetch|networkerror|load failed/i.test(m)) {
    registrar("red", e);
    return "No hay conexión. Revise el internet e intente de nuevo.";
  }
  if (!m || INGLES.test(m)) {
    registrar("error", e);
    return GENERICO;
  }
  return m;
}

type Filtro = [columna: string, operador: "eq" | "gte" | "lte" | "is", valor: string | null];

// Todas las filas que RLS deja ver, de a 1000 (el máximo de Supabase por consulta).
export async function leer<T>(tabla: string, columnas: string, filtros: Filtro[] = [], orden = "id"): Promise<T[]> {
  const filas: T[] = [];
  for (let desde = 0; ; desde += 1000) {
    let q = base().from(tabla).select(columnas).order(orden.replace(/\.desc$/, ""), { ascending: !orden.endsWith(".desc") });
    for (const [col, op, valor] of filtros) {
      if (op === "is") q = q.is(col, null);
      else q = q[op](col, valor as string);
    }
    const { data, error } = await q.range(desde, desde + 999);
    if (error) throw new Error(mensaje(error));
    filas.push(...((data ?? []) as T[]));
    if (!data || data.length < 1000) return filas;
  }
}
