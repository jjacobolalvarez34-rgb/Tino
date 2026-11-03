# -*- coding: utf-8 -*-
"""Tino en una ventana: la revisión del día y las ventas con tarjeta, sin usar la consola.

La ventana es HTML (panel/inicio.html), con los tokens de docs/DESIGN.md, dentro del motor de
Edge (WebView2) que trae Windows. Cada resultado se guarda como HTML junto a puntos.json y
se abre en otra ventana. Lo propio de la empresa sale de puntos.json, fuera del programa.

Para probar sin ventana, con los mismos argumentos de cada armar.py:
    app.py --revision --fecha ... --puntos ... --salida ... --excel ...
    app.py --tablero --puntos ... --salida ... reporte.xlsx ...
"""
import datetime as dt
import os
import sys
from pathlib import Path

CONGELADO = getattr(sys, "frozen", False)
RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ), str(RAIZ / "motores"), str(RAIZ / "motores" / "conciliador")]

from panel.revision import armar as revision  # noqa: E402
from panel.tablero import armar as tablero  # noqa: E402

# Lo que el programa guarda para sí (temporales y datos de la ventana) va junto a él, no
# en el disco del sistema: en el computador de pruebas, C: está lleno (D-034).
PROPIO = Path(sys.executable).parent if CONGELADO else RAIZ / ".ventana"
INICIO = (Path(sys._MEIPASS) if CONGELADO else Path(__file__).parent) / "inicio.html"
CONECTADO = (Path(sys._MEIPASS) if CONGELADO else Path(__file__).parent) / "tino.html"


def buscar(nombre):
    """Un archivo de configuración junto al programa o en una carpeta Tino-datos de más arriba."""
    inicio = Path(sys.executable).parent if CONGELADO else RAIZ
    for carpeta in [inicio, *inicio.parents]:
        for candidato in (carpeta / nombre, carpeta / "Tino-datos" / nombre):
            if candidato.exists():
                return candidato
    return None


def buscar_puntos():
    return buscar("puntos.json")


def abrir_html(titulo, ruta):
    import webview
    webview.create_window(f"Tino · {titulo}", url=Path(ruta).as_uri(), width=1280, height=720,
                          min_size=(400, 500), background_color="#F7F5F7")


class ApiConectada:
    """El programa conectado a la base: cada método devuelve {datos} o {error}.

    tino.json trae la dirección de Supabase y la llave pública, nunca la de servicio. La
    sesión vive solo en memoria: al cerrar el programa hay que volver a entrar.
    """

    def __init__(self, servicio, carpeta, correo=""):
        self._s, self._carpeta, self._correo = servicio, Path(carpeta), correo
        self._ventana, self._sesion = None, None

    def _envolver(self, trabajo):
        try:
            return {"datos": trabajo()}
        except Exception as e:  # noqa: BLE001 - se muestra en la pantalla
            return {"error": str(e) or e.__class__.__name__}

    def estado(self):
        ayer = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        return {"datos": {"ayer": ayer, "correo": self._correo, "sesion": self._sesion}}

    def entrar(self, correo, clave):
        def trabajo():
            self._sesion = self._s.entrar(correo, clave)
            return self._sesion
        return self._envolver(trabajo)

    def salir(self):
        self._s.c.token, self._sesion = None, None
        return {"datos": True}

    def archivos(self):
        return self._envolver(self._s.archivos)

    def errores(self):
        return self._envolver(self._s.errores)

    def elegir_y_preparar(self):
        import webview
        rutas = self._ventana.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True,
            file_types=("Archivos de Tino (*.xlsx;*.pdf)", "Excel (*.xlsx)", "Extracto en PDF (*.pdf)"))
        return self._envolver(lambda: self._s.preparar(list(rutas or [])))

    def subir(self, clave):
        return self._envolver(lambda: self._s.subir(clave))

    def deshacer(self, archivo_id):
        return self._envolver(lambda: self._s.deshacer(archivo_id))

    def _guardar_y_abrir(self, nombre, plantilla, datos, titulo):
        import json
        carpeta = self._carpeta / nombre[0]
        carpeta.mkdir(parents=True, exist_ok=True)
        salida = carpeta / nombre[1]
        texto = json.dumps(datos, ensure_ascii=False).replace("</", "<\\/")
        salida.write_text(plantilla.read_text(encoding="utf-8").replace("/*DATOS*/null", texto), encoding="utf-8")
        abrir_html(titulo, salida)

    def revisar_dia(self, fecha):
        def trabajo():
            r = self._s.revision_dia(fecha)
            con_excel = sum(1 for p in r["puntos"] if not p.get("sin_excel"))
            if con_excel:
                self._guardar_y_abrir(("revisiones", f"revision_{fecha}.html"), revision.PLANTILLA, r, f"revisión {fecha}")
            return {"puntos": con_excel}
        return self._envolver(trabajo)

    def transferencias(self, desde, hasta):
        return self._envolver(lambda: self._s.transferencias(desde, hasta))

    def decidir_transferencia(self, pago_id, estado, nota):
        return self._envolver(lambda: self._s.decidir_transferencia(pago_id, estado, nota))

    def por_confirmar(self):
        return self._envolver(self._s.por_confirmar)

    def decidir_cruce(self, cruce_id, estado, nota):
        return self._envolver(lambda: self._s.decidir_cruce(cruce_id, estado, nota))

    def descuadres(self, desde, hasta):
        return self._envolver(lambda: self._s.descuadres(desde, hasta))

    def pruebas(self, descuadre_id):
        return self._envolver(lambda: self._s.pruebas(descuadre_id))

    def cerrar_descuadre(self, descuadre_id, estado, nota):
        return self._envolver(lambda: self._s.cerrar_descuadre(descuadre_id, estado, nota))

    def tablero(self, desde, hasta):
        def trabajo():
            cobros = self._s.cobros(desde, hasta)
            if cobros:
                self._guardar_y_abrir(("tableros", f"tablero_{desde}_a_{hasta}.html"), tablero.PLANTILLA,
                                      tablero.armar_datos(cobros, []), "ventas con tarjeta")
            return {"cobros": len(cobros)}
        return self._envolver(trabajo)


