# -*- coding: utf-8 -*-
"""Empaca panel/app.py como Tino.exe (una carpeta con el programa adentro).

Uso, con el Python que tenga PyInstaller, pywebview, openpyxl y pdfplumber:
    python panel/construir_exe.py --construir D:/Repositorios/Tino-datos/construir --destino D:/Repositorios/Tino-datos/app

Se empaca como carpeta y no como un solo archivo: el de un solo archivo se descomprime en
el TEMP del sistema cada vez que se abre, y en este computador nada se escribe en C: (D-034).
Todo lo intermedio va a --construir; el programa queda en --destino/Tino/Tino.exe.
"""
import argparse
import ctypes
import os
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--construir", required=True, help="Carpeta para lo intermedio")
    p.add_argument("--destino", required=True, help="Carpeta donde queda Tino/Tino.exe")
    a = p.parse_args()
    construir = Path(a.construir)
    construir.mkdir(parents=True, exist_ok=True)
    # El ícono de Tino para el .exe y la barra de la ventana, desde el PNG de la marca.
    from PIL import Image
    icono = construir / "tino.ico"
    Image.open(RAIZ / "docs" / "marca" / "png" / "tino-icono-512.png").save(
        icono, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    entorno = dict(os.environ, PYINSTALLER_CONFIG_DIR=str(construir / "pyi-config"))
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)  # que Windows no se suspenda
    orden = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onedir", "--windowed", "--name", "Tino",
             "--icon", str(icono), "--add-data", f"{RAIZ / 'panel' / 'inicio.html'}{os.pathsep}.",
             "--workpath", str(construir / "work"), "--distpath", a.destino, "--specpath", str(construir),
             "--paths", str(RAIZ), "--paths", str(RAIZ / "motores"), "--paths", str(RAIZ / "motores" / "conciliador"),
             # excel_diario lo importa dentro de una función: PyInstaller no lo ve solo.
             "--hidden-import", "cierre.lector_xlsx",
             "--add-data", f"{RAIZ / 'panel' / 'revision' / 'plantilla.html'}{os.pathsep}revision",
             "--add-data", f"{RAIZ / 'panel' / 'tablero' / 'plantilla.html'}{os.pathsep}tablero",
             str(RAIZ / "panel" / "app.py")]
    sys.exit(subprocess.run(orden, cwd=construir, env=entorno).returncode)


if __name__ == "__main__":
    main()
