#!/usr/bin/env python3
"""Travel poster for NARVELL, a place that does not exist.

This program paints one 1024x1024 PNG travel poster using pure Python
standard library only: a dusk lagoon under a low golden moon, distant
mountains, and the floating lantern markets of Narvell, with the place
name set in large hand-drawn letters. No network, no font files, no
external assets. The output is fully deterministic: the same bytes
come out on every run.
"""

import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- pixel buffer

BUF = bytearray(W * H * 3)


def put(x, y, rgb):
    """Set one pixel, silently ignoring out-of-bounds coordinates."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        BUF[i] = rgb[0]
        BUF[i + 1] = rgb[1]
        BUF[i + 2] = rgb[2]


def blend(x, y, rgb, alpha):
    """Paint rgb over one pixel with alpha 0..255."""
    if 0 <= x < W and 0 <= y < H and alpha > 0:
        i = (y * W + x) * 3
        if alpha >= 255:
            BUF[i] = rgb[0]
            BUF[i + 1] = rgb[1]
            BUF[i + 2] = rgb[2]
        else:
            inv = 255 - alpha
            BUF[i] = (rgb[0] * alpha + BUF[i] * inv) // 255
            BUF[i + 1] = (rgb[1] * alpha + BUF[i + 1] * inv) // 255
            BUF[i + 2] = (rgb[2] * alpha + BUF[i + 2] * inv) // 255


def fill_rect(x0, y0, x1, y1, rgb):
    """Fill an axis-aligned rectangle, clipped to the canvas."""
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(W - 1, int(x1))
    y1 = min(H - 1, int(y1))
    for y in range(y0, y1 + 1):
        base = (y * W + x0) * 3
        for x in range(x0, x1 + 1):
            i = base + (x - x0) * 3
            BUF[i] = rgb[0]
            BUF[i + 1] = rgb[1]
            BUF[i + 2] = rgb[2]


def blend_rect(x0, y0, x1, y1, rgb, alpha):
    """Fill a rectangle with a translucent colour."""
    x0 = max(0, int(x0))
    y0 = max(0, int(y0))
    x1 = min(W - 1, int(x1))
    y1 = min(H - 1, int(y1))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            blend(x, y, rgb, alpha)


def disc(cx, cy, r, rgb, alpha=255):
    """Fill a solid circle of radius r."""
    cx, cy, r = int(cx), int(cy), int(r)
    if r <= 0:
        return
    r2 = r * r
    for y in range(cy - r, cy + r + 1):
        dy = y - cy
        span = int((r2 - dy * dy) ** 0.5)
        for x in range(cx - span, cx + span + 1):
            blend(x, y, rgb, alpha)


def ring(cx, cy, r0, r1, rgb, alpha):
    """Fill a ring between radii r0 and r1."""
    cx, cy, r0, r1 = int(cx), int(cy), int(r0), int(r1)
    for y in range(cy - r1, cy + r1 + 1):
        dy = y - cy
        for x in range(cx - r1, cx + r1 + 1):
            d2 = (x - cx) * (x - cx) + dy * dy
            if r0 * r0 <= d2 <= r1 * r1:
                blend(x, y, rgb, alpha)


def fill_poly(points, rgb, alpha=255):
    """Fill a simple polygon with a scanline fill."""
    if len(points) < 3:
        return
    ys = [p[1] for p in points]
    y0, y1 = max(0, int(min(ys))), min(H - 1, int(max(ys)))
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x1, yy1 = points[i]
            x2, yy2 = points[(i + 1) % n]
            if yy1 == yy2:
                continue
            if (yy1 <= y < yy2) or (yy2 <= y < yy1):
                t = (y - yy1) / (yy2 - yy1)
                xs.append(x1 + t * (x2 - x1))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            xa = max(0, int(xs[k]))
            xb = min(W - 1, int(xs[k + 1]))
            for x in range(xa, xb + 1):
                blend(x, y, rgb, alpha)


def line(x0, y0, x1, y1, rgb, thick=1):
    """Draw a straight line by stamping small discs along it."""
    x0, y0, x1, y1, thick = int(x0), int(y0), int(x1), int(y1), int(thick)
    steps = max(abs(x1 - x0), abs(y1 - y0), 1)
    for s in range(steps + 1):
        t = s / steps
        x = int(x0 + (x1 - x0) * t)
        y = int(y0 + (y1 - y0) * t)
        disc(x, y, thick, rgb)


def lerp(a, b, t):
    return int(a + (b - a) * t)


def mix(c1, c2, t):
    return (lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t))


def vgrad(y0, y1, top, bottom):
    """Fill a vertical gradient band."""
    span = max(1, y1 - y0)
    for y in range(y0, y1 + 1):
        t = (y - y0) / span
        fill_rect(0, y, W - 1, y, mix(top, bottom, t))


def lcg(seed):
    """Tiny deterministic pseudo-random generator (fixed seed, no random)."""
    state = seed & 0x7FFFFFFF
    while True:
        state = (1103515245 * state + 12345) & 0x7FFFFFFF
        yield state


# ---------------------------------------------------------------- hand lettering

# A 5x7 bitmap alphabet, drawn cell by cell as solid blocks, so the poster
# needs no font file at all. Each glyph is seven rows of five bits.
GLYPHS = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "I": ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    "-": ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ".": ("00000", "00000", "00000", "00000", "00000", "00000", "01100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
}


def text_width(text, scale, gap):
    """Pixel width of a string at the given cell scale and letter gap."""
    if not text:
        return 0
    return len(text) * (5 * scale + gap) - gap


def draw_glyph(ch, x, y, scale, rgb):
    glyph = GLYPHS.get(ch, GLYPHS[" "])
    for row in range(7):
        bits = glyph[row]
        for col in range(5):
            if bits[col] == "1":
                fill_rect(x + col * scale, y + row * scale,
                          x + col * scale + scale - 1,
                          y + row * scale + scale - 1, rgb)


def draw_text(text, cx, y, scale, rgb, gap, shadow=None, shadow_dx=0, shadow_dy=0):
    """Draw a centred line of hand-built letters; optional offset shadow."""
    total = text_width(text, scale, gap)
    x = cx - total // 2
    if shadow is not None:
        xx = x
        for ch in text:
            draw_glyph(ch, xx + shadow_dx, y + shadow_dy, scale, shadow)
            xx += 5 * scale + gap
    xx = x
    for ch in text:
        draw_glyph(ch, xx, y, scale, rgb)
        xx += 5 * scale + gap
    return total

# ------------------------------------------------------------------- the scene

# Palette (all colours chosen for a warm dusk over a teal lagoon).
CREAM = (255, 244, 214)
GOLD = (255, 205, 120)
DEEP = (18, 16, 52)          # deep indigo shadow for the title
SKY_TOP = (22, 20, 58)
SKY_MID = (74, 44, 112)
SKY_LOW = (255, 166, 105)    # peach band at the horizon
MOON = (255, 232, 175)
MOON_GLOW = (255, 214, 140)
RIDGE_BACK = (52, 34, 92)
RIDGE_FRONT = (28, 20, 58)
SEA_TOP = (18, 96, 116)
SEA_BOT = (8, 38, 68)
WOOD = (96, 62, 38)
WOOD_DARK = (58, 36, 22)
LANTERN_CORE = (255, 190, 80)
LANTERN_HALO = (255, 150, 60)


def paint_sky():
    """Dusk sky: indigo overhead melting to violet, then peach at the sea."""
    vgrad(0, 300, SKY_TOP, SKY_MID)
    vgrad(300, 560, SKY_MID, SKY_LOW)


def paint_stars():
    """A sparse field of small stars, fixed by a seeded generator."""
    gen = lcg(20261121)
    for _ in range(110):
        x = 40 + next(gen) % 944
        y = 40 + next(gen) % 330
        r = 1 + next(gen) % 2
        bright = 150 + next(gen) % 105
        disc(x, y, r, (bright, bright, min(255, bright + 20)),
             120 + next(gen) % 135)


def paint_birds():
    """Three distant birds crossing the evening sky."""
    for bx, by, s in ((300, 330, 9), (350, 305, 7), (620, 360, 8)):
        line(bx - s, by, bx, by + s // 2, (30, 24, 60), 2)
        line(bx, by + s // 2, bx + s, by, (30, 24, 60), 2)


def paint_moon(cx, cy, r):
    """A low golden moon with a soft halo and two faint shadow seas."""
    disc(cx, cy, r + 46, MOON_GLOW, 22)
    disc(cx, cy, r + 26, MOON_GLOW, 40)
    disc(cx, cy, r + 12, MOON_GLOW, 70)
    disc(cx, cy, r, MOON)
    disc(cx - r // 3, cy - r // 4, r // 5, (238, 205, 140))
    disc(cx + r // 4, cy + r // 3, r // 7, (238, 205, 140))
    disc(cx + r // 8, cy - r // 2, r // 9, (244, 214, 150))


def paint_mountains():
    """Two ridges of sleeping hills between sky and lagoon."""
    fill_poly([(0, 560), (0, 470), (90, 430), (180, 478), (290, 420),
               (410, 482), (520, 438), (640, 486), (760, 428), (880, 480),
               (960, 446), (1024, 480), (1024, 560)], RIDGE_BACK)
    fill_poly([(0, 560), (0, 520), (120, 486), (250, 528), (380, 492),
               (520, 534), (660, 496), (800, 536), (920, 500),
               (1024, 532), (1024, 560)], RIDGE_FRONT)


def paint_sea():
    """The lagoon: teal at the horizon, deep navy toward the viewer."""
    vgrad(560, 880, SEA_TOP, SEA_BOT)


def moon_path(cx):
    """A shimmering column of moonlight on the water."""
    gen = lcg(777)
    for y in range(566, 876, 7):
        wob = 26 + (next(gen) % 60)
        a = 26 + next(gen) % 60
        blend_rect(cx - wob, y, cx + wob, y + 3, MOON_GLOW, a)


def paint_sparkles():
    """Scattered glints where the last light catches the lagoon."""
    gen = lcg(4242)
    for _ in range(70):
        x = 40 + next(gen) % 944
        y = 570 + next(gen) % 300
        a = 30 + next(gen) % 70
        blend_rect(x, y, x + 8 + next(gen) % 22, y + 1, (255, 220, 160), a)


def lantern(x, y, r, glow=90):
    """One glowing paper lantern: halo, warm core, dark cap and tassel."""
    disc(x, y, r + 14, LANTERN_HALO, 30)
    disc(x, y, r + 7, LANTERN_HALO, glow)
    disc(x, y, r, LANTERN_CORE)
    disc(x, y - r // 3, r // 2, (255, 226, 150))
    fill_rect(x - r // 2, y - r - 3, x + r // 2, y - r + 1, (40, 20, 12))
    fill_rect(x - 1, y + r, x + 1, y + r + 6, (40, 20, 12))


def floating_lantern(x, y, r):
    """A lantern set adrift on the lagoon, with its reflection."""
    lantern(x, y, r)
    blend_rect(x - r // 2, y + r + 8, x + r // 2, y + r + 26,
               LANTERN_HALO, 60)


def paint_boat(cx, base_y, s, hull, canopy, lanterns):
    """One market boat: hull, striped awning, stall goods and lanterns.

    s scales the boat; lanterns is a list of (dx, dy, radius) offsets
    from the boat's centre line, hung from the awning poles.
    """
    # Hull: a broad trapezoid with a lifted prow and stern.
    fill_poly([(cx - 78 * s, base_y), (cx + 78 * s, base_y),
               (cx + 58 * s, base_y + 24 * s), (cx - 58 * s, base_y + 24 * s)],
              hull)
    fill_rect(cx - 78 * s, base_y, cx + 78 * s, base_y + 5 * s, WOOD_DARK)
    # Awning poles.
    line(cx - 52 * s, base_y - 62 * s, cx - 52 * s, base_y, WOOD_DARK, 3)
    line(cx + 52 * s, base_y - 62 * s, cx + 52 * s, base_y, WOOD_DARK, 3)
    # Striped awning: a peaked tent roof.
    fill_poly([(cx - 64 * s, base_y - 58 * s), (cx, base_y - 92 * s),
               (cx + 64 * s, base_y - 58 * s)], canopy)
    fill_rect(cx - 64 * s, base_y - 62 * s, cx + 64 * s, base_y - 56 * s,
              WOOD_DARK)
    for k in range(-2, 3):
        x0 = cx + k * 26 * s
        fill_poly([(x0 - 6 * s, base_y - 60 * s), (x0, base_y - 88 * s),
                   (x0 + 6 * s, base_y - 60 * s)], CREAM)
    # Stall goods: baskets of fruit and folded cloth on the deck.
    for gx, gc in ((-34, (255, 120, 60)), (-12, (255, 205, 90)),
                   (10, (120, 200, 140)), (32, (230, 90, 120))):
        fill_rect(cx + gx * s, base_y - 16 * s, cx + (gx + 16) * s,
                  base_y - 2 * s, gc)
        fill_rect(cx + gx * s, base_y - 18 * s, cx + (gx + 16) * s,
                  base_y - 16 * s, WOOD_DARK)
    # Hanging lanterns, each with its own reflection on the water.
    for dx, dy, lr in lanterns:
        lx, ly = cx + dx * s, base_y + dy * s
        line(lx, ly - 14 * s, lx, ly - 4 * s, WOOD_DARK, 2)
        lantern(lx, ly, lr)
        blend_rect(lx - lr // 2, base_y + 26 * s, lx + lr // 2,
                   base_y + 44 * s, LANTERN_HALO, 55)


def paint_pier():
    """A wooden pier across the foreground, with two lantern posts."""
    vgrad(880, 1024, (112, 74, 46), (70, 44, 26))
    for y in range(880, 1024, 26):
        fill_rect(0, y, W - 1, y + 2, WOOD_DARK)
    for row, off in enumerate(range(880, 1024, 26)):
        for x in range(off % 2 * 90, W, 180):
            fill_rect(x, row * 26 + 880, x + 2, row * 26 + 904, WOOD_DARK)
    # Lantern posts at either end of the pier.
    for px in (120, 904):
        fill_rect(px - 7, 806, px + 7, 884, WOOD_DARK)
        fill_rect(px - 26, 800, px + 26, 808, WOOD_DARK)
        line(px, 808, px, 826, WOOD_DARK, 2)
        lantern(px, 842, 15)


def paint_frame():
    """The poster's cream border and thin gold inner rule."""
    fill_rect(0, 0, W - 1, 25, CREAM)
    fill_rect(0, H - 26, W - 1, H - 1, CREAM)
    fill_rect(0, 0, 25, H - 1, CREAM)
    fill_rect(W - 26, 0, W - 1, H - 1, CREAM)
    fill_rect(30, 30, W - 31, 33, GOLD)
    fill_rect(30, H - 34, W - 31, H - 31, GOLD)
    fill_rect(30, 30, 33, H - 31, GOLD)
    fill_rect(W - 34, 30, W - 31, H - 31, GOLD)

