// Usuarios de la empresa: listar, crear sin invitar, dar una clave temporal, invitar o recuperar
// la clave por correo, cambiar rol y punto, desactivar y activar. Solo dueño y soporte.
//
// Sin correo (como hoy): el usuario se crea ya confirmado con una clave temporal que se le
// muestra una sola vez a quien lo creó, para entregarla en persona. Queda marcado con
// clave_temporal y la primera vez que entra Tino le pide cambiarla (Marco y /entrar lo mandan a
// /clave). La clave temporal no se guarda en ninguna parte.
//
// Corre en el servidor porque crear un acceso necesita la llave de servicio de Supabase
// (SUPABASE_SERVICE_ROLE_KEY), que nunca llega al navegador. Todo lo que toca la tabla usuario
// se hace con la sesión de quien llama, así RLS sigue decidiendo (usuario_crear y
// usuario_cambiar: dueño y soporte de su empresa). La llave de servicio solo crea, consulta o
// bloquea el acceso (auth.users).
import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import { randomBytes } from "crypto";
import { NextResponse, type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const URL_BASE = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const PUBLICA = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
const SERVICIO = process.env.SUPABASE_SERVICE_ROLE_KEY;
const ROLES = ["dueno", "encargada", "finanzas", "asesora", "soporte", "lider", "responsable_punto"];
const CON_PUNTO = ["asesora", "responsable_punto"];

const error = (texto: string, estado = 400) => NextResponse.json({ error: texto }, { status: estado });

// Clave temporal fácil de dictar: 12 letras y números sin los que se confunden (0/O, 1/l/I),
// en tres grupos. 31^12 combinaciones: suficiente para una clave que se cambia al primer ingreso.
const LETRAS = "abcdefghjkmnpqrstuvwxyz23456789";
function claveTemporal() {
  const b = randomBytes(12);
  const s = [...b].map((x) => LETRAS[x % LETRAS.length]).join("");
  return `${s.slice(0, 4)}-${s.slice(4, 8)}-${s.slice(8)}`;
}

async function quien(req: NextRequest) {
  const token = (req.headers.get("authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!token) return null;
  const yo = createClient(URL_BASE, PUBLICA, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { headers: { Authorization: `Bearer ${token}` } },
  });
  const { data: u } = await yo.auth.getUser(token);
  if (!u.user) return null;
  const { data } = await yo.from("usuario").select("id,empresa_id,rol,activo").eq("id", u.user.id).maybeSingle();
  if (!data || !data.activo || !["dueno", "soporte"].includes(data.rol)) return { yo, fila: null };
  return { yo, fila: data as { id: string; empresa_id: string; rol: string } };
}

function admin(): SupabaseClient | null {
  if (!SERVICIO) return null;
  return createClient(URL_BASE, SERVICIO, { auth: { persistSession: false, autoRefreshToken: false } });
}

export async function GET(req: NextRequest) {
  const q = await quien(req);
  if (!q) return error("Inicie sesión.", 401);
  if (!q.fila) return error("Solo el dueño y soporte administran usuarios.", 403);
  const adm = admin();
  if (!adm) return error("Falta SUPABASE_SERVICE_ROLE_KEY en el servidor.", 500);
  const { data, error: er } = await q.yo.from("usuario").select("id,nombre,rol,punto_id,activo,creado_en").order("nombre");
  if (er) { console.error("[Tino] usuarios", er); return error("No se pudo leer la lista de usuarios. Intente de nuevo.", 500); }
  const filas = await Promise.all((data ?? []).map(async (u) => {
    const { data: a } = await adm.auth.admin.getUserById(u.id);
    const meta = (a.user?.user_metadata ?? {}) as { invitado_en?: string; clave_temporal?: boolean };
    return { ...u, correo: a.user?.email ?? "", ultimo_ingreso: a.user?.last_sign_in_at ?? null,
             invitado_en: meta.invitado_en ?? null, clave_temporal: !!meta.clave_temporal, es_yo: u.id === q.fila!.id };
  }));
  return NextResponse.json({ usuarios: filas });
}

export async function POST(req: NextRequest) {
  const q = await quien(req);
  if (!q) return error("Inicie sesión.", 401);
  if (!q.fila) return error("Solo el dueño y soporte administran usuarios.", 403);
  const adm = admin();
  if (!adm) return error("Falta SUPABASE_SERVICE_ROLE_KEY en el servidor.", 500);
  const b = await req.json().catch(() => ({}));
  const accion = String(b.accion ?? "");

  if (accion === "crear") {
    const correo = String(b.correo ?? "").trim().toLowerCase();
    const nombre = String(b.nombre ?? "").trim();
    const rol = String(b.rol ?? "");
    const punto = b.punto_id ? String(b.punto_id) : null;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(correo)) return error("Escriba un correo válido.");
    if (nombre.length < 3) return error("Escriba el nombre.");
    if (!ROLES.includes(rol)) return error("Elija un rol.");
    if (rol === "soporte" && q.fila.rol !== "soporte") return error("Solo soporte crea usuarios de soporte.", 403);
    if (CON_PUNTO.includes(rol) && !punto) return error("Ese rol necesita un punto.");
    // Se crea el acceso ya confirmado y sin mandar ningún correo, con una clave temporal.
    const clave = claveTemporal();
    const { data: nuevo, error: er } = await adm.auth.admin.createUser({
      email: correo, email_confirm: true, password: clave, user_metadata: { nombre, clave_temporal: true },
    });
    if (er || !nuevo.user) {
      return error(/already|registered|exists/i.test(er?.message ?? "") ? "Ese correo ya tiene acceso a Tino." : "No se pudo crear el acceso.");
    }
    const { error: er2 } = await q.yo.from("usuario").insert({
      id: nuevo.user.id, empresa_id: q.fila.empresa_id, nombre, rol, punto_id: CON_PUNTO.includes(rol) ? punto : null,
    });
    if (er2) {
      // Si la base no lo dejó (permisos, punto de otra empresa), no queda un acceso suelto.
      await adm.auth.admin.deleteUser(nuevo.user.id);
      return error(er2.code === "23503" ? "Ese punto no es de su empresa." : "No se pudo guardar el usuario.");
    }
    return NextResponse.json({ ok: true, id: nuevo.user.id, clave });
  }

  const id = String(b.id ?? "");
  const { data: u } = await q.yo.from("usuario").select("id,rol,activo").eq("id", id).maybeSingle();
  if (!u) return error("No se encontró ese usuario en su empresa.", 404);
  const esYo = id === q.fila.id;

  if (accion === "clave_temporal") {
    if (esYo) return error("Su propia clave se cambia en «Cambiar mi clave».");
    if (!u.activo) return error("Actívelo antes de darle una clave.");
    const { data: a } = await adm.auth.admin.getUserById(id);
    const clave = claveTemporal();
    const { error: er } = await adm.auth.admin.updateUserById(id, {
      password: clave, user_metadata: { ...(a.user?.user_metadata ?? {}), clave_temporal: true },
    });
    if (er) { console.error("[Tino] clave temporal", er); return error("No se pudo cambiar la clave. Intente de nuevo.", 500); }
    return NextResponse.json({ ok: true, clave });
  }

  if (accion === "invitar" || accion === "recuperar") {
    const { data: a } = await adm.auth.admin.getUserById(id);
    if (!a.user?.email) return error("Ese usuario no tiene correo.");
    if (!u.activo) return error("Actívelo antes de invitarlo.");
    const anonimo = createClient(URL_BASE, PUBLICA, { auth: { persistSession: false } });
    const destino = `${req.nextUrl.origin}/clave`;
    const { error: er } = await anonimo.auth.resetPasswordForEmail(a.user.email, { redirectTo: destino });
    if (er) return error(/rate|limit/i.test(er.message) ? "Supabase limita los correos por hora. Intente más tarde." : "No se pudo enviar el correo.");
    if (accion === "invitar") {
      await adm.auth.admin.updateUserById(id, { user_metadata: { ...(a.user.user_metadata ?? {}), invitado_en: new Date().toISOString() } });
    }
    return NextResponse.json({ ok: true });
  }

  if (accion === "cambiar") {
    if (esYo) return error("No puede cambiar su propio rol.");
    const rol = String(b.rol ?? u.rol);
    if (!ROLES.includes(rol)) return error("Elija un rol.");
    if (rol === "soporte" && q.fila.rol !== "soporte") return error("Solo soporte asigna el rol de soporte.", 403);
    const punto = CON_PUNTO.includes(rol) ? (b.punto_id ? String(b.punto_id) : null) : null;
    if (CON_PUNTO.includes(rol) && !punto) return error("Ese rol necesita un punto.");
    const { error: er } = await q.yo.from("usuario").update({ rol, punto_id: punto }).eq("id", id);
    if (er) return error(er.code === "23503" ? "Ese punto no es de su empresa." : "No se pudo cambiar.");
    return NextResponse.json({ ok: true });
  }

  if (accion === "desactivar" || accion === "activar") {
    if (esYo) return error("No puede desactivarse a sí mismo.");
    const activo = accion === "activar";
    const { error: er } = await q.yo.from("usuario").update({ activo }).eq("id", id);
    if (er) return error("No se pudo cambiar.");
    // Desactivado: además se bloquea el acceso, para que no pueda ni iniciar sesión.
    await adm.auth.admin.updateUserById(id, { ban_duration: activo ? "none" : "876000h" });
    return NextResponse.json({ ok: true });
  }

  return error("Acción desconocida.");
}
