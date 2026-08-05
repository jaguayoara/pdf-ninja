@echo off
REM PDF Ninja - script de inicio para Windows
setlocal

cd /d "%~dp0"

REM Comprobar Python
where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python no esta instalado o no esta en PATH.
  echo Instala Python 3.10+ desde https://python.org
  pause
  exit /b 1
)

REM Comprobar dependencias
python -c "import flask, fitz, pdf2docx, pdfplumber, openpyxl, PIL, pikepdf" >nul 2>nul
if errorlevel 1 (
  echo Instalando dependencias por primera vez...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] No se pudieron instalar las dependencias.
    pause
    exit /b 1
  )
)

REM Detectar modo: si pywebview esta disponible, abrir ventana nativa;
REM si no, fallback al navegador.
python -c "import webview" >nul 2>nul
if errorlevel 1 (
  REM Modo navegador
  echo.
  echo ============================================================
  echo   PDF Ninja iniciando en navegador
  echo   Abre http://127.0.0.1:5050
  echo   Ctrl+C para detener
  echo ============================================================
  echo.
  start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5050"
  python app.py
) else (
  REM Modo desktop (ventana nativa)
  echo.
  echo ============================================================
  echo   PDF Ninja iniciando como aplicacion de escritorio
  echo   Una ventana se abrira en breve
  echo   ============================================================
  echo.
  python desktop.py
)

pause
