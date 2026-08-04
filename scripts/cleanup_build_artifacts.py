"""Limpia artefactos de debug y de builds anteriores."""
import os
import shutil
from pathlib import Path

BASE = Path('C:/Users/jagua/Desktop/Pdftool')

# 1) Quitar logo_preview.png (era solo para debug)
preview = BASE / 'logo_preview.png'
if preview.exists():
    preview.unlink()
    print(f"  - borrado: {preview.name}")

# 2) Quitar dist/Papiro (build anterior, ya no se usa)
old_dist = BASE / 'dist' / 'Papiro'
if old_dist.exists():
    shutil.rmtree(old_dist)
    print(f"  - borrado: dist/Papiro/")

# 3) build/ y dist/ ya se regeneraron arriba
print()
print("Limpieza OK")