class Api:
    """Lo que la pantalla puede pedirle a Python. Solo lee archivos y escribe HTML."""

    def __init__(self):
        self._puntos = buscar_puntos()
        self._ventana = None

    def estado(self):
        ayer = dt.date.today() - dt.timedelta(days=1)
        return {"ayer": ayer.isoformat(), "puntos": str(self._puntos) if self._puntos else None}

    def _dialogo(self, tipos, varios=True):
        import webview
        return self._ventana.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=varios, file_types=tipos)

    def elegir(self, tipo):
        tipos = ("Extracto en PDF (*.pdf)",) if tipo == "banco" else ("Excel (*.xlsx)",)
        return list(self._dialogo(tipos) or [])

    def cambiar_puntos(self):
        rutas = self._dialogo(("Configuración (*.json)",), varios=False)
        if rutas:
            self._puntos = Path(rutas[0] if isinstance(rutas, (list, tuple)) else rutas)
            return str(self._puntos)
        return None

    def _carpeta(self, nombre):
        carpeta = self._puntos.parent / nombre
        carpeta.mkdir(parents=True, exist_ok=True)
        return carpeta

    def _armar(self, hacer):
        if not self._puntos or not self._puntos.exists():
            return {"error": "Falta el archivo puntos.json de la empresa. Elíjalo con «Cambiar».", "falta_puntos": True}
        try:
            salida, avisos = hacer()
        except Exception as e:  # noqa: BLE001 - se muestra en la pantalla
            return {"error": str(e) or e.__class__.__name__}
        self.abrir(str(salida))
        return {"salida": str(salida), "avisos": avisos}

    def revisar(self, fecha, excel, banco, tarjetas):
        def hacer():
            dt.date.fromisoformat(fecha)
            salida = self._carpeta("revisiones") / f"revision_{fecha}.html"
            _, avisos = revision.generar(fecha, self._puntos, salida, excel, banco, tarjetas)
            return salida, avisos
        return self._armar(hacer)

    def tablero(self, reportes):
        def hacer():
            salida = self._carpeta("tableros") / f"tablero_{dt.date.today().isoformat()}.html"
            _, avisos = tablero.generar(self._puntos, salida, reportes)
            return salida, avisos
        return self._armar(hacer)

    def abrir(self, ruta):
        import webview
        webview.create_window(f"Tino · {Path(ruta).stem.replace('_', ' ')}", url=Path(ruta).as_uri(),
                              width=1280, height=720, min_size=(400, 500), background_color="#F7F5F7")


def ventana():
    PROPIO.mkdir(parents=True, exist_ok=True)
    (PROPIO / "tmp").mkdir(exist_ok=True)
    os.environ["TEMP"] = os.environ["TMP"] = str(PROPIO / "tmp")
    os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(PROPIO / "ventana")
    import json
    import webview

    config = buscar("tino.json")
    if config:
        # Conectado a la base: entrar, subir archivos y revisar desde Supabase.
        from panel.datos.cliente import Cliente
        from panel.servicio import Servicio
        datos = json.loads(config.read_text(encoding="utf-8"))
        api = ApiConectada(Servicio(Cliente(datos["url"], datos["llave_publica"])), config.parent,
                           datos.get("correo", ""))
        html, ancho, alto = CONECTADO, 1240, 760
    else:
        # Sin conexión: elegir archivos sueltos y armar la revisión o el tablero.
        api, html, ancho, alto = Api(), INICIO, 820, 700
    api._ventana = webview.create_window("Tino", html=html.read_text(encoding="utf-8"), js_api=api,
                                         width=ancho, height=alto, min_size=(420, 560), background_color="#F7F5F7")
    webview.start(private_mode=False, storage_path=str(PROPIO / "ventana"))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--revision", "--tablero"):
        modo = sys.argv.pop(1)
        (revision if modo == "--revision" else tablero).main()
    else:
        ventana()
