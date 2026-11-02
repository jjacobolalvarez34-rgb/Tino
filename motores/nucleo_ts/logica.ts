// Núcleo de cálculo en TypeScript. La especificación es motores/CONTRATO.md.

export type Item = { monto: number; id: string };
export type Restados = { sobran_a: Item[]; sobran_b: Item[] };
export type Vecino = { cubre: boolean; tiene_excel: boolean; anotado: Item[]; externo: Item[] };
export type Sobrantes = { ext_sobra: Item[]; excel_sobra: Item[] };
export type Donde = "externo_otro_dia" | "anotado_otro_dia";
export type OtroDia = { donde: Donde; monto: number; id: string };
export type MalDigitada = { anotado: Item; externo: Item };
export type Cruce = {
  no_llegaron: Item[];
  no_anotadas: Item[];
  otro_dia: OtroDia[];
  mal_digitadas: MalDigitada[];
};
export type Bloque = { consignacion: string; dias: string[]; grande: boolean };
export type FilaRedeban = {
  codigo: string;
  franquicia: string;
  fecha: string;
  esperado: number;
  banco: number;
};
export type FilaCruzada = FilaRedeban & {
  coincide: boolean;
  sin_datos: boolean;
  cruzado: boolean;
  cruza_con: string[];
};
export type Causa = { regla: string; monto: number };
export type EstadoDia = {
  estado: "cuadra" | "explicado" | "sin_explicar";
  explicado: number;
  sin_explicar: number;
};
export type Transferencia = {
  fecha: string;
  tipo: string;
  referencia: string | null;
  valor: number | null;
};
export type Punto = { punto: string; codigo: string };

const LIMITE_MONTO = 90_000_000_000_000;
const DIGITOS_LIMITE = 14;
const MS_POR_DIA = 86_400_000;
const DOMINGO = 0;
const SABADO = 6;

// El `.` de JavaScript corta también en retorno de carro y separadores Unicode, y su
// `\s` incluye espacios Unicode. Por eso van escritos a mano: solo ASCII.
const RE_VALOR = /^-?[0-9,]*[0-9](\.[0-9]+)?$/;
const RE_LINEA =
  /^(?<fecha>[0-9]{4}\/[0-9]{2}\/[0-9]{2})[ \t\n\r\f\v]+(?<tipo>PAGO QR|PAGO LLAVE)[ \t\n\r\f\v]+(?<resto>[^\n]*)$/;
const RE_VALOR_LINEA =
  /(-?[0-9.]*[0-9],[0-9]{3}(?:,[0-9]{3})*\.[0-9]{2}|-?[0-9]+\.[0-9]{2})[ \t\n\r\f\v]*$/;
const RE_REFERENCIA = /\b([0-9]{7,10})\b/;
const RE_ESPACIOS_EXTREMOS = /^[ \t\n\r\f\v]+|[ \t\n\r\f\v]+$/g;

function por_texto(x: string, y: string): number {
  if (x < y) return -1;
  return x > y ? 1 : 0;
}

export function a_pesos(texto: string): number | null {
  if (!RE_VALOR.test(texto)) return null;

  const negativo = texto.startsWith("-");
  const sin_signo = negativo ? texto.slice(1) : texto;
  const [entero, decimales = ""] = sin_signo.replaceAll(",", "").split(".");

  // Medir el largo evita convertir textos que Number no representaría exactos.
  const digitos = entero.replace(/^0+/, "");
  if (digitos.length > DIGITOS_LIMITE) return null;

  const sube = decimales !== "" && decimales[0] >= "5";
  const valor = Number(digitos) + (sube ? 1 : 0);
  if (valor > LIMITE_MONTO) return null;

  // -0 existe en JavaScript y no es igual a 0 en una comparación estricta.
  if (valor === 0) return 0;
  return negativo ? -valor : valor;
}

export function restar(a: Item[], b: Item[]): Restados {
  // Map y no objeto: un objeto reordena las llaves numéricas de menor a mayor.
  const grupos = new Map<number, Item[]>();
  for (const item of b) {
    const grupo = grupos.get(item.monto);
    if (grupo === undefined) grupos.set(item.monto, [item]);
    else grupo.push(item);
  }

  const sobran_a: Item[] = [];
  for (const item of a) {
    const grupo = grupos.get(item.monto);
    if (grupo !== undefined && grupo.length > 0) grupo.pop();
    else sobran_a.push(item);
  }

  return { sobran_a, sobran_b: [...grupos.values()].flat() };
}

function digitos_ordenados(numero: string): string {
  return [...numero].sort(por_texto).join("");
}

