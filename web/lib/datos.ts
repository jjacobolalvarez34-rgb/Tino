"use client";
// Lo que hacen las pantallas web: lo mismo que panel/servicio.py del programa de escritorio,
// con la sesión de quien entra.
import { base, leer, mensaje } from "./supabase";
import { armar, dias, extractosPorFecha, paraGuardar, revisar, type Config } from "./revision";
import { correrDias } from "./formato";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Libre = Record<string, any>;

async function rpc(funcion: string, argumentos: Libre) {
  const { data, error } = await base().rpc(funcion, argumentos);
  if (error) throw new Error(mensaje(error));
  return data;
}

async function cambiar(tabla: string, id: string, valores: Libre) {
  const { data, error } = await base().from(tabla).update(valores).eq("id", id).select();
  if (error) throw new Error(mensaje(error));
  if (!data?.length) throw new Error("No se encontró, o su usuario no puede cambiarlo.");
  return data[0];
}

// Puntos con nombre para mostrar; si dos se llaman igual, llevan su código.
export async function puntos(): Promise<Record<string, string>> {
  const filas = await leer<Libre>("punto_venta", "id,codigo,nombre", [["activo", "eq", "true"]], "codigo");
  const repetidos = new Set(filas.map((p) => p.nombre).filter((n, i, a) => a.indexOf(n) !== i));
  return Object.fromEntries(filas.map((p) => [p.id, repetidos.has(p.nombre) ? `${p.nombre} (${p.codigo})` : p.nombre]));
}

async function config(): Promise<Config> {
  const [c] = await leer<Libre>("empresa_config", "*", [], "empresa_id");
  return {
    tolerancia_cuadra: c.desc_umbral, porcentaje_explicado: c.desc_porcentaje_explicado, reglas_sin_peso: c.desc_reglas_sin_peso,
    compensacion: { monto_minimo: c.desc_comp_minimo, tolerancia: c.desc_comp_tolerancia, porcentaje: c.desc_comp_porcentaje },
    billete: { denominaciones: c.desc_billetes, max_billetes: c.desc_max_billetes },
    precios: { monto_minimo: c.desc_precios_minimo, max_productos: c.desc_precios_max_productos, max_mostradas: c.desc_precios_mostradas },
  };
}

// Corre la revisión de cada día del rango y la guarda (igual que el programa).
export async function revisarRango(desde: string, hasta: string): Promise<number> {
  const d0 = correrDias(desde, -7), d1 = correrDias(hasta, 7);
  const rango: [string, "gte" | "lte", string][] = [["fecha", "gte", d0], ["fecha", "lte", d1]];
  const [nombre, cfg, jornadas, reportes, pagos, detalle, movs, archivos] = await Promise.all([
    puntos(), config(),
    leer<Libre>("v_jornada", "id,punto_id,fecha,reporte_id,venta_teorica,descuadre_reportado,asesoras_texto", rango),
    leer<Libre>("v_reporte_vigente", "jornada_id,archivo_id", [], "jornada_id"),
    leer<Libre>("v_pago_vigente", "id,jornada_id,medio_tipo,monto,archivo_id,fila_origen", rango),
    leer<Libre>("v_detalle_vigente", "id,jornada_id,texto_producto,cantidad,precio_lista,archivo_id", rango),
    leer<Libre>("v_movimiento_vigente", "id,archivo_id,fuente,tipo,fecha,punto_id,bruto,prestamo,referencia,descripcion,etiqueta,fila_origen", rango),
    leer<Libre>("archivo_importado", "id,fuente,desde,hasta,creado_en", [["estado", "eq", "cargado"]]),
  ]);
  const { excel, banco, tarjetas } = armar({ jornadas, reportes, pagos, detalle, movs, archivos }, nombre);
  let n = 0;
  for (const f of dias(desde, hasta)) {
    const r = revisar(f, excel, banco, tarjetas, cfg);
    if ((r.puntos as Libre[]).some((p) => !p.sin_excel)) {
      await rpc("guardar_revision", { p: paraGuardar(r, excel) });
      n++;
    }
  }
  return n;
}

export async function resumen(desde: string, hasta: string) {
  const [nombre, trans, desc, sin] = await Promise.all([
    puntos(),
    leer<Libre>("v_transferencia", "estado,monto", [["fecha", "gte", desde], ["fecha", "lte", hasta]], "fecha"),
    leer<Libre>("v_jornada", "punto_id,fecha,descuadre,estado_motor,descuadre_estado,causa_codigo", [["fecha", "gte", desde], ["fecha", "lte", hasta]], "fecha"),
    sinOrigen(desde, hasta),
  ]);
  return {
    noLlegaron: trans.filter((t) => t.estado === "sospechosa"),
    porConfirmar: trans.filter((t) => t.estado === "propuesta").length,
    sinCausa: desc.filter((d) => d.estado_motor === "sin_explicar" && d.descuadre_estado === "abierto")
      .map((d): Libre => ({ ...d, punto: nombre[d.punto_id] ?? "" })),
    sinOrigen: sin.pendientes.length,
  };
}

