#!/usr/bin/env python3
"""Generate the favicon set for nero.freylab.systems.

The VM has no Pillow, no ImageMagick and no librsvg, so this does the whole
job with the standard library: shapes are defined analytically, rasterised
with 4x4 supersampling for antialiasing, and written out as PNG (zlib +
struct) and ICO (PNG-embedded, which every browser since IE11 understands).

The mark is a shell prompt: a chevron and a lit block cursor.

Usage, from the repository root:

    python3 tools/make_favicon.py

Writes favicon.svg, favicon.ico and apple-touch-icon.png.
"""

import math
import os
import struct
import zlib

# Design grid. Every coordinate below is in 32x32 space and scaled per output.
GRID = 32.0
CORNER = 6.5

BG = (0x0A, 0x0C, 0x10)       # page background
CHEVRON = (0x3B, 0x82, 0xF6)  # Nero blue
CURSOR = (0x93, 0xC5, 0xFD)   # lit cursor, one step brighter

CHEVRON_POINTS = ((9.4, 9.4), (15.2, 16.0), (9.4, 22.6))
CHEVRON_HALF_WIDTH = 1.9
CURSOR_BOX = (19.8, 9.4, 24.0, 22.6)
CURSOR_RADIUS = 1.2

SUPERSAMPLE = 4


def rounded_rect_sdf(px, py, x0, y0, x1, y1, r):
    """Signed distance to a rounded rectangle. Negative means inside."""
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    hw, hh = (x1 - x0) / 2.0 - r, (y1 - y0) / 2.0 - r
    dx, dy = abs(px - cx) - hw, abs(py - cy) - hh
    outside = math.hypot(max(dx, 0.0), max(dy, 0.0))
    inside = min(max(dx, dy), 0.0)
    return outside + inside - r


def segment_distance(px, py, ax, ay, bx, by):
    """Distance from a point to a line segment."""
    vx, vy = bx - ax, by - ay
    length_sq = vx * vx + vy * vy
    if length_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / length_sq))
    return math.hypot(px - (ax + vx * t), py - (ay + vy * t))


def sample(gx, gy, rounded):
    """Topmost shape colour at a point in design space, or None if empty."""
    for i in range(len(CHEVRON_POINTS) - 1):
        (ax, ay), (bx, by) = CHEVRON_POINTS[i], CHEVRON_POINTS[i + 1]
        if segment_distance(gx, gy, ax, ay, bx, by) <= CHEVRON_HALF_WIDTH:
            return CHEVRON
    if rounded_rect_sdf(gx, gy, *CURSOR_BOX, r=CURSOR_RADIUS) <= 0.0:
        return CURSOR
    if not rounded or rounded_rect_sdf(gx, gy, 0, 0, GRID, GRID, r=CORNER) <= 0.0:
        return BG
    return None


def render(size, rounded=True):
    """Rasterise to a list of rows of straight-alpha RGBA tuples."""
    scale = GRID / size
    step = 1.0 / SUPERSAMPLE
    samples = SUPERSAMPLE * SUPERSAMPLE
    rows = []
    for y in range(size):
        row = []
        for x in range(size):
            r = g = b = 0.0
            covered = 0
            for sy in range(SUPERSAMPLE):
                for sx in range(SUPERSAMPLE):
                    colour = sample(
                        (x + (sx + 0.5) * step) * scale,
                        (y + (sy + 0.5) * step) * scale,
                        rounded,
                    )
                    if colour is not None:
                        r += colour[0]
                        g += colour[1]
                        b += colour[2]
                        covered += 1
            if covered == 0:
                row.append((0, 0, 0, 0))
            else:
                row.append((
                    int(round(r / covered)),
                    int(round(g / covered)),
                    int(round(b / covered)),
                    int(round(255.0 * covered / samples)),
                ))
        rows.append(row)
    return rows


def encode_png(size, rows):
    raw = b"".join(
        b"\x00" + bytes(channel for pixel in row for channel in pixel) for row in rows
    )

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def encode_ico(images):
    """Pack (size, png_bytes) pairs into a PNG-embedded .ico."""
    header = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    directory, payload = b"", b""
    for size, blob in images:
        dimension = 0 if size >= 256 else size
        directory += struct.pack(
            "<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(blob), offset
        )
        offset += len(blob)
        payload += blob
    return header + directory + payload


SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" width="32" height="32" role="img" aria-label="Nero ops journal">
  <rect width="32" height="32" rx="{corner}" fill="{bg}"/>
  <path d="M{ax} {ay} L{mx} {my} L{bx} {by}" fill="none" stroke="{chevron}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="{cx0}" y="{cy0}" width="{cw}" height="{ch}" rx="{cr}" fill="{cursor}"/>
</svg>
"""


def hexof(rgb):
    return "#%02x%02x%02x" % rgb


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    (ax, ay), (mx, my), (bx, by) = CHEVRON_POINTS
    cx0, cy0, cx1, cy1 = CURSOR_BOX
    svg = SVG.format(
        corner=CORNER, bg=hexof(BG), chevron=hexof(CHEVRON), cursor=hexof(CURSOR),
        ax=ax, ay=ay, mx=mx, my=my, bx=bx, by=by,
        stroke=CHEVRON_HALF_WIDTH * 2, cx0=cx0, cy0=cy0,
        cw=round(cx1 - cx0, 2), ch=round(cy1 - cy0, 2), cr=CURSOR_RADIUS,
    )
    with open(os.path.join(root, "favicon.svg"), "w") as handle:
        handle.write(svg)

    ico = encode_ico([(s, encode_png(s, render(s))) for s in (16, 32, 48)])
    with open(os.path.join(root, "favicon.ico"), "wb") as handle:
        handle.write(ico)

    # iOS masks the corners itself, so the touch icon is full bleed.
    touch = encode_png(180, render(180, rounded=False))
    with open(os.path.join(root, "apple-touch-icon.png"), "wb") as handle:
        handle.write(touch)

    print("favicon.svg      %5d bytes" % len(svg))
    print("favicon.ico      %5d bytes (16, 32, 48)" % len(ico))
    print("apple-touch-icon %5d bytes (180)" % len(touch))


if __name__ == "__main__":
    main()
