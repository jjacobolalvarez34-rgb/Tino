#!/usr/bin/env python3
"""
procesar_transferencias.py
---------------------------------------------------------------
Automatiza la lectura de los reportes PDF de movimientos de
Bancolombia y arma un Excel (uno por fecha encontrada) con las
transferencias de cada punto de venta, listo para revisar,
completar la columna "Consignar" y pegar en el Google Sheet.

CÓMO USARLO (con interfaz - recomendado)
------------------------------------------
1. Instala las librerías necesarias (una sola vez):
       pip install pdfplumber openpyxl

2. Haz doble clic en el archivo, o corre:
       python procesar_transferencias.py

Se abre una ventana: eliges uno o varios PDF (también acepta
   .zip o .rar y los descomprime solo), das clic en "Procesar" y
   listo. Se exporta:
   - El Excel con el nombre de siempre:
        TRANSFERENCIAS {2026-08-30}.xlsx
        TRANSFERENCIAS {2026-08-30, 2026-08-31}.xlsx
   - Y además una copia de cada PDF con nombre tipo:
        Bancolombia movimientos 30 de agosto 2026.pdf
        Bancolombia movimientos 30 de agosto a 31 de agosto del 2026.pdf

CÓMO USARLO (por línea de comandos, opcional)
------------------------------------------------
También puedes pasarle los archivos directamente sin abrir la
ventana:
       python procesar_transferencias.py reporte1.pdf reporte2.pdf
       python procesar_transferencias.py "C:/ruta/a/mis/reportes"

QUÉ HACE Y QUÉ NO HACE
-----------------------
- Solo toma líneas que empiezan con "PAGO QR" o "PAGO LLAVE"
  (que son las que traen código de 11 dígitos identificable).
- Ignora Nequi, PSE, interbancarios, abonos de tarjetas, etc.
  Esas transacciones no tienen código y las sigues manejando tú
  a mano, tal como me indicaste.
- Identifica el punto de venta comparando los ÚLTIMOS 4 DÍGITOS
  de la referencia del pago contra los últimos 4 dígitos de cada
  código de la lista PUNTOS (ver diccionario más abajo), porque
  el código no siempre aparece completo o igual al inicio.
- Si una transacción no coincide con ningún punto conocido, se
  deja aparte en una hoja "SIN_IDENTIFICAR" para que la revises
  manualmente (por si hay un código nuevo o un typo).

CONFIGURACIÓN DE PUNTOS
------------------------
Si agregas, quitas o cambias un punto de venta, edita la lista
PUNTOS más abajo. El orden en que los pongas aquí es el orden en
que saldrán las filas en el Excel.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime

import pdfplumber
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
            "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# ---------------------------------------------------------------
# 1. CONFIGURACIÓN: nombre del punto -> código completo
#    (se usan solo los últimos 4 dígitos para el emparejamiento)
# ---------------------------------------------------------------
PUNTOS = [
    ("PLAZA IMPERIAL", "90484794"),
    ("SALITRE PLAZA",  "90484864"),
    ("ALTAVISTA",      "90487190"),
    ("KENNEDY",        "94487206"),
    ("SANTAFE",        "90489726"),
    ("PLAZA CLARO",    "90490767"),
    ("P DORADO",       "90490784"),
    ("P SUBA",         "90490822"),
    ("P AMERICAS",     "91271397"),
    ("P SUR",          "90490834"),
    ("BANDERAS",       "90490855"),
]

# Mapa rápido: últimos 4 dígitos -> (nombre, código completo)
LAST4_TO_PUNTO = {codigo[-4:]: (nombre, codigo) for nombre, codigo in PUNTOS}

# Líneas que sí nos interesan (tienen código de punto)
PATRON_LINEA = re.compile(
    r'^(?P<fecha>\d{4}/\d{2}/\d{2})\s+'
    r'(?P<tipo>PAGO QR|PAGO LLAVE)\s+'
    r'(?P<resto>.*)$'
)

# Un número de 7 a 10 dígitos en medio de la línea = referencia/código
PATRON_REFERENCIA = re.compile(r'\b(\d{7,10})\b')

# El valor siempre es lo último de la línea, con formato 1,234.56 o -1,234.56
PATRON_VALOR = re.compile(r'(-?[\d.]*\d,\d{3}(?:,\d{3})*\.\d{2}|-?\d+\.\d{2})\s*$')


def extraer_transacciones(pdf_path):
    """Lee un PDF y devuelve una lista de dicts con fecha, punto, código y valor."""
    resultados = []
    sin_identificar = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            texto = page.extract_text() or ""
            for linea in texto.split("\n"):
                m = PATRON_LINEA.match(linea.strip())
                if not m:
                    continue

                fecha = m.group("fecha")
                resto = m.group("resto")

                m_valor = PATRON_VALOR.search(resto)
                if not m_valor:
                    continue
                valor_str = m_valor.group(1).replace(",", "")
                try:
                    valor = float(valor_str)
                except ValueError:
                    continue

                # Buscamos la referencia en la parte de la línea ANTES del valor
                parte_sin_valor = resto[: m_valor.start()]
                refs = PATRON_REFERENCIA.findall(parte_sin_valor)
                if not refs:
                    sin_identificar.append(
                        {"fecha": fecha, "descripcion": linea.strip(), "valor": valor}
                    )
                    continue

                referencia = refs[0]
                last4 = referencia[-4:]
                punto_info = LAST4_TO_PUNTO.get(last4)

                if punto_info:
                    nombre_punto, codigo = punto_info
                    resultados.append(
                        {
                            "fecha": fecha,
                            "punto": nombre_punto,
                            "codigo": codigo,
                            "valor": valor,
                            "referencia": referencia,
                        }
                    )
                else:
                    sin_identificar.append(
                        {
                            "fecha": fecha,
                            "descripcion": linea.strip(),
                            "referencia": referencia,
                            "valor": valor,
                        }
                    )

    return resultados, sin_identificar


def agrupar_por_fecha(transacciones):
    """fecha -> punto -> [valores]"""
    agrupado = defaultdict(lambda: defaultdict(list))
    for t in transacciones:
        agrupado[t["fecha"]][t["punto"]].append(t["valor"])
    return agrupado


def nombre_archivo_salida(agrupado, carpeta_destino):
    """Genera 'TRANSFERENCIAS {fecha1, fecha2}.xlsx' a partir de las fechas encontradas.
    Los días seguidos se agrupan ('2026-09-01 a 2026-09-30'): un mes completo
    con cada fecha suelta da un nombre de ~400 caracteres y Windows no deja
    guardarlo (máximo 255)."""
    fechas = sorted(agrupado.keys())  # formato AAAA/MM/DD, ordena bien cronológicamente
    if not fechas:
        return os.path.join(carpeta_destino, "TRANSFERENCIAS (sin datos).xlsx")
    dias = [datetime.strptime(f, "%Y/%m/%d").date() for f in fechas]
    tramos = [[dias[0], dias[0]]]
    for d in dias[1:]:
        if (d - tramos[-1][1]).days == 1:
            tramos[-1][1] = d
        else:
            tramos.append([d, d])

    def texto(a, b):
        if a == b:
            return a.isoformat()
        if (b - a).days == 1:
            return f"{a.isoformat()}, {b.isoformat()}"
        return f"{a.isoformat()} a {b.isoformat()}"

    contenido = ", ".join(texto(a, b) for a, b in tramos)
    if len(contenido) > 150:   # muchos días sueltos: primero, último y cuántos
        contenido = f"{dias[0].isoformat()} a {dias[-1].isoformat()}, {len(dias)} días"
    return os.path.join(carpeta_destino, f"TRANSFERENCIAS {{{contenido}}}.xlsx")


def nombre_pdf_salida(fechas, carpeta_destino):
    """Genera el nombre de la copia del PDF en el formato solicitado:
       - un solo día: "Bancolombia movimientos 30 de agosto 2026"
       - varios días: "Bancolombia movimientos 30 de agosto a 31 de agosto del 2026"
    Recibe la lista de fechas AAAA/MM/DD encontradas en ese PDF."""
    fechas = sorted(set(fechas))
    if not fechas:
        nombre = "Bancolombia movimientos (sin datos)"
    else:
        a1, m1, d1 = fechas[0].split("/")
        dia_inicial, mes_inicial = int(d1), MESES_ES[int(m1) - 1]
        if len(fechas) == 1:
            nombre = f"Bancolombia movimientos {dia_inicial} de {mes_inicial} {a1}"
        else:
            a2, m2, d2 = fechas[-1].split("/")
            dia_final, mes_final = int(d2), MESES_ES[int(m2) - 1]
            nombre = (f"Bancolombia movimientos {dia_inicial} de {mes_inicial} a "
                      f"{dia_final} de {mes_final} del {a1}")
    return os.path.join(carpeta_destino, nombre + ".pdf")


def exportar_pdfs(pdfs_con_fechas, carpeta_destino, log=print):
    """Copia cada PDF procesado a `carpeta_destino` con el nombre nuevo
    (Bancolombia movimientos ...). Devuelve la lista de copias creadas."""
    exportados = []
    for ruta, fechas in pdfs_con_fechas:
        destino = nombre_pdf_salida(fechas, carpeta_destino)
        if os.path.exists(destino):
            base, ext = os.path.splitext(destino)
            n = 2
            while os.path.exists(f"{base} ({n}){ext}"):
                n += 1
            destino = f"{base} ({n}){ext}"
        shutil.copyfile(ruta, destino)
        exportados.append(destino)
        log(f"PDF exportado: {os.path.basename(destino)}")
    return exportados


def construir_excel(agrupado, sin_identificar, salida="transferencias_procesadas.xlsx"):
    wb = Workbook()
    wb.remove(wb.active)  # quitamos la hoja por defecto

    encabezado_fill = PatternFill("solid", fgColor="FFF200")
    sin_origen_fill = PatternFill("solid", fgColor="FFD966")
    titulo_font = Font(bold=True)
    total_font = Font(bold=True, size=11)
    total_fill = PatternFill("solid", fgColor="E8E8E8")
    MONEY_FMT = '"$"#,##0.00'

    # sin_identificar agrupado por fecha, para la sección "DATOS SIN ORIGEN"
    # de cada hoja (Nequi, PSE, etc. sin código de punto de venta: las
    # asesoras dicen a mano a qué punto pertenecen, aquí solo se listan).
    sin_id_por_fecha = defaultdict(list)
    for item in sin_identificar:
        sin_id_por_fecha[item["fecha"]].append(item)

    for fecha in sorted(agrupado.keys()):
        # nombre de hoja válido (Excel no permite / : * ? [ ] y máx 31 caracteres)
        nombre_hoja = fecha.replace("/", "-")
        ws = wb.create_sheet(title=nombre_hoja)

        # Encabezados (sin Consignar/Reporte archivo/Diferencia: esas se
        # calculan en el Google Sheet, no aquí)
        headers = ["PUNTOS", "código", "TOTAL"]
        for col, h in enumerate(headers, start=1):
            c = ws.cell(row=2, column=col, value=h)
            c.font = titulo_font
            c.fill = encabezado_fill

        # DOMICILIOS (sin código, se llena a mano) igual que en tu plantilla
        ws.cell(row=3, column=1, value="DOMICILIOS")

        fila = 4
        max_transacciones = 0
        for nombre_punto, codigo in PUNTOS:
            valores = agrupado.get(fecha, {}).get(nombre_punto, [])
            max_transacciones = max(max_transacciones, len(valores))

            ws.cell(row=fila, column=1, value=nombre_punto)
            ws.cell(row=fila, column=2, value=int(codigo))
            # C: TOTAL -> suma de las transacciones encontradas
            total = sum(valores)
            c_total = ws.cell(row=fila, column=3, value=total)
            c_total.number_format = MONEY_FMT

            # D en adelante: cada transferencia individual encontrada
            for i, v in enumerate(valores):
                cv = ws.cell(row=fila, column=4 + i, value=v)
                cv.number_format = MONEY_FMT

            fila += 1

        # Fila de TOTAL GENERAL, al final de todo (suma de la columna TOTAL)
        fila_total = fila + 1
        ws.cell(row=fila_total, column=1, value="TOTAL GENERAL").font = total_font
        for col in range(1, 4):
            ws.cell(row=fila_total, column=col).fill = total_fill
        primera_fila_puntos = 4
        ultima_fila_puntos = fila - 1
        col_c = get_column_letter(3)
        c_total_general = ws.cell(
            row=fila_total, column=3,
            value=f"=SUM({col_c}{primera_fila_puntos}:{col_c}{ultima_fila_puntos})")
        c_total_general.font = total_font
        c_total_general.number_format = MONEY_FMT

        # --- DATOS SIN ORIGEN de este día: Nequi, PSE, etc. sin código de
        # punto de venta. Se dejan aquí, en su propio cuadrito día a día,
        # para que se les asigne el punto a mano según lo que reporten las
        # asesoras (igual que en la hoja de Google Sheets). ---
        items_del_dia = sin_id_por_fecha.get(fecha, [])
        fila_dso = fila_total + 2
        ws.cell(row=fila_dso, column=1, value="DATOS SIN ORIGEN").font = total_font
        fila_dso += 1
        dso_headers = ["Descripción", "Punto (asignar a mano)", "Valor"]
        for col, h in enumerate(dso_headers, start=1):
            c = ws.cell(row=fila_dso, column=col, value=h)
            c.font = titulo_font
            c.fill = sin_origen_fill
        fila_dso += 1
        if items_del_dia:
            for item in items_del_dia:
                desc = item.get("descripcion") or item.get("referencia", "")
                ws.cell(row=fila_dso, column=1, value=desc)
                # columna B (Punto) queda en blanco a propósito: se llena a mano
                c_val = ws.cell(row=fila_dso, column=3, value=item["valor"])
                c_val.number_format = MONEY_FMT
                fila_dso += 1
        else:
            ws.cell(row=fila_dso, column=1, value="(ninguno este día)").font = Font(italic=True, color="999999")

        # Título con la fecha arriba
        ws.cell(row=1, column=1, value=f"Transferencias - {fecha}").font = Font(bold=True, size=12)

        # Anchos de columna básicos
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 14
        for col in range(4, 4 + max_transacciones):
            ws.column_dimensions[get_column_letter(col)].width = 12

    # Hoja de transacciones no identificadas (todas juntas, para revisión
    # global), si las hay
    if sin_identificar:
        ws = wb.create_sheet(title="SIN_IDENTIFICAR")
        ws.append(["Revisar manualmente - no coincide con ningún punto conocido"])
        ws.append(["Fecha", "Descripción / Referencia", "Valor"])
        for item in sin_identificar:
            desc = item.get("descripcion") or item.get("referencia", "")
            ws.append([item["fecha"], desc, item["valor"]])
        for row in range(3, ws.max_row + 1):
            ws.cell(row=row, column=3).number_format = MONEY_FMT

    wb.save(salida)
    return salida


def _find_unrar_tool():
    """Busca un extractor de .rar instalado (WinRAR o 7-Zip) en las rutas
    típicas de Windows."""
    bases = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"),
             os.environ.get("ProgramW6432"), os.environ.get("LOCALAPPDATA")]
    for base in bases:
        if not base:
            continue
        for carpeta, exe in (("WinRAR", "UnRAR.exe"), ("7-Zip", "7z.exe")):
            candidato = os.path.join(base, carpeta, exe)
            if os.path.isfile(candidato):
                return candidato
    return None


def _extraer_zip(ruta, destino, log):
    """Extrae todos los .pdf de un .zip a `destino`. Devuelve la lista de
    rutas PDF extraídas (sin sobrescribir, numerando si hay duplicados)."""
    encontrados = []
    with zipfile.ZipFile(ruta) as zf:
        for miembro in zf.infolist():
            nombre = os.path.basename(miembro.filename)
            if not nombre.lower().endswith(".pdf") or not nombre:
                continue
            target = os.path.join(destino, nombre)
            n = 1
            while os.path.exists(target):
                base, ext = os.path.splitext(nombre)
                target = os.path.join(destino, f"{base}_{n}{ext}")
                n += 1
            with zf.open(miembro) as src, open(target, "wb") as dst:
                dst.write(src.read())
            encontrados.append(target)
            log(f"   extraído: {os.path.basename(target)}")
    return encontrados


def _extraer_rar(ruta, destino, log):
    """Extrae todos los .pdf de un .rar a `destino`. Primero intenta con la
    librería `rarfile` (si está instalada y con unrar disponible); si no,
    usa WinRAR o 7-Zip instalado en el sistema. Devuelve la lista de PDFs."""
    try:
        import rarfile  # opcional; requiere el ejecutable unrar
        with rarfile.RarFile(ruta) as rf:
            encontrados = []
            for miembro in rf.infolist():
                nombre = os.path.basename(miembro.filename)
                if not nombre.lower().endswith(".pdf") or not nombre:
                    continue
                target = os.path.join(destino, nombre)
                n = 1
                while os.path.exists(target):
                    base, ext = os.path.splitext(nombre)
                    target = os.path.join(destino, f"{base}_{n}{ext}")
                    n += 1
                with rf.open(miembro) as src, open(target, "wb") as dst:
                    dst.write(src.read())
                encontrados.append(target)
                log(f"   extraído: {os.path.basename(target)}")
            if encontrados:
                return encontrados
    except Exception as e:
        log(f"   (rarfile no disponible: {e})")

    tool = _find_unrar_tool()
    if not tool:
        raise ValueError(
            "No encontré cómo extraer el .rar. Instala 7-Zip o WinRAR, o "
            "convierte el archivo a .zip.")
    if os.path.basename(tool).lower().startswith("unrar"):
        cmd = [tool, "e", "-y", "-o+", ruta, destino + os.sep]
    else:  # 7z.exe
        cmd = [tool, "e", "-y", f"-o{destino}", ruta]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    encontrados = []
    for f in sorted(os.listdir(destino)):
        if f.lower().endswith(".pdf"):
            encontrados.append(os.path.join(destino, f))
    for f in encontrados:
        log(f"   extraído: {os.path.basename(f)}")
    return encontrados


def _extraer_comprimido(ruta, destino, log):
    ext = os.path.splitext(ruta)[1].lower()
    log(f"Descomprimiendo: {os.path.basename(ruta)}")
    if ext == ".zip":
        return _extraer_zip(ruta, destino, log)
    if ext == ".rar":
        return _extraer_rar(ruta, destino, log)
    raise ValueError(f"No reconozco el archivo: {os.path.basename(ruta)} "
                     "(solo .pdf, .zip o .rar)")


def _descomprimir_necesarios(rutas, log=print):
    """Separa los PDF directos de los comprimidos (.zip/.rar); extrae estos
    últimos a una carpeta temporal y devuelve (pdfs, temporales) donde
    `temporales` son las carpetas a borrar al terminar."""
    pdfs = []
    temporales = []
    for r in rutas:
        if os.path.isdir(r):
            for f in sorted(os.listdir(r)):
                if f.lower().endswith(".pdf"):
                    pdfs.append(os.path.join(r, f))
            continue
        low = r.lower()
        if low.endswith(".pdf"):
            pdfs.append(r)
        elif low.endswith((".zip", ".rar")):
            td = tempfile.mkdtemp(prefix="suite_irina_")
            temporales.append(td)
            extraidos = _extraer_comprimido(r, td, log)
            if not extraidos:
                raise ValueError(
                    f"No encontré archivos PDF dentro de: {os.path.basename(r)}")
            pdfs.extend(extraidos)
        else:
            raise ValueError(f"No reconozco el archivo: {os.path.basename(r)} "
                             "(solo .pdf, .zip o .rar)")
    if not pdfs:
        raise ValueError("No se encontraron archivos PDF en lo que indicaste.")
    return pdfs, temporales


def recolectar_pdfs(rutas):
    """Compatibilidad: devuelve la lista de PDF a procesar (extrayendo los
    .zip/.rar sobre la marcha). Las carpetas temporales quedan a cargo del
    sistema operativo."""
    pdfs, _ = _descomprimir_necesarios(rutas)
    return pdfs


def procesar_pdfs(pdfs, carpeta_destino=None, log=print):
    """Corre todo el proceso sobre una lista de rutas (PDF directos, carpetas,
    o .zip/.rar de los que extrae los PDF) y devuelve (ruta_del_excel, [pdfs]).

    El Excel conserva el nombre de siempre (TRANSFERENCIAS {…}.xlsx). Además
    se guarda una copia de cada PDF procesado con el nombre nuevo
    (Bancolombia movimientos …).

    Si se pasa `carpeta_destino`, el resultado se guarda ahí. Si no se pasa
    nada, se usa Documentos/TRABAJO IRINA/TRANSFERENCIAS como antes. Si esa
    carpeta no se puede crear o escribir, se cae a Documentos como respaldo.
    """
    pdfs, temporales = _descomprimir_necesarios(pdfs, log)
    todas_transacciones = []
    todas_sin_identificar = []
    pdfs_con_fechas = []

    try:
        for pdf_path in pdfs:
            log(f"Procesando: {os.path.basename(pdf_path)}")
            trans, sin_id = extraer_transacciones(pdf_path)
            log(f"   -> {len(trans)} transferencias identificadas, {len(sin_id)} sin identificar")
            fechas_pdf = sorted({t["fecha"] for t in trans} | {s["fecha"] for s in sin_id})
            pdfs_con_fechas.append((pdf_path, fechas_pdf))
            todas_transacciones.extend(trans)
            todas_sin_identificar.extend(sin_id)

        agrupado = agrupar_por_fecha(todas_transacciones)

        documentos = os.path.join(os.path.expanduser("~"), "Documents")
        if not os.path.isdir(documentos):
            # En equipos en español a veces la carpeta se llama "Documentos"
            alt = os.path.join(os.path.expanduser("~"), "Documentos")
            documentos = alt if os.path.isdir(alt) else os.path.expanduser("~")

        destino_preferido = carpeta_destino or os.path.join(documentos, "TRABAJO IRINA", "TRANSFERENCIAS")

        try:
            os.makedirs(destino_preferido, exist_ok=True)
            salida = nombre_archivo_salida(agrupado, destino_preferido)
            construir_excel(agrupado, todas_sin_identificar, salida=salida)
            pdfs_exportados = exportar_pdfs(pdfs_con_fechas, destino_preferido, log)
        except OSError as e:
            log(f"Aviso: no se pudo guardar en '{destino_preferido}' ({e}).")
            respaldo = documentos
            os.makedirs(respaldo, exist_ok=True)
            log(f"Guardando en carpeta de respaldo: {respaldo}")
            salida = nombre_archivo_salida(agrupado, respaldo)
            construir_excel(agrupado, todas_sin_identificar, salida=salida)
            pdfs_exportados = exportar_pdfs(pdfs_con_fechas, respaldo, log)

        return salida, pdfs_exportados
    finally:
        for td in temporales:
            shutil.rmtree(td, ignore_errors=True)


def main_cli(argv):
    if not argv:
        print("Pasa la ruta de uno o varios PDF, .zip o .rar, o de una carpeta.")
        sys.exit(1)
    try:
        salida, pdfs = procesar_pdfs(list(argv))
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    print(f"\nListo. Archivo generado: {salida}")
    for p in pdfs:
        print(f"PDF exportado: {p}")
    print("Abre el archivo, llena 'Consignar', revisa 'Diferencia' y pega en tu Google Sheet.")


# ---------------------------------------------------------------
# INTERFAZ GRÁFICA
# ---------------------------------------------------------------
def lanzar_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox
    import threading
    import subprocess
    import platform

    archivos_seleccionados = []

    ventana = tk.Tk()
    ventana.title("Procesar transferencias Bancolombia")
    ventana.geometry("560x420")
    ventana.resizable(False, False)

    tk.Label(
        ventana,
        text="Procesador de transferencias por punto de venta",
        font=("Segoe UI", 13, "bold"),
    ).pack(pady=(15, 5))

    tk.Label(
        ventana,
        text="1) Elige uno o varios PDF de Bancolombia   2) Clic en Procesar",
        font=("Segoe UI", 9),
        fg="#444",
    ).pack(pady=(0, 10))

    lista_frame = tk.Frame(ventana)
    lista_frame.pack(fill="x", padx=15)

    lista_box = tk.Listbox(lista_frame, height=6)
    lista_box.pack(side="left", fill="x", expand=True)
    scrollbar = tk.Scrollbar(lista_frame, command=lista_box.yview)
    scrollbar.pack(side="right", fill="y")
    lista_box.config(yscrollcommand=scrollbar.set)

    def elegir_archivos():
        rutas = filedialog.askopenfilenames(
            title="Selecciona los reportes PDF",
            filetypes=[("Archivos PDF", "*.pdf")],
        )
        if rutas:
            archivos_seleccionados.clear()
            archivos_seleccionados.extend(rutas)
            lista_box.delete(0, tk.END)
            for r in rutas:
                lista_box.insert(tk.END, os.path.basename(r))

    botones_frame = tk.Frame(ventana)
    botones_frame.pack(pady=10)

    tk.Button(botones_frame, text="Elegir PDF...", command=elegir_archivos, width=18).pack(
        side="left", padx=5
    )

    log_text = tk.Text(ventana, height=10, width=68, state="disabled", bg="#f5f5f5")
    log_text.pack(padx=15, pady=(5, 10))

    def log(msg):
        log_text.config(state="normal")
        log_text.insert(tk.END, msg + "\n")
        log_text.see(tk.END)
        log_text.config(state="disabled")
        ventana.update_idletasks()

    def abrir_carpeta(ruta):
        carpeta = os.path.dirname(ruta)
        try:
            if platform.system() == "Windows":
                os.startfile(carpeta)
            elif platform.system() == "Darwin":
                subprocess.run(["open", carpeta])
            else:
                subprocess.run(["xdg-open", carpeta])
        except Exception:
            pass

    def procesar():
        if not archivos_seleccionados:
            messagebox.showwarning("Falta información", "Primero elige al menos un PDF.")
            return
        boton_procesar.config(state="disabled")
        log_text.config(state="normal")
        log_text.delete("1.0", tk.END)
        log_text.config(state="disabled")

        def tarea():
            try:
                salida, pdfs = procesar_pdfs(archivos_seleccionados, log=log)
                log(f"\nListo. Excel generado:\n{salida}")
                for p in pdfs:
                    log(f"PDF exportado:\n{p}")
                messagebox.showinfo(
                    "Proceso terminado",
                    f"Excel generado:\n{os.path.basename(salida)}\n\n"
                    f"PDF exportado{'s' if len(pdfs) > 1 else ''} "
                    f"({len(pdfs)}):\n" + "\n".join(os.path.basename(p) for p in pdfs) + "\n\n"
                    "Llena 'Consignar', revisa 'Diferencia' y pega en tu Google Sheet.",
                )
                abrir_carpeta(salida)
            except Exception as e:
                log(f"\nERROR: {e}")
                messagebox.showerror("Ocurrió un error", str(e))
            finally:
                boton_procesar.config(state="normal")

        threading.Thread(target=tarea, daemon=True).start()

    boton_procesar = tk.Button(
        botones_frame,
        text="Procesar",
        command=procesar,
        width=18,
        bg="#2e7d32",
        fg="white",
    )
    boton_procesar.pack(side="left", padx=5)

    ventana.mainloop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        main_cli(sys.argv[1:])
    else:
        lanzar_gui()
