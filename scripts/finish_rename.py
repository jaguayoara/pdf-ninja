"""Limpia las referencias a Papiro en JS, CSS y scripts."""
from pathlib import Path

BASE = Path('C:/Users/jagua/Desktop/Pdftool')

REPLACEMENTS = [
    # JS object name + localStorage key
    ('window.PdfNinja = (function', 'window.PdfNinja = (function'),  # safety
    ('window.Papiro', 'window.PdfNinja'),
    ('Papiro.', 'PdfNinja.'),
    ("'papiro-theme'", "'pdfninja-theme'"),
    ('"papiro-theme"', '"pdfninja-theme"'),
    # Comments and titles
    ('Papiro -', 'Pdf Ninja -'),
]

FILES = [
    'static/js/main.js',
    'static/js/tools.js',
    'static/css/style.css',
    'scripts/rename_to_pdf_ninja.py',  # limpieza del script mismo
]


def main():
    for rel in FILES:
        p = BASE / rel
        if not p.exists():
            print(f"  SKIP: {rel}")
            continue
        text = p.read_text(encoding='utf-8')
        original = text
        for old, new in REPLACEMENTS:
            text = text.replace(old, new)
        if text != original:
            p.write_text(text, encoding='utf-8')
            print(f"  OK: {rel}")
        else:
            print(f"  - sin cambios: {rel}")


if __name__ == '__main__':
    main()
