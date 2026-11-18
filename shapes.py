"""Flower shapes.

Each shape takes local coords (x right, y up, size ~1) and returns
brightness 0..1 (0 = not part of the shape).
"""
import math
from functools import lru_cache


def lily_center(x, y):
    """Lily center + 6 anther dots. Drawn on top of `lily` in its own color."""
    if math.hypot(x, y) < 0.12:
        return 1.0
    for i in range(6):  # anther dots between petals
        a = math.pi / 6 + i * math.pi / 3
        if math.hypot(x - 0.5 * math.cos(a), y - 0.5 * math.sin(a)) < 0.07:
            return 1.0
    return 0


def lily(x, y):
    """Front view: 6 pointed petals in a star."""
    if math.hypot(x, y) > 1:
        return 0
    k = round(math.atan2(y, x) / (math.pi / 3))  # nearest petal
    phi = k * math.pi / 3
    along = x * math.cos(phi) + y * math.sin(phi)
    side = -x * math.sin(phi) + y * math.cos(phi)
    t = along / (1.0 if k % 2 == 0 else 0.85)  # alternate long/short petals
    if not 0 < t < 1:
        return 0
    half = 0.32 * math.sin(math.pi * t) ** 0.7  # pointed at both ends
    if abs(side) >= half:
        return 0
    if t < 0.55 and _speckle(x, y):
        return 0.15  # dark dot near the throat, like real lilies
    return 0.35 + 0.6 * (1 - abs(side) / half) * (1 - 0.4 * t)  # bright midrib


def _speckle(x, y):
    """Fixed pseudo-random dots on a small grid in the flower's own coords."""
    ix, iy = int((x + 2) * 9), int((y + 2) * 9)
    return ((ix * 73856093) ^ (iy * 19349663)) % 7 == 0


def bud(x, y):
    """Closed flower bud: teardrop pointing up (base y=-0.5, tip y=0.6)."""
    t = (y + 0.5) / 1.1
    if not 0 < t < 1:
        return 0
    half = 0.24 * math.sin(math.pi * t) ** 0.6 * (1.15 - 0.6 * t)
    if abs(x) >= half:
        return 0
    return 0.35 + 0.55 * (1 - abs(x) / half)


def tulip(x, y):
    """Side view: rounded cup with 3 pointed tips on top."""
    y += 0.55  # origin at the middle of the cup
    e = (x / 0.5) ** 2 + ((y - 0.55) / 0.6) ** 2
    if e >= 1:
        return 0
    fold = math.cos(2 * math.pi * x / 0.33)  # +1 at petal middles, -1 at folds
    if y > 0.9 + 0.2 * fold:  # notched top edge
        return 0
    return 0.3 + 0.2 * (1 + fold) + 0.25 * (1 - e)


def leaf(x, y):
    """Long, narrow leaf curving right, with a midrib."""
    y += 0.5  # origin at the middle of the leaf
    if not 0 < y < 1:
        return 0
    d = abs(x - 0.3 * y * y)  # distance to the curved center line
    half = 0.1 * math.sin(math.pi * y) ** 0.8
    if d >= half:
        return 0
    if d < 0.2 * half:
        return 0.25  # midrib
    return 0.9 - 0.4 * d / half


def leaf_left(x, y):
    """Leaf curving left (mirror)."""
    return leaf(-x, y)


def stem(x, y, width, grow=1.0):
    """Vertical segment from y=-1 up to y=1, `width` = half thickness.
    `grow` 0..1 = how much of it is visible, from the bottom."""
    if not (-1 < y < 2 * grow - 1 and abs(x) < width):
        return 0
    return 0.75 - 0.45 * abs(x) / width  # round look: bright middle, dark edges


