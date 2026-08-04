"""
Modulo de edicion PDF server-side (operaciones batch).
El editor visual interactivo vive en el frontend (PDF.js + pdf-lib).
Aqui estan operaciones de edicion no visuales:
- Insertar imagen en una pagina
- Dibujar rectangulo / circulo / linea
- Anotaciones (highlight, texto, nota)
- Redaccion (eliminar area)
- Firmar (insertar imagen de firma)
"""
from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import fitz
from PIL import Image

from . import utils


Rect = Tuple[float, float, float, float]


def _parse_color(color, default=(0, 0, 0)) -> Tuple[float, float, float]:
    """Acepta hex (#RRGGBB) o tupla/list de 3 floats 0-1."""
    if not color:
        return default
    if isinstance(color, str):
        s = color.lstrip("#")
        if len(s) == 6:
            r = int(s[0:2], 16) / 255
            g = int(s[2:4], 16) / 255
            b = int(s[4:6], 16) / 255
            return (r, g, b)
        if len(s) == 3:
            r = int(s[0] * 2, 16) / 255
            g = int(s[1] * 2, 16) / 255
            b = int(s[2] * 2, 16) / 255
            return (r, g, b)
        return default
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return (float(color[0]), float(color[1]), float(color[2]))
    return default


# --- Dibujar formas ----------------------------------------------------

def draw_rectangle(pdf_path: Path, out_path: Path, page_num: int, rect: Rect,
                   color="#ff0000", width: float = 1.5, fill: Optional[str] = None,
                   opacity: float = 1.0) -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        r = fitz.Rect(*rect)
        col = _parse_color(color)
        if fill:
            fcol = _parse_color(fill)
            page.draw_rect(r, color=col, fill=fcol, width=width, overlay=True, fill_opacity=opacity)
        else:
            page.draw_rect(r, color=col, width=width, overlay=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


def draw_circle(pdf_path: Path, out_path: Path, page_num: int, center: Tuple[float, float],
                radius: float, color="#ff0000", width: float = 1.5, fill: Optional[str] = None,
                opacity: float = 1.0) -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        r = fitz.Rect(center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
        col = _parse_color(color)
        if fill:
            fcol = _parse_color(fill)
            page.draw_oval(r, color=col, fill=fcol, width=width, overlay=True, fill_opacity=opacity)
        else:
            page.draw_oval(r, color=col, width=width, overlay=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


def draw_line(pdf_path: Path, out_path: Path, page_num: int, start: Tuple[float, float],
              end: Tuple[float, float], color="#000000", width: float = 1.0) -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        col = _parse_color(color)
        page.draw_line(fitz.Point(*start), fitz.Point(*end), color=col, width=width, overlay=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


def add_text(pdf_path: Path, out_path: Path, page_num: int, point: Tuple[float, float],
             text: str, fontsize: float = 14, color="#000000",
             fontname: str = "helv", rotate: float = 0) -> Path:
    utils.ensure_pdf(pdf_path)
    if not text:
        raise ValueError("Texto vacio")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        col = _parse_color(color)
        # Validar font
        try:
            font = fitz.Font(fontname)
        except Exception:
            font = fitz.Font("helv")
        page.insert_text(
            fitz.Point(*point),
            text,
            fontsize=fontsize,
            fontname=font.name,
            color=col,
            rotate=rotate,
            overlay=True,
        )
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


# --- Insertar imagen / firma -------------------------------------------

def insert_image(pdf_path: Path, out_path: Path, page_num: int, rect: Rect,
                 image_path: Path) -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not image_path.exists():
        raise FileNotFoundError(f"Imagen no encontrada: {image_path}")
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        page.insert_image(fitz.Rect(*rect), filename=str(image_path), overlay=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


def insert_signature(pdf_path: Path, out_path: Path, page_num: int, rect: Rect,
                     image_b64: str) -> Path:
    """Inserta firma desde una imagen en base64 (PNG/JPG)."""
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    try:
        data = base64.b64decode(image_b64)
    except Exception as e:
        raise ValueError("Imagen base64 invalida") from e
    if not data:
        raise ValueError("Imagen base64 vacia")

    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        page.insert_image(fitz.Rect(*rect), stream=data, overlay=True)
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


# --- Anotaciones de resaltado ------------------------------------------

def highlight_text(pdf_path: Path, out_path: Path, page_num: int, text: str,
                   color="#FFEB3B") -> Path:
    """Resalta todas las ocurrencias de `text` en la pagina."""
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        rects = page.search_for(text)
        if not rects:
            raise ValueError(f"Texto no encontrado en la pagina: {text!r}")
        col = _parse_color(color, default=(1, 0.92, 0.23))
        for r in rects:
            annot = page.add_highlight_annot(r)
            annot.set_colors(stroke=col)
            annot.update()
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


def add_text_annotation(pdf_path: Path, out_path: Path, page_num: int,
                         point: Tuple[float, float], text: str,
                         title: str = "Comentario") -> Path:
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not text:
        raise ValueError("Texto vacio")
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        # add_text_annot no acepta 'title'; lo establecemos despues
        annot = page.add_text_annot(fitz.Point(*point), text)
        try:
            annot.set_info({"title": title, "content": text})
        except Exception:
            pass
        annot.update()
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path


# --- Redaccion (eliminar contenido) -----------------------------------

def redact_area(pdf_path: Path, out_path: Path, page_num: int, rect: Rect,
                color=(1, 1, 1)) -> Path:
    """Cubre el area con un rectangulo blanco opaco. No es redaction real (el
    texto sigue en el stream); usar con cuidado o post-procesar con pikepdf."""
    utils.ensure_pdf(pdf_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(pdf_path))
    try:
        if not (1 <= page_num <= doc.page_count):
            raise ValueError(f"Pagina fuera de rango: {page_num}")
        page = doc[page_num - 1]
        page.add_redact_annot(fitz.Rect(*rect), fill=color)
        page.apply_redactions()
        doc.save(str(out_path), garbage=4, deflate=True)
    finally:
        doc.close()
    return out_path
