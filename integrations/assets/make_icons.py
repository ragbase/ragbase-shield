"""Draw the RAGbase Shield icons as PNG files, with the Python standard library only.

Run from the repo root:  python integrations/assets/make_icons.py

The drawing is a navy rounded square with a white shield (left half tinted). It is our own
simple artwork, no third-party image. Outputs:

- integrations/assets/icon-512.png                (master copy)
- integrations/claude-desktop/icon.png             (512 x 512, MCPB bundle icon)
- integrations/openai-plugin/assets/icon.png       (512 x 512)
- integrations/claude-code/plugin/.claude-plugin/icon.png   (512 x 512, Claude plugin directory listing icon)
- integrations/browser-extension/icons/icon{16,32,48,128}.png
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path

NAVY = (23, 50, 77, 255)
WHITE = (255, 255, 255, 255)
TINT = (199, 222, 244, 255)
CLEAR = (0, 0, 0, 0)
SAMPLES = 4  # supersampling per axis, for smooth edges


def _bezier(p0, p1, p2, steps=24):
    out = []
    for i in range(steps + 1):
        t = i / steps
        x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0]
        y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
        out.append((x, y))
    return out


def _shield_polygon():
    """Shield outline in unit coordinates (0..1, y down)."""
    right = [(0.5, 0.17), (0.75, 0.23), (0.75, 0.50)] + _bezier((0.75, 0.50), (0.745, 0.73), (0.5, 0.85))[1:]
    left = [(1 - x, y) for (x, y) in reversed(right[1:-1])]
    return right + left


SHIELD = _shield_polygon()


def _inside(poly, x, y):
    hit = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            hit = not hit
        j = i
    return hit


def _in_tile(x, y, margin=0.03, radius=0.2):
    lo, hi = margin, 1 - margin
    if not (lo <= x <= hi and lo <= y <= hi):
        return False
    cx = min(max(x, lo + radius), hi - radius)
    cy = min(max(y, lo + radius), hi - radius)
    return (x - cx) ** 2 + (y - cy) ** 2 <= radius ** 2


def _color_at(x, y):
    if _inside(SHIELD, x, y):
        return TINT if x < 0.5 else WHITE
    if _in_tile(x, y):
        return NAVY
    return CLEAR


def render(size: int) -> bytes:
    """Return a size x size RGBA PNG."""
    rows = []
    n = SAMPLES * SAMPLES
    for py in range(size):
        row = bytearray([0])  # filter type 0
        for px in range(size):
            acc = [0, 0, 0, 0]
            for sy in range(SAMPLES):
                for sx in range(SAMPLES):
                    c = _color_at((px + (sx + 0.5) / SAMPLES) / size, (py + (sy + 0.5) / SAMPLES) / size)
                    a = c[3]
                    acc[0] += c[0] * a
                    acc[1] += c[1] * a
                    acc[2] += c[2] * a
                    acc[3] += a
            alpha = acc[3] / n
            if acc[3]:
                rgb = [round(acc[k] / acc[3]) for k in range(3)]
            else:
                rgb = [0, 0, 0]
            row += bytes(rgb + [round(alpha)])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # integrations/
    big = render(512)
    targets = [
        root / "assets" / "icon-512.png",
        root / "claude-desktop" / "icon.png",
        root / "openai-plugin" / "assets" / "icon.png",
        root / "claude-code" / "plugin" / ".claude-plugin" / "icon.png",
    ]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        t.write_bytes(big)
    for s in (16, 32, 48, 128):
        out = root / "browser-extension" / "icons" / f"icon{s}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(render(s))


if __name__ == "__main__":
    main()
