# ASCII Bouquet

A bouquet of lilies and tulips that grows in your terminal, drawn entirely with characters.

> **Heads-up:** this is not a serious project. I started it to experiment after seeing an ASCII art reel ("ASCII lilly bouquet" by [@arimecoa](https://www.instagram.com/arimecoa/)) and wondering how to build something like it in Python. It isn't meant to be a library or a product, and it has limitations I don't plan to fix (see [Limitations](#limitations)). Even so, the internals are explained properly below in case they're useful to someone.

## What it does

- **Animates a bouquet in the terminal.** The stems grow first, then the leaves unfold, buds appear, and the flowers open one by one. When everything has grown, the bouquet sways gently.
- **Draws a heart around the bouquet** out of your own text, ties a ribbon with a small heart on it, and writes a phrase at the base.
- **Generates random bouquets** that follow composition rules: flowers stay on screen, don't crowd each other, and are balanced left to right.
- **Lets you pick the flower colors** before it starts.
- **Controls Spotify** (macOS only): plays a song in the background, lets you choose which part to use (like Instagram stories), and gives you keyboard controls while the animation runs.
- **Exports the animation** as a GIF, or as an MP4 with an audio snippet.

## Requirements

| For | You need |
|-----|----------|
| The animation | Python 3 and a terminal with 24-bit color (for example, the VS Code terminal or iTerm2) |
| Big letters, GIF and MP4 | [Pillow](https://pypi.org/project/pillow/) (`pip3 install pillow`) |
| MP4 | [ffmpeg](https://ffmpeg.org/) (`brew install ffmpeg`) |
| Spotify | macOS with the Spotify desktop app |

The animation itself only uses the Python standard library.

## Usage

```bash
python3 main.py                  # gallery: each shape on its own, handy for tweaking
python3 main.py bouquet          # the bouquet
python3 main.py random           # a random bouquet (prints its seed on exit)
python3 main.py random 42        # the same random bouquet every time
python3 main.py bouquet --gif    # save it as bouquet.gif without showing it
python3 main.py bouquet --video  # save bouquet.mp4 with a snippet of an audio file
```

Before it starts, `bouquet` and `random` ask for:
1. **The flower colors.** Enter = defaults.
2. **A Spotify link** for background music. Enter = no music.
3. **Which part of the song to use**, only if you pasted a link.

When you close the animation, it asks whether to save it as a GIF. By default it doesn't.

### Keys while it runs

| Key | Action |
|-----|--------|
| `space` | Spotify play / pause |
| `n` / `p` | Next / previous track |
| `+` / `-` | Volume up / down |
| `q` or `Ctrl+C` | Quit |

For more detail, make your terminal font smaller. The drawing adapts to the window size.

## Customizing

The usual settings are at the top of `scenes.py`:

```python
NAME = "..."        # text that forms the outline of the big heart
PHRASE = "..."      # phrase at the base of the bouquet ("" = none)
PHRASE_SIZE = 1     # 1 = normal text; 5 or more = big letters that many rows tall
```

Further down the same file are the color palette, the `FLOWERS` and `LEAVES` tables (shape, angle, distance, size and color of each piece), and the animation timing (`SPEED`, `STAGGER`, `BLOOM_TIME`, …). Each constant has a comment explaining what it does.

## How it works

### 1. Coordinates and cell proportions

A terminal character is roughly twice as tall as it is wide. All drawing happens in **"row units"**: Y points up, the origin is at the vertical center of the screen, and one column equals half a unit (`ASPECT = 2` in `render.py`). Without this correction, circles would come out as ovals.

### 2. Shapes are functions, not images

Each shape in `shapes.py` is a function `f(x, y) -> brightness` in local coordinates of size ~1. It returns a value from 0 to 1, where 0 means "outside the shape". There are no sprites or images: everything is computed from geometry, so it scales to any screen size and can be animated just by changing parameters.

- **Lily**: six petals in a star. For each point, the nearest petal is picked by angle, and the point is converted to coordinates along and across that petal. The width follows `sin(π·t)^0.7`, which makes petals pointed at both ends. The speckles are a fixed pseudo-random pattern in the flower's own coordinates.
- **Tulip**: an ellipse cut at the top by a wavy edge, `cos(2πx/0.33)`, which forms the three tips. The same wave shades the petal folds.
- **Heart**: the classic implicit curve `(x² + y² − 1)³ = x²y³`. To draw just the outline with an even thickness, the distance to the curve is approximated as `|f| / |∇f|`, with the gradient computed analytically. The tracing animation filters by angle, from the top notch down to the tip.
- **Leaves, stems, buds and ribbon**: simple ellipses and parametric curves, with shading built into the brightness (lighter in the middle, darker toward the edges).

### 3. From scene to screen

A **scene** (`scenes.py`) is a function `(t, width, height) -> list of pieces`. Each piece is `(shape, cx, cy, scale, angle, color[, text])`. The renderer (`render.py`) processes it in two steps:

1. **`cells()` paints a grid** using the painter's algorithm: pieces are drawn back to front, and each one evaluates its function only inside its bounding box (not across the whole screen), mapping every cell to the shape's local coordinates with a translation, a rotation and a scale.
2. **Each cell becomes a character and a color:**
   - The **character** comes from a density ramp, ` .:-=+*#%@`, based on brightness. If the piece carries text (the heart outline), the letter `text[(x + y) % length]` is used instead. Because it depends on screen position rather than time, the letters don't flicker when something moves over them.
   - The **color** can be a single color or an `(inner, outer)` pair, interpolated by brightness. That is how petals come out pale in the middle and saturated at the tips. The color is then dimmed by brightness and emitted as a 24-bit color code (`ESC[38;2;r;g;bm`), written only when the color changes.

Empty cells may show **background sparkles**: a hash of `(x, y)` decides which cells can twinkle, and a sine wave with its own phase decides when.

### 4. Animation

Each part of the bouquet has its own time window, smoothed with an *ease-out* curve (`1 − (1 − p)³`). The flowers share a staggered timeline: stem → bud → flower, with each flower starting `STAGGER` seconds after the previous one. The sway is a sinusoidal rotation with a different phase per flower, applied around the point where the stems are tied, so the stem and its flower move together.

The main loop (`play()` in `render.py`) draws at ~30 fps and overwrites the screen from the top-left corner (`ESC[H`) instead of clearing it, which avoids flicker. To read keys without pausing the animation, it puts the terminal in *cbreak* mode (`termios`/`tty`) and waits with `select()` for at most one frame, instead of calling `sleep()`. It restores the terminal on exit.

### 5. Random bouquets

`random_bouquet.py` uses **rejection sampling**: for each flower it proposes random positions and keeps the first one that passes every rule (angle and height range per flower type, staying on screen, a minimum distance from the others). Lilies are placed before tulips because they are the main flowers, and sides alternate to keep the bouquet balanced. Everything depends on a seed, so the same number always produces the same bouquet.

### 6. Text

- **Normal phrase**: written character by character on a single row. Spaces clear what's behind them, so the phrase stays readable over the stems.
- **Big letters**: `text_bitmap()` draws the phrase with Pillow (Menlo Bold), shrinks the image to a grid of cells by averaging the pixels inside each cell, and turns that coverage into brightness. The result is treated like any other shape, with a left-to-right typing effect.

### 7. Spotify

`music.py` does not use the Spotify Web API. It controls the **desktop app through AppleScript** (`osascript`), so it needs no credentials or developer account. Shared links are validated with a strict regular expression before they are used in a command. While the animation runs:

- keyboard commands are sent in separate processes so drawing never stalls;
- a background thread checks what's playing every ~2 s, for the status line;
- another thread keeps the song inside the chosen snippet and jumps back when it passes the end. It stops doing so if you switch songs.

Spotify no longer exposes where a song's chorus is, so the snippet suggestions are **estimates** based on the typical structure of a pop song (roughly 28 %, 50 % and 75 % of its length).

### 8. Exporting

`export.py` reuses the same `cells()` as the terminal, so what gets exported is exactly what you see:

- Each character is drawn **only once** as a mask with Pillow, then "stamped" with its color into each cell. This is much faster than drawing text cell by cell.
- **GIF**: the format allows 256 colors per frame. A **single palette** is computed from the finished bouquet and applied to every frame without dithering, so colors stay steady between frames and the black background stays clean.
- **MP4**: raw frames are piped into `ffmpeg` through standard input and encoded as H.264 (`-tune animation`, `crf 14`). If there is audio, the chosen snippet is cut (`-ss`/`-t`) and given a fade-in and fade-out.

Spotify audio is DRM-protected and can't be extracted, which is why the MP4 uses your own audio file.

## Project layout

```
main.py            entry point: arguments, prompts and which mode to run
scenes.py          customization, palette, bouquet layout and timeline
shapes.py          the shapes (brightness functions) and big text
render.py          scene → grid → colored text; the terminal loop
random_bouquet.py  rule-based random bouquets
color_picker.py    color menu
music.py           Spotify: playback, controls and snippet picker
export.py          GIF and MP4
test_shapes.py     tests
```

## Tests

```bash
python3 test_shapes.py
```

It's a single script of `assert`s, with no framework. It checks the shapes, that the scene renders, that 200 random bouquets follow the rules, the color menu, Spotify link parsing, the text features, and that the GIF and MP4 are generated correctly. The export checks need Pillow and ffmpeg.

## Limitations

- **Performance**: everything is computed cell by cell in pure Python. With very small fonts (many cells) the animation gets less smooth.
- **Spotify only works on macOS** with the desktop app. On free accounts, Spotify may ignore the requested song.
- **The chorus suggestions are approximate.**
- **GIFs have no audio** (the format doesn't support it). To share with music, use the MP4.
- **All lilies face forward**: there are no side views.
- Some constants are hand-tuned to look good, not to cover every case.
