"use client";
// Poner o cambiar la clave: desde el enlace del correo (invitación o "Recuperar clave"), o la
// primera vez que se entra con una clave temporal (?primera=1). En los dos casos ya hay sesión y
// aquí solo se elige la clave nueva; al guardarla se quita la marca clave_temporal.
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { base } from "@/lib/supabase";

export default function Clave() {
  const router = useRouter();
  const [listo, setListo] = useState<boolean | null>(null);
  const [clave, setClave] = useState("");
  const [otra, setOtra] = useState("");
  const [error, setError] = useState("");
  const [ocupado, setOcupado] = useState(false);
  const [primera, setPrimera] = useState(false);
  useEffect(() => { setPrimera(new URLSearchParams(window.location.search).has("primera")); }, []);

  useEffect(() => {
    const { data: sub } = base().auth.onAuthStateChange((evento, sesion) => {
      if (sesion && (evento === "PASSWORD_RECOVERY" || evento === "SIGNED_IN")) setListo(true);
    });
    base().auth.getSession().then(({ data }) => setListo((v) => v ?? !!data.session));
    const reloj = setTimeout(() => setListo((v) => v ?? false), 4000);
    return () => { sub.subscription.unsubscribe(); clearTimeout(reloj); };
  }, []);

  async function guardar(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (clave.length < 10) { setError("Use al menos 10 caracteres."); return; }
    if (clave !== otra) { setError("Las dos claves no son iguales."); return; }
    setOcupado(true);
    const { error: er } = await base().auth.updateUser({ password: clave, data: { clave_temporal: false } });
    setOcupado(false);
    if (er) {
      console.error("[Tino] clave", er);
      setError(/same|different/i.test(er.message) ? "La clave nueva tiene que ser distinta de la temporal."
        : primera ? "No se pudo guardar. Intente de nuevo." : "No se pudo guardar. Pida otro enlace: este puede haber vencido.");
      return;
    }
    router.replace("/hoy");
  }

  return (
    <main className="pagina">
      <section className="tarjeta entrar" aria-labelledby="t-clave">
        <div className="cabeza">
          <svg className="logo" aria-hidden="true"><use href="#logo" /></svg>
          <h1 id="t-clave">{primera ? "Ponga su clave" : "Su clave"}</h1>
        </div>
        {primera && listo && <p className="pequeno">Entró con una clave temporal. Elija una suya, de al menos 10 caracteres, que solo usted sepa.</p>}
        {listo === null && <p className="pequeno">Revisando el enlace…</p>}
        {listo === false && <div className="nota aviso"><span>{primera ? "La sesión se cerró. Entre otra vez con la clave temporal." : "Este enlace no sirve o ya venció. Pida a quien administra Tino que le mande otro."}</span></div>}
        {listo && (
          <form onSubmit={guardar} className="m-form">
            <div className="campo"><label htmlFor="c1">Clave nueva</label>
              <input id="c1" type="password" autoComplete="new-password" value={clave} onChange={(e) => setClave(e.target.value)} /></div>
            <div className="campo"><label htmlFor="c2">Escríbala otra vez</label>
              <input id="c2" type="password" autoComplete="new-password" value={otra} onChange={(e) => setOtra(e.target.value)} /></div>
            {error && <p className="error-campo" role="alert">{error}</p>}
            <button className="boton" type="submit" disabled={ocupado}>{ocupado ? "Guardando…" : "Guardar y entrar"}</button>
          </form>
        )}
      </section>
    </main>
  );
}
