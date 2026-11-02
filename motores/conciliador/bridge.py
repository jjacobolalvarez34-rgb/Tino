# -*- coding: utf-8 -*-
"""
bridge.py — API expuesta a la interfaz web (webui/) vía pywebview.
Envuelve la lógica ya validada de core.py / verify.py / transferencias_core.py
sin modificarla; esto es solo pegamento + diálogos nativos + registro
histórico en SQLite.
"""
import os
import json
import threading
import datetime as dt

import webview


# ---------------------------------------------------------------------------
# Carga en segundo plano: los motores (openpyxl, pdfplumber, pymupdf...) tardan
# ~10 s en importarse. Se importan en un hilo MIENTRAS arranca la ventana, y la
# pantalla de carga espera a `estado_carga()`. Cualquier uso de `core.algo` antes
# de que termine simplemente espera.
# ---------------------------------------------------------------------------
_MODULOS = {}
_ERRORES_CARGA = []


def _cargar_modulos():
    try:
        import core
        import verify
        import transferencias_core
        import historial_db
        import cierre_core
        historial_db.init_db()
        _MODULOS.update(core=core, verify=verify, transferencias_core=transferencias_core,
                        historial_db=historial_db, cierre_core=cierre_core)
    except Exception as e:
        _ERRORES_CARGA.append(f"{type(e).__name__}: {e}")


_cargador = threading.Thread(target=_cargar_modulos, name="carga-motores", daemon=True)


class _Perezoso:
    def __init__(self, nombre):
        self._nombre = nombre

    def __getattr__(self, attr):
        if _cargador.is_alive():
            _cargador.join()
        elif not _MODULOS and not _ERRORES_CARGA:
            _cargar_modulos()   # sin hilo: uso fuera de la app (pruebas, consola)
        if self._nombre not in _MODULOS:
            raise RuntimeError(f"No se pudo cargar {self._nombre}: {'; '.join(_ERRORES_CARGA)}")
        return getattr(_MODULOS[self._nombre], attr)


core = _Perezoso("core")
verify = _Perezoso("verify")
tc = _Perezoso("transferencias_core")
hdb = _Perezoso("historial_db")
cierre_core = _Perezoso("cierre_core")


def default_output_dir():
    home = os.path.expanduser("~")
    for candidate in ("Documents", "Documentos", "Desktop", "Escritorio"):
        p = os.path.join(home, candidate)
        if os.path.isdir(p):
            return p
    return home


def _err(msg):
    return {"ok": False, "error": msg}


