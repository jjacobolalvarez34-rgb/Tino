// La revisión de la mañana en TypeScript: la misma de motores/revision.py y
// panel/datos/revisar.py, sobre el mismo núcleo (motores/nucleo_ts). Debe dar lo mismo
// que Python: lo exige tests/web/comparar_revision.ts con septiembre de un punto real.
import {
  causa_billete,
  causa_compensacion,
  causa_precios,
  causas_de_cruce,
  cruzar,
  emparejar,
  estado_dia,
  sobrantes_vecinos,
  type Item,
} from "../../motores/nucleo_ts/logica.ts";

export type Dia = {
  transferencias: Item[];
  tarjetas: Item[];
  descuadre: number | null;
  venta: number | null;
  asesoras: string;
  productos: { precio: number; nombre: string; movimiento: number }[];
  jornada_id?: string;
  reporte_id?: string | null;
};
export type Excel = Record<string, Record<string, Dia>>;
export type Banco = { por_dia: Map<string, Item[]>; fechas: Set<string>; sin_origen: Record<string, unknown>[] };
export type Tarjetas = { por_dia: Map<string, Item[]>; cubre: Map<string, Set<string>> };
export type Config = {
  tolerancia_cuadra: number;
  porcentaje_explicado: number;
  reglas_sin_peso: string[];
  compensacion?: { monto_minimo: number; tolerancia: number; porcentaje: number };
  billete?: { denominaciones: number[]; max_billetes: number };
  precios?: { monto_minimo: number; max_productos: number; max_mostradas: number };
};
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Libre = Record<string, any>;

const clave = (fecha: string, punto: string) => `${fecha}|${punto}`;
const porTexto = (x: string, y: string) => (x < y ? -1 : x > y ? 1 : 0);

