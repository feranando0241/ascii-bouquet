"""Lets the user pick flower colors in the terminal before the animation.
Empty or invalid answers keep the default colors."""
from render import RESET, fg
from scenes import BLUE, LIGHT_BLUE, ORANGE, PEACH, PINK, PURPLE, RED, WHITE, WINE, YELLOW

# (label shown to the user, rgb)
OPTIONS = [
    ("white", WHITE),
    ("pink", PINK),
    ("red", RED),
    ("yellow", YELLOW),
    ("orange", ORANGE),
    ("peach", PEACH),
    ("wine", WINE),
    ("purple", PURPLE),
    ("blue", BLUE),
    ("light blue", LIGHT_BLUE),
]


def parse_choice(text):
    """'1, 3' -> [rgb, rgb]. Empty or invalid -> None (= keep defaults)."""
    parts = text.replace(",", " ").split()
    if not parts or not all(p.isdigit() and 1 <= int(p) <= len(OPTIONS) for p in parts):
        return None
    return [OPTIONS[int(p) - 1][1] for p in parts]


def ask_colors():
    """Asks which colors to use. Returns a list of rgb, or None for the defaults."""
    print("\nChoose the flower colors (not sure? just press Enter)\n")
    for i, (label, rgb) in enumerate(OPTIONS, 1):
        print(f"  {i}. {fg(rgb)}██{RESET} {label}")
    print("\nAll flowers will only use the colors you choose.")
    print("Pick one or several, separated by commas, e.g. 2,7\n")
    try:
        text = input("Colors [Enter = default]: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    colors = parse_choice(text)
    if not colors and text.strip():
        print("  Didn't get that, using the default colors.")
    return colors


def recolor(flowers, colors):
    """Paints a FLOWERS-style list only with `colors`, cycling through them.
    None or [] = keep the original colors."""
    if not colors:
        return flowers
    return [(shape, deg, dist, size, colors[i % len(colors)])
            for i, (shape, deg, dist, size, _) in enumerate(flowers)]