export function parecidos(a: number, b: number): boolean {
  if (a === b) return false;

  const texto_a = String(a);
  const texto_b = String(b);
  if (texto_a.length !== texto_b.length) return a === 10 * b || b === 10 * a;

  if (digitos_ordenados(texto_a) === digitos_ordenados(texto_b)) return true;
  let distintas = 0;
  for (let i = 0; i < texto_a.length; i++) {
    if (texto_a[i] !== texto_b[i]) distintas++;
  }
  return distintas === 1;
}

export function sobrantes_vecinos(vecinos: Vecino[]): Sobrantes {
  const ext_sobra: Item[] = [];
  const excel_sobra: Item[] = [];
  for (const { cubre, tiene_excel, anotado, externo } of vecinos) {
    if (!cubre) {
      if (tiene_excel) excel_sobra.push(...anotado);
    } else if (!tiene_excel) {
      ext_sobra.push(...externo);
    } else {
      const { sobran_a, sobran_b } = restar(anotado, externo);
      excel_sobra.push(...sobran_a);
      ext_sobra.push(...sobran_b);
    }
  }
  return { ext_sobra, excel_sobra };
}

function buscar_otro_dia(
  pendientes: Item[],
  vecinos: Item[],
  donde: Donde,
  otro_dia: OtroDia[],
): Item[] {
  if (pendientes.length === 0) return pendientes;
  const sigue = restar(pendientes, vecinos).sobran_a;
  // Por id y no por monto: con montos repetidos, restar señalaría la fila equivocada.
  const siguen = new Set(sigue.map((item) => item.id));
  for (const { monto, id } of pendientes) {
    if (!siguen.has(id)) otro_dia.push({ donde, monto, id });
  }
  return sigue;
}

export function cruzar(
  anotado: Item[],
  externo: Item[],
  ext_vecinos: Item[],
  excel_vecinos: Item[],
): Cruce {
  const inicial = restar(anotado, externo);
  const otro_dia: OtroDia[] = [];
  const sin_llegar = buscar_otro_dia(inicial.sobran_a, ext_vecinos, "externo_otro_dia", otro_dia);
  const no_anotadas = [
    ...buscar_otro_dia(inicial.sobran_b, excel_vecinos, "anotado_otro_dia", otro_dia),
  ];

  const no_llegaron: Item[] = [];
  const mal_digitadas: MalDigitada[] = [];
  for (const item of sin_llegar) {
    const posicion = no_anotadas.findIndex((otro) => parecidos(item.monto, otro.monto));
    if (posicion === -1) {
      no_llegaron.push(item);
    } else {
      const [pareja] = no_anotadas.splice(posicion, 1);
      mal_digitadas.push({ anotado: item, externo: pareja });
    }
  }

  return { no_llegaron, no_anotadas, otro_dia, mal_digitadas };
}

function leer_fecha(fecha: string): number {
  const [anio, mes, dia] = fecha.split("-").map(Number);
  const ms = Date.UTC(anio, mes - 1, dia);
  // Date.UTC corre las fechas imposibles (30 de febrero) sin avisar.
  if (Number.isNaN(ms) || escribir_fecha(ms) !== fecha) {
    throw new Error(`fecha invalida: ${fecha}`);
  }
  return ms;
}

function escribir_fecha(ms: number): string {
  return new Date(ms).toISOString().slice(0, 10);
}

export function dia_habil_siguiente(fecha: string, festivos: string[]): string {
  const no_habiles = new Set(festivos);
  let ms = leer_fecha(fecha);
  while (true) {
    ms += MS_POR_DIA;
    const dia_semana = new Date(ms).getUTCDay();
    const candidata = escribir_fecha(ms);
    if (dia_semana !== DOMINGO && dia_semana !== SABADO && !no_habiles.has(candidata)) {
      return candidata;
    }
  }
}

export function bloques_deposito(fechas: string[], festivos: string[]): Bloque[] {
  const bloques = new Map<string, string[]>();
  for (const fecha of new Set(fechas)) {
    const consignacion = dia_habil_siguiente(fecha, festivos);
    const dias = bloques.get(consignacion);
    if (dias === undefined) bloques.set(consignacion, [fecha]);
    else dias.push(fecha);
  }

  return [...bloques.keys()].sort(por_texto).map((consignacion) => {
    const dias = [...(bloques.get(consignacion) ?? [])].sort(por_texto);
    return { consignacion, dias, grande: dias.length > 1 };
  });
}

export function coincide_deposito(
  banco: number,
  esperado: number,
  tolerancia: number,
  porcentajes: number[],
): boolean {
  return porcentajes.some((p) => Math.abs(100 * banco - p * esperado) <= 100 * tolerancia);
}

