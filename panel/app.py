# -*- coding: utf-8 -*-
"""Tino en una ventana: la revisión del día y el tablero de ventas, sin usar la consola.

Cada pantalla se guarda como HTML junto a puntos.json y se abre en el navegador. Lo propio
de la empresa sale de puntos.json, que vive fuera del programa. Nada se sube a internet.

Para probar sin ventana, con los mismos argumentos de cada armar.py:
    app.py --revision --fecha ... --puntos ... --salida ... --excel ...
    app.py --tablero --puntos ... --salida ... reporte.xlsx ...
"""
import datetime as dt
import queue
import sys
import threading
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(RAIZ / "motores" / "conciliador")]

from panel.revision import armar as revision  # noqa: E402
from panel.tablero import armar as tablero  # noqa: E402

FONDO, TINTA, SUAVE = "#F7F5F7", "#22161F", "#5E5862"


def buscar_puntos():
    """puntos.json junto al programa o en una carpeta Tino-datos de más arriba."""
    inicio = Path(sys.executable).parent if getattr(sys, "frozen", False) else RAIZ
    for carpeta in [inicio, *inicio.parents]:
        for candidato in (carpeta / "puntos.json", carpeta / "Tino-datos" / "puntos.json"):
            if candidato.exists():
                return candidato
    return None


