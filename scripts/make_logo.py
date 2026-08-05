"""
Extrae el ninja del banner.png y genera static/logo.png con fondo
transparente para usar en la barra superior de la UI.

Entrada : static/banner.png   (2816x1536, fondo blanco)
Salida  : static/logo.png     (PNG con alpha, ninja aislado)
"""
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / 'static' / 'banner.png'
OUT = BASE / 'static' / 'logo.png'

# BBox del ninja en el banner (calculado experimentalmente):
#   x: 817-2000, y: 214-1017  -> ancho 1183, alto 803
# Sin padding -> mas tarde agregamos padding transparente para hacer
# el canvas cuadrado sin incluir el texto "PDF NINJA" de abajo.
CROP = (810, 200, 2005, 1020)
# Tamano final: 512x512 (calidad alta para HiDPI, liviano para web)
OUT_SIZE = 512


def remove_white_bg(img: Image.Image) -> Image.Image:
    """
    Convierte el fondo blanco (y casi blanco neutro) en transparente,
    preservando el anti-aliasing de los bordes del dibujo.

    Reglas:
      - Si el pixel es acromatico y mn >= 248  -> totalmente transparente
        (fondo / ruido claro).
      - Si el pixel es acromatico y 220 <= mn < 248 -> alpha proporcional
        (zona de borde con anti-aliasing, 220 = opaco, 248 = transparente).
      - Resto -> sin tocar (parte solida del dibujo, incluye pixeles con color).
    """
    rgba = img.convert('RGBA')
    pixels = rgba.load()
    w, h = rgba.size
    EDGE_LO = 220
    EDGE_HI = 248
    span = EDGE_HI - EDGE_LO
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            mn = min(r, g, b)
            mx = max(r, g, b)
            chroma = mx - mn
            if chroma > 8:
                continue  # pixel con tinte: parte del dibujo, no tocar
            if mn >= EDGE_HI:
                pixels[x, y] = (r, g, b, 0)
            elif mn >= EDGE_LO:
                new_alpha = int(round((EDGE_HI - mn) / span * 255))
                new_alpha = max(0, min(255, new_alpha))
                pixels[x, y] = (r, g, b, new_alpha)
    return rgba


def main():
    if not SRC.exists():
        raise SystemExit(f'No existe la imagen fuente: {SRC}')

    img = Image.open(SRC).convert('RGBA')
    print(f'Fuente: {img.size[0]}x{img.size[1]}')

    ninja = img.crop(CROP)
    print(f'Crop: {ninja.size[0]}x{ninja.size[1]}')

    ninja = remove_white_bg(ninja)

    # Convertir a canvas cuadrado agregando padding transparente
    w, h = ninja.size
    side = max(w, h)
    square = Image.new('RGBA', (side, side), (0, 0, 0, 0))
    off_x = (side - w) // 2
    off_y = (side - h) // 2
    square.paste(ninja, (off_x, off_y), ninja)

    # Resize al tamano final
    square = square.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)
    square.save(OUT, format='PNG', optimize=True)
    print(f'OK {OUT.name}  ({OUT.stat().st_size:,} bytes, {OUT_SIZE}x{OUT_SIZE})')


if __name__ == '__main__':
    main()