// Índices en orden lexicográfico, igual que itertools.combinations.
function* combinaciones(total: number, n: number): Generator<number[]> {
  const indices = Array.from({ length: n }, (_, i) => i);
  while (true) {
    yield indices;
    let i = n - 1;
    while (i >= 0 && indices[i] === total - n + i) i--;
    if (i < 0) return;
    indices[i]++;
    for (let j = i + 1; j < n; j++) indices[j] = indices[j - 1] + 1;
  }
}

export function cruces_redeban(
  filas: FilaRedeban[],
  tolerancia: number,
  max_cruce: number,
): FilaCruzada[] {
  const salida: FilaCruzada[] = filas.map((fila) => ({
    ...fila,
    coincide: Math.abs(fila.banco - fila.esperado) <= tolerancia,
    sin_datos: fila.banco === 0 && fila.esperado === 0,
    cruzado: false,
    cruza_con: [],
  }));

  const grupos = new Map<string, FilaCruzada[]>();
  for (const fila of salida) {
    if (fila.coincide || fila.sin_datos) continue;
    // JSON y no un separador: un código con ese separador juntaría grupos distintos.
    const clave = JSON.stringify([fila.codigo, fila.franquicia]);
    const grupo = grupos.get(clave);
    if (grupo === undefined) grupos.set(clave, [fila]);
    else grupo.push(fila);
  }

  for (const grupo of grupos.values()) {
    if (grupo.length < 2) continue;
    const tope = Math.min(max_cruce, grupo.length);
    for (let n = 2; n <= tope; n++) {
      for (const indices of combinaciones(grupo.length, n)) {
        const elegidas = indices.map((i) => grupo[i]);
        if (elegidas.some((fila) => fila.cruzado)) continue;

        let suma_banco = 0;
        let suma_esperado = 0;
        for (const fila of elegidas) {
          suma_banco += fila.banco;
          suma_esperado += fila.esperado;
        }
        if (Math.abs(suma_banco - suma_esperado) <= tolerancia) {
          const fechas = elegidas.map((fila) => fila.fecha);
          for (const fila of elegidas) {
            fila.cruzado = true;
            fila.cruza_con = [...fechas];
          }
        }
      }
    }
  }

  return salida;
}

export function estado_dia(
  descuadre: number,
  causas: Causa[],
  tolerancia_cuadra: number,
  porcentaje_explicado: number,
  reglas_sin_peso: string[],
): EstadoDia {
  const abs_descuadre = Math.abs(descuadre);
  let mayor = 0;
  for (const { regla, monto } of causas) {
    if (monto !== 0 && !reglas_sin_peso.includes(regla)) {
      mayor = Math.max(mayor, Math.abs(monto));
    }
  }
  const e = Math.min(abs_descuadre, mayor);

  let estado: EstadoDia["estado"] = "sin_explicar";
  if (abs_descuadre <= tolerancia_cuadra) estado = "cuadra";
  else if (100 * e >= porcentaje_explicado * abs_descuadre) estado = "explicado";

  const signo = descuadre >= 0 ? 1 : -1;
  // -1 × 0 daría -0, que no es igual a 0 en una comparación estricta.
  const explicado = e === 0 ? 0 : signo * e;
  return { estado, explicado, sin_explicar: descuadre - explicado };
}

export function leer_linea_transferencia(linea: string): Transferencia | null {
  const partes = RE_LINEA.exec(linea.replace(RE_ESPACIOS_EXTREMOS, ""));
  if (partes === null || partes.groups === undefined) return null;
  const { fecha, tipo, resto } = partes.groups;

  const valor = RE_VALOR_LINEA.exec(resto);
  if (valor === null) return null;

  const pesos = a_pesos(valor[1]);
  if (pesos === null) return null;

  const referencia = RE_REFERENCIA.exec(resto.slice(0, valor.index));
  return {
    fecha: fecha.replaceAll("/", "-"),
    tipo,
    referencia: referencia === null ? null : referencia[1],
    valor: pesos,
  };
}

// Por caracteres y no por unidades UTF-16, que es lo que contaría slice sobre el texto.
function ultimos_cuatro(texto: string): string {
  return [...texto].slice(-4).join("");
}

export function punto_por_referencia(referencia: string, puntos: Punto[]): string | null {
  const buscados = ultimos_cuatro(referencia);
  let encontrado: string | null = null;
  for (const { punto, codigo } of puntos) {
    if (ultimos_cuatro(codigo) === buscados) encontrado = punto;
  }
  return encontrado;
}

