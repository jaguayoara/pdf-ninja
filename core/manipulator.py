"""
Modulo de manipulacion de PDFs: dividir, fusionar, rotar, comprimir,
organizar, marca de agua, numeros de pagina, proteger/desproteger.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import fitz  # PyMuPDF
import pikepdf
from PIL import Image

from . import utils


# --- Fusionar ------------------------------------------------------------

def merge_pdfs(pdf_paths: Sequence[Path], out_path: Path) -> Path:
    """Fusiona varios PDFs en uno solo, en el orden dado."""
    if not pdf_paths:
        raise ValueError("No se proporcionaron PDFs para fusionar")
    for p in pdf_paths:
        utils.ensure_pdf(p)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    result = fitz.open()
    try:
        for p in pdf_paths:
            with fitz.open(str(p)) as src:
                result.insert_pdf(src)
        result.save(str(out_path), garbage=4, deflate=True)
    finally:
        result.close()
    return out_path


# --- Dividir -------------------------------------------------------------

def split_pdf(pdf_path: Path, out_dir: Path, groups: List[List[int]]) -> List[Path]:
    """
    Divide el PDF segun `groups` (lista de listas de paginas 1-based).
    Cada grupo produce un PDF independiente. Los grupos pueden superponerse.
    """
    utils.ensure_pdf(pdf_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_dir = out_dir.resolve()

    # Validar y deduplicar grupos
    cleaned: List[List[int]] = []
    for g in groups:
        if not g:
            continue
        seen = set()
        ug = []
        for n in g:
            if n in seen:
                continue
            seen.add(n)
            ug.append(n)
        cleaned.append(sorted(ug))
    if not cleaned:
        raise ValueError("Los rangos de paginas no producen ningun grupo")

    src = fitz.open(str(pdf_path))
    outputs: List[Path] = []
    try:
        total = src.page_count
        for idx, group in enumerate(cleaned, start=1):
            out_doc = fitz.open()
            for n in group:
                if 1 <= n <= total:
                    out_doc.insert_pdf(src, from_page=n - 1, to_page=n - 1)
            if out_doc.page_count == 0:
                out_doc.close()
                continue
            out_file = out_dir / f"{pdf_path.stem}_parte_{idx}.pdf"
            out_file = utils.ensure_within_dir(out_file, out_dir)
            out_doc.save(str(out_file), garbage=4, deflate=True)
            out_doc.close()
            outputs.append(out_file)
    finally:
        src.close()

    if not outputs:
        raise RuntimeError("La division no produjo archivos validos")
    return outputs


def split_pdf_zip(pdf_path: Path, out_zip: Path, groups: List[List[int]]) -> Path:
    """Igual a split_pdf pero devuelve un .zip con todas las partes."""
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        files = split_pdf(pdf_path, tmp, groups)
        with __import__("zipfile").ZipFile(str(out_zip), "w", __import__("zipfile").ZIP_DEFLATED) as zf:
            for f in files:
                zf.write(str(f), arcname=f.name)
    return out_zip


# --- Organizar (reordenar / eliminar) -----------------------------------

def organize_pdf(pdf_path: Path, out_path: Path, order: List[int]) -> Path:
    """
    Reordena y/o elimina paginas.
    `order` es una lista de indices 1-based en el orden deseado.
    """
    utils.ensure_pdf(pdf_path)
    if not order:
        raise ValueError("Debe especificar al menos una pagina")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = fitz.open(str(pdf_path))
    try:
        total = src.page_count
        for n in order:
            if not (1 <= n <= total):
                raise ValueError(f"Pagina fuera de rango: {n}")
        out_doc = fitz.open()
        for n in order:
            out_doc.insert_pdf(src, from_page=n - 1, to_page=n - 1)
        out_doc.save(str(out_path), garbage=4, deflate=True)
        out_doc.close()
    finally:
        src.close()
    return out_path


# --- Rotar ---------------------------------------------------------------

def rotate_pdf(pdf_path: Path, out_path: Path, angle: int, pages: Optional[List[int]] = None) -> Path:
    """
    Rota paginas. `angle` debe ser multiplo de 90 (90, 180, 270, -90, etc).
    Si `pages` es None, rota todas.
    """
    if angle % 90 != 0:
        raise ValueError("El angulo debe ser multiplo de 90 grados")
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = fitz.open(str(pdf_path))
    try:
        if pages is None:
            pages = list(range(1, src.page_count + 1))
        for n in pages:
            if not (1 <= n <= src.page_count):
                raise ValueError(f"Pagina fuera de rango: {n}")
            page = src[n - 1]
            page.set_rotation((page.rotation + angle) % 360)
        src.save(str(out_path), garbage=4, deflate=True)
    finally:
        src.close()
    return out_path


# --- Comprimir -----------------------------------------------------------

def compress_pdf(pdf_path: Path, out_path: Path, quality: str = "medium") -> Path:
    """
    Reduce el tamano del PDF.
    quality: 'low' | 'medium' | 'high'
      low    -> rasteriza paginas a ~72 dpi JPG baja calidad
      medium -> rasteriza a ~120 dpi JPG calidad media (default)
      high   -> rasteriza a ~150 dpi JPG alta calidad
    NOTA: la rasterizacion convierte el PDF en imagenes, por lo que el texto
    deja de ser seleccionable. Para compresion sin perder texto, prueba primero
    'optimize' (aun no implementado para PDFs muy grandes).
    """
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    settings = {
        "low":    {"dpi": 72,  "jpg_quality": 50},
        "medium": {"dpi": 120, "jpg_quality": 72},
        "high":   {"dpi": 150, "jpg_quality": 85},
    }
    s = settings.get(quality, settings["medium"])

    src = fitz.open(str(pdf_path))
    try:
        out_doc = fitz.open()
        zoom = s["dpi"] / 72.0
        mat = fitz.Matrix(zoom, zoom)
        for page in src:
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=s["jpg_quality"], optimize=True)
            buf.seek(0)
            # Crear nueva pagina con mismo tamano en puntos
            rect = fitz.Rect(0, 0, page.rect.width, page.rect.height)
            new_page = out_doc.new_page(width=rect.width, height=rect.height)
            new_page.insert_image(rect, stream=buf.getvalue())
        out_doc.save(str(out_path), garbage=4, deflate=True)
        out_doc.close()
    finally:
        src.close()
    return out_path


# --- Marca de agua -------------------------------------------------------

def add_watermark(
    pdf_path: Path,
    out_path: Path,
    text: str,
    opacity: float = 0.3,
    fontsize: int = 48,
    rotation: int = 45,
    color: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    position: str = "center",  # 'center' | 'tile' | 'top' | 'bottom'
    pages: Optional[List[int]] = None,
) -> Path:
    """Anade marca de agua de texto al PDF. Soporta rotacion arbitraria."""
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not text.strip():
        raise ValueError("El texto de la marca de agua no puede estar vacio")
    if not (0.05 <= opacity <= 1.0):
        raise ValueError("Opacidad debe estar entre 0.05 y 1.0")
    # Mezclar opacidad con el color
    bg = (1.0, 1.0, 1.0)
    blended = tuple(color[i] * opacity + bg[i] * (1 - opacity) for i in range(3))
    src = fitz.open(str(pdf_path))
    try:
        if pages is None:
            pages = list(range(1, src.page_count + 1))
        font = fitz.Font("helv")
        for n in pages:
            if not (1 <= n <= src.page_count):
                raise ValueError(f"Pagina fuera de rango: {n}")
            page = src[n - 1]
            rect = page.rect

            def draw_at(cx: float, cy: float) -> None:
                # Calcular ancho del texto y colocarlo centrado horizontalmente
                try:
                    text_w = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
                except Exception:
                    text_w = fontsize * 0.55 * max(len(text), 1)
                # Posicion: baseline a la altura de cy, x = cx - text_w/2
                pos = (cx - text_w / 2, cy + fontsize * 0.35)
                tw = fitz.TextWriter(page.rect)
                tw.append(pos, text, font=font, fontsize=fontsize)
                # Rotar el texto alrededor de (cx, cy) y aplicar color
                # M = T(cx,cy) * R(theta) * T(-cx,-cy)
                rot_mat = fitz.Matrix(1, 0, 0, 1, -cx, -cy)
                rot_mat = rot_mat.prerotate(rotation)
                rot_mat = rot_mat.pretranslate(cx, cy)
                tw.write_text(page, color=blended, matrix=rot_mat)

            if position == "tile":
                step_x = max(150, fontsize * 6)
                step_y = max(150, fontsize * 6)
                y = 0
                while y < rect.height:
                    x = 0
                    while x < rect.width:
                        draw_at(x + step_x / 2, y + step_y / 2)
                        x += step_x
                    y += step_y
            elif position == "top":
                draw_at(rect.width / 2, rect.height * 0.15)
            elif position == "bottom":
                draw_at(rect.width / 2, rect.height * 0.85)
            else:  # center
                draw_at(rect.width / 2, rect.height / 2)

        src.save(str(out_path), garbage=4, deflate=True, encryption=fitz.PDF_ENCRYPT_KEEP)
    finally:
        src.close()
    return out_path


# --- Numeros de pagina ---------------------------------------------------

def add_page_numbers(
    pdf_path: Path,
    out_path: Path,
    position: str = "bottom-center",  # bottom-center | bottom-right | top-center | top-right
    start: int = 1,
    fontsize: int = 11,
    color: Tuple[float, float, float] = (0, 0, 0),
    prefix: str = "",
    suffix: str = "",
) -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = fitz.open(str(pdf_path))
    try:
        total = src.page_count
        for i, page in enumerate(src, start=1):
            rect = page.rect
            n = start + (i - 1)
            label = f"{prefix}{n}{suffix}"
            margin = 24
            if position.startswith("bottom"):
                y = rect.height - margin
            else:
                y = margin + fontsize
            if position.endswith("right"):
                box = fitz.Rect(rect.width - margin - 80, y - fontsize, rect.width - margin, y + 4)
                align = 2  # right
            elif position.endswith("left"):
                box = fitz.Rect(margin, y - fontsize, margin + 80, y + 4)
                align = 0  # left
            else:  # center
                box = fitz.Rect(rect.width / 2 - 40, y - fontsize, rect.width / 2 + 40, y + 4)
                align = 1
            page.insert_textbox(box, label, fontsize=fontsize, color=color, align=align, overlay=True)
        src.save(str(out_path), garbage=4, deflate=True)
    finally:
        src.close()
    return out_path


# --- Proteger (password) ------------------------------------------------

def protect_pdf(pdf_path: Path, out_path: Path, user_pwd: str, owner_pwd: Optional[str] = None) -> Path:
    """Cifra el PDF con password (AES-256)."""
    if not user_pwd:
        raise ValueError("La contrasena no puede estar vacia")
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    src = pikepdf.open(str(pdf_path))
    try:
        owner = owner_pwd or user_pwd
        # AES-256 con R6
        src.save(
            str(out_path),
            encryption=pikepdf.Encryption(
                user=user_pwd,
                owner=owner,
                aes=True,
                R=6,
            ),
        )
    finally:
        src.close()
    return out_path


# --- Desproteger --------------------------------------------------------

def unlock_pdf(pdf_path: Path, out_path: Path, password: str) -> Path:
    """Quita la contrasena del PDF."""
    if not password:
        raise ValueError("Debes proporcionar la contrasena")
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        src = pikepdf.open(str(pdf_path), password=password)
    except pikepdf.PasswordError as e:
        raise ValueError("Contrasena incorrecta") from e
    try:
        src.save(str(out_path))
    finally:
        src.close()
    return out_path


# --- Info del PDF -------------------------------------------------------

def pdf_info(pdf_path: Path) -> dict:
    """Devuelve metadata basica del PDF."""
    utils.ensure_pdf(pdf_path)
    doc = fitz.open(str(pdf_path))
    try:
        meta = doc.metadata or {}
        size = pdf_path.stat().st_size
        return {
            "pages": doc.page_count,
            "metadata": {k: str(v) for k, v in meta.items() if v},
            "encrypted": doc.is_encrypted,
            "size_bytes": size,
            "size_human": utils.human_size(size),
            "filename": pdf_path.name,
            "outline": [
                {"level": item[0], "title": item[1], "page": item[2]}
                for item in (doc.get_toc() or [])
            ],
        }
    finally:
        doc.close()
