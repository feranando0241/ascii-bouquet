"""Scenes: functions (t, w, h) -> list of (shape, cx, cy, scale, angle, rgb).
Coords are in row units, y up, origin at the vertical middle of the screen."""

# ============================================================
#  PERSONALIZE
#  The heart is written with this name. Change it to any text
#  you like, e.g. "Maria" or "love you ". Use "" for a plain heart.
NAME = "with love "

#  Written under the bow, at the base of the bouquet. "" = hide it.
PHRASE = "for you ❤"
#  Size of the phrase: 1 = normal text; 5, 6, 7... = big letters that many rows
#  tall (below 5 the letters are hard to read). Move it with PHRASE_Y if needed.
PHRASE_SIZE = 10

# ============================================================

import math
from functools import partial

from render import ASPECT
from shapes import big_text, bow, bud, heart, heart_fill, leaf, leaf_left, lily, lily_center, stem, text_bitmap, tulip

# Palette (RGB 0-255)
WHITE = (255, 250, 235)
PINK = (255, 140, 185)
RED = (235, 45, 60)
YELLOW = (255, 205, 50)
BLUE = (60, 110, 255)
LIGHT_BLUE = (120, 190, 255)
RIBBON = (200, 20, 40)
PURPLE = (170, 90, 230)
ORANGE = (255, 140, 40)
PEACH = (255, 170, 120)
WINE = (150, 30, 60)
STAMEN = (255, 130, 0)
GREEN = (70, 180, 70)
DARK_GREEN = (30, 120, 45)
LIGHT_GREEN = (150, 220, 110)
THROAT = (255, 240, 200)  # pale center that flower colors fade into


def mix(c1, c2, k):
    """Blend two colors: k=0 -> c1, k=1 -> c2."""
    return tuple(round(a + (b - a) * k) for a, b in zip(c1, c2))


def petal_gradient(color):
    """(inner, outer) pair: pale near the center/midrib, full color at the tips."""
    return mix(color, THROAT, 0.6), color


def bud_color(color):
    """Closed buds are a dark, greenish version of the flower color."""
    return mix(mix(color, DARK_GREEN, 0.45), (0, 0, 0), 0.3)


def gallery(t, w, h):
    """Phase 2: the three shapes side by side."""
    W = w / ASPECT
    s = min(h * 0.4, W / 6 * 0.9)
    sway = 0.15 * math.sin(t * 1.5)
    return [
        (lily, W * 1 / 6, 0, s, t * 0.3, PINK),
        (lily_center, W * 1 / 6, 0, s, t * 0.3, STAMEN),
        (tulip, W * 3 / 6, 0, s, sway, RED),
        (leaf, W * 5 / 6, 0, s, -sway, GREEN),
    ]


# Bouquet layout. Distances and sizes are fractions of the screen height.
# Angles are degrees from vertical, positive = leaning right.
TIE_Y = -0.28  # where the stems meet
TAIL = 0.18  # how far stems continue below the tie
STEM_W = 0.45  # stem half thickness, in rows

# (shape, angle, distance from tie, size, color). Later = drawn on top.
FLOWERS = [
    (tulip, -27, 0.70, 0.11, RED),
    (tulip, 28, 0.72, 0.11, YELLOW),
    (tulip, -42, 0.50, 0.12, LIGHT_BLUE),
    (tulip, 42, 0.50, 0.12, RED),
    (tulip, 2, 0.70, 0.10, BLUE),
    (lily, -17, 0.55, 0.16, WHITE),
    (lily, 17, 0.58, 0.16, PEACH),
    (lily, -34, 0.30, 0.12, LIGHT_BLUE),
    (lily, 0, 0.33, 0.15, PINK),
]

# (shape, angle, size). Long narrow leaves start at the tie and fan out.
LEAVES = [
    (leaf_left, -70, 0.34),
    (leaf, 68, 0.36),
    (leaf_left, -52, 0.44),
    (leaf, 50, 0.42),
    (leaf_left, -34, 0.48),
    (leaf, 36, 0.46),
    (leaf_left, -18, 0.40),
    (leaf, 20, 0.42),
    (leaf_left, -6, 0.30),
    (leaf, 8, 0.32),
]


# Growth timeline, in seconds at SPEED = 1. Flowers appear in FLOWERS order.
SPEED = 0.5  # 1 = normal, 0.5 = half speed, 2 = double
LEAF_START = 0.6  # leaves unfold once the stems are on their way
STAGGER = 0.5  # delay between one flower's stem and the next
STEM_TIME = 1.5  # how long a stem takes to grow
BUD_DELAY = 1.2  # closed bud appears as the stem reaches its top
BUD_TIME = 0.6
BLOOM_DELAY = 2.2  # bud opens into the flower this long after its stem starts
BLOOM_TIME = 1.2
SWAY = 2.0  # degrees, pivoting at the tie
BOW_START = 2.0  # the ribbon ties the stems once they are growing
BOW_SIZE = 0.2
HEART_START = 7.5  # the heart frame is traced once the flowers are open
HEART_TIME = 2.0
HEART_SIZE = 0.61  # fills the screen height
HEART_Y = -0.054  # centers it vertically
HEART_W = 0.6  # line half thickness, in rows
BOUQUET_SCALE = 0.78  # bouquet size inside the heart; lower = more space around it
BADGE_SIZE = 0.1  # filled heart on the bow knot, fraction of the bouquet size
PHRASE_Y = -0.2  # phrase position below the tie, fraction of the bouquet size
PHRASE_COLOR = (255, 225, 235)


