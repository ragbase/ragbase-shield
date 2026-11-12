"""Tray and app icons from integrations/assets/icon-512.png (our own artwork). Build time only.

Usage (repo .venv, Pillow is a dev dependency of the build only):
  .venv/bin/python packaging/common/make_tray_icons.py [<out_dir>]      default out_dir: build/icons

Outputs:
  shield_template.png   44 x 44 macOS menu bar template (black shield on transparency; macOS tints it)
  shield.ico            Windows tray and Start menu icon (16 to 256 px)
  shield.icns           macOS bundle icon (made with iconutil when it exists)
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "integrations" / "assets" / "icon-512.png"


def template(src: Image.Image, size: int = 44) -> Image.Image:
    """The white shield of the master icon as a black silhouette (alpha = brightness inside the square)."""
    rgba = src.convert("RGBA")
    w, h = rgba.size
    mask = Image.new("L", (w, h), 0)
    px, mpx = rgba.load(), mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a and min(r, g, b) > 140:  # white and tinted halves of the shield
                mpx[x, y] = a
    box = mask.getbbox() or (0, 0, w, h)
    mask = mask.crop(box)
    side = max(mask.size)
    square = Image.new("L", (side, side), 0)
    square.paste(mask, ((side - mask.size[0]) // 2, (side - mask.size[1]) // 2))
    inner = int(size * 0.86)
    square = square.resize((inner, inner), Image.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    black = Image.new("RGBA", (inner, inner), (0, 0, 0, 255))
    out.paste(black, ((size - inner) // 2, (size - inner) // 2), square)
    return out


def main(argv: list[str]) -> int:
    out = Path(argv[0]) if argv else ROOT / "build" / "icons"
    out.mkdir(parents=True, exist_ok=True)
    src = Image.open(SRC)
    template(src).save(out / "shield_template.png", optimize=True)
    src.convert("RGBA").save(out / "shield.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                           (128, 128), (256, 256)])
    shutil.copy2(SRC, out / "shield-512.png")
    if shutil.which("iconutil"):
        with tempfile.TemporaryDirectory() as td:
            iconset = Path(td) / "shield.iconset"
            iconset.mkdir()
            for px in (16, 32, 128, 256):
                src.resize((px, px), Image.LANCZOS).save(iconset / f"icon_{px}x{px}.png")
                src.resize((px * 2, px * 2), Image.LANCZOS).save(iconset / f"icon_{px}x{px}@2x.png")
            src.save(iconset / "icon_512x512.png")
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out / "shield.icns")], check=True)
    print(f"icons: {', '.join(sorted(p.name for p in out.iterdir()))}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