export function dias(desde: string, hasta: string): string[] {
  const salida: string[] = [];
  const d = new Date(desde + "T00:00:00Z");
  const fin = new Date(hasta + "T00:00:00Z");
  while (d <= fin) {
    salida.push(d.toISOString().slice(0, 10));
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return salida;
}

const correr = (f: string, n: number) => {
  const d = new Date(f + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

function cruce(fecha: string, diasPunto: Record<string, Dia>, rol: "transferencias" | "tarjetas",
  externoDe: (f: string) => Item[], cubre: (f: string) => boolean): Libre {
  const vecinos = [correr(fecha, 1), correr(fecha, -1)].map((f) => ({
    cubre: cubre(f), tiene_excel: f in diasPunto, anotado: diasPunto[f]?.[rol] ?? [], externo: externoDe(f),
  }));
  const sobra = sobrantes_vecinos(vecinos);
  const c = cruzar(diasPunto[fecha][rol], externoDe(fecha), sobra.ext_sobra, sobra.excel_sobra);
  return { ...c, externo_dia: externoDe(fecha), ext_vecinos: sobra.ext_sobra };
}

function causasDelDescuadre(fecha: string, diasPunto: Record<string, Dia>, config: Config): Libre[] {
  const dia = diasPunto[fecha];
  const descuadre = dia.descuadre as number;
  const causas: Libre[] = [];
  if (config.compensacion) {
    const fechas = Object.keys(diasPunto).sort(porTexto);
    const i = fechas.indexOf(fecha);
    const vecinos = ([["anterior", i - 1], ["siguiente", i + 1]] as [string, number][])
      .filter(([, j]) => j >= 0 && j < fechas.length).map(([c, j]) => [c, fechas[j]] as [string, string]);
    const cuando = Object.fromEntries(vecinos);
    const { monto_minimo, tolerancia, porcentaje } = config.compensacion;
    for (const c of causa_compensacion(descuadre, vecinos.map(([cual, f]) => ({ cual, descuadre: diasPunto[f].descuadre })),
      monto_minimo, tolerancia, porcentaje) as Libre[]) {
      causas.push({ ...c, fecha: cuando[c.cual] });
    }
  }
  if (config.billete) causas.push(...(causa_billete(descuadre, config.billete.denominaciones, config.billete.max_billetes) as Libre[]));
  if (config.precios) {
    const productos = dia.productos ?? [];
    const { monto_minimo, max_productos, max_mostradas } = config.precios;
    for (const c of causa_precios(descuadre, productos.map((p) => ({ precio: p.precio, movimiento: p.movimiento })),
      monto_minimo, max_productos, max_mostradas) as Libre[]) {
      const nombres = new Map<number, string[]>();
      // Igual que sorted(..., key=-movimiento) de Python: estable.
      for (const p of [...productos].sort((a, b) => b.movimiento - a.movimiento)) {
        if (!nombres.has(p.precio)) nombres.set(p.precio, []);
        nombres.get(p.precio)!.push(p.nombre);
      }
      c.productos = (c.combinaciones as number[][]).map((combo) =>
        combo.map((q) => ({ precio: q, nombres: (nombres.get(q) ?? []).slice(0, 2) })));
      causas.push(c);
    }
  }
  return causas;
}

export function revisar(fecha: string, excel: Excel, banco: Banco, tarjetas: Tarjetas, config: Config): Libre {
  const puntos: Libre[] = [];
  for (const punto of Object.keys(excel).sort(porTexto)) {
    const diasPunto = excel[punto];
    const dia = diasPunto[fecha];
    if (!dia) {
      puntos.push({ punto, sin_excel: true });
      continue;
    }
    const r: Libre = { punto, asesoras: dia.asesoras, venta: dia.venta, descuadre: dia.descuadre, cruces: {}, causas: [], sin_datos: [] };
    const descuadre = dia.descuadre ?? 0;
    if (banco.fechas.has(fecha)) {
      const c = cruce(fecha, diasPunto, "transferencias", (f) => banco.por_dia.get(clave(f, punto)) ?? [], (f) => banco.fechas.has(f));
      r.cruces.transferencias = c;
      r.causas.push(...causas_de_cruce("R30", c as never, descuadre));
    } else r.sin_datos.push("extracto del banco");
    const cubre = tarjetas.cubre.get(punto) ?? new Set<string>();
    if (cubre.has(fecha)) {
      const c = cruce(fecha, diasPunto, "tarjetas", (f) => tarjetas.por_dia.get(clave(f, punto)) ?? [], (f) => cubre.has(f));
      r.cruces.tarjetas = c;
      r.causas.push(...causas_de_cruce("R33", c as never, descuadre));
    } else r.sin_datos.push("reporte de Bold o Redeban");

    if (dia.descuadre === null) r.estado = { estado: "sin_dato", explicado: 0, sin_explicar: 0 };
    else {
      r.causas.push(...causasDelDescuadre(fecha, diasPunto, config));
      for (const c of r.causas) if (c.tipo === "causa" && config.reglas_sin_peso.includes(c.regla)) c.tipo = "pista";
      const causas = r.causas.filter((c: Libre) => c.tipo === "causa").map((c: Libre) => ({ regla: c.regla, monto: c.monto }));
      r.estado = estado_dia(dia.descuadre, causas, config.tolerancia_cuadra, config.porcentaje_explicado, config.reglas_sin_peso);
    }
    puntos.push(r);
  }
  const sin_origen = banco.sin_origen.filter((s) => s.fecha === fecha);
  const sin_configurar = ["compensacion", "billete", "precios"].filter((c) => !(c in config));
  return { fecha, puntos, sin_origen, sin_configurar };
}

// ---------------------------------------------------------------------------
// De las filas de la base a lo que espera revisar (como panel/datos/revisar.py)
// ---------------------------------------------------------------------------
export type Filas = {
  jornadas: Libre[]; reportes: Libre[]; pagos: Libre[]; detalle: Libre[]; movs: Libre[]; archivos: Libre[];
};

export function extractosPorFecha(archivos: Libre[]): Map<string, string> {
  const duenio = new Map<string, string>();
  const banco = archivos.filter((a) => a.fuente === "banco" && a.desde)
    .sort((a, b) => porTexto(a.creado_en, b.creado_en));
  for (const a of banco) for (const f of dias(a.desde, a.hasta)) duenio.set(f, a.id);
  return duenio;
}

// Igual que ingesta/tarjetas.unir_reportes: por proveedor y día, el reporte con préstamo y más cobros.
function unirReportes(lotes: Libre[][]): Libre[] {
  const valor = (c: Libre[]) => [c.reduce((a, x) => a + (x.prestamo ?? 0), 0) > 0 ? 1 : 0, c.length];
  const mejor = new Map<string, Libre[]>();
  for (const cobros of lotes) {
    const porDia = new Map<string, Libre[]>();
    for (const c of cobros) {
      const k = `${c.proveedor}|${c.fecha}`;
      if (!porDia.has(k)) porDia.set(k, []);
      porDia.get(k)!.push(c);
    }
    for (const [k, delDia] of porDia) {
      const actual = mejor.get(k);
      const [a1, a2] = valor(delDia);
      const [b1, b2] = actual ? valor(actual) : [-1, -1];
      if (!actual || a1 > b1 || (a1 === b1 && a2 > b2)) mejor.set(k, delDia);
    }
  }
  return [...mejor.keys()].sort(porTexto).flatMap((k) => mejor.get(k)!);
}

export function armar(f: Filas, nombre: Record<string, string>): { excel: Excel; banco: Banco; tarjetas: Tarjetas } {
  const reportes = new Map(f.reportes.map((r) => [r.jornada_id, r.archivo_id]));
  const excel: Excel = {};
  const porJornada = new Map<string, Dia>();
  for (const j of f.jornadas) {
    if (!(j.punto_id in nombre)) continue;
    const dia: Dia = { transferencias: [], tarjetas: [], descuadre: j.descuadre_reportado, venta: j.venta_teorica,
      asesoras: j.asesoras_texto ?? "", productos: [], jornada_id: j.id, reporte_id: j.reporte_id };
    (excel[nombre[j.punto_id]] ??= {})[j.fecha] = dia;
    porJornada.set(j.id, dia);
  }
  for (const p of f.pagos) {
    const dia = porJornada.get(p.jornada_id);
    if (!dia || (p.archivo_id && p.archivo_id !== reportes.get(p.jornada_id))) continue;
    const rol = p.medio_tipo === "transferencia" ? "transferencias" : p.medio_tipo === "tarjeta" ? "tarjetas" : null;
    if (rol) dia[rol].push({ monto: p.monto, id: `${p.id}|fila ${p.fila_origen ?? 0}` });
  }
  for (const d of f.detalle) {
    const dia = porJornada.get(d.jornada_id);
    if (dia && (!d.archivo_id || d.archivo_id === reportes.get(d.jornada_id))) {
      dia.productos.push({ precio: d.precio_lista, nombre: d.texto_producto, movimiento: d.cantidad ? 1 : 0 });
    }
  }
  const duenio = extractosPorFecha(f.archivos);
  const banco: Banco = { por_dia: new Map(), fechas: new Set(duenio.keys()), sin_origen: [] };
  const lotes = new Map<string, Libre[]>();
  for (const m of f.movs) {
    if (m.fuente === "banco") {
      if (duenio.get(m.fecha) !== m.archivo_id || m.tipo !== "transferencia") continue;
      if (m.punto_id in nombre) {
        const k = clave(m.fecha, nombre[m.punto_id]);
        if (!banco.por_dia.has(k)) banco.por_dia.set(k, []);
        banco.por_dia.get(k)!.push({ monto: m.bruto, id: m.id });
      } else if (m.punto_id === null) {
        banco.sin_origen.push({ fecha: m.fecha, valor: m.bruto, referencia: m.referencia, descripcion: m.descripcion,
          etiqueta: m.etiqueta, id: m.id });
      }
    } else if ((m.fuente === "bold" || m.fuente === "redeban") && m.punto_id in nombre) {
      if (!lotes.has(m.archivo_id)) lotes.set(m.archivo_id, []);
      lotes.get(m.archivo_id)!.push({ proveedor: m.fuente, fecha: m.fecha, punto: nombre[m.punto_id], bruto: m.bruto,
        prestamo: m.prestamo, id: m.id });
    }
  }
  const tarjetas: Tarjetas = { por_dia: new Map(), cubre: new Map() };
  for (const co of unirReportes([...lotes.values()])) {
    if (!tarjetas.cubre.has(co.punto)) tarjetas.cubre.set(co.punto, new Set());
    tarjetas.cubre.get(co.punto)!.add(co.fecha);
    if (co.bruto >= 0) {
      const k = clave(co.fecha, co.punto);
      if (!tarjetas.por_dia.has(k)) tarjetas.por_dia.set(k, []);
      tarjetas.por_dia.get(k)!.push({ monto: co.bruto, id: co.id });
    }
  }
  for (const [punto, fechas] of tarjetas.cubre) {
    const orden = [...fechas].sort(porTexto);
    tarjetas.cubre.set(punto, new Set(dias(orden[0], orden[orden.length - 1])));
  }
  return { excel, banco, tarjetas };
}

// ---------------------------------------------------------------------------
// Lo que se guarda (como para_guardar de Python)
// ---------------------------------------------------------------------------
const CODIGO: Record<string, string> = {
  "R30|no_llego": "transferencia_no_llego", "R30|sin_anotar": "transferencia_sin_anotar",
  "R30|mal_digitado": "transferencia_mal_digitada", "R33|no_llego": "tarjeta_no_aparece",
  "R33|sin_anotar": "tarjeta_sin_anotar", "R33|mal_digitado": "tarjeta_mal_digitada",
};
const pago = (id: string) => id.split("|")[0];

export function paraGuardar(r: Libre, excel: Excel): Libre {
  const descuadres: Libre[] = [];
  const cruces: Libre[] = [];
  const verificaciones: Libre[] = [];
  for (const p of r.puntos as Libre[]) {
    if (p.sin_excel) continue;
    const dia = excel[p.punto][r.fecha];
    if (p.descuadre !== null) {
      const causas = (p.causas as Libre[]).filter((c) => c.tipo === "causa");
      // Como max() de Python: con empate gana el primero.
      const principal = causas.reduce<Libre | null>((m, c) => (m === null || Math.abs(c.monto) > Math.abs(m.monto) ? c : m), null);
      const estado = p.estado.estado;
      const codigo = estado === "cuadra" ? null : estado === "sin_explicar" ? "sin_causa_clara"
        : CODIGO[`${principal!.regla}|${principal!.que}`] ?? principal!.que;
      const evidencias = (p.causas as Libre[]).map((c) => {
        const detalle: Libre = Object.fromEntries(Object.entries(c).filter(([k]) => !["regla", "que", "tipo", "monto", "total"].includes(k)));
        if (c.regla === "R30" || c.regla === "R33") {
          const cr = p.cruces[c.regla === "R30" ? "transferencias" : "tarjetas"];
          const campo: Record<string, string> = { no_llego: "no_llegaron", sin_anotar: "no_anotadas", mal_digitado: "mal_digitadas" };
          detalle.items = cr[campo[c.que]];
        }
        return { causa_codigo: CODIGO[`${c.regla}|${c.que}`] ?? c.que, tipo: c.tipo, monto: c.tipo === "causa" ? c.monto : 0,
          total: c.total, detalle };
      });
      descuadres.push({ jornada_id: dia.jornada_id, reporte_id: dia.reporte_id, monto: p.descuadre, explicado: p.estado.explicado,
        sin_explicar: p.estado.sin_explicar, estado_motor: estado, causa_codigo: codigo, evidencias });
    }
    for (const rol of ["transferencias", "tarjetas"] as const) {
      const c = p.cruces[rol];
      if (!c) continue;
      const mismo = emparejar(dia[rol], c.externo_dia).parejas;
      const vecinos = emparejar((c.otro_dia as Libre[]).filter((x) => x.donde === "externo_otro_dia").map((x) => ({ monto: x.monto, id: x.id })),
        c.ext_vecinos).parejas;
      const parejas: [Item, Item, string][] = [
        ...mismo.map((x) => [x.a, x.b, "mismo_dia"] as [Item, Item, string]),
        ...vecinos.map((x) => [x.a, x.b, "otro_dia"] as [Item, Item, string]),
        ...(c.mal_digitadas as Libre[]).map((m) => [m.anotado, m.externo, "mal_digitado"] as [Item, Item, string]),
      ];
      for (const [a, b, tipo] of parejas) cruces.push({ pago_id: pago(a.id), movimiento_id: b.id, tipo });
      if (rol === "transferencias") {
        for (const [a, b, tipo] of parejas) verificaciones.push({ pago_id: pago(a.id), extracto_id: b.id, estado: tipo === "mismo_dia" ? "confirmada" : "propuesta" });
        for (const a of c.no_llegaron as Item[]) verificaciones.push({ pago_id: pago(a.id), extracto_id: null, estado: "sospechosa" });
      }
    }
  }
  return { descuadres, cruces, verificaciones };
}
