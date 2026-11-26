// Precios de Tino: el único lugar donde viven. La página /precios y cualquier otra pantalla
// leen de aquí; nada de esto se repite en otro archivo. Pesos colombianos, por punto de venta
// al mes. Ver docs/NEGOCIO/precios.md. Sin IVA: no se menciona hasta que Jacobo lo confirme.

export type IdPlan = "equipo" | "caja" | "completo";

export type Plan = {
  id: IdPlan;
  nombre: string;
  precio: number;          // por punto al mes
  resumen: string;
  incluye: string[];
  destacado?: boolean;
};

export const PLANES: Plan[] = [
  {
    id: "equipo", nombre: "Equipo", precio: 30_000,
    resumen: "Para formar y acompañar a las personas de cada punto y saber quién vende cómo.",
    incluye: [
      "Ciclo de formación: en qué paso va cada persona y calendario de la semana",
      "Registro del día: clientes atendidos, conversión y sus propios indicadores",
      "Personas por punto, aunque estén en varios",
      "Venta por persona, ranking y ticket promedio",
      "Metas y cumplimiento por punto y por persona",
      "Observaciones, evaluaciones y sesiones",
      "Compromisos con fecha y alertas de quién necesita apoyo",
    ],
  },
  {
    id: "caja", nombre: "Caja", precio: 45_000,
    resumen: "Para saber cada día si la plata de cada punto cuadró, y si no, por qué.",
    incluye: [
      "Conciliación de tarjetas y transferencias",
      "Descuadres con su causa probable, o «sin causa clara»",
      "Extracto del banco, datáfonos y Excel del día en un solo cuadre",
      "Lo dudoso queda como propuesta: lo confirma una persona",
      "Copiar a Excel como números",
    ],
  },
  {
    id: "completo", nombre: "Completo", precio: 65_000, destacado: true,
    resumen: "Caja y Equipo juntos: la plata y las personas en el mismo lugar.",
    incluye: ["Todo lo de Caja", "Todo lo de Equipo"],
  },
];

export const CONDICIONES = {
  minimoPuntos: 3,
  implementacionDesde: 400_000,   // una sola vez
  mesesPagadosAlAno: 10,          // pago anual: 12 meses por el precio de 10
  descuentoFundador: 0.3,         // 30 % menos, fijo por 12 meses
  mesesFundador: 12,
  cuposFundador: 5,               // los primeros 5 clientes
  diasPiloto: 30,
  descuentoPiloto: 0.5,           // piloto a mitad de precio
};

export const PRECIO_DESDE = Math.min(...PLANES.map((p) => p.precio));

export const TEXTO_PRINCIPAL =
  `Desde ${pesosCortos(PRECIO_DESDE)} por punto al mes · Mínimo ${CONDICIONES.minimoPuntos} puntos · `
  + `Implementación desde ${pesosCortos(CONDICIONES.implementacionDesde)}`;

// Lo que se paga al mes por un plan, con los puntos y las condiciones elegidas.
// Pago anual: se muestra el equivalente mensual (precio × 10 ÷ 12) y el total del año.
export function cotizar(plan: Plan, puntos: number, { anual = false, fundador = false } = {}) {
  const n = Math.max(puntos, CONDICIONES.minimoPuntos);
  const base = plan.precio * n;
  const conFundador = fundador ? Math.round(base * (1 - CONDICIONES.descuentoFundador)) : base;
  const alAno = anual ? conFundador * CONDICIONES.mesesPagadosAlAno : conFundador * 12;
  return { puntos: n, mensual: Math.round(alAno / 12), alAno, piloto: Math.round(base * (1 - CONDICIONES.descuentoPiloto)) };
}

// "30.000" (sin $ ni decimales, para títulos)
export function pesosCortos(n: number) {
  return n.toLocaleString("es-CO");
}
