"use client";
// Subir archivos desde la web (D-057): el archivo va a la carpeta de la empresa en Supabase
// Storage y queda en cola; el programa de escritorio lo procesa con los lectores de siempre.
// Antes de subirlo se calcula su huella (sha256): si ya estaba cargado o en cola, se avisa.
import { useCallback, useEffect, useRef, useState } from "react";
import { base, mensaje } from "@/lib/supabase";
import { fechaHora } from "@/lib/formato";
import { Icono } from "./Iconos";

type EnCola = { id: string; nombre: string; estado: string; mensaje: string | null; creado_en: string; procesado_en: string | null };
type Fila = { nombre: string; estado: "leyendo" | "subiendo" | "listo" | "repetido" | "error"; texto?: string };

const ESTADO: Record<string, [string, string]> = {
  en_cola: ["En cola", "c-esp"], procesando: ["Procesando…", "c-esp"], cargado: ["● Cargado", "c-ok"],
  repetido: ["Ya estaba cargado", "c-neu"], error: ["■ No se pudo leer", "c-mal"],
};
const ACEPTA = ".xlsx,.xls,.xlsm,.zip,.pdf,.csv";
const MAXIMO = 50 * 1024 * 1024;

async function huella(archivo: File) {
  const digest = await crypto.subtle.digest("SHA-256", await archivo.arrayBuffer());
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

const limpio = (nombre: string) => nombre.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^A-Za-z0-9._ ()-]+/g, "_").slice(0, 120);

export function SubirArchivos({ empresaId, alCambiar }: { empresaId: string; alCambiar?: () => void }) {
  const [filas, setFilas] = useState<Fila[]>([]);
  const [cola, setCola] = useState<EnCola[] | null>(null);
  const [error, setError] = useState("");
  const entrada = useRef<HTMLInputElement>(null);

  const verCola = useCallback(async () => {
    const { data, error: er } = await base().from("archivo_en_cola").select("id,nombre,estado,mensaje,creado_en,procesado_en")
      .order("creado_en", { ascending: false }).limit(20);
    if (er) { setError(mensaje(er)); return; }
    setCola(data as EnCola[]);
  }, []);

  useEffect(() => { verCola(); }, [verCola]);
  // Mientras haya algo en cola, se revisa cada 20 segundos.
  useEffect(() => {
    if (!cola?.some((c) => c.estado === "en_cola" || c.estado === "procesando")) return;
    const reloj = setInterval(() => { verCola(); alCambiar?.(); }, 20000);
    return () => clearInterval(reloj);
  }, [cola, verCola, alCambiar]);

  function poner(i: number, f: Partial<Fila>) {
    setFilas((x) => x.map((y, j) => (j === i ? { ...y, ...f } : y)));
  }

  async function subir(lista: FileList | null) {
    if (!lista?.length) return;
    const archivos = [...lista];
    const inicio = filas.length;
    setFilas((x) => [...x, ...archivos.map((a) => ({ nombre: a.name, estado: "leyendo" as const }))]);
    for (const [k, archivo] of archivos.entries()) {
      const i = inicio + k;
      try {
        if (archivo.size > MAXIMO) { poner(i, { estado: "error", texto: "Pesa más de 50 MB." }); continue; }
        const h = await huella(archivo);
        const { data: ya } = await base().from("archivo_importado").select("nombre,creado_en").eq("hash", h).eq("estado", "cargado").limit(1);
        if (ya?.length) {
          poner(i, { estado: "repetido", texto: `Ya estaba cargado (${ya[0].nombre}, ${fechaHora(ya[0].creado_en)}). No se repite.` });
          continue;
        }
        poner(i, { estado: "subiendo" });
        const ruta = `${empresaId}/${h}/${limpio(archivo.name)}`;
        const { error: e1 } = await base().storage.from("archivos").upload(ruta, archivo, { upsert: false, contentType: archivo.type || undefined });
        if (e1 && !/exist|duplicate/i.test(e1.message)) throw new Error("No se pudo subir: " + e1.message);
        const { error: e2 } = await base().from("archivo_en_cola").insert({ empresa_id: empresaId, ruta, nombre: archivo.name, tamano: archivo.size, hash: h });
        if (e2) {
          if (e2.code === "23505") { poner(i, { estado: "repetido", texto: "Ese archivo ya está en cola." }); continue; }
          throw new Error(mensaje(e2));
        }
        poner(i, { estado: "listo", texto: "En cola. Se carga cuando el programa de escritorio lo procese." });
      } catch (e) {
        poner(i, { estado: "error", texto: (e as Error).message });
      }
    }
    if (entrada.current) entrada.current.value = "";
    verCola();
  }

  return (
    <section className="m-subir" aria-labelledby="t-subir">
      <div>
        <h3 id="t-subir">Subir archivos</h3>
        <p className="pequeno">El Excel del día, el .zip o PDF del banco y los reportes de los datáfonos. Quedan en cola y los carga el programa de escritorio con los lectores de siempre.</p>
      </div>
      <label className="boton m-subir-boton">
        <Icono id="subir" />Elegir archivos
        <input ref={entrada} type="file" multiple accept={ACEPTA} onChange={(e) => subir(e.target.files)} />
      </label>
      {filas.length > 0 && (
        <ul className="m-lista" aria-live="polite">
          {filas.map((f, i) => (
            <li key={i} className="m-fila">
              <span className="m-fila-texto"><b>{f.nombre}</b>
                <span className={f.estado === "error" ? "t-mal" : f.estado === "repetido" ? "t-neu" : ""}>
                  {f.estado === "leyendo" ? "Revisando si ya estaba…" : f.estado === "subiendo" ? "Subiendo…" : f.texto}
                </span></span>
            </li>
          ))}
        </ul>
      )}
      {error && <p className="error-campo" role="alert">{error}</p>}
      {cola && cola.length > 0 && (
        <div className="m-grupo">
          <h4>Últimos subidos desde la web</h4>
          <ul className="m-lista">
            {cola.map((c) => (
              <li key={c.id} className="m-fila">
                <span className="m-fila-texto"><b>{c.nombre}</b>
                  <span>Subido {fechaHora(c.creado_en)}{c.procesado_en ? ` · procesado ${fechaHora(c.procesado_en)}` : ""}</span>
                  {c.mensaje && <span className={c.estado === "error" ? "t-mal" : ""}>{c.mensaje}</span>}
                </span>
                <span className={"chip " + (ESTADO[c.estado]?.[1] ?? "c-neu")}>{ESTADO[c.estado]?.[0] ?? c.estado}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
