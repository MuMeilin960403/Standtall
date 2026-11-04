"""Generate the Windows icon files used for packaging.

This script is a build-time helper only; the running app paints its own QIcon.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"

SAGE = (93, 137, 113, 255)
SAGE_DARK = (66, 106, 84, 255)
CREAM = (255, 251, 243, 255)
PEACH = (233, 145, 110, 255)


def make_icon() -> Image.Image:
    scale = 4
    size = 1024 * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(image)
    pad = int(32 * scale)
    tile = (pad, pad, size - pad, size - pad)
    d.rounded_rectangle(tile, radius=int(250 * scale), fill=SAGE)
    inner = (pad + int(10 * scale), pad + int(10 * scale), size - pad - int(10 * scale), size - pad - int(10 * scale))
    d.rounded_rectangle(inner, radius=int(240 * scale), outline=(255, 255, 255, 24), width=int(5 * scale))

    s = scale
    cx = size // 2
    # Head.
    d.ellipse((cx - 72 * s, 222 * s, cx + 72 * s, 366 * s), fill=CREAM)
    # Torso / upright spine.
    d.rounded_rectangle((cx - 34 * s, 378 * s, cx + 34 * s, 580 * s), radius=34 * s, fill=CREAM)
    # Shoulders.
    d.rounded_rectangle((414 * s, 445 * s, 610 * s, 505 * s), radius=30 * s, fill=CREAM)
    # Seated thigh.
    d.line((cx + 18 * s, 570 * s, cx + 180 * s, 646 * s), fill=CREAM, width=68 * s)
    # Lower leg.
    d.line((cx + 180 * s, 646 * s, cx + 180 * s, 800 * s), fill=CREAM, width=68 * s)

    # Accent dot.
    d.ellipse((704 * s, 176 * s, 812 * s, 284 * s), fill=PEACH)

    image = image.resize((1024, 1024), Image.Resampling.LANCZOS)
    return image


def main() -> None:
    ASSETS.mkdir(exist_ok=True)
    icon = make_icon()
    icon.save(ASSETS / "standtall.png")
    icon.save(
        ASSETS / "standtall.ico",
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Wrote {ASSETS / 'standtall.png'} and {ASSETS / 'standtall.ico'}")


if __name__ == "__main__":
    main()