def ventana():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    raiz = tk.Tk()
    raiz.title("Tino")
    raiz.geometry("680x560")
    raiz.configure(bg=FONDO)
    estilo = ttk.Style()
    estilo.configure(".", background=FONDO, foreground=TINTA, font=("Segoe UI", 11))
    estilo.configure("Titulo.TLabel", font=("Segoe UI", 18, "bold"))
    estilo.configure("Suave.TLabel", foreground=SUAVE, font=("Segoe UI", 10))
    estilo.configure("TButton", padding=8)
    estilo.configure("TNotebook.Tab", padding=(16, 8))

    encontrado = buscar_puntos()
    puntos = tk.StringVar(value=str(encontrado) if encontrado else "")
    resultados = queue.Queue()

    def en_segundo_plano(boton, estado, trabajo):
        """Lee los archivos sin congelar la ventana; al terminar abre el HTML."""
        boton.state(["disabled"])
        estado.set("Leyendo archivos… puede tardar un minuto por cada Excel.")

        def correr():
            try:
                resultados.put((boton, estado, trabajo(), None))
            except Exception as e:  # noqa: BLE001 - se muestra a quien usa la ventana
                resultados.put((boton, estado, None, e))

        threading.Thread(target=correr, daemon=True).start()

    def revisar_cola():
        while not resultados.empty():
            boton, estado, salida, error = resultados.get()
            boton.state(["!disabled"])
            if error:
                estado.set("")
                messagebox.showerror("No se pudo armar", str(error))
            else:
                estado.set(f"Listo: {salida}")
                webbrowser.open(Path(salida).as_uri())
        raiz.after(200, revisar_cola)

    def carpeta_salida(nombre):
        carpeta = Path(puntos.get()).parent / nombre
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def puntos_listo():
        if not puntos.get() or not Path(puntos.get()).exists():
            messagebox.showwarning("Configuración", "Elija el archivo puntos.json de la empresa.")
            return False
        return True

    def selector(marco, fila, texto, tipos, destino):
        resumen = tk.StringVar(value="Ninguno")

        def elegir():
            rutas = filedialog.askopenfilenames(title=texto, filetypes=tipos)
            if rutas:
                destino[:] = list(rutas)
                resumen.set(f"{len(rutas)} archivo(s)")

        ttk.Label(marco, text=texto).grid(row=fila, column=0, sticky="w")
        ttk.Button(marco, text="Elegir…", command=elegir).grid(row=fila, column=1, sticky="w", pady=6)
        ttk.Label(marco, textvariable=resumen, style="Suave.TLabel").grid(row=fila, column=2, sticky="w", padx=8)

    cabeza = ttk.Frame(raiz, padding=(24, 20, 24, 8))
    cabeza.pack(fill="x")
    ttk.Label(cabeza, text="Tino", style="Titulo.TLabel").grid(row=0, column=0, sticky="w")
    ttk.Label(cabeza, text="Configuración de la empresa:", style="Suave.TLabel").grid(row=1, column=0, sticky="w")
    ttk.Label(cabeza, textvariable=puntos, style="Suave.TLabel", wraplength=380).grid(row=1, column=1, sticky="w", padx=6)

    def cambiar_puntos():
        ruta = filedialog.askopenfilename(title="puntos.json de la empresa", filetypes=[("JSON", "*.json")])
        if ruta:
            puntos.set(ruta)

    ttk.Button(cabeza, text="Cambiar…", command=cambiar_puntos).grid(row=1, column=2, sticky="w")

    pestanas = ttk.Notebook(raiz)
    pestanas.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    # Revisión del día
    rev = ttk.Frame(pestanas, padding=20)
    pestanas.add(rev, text="Revisión del día")
    ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    fecha = tk.StringVar(value=ayer)
    excel, banco, tarj = [], [], []
    ttk.Label(rev, text="Fecha (AAAA-MM-DD)").grid(row=0, column=0, sticky="w")
    ttk.Entry(rev, textvariable=fecha, width=14).grid(row=0, column=1, sticky="w", pady=6)
    selector(rev, 1, "Excel del día de cada punto", [("Excel", "*.xlsx")], excel)
    selector(rev, 2, "Extracto de Bancolombia (PDF)", [("PDF", "*.pdf")], banco)
    selector(rev, 3, "Reportes de Bold y Redeban", [("Excel", "*.xlsx")], tarj)
    estado_rev = tk.StringVar()
    ttk.Label(rev, textvariable=estado_rev, style="Suave.TLabel", wraplength=560).grid(
        row=5, column=0, columnspan=3, sticky="w", pady=(16, 0))

    def revisar():
        dia = fecha.get().strip()
        try:
            dt.date.fromisoformat(dia)
        except ValueError:
            messagebox.showwarning("Fecha", "Escriba la fecha así: 2026-09-26.")
            return
        if not puntos_listo():
            return
        if not excel:
            messagebox.showwarning("Archivos", "Elija al menos un Excel del día.")
            return

        def trabajo():
            salida = carpeta_salida("revisiones") / f"revision_{dia}.html"
            revision.generar(dia, puntos.get(), salida, excel, banco, tarj)
            return salida

        en_segundo_plano(boton_rev, estado_rev, trabajo)

    boton_rev = ttk.Button(rev, text="Revisar", command=revisar)
    boton_rev.grid(row=4, column=0, sticky="w", pady=(20, 0))

    # Tablero de ventas
    tab = ttk.Frame(pestanas, padding=20)
    pestanas.add(tab, text="Tablero de ventas")
    reportes = []
    ttk.Label(tab, text="Ventas con tarjeta por punto y por mes, desde los reportes de Bold y Redeban.",
              style="Suave.TLabel", wraplength=560).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
    selector(tab, 1, "Reportes de Bold y Redeban", [("Excel", "*.xlsx")], reportes)
    estado_tab = tk.StringVar()
    ttk.Label(tab, textvariable=estado_tab, style="Suave.TLabel", wraplength=560).grid(
        row=3, column=0, columnspan=3, sticky="w", pady=(16, 0))

    def armar_tablero():
        if not puntos_listo():
            return
        if not reportes:
            messagebox.showwarning("Archivos", "Elija al menos un reporte de Bold o Redeban.")
            return

        def trabajo():
            salida = carpeta_salida("tableros") / f"tablero_{dt.date.today().isoformat()}.html"
            tablero.generar(puntos.get(), salida, reportes)
            return salida

        en_segundo_plano(boton_tab, estado_tab, trabajo)

    boton_tab = ttk.Button(tab, text="Armar tablero", command=armar_tablero)
    boton_tab.grid(row=2, column=0, sticky="w", pady=(20, 0))

    revisar_cola()
    raiz.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--revision", "--tablero"):
        modo = sys.argv.pop(1)
        (revision if modo == "--revision" else tablero).main()
    else:
        ventana()
