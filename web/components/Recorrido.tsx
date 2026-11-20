"use client";
// Recorridos guiados con driver.js: uno por pantalla, que sale solo la primera vez que alguien
// entra a ella. El de Hoy termina abriendo "Registrar compromiso", que es lo primero que debe
// aprender alguien nuevo. Se guarda por usuario en recorrido_usuario: si lo vio o lo saltó, no
// vuelve a salir solo; "Más → Ver el recorrido de esta pantalla" lo repite.
import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";
import { base } from "@/lib/supabase";
import type { Textos } from "@/lib/textos";

type Paso = { sel?: string; titulo: string; texto: string };
export type NombreRecorrido = "inicio" | "equipo" | "ventas";

// Qué recorrido corresponde a cada pantalla.
export function recorridoDe(ruta: string): NombreRecorrido | null {
  if (ruta.startsWith("/hoy")) return "inicio";
  if (ruta === "/equipo") return "equipo";
  if (ruta.startsWith("/ventas")) return "ventas";
  return null;
}

const PASOS: Record<NombreRecorrido, (t: Textos) => Paso[]> = {
  inicio: (t) => [
    { titulo: "Bienvenida a Tino", texto: `En seis pasos le muestro dónde está lo importante y cómo registrar un compromiso con una ${t.persona}. Puede saltarlo cuando quiera.` },
    { sel: "pendientes", titulo: "Lo urgente, arriba", texto: "Hoy le dice primero qué necesita atención: compromisos vencidos, quién necesita apoyo y lo que viene. Cada frase se toca." },
    { sel: "resumen", titulo: "El mes en números", texto: "La venta, el ticket promedio, el cumplimiento de la meta y quién más vendió, comparado con el período anterior." },
    { sel: "equipo", titulo: `Cada ${t.persona}, su ficha`, texto: `En ${t.equipo} está la ficha de cada ${t.persona}: sus ventas, sus ${t.puntos}, sus compromisos y una línea de tiempo con todo lo registrado.` },
    { sel: "registrar", titulo: "+ Registrar, siempre a mano", texto: "Desde aquí registra una observación, un compromiso, una evaluación, una sesión o una meta. Cada uno cabe en una pantalla." },
    { titulo: "Ahora usted", texto: `Registre su primer compromiso: qué va a hacer la ${t.persona}, para cuándo y con qué prioridad. Tarda menos de 30 segundos.` },
  ],
  equipo: (t) => [
    { sel: "lista-equipo", titulo: `Sus ${t.personas}`, texto: `Busque por nombre, código o ${t.punto}. Arriba cambia entre activas e inactivas; nadie se borra.` },
    { sel: "ficha-cabeza", titulo: "La ficha", texto: `Toque a una ${t.persona} para ver su ficha. Desde "Registrar" le deja una observación, un compromiso o una meta sin elegirla otra vez.` },
    { sel: "ficha-puntos", titulo: `Sus ${t.puntos}`, texto: `Puede estar en varios ${t.puntos} a la vez. Asígnela a otro o sáquela con la ×: queda la fecha, no se borra nada.` },
    { sel: "ficha-cifras", titulo: "Cómo le va", texto: "Venta del mes, ticket promedio y su meta personal. Con las flechas cambia de mes; la comparación es con el mes anterior." },
    { sel: "ficha-compromisos", titulo: "Compromisos", texto: "Suba el avance o márquelo cumplido. Si vence, sale arriba en Hoy." },
    { sel: "ficha-linea", titulo: "Línea de tiempo", texto: "Todo lo registrado, lo más nuevo arriba: observaciones, evaluaciones, compromisos y cambios de punto." },
  ],
  ventas: (t) => [
    { sel: "ventas-periodo", titulo: "El período", texto: "Con las flechas cambia de mes. Siempre se compara con los mismos días del período anterior." },
    { sel: "ventas-cifras", titulo: "El total", texto: "Venta, ticket promedio y cumplimiento de la meta de todos los puntos." },
    { sel: "ventas-vista", titulo: `Por ${t.persona} o por ${t.punto}`, texto: "Cambie la vista del ranking." },
    { sel: "ventas-tabla", titulo: "El ranking", texto: `Toque el nombre de una columna para ordenar. Toque a una ${t.persona} para abrir su ficha.` },
    { sel: "copiar", titulo: "Copiar como números", texto: "Copia la tabla con enteros sin $ ni puntos, lista para pegar en Excel y sumar." },
  ],
};

// El elemento que se ve: en el computador el del riel, en el celular el de la barra.
function visible(sel: string): Element | undefined {
  return [...document.querySelectorAll(`[data-recorrido="${sel}"]`)]
    .find((e) => (e as HTMLElement).offsetParent !== null || getComputedStyle(e).position === "fixed");
}

export async function yaLoVio(nombre: NombreRecorrido): Promise<boolean> {
  const { data, error } = await base().from("recorrido_usuario").select("estado").eq("recorrido", nombre).maybeSingle();
  if (error) return true; // si no se puede leer, no se molesta a nadie
  return !!data;
}

async function guardar(empresa_id: string, nombre: NombreRecorrido, estado: "visto" | "saltado", paso: number) {
  const { data } = await base().from("recorrido_usuario").select("id").eq("recorrido", nombre).maybeSingle();
  if (data) await base().from("recorrido_usuario").update({ estado, paso }).eq("id", data.id);
  else await base().from("recorrido_usuario").insert({ empresa_id, recorrido: nombre, estado, paso });
}

export function iniciarRecorrido({ nombre, empresa_id, textos, alTerminar }: {
  nombre: NombreRecorrido; empresa_id: string; textos: Textos; alTerminar?: () => void;
}) {
  // Un paso que señala algo que no está en pantalla (por ejemplo, la ficha antes de elegir a
  // alguien) se salta: mejor un recorrido corto que uno que señala al vacío.
  const pasos: DriveStep[] = PASOS[nombre](textos).flatMap((p) => {
    if (!p.sel) return [{ popover: { title: p.titulo, description: p.texto } }];
    const el = visible(p.sel);
    return el ? [{ element: el, popover: { title: p.titulo, description: p.texto } }] : [];
  });
  if (!pasos.length) return;
  const final = nombre === "inicio" && alTerminar ? "Registrar un compromiso" : "Listo";
  let ultimo = 0;
  let termino = false;
  const d = driver({
    steps: pasos, showProgress: pasos.length > 1, progressText: "{{current}} de {{total}}", allowClose: true,
    nextBtnText: "Siguiente", prevBtnText: "Atrás", doneBtnText: final, overlayOpacity: 0.45,
    stagePadding: 6, stageRadius: 14, popoverClass: "tino-recorrido",
    onHighlightStarted: (_e, _s, { state }) => { ultimo = state.activeIndex ?? ultimo; },
    onNextClick: () => {
      if (d.isLastStep()) { termino = true; d.destroy(); return; }
      d.moveNext();
    },
    onDestroyed: () => {
      guardar(empresa_id, nombre, termino ? "visto" : "saltado", ultimo).catch(() => undefined);
      if (termino && alTerminar) alTerminar();
    },
  });
  d.drive();
}
