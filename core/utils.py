"""
Utilidades compartidas para Pdf Ninja.
Manejo de archivos, validacion, helpers de paginas/rangos.
"""
from __future__ import annotations

import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

# Limites
MAX_FILE_SIZE = 200 * 1024 * 1024  # 200 MB
ALLOWED_PDF_EXT = {".pdf"}
ALLOWED_IMG_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp", ".gif"}

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def safe_filename(name: str) -> str:
    """Devuelve un nombre de archivo seguro sin caracteres problematicos."""
    name = Path(name).name
    name = re.sub(r"[^\w.\-]+", "_", name, flags=re.UNICODE)
    return name[:200] or "archivo"


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


def new_upload_path(original_name: str) -> Tuple[Path, str]:
    """Crea una ruta unica en uploads/ y devuelve (path, file_id)."""
    fid = f"{int(time.time())}_{gen_id()}"
    ext = Path(safe_filename(original_name)).suffix.lower()
    path = UPLOAD_DIR / f"{fid}{ext}"
    return path, fid


def new_output_path(stem: str, ext: str) -> Path:
    """Genera una ruta unica en outputs/."""
    fid = f"{int(time.time())}_{gen_id()}"
    stem = safe_filename(Path(stem).stem)
    return OUTPUT_DIR / f"{stem}_{fid}{ext.lower()}"


def cleanup_old_files(max_age_seconds: int = 3600) -> None:
    """Borra archivos mas viejos que max_age_seconds en uploads/ y outputs/."""
    cutoff = time.time() - max_age_seconds
    for d in (UPLOAD_DIR, OUTPUT_DIR):
        for p in d.iterdir():
            try:
                if p.is_file() and p.stat().st_mtime < cutoff:
                    p.unlink(missing_ok=True)
            except OSError:
                pass


def parse_page_ranges(spec: str, total: int) -> List[int]:
    """
    Parsea un string de rangos tipo '1-3,5,7-9' y devuelve una lista
    de indices 1-based unicos y ordenados, sin exceder `total`.
    Acepta 'all' o vacio para todas las paginas.
    """
    if not spec or spec.strip().lower() in {"all", "todas", "*", ""}:
        return list(range(1, total + 1))

    pages: List[int] = []
    seen: set[int] = set()
    parts = re.split(r"[,\s]+", spec.strip())
    for part in parts:
        if not part:
            continue
        if "-" in part:
            a_s, b_s = part.split("-", 1)
            try:
                a, b = int(a_s), int(b_s)
            except ValueError:
                raise ValueError(f"Rango invalido: {part!r}")
            if a > b:
                a, b = b, a
            for n in range(a, b + 1):
                if 1 <= n <= total and n not in seen:
                    seen.add(n)
                    pages.append(n)
        else:
            try:
                n = int(part)
            except ValueError:
                raise ValueError(f"Pagina invalida: {part!r}")
            if 1 <= n <= total and n not in seen:
                seen.add(n)
                pages.append(n)
    return pages


def parse_page_groups(spec: str, total: int) -> List[List[int]]:
    """
    Divide los rangos en grupos separados por ';' o '|'.
    Ej: '1-3;4-6;7' -> [[1,2,3],[4,5,6],[7]]
    Util para dividir PDF en multiples archivos.
    """
    if not spec or not spec.strip():
        return [list(range(1, total + 1))]
    groups: List[List[int]] = []
    parts = re.split(r"[;|]+", spec.strip())
    for p in parts:
        if p.strip():
            groups.append(parse_page_ranges(p, total))
    return groups


def is_pdf(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_PDF_EXT


def is_image(path: Path) -> bool:
    return path.suffix.lower() in ALLOWED_IMG_EXT


def ensure_pdf(path: Path) -> Path:
    """Verifica que el archivo exista y sea PDF."""
    if not path.exists():
        raise FileNotFoundError(f"No existe: {path}")
    if not is_pdf(path):
        raise ValueError(f"No es un PDF: {path.name}")
    if path.stat().st_size == 0:
        raise ValueError("PDF vacio o danado")
    return path


def ensure_within_dir(path: Path, base: Path) -> Path:
    """Previene path traversal: verifica que `path` este dentro de `base`."""
    base = base.resolve()
    p = path.resolve()
    try:
        p.relative_to(base)
    except ValueError:
        raise ValueError(f"Ruta fuera del directorio permitido: {p}")
    return p


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def download_response_headers(filename: str) -> dict:
    return {
        "Content-Disposition": f'attachment; filename="{safe_filename(filename)}"',
        "X-Content-Type-Options": "nosniff",
    }