export type Cobro = {
  fecha: string;
  hora: number | null;
  punto: string;
  proveedor: string;
  franquicia: string | null;
  bruto: number;
  comision: number;
  retenciones: number;
  neto: number;
};
export type Grupo<T> = {
  clave: T;
  cobros: number;
  bruto: number;
  comision: number;
  retenciones: number;
  neto: number;
  ticket_promedio: number;
};
export type FilaSemana = {
  clave: number;
  dias: number;
  cobros: number;
  bruto: number;
  promedio_por_dia: number;
};
export type Estadisticas = {
  totales: Omit<Grupo<string>, "clave"> & {
    ticket_mediano: number;
    dias: number;
    promedio_por_dia: number;
  };
  por_punto: Grupo<string>[];
  por_dia: Grupo<string>[];
  por_dia_semana: FilaSemana[];
  por_hora: Grupo<number>[];
  por_proveedor: Grupo<string>[];
  por_franquicia: Grupo<string>[];
  sin_hora: number;
  dia_pico: string | null;
  hora_pico: number | null;
};

// Con el resto y no con `a / b`: la división de JavaScript deja decimales.
function redondear(a: number, b: number): number {
  if (b === 0) return 0;
  const resto = a % b;
  const cociente = (a - resto) / b;
  return 2 * resto >= b ? cociente + 1 : cociente;
}

function agrupar<T extends string | number>(
  cobros: Cobro[],
  clave_de: (cobro: Cobro) => T | null,
): Grupo<T>[] {
  const grupos = new Map<T, Grupo<T>>();
  for (const cobro of cobros) {
    const clave = clave_de(cobro);
    if (clave === null) continue;
    let grupo = grupos.get(clave);
    if (grupo === undefined) {
      grupo = { clave, cobros: 0, bruto: 0, comision: 0, retenciones: 0, neto: 0, ticket_promedio: 0 };
      grupos.set(clave, grupo);
    }
    grupo.cobros += 1;
    grupo.bruto += cobro.bruto;
    grupo.comision += cobro.comision;
    grupo.retenciones += cobro.retenciones;
    grupo.neto += cobro.neto;
  }
  const salida = [...grupos.values()];
  for (const grupo of salida) grupo.ticket_promedio = redondear(grupo.bruto, grupo.cobros);
  return salida;
}

function por_bruto(grupos: Grupo<string>[]): Grupo<string>[] {
  return [...grupos].sort((x, y) => y.bruto - x.bruto || por_texto(x.clave, y.clave));
}

function pico<T>(grupos: Grupo<T>[]): T | null {
  let mejor: Grupo<T> | null = null;
  for (const grupo of grupos) {
    if (mejor === null || grupo.bruto > mejor.bruto) mejor = grupo;
  }
  return mejor === null ? null : mejor.clave;
}

function mediana(valores: number[]): number {
  const orden = [...valores].sort((x, y) => x - y);
  const n = orden.length;
  if (n === 0) return 0;
  const mitad = (n - n % 2) / 2;
  if (n % 2 === 1) return orden[mitad];
  return redondear(orden[mitad - 1] + orden[mitad], 2);
}

// Lunes es 0, como en el contrato; getUTCDay da domingo como 0.
function dia_semana(fecha: string): number {
  return (new Date(leer_fecha(fecha)).getUTCDay() + 6) % 7;
}

export function estadisticas_ventas(cobros: Cobro[]): Estadisticas {
  const [suma] = agrupar(cobros, () => "total");
  const { cobros: cantidad, bruto, comision, retenciones, neto, ticket_promedio } = suma ?? {
    cobros: 0,
    bruto: 0,
    comision: 0,
    retenciones: 0,
    neto: 0,
    ticket_promedio: 0,
  };
  const dias = new Set(cobros.map((cobro) => cobro.fecha)).size;

  const por_dia = agrupar(cobros, (cobro) => cobro.fecha).sort((x, y) => por_texto(x.clave, y.clave));
  const por_hora = agrupar(cobros, (cobro) => cobro.hora).sort((x, y) => x.clave - y.clave);

  const por_dia_semana: FilaSemana[] = Array.from({ length: 7 }, (_, clave) => ({
    clave,
    dias: 0,
    cobros: 0,
    bruto: 0,
    promedio_por_dia: 0,
  }));
  for (const grupo of por_dia) {
    const fila = por_dia_semana[dia_semana(grupo.clave)];
    fila.dias += 1;
    fila.cobros += grupo.cobros;
    fila.bruto += grupo.bruto;
  }
  for (const fila of por_dia_semana) fila.promedio_por_dia = redondear(fila.bruto, fila.dias);

  return {
    totales: {
      cobros: cantidad,
      bruto,
      comision,
      retenciones,
      neto,
      ticket_promedio,
      ticket_mediano: mediana(cobros.map((cobro) => cobro.bruto)),
      dias,
      promedio_por_dia: redondear(bruto, dias),
    },
    por_punto: por_bruto(agrupar(cobros, (cobro) => cobro.punto)),
    por_dia,
    por_dia_semana,
    por_hora,
    por_proveedor: agrupar(cobros, (cobro) => cobro.proveedor).sort((x, y) =>
      por_texto(x.clave, y.clave),
    ),
    por_franquicia: por_bruto(agrupar(cobros, (cobro) => cobro.franquicia)),
    sin_hora: cobros.filter((cobro) => cobro.hora === null).length,
    dia_pico: pico(por_dia),
    hora_pico: pico(por_hora),
  };
}