export async function transferencias(desde: string, hasta: string) {
  const [nombre, filas] = await Promise.all([puntos(),
    leer<Libre>("v_transferencia", "pago_id,punto_id,fecha,monto,fila_origen,estado,fecha_banco,referencia,nota", [["fecha", "gte", desde], ["fecha", "lte", hasta]], "fecha")]);
  const orden: Record<string, number> = { sospechosa: 0, propuesta: 1, pendiente: 2, confirmada: 3, rechazada: 4 };
  return filas.map((f): Libre => ({ ...f, punto: nombre[f.punto_id] ?? "" }))
    .sort((a, b) => (orden[a.estado] - orden[b.estado]) || a.fecha.localeCompare(b.fecha) || a.punto.localeCompare(b.punto));
}

export async function decidirTransferencia(pagoId: string, estado: "confirmada" | "rechazada", nota: string) {
  if (!nota.trim()) throw new Error("Para decidir hace falta una nota.");
  const actual = await leer<Libre>("verificacion_transferencia", "id,extracto_id", [["pago_id", "eq", pagoId]]);
  if (estado === "confirmada" && !actual[0]?.extracto_id) throw new Error("Nada se confirma sin el extracto.");
  if (!actual.length) {
    const yo = await leer<Libre>("empresa_config", "empresa_id", [], "empresa_id");
    const { error } = await base().from("verificacion_transferencia").insert({ empresa_id: yo[0].empresa_id, pago_id: pagoId, estado: "pendiente" });
    if (error) throw new Error(mensaje(error));
  }
  const { error } = await base().from("verificacion_transferencia").update({ estado, nota }).eq("pago_id", pagoId);
  if (error) throw new Error(mensaje(error));
}

async function transferenciasBanco(desde: string, hasta: string) {
  const archivos = await leer<Libre>("archivo_importado", "id,fuente,desde,hasta,creado_en", [["fuente", "eq", "banco"], ["estado", "eq", "cargado"]], "creado_en");
  const duenio = extractosPorFecha(archivos);
  const movs = await leer<Libre>("v_movimiento_vigente", "id,archivo_id,fecha,punto_id,referencia,descripcion,etiqueta,bruto,nota",
    [["fecha", "gte", desde], ["fecha", "lte", hasta], ["tipo", "eq", "transferencia"], ["fuente", "eq", "banco"]], "fecha");
  return movs.filter((m) => duenio.get(m.fecha) === m.archivo_id);
}

export async function sinOrigen(desde: string, hasta: string) {
  const [nombre, movs, anotadas] = await Promise.all([puntos(), transferenciasBanco(desde, hasta),
    leer<Libre>("v_transferencia", "pago_id,punto_id,fecha,monto,estado", [["fecha", "gte", correrDias(desde, -1)], ["fecha", "lte", correrDias(hasta, 1)]], "fecha")]);
  const cerca = (a: string, b: string) => Math.abs(Date.parse(a) - Date.parse(b)) <= 86_400_000;
  const pendientes: Libre[] = [], asignados: Libre[] = [];
  for (const m of movs) {
    const fila = { id: m.id, fecha: m.fecha, descripcion: m.descripcion, etiqueta: m.etiqueta, valor: m.bruto,
      punto: m.punto_id ? nombre[m.punto_id] : null, punto_id: m.punto_id, nota: m.nota };
    if (m.punto_id === null) {
      pendientes.push({ ...fila, sugerencias: anotadas.filter((t) => t.estado === "sospechosa" && t.monto === m.bruto && cerca(t.fecha, m.fecha))
        .map((t) => ({ punto: nombre[t.punto_id], punto_id: t.punto_id, fecha: t.fecha })) });
    } else if (m.nota) asignados.push(fila);
  }
  const senales: Libre[] = [];
  for (const fecha of [...new Set(pendientes.map((p) => p.fecha))].sort()) {
    const delDia = anotadas.filter((t) => t.fecha === fecha);
    for (const pid of [...new Set(delDia.map((t) => t.punto_id))].sort()) {
      const suyas = delDia.filter((t) => t.punto_id === pid);
      if (suyas.length && suyas.every((t) => t.estado === "sospechosa" || t.estado === "pendiente")) {
        senales.push({ fecha, punto: nombre[pid], anotadas: suyas.length });
      }
    }
  }
  return { pendientes, asignados, senales, puntos: Object.entries(nombre).map(([id, n]) => ({ id, nombre: n })).sort((a, b) => a.nombre.localeCompare(b.nombre)) };
}