def bow(x, y):
    """Ribbon bow: knot, two loops (with holes) and two hanging tails."""
    if (x / 0.18) ** 2 + (y / 0.16) ** 2 < 1:
        return 0.95  # knot
    lx = abs(x)  # both sides are mirrors
    ex, ey = lx - 0.42, y - 0.1
    if (ex / 0.38) ** 2 + (ey / 0.24) ** 2 < 1:  # loop
        if (ex / 0.2) ** 2 + (ey / 0.1) ** 2 < 1:
            return 0  # hole: stems show through
        return 0.75 - 0.3 * abs(ex) / 0.38
    if -0.9 < y < -0.1 and abs(lx - (0.12 - 0.35 * y)) < 0.07:
        return 0.6  # tail, going down and outward
    return 0


def heart(x, y, width, draw=1.0):
    """Heart outline (tip at y=-0.71, lobes up to y=0.89). `width` = half thickness.
    `draw` 0..1 traces it from the top notch down both sides to the tip."""
    if abs(math.atan2(x, y)) > math.pi * draw:
        return 0
    X, Y = x * 1.4, y * 1.4  # classic curve (x²+y²-1)³ = x²y³, shrunk to fit radius ~1
    q = X * X + Y * Y - 1
    f = q ** 3 - X * X * Y ** 3
    gx = 6 * X * q * q - 2 * X * Y ** 3
    gy = 6 * Y * q * q - 3 * X * X * Y * Y
    g = math.hypot(gx, gy)
    if g == 0:
        return 0
    d = abs(f) / g / 1.4  # approx distance to the curve
    return 0.9 - 0.4 * d / width if d < width else 0


def heart_fill(x, y):
    """Solid heart, same outline as `heart` (tip y=-0.71, lobes y=0.89).
    Brighter in the middle, darker toward the edge."""
    X, Y = x * 1.4, y * 1.4
    f = (X * X + Y * Y - 1) ** 3 - X * X * Y ** 3
    if f > 0:
        return 0
    return 0.95 - 0.5 * min(1.0, math.hypot(x, y - 0.1) / 0.85)


# --- Big text: letters drawn with characters --------------------------------

BIG_FONT = "/System/Library/Fonts/Menlo.ttc"


@lru_cache(maxsize=8)
def text_bitmap(text, rows, aspect=2.0):
    """Rasterizes `text` so its letters are about `rows` cells tall.
    Returns a tuple of rows, each a tuple of coverage values 0..1 (one per cell).
    Uses Pillow, imported here so it's only needed for big text."""
    from PIL import Image, ImageDraw, ImageFont
    px = 16  # pixels per cell row while drawing
    try:
        font = ImageFont.truetype(BIG_FONT, round(px * rows * 1.35), index=1)  # bold
    except OSError:
        font = ImageFont.load_default(round(px * rows * 1.35))
    left, top, right, bottom = font.getbbox(text)
    img = Image.new("L", (right - left + 4, bottom - top + 4), 0)
    ImageDraw.Draw(img).text((2 - left, 2 - top), text, fill=255, font=font)
    cols, n = max(1, round(img.width / (px / aspect))), max(1, round(img.height / px))
    small = img.resize((cols, n), Image.BOX)  # average the pixels inside each cell
    return tuple(tuple(small.getpixel((x, y)) / 255 for x in range(cols)) for y in range(n))


def big_text(x, y, bitmap, half_w, half_h, reveal=1.0):
    """Shape for a text_bitmap. half_w/half_h: its half size in local units.
    `reveal` 0..1 shows it from left to right (typing effect)."""
    if not (-half_w <= x < half_w and -half_h < y <= half_h):
        return 0
    n, cols = len(bitmap), len(bitmap[0])
    c = int((x + half_w) / (2 * half_w) * cols)
    r = int((half_h - y) / (2 * half_h) * n)
    if c >= cols * reveal or r >= n:
        return 0
    v = bitmap[r][c]
    return 0.3 + 0.65 * v if v > 0.2 else 0.01  # 0.01 draws a blank: clears what's behind
