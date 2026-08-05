"""
PDF Ninja - Aplicacion Flask principal.
Sirve la UI y expone una API REST para todas las herramientas PDF.
Ejecutar: python app.py
Luego abre http://127.0.0.1:5050 en el navegador.
"""
from __future__ import annotations

import io
import logging
import os
import time
from pathlib import Path
from typing import List, Optional

from flask import (
    Flask,
    abort,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)
from flask_cors import CORS
from werkzeug.utils import secure_filename

from core import converter, editor, manipulator, utils
from core.icons import ICONS, TOOL_ICONS

# -----------------------------------------------------------------------------
# App
# -----------------------------------------------------------------------------

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = utils.MAX_FILE_SIZE
app.config["JSON_AS_ASCII"] = False
CORS(app)


@app.context_processor
def inject_globals():
    """Inyecta iconos SVG y otros datos disponibles en todos los templates."""
    return {
        "icons": ICONS,
        "tool_icons": TOOL_ICONS,
    }

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("pdfninja")


# -----------------------------------------------------------------------------
# Util
# -----------------------------------------------------------------------------

def _err(msg: str, code: int = 400):
    return jsonify({"ok": False, "error": str(msg)}), code


def _save_upload(file_storage) -> Path:
    """Guarda un FileStorage de werkzeug y devuelve la ruta."""
    if not file_storage or not file_storage.filename:
        raise ValueError("Archivo vacio")
    name = utils.safe_filename(file_storage.filename)
    path, _ = utils.new_upload_path(name)
    file_storage.save(str(path))
    return path


def _read_int(form, key: str, default: int, min_v: int = None, max_v: int = None) -> int:
    raw = form.get(key)
    try:
        v = int(raw) if raw is not None and raw != "" else default
    except (TypeError, ValueError):
        v = default
    if min_v is not None:
        v = max(min_v, v)
    if max_v is not None:
        v = min(max_v, v)
    return v


def _read_float(form, key: str, default: float, min_v: float = None, max_v: float = None) -> float:
    raw = form.get(key)
    try:
        v = float(raw) if raw is not None and raw != "" else default
    except (TypeError, ValueError):
        v = default
    if min_v is not None:
        v = max(min_v, v)
    if max_v is not None:
        v = min(max_v, v)
    return v


def _read_color(form, key: str, default="#000000") -> str:
    return (form.get(key) or default).strip()


