"use client";
// El marco de todas las pantallas: pide entrar si no hay sesión y muestra el menú al costado.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { base } from "@/lib/supabase";
import { Icono } from "./Iconos";

export type Yo = { id: string; nombre: string; rol: string; empresa_id: string; empresa: string };
const Contexto = createContext<Yo | null>(null);
export const useYo = () => useContext(Contexto);

const MENU = [
  { ruta: "/hoy", texto: "Hoy", icono: "sol" },
  { ruta: "/equipo", texto: "Equipo", icono: "gente" },
  { ruta: "/ventas", texto: "Ventas", icono: "ventas" },
  { ruta: "/resumen", texto: "Cuadre de caja", icono: "dia" },
  { ruta: "/transferencias", texto: "Transferencias", icono: "transf" },
  { ruta: "/sin-origen", texto: "Sin origen", icono: "buscar" },
  { ruta: "/por-confirmar", texto: "Por confirmar", icono: "revisar" },
  { ruta: "/descuadres", texto: "Descuadres", icono: "caja" },
  { ruta: "/archivos", texto: "Archivos", icono: "subir" },
  { ruta: "/puntos", texto: "Puntos de venta", icono: "ajustes" },
];

export function Programa({ children }: { children: React.ReactNode }) {
  const [yo, setYo] = useState<Yo | null>(null);
  const [error, setError] = useState("");
  const ruta = usePathname();
  const router = useRouter();

  useEffect(() => {
    (async () => {
      const { data } = await base().auth.getSession();
      if (!data.session) {
        router.replace("/entrar");
        return;
      }
      const uid = data.session.user.id;
      const [u, e] = await Promise.all([
        base().from("usuario").select("id,nombre,rol,empresa_id").eq("id", uid).maybeSingle(),
        base().from("empresa").select("nombre").limit(1).maybeSingle(),
      ]);
      if (!u.data || !e.data) {
        setError("Este usuario no tiene empresa asignada en Tino.");
        return;
      }
      setYo({ ...(u.data as Omit<Yo, "empresa">), empresa: (e.data as { nombre: string }).nombre });
    })();
  }, [router]);

  async function salir() {
    await base().auth.signOut();
    router.replace("/entrar");
  }

  if (error) return <main className="pagina"><div className="nota mal"><b>{error}</b></div></main>;
  if (!yo) return <main className="pagina"><p className="estado-carga"><Icono id="cargando" girando />Cargando…</p></main>;

  return (
    <Contexto.Provider value={yo}>
      <div className="app">
        <aside className="lateral">
          <header className="cabeza">
            <svg className="logo" aria-hidden="true"><use href="#logo" /></svg>
            <div><h1>Tino</h1><div className="pequeno">{yo.empresa} · {yo.nombre}</div></div>
          </header>
          <nav className="pestanas" aria-label="Pantallas">
            {MENU.map((m) => (
              <Link key={m.ruta} href={m.ruta} className="pestana" aria-current={ruta === m.ruta ? "page" : undefined}>
                <Icono id={m.icono} />{m.texto}
              </Link>
            ))}
          </nav>
          <button className="boton texto compacto salir" onClick={salir}><Icono id="salir" />Salir</button>
        </aside>
        <main className="pagina">{children}</main>
      </div>
    </Contexto.Provider>
  );
}
