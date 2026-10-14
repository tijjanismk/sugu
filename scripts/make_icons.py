"""Icônes de l'application (ticket #14) : « S » de Figtree ExtraBold blanc sur indigo, point
sun en haut à droite (le soleil du marché). Les PNG sont versionnés ; relancer ce script après
un changement de charte :

    uv run python scripts/make_icons.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT = ROOT / "static/fonts/figtree-latin-wght-normal.woff2"
OUT = ROOT / "static/img/icons"

INDIGO = "#2b3c8e"  # design/tokens.css --indigo (clair)
SUN = "#e8a51f"  # --sun
WHITE = "#ffffff"  # --on-indigo


def draw(size: int, *, safe: float, radius: float = 0.0) -> Image.Image:
    """`safe` : part du côté occupée par la lettre (une icône « maskable » doit tenir dans le
    cercle central de 80 %). `radius` : coins arrondis, en part du côté (0 = carré plein)."""
    scale = 4  # dessin en grand puis réduction : bords lisses
    big = size * scale
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    canvas = ImageDraw.Draw(image)
    canvas.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * radius), fill=INDIGO)

    font = ImageFont.truetype(str(FONT), int(big * safe))
    font.set_variation_by_name("ExtraBold")
    left, top, right, bottom = canvas.textbbox((0, 0), "S", font=font)
    dot = big * safe * 0.16
    # La lettre et le point forment un groupe centré (le point dépasse à droite de la lettre).
    x = (big - (right - left + dot * 0.7)) / 2 - left
    y = (big - (bottom - top)) / 2 - top
    canvas.text((x, y), "S", font=font, fill=WHITE)

    cx, cy = x + right + dot * 0.2, y + top + dot * 0.6
    canvas.ellipse((cx - dot / 2, cy - dot / 2, cx + dot / 2, cy + dot / 2), fill=SUN)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for size in (192, 512):
        draw(size, safe=0.62, radius=0.22).save(OUT / f"icon-{size}.png", optimize=True)
    draw(512, safe=0.5).save(OUT / "maskable-512.png", optimize=True)
    draw(180, safe=0.58).convert("RGB").save(OUT / "apple-touch-icon.png", optimize=True)
    favicon = draw(64, safe=0.7, radius=0.22)
    favicon.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    for path in sorted(OUT.iterdir()):
        print(f"{path.relative_to(ROOT)} : {path.stat().st_size} octets")


if __name__ == "__main__":
    main()
