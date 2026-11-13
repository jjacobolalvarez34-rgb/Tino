# -*- coding: utf-8 -*-
"""Lo que se hace con un archivo antes de leerlo: abrir comprimidos y nombrar copias.

Un .zip (como el que descarga Bancolombia) se abre solo: cada PDF o Excel de adentro
entra como un archivo más. Se extrae en la carpeta temporal del programa, que en este
computador está en D: (TEMP), nunca en la del sistema.
"""
import datetime as dt
import shutil
import tempfile
import zipfile
from pathlib import Path

LEIBLES = (".pdf", ".xlsx", ".xlsm")
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre"]


class ArchivoNoValido(Exception):
    pass


def expandir(rutas, carpeta=None):
    """Lista de (ruta para leer, nombre para mostrar). Los .zip se abren; lo demás pasa igual."""
    salida = []
    for ruta in map(Path, rutas):
        if ruta.suffix.lower() != ".zip":
            salida.append((ruta, ruta.name))
            continue
        destino = Path(tempfile.mkdtemp(prefix="tino_zip_", dir=carpeta))
        try:
            with zipfile.ZipFile(ruta) as z:
                adentro = [n for n in z.namelist() if n.lower().endswith(LEIBLES) and not n.endswith("/")]
                if not adentro:
                    raise ArchivoNoValido(f"{ruta.name} no trae ningún PDF ni Excel adentro.")
                for n in adentro:
                    # Solo el nombre: un .zip no puede escribir fuera de su carpeta temporal.
                    final = destino / Path(n).name
                    with z.open(n) as origen, open(final, "wb") as copia:
                        shutil.copyfileobj(origen, copia)
                    salida.append((final, f"{Path(n).name} (de {ruta.name})"))
        except zipfile.BadZipFile:
            raise ArchivoNoValido(f"{ruta.name} no se puede abrir: el .zip está dañado.") from None
    return salida


def nombre_extracto(banco, fechas):
    """'Bancolombia movimientos 30 de agosto 2026' o '... 1 de septiembre a 30 de septiembre del 2026'."""
    dias = sorted({dt.date.fromisoformat(f) for f in fechas})
    if not dias:
        return f"{banco} movimientos (sin datos)"
    a, b = dias[0], dias[-1]
    texto = lambda d: f"{d.day} de {MESES[d.month - 1]}"  # noqa: E731
    if a == b:
        return f"{banco} movimientos {texto(a)} {a.year}"
    if a.year == b.year:
        return f"{banco} movimientos {texto(a)} a {texto(b)} del {a.year}"
    return f"{banco} movimientos {texto(a)} del {a.year} a {texto(b)} del {b.year}"


def guardar_copia(ruta, carpeta, nombre):
    """Copia el archivo con su nombre claro, sin pisar uno que ya exista."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    destino = carpeta / f"{nombre}{Path(ruta).suffix.lower()}"
    n = 2
    while destino.exists():
        destino = carpeta / f"{nombre} ({n}){Path(ruta).suffix.lower()}"
        n += 1
    shutil.copyfile(ruta, destino)
    return destino
