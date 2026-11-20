"use client";
// Marco de la nueva dirección visual (DESIGN.md §15): riel angosto de íconos en el
// computador, barra inferior en el celular, y "+ Registrar" siempre a la vista.
// Pide entrar si no hay sesión y comparte quién es, la configuración y el registrador.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { base } from "@/lib/supabase";
import { config as leerConfig, type Config } from "@/lib/equipo";
import { TEXTOS_BASE } from "@/lib/textos";
import { HojaInferior } from "./HojaInferior";
import { Icono } from "./Iconos";
import { iniciarRecorrido } from "./Recorrido";
import { Registrar } from "./Registrar";

export type Yo = { id: string; nombre: string; rol: string; empresa_id: string; empresa: string; punto_id: string | null };
type Contexto = {
  yo: Yo; config: Config; avisar: (texto: string) => void;
  registrar: (persona?: string, tipo?: string) => void; version: number; verRecorrido: () => void;
};
const Ctx = createContext<Contexto | null>(null);
export const useMarco = () => {
  const c = useContext(Ctx);
  if (!c) throw new Error("useMarco va dentro de <Marco>");
  return c;
};

const PRINCIPAL = [
  { ruta: "/hoy", texto: "Hoy", icono: "sol" },
  { ruta: "/equipo", texto: "Equipo", icono: "gente" },
  { ruta: "/ventas", texto: "Ventas", icono: "ventas" },
];
const MAS = [
  { ruta: "/resumen", texto: "Cuadre de caja", icono: "caja" },
  { ruta: "/transferencias", texto: "Transferencias", icono: "transf" },
  { ruta: "/sin-origen", texto: "Sin origen", icono: "buscar" },
  { ruta: "/por-confirmar", texto: "Por confirmar", icono: "revisar" },
  { ruta: "/descuadres", texto: "Descuadres", icono: "caja" },
  { ruta: "/archivos", texto: "Archivos", icono: "subir" },
  { ruta: "/puntos", texto: "Puntos de venta", icono: "tienda" },
];

