@echo off
REM Pdf Ninja - Lanzador de la version portable (.exe).
REM Si tienes el .exe empaquetado, este .bat es solo una comodidad extra.
REM Alternativa: doble clic directo en PdfNinja.exe (en dist\PdfNinja\).

setlocal
cd /d "%~dp0"

if exist "dist\PdfNinja\PdfNinja.exe" (
  start "" "dist\PdfNinja\PdfNinja.exe"
) else (
  echo ============================================================
  echo   No se encontro dist\PdfNinja\PdfNinja.exe
  echo   Ejecuta build.bat para empaquetar el ejecutable
  echo   o usa start.bat para el modo desarrollo (requiere Python)
  echo ============================================================
  pause
)

endlocal
