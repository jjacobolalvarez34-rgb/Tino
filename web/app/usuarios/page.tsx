"use client";
// Usuarios: quién entra a Tino y con qué rol. Solo dueño y soporte. Crear no manda ningún
// correo: el usuario queda "sin invitar" hasta que se toque "Invitar".
import { useEffect, useState } from "react";
import { Marco, useMarco } from "@/components/Marco";
import { Avatar } from "@/components/Avatar";
import { Icono } from "@/components/Iconos";
import { puntos as leerPuntos } from "@/lib/datos";
import { fechaHora } from "@/lib/formato";
import { base } from "@/lib/supabase";

export default function PaginaUsuarios() {
  return <Marco><Usuarios /></Marco>;
}

type Usuario = { id: string; nombre: string; rol: string; punto_id: string | null; activo: boolean; correo: string;
  ultimo_ingreso: string | null; invitado_en: string | null; es_yo: boolean };

const CON_PUNTO = ["asesora", "responsable_punto"];

async function api(metodo: "GET" | "POST", cuerpo?: Record<string, unknown>) {
  const { data } = await base().auth.getSession();
  const r = await fetch("/api/usuarios", {
    method: metodo, headers: { "Content-Type": "application/json", Authorization: `Bearer ${data.session?.access_token ?? ""}` },
    body: cuerpo ? JSON.stringify(cuerpo) : undefined,
  });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error ?? "Algo salió mal.");
  return j;
}

