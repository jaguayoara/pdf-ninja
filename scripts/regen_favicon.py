"""
Regenera el branding grafico de Pdf Ninja usando la imagen de
Gemini (ninja con shuriken y PDFs).

Genera:
  - static/banner.png        : imagen completa (2816x1536) para README
  - static/og-image.png      : igual al banner, para Open Graph
  - static/favicon.png       : crop cuadrado del ninja, 256x256
  - static/favicon.ico       : 7 tamanos (16/24/32/48/64/128/256) del crop
"""
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / 'dist' / 'PdfNinja' / 'Img' / 'Gemini_Generated_Image_xbis6mxbis6mxbis.png'

BANNER = BASE / 'static' / 'banner.png'
OG_IMAGE = BASE / 'static' / 'og-image.png'
FAVICON_PNG = BASE / 'static' / 'favicon.png'
FAVICON_ICO = BASE / 'static' / 'favicon.ico'


def main():
    if not SRC.exists():
        raise SystemExit(f'No existe la imagen fuente: {SRC}')

    img = Image.open(SRC).convert('RGBA')
    w, h = img.size
    print(f'Fuente: {w}x{h}')

    # 1. Banner y og-image: la imagen completa
    BANNER.parent.mkdir(parents=True, exist_ok=True)
    img.save(BANNER)
    img.save(OG_IMAGE)
    print(f'OK banner.png  ({BANNER.stat().st_size:,} bytes)')
    print(f'OK og-image.png ({OG_IMAGE.stat().st_size:,} bytes)')

    # 2. Crop cuadrado del ninja (sin el texto "PDF NINJA" de abajo)
    # El ninja esta aprox entre x=350-1850, y=60-960
    # Cuadrado 1000x1000: x=350, y=60, x+w=1350, y+h=1060
    crop_box = (350, 60, 1350, 1060)
    ninja = img.crop(crop_box)
    # Resize a 256x256 para favicon
    ninja_256 = ninja.resize((256, 256), Image.LANCZOS)
    ninja_256.save(FAVICON_PNG)
    print(f'OK favicon.png ({FAVICON_PNG.stat().st_size:,} bytes, 256x256)')

    # 3. favicon.ico con multiples tamanos
    sizes = [16, 24, 32, 48, 64, 128, 256]
    icons = [ninja.resize((s, s), Image.LANCZOS) for s in sizes]
    icons[-1].save(
        FAVICON_ICO,
        format='ICO',
        sizes=[(s, s) for s in sizes],
        append_images=icons[:-1],
    )
    print(f'OK favicon.ico ({FAVICON_ICO.stat().st_size:,} bytes, {len(sizes)} tamanos)')

    print('\nBranding regenerado con exito.')


if __name__ == '__main__':
    main()
