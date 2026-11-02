# -*- mode: python ; coding: utf-8 -*-
# Copia de SuiteIrina.spec SOLO para diagnóstico: console=True para poder
# ver errores/traces. NO es la versión de entrega.


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('webui', 'webui')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas', 'scipy', 'matplotlib', 'pyarrow', 'seaborn',
        'IPython', 'jedi', 'parso', 'ipykernel', 'jupyter_client',
        'jupyter_core', 'nbformat', 'traitlets', 'jsonschema', 'lark',
        'zmq', 'pygments', 'pytest', 'debugpy', 'sqlalchemy', 'mock',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SuiteIrina_debug',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)