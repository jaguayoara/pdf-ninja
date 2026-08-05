#!/usr/bin/env bash
# PDF Ninja - Empaqueta la app como binario portable para macOS / Linux.
# Resultado: dist/PdfNinja/PdfNinja  (lanzador) + dist/PdfNinja/_internal/
#
# NOTA: este script usa el mismo PdfNinja.spec que build.bat. Para builds
# multiplataforma hay que correrlo en cada OS por separado (no se cruzan
# binarios nativos entre plataformas).
set -e
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python 3 no esta instalado."
  exit 1
fi

echo "Comprobando PyInstaller..."
if ! python3 -c "import PyInstaller" >/dev/null 2>&1; then
  echo "Instalando PyInstaller..."
  python3 -m pip install pyinstaller==6.10.0
fi

echo
echo "============================================================"
echo "  Empaquetando PDF Ninja (esto puede tardar varios minutos)"
echo "============================================================"
echo

python3 -m PyInstaller --noconfirm --clean PdfNinja.spec

echo
echo "============================================================"
echo "  Build OK"
if [ -d "dist/PdfNinja" ]; then
  SIZE=$(du -sh dist/PdfNinja 2>/dev/null | cut -f1)
  echo "  Ejecutable: dist/PdfNinja/"
  echo "  Tamano:     $SIZE"
fi
echo "  Para distribuir: comprime la carpeta dist/PdfNinja/"
echo "============================================================"
echo
