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
import { iniciarRecorrido, recorridoDe, type NombreRecorrido } from "./Recorrido";
import { Registrar } from "./Registrar";

export type Yo = { id: string; nombre: string; rol: string; empresa_id: string; empresa: string; punto_id: string | null };
type Contexto = {
  yo: Yo; config: Config; avisar: (texto: string) => void;
  registrar: (persona?: string, tipo?: string, dia?: string) => void; version: number; verRecorrido: (nombre?: NombreRecorrido) => void;
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
  { ruta: "/caja", texto: "Caja", icono: "caja" },
];
const MAS = [
  { ruta: "/caja", texto: "Caja del día", icono: "caja" },
  { ruta: "/resumen", texto: "Lo que necesita atención", icono: "revisar" },
  { ruta: "/transferencias", texto: "Transferencias", icono: "transf" },
  { ruta: "/sin-origen", texto: "Sin origen", icono: "buscar" },
  { ruta: "/por-confirmar", texto: "Por confirmar", icono: "revisar" },
  { ruta: "/descuadres", texto: "Descuadres", icono: "caja" },
  { ruta: "/archivos", texto: "Archivos", icono: "subir" },
  { ruta: "/puntos", texto: "Puntos de venta", icono: "tienda" },
  { ruta: "/equipo/ajustes", texto: "Ajustes de Equipo", icono: "ajustes" },
  { ruta: "/usuarios", texto: "Usuarios", icono: "gente", roles: ["dueno", "soporte"] },
];

export function Marco({ children }: { children: React.ReactNode }) {
  const [yo, setYo] = useState<Yo | null>(null);
  const [cfg, setCfg] = useState<Config | null>(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [mas, setMas] = useState(false);
  const [reg, setReg] = useState<{ persona?: string; tipo?: string; dia?: string } | null>(null);
  const [version, setVersion] = useState(0);
  const reloj = useRef<ReturnType<typeof setTimeout>>();
  const ruta = usePathname();
  const router = useRouter();
  const listo = !!yo && !!cfg;

  // Al elegir una pantalla se cierra "Más". La ventisca va en la portada, no aquí (pedido de
  // Jacobo, 20 nov).
  const irA = useCallback((_e: React.MouseEvent, _destino: string) => { setMas(false); }, []);

  useEffect(() => {
    (async () => {
      const { data } = await base().auth.getSession();
      if (!data.session) { router.replace("/entrar"); return; }
      // Con clave temporal, lo primero es cambiarla (se creó sin correo, ver /api/usuarios).
      if (data.session.user.user_metadata?.clave_temporal) { router.replace("/clave?primera=1"); return; }
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
  const registrar = useCallback((persona?: string, tipo?: string, dia?: string) => setReg({ persona, tipo, dia }), []);
  const verRecorrido = useCallback((nombre?: NombreRecorrido) => {
    const cual = nombre ?? recorridoDe(window.location.pathname);
    if (!yo || !cfg || !cual) return;
    setMas(false);
    // Espera a que se cierre la hoja de "Más" antes de resaltar.
    setTimeout(() => iniciarRecorrido({ nombre: cual, empresa_id: yo.empresa_id, textos: cfg.textos,
      alTerminar: cual === "inicio" ? () => setReg({ tipo: "compromiso" }) : undefined }), 250);
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
          <Link href="/hoy" className="m-riel-logo" aria-label="Tino, ir a Hoy" onClick={(e) => irA(e, "/hoy")}>
            <svg aria-hidden="true"><use href="#logo" /></svg>
          </Link>
          <button className="m-registrar" data-recorrido="registrar" onClick={() => registrar()}>
            <span className="m-registrar-boton"><Icono id="mas" /></span>Registrar
          </button>
          {PRINCIPAL.map((m) => (
            <Link key={m.ruta} href={m.ruta} className="m-destino" aria-current={activa(m.ruta) ? "page" : undefined}
              data-recorrido={m.ruta === "/equipo" ? "equipo" : undefined} onClick={(e) => irA(e, m.ruta)}>
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
              data-recorrido={m.ruta === "/equipo" ? "equipo" : undefined} onClick={(e) => irA(e, m.ruta)}>
              <span className="m-destino-icono"><Icono id={m.icono} /></span>{m.texto}
            </Link>
          ))}
          <button className="m-registrar" data-recorrido="registrar" onClick={() => registrar()}>
            <span className="m-registrar-boton"><Icono id="mas" /></span>Registrar
          </button>
          <Link href="/ventas" className="m-destino" aria-current={activa("/ventas") ? "page" : undefined} onClick={(e) => irA(e, "/ventas")}>
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
          {MAS.filter((m) => !("roles" in m) || (m.roles as string[]).includes(yo.rol)).map((m) => (
            <li key={m.ruta}>
              <Link href={m.ruta} className="m-fila" onClick={(e) => irA(e, m.ruta)}>
                <span className="m-fila-icono"><Icono id={m.icono} /></span>
                <span className="m-fila-texto"><b>{m.texto}</b></span>
                <Icono id="derecha" />
              </Link>
            </li>
          ))}
          <li>
            <button className="m-fila" onClick={() => verRecorrido(recorridoDe(ruta) ?? "inicio")}>
              <span className="m-fila-icono"><Icono id="sol" /></span>
              <span className="m-fila-texto"><b>Ver el recorrido de esta pantalla</b>
                <span>{recorridoDe(ruta) ? "Unos pasos por lo importante de aquí" : "El de Hoy: lo importante en seis pasos"}</span></span>
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

      <Registrar abierta={!!reg} persona={reg?.persona} tipo={reg?.tipo} dia={reg?.dia}
        alCerrar={() => setReg(null)}
        alGuardar={(texto) => { setReg(null); avisar(texto); setVersion((v) => v + 1); }} />

      <div className={"m-aviso" + (aviso ? " ver" : "")} role="status" aria-live="polite">
        {aviso && <><Icono id="ok" />{aviso}</>}
      </div>
    </Ctx.Provider>
  );
}