type Entrada = Record<string, unknown>;
type Registro = { parametros: string[]; llamar: (e: Entrada) => unknown };

// Map y no objeto: así `ejecutar("constructor", ...)` es función desconocida.
const FUNCIONES = new Map<string, Registro>([
  ["a_pesos", { parametros: ["texto"], llamar: (e) => a_pesos(e.texto as string) }],
  ["restar", { parametros: ["a", "b"], llamar: (e) => restar(e.a as Item[], e.b as Item[]) }],
  [
    "parecidos",
    { parametros: ["a", "b"], llamar: (e) => parecidos(e.a as number, e.b as number) },
  ],
  [
    "sobrantes_vecinos",
    { parametros: ["vecinos"], llamar: (e) => sobrantes_vecinos(e.vecinos as Vecino[]) },
  ],
  [
    "cruzar",
    {
      parametros: ["anotado", "externo", "ext_vecinos", "excel_vecinos"],
      llamar: (e) =>
        cruzar(
          e.anotado as Item[],
          e.externo as Item[],
          e.ext_vecinos as Item[],
          e.excel_vecinos as Item[],
        ),
    },
  ],
  [
    "dia_habil_siguiente",
    {
      parametros: ["fecha", "festivos"],
      llamar: (e) => dia_habil_siguiente(e.fecha as string, e.festivos as string[]),
    },
  ],
  [
    "bloques_deposito",
    {
      parametros: ["fechas", "festivos"],
      llamar: (e) => bloques_deposito(e.fechas as string[], e.festivos as string[]),
    },
  ],
  [
    "coincide_deposito",
    {
      parametros: ["banco", "esperado", "tolerancia", "porcentajes"],
      llamar: (e) =>
        coincide_deposito(
          e.banco as number,
          e.esperado as number,
          e.tolerancia as number,
          e.porcentajes as number[],
        ),
    },
  ],
  [
    "cruces_redeban",
    {
      parametros: ["filas", "tolerancia", "max_cruce"],
      llamar: (e) =>
        cruces_redeban(e.filas as FilaRedeban[], e.tolerancia as number, e.max_cruce as number),
    },
  ],
  [
    "estado_dia",
    {
      parametros: [
        "descuadre",
        "causas",
        "tolerancia_cuadra",
        "porcentaje_explicado",
        "reglas_sin_peso",
      ],
      llamar: (e) =>
        estado_dia(
          e.descuadre as number,
          e.causas as Causa[],
          e.tolerancia_cuadra as number,
          e.porcentaje_explicado as number,
          e.reglas_sin_peso as string[],
        ),
    },
  ],
  [
    "leer_linea_transferencia",
    { parametros: ["linea"], llamar: (e) => leer_linea_transferencia(e.linea as string) },
  ],
  [
    "punto_por_referencia",
    {
      parametros: ["referencia", "puntos"],
      llamar: (e) => punto_por_referencia(e.referencia as string, e.puntos as Punto[]),
    },
  ],
  [
    "estadisticas_ventas",
    { parametros: ["cobros"], llamar: (e) => estadisticas_ventas(e.cobros as Cobro[]) },
  ],
]);

export function ejecutar(funcion: string, entrada: object): unknown {
  const registro = FUNCIONES.get(funcion);
  if (registro === undefined) throw new Error(`funcion desconocida: ${funcion}`);

  // Sin esto un parámetro mal escrito llega como undefined y da un false creíble.
  const { parametros, llamar } = registro;
  const faltan = parametros.filter((nombre) => !Object.hasOwn(entrada, nombre));
  const sobran = Object.keys(entrada).filter((nombre) => !parametros.includes(nombre));
  if (faltan.length > 0 || sobran.length > 0) {
    throw new Error(`${funcion}: faltan [${faltan}], sobran [${sobran}]`);
  }
  return llamar(entrada as Entrada);
}
