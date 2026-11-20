"use client";
// Datos de la pantalla Caja: un día, todos los puntos. Solo las columnas que se muestran.
import { base, leer, mensaje } from "./supabase";

export type DiaPunto = {
  jornada_id: string | null; punto_id: string; punto: string; estado: "abierta" | "cerrada" | "conciliada" | "bloqueada" | null;
  venta: number | null; descuadre: number | null; estado_motor: string | null; causa: string | null;
  descuadre_estado: string | null; transf: { llegaron: number; no: number; confirmar: number; esperando: number };
  cierre: { accion: string; nota: string | null; descuadres_abiertos: number; creado_en: string } | null;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Libre = Record<string, any>;

export async function dia(fecha: string): Promise<DiaPunto[]> {
  const [puntos, jornadas, transf, causas] = await Promise.all([
    leer<Libre>("punto_venta", "id,codigo,nombre,tipo", [["activo", "eq", "true"]], "codigo"),
    leer<Libre>("v_jornada", "id,punto_id,estado,venta_teorica,descuadre,estado_motor,causa_codigo,descuadre_estado", [["fecha", "eq", fecha]], "punto_id"),
    leer<Libre>("v_transferencia", "punto_id,estado", [["fecha", "eq", fecha]], "punto_id"),
    leer<Libre>("causa_descuadre", "codigo,nombre", [], "codigo"),
  ]);
  const ids = jornadas.map((j) => j.id);
  const cierres = ids.length
    ? ((await base().from("v_jornada_cierre").select("jornada_id,accion,nota,descuadres_abiertos,creado_en").in("jornada_id", ids)).data ?? [])
    : [];
  const nombreCausa = new Map(causas.map((c) => [c.codigo, c.nombre]));
  return puntos.filter((p) => p.tipo !== "bodega").map((p) => {
    const j = jornadas.find((x) => x.punto_id === p.id);
    const t = transf.filter((x) => x.punto_id === p.id);
    const cierre = j ? cierres.find((c: Libre) => c.jornada_id === j.id) ?? null : null;
    return {
      jornada_id: j?.id ?? null, punto_id: p.id, punto: p.nombre, estado: j?.estado ?? null,
      venta: j?.venta_teorica ?? null, descuadre: j?.descuadre ?? null, estado_motor: j?.estado_motor ?? null,
      causa: j?.causa_codigo ? nombreCausa.get(j.causa_codigo) ?? j.causa_codigo : null,
      descuadre_estado: j?.descuadre_estado ?? null,
      transf: {
        llegaron: t.filter((x) => x.estado === "confirmada").length, no: t.filter((x) => x.estado === "sospechosa").length,
        confirmar: t.filter((x) => x.estado === "propuesta").length, esperando: t.filter((x) => x.estado === "pendiente").length,
      },
      cierre,
    };
  });
}

export async function cerrar(jornadas: string[]): Promise<number> {
  const { data, error } = await base().rpc("cerrar_dias", { p_jornadas: jornadas });
  if (error) throw new Error(mensaje(error));
  return Number(data) || 0;
}

export async function desbloquear(jornada: string, nota: string) {
  const { error } = await base().rpc("desbloquear_dia", { p_jornada: jornada, p_nota: nota });
  if (error) throw new Error(error.code === "23514" ? "Escriba por qué se desbloquea." : mensaje(error));
}
