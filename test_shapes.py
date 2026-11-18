"""Run: python3 test_shapes.py"""
from render import render
from scenes import bouquet, gallery
from shapes import bow, bud, heart, leaf, lily, lily_center, tulip

assert lily_center(0, 0) == 1 and lily_center(0.3, 0) == 0 and lily(0.5, 0) > 0 and lily(2, 0) == 0
assert bud(0, 0) > 0 and bud(0, 0.7) == 0 and bud(0.3, 0) == 0
assert tulip(0, 0) > 0 and tulip(0, 0.7) == 0
assert bow(0, 0) > 0 and bow(0, 0.5) == 0 and bow(0.42, 0.1) == 0  # knot, empty, loop hole
assert heart(1 / 1.4, 1 / 1.4, 0.05) > 0 and heart(0, 0, 0.05) == 0  # on curve, center
assert heart(1 / 1.4, 1 / 1.4, 0.05, draw=0.1) == 0  # not traced yet
assert leaf(0.0625, 0) > 0 and leaf(-0.3, 0) == 0
assert "@" in render(gallery(0, 120, 30), 120, 30)
assert "@" in render(bouquet(30, 160, 46), 160, 46)
assert set(render(bouquet(0, 160, 46), 160, 46)) <= {" ", "\n"}  # nothing yet
assert any(ch in render(bouquet(0, 160, 46), 160, 46, t=t) for ch in ".+*" for t in (0.5, 1, 2, 3))  # sparkles
# Random bouquets always follow the rules
import math
from random_bouquet import MIN_GAP, RULES, TOP, random_flowers
from scenes import TIE_Y
counts = {lily: 0, tulip: 0}
for seed in range(200):
    fl = random_flowers(seed)
    assert fl == random_flowers(seed)  # same seed, same bouquet
    pts = []
    for shape, deg, dist, size, color in fl:
        r = RULES[shape]
        assert abs(deg) <= r["max_angle"] and r["dist"][0] <= dist <= r["dist"][1]
        assert TIE_Y + math.cos(math.radians(deg)) * dist + size <= TOP + 0.01
        pts.append((math.sin(math.radians(deg)) * dist, math.cos(math.radians(deg)) * dist, size))
    for i, (x, y, s) in enumerate(pts):
        for px, py, ps in pts[:i]:
            assert math.hypot(x - px, y - py) >= MIN_GAP * (s + ps) - 0.01
    for shape in counts:
        counts[shape] += sum(f[0] is shape for f in fl)
    assert "@" in render(bouquet(30, 160, 46, flowers=fl), 160, 46)
print("avg flowers per bouquet:", {s.__name__: c / 200 for s, c in counts.items()})
import re
from scenes import NAME
plain = re.sub(r"\x1b\[[0-9;]*m", "", render(bouquet(30, 160, 46), 160, 46))
assert any((NAME * 2)[i:i + 4] in plain for i in range(len(NAME)))  # the heart spells the name (any length)
# Color picker: invalid/empty -> defaults, valid -> cycles per flower type
from color_picker import parse_choice, recolor
from scenes import BLUE, FLOWERS, PINK, WHITE
assert parse_choice("") is None and parse_choice("abc") is None and parse_choice("0") is None and parse_choice("99") is None
assert parse_choice("1, 9") == [WHITE, BLUE] and parse_choice("2 2") == [PINK, PINK]
assert recolor(FLOWERS, None) == FLOWERS
assert {f[4] for f in recolor(FLOWERS, [BLUE])} == {BLUE}
assert {f[4] for f in recolor(FLOWERS, [BLUE, PINK])} == {BLUE, PINK}
for seed in range(50):
    assert {f[4] for f in random_flowers(seed, [PINK, BLUE])} <= {PINK, BLUE}
