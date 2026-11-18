"""Usage:
    python3 main.py [scene]          scenes: gallery (default), bouquet
    python3 main.py random [seed]    random bouquet; same seed = same bouquet
    bouquet and random first ask for flower colors and a Spotify song
    (Enter = defaults / no music)
    add --gif to save it as a GIF, or --video for an MP4 with part of a song
"""
import random
import sys
from functools import partial

import music
from color_picker import ask_colors, recolor
from random_bouquet import random_flowers
from render import play
from scenes import FLOWERS, SCENES, bouquet


def with_music(scene_fn):
    """Asks for a song, plays it during the animation with live Spotify
    controls, and pauses it on exit if we started it."""
    uri = music.ask_song()
    if uri and not music.play(uri):
        print("  Couldn't control Spotify (did you allow the terminal to?). Continuing without music.")
        uri = None
    if uri:
        music.choose_part(uri)  # Instagram-style: pick which part of the song to use
    try:
        play(scene_fn, *music.controls())  # keys control Spotify, bottom line shows the song
    finally:
        if uri:
            music.pause()


def show(scene_fn, file_name):
    """Plays in the terminal, or exports: --gif (no sound) / --video (MP4 + song snippet)."""
    if "--gif" in sys.argv or "--video" in sys.argv:
        import export  # Pillow/ffmpeg are only needed here
        if "--video" in sys.argv:
            path = export.export_mp4(scene_fn, file_name + ".mp4", export.ask_audio())
        else:
            path = export.export_gif(scene_fn, file_name + ".gif")
        print(f"Done: {path}")
    else:
        with_music(scene_fn)
        if wants_gif():
            import export
            print(f"Done: {export.export_gif(scene_fn, file_name + '.gif')}")


def wants_gif():
    """Asked after watching the animation. Anything but yes = no GIF."""
    try:
        answer = input("Save this bouquet as a GIF? [y/N]: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    return answer.strip().lower() in ("y", "yes")


args = [a for a in sys.argv[1:] if not a.startswith("-")]
name = args[0] if args else "gallery"

if name == "random":
    seed = int(args[1]) if len(args) > 1 else random.randrange(10000)
    colors = ask_colors()
    show(partial(bouquet, flowers=random_flowers(seed, colors)), f"bouquet_{seed}")
    print(f"seed: {seed}  (repeat it with: python3 main.py random {seed})")
elif name == "bouquet":
    colors = ask_colors()
    show(partial(bouquet, flowers=recolor(FLOWERS, colors)), "bouquet")
elif name in SCENES:
    play(SCENES[name])
else:
    sys.exit(f"Unknown scene '{name}'. Options: {', '.join(SCENES)}, random")
