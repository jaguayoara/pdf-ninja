"""Script de smoke-testing de los endpoints de PDF Ninja."""
import io
import os
import sys
import time
from pathlib import Path

import requests

BASE = "http://127.0.0.1:5050"
TEST_PDF = Path("test.pdf")
TEST_PDF2 = Path("test2.pdf")
TEST_IMG = Path("test.png")

PASS = []
FAIL = []


def check(name, ok, detail=""):
    if ok:
        PASS.append(name)
        print(f"  OK   {name}")
    else:
        FAIL.append((name, detail))
        print(f"  FAIL {name}: {detail}")


def post_file(endpoint, file_path, extra=None):
    url = BASE + endpoint
    files = {"file": (file_path.name, open(file_path, "rb"), "application/octet-stream")}
    data = extra or {}
    try:
        r = requests.post(url, files=files, data=data, timeout=120)
    finally:
        files["file"][1].close()
    return r


def post_files(endpoint, paths, extra=None):
    files = [("files", (p.name, open(p, "rb"), "application/octet-stream")) for p in paths]
    data = extra or {}
    try:
        r = requests.post(BASE + endpoint, files=files, data=data, timeout=120)
    finally:
        for _, (_, fh, _) in files:
            fh.close()
    return r


# ---- Setup ---------------------------------------------------------------
print("Setup: creando PDF de prueba adicional e imagen...")
import fitz
from PIL import Image, ImageDraw, ImageFont

if not TEST_PDF2.exists():
    doc = fitz.open()
    for i in range(2):
        p = doc.new_page()
        p.insert_text((72, 100), f"Documento B - Pagina {i+1}", fontsize=18)
        p.insert_text((72, 140), "Contenido del segundo PDF para fusionar.", fontsize=12)
    doc.save(str(TEST_PDF2))
    doc.close()

if not TEST_IMG.exists():
    img = Image.new("RGB", (800, 600), (220, 240, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([(50, 50), (750, 550)], outline=(60, 100, 200), width=4)
    d.text((100, 250), "Imagen de prueba", fill=(40, 60, 120))
    img.save(str(TEST_IMG))

print()


# ---- Tests ---------------------------------------------------------------
def t_info():
    r = post_file("/api/info", TEST_PDF)
    check("info", r.ok and r.json().get("ok"), r.text[:200])


def t_pdf_to_word():
    r = post_file("/api/pdf-to-word", TEST_PDF)
    check("pdf-to-word", r.ok and len(r.content) > 1000, f"status={r.status_code}, size={len(r.content)}")


def t_pdf_to_excel():
    r = post_file("/api/pdf-to-excel", TEST_PDF)
    check("pdf-to-excel", r.ok and len(r.content) > 1000, f"status={r.status_code}, size={len(r.content)}")


def t_pdf_to_images():
    r = post_file("/api/pdf-to-images", TEST_PDF, {"format": "png", "dpi": "100", "zip": "1"})
    check("pdf-to-images (zip)", r.ok and len(r.content) > 1000, f"status={r.status_code}, size={len(r.content)}")


def t_images_to_pdf():
    r = post_files("/api/images-to-pdf", [TEST_IMG, TEST_IMG])
    check("images-to-pdf", r.ok and len(r.content) > 1000, f"status={r.status_code}, size={len(r.content)}")


def t_pdf_to_text():
    r = post_file("/api/pdf-to-text", TEST_PDF)
    check("pdf-to-text", r.ok and b"Pagina" in r.content, f"status={r.status_code}")


def t_pdf_to_pdfa():
    r = post_file("/api/pdf-to-pdfa", TEST_PDF)
    check("pdf-to-pdfa", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_merge():
    r = post_files("/api/merge", [TEST_PDF, TEST_PDF2])
    check("merge", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_split():
    r = post_file("/api/split", TEST_PDF, {"ranges": "1-2;3"})
    check("split (multi-grupo)", r.ok and len(r.content) > 1000, f"status={r.status_code}")
    r = post_file("/api/split", TEST_PDF, {"ranges": "1", "zip": "0"})
    check("split (una parte)", r.ok and len(r.content) > 500, f"status={r.status_code}")


def t_organize():
    r = post_file("/api/organize", TEST_PDF, {"order": "3,2,1"})
    check("organize", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_rotate():
    r = post_file("/api/rotate", TEST_PDF, {"angle": "90"})
    check("rotate 90", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_compress():
    r = post_file("/api/compress", TEST_PDF, {"quality": "medium"})
    check("compress", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_watermark():
    r = post_file("/api/watermark", TEST_PDF, {
        "text": "CONFIDENCIAL", "position": "center",
        "fontsize": "36", "color": "#ff0000", "rotation": "45", "opacity": "0.3"
    })
    check("watermark", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_page_numbers():
    r = post_file("/api/page-numbers", TEST_PDF, {"position": "bottom-center", "start": "1"})
    check("page-numbers", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_protect():
    r = post_file("/api/protect", TEST_PDF, {"password": "secret123"})
    check("protect", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_unlock():
    # Primero proteger, luego desproteger
    r1 = post_file("/api/protect", TEST_PDF, {"password": "abc123"})
    if r1.ok:
        Path("test_protected.pdf").write_bytes(r1.content)
        r2 = post_file("/api/unlock", Path("test_protected.pdf"), {"password": "abc123"})
        check("unlock", r2.ok and len(r2.content) > 1000, f"status={r2.status_code}")
    else:
        check("unlock", False, "no se pudo crear PDF protegido")


def t_edit_text():
    r = post_file("/api/edit/text", TEST_PDF, {
        "page": "1", "point": "100,500", "text": "Hola Mundo", "fontsize": "20", "color": "#0033cc"
    })
    check("edit/text", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_edit_rect():
    r = post_file("/api/edit/rect", TEST_PDF, {
        "page": "1", "rect": "50,400,200,100", "color": "#ff0000", "width": "2", "fill": "#ffeb3b"
    })
    check("edit/rect", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_edit_highlight():
    r = post_file("/api/edit/highlight", TEST_PDF, {
        "page": "1", "text": "prueba", "color": "#FFEB3B"
    })
    check("edit/highlight", r.ok and len(r.content) > 1000, f"status={r.status_code}")


def t_edit_note():
    r = post_file("/api/edit/note", TEST_PDF, {
        "page": "1", "point": "200,300", "text": "Esto es una nota", "title": "Comentario"
    })
    check("edit/note", r.ok and len(r.content) > 1000, f"status={r.status_code}")


# ---- Main ---------------------------------------------------------------
tests = [
    t_info, t_pdf_to_word, t_pdf_to_excel, t_pdf_to_images,
    t_images_to_pdf, t_pdf_to_text, t_pdf_to_pdfa,
    t_merge, t_split, t_organize, t_rotate, t_compress,
    t_watermark, t_page_numbers, t_protect, t_unlock,
    t_edit_text, t_edit_rect, t_edit_highlight, t_edit_note,
]
for t in tests:
    print(f"\n--- {t.__name__} ---")
    try:
        t()
    except Exception as e:
        check(t.__name__, False, f"excepcion: {e}")

print()
print("=" * 60)
print(f"Pasados: {len(PASS)}/{len(PASS) + len(FAIL)}")
if FAIL:
    print("Fallaron:")
    for n, d in FAIL:
        print(f"  - {n}: {d[:150]}")
    sys.exit(1)
print("Todos los endpoints funcionan correctamente.")
