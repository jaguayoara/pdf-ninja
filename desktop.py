"""
PDF Ninja - Lanzador desktop (ventana nativa).

Arranca Flask en un thread en background y abre una ventana nativa
usando el webview del sistema (Edge WebView2 en Windows, WebKit en macOS,
WebKitGTK en Linux). Todo el frontend (HTML/CSS/JS) y backend (Python)
siguen funcionando igual, solo cambia el contenedor de la UI.

Uso:
    python desktop.py

Para empaquetar como ejecutable unico:
    pyinstaller --noconfirm --onedir --windowed --name PdfNinja --icon=static/favicon.ico desktop.py
"""
from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# -----------------------------------------------------------------------------
# Detectar si estamos corriendo empaquetados por PyInstaller
# -----------------------------------------------------------------------------
# PyInstaller extrae todo a una carpeta temporal y la expone en sys._MEIPASS.
# El cwd (donde esta el .exe) sigue siendo la carpeta del usuario.
if getattr(sys, "frozen", False):
    # Empaquetado: el bundle vive en sys._MEIPASS
    BUNDLE_DIR = Path(sys._MEIPASS)
    RUNTIME_DIR = Path(sys.executable).parent  # carpeta donde esta el .exe
else:
    # Desarrollo: ambos son la carpeta del proyecto
    BUNDLE_DIR = Path(__file__).resolve().parent
    RUNTIME_DIR = BUNDLE_DIR

# -----------------------------------------------------------------------------
# Configurar logging a archivo (especialmente util en modo --windowed donde
# no hay consola para ver errores)
# -----------------------------------------------------------------------------
LOG_FILE = RUNTIME_DIR / "pdfninja.log"
try:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
except Exception:
    logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pdfninja")

# Silenciar werkzeug (logs de Flask) para no llenar el log
logging.getLogger("werkzeug").setLevel(logging.WARNING)


def find_free_port() -> int:
    """Encuentra un puerto libre y lo retorna."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def wait_for_server(url: str, timeout: float = 15.0) -> bool:
    """Espera a que el servidor responda."""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(0.15)
    return False


def start_flask_in_thread(port: int):
    """Inicia Flask en un thread daemon."""
    # Cambiar cwd al bundle para que Flask encuentre templates/ y static/
    # relativo a la carpeta donde el codigo espera sus assets
    os.chdir(BUNDLE_DIR)
    if str(BUNDLE_DIR) not in sys.path:
        sys.path.insert(0, str(BUNDLE_DIR))

    log.info("Iniciando Flask (bundle=%s, runtime=%s)", BUNDLE_DIR, RUNTIME_DIR)

    from app import app  # noqa: E402  (imports must come after sys.path tweak)

    def run():
        try:
            # use_reloader=False y threaded=True para no bloquear y soportar concurrentes
            app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False, threaded=True)
        except Exception as e:
            log.exception("Fallo arrancando Flask: %s", e)

    t = threading.Thread(target=run, daemon=True, name="flask-server")
    t.start()
    return t


def main():
    try:
        port = find_free_port()
        url = f"http://127.0.0.1:{port}"
        log.info("PDF Ninja iniciando en %s", url)
        log.info("Log file: %s", LOG_FILE)

        # Crear carpetas uploads/ y outputs/ junto al .exe (en runtime, no en bundle)
        (RUNTIME_DIR / "uploads").mkdir(exist_ok=True)
        (RUNTIME_DIR / "outputs").mkdir(exist_ok=True)

        # Arrancar Flask
        flask_thread = start_flask_in_thread(port)

        # Esperar a que el server este listo
        if not wait_for_server(url, timeout=15.0):
            log.error("El servidor no arranco en %s tras 15s", url)
            # Si hay ventana nativa abierta, mostrar un mensaje
            try:
                import webview
                webview.create_window(
                    title="PDF Ninja - Error",
                    html=(
                        "<html><body style='font-family:system-ui;padding:40px;'>"
                        "<h1>No se pudo iniciar PDF Ninja</h1>"
                        f"<p>El servidor no arranco. Revisa el log en:</p>"
                        f"<pre>{LOG_FILE}</pre>"
                        "</body></html>"
                    ),
                    width=600,
                    height=400,
                )
                webview.start()
            except Exception:
                pass
            sys.exit(1)

        log.info("Servidor listo, abriendo ventana nativa")

        import webview  # import aqui para no requerirlo si solo se quiere loguear

        # Icono: preferir .ico (Windows) en el bundle; fallback al .ico del runtime
        icon_path = BUNDLE_DIR / "static" / "favicon.ico"
        if not icon_path.exists():
            icon_path = RUNTIME_DIR / "static" / "favicon.ico"

        window = webview.create_window(
            title="PDF Ninja",
            url=url,
            width=1280,
            height=820,
            min_size=(900, 600),
            resizable=True,
            fullscreen=False,
            minimized=False,
            maximized=True,        # abre maximizado por defecto
            on_top=False,
            shadow=True,
            text_select=True,
            confirm_close=False,
        )

        if icon_path.exists():
            try:
                window.icon = str(icon_path)
                log.info("Icono cargado: %s", icon_path)
            except Exception as e:
                log.warning("No se pudo cargar el icono: %s", e)

        try:
            webview.start(
                gui=None,            # usa el webview nativo del sistema
                debug=False,
                http_server=False,   # nosotros proveemos el server
            )
        except KeyboardInterrupt:
            pass
        finally:
            log.info("PDF Ninja cerrado por el usuario")
    except Exception as e:
        log.exception("Error fatal: %s", e)
        try:
            # Mostrar error en una ventana si es posible
            import webview
            webview.create_window(
                title="PDF Ninja - Error fatal",
                html=(
                    "<html><body style='font-family:system-ui;padding:40px;color:#b00;'>"
                    "<h1>Error al iniciar PDF Ninja</h1>"
                    f"<pre>{e}</pre>"
                    f"<p>Log completo: {LOG_FILE}</p>"
                    "</body></html>"
                ),
                width=700,
                height=500,
            )
            webview.start()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