def ease(t, start, duration):
    """0 before start, 1 after start+duration, ease-out curve in between."""
    p = min(1.0, max(0.0, (t - start) / duration))
    return 1 - (1 - p) ** 3


def bouquet(t, w, h, flowers=FLOWERS):
    """Grows stem -> leaves -> bud -> flower, then sways.
    Layers back to front: heart, leaves, stems, bow, buds, tulips, lilies."""
    t *= SPEED
    W = w / ASPECT
    screen = min(h, W)  # the heart uses the full screen
    unit = screen * BOUQUET_SCALE  # the bouquet is smaller, centered inside it
    tx, ty = W / 2, TIE_Y * unit

    def along(deg, dist):  # point at `dist` from the tie, in direction `deg`
        r = math.radians(deg)
        return tx + math.sin(r) * dist, ty + math.cos(r) * dist

    leaves, stems, buds, tulips, lilies = [], [], [], [], []
    for i, (shape, deg, size) in enumerate(LEAVES):
        g = ease(t, LEAF_START + 0.2 * i, STEM_TIME)
        if g == 0:
            continue
        deg += SWAY * 0.5 * math.sin(t * 1.3 + i + 10)
        s = size * unit * g  # grows from its base at the tie
        leaves.append((shape, *along(deg, s / 2), s, -math.radians(deg), (LIGHT_GREEN, GREEN)))

    for i, (shape, deg, dist, size, color) in enumerate(flowers):
        start = i * STAGGER
        g = ease(t, start, STEM_TIME)
        if g == 0:
            continue
        deg += SWAY * math.sin(t * 1.3 + i)  # stem + flower pivot together
        a = -math.radians(deg)
        d, tail = dist * unit, TAIL * unit
        half = (d + tail) / 2
        stems.append((partial(stem, width=STEM_W / half, grow=g),
                      *along(deg, (d - tail) / 2), half, a, (GREEN, DARK_GREEN)))

        pos = along(deg, d)
        u = ease(t, start + BUD_DELAY, BUD_TIME)
        b = ease(t, start + BLOOM_DELAY, BLOOM_TIME)
        if u > 0 and b < 0.5:  # bud stays until the flower is half open
            buds.append((bud, *pos, size * unit * 0.75 * u, a, bud_color(color)))
        if b == 0:
            continue
        if shape is lily:
            a += (1 - b) * 1.5  # petals twist open as they grow
        s, grad = size * unit * b, petal_gradient(color)
        if shape is lily:
            lilies += [(lily, *pos, s, a, grad), (lily_center, *pos, s, a, STAMEN)]
        else:
            tulips.append((shape, *pos, s, a, grad))
    k = ease(t, BOW_START, BLOOM_TIME)
    ribbon = [(bow, tx, ty, BOW_SIZE * unit * k, 0, RIBBON)] if k > 0 else []
    k = ease(t, HEART_START, HEART_TIME)
    frame = []
    if k > 0:
        hs = HEART_SIZE * screen * (1 + 0.015 * math.sin(t * 3))  # gentle beat
        frame = [(partial(heart, width=HEART_W / hs, draw=k), tx, HEART_Y * screen, hs, 0, RED, NAME)]
    k = ease(t, BOW_START + 0.5, BLOOM_TIME)  # filled heart pops in on the bow
    badge = [(heart_fill, tx, ty, BADGE_SIZE * unit * k, 0,
              (mix(RED, WHITE, 0.45), RED))] if k > 0 else []
    k = ease(t, HEART_START, HEART_TIME)  # phrase is typed while the big heart is drawn
    label = phrase_label(k, tx, ty + PHRASE_Y * unit)
    return frame + leaves + stems + ribbon + badge + buds + tulips + lilies + label


def phrase_label(k, cx, cy):
    """PHRASE typed up to fraction k, as plain text (size 1) or big letters."""
    if not PHRASE or k == 0:
        return []
    if PHRASE_SIZE <= 1:
        return [(f" {PHRASE[:round(len(PHRASE) * k)]} ", cx, cy, 1, 0, PHRASE_COLOR)]
    bitmap = text_bitmap(PHRASE, PHRASE_SIZE, ASPECT)
    w, h = len(bitmap[0]) / ASPECT / 2, len(bitmap) / 2  # half size in row units
    s = max(w, h) * 1.1  # corners stay inside the renderer's bounding circle (radius 1.31)
    return [(partial(big_text, bitmap=bitmap, half_w=w / s, half_h=h / s, reveal=k),
             cx, cy, s, 0, (WHITE, PHRASE_COLOR))]


SCENES = {"gallery": gallery, "bouquet": bouquet}
