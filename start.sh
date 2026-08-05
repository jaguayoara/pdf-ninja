#!/usr/bin/env bash
# PDF Ninja - script de inicio para macOS y Linux.
# Detecta automaticamente el modo (ventana nativa o navegador).
set -e
cd "$(dirname "$0")"

echo "Iniciando PDF Ninja..."

# Detectar python3
if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] Python 3 no esta instalado."
  echo "macOS: brew install python3   o   https://python.org/downloads/"
  echo "Linux: sudo apt install python3 python3-pip   (o equivalente)"
  exit 1
fi

# Instalar dependencias si faltan
if ! python3 -c "import flask, fitz, pdf2docx, pdfplumber, openpyxl, PIL, pikepdf" >/dev/null 2>&1; then
  echo "Instalando dependencias por primera vez..."
  python3 -m pip install -r requirements.txt
fi

# Detectar si pywebview esta disponible
if python3 -c "import webview" >/dev/null 2>&1; then
  # Modo desktop (ventana nativa)
  echo "Iniciando como aplicacion de escritorio..."
  python3 desktop.py
else
  # Modo navegador
  echo "Iniciando en navegador..."
  echo "Abre http://127.0.0.1:5050 (se abrira automaticamente en unos segundos)"
  ( sleep 2 && (xdg-open http://127.0.0.1:5050 >/dev/null 2>&1 || open http://127.0.0.1:5050 >/dev/null 2>&1 || true) ) &
  python3 app.py
fi
