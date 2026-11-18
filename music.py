"""Background song through the Spotify desktop app (macOS, via AppleScript).
No developer account or login needed: it just tells the app what to play."""
import re
import subprocess
import threading
import time


def to_uri(text):
    """Spotify share link or URI -> 'spotify:track:ID' (also album/playlist).
    None if it doesn't look like one. The strict pattern also keeps
    anything weird out of the AppleScript command."""
    m = re.search(r"(track|album|playlist)[/:]([A-Za-z0-9]{22})", text)
    return f"spotify:{m[1]}:{m[2]}" if m else None


def _spotify(cmd):
    """Runs `tell application "Spotify" to <cmd>`. Returns its output or None on error."""
    r = subprocess.run(["osascript", "-e", f'tell application "Spotify" to {cmd}'],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def play(uri):
    """Starts the song. Opens Spotify first if needed. True if it worked."""
    if subprocess.run(["pgrep", "-x", "Spotify"], capture_output=True).returncode:
        subprocess.run(["open", "-a", "Spotify"])
        for _ in range(20):  # wait up to ~10 s for the app to be ready
            time.sleep(0.5)
            if _spotify("player state") is not None:
                break
    return _spotify(f'play track "{uri}"') is not None


def pause():
    _spotify("pause")


def ask_song():
    """Asks for a Spotify link. Returns a URI, or None for no music."""
    print("\nBackground music: in Spotify, go to Share → Copy Song Link and paste it here.")
    try:
        text = input("Song [Enter = no music]: ")
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    uri = to_uri(text)
    if not uri and text.strip():
        print("  That doesn't look like a Spotify link, continuing without music.")
    return uri


# --- Live controls while the bouquet plays ---------------------------------

KEYS = {  # key -> Spotify AppleScript command
    " ": "playpause",
    "n": "next track",
    "p": "previous track",
    "+": "set sound volume to (sound volume + 10)",
    "=": "set sound volume to (sound volume + 10)",  # same key as + without shift
    "-": "set sound volume to (sound volume - 10)",
}
HELP = "[space] play/pause  [n] next  [p] previous  [+/-] volume  [q] quit"
NOW_PLAYING = ('(player state as string) & "|" & (name of current track) & "|" & '
               '(artist of current track) & "|" & (sound volume as string)')


def is_running():
    return subprocess.run(["pgrep", "-x", "Spotify"], capture_output=True).returncode == 0


def describe(out):
    """Raw NOW_PLAYING output -> one readable line."""
    if not out:
        return "♪ Spotify: no song"
    p = out.split("|")
    if len(p) < 4:
        return "♪ Spotify: no song"
    state, name, artist, vol = p[0], "|".join(p[1:-2]), p[-2], p[-1]
    icon = "▶" if state == "playing" else "⏸"
    return f"{icon} {name} – {artist}  (vol {vol}%)"


def controls():
    """Returns (on_key, status) for render.play.
    on_key sends commands without blocking the animation;
    status() is refreshed by a background thread every ~2 s."""
    info = {"text": "♪ Spotify: connecting..."}
    refresh = threading.Event()

    def poll():
        while True:
            info["text"] = describe(_spotify(NOW_PLAYING)) if is_running() else "♪ Spotify is closed"
            refresh.wait(2)
            refresh.clear()

    threading.Thread(target=poll, daemon=True).start()

    def on_key(ch):
        if ch in "qQ":
            return True  # quit
        cmd = KEYS.get(ch.lower())
        if cmd:
            subprocess.Popen(["osascript", "-e", f'tell application "Spotify" to {cmd}'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            threading.Timer(0.4, refresh.set).start()  # show the change quickly
        return False

    return on_key, lambda: f"{info['text']}    {HELP}"


# --- Pick the part of the song (like Instagram stories/notes) --------------

SNIPPET_SECONDS = 30  # length of the part that loops during the animation; None = no loop

# Typical pop structure, as a fraction of the song length. Spotify doesn't
# expose where the chorus is anymore, so these are educated guesses.
PARTS = [
    ("Start", 0.0),
    ("First chorus (approx.)", 0.28),
    ("Middle of the song", 0.5),
    ("Last chorus (approx.)", 0.75),
]
SUGGESTED = 1  # index in PARTS that starts playing first (the chorus)


def fmt(sec):
    return f"{int(sec) // 60}:{int(sec) % 60:02d}"


def suggestions(duration, length=SNIPPET_SECONDS):
    """[(label, start_second)], starts rounded to 5 s and leaving room for `length` seconds."""
    room = max(0, duration - (length or 0))
    return [(label, min(room, round(duration * k / 5) * 5)) for label, k in PARTS]


def parse_part(text, options, duration):
    """'2' -> start of option 2, '1:23' -> 83. None if invalid or past the end."""
    text = text.strip()
    if text.isdigit() and 1 <= int(text) <= len(options):
        return options[int(text) - 1][1]
    m = re.fullmatch(r"(\d{1,2}):([0-5]\d)", text)
    if m and int(m[1]) * 60 + int(m[2]) < duration:
        return int(m[1]) * 60 + int(m[2])
    return None


def _current_track_duration(uri):
    """Waits until Spotify switched to `uri`; returns its length in seconds or None."""
    for _ in range(20):
        if _spotify("id of current track") == uri:
            ms = _spotify("duration of current track")
            return int(ms) / 1000 if ms and ms.isdigit() else None
        time.sleep(0.25)
    return None


def _position():
    out = _spotify("player position as string")
    try:
        return float(out.replace(",", "."))  # some locales use a decimal comma
    except (AttributeError, ValueError):
        return None


def loop_snippet(uri, start, length):
    """Background thread: keeps the song inside [start, start+length].
    Stops looping as soon as the user switches to another song."""
    def run():
        while True:
            time.sleep(0.5)
            if _spotify("id of current track") != uri:
                return
            pos = _position()
            if pos is not None and not (start - 1 <= pos < start + length):
                _spotify(f"set player position to {start}")
    threading.Thread(target=run, daemon=True).start()


def choose_part(uri):
    """Instagram-style: suggests parts of the song, previews each one,
    Enter keeps the one playing. Then loops it during the animation."""
    if not uri.startswith("spotify:track:"):
        return  # albums/playlists just play normally
    duration = _current_track_duration(uri)
    if not duration:
        return
    start = pick_start(duration, lambda sec: _spotify(f"set player position to {sec}"))
    if SNIPPET_SECONDS:
        loop_snippet(uri, start, SNIPPET_SECONDS)
        print(f"  Using {fmt(start)} – {fmt(start + SNIPPET_SECONDS)} on a loop.")


def pick_start(duration, preview, length=SNIPPET_SECONDS):
    """Instagram-style picker shared by Spotify and audio files.
    preview(sec) starts playing from `sec`. Returns the chosen start second."""
    options = suggestions(duration, length)
    start = options[SUGGESTED][1]
    preview(start)

    print(f"\nWhich part of the song do you want to use? (length {fmt(duration)})")
    for i, (label, sec) in enumerate(options, 1):
        star = "  ← playing now ★" if i - 1 == SUGGESTED else ""
        print(f"  {i}. {label:<28} {fmt(sec)}{star}")
    print("You can also type an exact time, e.g. 1:23")
    while True:
        try:
            text = input("Part [Enter = use the one playing]: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text.strip():
            break
        sec = parse_part(text, options, duration)
        if sec is None:
            print("  Didn't get that. Type a number from the list or a time like 1:23.")
            continue
        start = sec
        preview(start)
        print(f"  ▶ Playing from {fmt(start)}. Enter to use this part, or pick another option.")
    return start