export function Marco({ children }: { children: React.ReactNode }) {
  const [yo, setYo] = useState<Yo | null>(null);
  const [cfg, setCfg] = useState<Config | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [mas, setMas] = useState(false);
  const [reg, setReg] = useState<{ persona?: string; tipo?: string } | null>(null);
  const [version, setVersion] = useState(0);
  const reloj = useRef<ReturnType<typeof setTimeout>>();
  const ruta = usePathname();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      const { data } = await base().auth.getSession();
      if (!data.session) { router.replace("/entrar"); return; }
      const uid = data.session.user.id;
      const [u, e] = await Promise.all([
        base().from("usuario").select("id,nombre,rol,empresa_id,punto_id").eq("id", uid).maybeSingle(),
        base().from("empresa").select("nombre").limit(1).maybeSingle(),
      ]);
      if (!u.data || !e.data) { setError("Este usuario no tiene empresa asignada en Tino."); return; }
      setYo({ ...(u.data as Omit<Yo, "empresa">), empresa: (e.data as { nombre: string }).nombre });
      try { setCfg(await leerConfig()); }
      catch { setCfg({ umbral_cumplimiento: null, umbral_dias_sin_seguimiento: null, umbral_compromisos_vencidos: null,
                       dias_proximos: 7, textos: TEXTOS_BASE }); }
    })();
  }, [router]);

  const avisar = useCallback((texto: string) => {
    setAviso(texto);
    clearTimeout(reloj.current);
    reloj.current = setTimeout(() => setAviso(""), 2600);
  }, []);
  const registrar = useCallback((persona?: string, tipo?: string) => setReg({ persona, tipo }), []);
  const verRecorrido = useCallback(() => {
    if (!yo || !cfg) return;
    setMas(false);
    // Espera a que se cierre la hoja de "Más" antes de resaltar.
    setTimeout(() => iniciarRecorrido({ empresa_id: yo.empresa_id, textos: cfg.textos,
      alTerminar: () => setReg({ tipo: "compromiso" }) }), 200);
  }, [yo, cfg]);

  async function salir() {
    await base().auth.signOut();
    router.replace("/entrar");
  }

  if (error) return <main className="m-pagina"><div className="nota mal"><b>{error}</b></div></main>;
  if (!yo || !cfg) return <main className="m-pagina" aria-busy="true"><div className="m-esqueleto" style={{ height: 40, width: 220 }} /><div className="m-esqueleto" style={{ height: 160 }} /></main>;

  const activa = (r: string) => ruta === r || ruta.startsWith(r + "/");
  return (
    <Ctx.Provider value={{ yo, config: cfg, avisar, registrar, version, verRecorrido }}>
      <a className="m-saltar" href="#contenido">Saltar al contenido</a>
      <div className="m-app">
        <nav className="m-riel" aria-label="Pantallas">
          <Link href="/hoy" className="m-riel-logo" aria-label="Tino, ir a Hoy">
            <svg aria-hidden="true"><use href="#logo" /></svg>
          </Link>
          <button className="m-registrar" data-recorrido="registrar" onClick={() => registrar()}>
            <span className="m-registrar-boton"><Icono id="mas" /></span>Registrar
          </button>
          {PRINCIPAL.map((m) => (
            <Link key={m.ruta} href={m.ruta} className="m-destino" aria-current={activa(m.ruta) ? "page" : undefined}
              data-recorrido={m.ruta === "/equipo" ? "equipo" : undefined}>
              <span className="m-destino-icono"><Icono id={m.icono} /></span>{m.texto}
            </Link>
          ))}
          <button className="m-destino" onClick={() => setMas(true)} aria-haspopup="dialog"
            aria-current={MAS.some((m) => activa(m.ruta)) ? "page" : undefined}>
            <span className="m-destino-icono"><Icono id="puntos3" /></span>Más
          </button>
        </nav>
        <main id="contenido" className="m-pagina">{children}</main>
        <nav className="m-barra" aria-label="Pantallas">
          {PRINCIPAL.slice(0, 2).map((m) => (
            <Link key={m.ruta} href={m.ruta} className="m-destino" aria-current={activa(m.ruta) ? "page" : undefined}
              data-recorrido={m.ruta === "/equipo" ? "equipo" : undefined}>
              <span className="m-destino-icono"><Icono id={m.icono} /></span>{m.texto}
            </Link>
          ))}
          <button className="m-registrar" data-recorrido="registrar" onClick={() => registrar()}>
            <span className="m-registrar-boton"><Icono id="mas" /></span>Registrar
          </button>
          <Link href="/ventas" className="m-destino" aria-current={activa("/ventas") ? "page" : undefined}>
            <span className="m-destino-icono"><Icono id="ventas" /></span>Ventas
          </Link>
          <button className="m-destino" onClick={() => setMas(true)} aria-haspopup="dialog">
            <span className="m-destino-icono"><Icono id="puntos3" /></span>Más
          </button>
        </nav>
      </div>

      <HojaInferior abierta={mas} titulo="Más" alCerrar={() => setMas(false)}>
        <p className="m-contexto">{yo.empresa} · {yo.nombre}</p>
        <ul className="m-lista">
          {MAS.map((m) => (
            <li key={m.ruta}>
              <Link href={m.ruta} className="m-fila" onClick={() => setMas(false)}>
                <span className="m-fila-icono"><Icono id={m.icono} /></span>
                <span className="m-fila-texto"><b>{m.texto}</b></span>
                <Icono id="derecha" />
              </Link>
            </li>
          ))}
          <li>
            <button className="m-fila" onClick={verRecorrido}>
              <span className="m-fila-icono"><Icono id="sol" /></span>
              <span className="m-fila-texto"><b>Ver el recorrido otra vez</b><span>Seis pasos por lo importante</span></span>
            </button>
          </li>
          <li>
            <button className="m-fila" onClick={salir}>
              <span className="m-fila-icono"><Icono id="salir" /></span>
              <span className="m-fila-texto"><b>Salir</b></span>
            </button>
          </li>
        </ul>
      </HojaInferior>

      <Registrar abierta={!!reg} persona={reg?.persona} tipo={reg?.tipo}
        alCerrar={() => setReg(null)}
        alGuardar={(texto) => { setReg(null); avisar(texto); setVersion((v) => v + 1); }} />

      <div className={"m-aviso" + (aviso ? " ver" : "")} role="status" aria-live="polite">
        {aviso && <><Icono id="ok" />{aviso}</>}
      </div>
    </Ctx.Provider>
  );
}
