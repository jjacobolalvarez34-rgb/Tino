/* ==========================================================================
   Cierre del día — pestañas Hoy · Punto · Asesora · Pendientes.
   Depende de window.Suite (app.js) y window.pywebview.api (bridge.py).
   ========================================================================== */
(function () {
  "use strict";

  const api = () => window.pywebview.api;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pesos = (n) => (n == null ? "—" :
    (n < 0 ? "−" : "") + "$" + Math.abs(Math.round(n)).toLocaleString("es-CO"));
  // Descuadre con signo explícito: + sobra plata, − falta.
  const conSigno = (n) => (n == null ? "" : (Math.round(n) > 0 ? "+" : "") + pesos(n));
  const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre"];
  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const REVISIONES = ["pendiente", "revisado", "error confirmado", "descartado"];

  function fechaLarga(iso) {
    const [y, m, d] = iso.split("-").map(Number);
    const f = new Date(y, m - 1, d);
    return `${DIAS[f.getDay()]} ${d} de ${MESES[m - 1]}`;
  }
  const nombreMes = (mes) => { const [y, m] = mes.split("-").map(Number); return `${MESES[m - 1]} ${y}`; };
  const slug = (s) => String(s).replace(/\s+/g, "-");

  const CLASE_ESTADO = { "cuadra": "cuadra", "explicado": "explicado", "sin explicar": "sin-explicar" };
  const CLASE_SEV = { alta: "critical", media: "warning", baja: "muted", info: "muted" };

  let iniciado = false;
  let estado = null;      // último estado del bridge (archivos, fechas, meses, puntos)
  let tab = "hoy";
  let ultimoHoy = null;   // última revisión mostrada en Hoy

  // ==================================================================
  // Pestañas
  // ==================================================================
  function cambiarTab(nueva) {
    tab = nueva;
    document.querySelectorAll(".cierre-tab").forEach((b) => b.classList.toggle("activa", b.dataset.tab === nueva));
    document.querySelectorAll(".cierre-panel").forEach((p) => { p.hidden = p.dataset.panel !== nueva; });
    const panel = document.querySelector(`.cierre-panel[data-panel="${nueva}"]`);
    anime({ targets: panel, opacity: [0, 1], translateY: [8, 0], duration: 320, easing: "easeOutCubic" });
    if (nueva === "punto") cargarPunto();
    if (nueva === "asesora") cargarAsesoras();
    if (nueva === "pendientes") cargarPendientes();
  }
  document.querySelectorAll(".cierre-tab").forEach((b) => b.addEventListener("click", () => cambiarTab(b.dataset.tab)));

  async function actualizarBadge() {
    const res = await api().cierre_vista_pendientes(false);
    if (!res.ok) return;
    const b = $("badgePendientes");
    b.textContent = res.data.total;
    b.hidden = !res.data.total;
  }

  // ==================================================================
  // Paso 1: archivos · Paso 2: fecha
  // ==================================================================
  function renderPuntos(st) {
    const wrap = $("cierrePuntos");
    wrap.innerHTML = st.archivos.map((a) => `
      <div class="cp-chip ${a.archivo ? "ok" : ""}" title="${esc(a.archivo || "Sin archivo cargado")}">
        <span class="dot"></span>
        <div class="cp-txt"><b>${esc(a.nombre)}</b><span>${a.google ? "Google · " : ""}${esc(a.archivo || "sin archivo")}</span></div>
      </div>`).join("");
    if (st.no_asignados && st.no_asignados.length) {
      const al = document.createElement("div");
      al.className = "cierre-alerta";
      al.style.gridColumn = "1 / -1";
      al.innerHTML = st.no_asignados.map((n) => `⚠ ${esc(n.archivo)}: ${esc(n.motivo)}`).join("<br>");
      wrap.appendChild(al);
    }
  }

  function renderFechas(st) {
    const sel = $("cierreFecha");
    const previa = sel.value;
    if (!st.fechas.length) {
      sel.innerHTML = "<option>Carga primero los archivos</option>";
      sel.disabled = true;
      $("btnCierreRevisar").disabled = true;
      $("btnCierreMes").disabled = true;
      return;
    }
    sel.innerHTML = st.fechas.slice().reverse()
      .map((f) => `<option value="${f}">${esc(fechaLarga(f))} · ${f}</option>`).join("");
    sel.value = st.fechas.includes(previa) ? previa : (st.sugerida || st.fechas[st.fechas.length - 1]);
    sel.disabled = false;
    $("btnCierreRevisar").disabled = false;
    actualizarBotonMes();
  }

  function actualizarBotonMes() {
    const mes = ($("cierreFecha").value || "").slice(0, 7);
    const hay = estado && estado.meses_archivos.includes(mes);
    $("btnCierreMes").disabled = !hay;
    $("btnCierreMes").querySelector(".btn-label").textContent =
      hay ? `Revisar todo ${nombreMes(mes)}` : "Revisar todo el mes";
  }
  $("cierreFecha").addEventListener("change", actualizarBotonMes);

  function aplicarEstado(st) {
    if (!st || st.ok === false) {
      if (st) window.Suite.showToast(st.error, "critical");
      return;
    }
    estado = st;
    renderPuntos(st);
    renderFechas(st);
    renderFuentes(st);
  }

  function renderFuentes(st) {
    const s = st.siigo || [];
    $("cierreSiigoLista").textContent = s.length
      ? "Siigo: " + s.map((x) => (x.hasta && x.hasta !== x.fecha
          ? `del ${fechaLarga(x.fecha)} al ${fechaLarga(x.hasta)}` : fechaLarga(x.fecha)) + ` (${x.archivo})`).join(" · ")
      : "Ninguno cargado.";
    if (st.mapeo) $("cierreMapeo").textContent = st.mapeo.archivo + (st.mapeo.propio ? " (el tuyo)" : " (el del programa)");
    const b = st.banco;
    $("cierreBancoLista").textContent = b && b.dias
      ? `${b.archivos.join(" · ")} — ${b.dias} día(s), del ${fechaLarga(b.desde)} al ${fechaLarga(b.hasta)}`
      : "Nada cargado.";
    const t = st.tarjetas;
    $("cierreTarjetasLista").textContent = t && t.archivos && t.archivos.length
      ? `${t.archivos.join(" · ")} — ${t.puntos} punto(s), del ${fechaLarga(t.desde)} al ${fechaLarga(t.hasta)}`
      : "Nada cargado.";
  }

  $("btnCierreTarjetas").addEventListener("click", async () => {
    const btn = $("btnCierreTarjetas");
    window.Suite.setLoading(btn, true);
    try {
      const res = await api().cierre_cargar_tarjetas();
      aplicarEstado(res);
      if (!res || !res.ok || !res.tarjetas_cargados) return;
      res.tarjetas_cargados.forEach((c) => {
        if (c.error) { window.Suite.showToast(`${c.archivo}: ${c.error}`, "critical"); return; }
        const av = c.avisos && c.avisos.length ? "\n" + c.avisos.slice(0, 4).join("\n") : "";
        window.Suite.showToast(`${c.archivo} (${c.tipo}): ${c.cobros} cobros de ${c.puntos} punto(s).${av}`,
          av ? "critical" : "good");
      });
    } finally {
      window.Suite.setLoading(btn, false);
    }
  });

  $("btnCierreBanco").addEventListener("click", async () => {
    const btn = $("btnCierreBanco");
    window.Suite.setLoading(btn, true);
    try {
      const res = await api().cierre_cargar_banco();
      aplicarEstado(res);
      if (!res || !res.ok || !res.banco_cargados) return;
      res.banco_cargados.forEach((c) => {
        if (c.error) { window.Suite.showToast(`${c.archivo}: ${c.error}`, "critical"); return; }
        const av = c.avisos && c.avisos.length ? "\n" + c.avisos.slice(0, 4).join("\n") : "";
        window.Suite.showToast(`${c.archivo}: ${c.transferencias} transferencias en ${c.dias} día(s).${av}`,
          av ? "critical" : "good");
      });
    } finally {
      window.Suite.setLoading(btn, false);
    }
  });

  $("btnCierreSiigo").addEventListener("click", async () => {
    const res = await api().cierre_cargar_siigo();
    aplicarEstado(res);
    if (!res || !res.ok || !res.siigo_cargados) return;
    res.siigo_cargados.forEach((c) => {
      if (c.error) window.Suite.showToast(`${c.archivo}: ${c.error}`, "critical");
      else window.Suite.showToast((c.dias
          ? `Siigo del ${fechaLarga(c.fecha)} al ${fechaLarga(c.hasta)} cargado: ${c.facturas} facturas de ${c.puntos.join(", ")}.`
          : `Siigo del ${fechaLarga(c.fecha)} cargado (${c.puntos.length} puntos).`)
        + (c.avisos && c.avisos.length ? "\n" + c.avisos.join("\n") : ""), c.avisos && c.avisos.length ? "critical" : "good");
    });
  });

  $("btnCierreMapeo").addEventListener("click", async () => {
    const res = await api().cierre_cargar_mapeo();
    aplicarEstado(res);
    if (res && res.ok && res.mapeo_cargado) {
      const m = res.mapeo_cargado;
      window.Suite.showToast(`Mapeo cargado: ${m.productos} productos y ${m.kits} kits.`
        + (m.avisos.length ? "\n" + m.avisos.join("\n") : ""), m.avisos.length ? "critical" : "good");
    }
  });

  window.__cierreLog = function (msg) {
    const el = $(tab === "hoy" && $("cierreLogMes").dataset.activo ? "cierreLogMes" : "cierreLog");
    el.hidden = false;
    el.textContent = msg;
  };

  async function alEntrar() {
    if (iniciado) return;
    iniciado = true;
    aplicarEstado(await api().cierre_estado());
    actualizarBadge();
    renderGoogle(await api().cierre_google_estado());
  }

  // ==================================================================
  // Google Sheets
  // ==================================================================
  const GUIA_GOOGLE = `
    <details class="gs-guia"><summary>Cómo crear las credenciales, paso a paso (una sola vez, ~10 min)</summary>
      <ol>
        <li>Entra a <b>console.cloud.google.com</b> con la cuenta de Google que tiene acceso a la carpeta <b>"cierres 2026"</b>.</li>
        <li>Arriba, en el selector de proyecto: <b>Proyecto nuevo</b> → nombre <b>Suite Irina</b> → Crear. Asegúrate de quedar dentro de ese proyecto.</li>
        <li>Menú ☰ → <b>APIs y servicios → Biblioteca</b>. Busca y dale <b>Habilitar</b> a <b>Google Drive API</b> y luego a <b>Google Sheets API</b>.</li>
        <li>Menú ☰ → <b>APIs y servicios → Pantalla de consentimiento de OAuth</b> (puede llamarse <b>Google Auth Platform</b>):
            tipo <b>Externo</b>, nombre de la app <b>Suite Irina</b>, tu correo como correo de asistencia y de contacto. En <b>Usuarios de prueba</b> (o "Público"), agrega tu propio correo.</li>
        <li>Menú ☰ → <b>APIs y servicios → Credenciales → Crear credenciales → ID de cliente de OAuth</b>. Tipo de aplicación: <b>App de escritorio</b>. Crear → <b>Descargar JSON</b>.</li>
        <li>Aquí: <b>Cargar credenciales (JSON)</b> y elige ese archivo. Luego <b>Conectar con Google</b>: se abre el navegador, inicias sesión y das <b>Permitir</b>.</li>
      </ol>
      <p class="nota">El permiso es <b>solo de lectura</b>: el programa puede ver los nombres de las carpetas y leer los Sheets, nunca cambiarlos.
        Google mostrará el aviso "Google no verificó esta app": es normal porque la app es tuya; dale <b>Continuar</b>.
        Mientras la app esté "En prueba", Google pide volver a conectar cada 7 días; para que no lo pida, en la pantalla de
        consentimiento dale <b>Publicar app</b> (no hace falta verificarla para usarla tú).</p>
    </details>`;

  let gsBusqueda = null;

  function mesesParaGoogle() {
    const hoy = new Date();
    const ayer = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate() - 1);
    const out = [];
    for (let k = 0; k < 4; k++) {
      const d = new Date(ayer.getFullYear(), ayer.getMonth() - k, 1);
      out.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`);
    }
    return out;
  }

  function renderGoogle(g) {
    const cont = $("gsEstado");
    if (!g || g.ok === false) {
      cont.innerHTML = `<p class="muted-note">${esc(g ? g.error : "No se pudo revisar la conexión con Google.")}</p>`;
      return;
    }
    if (!g.credenciales) {
      cont.innerHTML = `<p class="muted-note" style="margin:0">Para conectar hace falta crear, una sola vez, unas credenciales en Google Cloud con tu cuenta.</p>
        ${GUIA_GOOGLE}
        <div class="row" style="margin-top:12px"><button class="btn sky" id="gsCredenciales">Cargar credenciales (JSON)</button></div>`;
    } else if (!g.conectado) {
      cont.innerHTML = `<p class="muted-note" style="margin:0">Credenciales listas. Al conectar se abre tu navegador para iniciar sesión con Google (permiso de solo lectura).</p>
        <div class="row" style="margin-top:12px">
          <button class="btn sky" id="gsConectar"><span class="btn-label">Conectar con Google</span><span class="spinner"></span></button>
          <button class="link-btn" id="gsCredenciales">cambiar credenciales</button>
        </div>${GUIA_GOOGLE}`;
    } else {
      const opts = mesesParaGoogle().map((m) => `<option value="${m}">${esc(nombreMes(m))}</option>`).join("");
      cont.innerHTML = `<p class="muted-note" style="margin:0">Conectado como <b>${esc(g.cuenta || "tu cuenta de Google")}</b> ·
          <button class="link-btn" id="gsDesconectar">desconectar</button></p>
        <div class="row" style="margin-top:12px">
          <select class="input" id="gsMes">${opts}</select>
          <button class="btn sky" id="gsBuscar"><span class="btn-label">Buscar los Sheets del mes</span><span class="spinner"></span></button>
        </div>`;
    }
    const on = (id, fn) => { const el = $(id); if (el) el.addEventListener("click", fn); };
    on("gsCredenciales", async () => renderGoogle(await api().cierre_google_credenciales()));
    on("gsDesconectar", async () => { $("gsAsignacion").hidden = true; renderGoogle(await api().cierre_google_desconectar()); });
    on("gsConectar", async () => {
      const btn = $("gsConectar");
      window.Suite.setLoading(btn, true);
      window.Suite.showToast("Se abrió el navegador: inicia sesión con Google y dale Permitir.", "good");
      try {
        const r = await api().cierre_google_conectar();
        if (r.ok === false) window.Suite.showToast(r.error, "critical");
        renderGoogle(r.ok === false ? await api().cierre_google_estado() : r);
      } finally { const b = $("gsConectar"); if (b) window.Suite.setLoading(b, false); }
    });
    on("gsBuscar", buscarGoogle);
  }

  async function buscarGoogle() {
    const btn = $("gsBuscar");
    const mes = $("gsMes").value;
    window.Suite.setLoading(btn, true);
    try {
      const r = await api().cierre_google_buscar(mes);
      if (!r.ok) { window.Suite.showToast(r.error, "critical"); return; }
      gsBusqueda = r.data;
      renderAsignacion(r.data);
    } finally { window.Suite.setLoading(btn, false); }
  }

  function renderAsignacion(d) {
    const cont = $("gsAsignacion");
    const opciones = (sel, nombreSel) => {
      // Un Sheet asignado que no está en la lista nunca se pierde al guardar.
      const lista = sel && !d.sheets.some((s) => s.id === sel)
        ? d.sheets.concat([{ id: sel, nombre: nombreSel || `Sheet ${sel.slice(0, 10)}…` }]) : d.sheets;
      return `<option value="">— ninguno —</option>` + lista.map((s) =>
        `<option value="${esc(s.id)}" ${s.id === sel ? "selected" : ""}>${esc(s.nombre)}</option>`).join("");
    };
    cont.hidden = false;
    cont.innerHTML = `
      <p class="muted-note" style="margin-top:12px">Carpeta: <b>${esc(d.carpeta)}</b> · ${d.sheets.length} Sheets.
        Revisa que cada punto tenga su Sheet; se recuerda para este mes.</p>
      <div style="overflow-x:auto"><table class="gs-tabla">
        <thead><tr><th>Punto</th><th>Sheet</th><th></th></tr></thead>
        <tbody>${d.puntos.map((p) => `
          <tr class="${p.sheet ? "" : "falta"}"><td>${esc(p.nombre)}</td>
            <td><select class="input" data-punto="${esc(p.id)}">${opciones(p.sheet, p.sheet_nombre)}</select></td>
            <td class="origen">${esc(p.origen || "")}</td></tr>`).join("")}
          <tr><td><b>Transferencias</b></td>
            <td><select class="input" id="gsTransf">${opciones(d.transferencias)}</select></td>
            <td class="origen">fuente del banco (R30)</td></tr>
        </tbody></table></div>
      ${d.avisos.length ? `<div class="gs-avisos">${d.avisos.map((a) => "⚠ " + esc(a)).join("<br>")}</div>` : ""}
      <div class="row" style="margin-top:12px">
        <button class="btn" style="--accent:var(--coral)" id="gsCargar"><span class="btn-label">Guardar y cargar</span><span class="spinner"></span></button>
        <span class="muted-note" style="margin:0">La primera vez lee cada Sheet completo; después solo los que cambiaron.</span>
      </div>`;
    $("gsCargar").addEventListener("click", cargarGoogle);
  }

  async function cargarGoogle() {
    const btn = $("gsCargar");
    const puntos = {};
    document.querySelectorAll("#gsAsignacion select[data-punto]").forEach((s) => { puntos[s.dataset.punto] = s.value || null; });
    window.Suite.setLoading(btn, true);
    try {
      const r = await api().cierre_google_cargar(gsBusqueda.mes, puntos, $("gsTransf").value || null);
      if (!r.ok) { window.Suite.showToast(r.error, "critical"); return; }
      aplicarEstado(r);
      const bien = r.google_cargados.filter((c) => !c.error);
      const mal = r.google_cargados.filter((c) => c.error);
      window.Suite.showToast(`${bien.length} Sheet(s) leídos de Google.`, "good");
      if (mal.length) window.Suite.showToast(mal.map((m) => `${m.nombre}: ${m.error}`).join("\n"), "critical");
      $("gsAsignacion").hidden = true;
    } finally {
      const b = $("gsCargar"); if (b) window.Suite.setLoading(b, false);
      $("cierreLog").hidden = true;
    }
  }

  $("btnCierreCargar").addEventListener("click", async () => {
    const btn = $("btnCierreCargar");
    window.Suite.setLoading(btn, true);
    try {
      const res = await api().cierre_cargar_xlsx();
      aplicarEstado(res);
      if (res && res.ok && res.cargados) {
        const bien = res.cargados.filter((c) => c.punto);
        const mal = res.cargados.filter((c) => !c.punto);
        if (bien.length) window.Suite.showToast(`${bien.length} archivo(s) cargado(s).`, "good");
        if (mal.length) window.Suite.showToast(mal.map((m) => `${m.archivo}: ${m.error}`).join("\n"), "critical");
        const avisos = bien.flatMap((c) => (c.avisos || []).map((a) => `${c.archivo}: ${a}`));
        if (avisos.length) window.Suite.showToast(avisos.join("\n"), "critical");
      }
    } finally {
      window.Suite.setLoading(btn, false);
      $("cierreLog").hidden = true;
    }
  });

  $("btnCierreQuitar").addEventListener("click", async () => {
    aplicarEstado(await api().cierre_quitar_todos());
    $("cierreHoy").hidden = true;
  });

  async function revisarFecha(fecha) {
    const btn = $("btnCierreRevisar");
    window.Suite.setLoading(btn, true);
    try {
      const res = await api().cierre_revisar(fecha);
      if (!res.ok) { window.Suite.showToast(res.error, "critical"); return false; }
      ultimoHoy = res.data;
      renderHoy(res.data);
      actualizarBadge();
      return true;
    } finally {
      window.Suite.setLoading(btn, false);
    }
  }
  $("btnCierreRevisar").addEventListener("click", () => revisarFecha($("cierreFecha").value));

  $("btnCierreMes").addEventListener("click", async () => {
    const mes = $("cierreFecha").value.slice(0, 7);
    const btn = $("btnCierreMes");
    const log = $("cierreLogMes");
    log.dataset.activo = "1";
    window.Suite.setLoading(btn, true);
    try {
      const res = await api().cierre_revisar_mes(mes);
      if (!res.ok) { window.Suite.showToast(res.error, "critical"); return; }
      aplicarEstado(res);
      window.Suite.showToast(`${res.revisados} día(s) de ${nombreMes(mes)} revisados y guardados.\nYa puedes verlos en Punto y Asesora.`, "good");
      await revisarFecha($("cierreFecha").value);
    } finally {
      window.Suite.setLoading(btn, false);
      delete log.dataset.activo;
      log.hidden = true;
    }
  });

  // Saltar al detalle de un día (desde Punto, Asesora o Pendientes).
  async function irAHoy(fecha, punto) {
    cambiarTab("hoy");
    const sel = $("cierreFecha");
    if (![...sel.options].some((o) => o.value === fecha)) {
      const o = document.createElement("option");
      o.value = fecha; o.textContent = `${fechaLarga(fecha)} · ${fecha}`;
      sel.prepend(o);
      sel.disabled = false; $("btnCierreRevisar").disabled = false;
    }
    sel.value = fecha;
    actualizarBotonMes();
    if (!(await revisarFecha(fecha))) return;
    const tr = document.querySelector(`#cierreFilas tr.fila-punto[data-punto="${CSS.escape(punto)}"]`);
    if (tr) {
      tr.click();
      setTimeout(() => tr.scrollIntoView({ behavior: "smooth", block: "start" }), 120);
    }
  }

  // ==================================================================
  // HOY
  // ==================================================================
  function pillEstado(p) {
    const cls = CLASE_ESTADO[p.estado] || "vacio";
    return `<span class="pill ${cls}"><span class="dot"></span>${esc(p.estado)}</span>`;
  }

  function celdaCausa(p) {
    if (p.descuadre == null) return "";
    const pendientes = p.hallazgos.filter((h) => h.revision === "pendiente" && !esMenor(h)).length;
    const senales = p.hallazgos.filter((h) => h.tipo === "señal").length;
    const extra = [senales ? `${senales} señal(es) para revisar` : "",
      pendientes ? `${pendientes} pendiente(s)` : ""].filter(Boolean).join(" · ");
    const small = extra ? `<small>${extra}</small>` : "";
    if (p.estado === "cuadra") return `<span class="sin-hallazgos">—</span>${small}`;
    if (!p.causa_principal) return `Sin causa probable encontrada.${small}`;
    const c = p.causa_principal;
    return `${esc(c.texto)}<small>${esc(c.regla)} · explica ${pesos(c.monto)}</small>${small}`;
  }

  function renderHoy(data) {
    $("cierreHoy").hidden = false;
    $("cierreHoyTitulo").textContent = `¿Qué pasó el ${fechaLarga(data.fecha)}?`;

    const con = data.puntos.filter((p) => p.descuadre != null);
    const n = (e) => con.filter((p) => p.estado === e).length;
    const sinExplicar = con.filter((p) => p.estado === "sin explicar")
      .reduce((a, p) => a + Math.abs(p.sin_explicar || 0), 0);
    const pl = (k, uno, varios) => `${k} ${k === 1 ? uno : varios}`;
    const pills = [];
    if (n("cuadra")) pills.push(`<span class="pill cuadra"><span class="dot"></span>${pl(n("cuadra"), "cuadra", "cuadran")}</span>`);
    if (n("explicado")) pills.push(`<span class="pill explicado"><span class="dot"></span>${pl(n("explicado"), "explicado", "explicados")}</span>`);
    if (n("sin explicar")) pills.push(`<span class="pill sin-explicar"><span class="dot"></span>${n("sin explicar")} sin explicar · ${pesos(sinExplicar)}</span>`);
    const vacios = data.puntos.length - con.length;
    if (vacios) pills.push(`<span class="pill muted">${vacios} sin datos</span>`);
    $("cierreResumen").innerHTML = pills.join("");

    const tbody = $("cierreFilas");
    tbody.innerHTML = "";
    data.puntos.forEach((p) => {
      const tr = document.createElement("tr");
      tr.className = "fila-punto" + (p.descuadre == null ? " vacia" : "");
      tr.dataset.punto = p.punto;
      tr.innerHTML = `
        <td class="punto-nombre"><span class="chev">${p.descuadre == null ? "" : "›"}</span> ${esc(p.nombre)}</td>
        <td>${esc((p.asesoras || []).join(", "))}</td>
        <td class="num">${p.venta == null ? "" : pesos(p.venta)}</td>
        <td class="num descuadre">${conSigno(p.descuadre)}</td>
        <td>${pillEstado(p)}</td>
        <td class="col-causa">${celdaCausa(p)}</td>`;
      if (p.descuadre != null) tr.addEventListener("click", () => alternarDetalle(tr, p));
      tbody.appendChild(tr);
    });
    anime({ targets: "#cierreFilas tr", opacity: [0, 1], translateY: [6, 0], duration: 300,
      delay: anime.stagger(30), easing: "easeOutCubic" });
  }

  function alternarDetalle(tr, p) {
    const sig = tr.nextElementSibling;
    if (sig && sig.classList.contains("detalle")) {
      sig.remove();
      tr.classList.remove("abierta");
      return;
    }
    tr.classList.add("abierta");
    const det = document.createElement("tr");
    det.className = "detalle";
    det.innerHTML = `<td colspan="6">${htmlDetalle(p)}</td>`;
    tr.after(det);
    det.querySelectorAll("[data-abrir]").forEach((b) =>
      b.addEventListener("click", (e) => { e.stopPropagation(); api().cierre_abrir_archivo(b.dataset.abrir); }));
    anime({ targets: det.querySelectorAll(".hz"), opacity: [0, 1], translateY: [6, 0], duration: 260,
      delay: anime.stagger(25), easing: "easeOutCubic" });
  }

  function valorEv(v) {
    if (v == null || v === "") return "<em>vacía</em>";
    if (typeof v === "number") return esc(v.toLocaleString("es-CO", { maximumFractionDigits: 2 }));
    return esc(v);
  }

  const esMenor = (h) => h.tipo === "integridad" && (h.severidad === "baja" || h.severidad === "info");

  function htmlRevision(h) {
    if (!h.id) return "";
    const opts = REVISIONES.map((r) => `<option value="${r}" ${r === h.revision ? "selected" : ""}>${r}</option>`).join("");
    const cuando = h.fecha_revision ? `<span class="rev-estado">marcado el ${esc(h.fecha_revision.replace("T", " "))}</span>` : "";
    return `<div class="hz-rev" data-hid="${h.id}">
        <span class="pill rev-${slug(h.revision)}">${esc(h.revision)}</span>
        <select class="input" aria-label="Revisión">${opts}</select>
        <input class="input" maxlength="500" placeholder="Nota (opcional): qué se encontró o qué se hizo" value="${esc(h.nota || "")}">
        <button class="btn sm" style="--accent:var(--coral)" data-guardar>Guardar</button>${cuando}
      </div>`;
  }

  function htmlHallazgo(h, donde) {
    const monto = h.monto ? `<span class="hz-monto">explica <b>${pesos(h.monto)}</b></span>` : "";
    const ev = h.evidencia.length ? `
      <details><summary>Ver evidencia (${h.evidencia.length})</summary>
        <table class="ev-tabla">${h.evidencia.map((e) => `
          <tr><td class="mono">${esc(e.hoja)}!${esc(e.celda)}</td>
              <td class="ev-valor">${valorEv(e.valor)}</td>
              <td class="mono">${esc(e.formula || "")}</td>
              <td>${esc(e.nota || "")}</td></tr>`).join("")}
        </table></details>` : "";
    const lugar = donde ? `<div class="pend-donde">${esc(h.nombre_punto)} · ${esc(fechaLarga(h.fecha))} ·
        <button class="link-btn" data-ir-fecha="${esc(h.fecha)}" data-ir-punto="${esc(h.punto)}">ver el día</button></div>` : "";
    const ok = h.revision && h.revision !== "pendiente" ? " revisado-ok" : "";
    return `<div class="hz ${esc(h.tipo)}${ok}" data-hid="${h.id || ""}">
        ${lugar}
        <div class="hz-head"><span class="hz-regla">${esc(h.regla)}</span>
          <span class="pill ${CLASE_SEV[h.severidad] || "muted"}">${esc(h.severidad)}</span>${monto}</div>
        <div class="hz-texto">${esc(h.texto)}</div>${ev}${htmlRevision(h)}</div>`;
  }

  function grupo(titulo, lista, plegado) {
    if (!lista.length) return "";
    const items = `<div class="hz-lista">${lista.map((h) => htmlHallazgo(h)).join("")}</div>`;
    if (plegado) return `<div class="hz-grupo"><details><summary>${esc(titulo)} (${lista.length})</summary>${items}</details></div>`;
    return `<div class="hz-grupo"><h4>${esc(titulo)}</h4>${items}</div>`;
  }

  function htmlDetalle(p) {
    const hs = p.hallazgos;
    const causas = hs.filter((h) => h.tipo === "causa");
    const senales = hs.filter((h) => h.tipo === "señal");
    const integ = hs.filter((h) => h.tipo === "integridad");
    const integMayor = integ.filter((h) => !esMenor(h));
    const integMenor = integ.filter(esMenor);
    const origen = p.fuente === "guardado"
      ? `<span>Guardado el <b>${esc((p.revisado_en || "").replace("T", " "))}</b> (el archivo no está cargado ahora)</span>`
      : `<span>Hoja <b>${esc(p.hoja)}</b> de <b>${esc(p.archivo)}</b>
          · <button class="link-btn" data-abrir="${esc(p.punto)}">Abrir Excel</button></span>`;
    const NOMBRE_FUENTE = { excel: "Excel", siigo: "Siigo", banco: "Bancolombia", tarjetas: "Bold/Redeban" };
    const fuentes = (p.fuentes || ["excel"]).map((f) => NOMBRE_FUENTE[f] || f).join(" + ");
    const meta = `<div class="detalle-meta">${origen}
        <span>Fuentes <b>${esc(fuentes)}</b></span>
        <span>Descuadre <b>${conSigno(p.descuadre)}</b> ${p.descuadre > 0 ? "(sobra)" : p.descuadre < 0 ? "(falta)" : ""}</span>
        ${p.estado === "cuadra" ? "" : `<span>Explicado <b>${pesos(p.explicado)}</b></span>
        <span>Sin explicar <b>${pesos(p.sin_explicar)}</b></span>`}
      </div>`;
    const avisos = p.avisos.length ? `<div class="avisos-lectura">${p.avisos.map((a) => "⚠ " + esc(a)).join("<br>")}</div>` : "";
    const cuerpo = grupo("Causas probables del descuadre", causas, false)
      + grupo("Señales para revisar", senales, false)
      + grupo("Planilla: fórmulas y continuidad", integMayor, false)
      + grupo("Avisos menores de la planilla", integMenor, true);
    return `<div class="detalle-in">${meta}${avisos}${cuerpo || '<p class="sin-hallazgos">Sin hallazgos para este día.</p>'}</div>`;
  }

  // Guardar la revisión de un hallazgo (en Hoy y en Pendientes).
  document.addEventListener("click", async (e) => {
    const ir = e.target.closest("[data-ir-fecha]");
    if (ir) { e.stopPropagation(); irAHoy(ir.dataset.irFecha, ir.dataset.irPunto); return; }
    const b = e.target.closest("[data-guardar]");
    if (!b) return;
    e.stopPropagation();
    const caja = b.closest(".hz-rev");
    const id = Number(caja.dataset.hid);
    const revision = caja.querySelector("select").value;
    const nota = caja.querySelector("input").value;
    b.disabled = true;
    try {
      const res = await api().cierre_marcar(id, revision, nota);
      if (!res.ok) { window.Suite.showToast(res.error, "critical"); return; }
      const h = res.hallazgo;
      if (ultimoHoy) {   // que Hoy no muestre un estado viejo al volver a abrir el detalle
        ultimoHoy.puntos.forEach((p) => p.hallazgos.forEach((x) => {
          if (x.id === h.id) Object.assign(x, { revision: h.revision, nota: h.nota, fecha_revision: h.fecha_revision });
        }));
      }
      const tarjeta = caja.closest(".hz");
      if (tab === "pendientes" && h.revision !== "pendiente") {
        anime({ targets: tarjeta, opacity: 0, height: 0, marginTop: 0, paddingTop: 0, paddingBottom: 0,
          duration: 380, easing: "easeInOutQuad", complete: () => { tarjeta.remove(); avisarSiVacio(); } });
      } else {
        caja.outerHTML = htmlRevision(h);
        tarjeta.classList.toggle("revisado-ok", h.revision !== "pendiente");
      }
      window.Suite.showToast(h.revision === "pendiente" ? "Vuelve a pendientes." : `Marcado como "${h.revision}".`, "good");
      actualizarBadge();
    } finally {
      b.disabled = false;
    }
  });

  // ==================================================================
  // PUNTO — ¿cómo va este punto?
  // ==================================================================
  function llenarSelects() {
    if (!estado) return;
    const vp = $("vpPunto"), vm = $("vpMes"), am = $("vaMes");
    const prevP = vp.value, prevM = vm.value, prevA = am.value;
    vp.innerHTML = estado.puntos.map((p) => `<option value="${esc(p.id)}">${esc(p.nombre)}</option>`).join("");
    const conArchivo = estado.archivos.find((a) => a.archivo);
    vp.value = prevP || (conArchivo ? conArchivo.punto : estado.puntos[0].id);
    const meses = estado.meses.slice().reverse();
    const opts = meses.length ? meses.map((m) => `<option value="${m}">${esc(nombreMes(m))}</option>`).join("")
      : "<option value=''>Sin meses revisados</option>";
    const sugerido = ($("cierreFecha").value || "").slice(0, 7);
    vm.innerHTML = opts; am.innerHTML = opts;
    vm.value = meses.includes(prevM) ? prevM : (meses.includes(sugerido) ? sugerido : meses[0] || "");
    am.value = meses.includes(prevA) ? prevA : (meses.includes(sugerido) ? sugerido : meses[0] || "");
  }

  async function cargarPunto() {
    aplicarEstado(await api().cierre_estado());
    llenarSelects();
    const punto = $("vpPunto").value, mes = $("vpMes").value;
    const cont = $("vpContenido");
    if (!mes) {
      cont.innerHTML = '<p class="empty-hint">Todavía no hay días revisados. Revisa un día (o "Revisar todo el mes") en la pestaña Hoy.</p>';
      return;
    }
    const res = await api().cierre_vista_punto(punto, mes);
    if (!res.ok) { window.Suite.showToast(res.error, "critical"); return; }
    const d = res.data, t = d.totales;
    const est = t.por_estado;
    const kpis = `
      <div class="mes-kpis">
        <div class="card kpi-tile"><p class="kpi-label">Días revisados</p><p class="kpi-value">${t.dias_revisados} <span style="font-size:13px;color:var(--text-muted)">de ${d.calendario.length}</span></p>
          <div class="mes-estados">
            ${est.cuadra ? `<span class="pill cuadra">${est.cuadra} cuadran</span>` : ""}
            ${est.explicado ? `<span class="pill explicado">${est.explicado} explicados</span>` : ""}
            ${est["sin explicar"] ? `<span class="pill sin-explicar">${est["sin explicar"]} sin explicar</span>` : ""}
          </div></div>
        <div class="card kpi-tile"><p class="kpi-label">Descuadre neto del mes</p><p class="kpi-value">${conSigno(t.descuadre_neto)}</p>
          <p class="kpi-sub">Venta del mes ${pesos(t.venta)}</p></div>
        <div class="card kpi-tile"><p class="kpi-label">Faltante sin explicar</p><p class="kpi-value ${t.faltante_sin_explicar ? "critical" : ""}">${pesos(t.faltante_sin_explicar)}</p>
          <p class="kpi-sub">Sobrante sin explicar: ${conSigno(t.sobrante_sin_explicar) || "$0"}</p></div>
        <div class="card kpi-tile"><p class="kpi-label">Hallazgos pendientes</p><p class="kpi-value">${t.pendientes}</p>
          <p class="kpi-sub">sin marcar como revisados</p></div>
      </div>`;
    const [y, m] = mes.split("-").map(Number);
    const vacios = (new Date(y, m - 1, 1).getDay() + 6) % 7;   // lunes primero
    const dows = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"].map((x) => `<div class="cal-dow">${x}</div>`).join("");
    const celdas = Array(vacios).fill('<div class="cal-dia vacio"></div>').join("") + d.calendario.map((c) => {
      const cls = c.estado === "sin revisar" ? "sin-revisar" : (CLASE_ESTADO[c.estado] || "");
      const pend = c.pendientes ? `<span class="pend" title="Hallazgos pendientes">${c.pendientes}</span>` : "";
      const titulo = `${fechaLarga(c.fecha)} · ${c.estado}${c.asesoras.length ? " · " + c.asesoras.join(", ") : ""}`;
      return `<div class="cal-dia ${cls}" data-fecha="${c.fecha}" title="${esc(titulo)}">
          <span class="num-dia">${Number(c.fecha.slice(8))}</span>${pend}
          <span class="monto">${c.descuadre == null ? "" : conSigno(c.descuadre)}</span></div>`;
    }).join("");
    cont.innerHTML = `${kpis}
      <div class="card">
        <div class="calendario">${dows}${celdas}</div>
        <div class="cal-leyenda" style="margin-top:14px">
          <span><i style="background:var(--good)"></i>cuadra</span><span><i style="background:var(--warning)"></i>explicado</span>
          <span><i style="background:var(--critical)"></i>sin explicar</span><span><i style="background:var(--surface-hover)"></i>sin revisar</span>
          <span>· El número rojo arriba a la derecha son hallazgos pendientes.</span>
        </div>
      </div>`;
    cont.querySelectorAll(".cal-dia[data-fecha]:not(.sin-revisar)").forEach((el) =>
      el.addEventListener("click", () => irAHoy(el.dataset.fecha, punto)));
    anime({ targets: cont.querySelectorAll(".cal-dia:not(.vacio)"), opacity: [0, 1], scale: [0.96, 1],
      duration: 300, delay: anime.stagger(12), easing: "easeOutCubic" });
  }
  $("vpPunto").addEventListener("change", cargarPunto);
  $("vpMes").addEventListener("change", cargarPunto);

  // ==================================================================
  // ASESORA — ¿cómo va esta persona?
  // ==================================================================
  async function cargarAsesoras() {
    aplicarEstado(await api().cierre_estado());
    llenarSelects();
    const mes = $("vaMes").value;
    const cont = $("vaContenido");
    if (!mes) {
      cont.innerHTML = '<p class="empty-hint">Todavía no hay días revisados.</p>';
      return;
    }
    const res = await api().cierre_vista_asesoras(mes);
    if (!res.ok) { window.Suite.showToast(res.error, "critical"); return; }
    const lista = res.data.asesoras;
    if (!lista.length) { cont.innerHTML = '<p class="empty-hint">No hay asesoras registradas ese mes.</p>'; return; }
    cont.innerHTML = `<div class="card flush"><div class="cierre-tabla-wrap"><table class="as-tabla">
        <thead><tr><th>Asesora</th><th class="num">Días</th><th class="num">Faltante sin explicar</th>
          <th class="num">Sobrante sin explicar</th><th class="num">Pendientes</th><th>Señales para revisar</th></tr></thead>
        <tbody>${lista.map((a, i) => `
          <tr class="fila-as" data-i="${i}">
            <td class="as-nombre">${esc(a.asesora)}<small>${esc(a.puntos.join(", "))}</small></td>
            <td class="num">${a.dias_trabajados}${a.dias_compartidos ? `<br><small style="color:var(--text-muted)">${a.dias_compartidos} compartidos</small>` : ""}</td>
            <td class="num">${a.faltantes.dias ? `${pesos(a.faltantes.monto)}<br><small style="color:var(--text-muted)">${a.faltantes.dias} día(s)</small>` : "—"}</td>
            <td class="num">${a.sobrantes.dias ? `${conSigno(a.sobrantes.monto)}<br><small style="color:var(--text-muted)">${a.sobrantes.dias} día(s)</small>` : "—"}</td>
            <td class="num">${a.pendientes || "—"}</td>
            <td><div class="as-senales">${a.senales.length ? a.senales.map((s) => `<span class="as-senal">⚑ ${esc(s)}</span>`).join("") : '<span class="sin-hallazgos">—</span>'}</div></td>
          </tr>`).join("")}</tbody></table></div></div>
      <p class="muted-note">Un día compartido cuenta para todas las asesoras de ese día. Los nombres se unen solos ("Ana" = "Ana Pérez" en el mismo punto); si hace falta, se corrigen en <b>asesoras_alias</b> de cierre_config.json.</p>`;
    cont.querySelectorAll("tr.fila-as").forEach((tr) => tr.addEventListener("click", () => {
      const sig = tr.nextElementSibling;
      if (sig && sig.classList.contains("detalle")) { sig.remove(); tr.classList.remove("abierta"); return; }
      tr.classList.add("abierta");
      const a = lista[Number(tr.dataset.i)];
      const det = document.createElement("tr");
      det.className = "detalle";
      det.innerHTML = `<td colspan="6"><table class="as-dias">${a.dias.map((x) => `
          <tr data-fecha="${x.fecha}" data-punto="${esc(x.punto)}">
            <td>${esc(fechaLarga(x.fecha))}</td><td>${esc(x.nombre_punto)}</td>
            <td>${pillEstado(x)}</td><td class="num">${conSigno(x.descuadre)}</td>
            <td>${x.estado === "sin explicar" ? `sin explicar ${conSigno(x.sin_explicar)}` : ""}</td>
            <td class="compartido">${[x.compartido ? "compartido" : "", x.pendientes ? `${x.pendientes} pendiente(s)` : ""].filter(Boolean).join(" · ")}</td>
          </tr>`).join("")}</table></td>`;
      tr.after(det);
      det.querySelectorAll("tr[data-fecha]").forEach((r) =>
        r.addEventListener("click", () => irAHoy(r.dataset.fecha, r.dataset.punto)));
    }));
    anime({ targets: cont.querySelectorAll("tr.fila-as"), opacity: [0, 1], translateY: [6, 0], duration: 300,
      delay: anime.stagger(40), easing: "easeOutCubic" });
  }
  $("vaMes").addEventListener("change", cargarAsesoras);

  // ==================================================================
  // PENDIENTES
  // ==================================================================
  function avisarSiVacio() {
    const cont = $("pendContenido");
    if (!cont.querySelector(".hz")) cont.innerHTML = '<p class="vacio-ok">✓ No hay hallazgos pendientes.</p>';
  }

  async function cargarPendientes() {
    const res = await api().cierre_vista_pendientes($("pendMenores").checked);
    if (!res.ok) { window.Suite.showToast(res.error, "critical"); return; }
    const hs = res.data.pendientes;
    const cont = $("pendContenido");
    if (!hs.length) { avisarSiVacio(); return; }
    const porFecha = {};
    hs.forEach((h) => { (porFecha[h.fecha] = porFecha[h.fecha] || []).push(h); });
    cont.innerHTML = Object.keys(porFecha).sort().map((f) => `
      <div class="pend-grupo"><h4>${esc(fechaLarga(f))}</h4>
        ${porFecha[f].map((h) => htmlHallazgo(h, true)).join("")}</div>`).join("");
    anime({ targets: cont.querySelectorAll(".hz"), opacity: [0, 1], translateY: [6, 0], duration: 260,
      delay: anime.stagger(20, { from: "first" }), easing: "easeOutCubic" });
  }
  $("pendMenores").addEventListener("change", cargarPendientes);

  window.Cierre = { alEntrar };
})();
