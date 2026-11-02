/* ==========================================================================
   Suite Irina — app.js
   Router + llamadas al bridge Python (pywebview) + animaciones (anime.js).
   ========================================================================== */
(function () {
  "use strict";

  const MESES_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const MESES_ES_LARGO = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const DOW_ES = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"];

  const fmtMoney = (n) => (n || 0).toLocaleString("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 });
  const fmtDateShort = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${d} ${MESES_ES[m - 1]} ${y}`; };
  const pad2 = (n) => String(n).padStart(2, "0");

  // ------------------------------------------------------------------
  // Toasts
  // ------------------------------------------------------------------
  const toastStack = document.getElementById("toastStack");
  function showToast(msg, type) {
    type = type || "good";
    const el = document.createElement("div");
    el.className = "toast " + type;
    el.innerHTML = `<div class="icon">${type === "critical" ? "⚠" : "✓"}</div><div class="msg"></div>`;
    el.querySelector(".msg").textContent = msg;
    toastStack.appendChild(el);
    anime({ targets: el, translateX: [40, 0], opacity: [0, 1], duration: 280, easing: "easeOutCubic" });
    setTimeout(() => {
      anime({
        targets: el, translateX: [0, 40], opacity: [1, 0], duration: 220, easing: "easeInQuad",
        complete: () => el.remove(),
      });
    }, 5200);
  }

  function setLoading(btn, isLoading) {
    btn.classList.toggle("is-loading", isLoading);
    btn.disabled = isLoading;
  }

  function animateNumber(el, to, formatter) {
    const obj = { val: 0 };
    anime({
      targets: obj, val: to, duration: 750, easing: "easeOutExpo", round: 1,
      update: () => { el.textContent = formatter(obj.val); },
    });
  }

  // ------------------------------------------------------------------
  // Router
  // ------------------------------------------------------------------
  const SCREEN_META = {
    home: { title: "Inicio", sub: "Elige un módulo para empezar.", accent: "var(--violet)", back: false },
    conciliador: { title: "Bold / Redeban", sub: "Puedes subir Bold y Redeban juntos: se generan reportes separados.", accent: "var(--violet)", back: true },
    transferencias: { title: "Transferencias por punto de venta", sub: "Extrae PAGO QR / PAGO LLAVE de los PDF de Bancolombia.", accent: "var(--sky)", back: true },
    cierre: { title: "Cierre del día", sub: "Descuadres de los 11 puntos, con sus causas probables y evidencia.", accent: "var(--coral)", back: true },
    historial: { title: "Historial & diferencias", sub: "Acumulado de todas las verificaciones contra Bancolombia.", accent: "var(--lime)", back: true },
  };
  let currentScreen = null;

  function updateTopbar(name) {
    const meta = SCREEN_META[name];
    document.getElementById("topbarTitle").textContent = meta.title;
    document.getElementById("topbarSub").textContent = meta.sub;
    document.getElementById("topbarAccent").style.background = meta.accent;
    document.getElementById("btnBack").style.display = meta.back ? "" : "none";
  }

  function updateNavActive(name) {
    document.querySelectorAll(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.goto === name));
  }

  function navigate(name) {
    if (name === currentScreen) return;
    const outEl = document.querySelector(".screen.is-active");
    const inEl = document.querySelector(`.screen[data-screen="${name}"]`);
    if (!inEl) return;

    updateTopbar(name);
    updateNavActive(name);

    if (outEl) {
      anime({
        targets: outEl, opacity: [1, 0], translateY: [0, -6], duration: 140, easing: "easeInQuad",
        complete: () => outEl.classList.remove("is-active"),
      });
    }
    inEl.classList.add("is-active");
    anime({ targets: inEl, opacity: [0, 1], translateY: [10, 0], duration: 320, easing: "easeOutCubic", delay: outEl ? 90 : 0 });
    const cards = inEl.querySelectorAll(".card, .module-card");
    anime({
      targets: cards, opacity: [0, 1], translateY: [14, 0], duration: 380, easing: "easeOutCubic",
      delay: anime.stagger(40, { start: outEl ? 140 : 60 }),
    });

    currentScreen = name;
    onScreenEnter(name);
  }

  function onScreenEnter(name) {
    if (name === "historial") loadHistorial();
    if (name === "cierre" && window.Cierre) window.Cierre.alEntrar();
  }

  // Lo que otras pantallas (js/cierre.js) necesitan de aquí.
  window.Suite = { showToast, setLoading, animateNumber, navigate };

  document.querySelectorAll("[data-goto]").forEach((el) => el.addEventListener("click", () => navigate(el.dataset.goto)));
  document.getElementById("btnBack").addEventListener("click", () => navigate("home"));

  // ------------------------------------------------------------------
  // Espera a que pywebview inyecte window.pywebview.api
  // ------------------------------------------------------------------
  function whenApiReady(cb) {
    if (window.pywebview && window.pywebview.api) return cb();
    window.addEventListener("pywebviewready", cb, { once: true });
  }

  window.__appendLog = function (msg) {
    const box = document.getElementById("trLog");
    const empty = box.querySelector(".log-empty");
    if (empty) empty.remove();
    const line = document.createElement("div");
    line.className = "line";
    line.textContent = msg;
    box.appendChild(line);
    box.scrollTop = box.scrollHeight;
    anime({ targets: line, opacity: [0, 1], translateY: [3, 0], duration: 200, easing: "easeOutQuad" });
  };

  // ==================================================================
  // CONCILIADOR
  // ==================================================================
  const api = () => window.pywebview.api;

  let conciliadorState = null;
  let calYear = null, calMonth = null, calInitialized = false;

  function renderFileChips(state) {
    const wrap = document.getElementById("fileChips");
    wrap.innerHTML = "";
    state.bold_files.forEach((f) => {
      const c = document.createElement("span"); c.className = "file-chip bold"; c.textContent = "BOLD · " + f;
      wrap.appendChild(c);
    });
    state.redeban_files.forEach((f) => {
      const c = document.createElement("span"); c.className = "file-chip redeban"; c.textContent = "REDEBAN · " + f;
      wrap.appendChild(c);
    });
    if (!state.bold_files.length && !state.redeban_files.length) {
      const c = document.createElement("span"); c.className = "file-chip"; c.textContent = "Ningún archivo cargado todavía.";
      wrap.appendChild(c);
    }
    const om = document.getElementById("filesOmitidas");
    if (state.omitidas) {
      om.style.display = "";
      om.textContent = `${state.omitidas} transacción(es) no exitosa(s) ignorada(s) del archivo Bold.`;
    } else om.style.display = "none";
  }

  function populateDateSelects(state, resetRange) {
    const desde = document.getElementById("selDesde"), hasta = document.getElementById("selHasta");
    const prevD = desde.value, prevH = hasta.value;
    desde.innerHTML = ""; hasta.innerHTML = "";
    state.dates.forEach((iso) => {
      const o1 = document.createElement("option"); o1.value = iso; o1.textContent = fmtDateShort(iso); desde.appendChild(o1);
      const o2 = o1.cloneNode(true); hasta.appendChild(o2);
    });
    if (state.dates.length) {
      if (!resetRange && state.dates.includes(prevD)) desde.value = prevD; else desde.value = state.dates[0];
      if (!resetRange && state.dates.includes(prevH)) hasta.value = prevH; else hasta.value = state.dates[state.dates.length - 1];
    }
  }

  function renderCalendar(state) {
    const card = document.getElementById("cardHolidays");
    if (!state.has_bold) { card.style.display = "none"; return; }
    card.style.display = "";

    if (!calInitialized && state.bold_available_dates.length) {
      const [y, m] = state.bold_available_dates[0].split("-").map(Number);
      calYear = y; calMonth = m - 1; calInitialized = true;
    }
    if (calYear === null) { const now = new Date(); calYear = now.getFullYear(); calMonth = now.getMonth(); }

    document.getElementById("calLabel").textContent = `${MESES_ES_LARGO[calMonth]} ${calYear}`;
    const grid = document.getElementById("calGrid");
    grid.innerHTML = "";
    DOW_ES.forEach((d) => { const el = document.createElement("div"); el.className = "dow"; el.textContent = d; grid.appendChild(el); });

    const dataSet = new Set(state.bold_available_dates);
    const holidaySet = new Set(state.holidays);
    const firstDow = (new Date(calYear, calMonth, 1).getDay() + 6) % 7;
    const nDays = new Date(calYear, calMonth + 1, 0).getDate();

    for (let i = 0; i < firstDow; i++) { const e = document.createElement("div"); e.className = "mini-cal-day empty"; grid.appendChild(e); }
    for (let day = 1; day <= nDays; day++) {
      const iso = `${calYear}-${pad2(calMonth + 1)}-${pad2(day)}`;
      const el = document.createElement("div");
      el.className = "mini-cal-day" + (dataSet.has(iso) ? " has-data" : "") + (holidaySet.has(iso) ? " holiday" : "");
      el.textContent = day;
      el.addEventListener("click", async () => {
        const newState = await api().toggle_holiday(iso);
        applyConciliadorState(newState, { resetRange: false });
      });
      grid.appendChild(el);
    }

    const lbl = document.getElementById("holidaysLabel");
    lbl.textContent = "Festivos marcados: " + (state.holidays.length ? state.holidays.slice().sort().join(", ") : "(ninguno)");
  }

  function applyConciliadorState(state, opts) {
    opts = opts || {};
    if (!state || state.ok === false) { if (state) showToast(state.error, "critical"); return; }
    conciliadorState = state;
    renderFileChips(state);
    populateDateSelects(state, !!opts.resetRange);
    renderCalendar(state);
    document.getElementById("outdirLabel").textContent = state.out_dir;
    document.getElementById("pdfLabel").textContent = state.bank_pdf || "Ninguno.";
  }

  document.getElementById("btnUploadFiles").addEventListener("click", async () => {
    const state = await api().pick_conciliador_files();
    applyConciliadorState(state, { resetRange: true });
    document.getElementById("generateResult").textContent = "";
    document.getElementById("verifyResult").textContent = "";
  });
  document.getElementById("btnClearFiles").addEventListener("click", async () => {
    calInitialized = false;
    const state = await api().clear_conciliador_files();
    applyConciliadorState(state, { resetRange: true });
    document.getElementById("generateResult").textContent = "";
    document.getElementById("verifyResult").textContent = "";
  });
  document.getElementById("btnChooseOutdir").addEventListener("click", async () => {
    const state = await api().choose_conciliador_outdir();
    applyConciliadorState(state, { resetRange: false });
  });
  document.getElementById("btnUploadPdf").addEventListener("click", async () => {
    const state = await api().pick_bank_pdf();
    applyConciliadorState(state, { resetRange: false });
  });
  document.getElementById("calPrev").addEventListener("click", () => {
    calMonth--; if (calMonth < 0) { calMonth = 11; calYear--; }
    renderCalendar(conciliadorState);
  });
  document.getElementById("calNext").addEventListener("click", () => {
    calMonth++; if (calMonth > 11) { calMonth = 0; calYear++; }
    renderCalendar(conciliadorState);
  });

  document.getElementById("btnGenerate").addEventListener("click", async () => {
    const desde = document.getElementById("selDesde").value, hasta = document.getElementById("selHasta").value;
    if (!desde || !hasta) { showToast("Elige la fecha de inicio y la de fin.", "critical"); return; }
    const btn = document.getElementById("btnGenerate");
    setLoading(btn, true);
    try {
      const res = await api().generate_report(desde, hasta);
      if (!res.ok) { showToast(res.error, "critical"); return; }
      const lines = res.reports.map((g) => {
        let l = `✓ ${g.path.split(/[\\/]/).pop()}`;
        if (g.omitidas) l += ` (${g.omitidas} transacciones no exitosas ignoradas)`;
        return l;
      });
      document.getElementById("generateResult").textContent = lines.join("  ·  ");
      document.getElementById("verifyResult").textContent = "";
      applyConciliadorState(res.state, { resetRange: false });
      showToast(`${res.reports.length} reporte(s) generado(s) en:\n${conciliadorState.out_dir}`, "good");
    } finally { setLoading(btn, false); }
  });

  document.getElementById("btnVerify").addEventListener("click", async () => {
    const btn = document.getElementById("btnVerify");
    setLoading(btn, true);
    try {
      const res = await api().run_verify();
      if (!res.ok) { showToast(res.error, "critical"); return; }
      let txt = `✓ ${res.coinciden} coinciden`;
      if (res.cruzados) txt += `, ${res.cruzados} cuadran en conjunto (cruce)`;
      txt += `, ${res.difieren} difieren (de ${res.total} revisados).`;
      document.getElementById("verifyResult").textContent = txt;
      showToast(txt + "\nQuedó registrado en el Historial.", res.difieren ? "critical" : "good");
    } finally { setLoading(btn, false); }
  });

  // ==================================================================
  // TRANSFERENCIAS
  // ==================================================================
  function renderTrChips(state) {
    const wrap = document.getElementById("trFileChips");
    wrap.innerHTML = "";
    if (!state.files.length) {
      const c = document.createElement("span"); c.className = "file-chip"; c.textContent = "Ningún PDF cargado todavía.";
      wrap.appendChild(c);
      return;
    }
    state.files.forEach((f) => { const c = document.createElement("span"); c.className = "file-chip"; c.textContent = f; wrap.appendChild(c); });
  }
  function applyTrState(state) {
    if (!state || state.ok === false) { if (state) showToast(state.error, "critical"); return; }
    renderTrChips(state);
    document.getElementById("trOutdirLabel").textContent = state.out_dir;
  }

  document.getElementById("btnUploadTrPdfs").addEventListener("click", async () => {
    applyTrState(await api().pick_transferencias_pdfs());
    document.getElementById("trResult").textContent = "";
  });
  document.getElementById("btnClearTr").addEventListener("click", async () => {
    applyTrState(await api().clear_transferencias());
    document.getElementById("trResult").textContent = "";
    document.getElementById("trLog").innerHTML = '<div class="log-empty">Listo para procesar.</div>';
  });
  document.getElementById("btnChooseTrOutdir").addEventListener("click", async () => {
    applyTrState(await api().choose_transferencias_outdir());
  });
  document.getElementById("btnProcesarTr").addEventListener("click", async () => {
    const btn = document.getElementById("btnProcesarTr");
    setLoading(btn, true);
    document.getElementById("trLog").innerHTML = "";
    document.getElementById("trResult").textContent = "";
    try {
      const res = await api().process_transferencias();
      if (!res.ok) { showToast(res.error, "critical"); return; }
      const pdfsList = (res.pdfs || []).map((p) => p.split(/[\\/]/).pop());
      document.getElementById("trResult").textContent =
        "✓ Listo: " + res.out_path.split(/[\\/]/).pop() +
        (pdfsList.length ? " — PDF exportado: " + pdfsList.join(", ") : "");
      showToast("Excel generado:\n" + res.out_path + (pdfsList.length ? "\n\nPDF:\n" + pdfsList.join("\n") : ""), "good");
    } finally { setLoading(btn, false); }
  });

  // ==================================================================
  // HISTORIAL
  // ==================================================================
  function renderBarList(containerId, rows, tipoClass) {
    const el = document.getElementById(containerId);
    el.innerHTML = "";
    const withFails = rows.filter((r) => r.fallidas > 0);
    if (!withFails.length) {
      el.innerHTML = '<div class="bar-empty">Sin fallas registradas en este rango — todo cuadró. ✓</div>';
      return;
    }
    const max = Math.max(...withFails.map((r) => r.fallidas));
    withFails.slice(0, 10).forEach((r) => {
      const row = document.createElement("div"); row.className = "bar-row";
      const pct = Math.max(6, Math.round((r.fallidas / max) * 100));
      row.innerHTML = `<div class="name" title="${r.punto_venta}">${r.punto_venta}</div>
        <div class="bar-track"><div class="bar-fill ${tipoClass}" data-pct="${pct}"></div></div>
        <div class="count">${r.fallidas}</div>`;
      el.appendChild(row);
    });
    anime({
      targets: `#${containerId} .bar-fill`, width: (elm) => elm.dataset.pct + "%",
      duration: 650, easing: "easeOutCubic", delay: anime.stagger(50),
    });
  }

  function renderTrend(rows) {
    const wrap = document.getElementById("trendWrap");
    if (!rows.length) { wrap.innerHTML = '<div class="trend-empty">Aún no hay suficientes verificaciones para mostrar tendencia.</div>'; return; }
    const w = 900, h = 110, padX = 6, padY = 14;
    const max = Math.max(1, ...rows.map((r) => r.fallidas));
    const step = rows.length > 1 ? (w - padX * 2) / (rows.length - 1) : 0;
    const pts = rows.map((r, i) => {
      const x = padX + step * i;
      const y = h - padY - (r.fallidas / max) * (h - padY * 2);
      return [x, y];
    });
    const line = pts.map((p, i) => (i === 0 ? "M" : "L") + p[0].toFixed(1) + "," + p[1].toFixed(1)).join(" ");
    const area = line + ` L${pts[pts.length - 1][0].toFixed(1)},${h} L${pts[0][0].toFixed(1)},${h} Z`;
    const last = rows[rows.length - 1];
    wrap.innerHTML = `<svg class="trend-svg" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">
        <path d="${area}" fill="var(--critical)" opacity="0.10"></path>
        <path d="${line}" fill="none" stroke="var(--critical)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="trend-line"></path>
      </svg>
      <div class="row" style="justify-content:space-between;margin-top:2px">
        <span class="muted-note" style="margin:0">${fmtDateShort(rows[0].fecha)}</span>
        <span class="muted-note" style="margin:0">${last.fallidas} fallida(s) el ${fmtDateShort(last.fecha)}</span>
      </div>`;
    const path = wrap.querySelector(".trend-line");
    const len = path.getTotalLength();
    path.style.strokeDasharray = len; path.style.strokeDashoffset = len;
    anime({ targets: path, strokeDashoffset: [len, 0], duration: 900, easing: "easeOutCubic" });
  }

  function renderRuns(runs) {
    const body = document.getElementById("runsBody");
    if (!runs.length) { body.innerHTML = '<tr><td colspan="4" class="empty-hint">Sin corridas registradas todavía.</td></tr>'; return; }
    body.innerHTML = "";
    runs.forEach((r) => {
      const tr = document.createElement("tr");
      const fecha = r.ts.replace("T", "  ·  ");
      const pillClass = r.fallidas > 0 ? "critical" : "good";
      const firstPath = (r.xlsx_path || "").split(";")[0].trim();
      tr.innerHTML = `<td class="mono">${fecha}</td><td>${r.total}</td>
        <td><span class="pill ${pillClass}"><span class="dot"></span>${r.fallidas}</span></td>
        <td><button class="link-btn">Abrir carpeta</button></td>`;
      tr.querySelector(".link-btn").addEventListener("click", () => firstPath && api().open_path(firstPath));
      body.appendChild(tr);
    });
  }

  async function loadHistorial() {
    const from = document.getElementById("histFrom").value || null;
    const to = document.getElementById("histTo").value || null;
    const [summaryRes, boldRes, redebanRes, tsRes, runsRes] = await Promise.all([
      api().get_historial_summary(from, to),
      api().get_historial_por_punto(from, to, "bold"),
      api().get_historial_por_punto(from, to, "redeban"),
      api().get_historial_timeseries(from, to),
      api().get_historial_runs(30),
    ]);

    const s = summaryRes.data;
    animateNumber(document.getElementById("kpiTotal"), s.total_general, fmtMoney);
    document.getElementById("kpiTotalSub").textContent = `Bold ${fmtMoney(s.total_bold)} · Redeban ${fmtMoney(s.total_redeban)}`;
    animateNumber(document.getElementById("kpiNoCoincidio"), s.total_no_coincidio, fmtMoney);
    document.getElementById("kpiNoCoincidioSub").textContent = `${s.no_coinciden} de ${s.revisados} revisadas no coincidieron`;
    animateNumber(document.getElementById("kpiDiferencia"), s.diferencia, fmtMoney);
    animateNumber(document.getElementById("kpiFallidasCount"), s.no_coinciden, (v) => Math.round(v).toLocaleString("es-CO"));
    document.getElementById("kpiFallidasSub").textContent = `Bold: ${s.fallidas_bold} · Redeban: ${s.fallidas_redeban}${s.cruzados ? ` · ${s.cruzados} cruzada(s)` : ""}`;

    renderBarList("barListBold", boldRes.data, "tipo-bold");
    renderBarList("barListRedeban", redebanRes.data, "tipo-redeban");
    renderTrend(tsRes.data);
    renderRuns(runsRes.data);
  }

  document.getElementById("btnHistFilter").addEventListener("click", loadHistorial);
  document.getElementById("btnHistClear").addEventListener("click", () => {
    document.getElementById("histFrom").value = ""; document.getElementById("histTo").value = "";
    loadHistorial();
  });

  // ------------------------------------------------------------------
  // Arranque
  // ------------------------------------------------------------------
  const MENSAJES_CARGA = ["Iniciando…", "Cargando el lector de Excel…", "Cargando el lector de PDF del banco…",
    "Preparando los módulos…", "Casi listo…"];

  function textoSplash(msg, esError) {
    const el = document.getElementById("splashTexto");
    if (!el) return;
    el.classList.add("cambia");
    setTimeout(() => {
      el.textContent = msg;
      el.classList.toggle("error", !!esError);
      el.classList.remove("cambia");
    }, 350);
  }

  // Los motores (Excel, PDF) se cargan en segundo plano en Python; la pantalla
  // de carga se queda hasta que bridge.estado_carga() diga que están listos.
  async function esperarMotores() {
    let i = 0;
    const rotar = setInterval(() => {
      i = Math.min(i + 1, MENSAJES_CARGA.length - 1);
      textoSplash(MENSAJES_CARGA[i]);
    }, 1800);
    try {
      for (;;) {
        const r = await api().estado_carga();
        if (r.error) {
          textoSplash(`No se pudo iniciar: ${r.error}. Cierra y vuelve a abrir el programa.`, true);
          return false;
        }
        if (r.listo) return true;
        await new Promise((res) => setTimeout(res, 250));
      }
    } finally {
      clearInterval(rotar);
    }
  }

  function ocultarSplash() {
    const el = document.getElementById("splash");
    if (!el) return;
    textoSplash("Listo");
    el.classList.add("saliendo");          // fundido de 3 s (transición en index.html)
    setTimeout(() => el.remove(), 3100);
  }

  whenApiReady(async () => {
    if (!(await esperarMotores())) return;
    document.querySelector('.screen[data-screen="home"]').classList.add("is-active");
    currentScreen = "home";
    updateTopbar("home"); updateNavActive("home");
    ocultarSplash();
    // La entrada de la app va más lenta que de costumbre para verse a través del fundido.
    anime({ targets: '.screen[data-screen="home"] .module-card', opacity: [0, 1], translateY: [24, 0], duration: 1100, delay: anime.stagger(110, { start: 500 }), easing: "easeOutCubic" });
    anime({ targets: ".sidebar .nav-item, .brand", opacity: [0, 1], translateX: [-10, 0], duration: 800, delay: anime.stagger(70, { start: 300 }), easing: "easeOutCubic" });

    try {
      applyConciliadorState(await api().get_conciliador_state(), { resetRange: true });
    } catch (e) { /* noop */ }
    try {
      applyTrState(await api().get_transferencias_state());
    } catch (e) { /* noop */ }
  });
})();
