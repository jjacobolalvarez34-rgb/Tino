"use client";
// Recorrido guiado de 6 pasos con driver.js. Termina en registrar un compromiso, que es lo
// que alguien nuevo debe aprender primero. Se guarda por usuario en recorrido_usuario: si
// lo vio o lo saltó, no vuelve a salir solo; "Ver el recorrido otra vez" lo repite.
import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";
import { base } from "@/lib/supabase";
import type { Textos } from "@/lib/textos";

export const RECORRIDO = "inicio";

// El elemento que se ve: en el computador el del riel, en el celular el de la barra. Se busca
// al empezar el recorrido; si no está en esta pantalla, el paso sale centrado.
function visible(sel: string): Element | undefined {
  return [...document.querySelectorAll(sel)].find((e) => (e as HTMLElement).offsetParent !== null);
}

export async function yaLoVio(): Promise<boolean> {
  const { data, error } = await base().from("recorrido_usuario").select("estado").eq("recorrido", RECORRIDO).maybeSingle();
  if (error) return true; // si no se puede leer, no se molesta a nadie
  return !!data;
}

async function guardar(empresa_id: string, estado: "visto" | "saltado", paso: number) {
  const { data } = await base().from("recorrido_usuario").select("id").eq("recorrido", RECORRIDO).maybeSingle();
  if (data) await base().from("recorrido_usuario").update({ estado, paso }).eq("id", data.id);
  else await base().from("recorrido_usuario").insert({ empresa_id, recorrido: RECORRIDO, estado, paso });
}

export function iniciarRecorrido({ empresa_id, textos: t, alTerminar }: {
  empresa_id: string; textos: Textos; alTerminar: () => void;
}) {
  const pasos: DriveStep[] = [
    { popover: { title: "Bienvenida a Tino", description:
      `En seis pasos le muestro dónde está lo importante y cómo registrar un compromiso con una ${t.persona}. Puede saltarlo cuando quiera.` } },
    { element: visible('[data-recorrido="pendientes"]'), popover: { title: "Lo urgente, arriba",
      description: "Hoy le dice primero qué necesita atención: compromisos vencidos, quién necesita apoyo y lo que viene. Cada frase se toca." } },
    { element: visible('[data-recorrido="resumen"]'), popover: { title: "El mes en números",
      description: "La venta, el ticket promedio, el cumplimiento de la meta y quién más vendió, comparado con el período anterior." } },
    { element: visible('[data-recorrido="equipo"]'), popover: { title: `Cada ${t.persona}, su ficha`,
      description: `En ${t.equipo} está la ficha de cada ${t.persona}: sus ventas, sus ${t.puntos}, sus compromisos y una línea de tiempo con todo lo registrado.` } },
    { element: visible('[data-recorrido="registrar"]'), popover: { title: "+ Registrar, siempre a mano",
      description: "Desde aquí registra una observación, un compromiso, una sesión o una meta. Cada uno cabe en una pantalla." } },
    { popover: { title: "Ahora usted", description:
      `Registre su primer compromiso: qué va a hacer la ${t.persona}, para cuándo y con qué prioridad. Tarda menos de 30 segundos.`,
      doneBtnText: "Registrar un compromiso" } },
  ];
  let ultimo = 0;
  let termino = false;
  const d = driver({
    steps: pasos, showProgress: true, progressText: "{{current}} de {{total}}", allowClose: true,
    nextBtnText: "Siguiente", prevBtnText: "Atrás", doneBtnText: "Listo", overlayOpacity: 0.45,
    stagePadding: 6, stageRadius: 14, popoverClass: "tino-recorrido",
    onHighlightStarted: (_e, _s, { state }) => { ultimo = state.activeIndex ?? ultimo; },
    onNextClick: () => {
      if (d.isLastStep()) { termino = true; d.destroy(); return; }
      d.moveNext();
    },
    onDestroyed: () => {
      guardar(empresa_id, termino ? "visto" : "saltado", ultimo).catch(() => undefined);
      if (termino) alTerminar();
    },
  });
  d.drive();
}
