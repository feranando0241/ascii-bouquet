"""Saves the animation as a looping GIF (Pillow) or an MP4 with a song snippet (ffmpeg)."""
import os
import shlex
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

import music
from render import ASPECT, cells
from scenes import HEART_START, HEART_TIME, SPEED

COLS, ROWS = 132, 60  # characters; a bit wider than square so the heart is not cut
FPS = 12  # GIF frame rate
VIDEO_FPS = 30  # MP4 frame rate (smoother; video compresses much better than GIF)
SECONDS = (HEART_START + HEART_TIME) / SPEED + 3  # full growth + heart + a little swaying
FONT_SIZE = 18  # pixels; bigger = sharper characters (and a heavier file)
FONT = "/System/Library/Fonts/Menlo.ttc"
FONT_INDEX = 1  # Menlo.ttc: 0 regular, 1 bold (bold stays crisp when shared)
BACKGROUND = (0, 0, 0)


def drawer(scene_fn):
    """Returns draw(t) -> RGB image of the scene at time t, drawn with the same
    cells as the terminal."""
    try:
        font = ImageFont.truetype(FONT, FONT_SIZE, index=FONT_INDEX)
    except OSError:
        font = ImageFont.load_default(FONT_SIZE)
    cw = round(font.getlength("M"))  # cell width in pixels
    chh = round(cw * ASPECT)  # cell height, same proportions as the terminal model

    glyphs = {}  # char -> mask image, drawn once and reused

    def glyph(ch):
        if ch not in glyphs:
            mask = Image.new("L", (cw, chh), 0)
            ImageDraw.Draw(mask).text((cw / 2, chh / 2), ch, fill=255, font=font, anchor="mm")
            glyphs[ch] = mask
        return glyphs[ch]

    def draw(t):
        img = Image.new("RGB", (COLS * cw, ROWS * chh), BACKGROUND)
        for y, row in enumerate(cells(scene_fn(t, COLS, ROWS), COLS, ROWS, t)):
            for x, cell in enumerate(row):
                if cell:
                    ch, rgb = cell
                    img.paste(rgb, (x * cw, y * chh, (x + 1) * cw, (y + 1) * chh), glyph(ch))
        return img

    return draw


def frames(scene_fn, seconds, fps, label):
    """Yields one RGB image per frame."""
    draw = drawer(scene_fn)
    n = int(seconds * fps)
    for i in range(n):
        print(f"\r  Rendering {label}: frame {i + 1}/{n}", end="", flush=True)
        yield draw(i / fps)
    print()


def export_gif(scene_fn, path, seconds=SECONDS, fps=FPS):
    """GIFs allow 256 colors. One shared palette, taken from the finished bouquet
    (it has every color), keeps colors steady between frames; no dithering keeps
    the black background clean instead of speckled."""
    palette = drawer(scene_fn)(seconds).quantize(256, dither=Image.Dither.NONE)
    imgs = [img.quantize(palette=palette, dither=Image.Dither.NONE)
            for img in frames(scene_fn, seconds, fps, "GIF")]
    imgs[0].save(path, save_all=True, append_images=imgs[1:],
                 duration=round(1000 / fps), loop=0, optimize=True)
    return path


# --- MP4 with a song snippet -----------------------------------------------

def audio_duration(path):
    """Length in seconds via ffprobe, or None if it isn't a readable audio file."""
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return None


def ask_audio(length=SECONDS):
    """Asks for an audio file and which part to use (with preview).
    Returns (path, start_second) or None for a silent video."""
    print("\nVideo audio: drag an audio file (mp3, m4a, wav...) here or type its path.")
    print("(Spotify audio can't be extracted, so it has to be your own file.)")
    try:
        text = input("File [Enter = no audio]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not text:
        return None
    try:
        path = shlex.split(text)[0]  # handles drag-and-drop quotes and "\ " escapes
    except ValueError:
        path = text
    path = os.path.expanduser(path)
    duration = audio_duration(path) if os.path.isfile(path) else None
    if not duration:
        print("  Couldn't read that audio file, continuing without audio.")
        return None

    player = []  # the preview currently playing, if any

    def preview(sec):
        stop_preview(player)
        if shutil.which("ffplay"):
            player.append(subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet",
                 "-ss", str(sec), "-t", str(length), path],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

    try:
        start = music.pick_start(duration, preview, length)
    finally:
        stop_preview(player)
    print(f"  Using {music.fmt(start)} – {music.fmt(min(duration, start + length))}.")
    return path, start


def stop_preview(player):
    while player:
        player.pop().terminate()


def export_mp4(scene_fn, path, audio=None, seconds=SECONDS, fps=VIDEO_FPS):
    """Pipes full-color frames into ffmpeg (H.264). audio = (file, start) adds that
    part of the song with a short fade in/out; None = silent video."""
    imgs = frames(scene_fn, seconds, fps, "video")
    first = next(imgs)
    w, h = first.size
    cmd = ["ffmpeg", "-y", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio:
        file, start = audio
        cmd += ["-ss", str(start), "-t", str(seconds), "-i", file]
    cmd += ["-map", "0:v", "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",  # H.264 needs even sizes
            "-c:v", "libx264", "-preset", "slow", "-tune", "animation",  # sharper flat colors/text
            "-crf", "14", "-pix_fmt", "yuv420p"]  # crf: lower = better quality; yuv420p plays everywhere
    if audio:
        fade_out = max(0, seconds - 2)
        cmd += ["-map", "1:a", "-c:a", "aac", "-b:a", "192k",
                "-af", f"afade=t=in:d=1,afade=t=out:st={fade_out}:d=2"]
    cmd += ["-movflags", "+faststart", path]  # plays right away when shared

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        proc.stdin.write(first.tobytes())
        for img in imgs:
            proc.stdin.write(img.tobytes())
    finally:
        proc.stdin.close()
    if proc.wait():
        raise SystemExit("ffmpeg couldn't create the video.")
    return path