function Usuarios() {
  const { yo, avisar, config } = useMarco();
  const t = config.textos;
  const ROL: Record<string, string> = {
    dueno: "Dueño", encargada: "Encargada", finanzas: "Finanzas", asesora: t.Persona, soporte: "Soporte de Tino",
    lider: "Líder", responsable_punto: `Responsable de ${t.punto}`,
  };
  const [lista, setLista] = useState<Usuario[] | null>(null);
  const [puntos, setPuntos] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [nuevo, setNuevo] = useState(false);
  const [confirmar, setConfirmar] = useState<{ u: Usuario; accion: "invitar" | "recuperar" | "desactivar" } | null>(null);
  const [editando, setEditando] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const puede = ["dueno", "soporte"].includes(yo.rol);

  useEffect(() => {
    if (!puede) return;
    Promise.all([api("GET"), leerPuntos()]).then(([r, p]) => { setLista(r.usuarios); setPuntos(p); })
      .catch((e) => setError((e as Error).message));
  }, [recarga, puede]);

  async function hacer(cuerpo: Record<string, unknown>, ok: string) {
    try { await api("POST", cuerpo); avisar(ok); setConfirmar(null); setEditando(null); setRecarga((r) => r + 1); }
    catch (e) { avisar((e as Error).message); }
  }

  function estado(u: Usuario) {
    if (!u.activo) return <span className="chip c-neu">Desactivado</span>;
    if (u.ultimo_ingreso) return <span className="chip c-ok">● Activo · entró {fechaHora(u.ultimo_ingreso)}</span>;
    if (u.invitado_en) return <span className="chip c-esp">Invitado {fechaHora(u.invitado_en)}</span>;
    return <span className="chip c-rev">▲ Sin invitar</span>;
  }

  if (!puede) return <div className="nota aviso"><span>Solo el dueño y soporte administran los usuarios.</span></div>;
  return (
    <>
      <header className="m-encabezado">
        <h1>Usuarios</h1>
        <p className="m-contexto">Quién entra a Tino y qué puede ver. Crear un usuario no le manda ningún correo: usted decide cuándo invitarlo.</p>
      </header>
      {error && <div className="nota mal" role="alert"><b>{error}</b></div>}
      {!nuevo
        ? <button className="boton secundario" style={{ alignSelf: "flex-start" }} onClick={() => setNuevo(true)}><Icono id="mas" />Nuevo usuario</button>
        : <Formulario roles={ROL} puntos={puntos} soySoporte={yo.rol === "soporte"} alCerrar={() => setNuevo(false)}
            alGuardar={(c) => hacer({ accion: "crear", ...c }, "Usuario creado, sin invitar todavía")} />}
      {!lista && !error && [0, 1, 2].map((i) => <div key={i} className="m-esqueleto" style={{ height: 64 }} />)}
      {lista && (
        <ul className="m-lista">
          {lista.map((u) => (
            <li key={u.id} className="m-usuario">
              <div className="m-usuario-quien">
                <Avatar id={u.id} nombre={u.nombre} />
                <span className="m-fila-texto">
                  <b>{u.nombre}{u.es_yo ? " (usted)" : ""}</b>
                  <span>{u.correo} · {ROL[u.rol] ?? u.rol}{u.punto_id ? ` · ${puntos[u.punto_id] ?? ""}` : ""}</span>
                  <span>{estado(u)}</span>
                </span>
              </div>
              {editando === u.id ? (
                <Formulario roles={ROL} puntos={puntos} soySoporte={yo.rol === "soporte"} usuario={u} alCerrar={() => setEditando(null)}
                  alGuardar={(c) => hacer({ accion: "cambiar", id: u.id, rol: c.rol, punto_id: c.punto_id }, "Cambio guardado")} />
              ) : (
                <div className="m-compromiso-acciones">
                  {u.activo && !u.ultimo_ingreso && <button className="boton secundario compacto" onClick={() => setConfirmar({ u, accion: "invitar" })}>Invitar</button>}
                  {u.activo && u.ultimo_ingreso && <button className="boton texto compacto" onClick={() => setConfirmar({ u, accion: "recuperar" })}>Recuperar clave</button>}
                  {!u.es_yo && <button className="boton texto compacto" onClick={() => setEditando(u.id)}><Icono id="lapiz" />Rol y {t.punto}</button>}
                  {!u.es_yo && (u.activo
                    ? <button className="boton texto compacto" onClick={() => setConfirmar({ u, accion: "desactivar" })}>Desactivar</button>
                    : <button className="boton texto compacto" onClick={() => hacer({ accion: "activar", id: u.id }, "Activo otra vez")}>Activar</button>)}
                </div>
              )}
              {confirmar?.u.id === u.id && (
                <div className="nota aviso" role="alert">
                  <span className="cuerpo">
                    <b>{confirmar.accion === "desactivar" ? `¿Desactivar a ${u.nombre}?` : confirmar.accion === "invitar" ? `¿Invitar a ${u.nombre}?` : `¿Mandar a ${u.nombre} un correo para cambiar la clave?`}</b>
                    <span>{confirmar.accion === "desactivar"
                      ? "Deja de poder entrar desde ya. No se borra nada: lo que registró se queda y lo puede activar otra vez."
                      : `Le llega un correo a ${u.correo} con un enlace para poner su clave.`}</span>
                    <span className="m-compromiso-acciones">
                      <button className="boton compacto" onClick={() => hacer({ accion: confirmar.accion, id: u.id },
                        confirmar.accion === "desactivar" ? "Desactivado" : "Correo enviado")}>
                        {confirmar.accion === "desactivar" ? "Sí, desactivar" : "Sí, enviar el correo"}</button>
                      <button className="boton secundario compacto" onClick={() => setConfirmar(null)}>Cancelar</button>
                    </span>
                  </span>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Formulario({ roles, puntos, soySoporte, usuario, alCerrar, alGuardar }: {
  roles: Record<string, string>; puntos: Record<string, string>; soySoporte: boolean; usuario?: Usuario;
  alCerrar: () => void; alGuardar: (c: { correo: string; nombre: string; rol: string; punto_id: string | null }) => void;
}) {
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState(usuario?.rol ?? "encargada");
  const [punto, setPunto] = useState(usuario?.punto_id ?? "");
  const [falta, setFalta] = useState("");
  const necesitaPunto = CON_PUNTO.includes(rol);
  return (
    <form className="m-form m-tarjeta-suave" onSubmit={(e) => {
      e.preventDefault();
      if (!usuario && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo.trim())) { setFalta("Escriba un correo válido."); return; }
      if (!usuario && nombre.trim().length < 3) { setFalta("Escriba el nombre."); return; }
      if (necesitaPunto && !punto) { setFalta("Ese rol necesita un punto."); return; }
      alGuardar({ correo: correo.trim(), nombre: nombre.trim(), rol, punto_id: necesitaPunto ? punto : null });
    }}>
      {!usuario && <>
        <div className="campo"><label htmlFor="u-nombre">Nombre</label>
          <input id="u-nombre" type="text" value={nombre} onChange={(e) => setNombre(e.target.value)} maxLength={120} autoFocus /></div>
        <div className="campo"><label htmlFor="u-correo">Correo</label>
          <input id="u-correo" type="email" inputMode="email" value={correo} onChange={(e) => setCorreo(e.target.value)} maxLength={160} /></div>
      </>}
      <div className="m-dos">
        <div className="campo"><label htmlFor="u-rol">Rol</label>
          <select id="u-rol" value={rol} onChange={(e) => setRol(e.target.value)}>
            {Object.entries(roles).filter(([k]) => k !== "soporte" || soySoporte).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></div>
        {necesitaPunto && <div className="campo"><label htmlFor="u-punto">Punto</label>
          <select id="u-punto" value={punto} onChange={(e) => setPunto(e.target.value)}>
            <option value="">Elija el punto</option>
            {Object.entries(puntos).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select></div>}
      </div>
      {falta && <p className="error-campo" role="alert">{falta}</p>}
      <div className="m-pie-acciones">
        <button type="button" className="boton secundario" onClick={alCerrar}>Cancelar</button>
        <button type="submit" className="boton">{usuario ? "Guardar" : "Crear sin invitar"}</button>
      </div>
    </form>
  );
}