# ------------------------------------------------------------------- PNG output

def png_bytes():
    """Encode the buffer as a PNG: 8-bit RGB, filter 0, zlib level 9."""
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += BUF[y * W * 3:(y + 1) * W * 3]
    compressed = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", compressed) + chunk(b"IEND", b""))


# ------------------------------------------------------------------- the poster

def paint_poster():
    """Compose the whole poster, back to front."""
    paint_sky()
    paint_stars()
    paint_birds()
    paint_moon(815, 350, 80)
    paint_mountains()
    paint_sea()
    moon_path(815)
    paint_sparkles()
    # Far market boat, small against the hills.
    paint_boat(230, 610, 0.55, (44, 88, 96), GOLD,
               [(-46, -34, 6), (0, -40, 7), (46, -34, 6)])
    # The main boat, centre of the lagoon, lanterns lit.
    paint_boat(470, 690, 1.0, (150, 62, 40), (235, 92, 70),
               [(-56, -30, 10), (0, -38, 12), (56, -30, 10)])
    # A second boat nearer the pier, teal awning.
    paint_boat(790, 760, 0.8, (32, 82, 92), (40, 160, 150),
               [(-50, -32, 8), (50, -32, 8)])
    # Lanterns adrift between the boats.
    floating_lantern(330, 830, 7)
    floating_lantern(620, 850, 6)
    floating_lantern(880, 820, 7)
    floating_lantern(180, 862, 6)
    paint_pier()
    paint_frame()
    # The place name, set large across the sky, and its promise below it.
    # Bigger, more legible lettering: scale 22 with a wider gap and a
    # deeper drop shadow so NARVELL reads clearly at a glance.
    draw_text("NARVELL", W // 2, 56, 22, CREAM, 20,
              shadow=DEEP, shadow_dx=6, shadow_dy=6)
    draw_text("THE FLOATING LANTERN MARKETS", W // 2, 228, 5, GOLD, 5,
              shadow=DEEP, shadow_dx=2, shadow_dy=2)


def main():
    paint_poster()
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(png_bytes())
    print("wrote", path)


if __name__ == "__main__":
    main()
