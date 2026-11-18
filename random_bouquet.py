"""Random bouquets that still follow the rules of a "normal" bouquet.

Placement uses rejection sampling: pick a random spot, keep it only if it
passes every rule, otherwise try again (up to TRIES times).
"""
import math
import random

from scenes import BLUE, LIGHT_BLUE, PEACH, PINK, RED, TIE_Y, WHITE, WINE, YELLOW
from shapes import lily, tulip

# Per flower type, placed in this order (lilies first: they are the stars).
# Distances/sizes are fractions of the screen height,
# angles are degrees from vertical (max lean to either side).
RULES = {
    lily: dict(count=(3, 4), max_angle=25, dist=(0.30, 0.58), size=(0.13, 0.17),
               colors=[WHITE, WHITE, PINK, PEACH, RED, YELLOW, LIGHT_BLUE]),  # white twice = more likely
    tulip: dict(count=(4, 6), max_angle=45, dist=(0.45, 0.72), size=(0.10, 0.12),
                colors=[RED, YELLOW, PINK, WINE, BLUE, LIGHT_BLUE]),
}
TOP = 0.46  # no flower may reach higher than this (0.5 = top of screen)
MIN_GAP = 0.5  # centers at least MIN_GAP * (sum of sizes) apart; <1 allows some overlap
TRIES = 200


def random_flowers(seed, colors=None):
    """Returns a FLOWERS-style list: (shape, angle, dist, size, color).
    `colors`: if given, every flower picks only from these."""
    rng = random.Random(seed)
    placed = []  # (x, y, size) relative to the tie, for the overlap rule
    result = {tulip: [], lily: []}

    for shape, rule in RULES.items():
        for i in range(rng.randint(*rule["count"])):
            side = 1 if i % 2 else -1  # alternate left/right = balanced
            for _ in range(TRIES):
                deg = side * rng.uniform(0, rule["max_angle"])
                dist = rng.uniform(*rule["dist"])
                size = rng.uniform(*rule["size"])
                x = math.sin(math.radians(deg)) * dist
                y = math.cos(math.radians(deg)) * dist
                if TIE_Y + y + size > TOP:
                    continue  # would leave the screen
                if any(math.hypot(x - px, y - py) < MIN_GAP * (size + ps)
                       for px, py, ps in placed):
                    continue  # too close to another flower
                placed.append((x, y, size))
                result[shape].append((shape, round(deg), dist, size, rng.choice(colors or rule["colors"])))
                break  # placed; if all tries fail the flower is skipped

    # Appearance order: higher flowers first, the lowest lily (front) last.
    by_height = lambda f: -f[2] * math.cos(math.radians(f[1]))
    return sorted(result[tulip], key=by_height) + sorted(result[lily], key=by_height)
