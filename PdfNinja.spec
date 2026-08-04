# -*- mode: python ; coding: utf-8 -*-
"""
Pdf Ninja - PyInstaller spec.

Empaqueta desktop.py + Flask backend + todos los assets en un ejecutable
Windows portable. Modo onedir para arranque rapido (PyMuPDF y pdf2docx
son muy pesados; onefile tarda demasiado en descomprimir cada vez).

Resultado: dist/PdfNinja/PdfNinja.exe  (lanzador)
          + dist/PdfNinja/_internal/ (librerias + assets)

Para distribuir, comprimir la carpeta dist/PdfNinja/ en un .zip.
"""
from pathlib import Path

BASE = Path('.').resolve()

block_cipher = None


# Recolectar dependencias con data files / binarios nativos
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Flask incluye Jinja2, Werkzeug, click, itsdangerous, etc.
flask_datas, flask_binaries, flask_hiddenimports = collect_all('flask')
# PyMuPDF (fitz) trae PyMuPDFb (.pyd) y mupdf.so
pymupdf_datas, pymupdf_binaries, pymupdf_hiddenimports = collect_all('pymupdf')
# pikepdf tiene un C extension (qpdf)
pikepdf_datas, pikepdf_binaries, pikepdf_hiddenimports = collect_all('pikepdf')
# pdf2docx trae modelos y fonts
pdf2docx_datas, pdf2docx_binaries, pdf2docx_hiddenimports = collect_all('pdf2docx')
# openpyxl tiene templates
openpyxl_datas, openpyxl_binaries, openpyxl_hiddenimports = collect_all('openpyxl')
# reportlab trae fonts
reportlab_datas, reportlab_binaries, reportlab_hiddenimports = collect_all('reportlab')
# Pillow trae imagenes
pil_datas, pil_binaries, pil_hiddenimports = collect_all('PIL')
# pywebview necesita sus assets HTML/JS del lado de Python
pywebview_datas, pywebview_binaries, pywebview_hiddenimports = collect_all('webview')
# pdfplumber (sin extras normalmente, pero por si acaso)
pdfplumber_datas, pdfplumber_binaries, pdfplumber_hiddenimports = collect_all('pdfplumber')

# numpy: recolectar TODOS los submodulos. Sin esto, PyInstaller genera un bundle
# que falla con "cannot load module more than once per process" cuando pdf2docx
# (vía algorithm.py) importa numpy._core.multiarray.
numpy_hiddenimports = collect_submodules('numpy')

a = Analysis(
    ['desktop.py'],
    pathex=[str(BASE)],
    binaries=[
        *flask_binaries,
        *pymupdf_binaries,
        *pikepdf_binaries,
        *pdf2docx_binaries,
        *openpyxl_binaries,
        *reportlab_binaries,
        *pil_binaries,
        *pywebview_binaries,
        *pdfplumber_binaries,
    ],
    datas=[
        *flask_datas,
        *pymupdf_datas,
        *pikepdf_datas,
        *pdf2docx_datas,
        *openpyxl_datas,
        *reportlab_datas,
        *pil_datas,
        *pywebview_datas,
        *pdfplumber_datas,
        # Assets propios
        ('templates', 'templates'),
        ('static', 'static'),
        ('core', 'core'),
    ],
    hiddenimports=[
        *flask_hiddenimports,
        *pymupdf_hiddenimports,
        *pikepdf_hiddenimports,
        *pdf2docx_hiddenimports,
        *openpyxl_hiddenimports,
        *reportlab_hiddenimports,
        *pil_hiddenimports,
        *pywebview_hiddenimports,
        *pdfplumber_hiddenimports,
        *numpy_hiddenimports,
        # core modules
        'core',
        'core.converter',
        'core.editor',
        'core.manipulator',
        'core.utils',
        'core.icons',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # No los necesitamos en el .exe -> reduce peso
        'tkinter',
        'matplotlib',
        'numpy.tests',
        'scipy',
        'pandas',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # onedir: .exe ligero, DLLs aparte
    name='PdfNinja',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # comprime con UPX si esta disponible
    console=False,           # sin ventana de consola
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(BASE / 'static' / 'favicon.ico'),
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PdfNinja',
)