export async function asignar(movId: string, puntoId: string | null, nota: string) {
  if (!nota.trim()) throw new Error("Para asignar un pago hace falta una nota.");
  const m = await cambiar("movimiento_externo", movId, { punto_id: puntoId, nota });
  await revisarRango(correrDias(m.fecha, -1), correrDias(m.fecha, 1));
}

export async function porConfirmar() {
  const [nombre, filas] = await Promise.all([puntos(), leer<Libre>("v_cruce",
    "id,tipo,punto_id,fecha_anotada,monto_anotado,medio_tipo,fila_origen,fuente,fecha_externa,monto_externo,referencia", [["estado", "eq", "propuesta"]], "fecha_anotada")]);
  return filas.map((f): Libre => ({ ...f, punto: nombre[f.punto_id] ?? "" }));
}

export async function decidirCruce(id: string, estado: "confirmada" | "rechazada", nota: string) {
  if (!nota.trim()) throw new Error("Para decidir hace falta una nota.");
  await cambiar("conciliacion", id, { estado, nota });
}

export async function descuadres(desde: string, hasta: string) {
  const [nombre, filas, causas] = await Promise.all([puntos(),
    leer<Libre>("v_jornada", "id,punto_id,fecha,descuadre_id,descuadre,explicado,sin_explicar,estado_motor,causa_codigo,descuadre_estado,descuadre_nota,asesoras_texto", [["fecha", "gte", desde], ["fecha", "lte", hasta]], "fecha"),
    leer<Libre>("causa_descuadre", "codigo,nombre", [], "codigo")]);
  const causa = Object.fromEntries(causas.map((c) => [c.codigo, c.nombre]));
  const orden: Record<string, number> = { sin_explicar: 0, explicado: 1, cuadra: 2 };
  return filas.filter((f) => f.descuadre_id).map((f): Libre => ({ ...f, punto: nombre[f.punto_id] ?? "", causa: causa[f.causa_codigo] ?? "" }))
    .sort((a, b) => Number(a.descuadre_estado !== "abierto") - Number(b.descuadre_estado !== "abierto") || orden[a.estado_motor] - orden[b.estado_motor] || a.fecha.localeCompare(b.fecha));
}

export async function pruebas(descuadreId: string) {
  const [filas, causas] = await Promise.all([
    leer<Libre>("descuadre_evidencia", "causa_codigo,tipo,monto,total", [["descuadre_id", "eq", descuadreId], ["vigente", "eq", "true"]], "tipo"),
    leer<Libre>("causa_descuadre", "codigo,nombre", [], "codigo")]);
  const causa = Object.fromEntries(causas.map((c) => [c.codigo, c.nombre]));
  return filas.map((f): Libre => ({ ...f, causa: causa[f.causa_codigo] ?? f.causa_codigo }));
}

export async function cerrarDescuadre(id: string, estado: "explicado" | "resuelto" | "aceptado", nota: string) {
  if (!nota.trim()) throw new Error("Para cerrar un descuadre hace falta una nota.");
  await cambiar("descuadre", id, { estado, nota });
}

export const archivos = () => leer<Libre>("archivo_importado", "id,fuente,nombre,desde,hasta,filas,estado,creado_en", [], "creado_en.desc");
export const errores = () => leer<Libre>("error_importacion", "id,tipo,texto,fila_origen", [["resuelto", "eq", "false"]], "creado_en.desc");
export async function deshacer(id: string) { await rpc("deshacer_archivo", { p_archivo: id }); }

export async function listaPuntos() {
  const [ps, codigos, terminales] = await Promise.all([
    leer<Libre>("punto_venta", "id,codigo,nombre,tipo,activo", [], "codigo"),
    leer<Libre>("codigo_recaudo", "punto_id,codigo", [["activo_hasta", "is", null]], "codigo"),
    leer<Libre>("terminal_datafono", "id,punto_id,proveedor,codigo_terminal", [["activo_hasta", "is", null]], "codigo_terminal")]);
  return ps.map((p): Libre => ({ ...p, codigo_pago: codigos.find((c) => c.punto_id === p.id)?.codigo ?? "",
    datafonos: terminales.filter((t) => t.punto_id === p.id) }));
}

export async function guardarPunto(p: { id?: string; codigo?: string; nombre: string; tipo: string; activo: boolean }) {
  if (!p.nombre.trim()) throw new Error("Escriba el nombre del punto.");
  if (p.id) await cambiar("punto_venta", p.id, { nombre: p.nombre.trim(), tipo: p.tipo, activo: p.activo });
  else {
    if (!p.codigo?.trim()) throw new Error("Escriba un código corto para el punto, como P12.");
    const yo = await leer<Libre>("empresa_config", "empresa_id", [], "empresa_id");
    const { error } = await base().from("punto_venta").insert({ empresa_id: yo[0].empresa_id, codigo: p.codigo.trim().toUpperCase(), nombre: p.nombre.trim(), tipo: p.tipo });
    if (error) throw new Error(mensaje(error));
  }
}
