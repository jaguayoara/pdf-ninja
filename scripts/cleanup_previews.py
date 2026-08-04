"""Quita los PNGs de preview generados para debug."""
from pathlib import Path
BASE = Path('C:/Users/jagua/Desktop/Pdftool')
for name in ['logo_final_64.png', 'logo_final_256.png']:
    f = BASE / name
    if f.exists():
        f.unlink()
        print(f"  - borrado: {name}")