class Api:
    def __init__(self):
        self._window = None

        # --- estado Conciliador Bold/Redeban ---
        self.bold_paths = []
        self.redeban_paths = []
        self.holidays = set()
        self.bank_pdf_path = None
        self.out_dir = default_output_dir()
        self.last_reports = []

        # --- estado Transferencias ---
        self.tr_paths = []
        self.tr_out_dir = default_output_dir()

        # --- estado Cierre del día (se crea al entrar a la pantalla) ---
        self._cierre = None

        if not _cargador.is_alive() and not _MODULOS:
            _cargador.start()

    # ------------------------------------------------------------------
    def bind_window(self, window):
        self._window = window

    def _log_js(self, msg):
        if self._window is not None:
            try:
                import json as _json
                self._window.evaluate_js(f"window.__appendLog && window.__appendLog({_json.dumps(msg)})")
            except Exception:
                pass

    # ==================================================================
    # Generales
    # ==================================================================
    def open_path(self, path):
        try:
            os.startfile(path)
            return {"ok": True}
        except Exception as e:
            return _err(str(e))

    def get_home_state(self):
        return {"ok": True}

    def estado_carga(self):
        """La pantalla de carga pregunta esto hasta que los motores estén listos."""
        if _ERRORES_CARGA:
            return {"listo": False, "error": "; ".join(_ERRORES_CARGA)}
        return {"listo": bool(_MODULOS) and not _cargador.is_alive(), "error": None}

    # ==================================================================
    # Conciliador Bold / Redeban
    # ==================================================================
    def _conciliador_state(self):
        bold_dates = []
        if self.bold_paths:
            try:
                rows, formato, omitidas = core.load_bold_multi(self.bold_paths)
                bold_date_objs = core.get_available_dates(rows, "bold")
                bold_dates = [d.isoformat() for d in bold_date_objs]
                self._prune_stale_holidays(bold_date_objs)
            except Exception:
                formato, omitidas = None, 0
        else:
            formato, omitidas = None, 0

        redeban_dates = []
        if self.redeban_paths:
            try:
                rrows = core.load_redeban_multi(self.redeban_paths)
                redeban_dates = [d.isoformat() for d in core.get_available_dates(rrows, "redeban")]
            except Exception:
                pass

        all_dates = sorted(set(bold_dates) | set(redeban_dates))

        return {
            "ok": True,
            "bold_files": [os.path.basename(p) for p in self.bold_paths],
            "redeban_files": [os.path.basename(p) for p in self.redeban_paths],
            "dates": all_dates,
            "bold_available_dates": bold_dates,
            "has_bold": bool(self.bold_paths),
            "formato": formato,
            "omitidas": omitidas,
            "out_dir": self.out_dir,
            "holidays": sorted(h.isoformat() for h in self.holidays),
            "bank_pdf": os.path.basename(self.bank_pdf_path) if self.bank_pdf_path else None,
            "last_reports": [{"kind": g["kind"], "path": g["out_path"]} for g in self.last_reports],
        }

    def get_conciliador_state(self):
        return self._conciliador_state()

    def _prune_stale_holidays(self, bold_date_objs):
        """Si se sube un archivo Bold de un mes distinto sin darle antes a
        'Quitar todos', los festivos marcados para el archivo ANTERIOR se
        quedaban guardados y se seguían aplicando en silencio (el 'caché'
        que reportaron). Aquí se descartan los festivos que ya no caen
        cerca del rango de fechas del archivo actualmente cargado."""
        if not bold_date_objs or not self.holidays:
            return
        margin = dt.timedelta(days=10)
        low = min(bold_date_objs) - margin
        high = max(bold_date_objs) + margin
        self.holidays = {h for h in self.holidays if low <= h <= high}

    def pick_conciliador_files(self):
        if self._window is None:
            return _err("Ventana no lista.")
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Excel (*.xlsx)", "Todos los archivos (*.*)"))
        if not result:
            return self._conciliador_state()

        new_bold, new_redeban = [], []
        try:
            for p in result:
                k = core.detect_file_type(p)
                (new_bold if k == "bold" else new_redeban).append(p)
        except core.FormatoNoReconocido as e:
            return _err(str(e))
        except Exception as e:
            return _err(f"Error al leer el archivo: {e}")

        self.bold_paths.extend(new_bold)
        self.redeban_paths.extend(new_redeban)
        self.last_reports = []
        return self._conciliador_state()

    def clear_conciliador_files(self):
        self.bold_paths = []
        self.redeban_paths = []
        self.holidays = set()
        self.last_reports = []
        return self._conciliador_state()

    def choose_conciliador_outdir(self):
        if self._window is None:
            return _err("Ventana no lista.")
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=self.out_dir)
        if result:
            self.out_dir = result[0]
        return self._conciliador_state()

    def toggle_holiday(self, iso_date):
        d = dt.date.fromisoformat(iso_date)
        if d in self.holidays:
            self.holidays.discard(d)
        else:
            self.holidays.add(d)
        return self._conciliador_state()

    def pick_bank_pdf(self):
        if self._window is None:
            return _err("Ventana no lista.")
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("PDF (*.pdf)", "Todos los archivos (*.*)"))
        if result:
            self.bank_pdf_path = result[0]
        return self._conciliador_state()

    def _ensure_out_dir(self, path):
        if not path:
            return _err("Elige una carpeta de destino válida.")
        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            return _err(f"No se pudo crear ni acceder a:\n{path}\n\nDetalle: {e}")
        if not os.path.isdir(path):
            return _err(f"La carpeta no está disponible ahora mismo:\n{path}")
        return None

    def _safe_save_path(self, out_path):
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except PermissionError:
                return _err(
                    f"No pude reemplazar este archivo porque está abierto en otro "
                    f"programa (probablemente Excel):\n{out_path}\n\nCiérralo e inténtalo de nuevo.")
        return None

    def generate_report(self, date_start_iso, date_end_iso):
        if not self.bold_paths and not self.redeban_paths:
            return _err("Primero sube al menos un archivo virgen.")
        try:
            date_start = dt.date.fromisoformat(date_start_iso)
            date_end = dt.date.fromisoformat(date_end_iso)
        except Exception:
            return _err("Elige la fecha de inicio y la de fin.")
        if date_start > date_end:
            date_start, date_end = date_end, date_start

        err = self._ensure_out_dir(self.out_dir)
        if err:
            return err

        jobs = []
        if self.bold_paths:
            jobs.append(("bold", self.bold_paths, []))
        if self.redeban_paths:
            jobs.append(("redeban", [], self.redeban_paths))

        generated = []
        for kind_hint, bp, rp in jobs:
            tentative_name = core.build_filename(kind_hint, date_start, date_end)
            out_path = os.path.join(self.out_dir, tentative_name)
            err = self._safe_save_path(out_path)
            if err:
                return err
            try:
                kind, info = core.process_combined(bp, rp, date_start, date_end,
                                                     out_path, holidays=self.holidays)
            except core.FormatoNoReconocido as e:
                return _err(str(e))
            except (OSError, PermissionError) as e:
                return _err(f"No se pudo escribir en:\n{out_path}\n\nDetalle: {e}")
            except Exception as e:
                return _err(f"Error al procesar: {e}")

            real_name = core.build_filename(kind, info["settlement_start"], info["settlement_end"])
            real_path = os.path.join(self.out_dir, real_name)
            final_path = out_path
            if real_path != out_path:
                try:
                    if os.path.exists(real_path):
                        os.remove(real_path)
                    os.rename(out_path, real_path)
                    final_path = real_path
                except OSError:
                    final_path = out_path

            generated.append({"kind": kind, "out_path": final_path, "info": info})

        self.last_reports = generated
        return {
            "ok": True,
            "reports": [{"kind": g["kind"], "path": g["out_path"],
                         "omitidas": g["info"].get("omitidas", 0)} for g in generated],
            "state": self._conciliador_state(),
        }

    @staticmethod
    def _bold_rows_for_historial(results):
        rows = []
        for r in results:
            breakdown = r.get("store_breakdown") or {}
            block_total = r["computed_total"]
            bank_total = r["bank_total"]
            for store, monto in breakdown.items():
                share = (monto / block_total) if block_total else 0.0
                rows.append({
                    "tipo": "bold", "punto_venta": store, "franquicia": None,
                    "fecha": r["settlement_date"], "computed_total": monto,
                    "bank_total": bank_total * share, "matched": r["matched"],
                    "cruzado": False,
                })
        return rows

    @staticmethod
    def _redeban_rows_for_historial(results):
        rows = []
        for r in results:
            if r.get("no_data"):
                continue
            rows.append({
                "tipo": "redeban",
                "punto_venta": core.REDEBAN_STORES.get(r["code"], r["code"]),
                "franquicia": r["franquicia"], "fecha": r["canje_date"],
                "computed_total": r["computed_total"], "bank_total": r["bank_total"],
                "matched": r["matched"], "cruzado": r.get("cruzado", False),
            })
        return rows

    def run_verify(self):
        if not self.last_reports:
            return _err("Primero genera el/los reporte(s) en la sección de arriba.")
        if not self.bank_pdf_path:
            return _err("Sube el PDF de movimientos de Bancolombia.")
        for g in self.last_reports:
            if not os.path.exists(g["out_path"]):
                return _err(f"No encuentro el reporte generado en:\n{g['out_path']}\nVuelve a generarlo arriba.")

        err = self._ensure_out_dir(self.out_dir)
        if err:
            return err

        out_pdf_name = os.path.splitext(os.path.basename(self.bank_pdf_path))[0] + " (anotado).pdf"
        out_pdf = os.path.join(self.out_dir, out_pdf_name)
        err = self._safe_save_path(out_pdf)
        if err:
            return err

        all_results = []
        historial_rows = []
        try:
            bank_entries = verify.parse_bancolombia_pdf(self.bank_pdf_path)
            for g in self.last_reports:
                jobs = []
                if g["info"].get("verificacion_bold"):
                    jobs.append(("bold", core.AGG_SHEET_BOLD, g["info"]["verificacion_bold"]))
                if g["info"].get("verificacion_redeban"):
                    jobs.append(("redeban", core.AGG_SHEET_REDEBAN, g["info"]["verificacion_redeban"]))
                for kind, sheet_name, verificacion in jobs:
                    if not verificacion:
                        continue
                    if kind == "bold":
                        results = verify.match_bold(bank_entries, verificacion)
                        verify.color_excel_bold(g["out_path"], sheet_name, results)
                        historial_rows.extend(self._bold_rows_for_historial(results))
                    else:
                        results = verify.match_redeban(bank_entries, verificacion)
                        verify.color_excel_redeban(g["out_path"], sheet_name, results)
                        historial_rows.extend(self._redeban_rows_for_historial(results))
                    all_results.extend(results)
            verify.annotate_pdf(self.bank_pdf_path, all_results, out_pdf)
        except (OSError, PermissionError) as e:
            return _err(f"No se pudo escribir en:\n{out_pdf}\n\nDetalle: {e}")
        except Exception as e:
            return _err(f"Error al verificar: {e}")

        run_id = None
        try:
            run_id = hdb.record_verification(
                xlsx_path="; ".join(g["out_path"] for g in self.last_reports),
                pdf_path=self.bank_pdf_path, rows=historial_rows)
        except Exception:
            pass  # el registro histórico nunca debe tumbar una verificación ya exitosa

        checked = [r for r in all_results if not r.get("no_data")]
        cruzados = sum(1 for r in checked if r.get("cruzado"))
        ok = sum(1 for r in checked if r["matched"] and not r.get("cruzado"))
        bad = len(checked) - ok - cruzados

        return {
            "ok": True, "total": len(checked), "coinciden": ok,
            "cruzados": cruzados, "difieren": bad, "out_pdf": out_pdf,
            "run_id": run_id,
            "reports": [g["out_path"] for g in self.last_reports],
        }

    # ==================================================================
    # Transferencias por punto de venta
    # ==================================================================
    def _tr_state(self):
        return {
            "ok": True,
            "files": [os.path.basename(p) for p in self.tr_paths],
            "out_dir": self.tr_out_dir,
        }

    def get_transferencias_state(self):
        return self._tr_state()

    def pick_transferencias_pdfs(self):
        if self._window is None:
            return _err("Ventana no lista.")
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Documentos (*.pdf;*.zip;*.rar)", "Todos los archivos (*.*)"))
        if result:
            self.tr_paths = list(result)
        return self._tr_state()

    def clear_transferencias(self):
        self.tr_paths = []
        return self._tr_state()

    def choose_transferencias_outdir(self):
        if self._window is None:
            return _err("Ventana no lista.")
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER, directory=self.tr_out_dir)
        if result:
            self.tr_out_dir = result[0]
        return self._tr_state()

    def process_transferencias(self):
        if not self.tr_paths:
            return _err("Primero sube al menos un PDF.")
        err = self._ensure_out_dir(self.tr_out_dir)
        if err:
            return err
        try:
            salida, pdfs = tc.procesar_pdfs(self.tr_paths, carpeta_destino=self.tr_out_dir, log=self._log_js)
            return {"ok": True, "out_path": salida, "pdfs": pdfs}
        except Exception as e:
            return _err(str(e))

    # ==================================================================
    # Historial / Dashboard
    # ==================================================================
    def get_historial_summary(self, date_from=None, date_to=None):
        return {"ok": True, "data": hdb.get_summary(date_from or None, date_to or None)}

    def get_historial_por_punto(self, date_from=None, date_to=None, tipo=None):
        return {"ok": True, "data": hdb.get_por_punto_venta(date_from or None, date_to or None, tipo or None)}

    def get_historial_timeseries(self, date_from=None, date_to=None):
        return {"ok": True, "data": hdb.get_timeseries(date_from or None, date_to or None)}

    def get_historial_runs(self, limit=30):
        return {"ok": True, "data": hdb.get_runs(limit)}

    # ==================================================================
    # Cierre del día
    # ==================================================================
    # OJO: la sesión va en un atributo con "_" a propósito. pywebview recorre
    # todos los atributos públicos de esta clase para exponerlos a JS, y
    # meterse en los libros leídos (miles de celdas) sería lentísimo.
    def _sesion_cierre(self):
        if self._cierre is None:
            self._cierre = cierre_core.SesionCierre()
        return self._cierre

    def _log_cierre(self, msg):
        if self._window is not None:
            try:
                self._window.evaluate_js(f"window.__cierreLog && window.__cierreLog({json.dumps(msg)})")
            except Exception:
                pass

    def _cierre_state(self):
        s = self._sesion_cierre()
        fechas = [f.isoformat() for f in s.fechas_disponibles()]
        ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        sugerida = ayer if ayer in fechas else (fechas[-1] if fechas else None)
        meses_archivos = sorted({f.isoformat()[:7] for f in s.fechas_en_archivos()})
        return {"ok": True, "archivos": s.estado_archivos(), "fechas": fechas, "sugerida": sugerida,
                "meses": s.meses_disponibles(), "meses_archivos": meses_archivos,
                "puntos": [{"id": p["id"], "nombre": p["nombre"]} for p in s.config["puntos"]],
                "siigo": s.estado_siigo(),
                "banco": s.estado_banco(),
                "tarjetas": s.estado_tarjetas(),
                "mapeo": {"archivo": os.path.basename(s.ruta_mapeo()),
                          "propio": s.ruta_mapeo() == cierre_core.MAPEO_USUARIO},
                "no_asignados": [{"archivo": os.path.basename(r), "motivo": m} for r, m in s.no_asignados]}

    def cierre_estado(self):
        try:
            return self._cierre_state()
        except Exception as e:
            return _err(f"No se pudo iniciar Cierre del día: {e}")

    def cierre_cargar_xlsx(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Excel (*.xlsx)", "Todos los archivos (*.*)"))
        if not rutas:
            return self._cierre_state()
        try:
            resultado = self._sesion_cierre().cargar_xlsx(list(rutas), log=self._log_cierre)
        except Exception as e:
            return _err(f"Error al leer los archivos: {e}")
        estado = self._cierre_state()
        estado["cargados"] = resultado
        return estado

    def cierre_cargar_siigo(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Excel (*.xlsx)", "Todos los archivos (*.*)"))
        if not rutas:
            return self._cierre_state()
        try:
            resultado = self._sesion_cierre().cargar_siigo(list(rutas))
        except Exception as e:
            return _err(f"Error al leer el reporte de Siigo: {e}")
        estado = self._cierre_state()
        estado["siigo_cargados"] = resultado
        return estado

    def cierre_cargar_tarjetas(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Excel (*.xlsx)", "Todos los archivos (*.*)"))
        if not rutas:
            return self._cierre_state()
        try:
            resultado = self._sesion_cierre().cargar_tarjetas(list(rutas))
        except Exception as e:
            return _err(f"Error al leer los reportes de tarjetas: {e}")
        estado = self._cierre_state()
        estado["tarjetas_cargados"] = resultado
        return estado

    def cierre_cargar_banco(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Banco (*.pdf;*.zip;*.xlsx)", "Todos los archivos (*.*)"))
        if not rutas:
            return self._cierre_state()
        try:
            resultado = self._sesion_cierre().cargar_banco(list(rutas))
        except Exception as e:
            return _err(f"Error al leer lo del banco: {e}")
        estado = self._cierre_state()
        estado["banco_cargados"] = resultado
        return estado

    # ---------------- Google Sheets ----------------
    def cierre_google_estado(self):
        try:
            return {"ok": True, **self._sesion_cierre().google_estado()}
        except Exception as e:
            return _err(f"No se pudo revisar la conexión con Google: {e}")

    def cierre_google_credenciales(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("JSON (*.json)", "Todos los archivos (*.*)"))
        if not rutas:
            return self.cierre_google_estado()
        try:
            self._sesion_cierre().google.guardar_credenciales(rutas[0])
        except Exception as e:
            return _err(str(e))
        return self.cierre_google_estado()

    def cierre_google_conectar(self):
        try:
            self._sesion_cierre().google.conectar()
        except Exception as e:
            return _err(str(e))
        return self.cierre_google_estado()

    def cierre_google_desconectar(self):
        self._sesion_cierre().google.desconectar()
        return self.cierre_google_estado()

    def cierre_google_buscar(self, mes):
        try:
            return {"ok": True, "data": self._sesion_cierre().google_buscar(mes)}
        except Exception as e:
            return _err(str(e))

    def cierre_google_cargar(self, mes, puntos, transferencias):
        s = self._sesion_cierre()
        try:
            s.google_guardar_asignacion(mes, puntos or {}, transferencias)
            resultado = s.google_cargar(mes, log=self._log_cierre)
        except Exception as e:
            return _err(str(e))
        estado = self._cierre_state()
        estado["google_cargados"] = resultado
        return estado

    def cierre_cargar_mapeo(self):
        if self._window is None:
            return _err("Ventana no lista.")
        rutas = self._window.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("Excel (*.xlsx)", "Todos los archivos (*.*)"))
        if not rutas:
            return self._cierre_state()
        try:
            info = self._sesion_cierre().cargar_mapeo_siigo(rutas[0])
        except Exception as e:
            return _err(f"Ese archivo no sirve como mapeo de Siigo: {e}")
        estado = self._cierre_state()
        estado["mapeo_cargado"] = info
        return estado

    def cierre_quitar_todos(self):
        self._sesion_cierre().quitar_todos()
        return self._cierre_state()

    def cierre_revisar(self, fecha_iso):
        if not fecha_iso:
            return _err("Elige la fecha a revisar.")
        try:
            return {"ok": True, "data": self._sesion_cierre().revisar(fecha_iso)}
        except Exception as e:
            return _err(f"Error al revisar: {e}")

    def cierre_revisar_mes(self, mes):
        if not mes:
            return _err("Elige el mes.")
        try:
            n = self._sesion_cierre().revisar_mes(mes, log=self._log_cierre)
        except Exception as e:
            return _err(f"Error al revisar el mes: {e}")
        estado = self._cierre_state()
        estado["revisados"] = n
        return estado

    def cierre_marcar(self, hallazgo_id, revision, nota=""):
        try:
            return {"ok": True, "hallazgo": self._sesion_cierre().marcar(hallazgo_id, revision, nota)}
        except Exception as e:
            return _err(str(e))

    def cierre_vista_punto(self, punto, mes):
        try:
            return {"ok": True, "data": self._sesion_cierre().vista_punto(punto, mes)}
        except Exception as e:
            return _err(f"No se pudo armar la vista del punto: {e}")

    def cierre_vista_asesoras(self, mes):
        try:
            return {"ok": True, "data": self._sesion_cierre().vista_asesoras(mes)}
        except Exception as e:
            return _err(f"No se pudo armar la vista de asesoras: {e}")

    def cierre_vista_pendientes(self, incluir_menores=False):
        try:
            return {"ok": True, "data": self._sesion_cierre().vista_pendientes(bool(incluir_menores))}
        except Exception as e:
            return _err(f"No se pudo leer los pendientes: {e}")

    def cierre_abrir_archivo(self, punto):
        ruta = self._sesion_cierre().archivos.get(punto)
        if not ruta:
            return _err("Ese punto no tiene archivo cargado.")
        return self.open_path(ruta)