# -----------------------------------------------------------------------------
# Rutas UI
# -----------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# Catalogo de herramientas: cada slug -> metadata para tool_generic.html
TOOL_CATALOG = {
    "pdf-to-word": {
        "icon": "📝", "title": "PDF a Word",
        "description": "Convierte tus PDFs a documentos Word editables (.docx), manteniendo el texto, las tablas y el diseño básico.",
        "endpoint": "/api/pdf-to-word",
        "multiple": False, "file_types": "pdf",
        "action_label": "Convertir a Word",
        "drop_sub": "o haz clic para seleccionar un PDF",
    },
    "pdf-to-excel": {
        "icon": "📊", "title": "PDF a Excel",
        "description": "Extrae las tablas de tu PDF a hojas de cálculo Excel (.xlsx). Si no hay tablas, se incluye el texto.",
        "endpoint": "/api/pdf-to-excel",
        "multiple": False, "file_types": "pdf",
        "action_label": "Convertir a Excel",
        "drop_sub": "o haz clic para seleccionar un PDF",
    },
    "pdf-to-images": {
        "icon": "🖼️", "title": "PDF a Imagen",
        "description": "Convierte cada página de tu PDF en una imagen PNG o JPG de alta calidad, lista para descargar.",
        "endpoint": "/api/pdf-to-images",
        "multiple": False, "file_types": "pdf",
        "action_label": "Convertir a imágenes",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Formato</label>
            <select name="format">
              <option value="png" selected>PNG (mejor calidad)</option>
              <option value="jpg">JPG (más liviano)</option>
            </select>
          </div>
          <div class="opt">
            <label>Resolución (DPI)</label>
            <input type="number" name="dpi" value="150" min="50" max="400" step="10" />
            <small>Mayor DPI = más detalle y más peso.</small>
          </div>
        """,
        "extra_fields": ["format", "dpi"],
    },
    "images-to-pdf": {
        "icon": "📚", "title": "Imagen a PDF",
        "description": "Combina una o varias imágenes (PNG, JPG, WebP, BMP, TIFF) en un único archivo PDF.",
        "endpoint": "/api/images-to-pdf",
        "multiple": True, "file_types": "image",
        "action_label": "Crear PDF",
        "drop_sub": "arrastra una o varias imágenes",
        "drop_title": "Arrastra tus imágenes aquí",
        "hint": "Puedes subir varias imágenes, se ordenarán alfabéticamente.",
    },
    "pdf-to-text": {
        "icon": "📃", "title": "PDF a Texto",
        "description": "Extrae todo el texto de tu PDF a un archivo .txt plano.",
        "endpoint": "/api/pdf-to-text",
        "multiple": False, "file_types": "pdf",
        "action_label": "Extraer texto",
        "drop_sub": "o haz clic para seleccionar un PDF",
    },
    "pdf-to-pdfa": {
        "icon": "🏛️", "title": "PDF a PDF/A",
        "description": "Reescribe el PDF intentando embeber fuentes para mejorar la portabilidad y archivado.",
        "endpoint": "/api/pdf-to-pdfa",
        "multiple": False, "file_types": "pdf",
        "action_label": "Convertir a PDF/A",
        "drop_sub": "o haz clic para seleccionar un PDF",
    },
    "merge": {
        "icon": "🧩", "title": "Fusionar PDF",
        "description": "Une varios PDFs en un único archivo. El orden será el mismo en que los subas.",
        "endpoint": "/api/merge",
        "multiple": True, "file_types": "pdf",
        "action_label": "Fusionar",
        "drop_title": "Arrastra varios PDFs aquí",
        "drop_sub": "o haz clic para seleccionar 2 o más archivos",
        "hint": "Sube al menos 2 PDFs.",
    },
    "split": {
        "icon": "✂️", "title": "Dividir PDF",
        "description": "Extrae páginas o rangos de tu PDF. Puedes definir varios grupos separados por ; para obtener varios PDFs.",
        "endpoint": "/api/split",
        "multiple": False, "file_types": "pdf",
        "action_label": "Dividir",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Rangos de páginas</label>
            <input type="text" name="ranges" placeholder="Ej: 1-3,5 ; 7-10 ; 12" value="" />
            <small>
              Formato: <code>1-3,5,7-9</code>. Múltiples grupos separados por <code>;</code> producen varios PDFs.
              Vacío = todas las páginas.
            </small>
          </div>
        """,
        "extra_fields": ["ranges"],
    },
    "organize": {
        "icon": "🗂️", "title": "Organizar PDF",
        "description": "Reordena y/o elimina páginas indicando el nuevo orden con números separados por comas.",
        "endpoint": "/api/organize",
        "multiple": False, "file_types": "pdf",
        "action_label": "Reorganizar",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Nuevo orden</label>
            <input type="text" name="order" placeholder="Ej: 3,1,2,4" />
            <small>Lista de páginas en el orden deseado. Ej: <code>3,1,2,4</code>.</small>
          </div>
        """,
        "extra_fields": ["order"],
    },
    "rotate": {
        "icon": "🔄", "title": "Rotar PDF",
        "description": "Rota una o varias páginas 90°, 180° o 270°.",
        "endpoint": "/api/rotate",
        "multiple": False, "file_types": "pdf",
        "action_label": "Rotar",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Ángulo</label>
            <select name="angle">
              <option value="90">90° (a la derecha)</option>
              <option value="180">180°</option>
              <option value="270">270° (a la izquierda)</option>
              <option value="-90">-90°</option>
            </select>
          </div>
          <div class="opt">
            <label>Páginas (opcional)</label>
            <input type="text" name="pages" placeholder="Ej: 1,3,5-7. Vacío = todas" />
          </div>
        """,
        "extra_fields": ["angle", "pages"],
    },
    "compress": {
        "icon": "🗜️", "title": "Comprimir PDF",
        "description": "Reduce el tamaño del PDF rasterizando las páginas como imágenes JPG. Útil para PDFs con muchas imágenes.",
        "endpoint": "/api/compress",
        "multiple": False, "file_types": "pdf",
        "action_label": "Comprimir",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Calidad</label>
            <select name="quality">
              <option value="low">Baja — más compresión, menor calidad</option>
              <option value="medium" selected>Media — equilibrio</option>
              <option value="high">Alta — menos compresión, mejor calidad</option>
            </select>
            <small>El texto dejará de ser seleccionable, porque el PDF pasa a ser imagen.</small>
          </div>
        """,
        "extra_fields": ["quality"],
    },
    "watermark": {
        "icon": "💧", "title": "Marca de agua",
        "description": "Añade una marca de agua de texto diagonal (o centrada, arriba, abajo, o en mosaico).",
        "endpoint": "/api/watermark",
        "multiple": False, "file_types": "pdf",
        "action_label": "Aplicar marca de agua",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Texto</label>
            <input type="text" name="text" placeholder="Ej: CONFIDENCIAL" value="CONFIDENCIAL" />
          </div>
          <div class="opt-row">
            <div class="opt">
              <label>Tamaño</label>
              <input type="number" name="fontsize" value="48" min="8" max="200" />
            </div>
            <div class="opt">
              <label>Rotación (°)</label>
              <input type="number" name="rotation" value="45" min="-360" max="360" />
            </div>
          </div>
          <div class="opt">
            <label>Posición</label>
            <select name="position">
              <option value="center" selected>Centro (diagonal)</option>
              <option value="tile">Mosaico</option>
              <option value="top">Arriba</option>
              <option value="bottom">Abajo</option>
            </select>
          </div>
          <div class="opt-row">
            <div class="opt">
              <label>Color</label>
              <input type="color" name="color" value="#808080" />
            </div>
            <div class="opt">
              <label>Opacidad</label>
              <input type="number" name="opacity" value="0.3" min="0.05" max="1" step="0.05" />
            </div>
          </div>
          <div class="opt">
            <label>Páginas (opcional)</label>
            <input type="text" name="pages" placeholder="Vacío = todas. Ej: 1,3,5-7" />
          </div>
        """,
        "extra_fields": ["text", "fontsize", "rotation", "position", "color", "opacity", "pages"],
    },
    "page-numbers": {
        "icon": "🔢", "title": "Números de página",
        "description": "Añade numeración automática a cada página de tu PDF.",
        "endpoint": "/api/page-numbers",
        "multiple": False, "file_types": "pdf",
        "action_label": "Numerar páginas",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Posición</label>
            <select name="position">
              <option value="bottom-center" selected>Abajo centrado</option>
              <option value="bottom-right">Abajo derecha</option>
              <option value="top-center">Arriba centrado</option>
              <option value="top-right">Arriba derecha</option>
            </select>
          </div>
          <div class="opt-row">
            <div class="opt">
              <label>Empezar en</label>
              <input type="number" name="start" value="1" />
            </div>
            <div class="opt">
              <label>Tamaño</label>
              <input type="number" name="fontsize" value="11" min="6" max="72" />
            </div>
          </div>
          <div class="opt-row">
            <div class="opt">
              <label>Prefijo</label>
              <input type="text" name="prefix" placeholder="Página " />
            </div>
            <div class="opt">
              <label>Sufijo</label>
              <input type="text" name="suffix" placeholder=" de 10" />
            </div>
          </div>
          <div class="opt">
            <label>Color</label>
            <input type="color" name="color" value="#000000" />
          </div>
        """,
        "extra_fields": ["position", "start", "fontsize", "prefix", "suffix", "color"],
    },
    "protect": {
        "icon": "🔐", "title": "Proteger PDF",
        "description": "Cifra el PDF con contraseña (AES-256). Necesitarás la contraseña para abrirlo.",
        "endpoint": "/api/protect",
        "multiple": False, "file_types": "pdf",
        "action_label": "Proteger",
        "drop_sub": "o haz clic para seleccionar un PDF",
        "options": """
          <div class="opt">
            <label>Contraseña</label>
            <input type="password" name="password" placeholder="Contraseña" autocomplete="new-password" />
          </div>
          <div class="opt">
            <label>Contraseña de owner (opcional)</label>
            <input type="password" name="owner_password" placeholder="Si la dejas vacía, se usa la misma" autocomplete="new-password" />
          </div>
          <div class="opt">
            <small>⚠️ No hay forma de recuperar la contraseña. Guárdala bien.</small>
          </div>
        """,
        "extra_fields": ["password", "owner_password"],
    },
    "unlock": {
        "icon": "🔓", "title": "Desproteger PDF",
        "description": "Quita la contraseña de un PDF cifrado. Necesitas conocer la contraseña actual.",
        "endpoint": "/api/unlock",
        "multiple": False, "file_types": "pdf",
        "action_label": "Desproteger",
        "drop_sub": "o haz clic para seleccionar un PDF protegido",
        "options": """
          <div class="opt">
            <label>Contraseña actual</label>
            <input type="password" name="password" placeholder="Contraseña del PDF" autocomplete="current-password" />
          </div>
        """,
        "extra_fields": ["password"],
    },
    "metadata": {
        "icon": "ℹ️", "title": "Metadatos del documento",
        "description": "Inspecciona la ficha tecnica de un PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), imagen o texto: titulo, autor, programa que lo creo, fechas, paginas/hojas/slides, tablas y mas.",
        "endpoint": "/api/info",
        "multiple": False, "file_types": "document",
        "action_label": "Inspeccionar metadatos",
        "drop_sub": "o haz clic para seleccionar un documento (PDF, Word, Excel, PPT, imagen, txt)",
        "drop_title": "Arrastra tu documento aqui",
        "hint": "Soportado: PDF, .docx, .xlsx, .pptx, .png/.jpg/.webp, .txt/.md/.csv",
        "response_kind": "json",
    },
}


@app.route("/tool/<slug>")
def tool(slug):
    cfg = TOOL_CATALOG.get(slug)
    if not cfg:
        abort(404)
    accept_map = {
        "pdf": ".pdf,application/pdf",
        "image": "image/*",
        "document": (
            ".pdf,.docx,.xlsx,.pptx,.txt,.md,.csv,"
            "application/pdf,"
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,"
            "application/vnd.openxmlformats-officedocument.presentationml.presentation,"
            "text/plain,text/markdown,text/csv,image/*"
        ),
    }
    return render_template(
        "tool_generic.html",
        slug=slug,
        title=cfg.get("title", slug),
        description=cfg.get("description", ""),
        icon=cfg.get("icon", "📄"),
        endpoint=cfg.get("endpoint", ""),
        multiple=cfg.get("multiple", False),
        file_types=cfg.get("file_types", "pdf"),
        accept=accept_map.get(cfg.get("file_types", "pdf"), ".pdf"),
        options=cfg.get("options", ""),
        extra_fields=cfg.get("extra_fields", []),
        action_label=cfg.get("action_label", "Procesar"),
        drop_title=cfg.get("drop_title", "Arrastra tu archivo aquí"),
        drop_sub=cfg.get("drop_sub", "o haz clic para seleccionar"),
        hint=cfg.get("hint", ""),
        response_kind=cfg.get("response_kind", "download"),
    )


# -----------------------------------------------------------------------------
# API: info
# -----------------------------------------------------------------------------

@app.route("/api/info", methods=["POST"])
def api_info():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        path = _save_upload(f)
        info = manipulator.document_info(path)
        return jsonify({"ok": True, "info": info})
    except Exception as e:
        log.exception("info")
        return _err(str(e), 500)


# -----------------------------------------------------------------------------
# API: conversiones
# -----------------------------------------------------------------------------

@app.route("/api/pdf-to-word", methods=["POST"])
def api_pdf_to_word():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem, ".docx")
        converter.pdf_to_word(pdf, out)
        return _send(out, f"{pdf.stem}.docx")
    except Exception as e:
        log.exception("pdf-to-word")
        return _err(str(e), 500)


@app.route("/api/pdf-to-excel", methods=["POST"])
def api_pdf_to_excel():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem, ".xlsx")
        converter.pdf_to_excel(pdf, out)
        return _send(out, f"{pdf.stem}.xlsx")
    except Exception as e:
        log.exception("pdf-to-excel")
        return _err(str(e), 500)


@app.route("/api/pdf-to-images", methods=["POST"])
def api_pdf_to_images():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        fmt = (request.form.get("format") or "png").lower()
        if fmt == "jpeg":
            fmt = "jpg"
        if fmt not in {"png", "jpg"}:
            fmt = "png"
        dpi = _read_int(request.form, "dpi", 150, 50, 400)
        as_zip = (request.form.get("zip") or "1") not in {"0", "false", "no", ""}
        pdf = _save_upload(f)

        if as_zip:
            out = utils.new_output_path(pdf.stem, ".zip")
            converter.pdf_to_images_zip(pdf, out, fmt=fmt, dpi=dpi)
            return _send(out, f"{pdf.stem}_imagenes.zip")
        else:
            # Devolver la primera imagen como preview y un zip si hay mas
            import tempfile
            with tempfile.TemporaryDirectory() as td:
                td_p = Path(td)
                imgs = converter.pdf_to_images(pdf, td_p, fmt=fmt, dpi=dpi)
                if len(imgs) == 1:
                    return _send(imgs[0], imgs[0].name)
                out = utils.new_output_path(pdf.stem, ".zip")
                import zipfile
                with zipfile.ZipFile(str(out), "w", zipfile.ZIP_DEFLATED) as zf:
                    for i in imgs:
                        zf.write(str(i), arcname=i.name)
                return _send(out, f"{pdf.stem}_imagenes.zip")
    except Exception as e:
        log.exception("pdf-to-images")
        return _err(str(e), 500)


@app.route("/api/images-to-pdf", methods=["POST"])
def api_images_to_pdf():
    try:
        files = request.files.getlist("files")
        if not files:
            return _err("No se subieron imagenes")
        saved: List[Path] = []
        for fs in files:
            if not fs.filename:
                continue
            p = utils.new_upload_path(utils.safe_filename(fs.filename))[0]
            fs.save(str(p))
            if utils.is_image(p):
                saved.append(p)
            else:
                p.unlink(missing_ok=True)
        if not saved:
            return _err("Ninguna imagen valida")
        out = utils.new_output_path("imagenes", ".pdf")
        converter.images_to_pdf(saved, out)
        return _send(out, "imagenes.pdf")
    except Exception as e:
        log.exception("images-to-pdf")
        return _err(str(e), 500)


@app.route("/api/pdf-to-text", methods=["POST"])
def api_pdf_to_text():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem, ".txt")
        converter.pdf_to_text(pdf, out)
        return _send(out, f"{pdf.stem}.txt")
    except Exception as e:
        log.exception("pdf-to-text")
        return _err(str(e), 500)


@app.route("/api/pdf-to-pdfa", methods=["POST"])
def api_pdf_to_pdfa():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem + "_pdfa", ".pdf")
        converter.pdf_to_pdfa(pdf, out)
        return _send(out, out.name)
    except Exception as e:
        log.exception("pdf-to-pdfa")
        return _err(str(e), 500)


# -----------------------------------------------------------------------------
# API: manipulacion
# -----------------------------------------------------------------------------

@app.route("/api/merge", methods=["POST"])
def api_merge():
    try:
        files = request.files.getlist("files")
        if len(files) < 2:
            return _err("Sube al menos 2 PDFs para fusionar")
        saved: List[Path] = []
        for fs in files:
            if not fs.filename:
                continue
            p = utils.new_upload_path(utils.safe_filename(fs.filename))[0]
            fs.save(str(p))
            if utils.is_pdf(p):
                saved.append(p)
        if len(saved) < 2:
            return _err("Se necesitan al menos 2 PDFs validos")
        out = utils.new_output_path("fusionado", ".pdf")
        manipulator.merge_pdfs(saved, out)
        return _send(out, "fusionado.pdf")
    except Exception as e:
        log.exception("merge")
        return _err(str(e), 500)


@app.route("/api/split", methods=["POST"])
def api_split():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        ranges = (request.form.get("ranges") or "all").strip()
        as_zip = (request.form.get("zip") or "1") not in {"0", "false", "no", ""}

        # Necesitamos el total de paginas para parsear rangos
        import fitz
        doc = fitz.open(str(pdf))
        total = doc.page_count
        doc.close()

        if ";" in ranges or "|" in ranges:
            groups = utils.parse_page_groups(ranges, total)
        else:
            groups = [utils.parse_page_ranges(ranges, total)]

        if as_zip or len(groups) > 1:
            out = utils.new_output_path(pdf.stem + "_partes", ".zip")
            manipulator.split_pdf_zip(pdf, out, groups)
            return _send(out, f"{pdf.stem}_partes.zip")
        else:
            out = utils.new_output_path(pdf.stem + "_parte_1", ".pdf")
            parts = manipulator.split_pdf(pdf, out.parent, groups)
            if parts:
                return _send(parts[0], parts[0].name)
            raise RuntimeError("Division sin resultados")
    except Exception as e:
        log.exception("split")
        return _err(str(e), 500)


@app.route("/api/organize", methods=["POST"])
def api_organize():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        order_raw = (request.form.get("order") or "").strip()
        if not order_raw:
            return _err("Especifica el orden, ej: '3,1,2,4'")
        order = utils.parse_page_ranges(order_raw, 999999)  # validamos luego
        out = utils.new_output_path(pdf.stem + "_ordenado", ".pdf")
        manipulator.organize_pdf(pdf, out, order)
        return _send(out, out.name)
    except Exception as e:
        log.exception("organize")
        return _err(str(e), 500)


@app.route("/api/rotate", methods=["POST"])
def api_rotate():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        angle = _read_int(request.form, "angle", 90, -360, 360)
        pages_raw = (request.form.get("pages") or "").strip()
        import fitz
        doc = fitz.open(str(pdf))
        total = doc.page_count
        doc.close()
        pages = utils.parse_page_ranges(pages_raw, total) if pages_raw else None
        out = utils.new_output_path(pdf.stem + "_rotado", ".pdf")
        manipulator.rotate_pdf(pdf, out, angle, pages)
        return _send(out, out.name)
    except Exception as e:
        log.exception("rotate")
        return _err(str(e), 500)


@app.route("/api/compress", methods=["POST"])
def api_compress():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        quality = (request.form.get("quality") or "medium").lower()
        if quality not in {"low", "medium", "high"}:
            quality = "medium"
        out = utils.new_output_path(pdf.stem + "_comprimido", ".pdf")
        manipulator.compress_pdf(pdf, out, quality)
        return _send(out, out.name)
    except Exception as e:
        log.exception("compress")
        return _err(str(e), 500)


@app.route("/api/watermark", methods=["POST"])
def api_watermark():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        text = (request.form.get("text") or "").strip()
        if not text:
            return _err("Falta el texto de la marca de agua")
        opacity = _read_float(request.form, "opacity", 0.3, 0.05, 1.0)
        fontsize = _read_int(request.form, "fontsize", 48, 8, 200)
        rotation = _read_int(request.form, "rotation", 45, -360, 360)
        position = (request.form.get("position") or "center").lower()
        if position not in {"center", "tile", "top", "bottom"}:
            position = "center"
        color = _read_color(request.form, "color", "#808080")
        pages_raw = (request.form.get("pages") or "").strip()
        import fitz
        doc = fitz.open(str(pdf))
        total = doc.page_count
        doc.close()
        pages = utils.parse_page_ranges(pages_raw, total) if pages_raw else None
        out = utils.new_output_path(pdf.stem + "_marca", ".pdf")
        manipulator.add_watermark(
            pdf, out, text,
            opacity=opacity, fontsize=fontsize, rotation=rotation,
            color=editor._parse_color(color, default=(0.5, 0.5, 0.5)),
            position=position, pages=pages,
        )
        return _send(out, out.name)
    except Exception as e:
        log.exception("watermark")
        return _err(str(e), 500)


@app.route("/api/page-numbers", methods=["POST"])
def api_page_numbers():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        position = (request.form.get("position") or "bottom-center").lower()
        start = _read_int(request.form, "start", 1, -9999, 9999)
        fontsize = _read_int(request.form, "fontsize", 11, 6, 72)
        prefix = (request.form.get("prefix") or "")
        suffix = (request.form.get("suffix") or "")
        color = _read_color(request.form, "color", "#000000")
        out = utils.new_output_path(pdf.stem + "_numerado", ".pdf")
        manipulator.add_page_numbers(
            pdf, out,
            position=position, start=start, fontsize=fontsize,
            color=editor._parse_color(color, default=(0, 0, 0)),
            prefix=prefix, suffix=suffix,
        )
        return _send(out, out.name)
    except Exception as e:
        log.exception("page-numbers")
        return _err(str(e), 500)


@app.route("/api/protect", methods=["POST"])
def api_protect():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pwd = (request.form.get("password") or "").strip()
        owner = (request.form.get("owner_password") or "").strip() or None
        if not pwd:
            return _err("Falta la contrasena")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem + "_protegido", ".pdf")
        manipulator.protect_pdf(pdf, out, pwd, owner)
        return _send(out, out.name)
    except Exception as e:
        log.exception("protect")
        return _err(str(e), 500)


@app.route("/api/unlock", methods=["POST"])
def api_unlock():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pwd = (request.form.get("password") or "").strip()
        if not pwd:
            return _err("Falta la contrasena")
        pdf = _save_upload(f)
        out = utils.new_output_path(pdf.stem + "_desprotegido", ".pdf")
        manipulator.unlock_pdf(pdf, out, pwd)
        return _send(out, out.name)
    except Exception as e:
        log.exception("unlock")
        return _err(str(e), 500)


# -----------------------------------------------------------------------------
# API: edicion
# -----------------------------------------------------------------------------

def _json_rect(form, key: str) -> tuple:
    """Lee 'x,y,w,h' o un JSON {x,y,w,h}."""
    raw = (form.get(key) or "").strip()
    if not raw:
        raise ValueError(f"Falta {key}")
    if raw.startswith("{"):
        import json
        d = json.loads(raw)
        return (float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]))
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 4:
        raise ValueError(f"{key} debe ser x,y,w,h")
    return tuple(float(p) for p in parts)  # type: ignore


def _json_point(form, key: str) -> tuple:
    raw = (form.get(key) or "").strip()
    if not raw:
        raise ValueError(f"Falta {key}")
    parts = [p.strip() for p in raw.split(",")]
    if len(parts) != 2:
        raise ValueError(f"{key} debe ser x,y")
    return (float(parts[0]), float(parts[1]))


@app.route("/api/edit/rect", methods=["POST"])
def api_edit_rect():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        rect = _json_rect(request.form, "rect")
        color = _read_color(request.form, "color", "#ff0000")
        fill = (request.form.get("fill") or "").strip() or None
        width = _read_float(request.form, "width", 1.5, 0.1, 20)
        opacity = _read_float(request.form, "opacity", 1.0, 0.0, 1.0)
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.draw_rectangle(pdf, out, page, rect, color=color, fill=fill, width=width, opacity=opacity)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/rect")
        return _err(str(e), 500)


@app.route("/api/edit/circle", methods=["POST"])
def api_edit_circle():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        center = _json_point(request.form, "center")
        radius = _read_float(request.form, "radius", 20, 1, 2000)
        color = _read_color(request.form, "color", "#ff0000")
        fill = (request.form.get("fill") or "").strip() or None
        width = _read_float(request.form, "width", 1.5, 0.1, 20)
        opacity = _read_float(request.form, "opacity", 1.0, 0.0, 1.0)
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.draw_circle(pdf, out, page, center, radius, color=color, fill=fill, width=width, opacity=opacity)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/circle")
        return _err(str(e), 500)


@app.route("/api/edit/line", methods=["POST"])
def api_edit_line():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        start = _json_point(request.form, "start")
        end = _json_point(request.form, "end")
        color = _read_color(request.form, "color", "#000000")
        width = _read_float(request.form, "width", 1.0, 0.1, 20)
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.draw_line(pdf, out, page, start, end, color=color, width=width)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/line")
        return _err(str(e), 500)


@app.route("/api/edit/text", methods=["POST"])
def api_edit_text():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        point = _json_point(request.form, "point")
        text = request.form.get("text") or ""
        if not text:
            return _err("Falta 'text'")
        fontsize = _read_float(request.form, "fontsize", 14, 4, 200)
        color = _read_color(request.form, "color", "#000000")
        rotate = _read_float(request.form, "rotate", 0, -360, 360)
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.add_text(pdf, out, page, point, text, fontsize=fontsize, color=color, rotate=rotate)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/text")
        return _err(str(e), 500)


@app.route("/api/edit/image", methods=["POST"])
def api_edit_image():
    try:
        f = request.files.get("file")
        img = request.files.get("image")
        if not f or not img:
            return _err("Falta 'file' o 'image'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        rect = _json_rect(request.form, "rect")
        img_path = utils.new_upload_path(utils.safe_filename(img.filename))[0]
        img.save(str(img_path))
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.insert_image(pdf, out, page, rect, img_path)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/image")
        return _err(str(e), 500)


@app.route("/api/edit/signature", methods=["POST"])
def api_edit_signature():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        rect = _json_rect(request.form, "rect")
        b64 = request.form.get("image_base64") or ""
        if not b64:
            return _err("Falta 'image_base64'")
        out = utils.new_output_path(pdf.stem + "_firmado", ".pdf")
        editor.insert_signature(pdf, out, page, rect, b64)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/signature")
        return _err(str(e), 500)


@app.route("/api/edit/highlight", methods=["POST"])
def api_edit_highlight():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        text = (request.form.get("text") or "").strip()
        if not text:
            return _err("Falta 'text'")
        color = _read_color(request.form, "color", "#FFEB3B")
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.highlight_text(pdf, out, page, text, color=color)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/highlight")
        return _err(str(e), 500)


@app.route("/api/edit/note", methods=["POST"])
def api_edit_note():
    try:
        f = request.files.get("file")
        if not f:
            return _err("Falta el archivo 'file'")
        pdf = _save_upload(f)
        page = _read_int(request.form, "page", 1, 1)
        point = _json_point(request.form, "point")
        text = request.form.get("text") or ""
        if not text:
            return _err("Falta 'text'")
        title = (request.form.get("title") or "Nota")
        out = utils.new_output_path(pdf.stem + "_edit", ".pdf")
        editor.add_text_annotation(pdf, out, page, point, text, title=title)
        return _send(out, out.name)
    except Exception as e:
        log.exception("edit/note")
        return _err(str(e), 500)


# -----------------------------------------------------------------------------
# Helper: enviar archivo con headers correctos
# -----------------------------------------------------------------------------

def _send(path: Path, download_name: str):
    if not path.exists() or path.stat().st_size == 0:
        return _err("El servidor produjo un archivo vacio", 500)
    return send_file(
        str(path),
        as_attachment=True,
        download_name=download_name,
        max_age=0,
    )


# -----------------------------------------------------------------------------
# Error handlers
# -----------------------------------------------------------------------------

@app.errorhandler(413)
def too_large(e):
    return _err(f"Archivo demasiado grande. Maximo {utils.MAX_FILE_SIZE // (1024*1024)} MB.", 413)


@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return _err("Endpoint no encontrado", 404)
    return ("Not Found", 404)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    # Limpieza inicial
    utils.cleanup_old_files(0)
    port = int(os.environ.get("PDFTOOL_PORT", "5050"))
    host = os.environ.get("PDFTOOL_HOST", "127.0.0.1")
    url = f"http://{host}:{port}"
    log.info("PDF Ninja iniciando en %s", url)
    print()
    print("=" * 60)
    print(f"  PDF Ninja - servidor local")
    print(f"  Abre en tu navegador: {url}")
    print("  Ctrl+C para detener")
    print("=" * 60)
    print()
    # use_reloader=False evita doble inicio en Windows
    app.run(host=host, port=port, debug=False, use_reloader=False, threaded=True)


if __name__ == "__main__":
    main()
