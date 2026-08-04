"""Test que descarga outputs reales y los valida."""
import requests
from pathlib import Path
import fitz

out_dir = Path("test_outputs")
out_dir.mkdir(exist_ok=True)


def save(endpoint, files, data, name):
    """files puede ser dict o list, data dict, name str."""
    try:
        r = requests.post(f"http://127.0.0.1:5050{endpoint}", files=files, data=data, timeout=60)
        # cerrar fileobjs
        if isinstance(files, dict):
            for v in files.values():
                if hasattr(v, "close"): v.close()
                elif isinstance(v, (list, tuple)):
                    for sub in v:
                        if hasattr(sub, "close"): sub.close()
        elif isinstance(files, (list, tuple)):
            for item in files:
                if isinstance(item, (list, tuple)):
                    # ('field', (filename, fileobj, ctype))
                    inner = item[1] if len(item) >= 2 else None
                    if isinstance(inner, (list, tuple)):
                        for sub in inner:
                            if hasattr(sub, "close"): sub.close()
                    elif hasattr(inner, "close"):
                        inner.close()
                elif hasattr(item, "close"):
                    item.close()
        if r.ok:
            out = out_dir / name
            out.write_bytes(r.content)
            print(f"  {endpoint:35s} -> {name} ({len(r.content)} bytes)")
            return out
        else:
            print(f"  {endpoint:35s} -> FAIL {r.status_code} {r.text[:150]}")
    except Exception as e:
        print(f"  {endpoint:35s} -> EXCEPTION {e}")
    return None


# Generar outputs
out = save("/api/pdf-to-word", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {}, "out.docx")
out = save("/api/pdf-to-excel", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {}, "out.xlsx")
out = save("/api/pdf-to-text", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {}, "out.txt")
out = save("/api/pdf-to-images", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"zip": "1", "format": "png", "dpi": "100"}, "out_images.zip")
out = save("/api/merge", [("files", ("test.pdf", open("test.pdf", "rb"), "application/pdf")), ("files", ("test2.pdf", open("test2.pdf", "rb"), "application/pdf"))], {}, "merged.pdf")
out = save("/api/watermark", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"text": "CONFIDENCIAL", "position": "center", "fontsize": "36", "color": "#ff0000", "rotation": "45", "opacity": "0.3"}, "watermarked.pdf")
out = save("/api/compress", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"quality": "medium"}, "compressed.pdf")
out = save("/api/split", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"ranges": "1-2;3"}, "split.zip")
out = save("/api/rotate", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"angle": "90"}, "rotated.pdf")
out = save("/api/page-numbers", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"position": "bottom-center", "start": "1"}, "numbered.pdf")
out = save("/api/protect", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"password": "abc"}, "protected.pdf")
out = save("/api/images-to-pdf", [("files", ("test.png", open("test.png", "rb"), "image/png"))], {}, "from_images.pdf")
out = save("/api/edit/text", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"page": "1", "point": "100,500", "text": "Modificado", "fontsize": "16"}, "edited_text.pdf")
out = save("/api/edit/rect", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"page": "1", "rect": "50,400,200,100", "color": "#ff0000", "width": "2", "fill": "#ffeb3b"}, "edited_rect.pdf")
out = save("/api/edit/highlight", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"page": "1", "text": "prueba"}, "edited_highlight.pdf")
out = save("/api/edit/note", {"file": ("test.pdf", open("test.pdf", "rb"), "application/pdf")}, {"page": "1", "point": "200,300", "text": "Esto es una nota"}, "edited_note.pdf")

print()
print("Validando PDFs descargados:")
for pdf in out_dir.glob("*.pdf"):
    try:
        d = fitz.open(str(pdf))
        print(f"  {pdf.name:30s}: {d.page_count} paginas - OK")
        d.close()
    except Exception as e:
        print(f"  {pdf.name:30s}: INVALIDO - {e}")

# Validar el ZIP de imagenes
import zipfile
zp = out_dir / "out_images.zip"
if zp.exists():
    with zipfile.ZipFile(zp) as zf:
        print(f"  {zp.name:30s}: {len(zf.namelist())} archivos en zip")

# Validar el docx
if (out_dir / "out.docx").exists():
    with zipfile.ZipFile(out_dir / "out.docx") as zf:
        names = zf.namelist()
        print(f"  out.docx: {len(names)} partes, contiene 'word/document.xml': {'word/document.xml' in names}")

# Validar xlsx
if (out_dir / "out.xlsx").exists():
    with zipfile.ZipFile(out_dir / "out.xlsx") as zf:
        names = zf.namelist()
        print(f"  out.xlsx: {len(names)} partes, contiene 'xl/workbook.xml': {'xl/workbook.xml' in names}")

# Texto
if (out_dir / "out.txt").exists():
    text = (out_dir / "out.txt").read_text(encoding="utf-8")
    print(f"  out.txt: {len(text)} chars, contiene 'Pagina': {'Pagina' in text}")

# ZIP del split
szp = out_dir / "split.zip"
if szp.exists():
    with zipfile.ZipFile(szp) as zf:
        print(f"  split.zip: {len(zf.namelist())} partes -> {zf.namelist()}")
