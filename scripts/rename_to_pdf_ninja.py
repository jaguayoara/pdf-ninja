"""
Renombra Pdf Ninja -> Pdf Ninja en todos los archivos de texto relevantes
y renombra archivos .spec / .bat / .log.

Lo que cambia:
  - Cadenas visibles: 'Papiro' -> 'Pdf Ninja' (titulo de ventana, banners, HTML, README)
  - Cadenas internas: 'papiro' -> 'pdfninja' (logger name, nombres de archivo)
  - Archivos: PdfNinja.spec -> PdfNinja.spec, PdfNinja.bat -> PdfNinja.bat
"""
from pathlib import Path
import re

BASE = Path('C:/Users/jagua/Desktop/Pdftool')

# Archivos a procesar (relativos a BASE)
FILES = [
    'desktop.py',
    'PdfNinja.spec',
    'README.md',
    'build.bat',
    'PdfNinja.bat',
    'start.bat',
    'app.py',
    'core/icons.py',
    'core/utils.py',
    'core/__init__.py',
    'templates/base.html',
    'templates/index.html',
    'templates/tool_generic.html',
    # Tests (no se distribuyen pero los mantenemos consistentes)
    'test_endpoints.py',
    'test_editor_load.py',
    'test_outputs.py',
]

# Renombramientos de archivo
RENAMES = {
    'PdfNinja.spec': 'PdfNinja.spec',
    'PdfNinja.bat': 'PdfNinja.bat',
}

# Reemplazos dentro de archivos
#  - texto (mayusculas): "Papiro" -> "Pdf Ninja"  (titulos, banners, copy)
#  - codigo (minusculas): "papiro" -> "pdfninja" (logger, log file, identificadores)
REPLACEMENTS = [
    ('Pdf Ninja Ninja', 'Pdf Ninja'),  # safety: evitar duplicacion si se corre 2 veces
    ('Pdf Ninja', 'Pdf Ninja'),
    ('Papiro', 'Pdf Ninja'),           # si quedaba algun Papiro suelto
    ('pdfninja.log', 'pdfninja.log'),
    ('papiro.log', 'pdfninja.log'),
    ('pdfninja', 'pdfninja'),
    ('papiro', 'pdfninja'),
]

# Excluir archivos donde no debe tocar
EXCLUDE_PATTERNS = [
    re.compile(r'\.git/'),
    re.compile(r'build/'),
    re.compile(r'dist/'),
    re.compile(r'__pycache__/'),
    re.compile(r'outputs/'),
    re.compile(r'uploads/'),
]


def should_skip(path: Path) -> bool:
    rel = str(path.relative_to(BASE)).replace('\\', '/')
    return any(p.search(rel) for p in EXCLUDE_PATTERNS)


def process_file(path: Path) -> int:
    """Lee el archivo, aplica reemplazos, escribe de vuelta. Retorna numero
    de cambios."""
    text = path.read_text(encoding='utf-8')
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        path.write_text(text, encoding='utf-8')
        return sum(1 for a, b in zip(original.splitlines(), text.splitlines()) if a != b)
    return 0


def main():
    changed_files = []
    for rel in FILES:
        p = BASE / rel
        if not p.exists():
            print(f"  - SKIP (no existe): {rel}")
            continue
        n = process_file(p)
        if n > 0:
            changed_files.append((rel, n))
            print(f"  OK ({n} lineas cambiadas): {rel}")
        else:
            print(f"  - sin cambios: {rel}")

    print()
    print("Renombrando archivos:")
    for old, new in RENAMES.items():
        old_p = BASE / old
        new_p = BASE / new
        if old_p.exists() and not new_p.exists():
            old_p.rename(new_p)
            print(f"  {old} -> {new}")
        elif new_p.exists():
            print(f"  {old} -> {new} (destino ya existe, no renombrado)")
        else:
            print(f"  {old} (no existe)")

    print()
    print(f"Listo. {len(changed_files)} archivos modificados.")


if __name__ == '__main__':
    main()
