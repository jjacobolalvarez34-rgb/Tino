# -*- coding: utf-8 -*-
"""
Suite Irina — punto de entrada único.
Ejecutar con:  python main.py
Requisitos:    pip install -r requirements.txt

La interfaz vive en webui/ (HTML/CSS/JS, con anime.js para las animaciones)
y corre embebida en una ventana nativa vía pywebview. Toda la lógica de
negocio (lectura de Excel/PDF, fórmulas, verificación bancaria) sigue en
core.py / verify.py / transferencias_core.py, sin tocar. bridge.py es el
único punto de contacto entre la interfaz y ese motor.

La interfaz anterior en Tkinter quedó en legacy_tkinter/ como respaldo
(ejecútala con `python legacy_tkinter/main.py` si hiciera falta).
"""
import os
import sys

import webview

from bridge import Api

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "webui", "index.html")


def main():
    api = Api()
    window = webview.create_window(
        "Suite Irina",
        INDEX_HTML,
        js_api=api,
        width=1280,
        height=880,
        min_size=(960, 640),
        background_color="#0A0912",   # mismo fondo que la pantalla de carga: sin destello
        text_select=True,
    )
    api.bind_window(window)
    debug = "--debug" in sys.argv
    # Perfil de WebView2 fijo: por defecto pywebview crea uno temporal en cada
    # arranque, y WebView2 tarda bastante más en iniciar un perfil nuevo.
    perfil = os.path.join(os.getenv("APPDATA") or os.path.expanduser("~"), "SuiteIrina", "webview")
    webview.start(debug=debug, private_mode=False, storage_path=perfil)


if __name__ == "__main__":
    main()
