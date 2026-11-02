# -*- mode: python ; coding: utf-8 -*-
#
# Suite Irina como CARPETA (dist/SuiteIrina/SuiteIrina.exe), no como un solo .exe:
# el .exe de un solo archivo descomprimía ~400 MB en C:\...\Temp en CADA arranque
# (lento, y falla si el disco C: está lleno). En carpeta arranca directo.
from PyInstaller.utils.hooks import collect_data_files

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # Los documentos de descubrimiento de las APIs de Google (Drive, Sheets) van
    # dentro, para no depender de descargarlos al conectar.
    datas=[('webui', 'webui'), ('cierre_config.json', '.'), ('mapeo_siigo.xlsx', '.')]
          + collect_data_files('googleapiclient', includes=['discovery_cache/documents/drive.v3.json',
                                                            'discovery_cache/documents/sheets.v4.json']),
    # bridge.py importa los motores dentro de una función (carga en segundo
    # plano); se listan aquí para que PyInstaller no los deje por fuera.
    hiddenimports=['core', 'verify', 'transferencias_core', 'historial_db', 'cierre_core',
                   'cierre.lector_xlsx', 'cierre.reglas_n1', 'cierre.plantilla',
                   'cierre.formulas', 'cierre.modelo', 'cierre.texto', 'cierre.db',
                   'cierre.asesoras', 'cierre.siigo', 'cierre.reglas_n2', 'cierre.banco',
                   'cierre.reglas_n3', 'cierre.lector_sheets', 'cierre.tarjetas',
                   'googleapiclient.discovery', 'google_auth_oauthlib.flow',
                   'google.oauth2.credentials', 'google.auth.transport.requests'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Librerías instaladas en el Python de la máquina que el programa NO usa;
    # PyInstaller las arrastraba y casi duplicaban el tamaño.
    excludes=['IPython', 'jupyter', 'jupyter_client', 'jupyter_core', 'notebook', 'ipykernel',
              'matplotlib', 'pandas', 'scipy', 'pyarrow', 'sklearn', 'sympy', 'tkinter',
              'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'torch', 'tensorflow'],
    noarchive=False,
    optimize=0,
)
# El gancho de PyInstaller para googleapiclient mete la descripción de ~500 APIs
# (~100 MB); solo se usan Drive y Sheets.
_SOLO = ("drive.v3.json", "sheets.v4.json")
a.datas = [d for d in a.datas
           if "discovery_cache" not in d[0].replace("\\", "/") or d[0].endswith(_SOLO)]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SuiteIrina',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SuiteIrina',
)
