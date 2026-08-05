@echo off
REM PDF Ninja - Empaqueta el .exe portable con PyInstaller.
REM Resultado: dist\Pdf Ninja\Pdf Ninja.exe + dist\Pdf Ninja\_internal\
REM Para distribuir: comprimir la carpeta dist\Pdf Ninja\ en un .zip.

setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python no esta instalado.
  pause
  exit /b 1
)

echo Comprobando PyInstaller...
python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
  echo Instalando PyInstaller...
  python -m pip install pyinstaller==6.10.0
  if errorlevel 1 (
    echo [ERROR] No se pudo instalar PyInstaller.
    pause
    exit /b 1
  )
)

echo.
echo ============================================================
echo   Empaquetando PDF Ninja (esto puede tardar varios minutos)
echo ============================================================
echo.

python -m PyInstaller --noconfirm --clean Pdf Ninja.spec
if errorlevel 1 (
  echo.
  echo [ERROR] El build fallo. Revisa los mensajes arriba.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo   Build OK
echo   Ejecutable: dist\Pdf Ninja\Pdf Ninja.exe
echo   Para distribuir: comprime la carpeta dist\Pdf Ninja\
echo ============================================================
echo.
pause

endlocal
