// Las palabras de la pantalla que cambian de un negocio a otro, en un solo lugar.
// Cada empresa puede cambiarlas en empresa_config.textos, por ejemplo
// {"persona": "vendedora", "personas": "vendedoras", "punto": "tienda", "puntos": "tiendas"}.
export const TEXTOS_BASE = {
  persona: "asesora",
  personas: "asesoras",
  Persona: "Asesora",
  Personas: "Asesoras",
  punto: "punto",
  puntos: "puntos",
  Punto: "Punto",
  Puntos: "Puntos",
  equipo: "Equipo",
  lider: "líder",
  responsable_punto: "responsable de punto",
  // El nombre del programa de fidelización de la empresa (en Milagros, otro): sale en la
  // plantilla sugerida de Formación y en sus textos.
  programa: "programa de fidelización",
};

export type Textos = typeof TEXTOS_BASE;

const mayuscula = (t: string) => t.charAt(0).toUpperCase() + t.slice(1);

export function textosDe(propios: Record<string, string> | null | undefined): Textos {
  const t = { ...TEXTOS_BASE };
  for (const [k, v] of Object.entries(propios ?? {})) {
    if (typeof v === "string" && v.trim() && k in t) (t as Record<string, string>)[k] = v.trim();
  }
  // Si la empresa cambió solo la palabra en minúscula, la de mayúscula la sigue.
  for (const k of ["persona", "personas", "punto", "puntos"] as const) {
    if (!propios?.[mayuscula(k)]) (t as Record<string, string>)[mayuscula(k)] = mayuscula(t[k]);
  }
  return t;
}
