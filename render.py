"""Turns a scene into colored ASCII and plays it in the terminal."""
import math
import os
import select
import shutil
import sys
import termios
import time
import tty

RAMP = " .:-=+*#%@"  # empty to dense
ASPECT = 2.0  # ponytail: cells are ~2x taller than wide; tune for your font
FPS = 30
RESET = "\x1b[0m"

# Background sparkles (empty cells only)
SPARKLE_EVERY = 45  # ~1 in N empty cells can twinkle; higher = fewer
SPARKLE_COLOR = (210, 210, 235)


def shade(rgb, b):
    """Final cell color: RGB (0-255) dimmed by brightness b."""
    k = 0.55 + 0.45 * b
    return tuple(round(c * k) for c in rgb)


def fg(rgb, b=1.0):
    """24-bit (truecolor) foreground escape for RGB (0-255), dimmed by brightness b."""
    r, g, bl = shade(rgb, b)
    return f"\x1b[38;2;{r};{g};{bl}m"


def pick_color(rgb, b):
    """rgb is one color, or a gradient pair (inner, outer):
    bright parts of the shape get `inner`, dim parts get `outer`."""
    if isinstance(rgb[0], tuple):
        inner, outer = rgb
        return tuple(o + (i - o) * b for i, o in zip(inner, outer))
    return rgb


def sparkle(x, y, t):
    """Twinkle brightness 0..1 for an empty cell, fixed positions on screen."""
    h = ((x * 73856093) ^ (y * 19349663)) & 0xFFFF
    if h % SPARKLE_EVERY:
        return 0
    return max(0.0, math.sin(t * 1.2 + h)) ** 3  # mostly off, short bright blinks


def cells(scene, w, h, t=None):
    """Draws the scene into h rows of w cells. Each cell is None (empty) or (char, rgb).
    scene: list of (shape, cx, cy, scale, angle, rgb[, text]) in row units, y up.
    Later items are drawn on top of earlier ones (layers).
    rgb can be a gradient pair, see pick_color.
    With `text`, the shape is written with those letters instead of RAMP.
    If `shape` is a string instead of a function, it is written as plain,
    readable text centered at (cx, cy); spaces clear what is behind them.
    With `t`, empty cells may show twinkling sparkles."""
    grid = [[None] * w for _ in range(h)]  # (brightness, rgb, text) per cell

    # Paint each shape only inside its bounding box, back to front.
    for shape, cx, cy, s, a, rgb, *text in scene:
        if isinstance(shape, str):  # text label
            y = round(h / 2 - cy)
            x0 = round(cx * ASPECT - len(shape) / 2)
            if 0 <= y < h:
                for i, ch in enumerate(shape):
                    if 0 <= x0 + i < w:
                        grid[y][x0 + i] = (1.0, rgb, ch) if ch != " " else None
            continue
        if s <= 0:
            continue
        fill = text[0] if text else None
        c, sn = math.cos(a), math.sin(a)
        r = 1.31 * s  # sqrt(1.7): bounding circle radius
        y0, y1 = max(0, int(h / 2 - cy - r)), min(h, int(h / 2 - cy + r) + 2)
        x0, x1 = max(0, int((cx - r) * ASPECT)), min(w, int((cx + r) * ASPECT) + 2)
        for y in range(y0, y1):
            dy = (h / 2 - y - cy) / s
            row = grid[y]
            for x in range(x0, x1):
                dx = (x / ASPECT - cx) / s
                if dx * dx + dy * dy > 1.7:
                    continue
                val = shape(dx * c + dy * sn, -dx * sn + dy * c)
                if val > 0:
                    row[x] = (val, rgb, fill)

    # Pick the character and final color of every cell.
    for y in range(h):
        row = grid[y]
        for x in range(w):
            cell = row[x]
            if cell is None and t is not None:
                sb = sparkle(x, y, t)
                if sb > 0.2:
                    cell = (sb, SPARKLE_COLOR, "." if sb < 0.6 else "+" if sb < 0.9 else "*")
            if cell is None:
                continue
            b, color, fill = cell
            if fill:  # by position, so letters stay put when flowers sway over them
                ch = fill[(x + y) % len(fill)]
            else:
                ch = RAMP[min(len(RAMP) - 1, int(b * len(RAMP)))]
            row[x] = (ch, shade(pick_color(color, b), b))
    return grid


def render(scene, w, h, t=None):
    """Scene -> colored terminal text (see cells)."""
    lines = []
    for row in cells(scene, w, h, t):
        out, last = [], None
        for cell in row:
            if cell is None:
                out.append(" ")
                continue
            ch, rgb = cell
            if rgb != last:
                out.append("\x1b[38;2;%d;%d;%dm" % rgb)
                last = rgb
            out.append(ch)
        if last is not None:
            out.append(RESET)
        lines.append("".join(out))
    return "\n".join(lines)


def play(scene_fn, on_key=None, status=None):
    """Calls scene_fn(t, w, h) every frame until Ctrl+C.
    on_key(ch): called for each key pressed (no Enter needed); return True to quit.
    status(): text shown on the bottom line."""
    keys = on_key is not None and sys.stdin.isatty()
    if keys:
        fd = sys.stdin.fileno()
        saved = termios.tcgetattr(fd)
        tty.setcbreak(fd)  # read keys one by one, Ctrl+C still works
    sys.stdout.write("\x1b[?25l\x1b[2J")  # hide cursor, clear screen
    start = time.time()
    try:
        while True:
            w, h = shutil.get_terminal_size()
            h -= 1  # last line: status (or empty, avoids scrolling)
            t = time.time() - start
            frame = render(scene_fn(t, w, h), w, h, t)
            if status:
                frame += "\n" + fg((140, 140, 140)) + status()[:w].ljust(w) + RESET
            sys.stdout.write("\x1b[H" + frame)
            sys.stdout.flush()
            if keys:  # wait for the next frame, but wake up on a key press
                if select.select([fd], [], [], 1 / FPS)[0]:
                    pressed = os.read(fd, 32).decode(errors="ignore")
                    if any(on_key(ch) for ch in pressed):
                        break
            else:
                time.sleep(1 / FPS)
    except KeyboardInterrupt:
        pass
    finally:
        if keys:
            termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write(RESET + "\x1b[?25h\n")  # reset color, restore cursor
        sys.stdout.flush()