# Spotify links -> URIs; anything else -> None
from music import to_uri
ID = "4uLU6hMCjMI75M1A2tKUQC"
assert to_uri(f"https://open.spotify.com/track/{ID}?si=abc123") == f"spotify:track:{ID}"
assert to_uri(f"https://open.spotify.com/intl-es/track/{ID}") == f"spotify:track:{ID}"
assert to_uri(f"spotify:track:{ID}") == f"spotify:track:{ID}"
assert to_uri(f"https://open.spotify.com/playlist/{ID}") == f"spotify:playlist:{ID}"
assert to_uri("") is None and to_uri("hello") is None and to_uri('track/" & do shell script "x') is None
from music import KEYS, describe
assert describe(None) == describe("") == describe("x|y") == "♪ Spotify: no song"
assert describe("playing|Angel|Massive Attack|70") == "▶ Angel – Massive Attack  (vol 70%)"
assert describe("paused|A|B|C|D|50").startswith("⏸ A|B|C – D")  # '|' inside the song name
assert set(KEYS) >= {" ", "n", "p", "+", "-"}
# Song parts
from music import fmt, parse_part, suggestions
assert fmt(83) == "1:23" and fmt(0) == "0:00" and fmt(600) == "10:00"
opts = suggestions(200)  # 3:20 song
assert [s for _, s in opts] == [0, 55, 100, 150]
assert all(s <= 40 - 30 for _, s in suggestions(40))  # short song: room for the snippet
assert parse_part("2", opts, 200) == 55 and parse_part("1:23", opts, 200) == 83
assert parse_part("5", opts, 200) is None and parse_part("4:00", opts, 200) is None
assert parse_part("1:75", opts, 200) is None and parse_part("hello", opts, 200) is None
# GIF export: a tiny 3-frame GIF with the right size
import os, tempfile
from PIL import Image
from export import export_gif
gif = os.path.join(tempfile.mkdtemp(), "t.gif")
export_gif(bouquet, gif, seconds=0.25, fps=12)
with Image.open(gif) as im:
    assert im.n_frames == 3 and im.size[0] > 0
# MP4 export: short video with a snippet of a generated tone has video + audio
import subprocess
from export import audio_duration, export_mp4
tone, mp4 = os.path.join(tempfile.mkdtemp(), "tone.m4a"), os.path.join(tempfile.mkdtemp(), "t.mp4")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=duration=5", tone], check=True)
assert round(audio_duration(tone)) == 5 and audio_duration(__file__) is None
export_mp4(bouquet, mp4, (tone, 2), seconds=0.5, fps=4)
streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", mp4],
                         capture_output=True, text=True).stdout.split()
assert streams == ["video", "audio"], streams
# Filled heart + readable text labels at the base
from shapes import heart_fill
from render import cells
assert heart_fill(0, 0) > 0 and heart_fill(0, 0.95) == 0 and heart_fill(0.9, -0.6) == 0
row = cells([("hello world", 5, 0, 1, 0, (255, 255, 255))], 20, 5)[2]  # cx=5 row units = column 10 (center)
assert "".join(c[0] if c else " " for c in row).strip() == "hello world"
from scenes import PHRASE
plain = re.sub(r"\x1b\[[0-9;]*m", "", render(bouquet(30, 160, 46), 160, 46))
import scenes as _sc
assert not PHRASE or _sc.PHRASE_SIZE > 1 or PHRASE in plain  # plain-text phrase is written in full
# Big phrase: letters about PHRASE_SIZE rows tall, clean background, typing reveal
from shapes import big_text, text_bitmap
bm = text_bitmap("Jo", 6)
assert 6 <= len(bm) <= 9 and any(v > 0.5 for row in bm for v in row)
assert big_text(0, 0, bm, 1, 0.5) > 0  # inside the box: letter or blank (never transparent)
assert big_text(0.9, 0, bm, 1, 0.5, reveal=0.1) == 0  # not typed yet
assert big_text(0, 0.9, bm, 1, 0.5) == 0  # outside the box
import scenes
scenes.PHRASE_SIZE = 6
assert "@" in render(bouquet(30, 160, 46), 160, 46)
scenes.PHRASE_SIZE = 1
print("ok")
