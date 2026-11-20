"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { base } from "@/lib/supabase";

export default function Entrar() {
  const [correo, setCorreo] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const router = useRouter();

  async function entrar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setOcupado(true);
    const { error } = await base().auth.signInWithPassword({ email: correo.trim(), password: clave });
    setOcupado(false);
    if (error) setError("Correo o clave incorrectos.");
    else router.replace("/resumen");
  }

  return (
    <main className="pagina">
      <section className="tarjeta entrar" aria-labelledby="t-entrar">
        <div className="cabeza">
          <svg className="logo" aria-hidden="true"><use href="#logo" /></svg>
          <h1 id="t-entrar">Tino</h1>
        </div>
        <p className="pequeno">Entre con el correo y la clave que le dieron.</p>
        <form onSubmit={entrar} className="tarjeta" style={{ border: 0, padding: 0, gap: "var(--esp-3)" }}>
          <div className="campo"><label htmlFor="correo">Correo</label>
            <input type="email" id="correo" autoComplete="username" required value={correo} onChange={(e) => setCorreo(e.target.value)} /></div>
          <div className="campo"><label htmlFor="clave">Clave</label>
            <input type="password" id="clave" autoComplete="current-password" required value={clave} onChange={(e) => setClave(e.target.value)} /></div>
          <p className="error-campo" role="alert">{error}</p>
          <button className="boton" type="submit" aria-disabled={ocupado}>{ocupado ? "Entrando…" : "Entrar"}</button>
        </form>
      </section>
    </main>
  );
}
