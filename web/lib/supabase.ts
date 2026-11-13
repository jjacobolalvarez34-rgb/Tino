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

export function mensaje(error: { code?: string; message?: string } | null): string {
  if (!error) return "";
  return (error.code && MENSAJES[error.code]) || error.message || "Algo salió mal.";
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
