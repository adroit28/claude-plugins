"""Shared helpers for the facts-shorts scripts: paths, channel config, the story file, keys.

A Short lives in <content root>/<slug>/ and is described by story.v<N>.json (schema facts-story/1.0).
The content root is FACTS_DIR, else $CLAUDE_PROJECT_DIR/facts-channel. It holds channel.json (name,
tagline, avatar, voice, style, pace), IDEAS.md (the topic ledger), fonts/ (optional) and cost_log.jsonl.
Scripts take the story path and only ever write inside its folder.
"""
import json, os, pathlib, re, subprocess, sys

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
CONFIG = pathlib.Path.home() / ".config/facts-shorts"
CACHE = pathlib.Path.home() / ".cache/facts-shorts"
W, H = 1080, 1920
FONTS = ["Anton-Regular.ttf", "BarlowCondensed-ExtraBold.ttf", "BarlowCondensed-SemiBold.ttf"]

STYLE = ("AUDIO PROFILE: A 25-year-old Indian guy who runs a popular facts channel. Speaks natural, fast Hinglish, mixing "
         "Hindi and English the way young Indians talk with friends. Bright, warm, slightly husky voice.\n\n"
         "DELIVERY: Super curious and excited, like he just discovered something mind-blowing and can't wait to tell you. "
         "Big hook at the start, quick pace, dramatic pauses before the reveal, playful emphasis on the surprising words. "
         "Smiles while talking. Never sounds like a teacher or a news reader.")
CHANNEL_DEFAULTS = {
    "name": "",                                   # empty: the outro says "Like & Subscribe"
    "tagline": "for more surprising stories",
    "avatar": "☎️",
    "promise": "The surprising story behind things you see every day.",
    "language": "Hinglish in Roman script: mostly English words, light Hindi as glue",
    "length": {"min": 30, "max": 40},
    "voice": "gemini:en-in-commercial-1",
    "pace": 1.0,
    "style": STYLE,
    "timezone": "Asia/Kolkata",
    "categories": ["money/objects", "medicine/science", "superstitions", "words/habits", "India history"],
}


def content_dir(edit_dir=None):
    """FACTS_DIR, else the parent of the edit folder if it holds channel.json, else $CLAUDE_PROJECT_DIR/facts-channel."""
    if os.environ.get("FACTS_DIR"):
        return pathlib.Path(os.environ["FACTS_DIR"]).expanduser().resolve()
    if edit_dir and (pathlib.Path(edit_dir).resolve().parent / "channel.json").exists():
        return pathlib.Path(edit_dir).resolve().parent
    return (pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "facts-channel").resolve()


def channel(root=None):
    """channel.json merged over the defaults."""
    p = (root or content_dir()) / "channel.json"
    user = json.loads(p.read_text()) if p.exists() else {}
    return {**CHANNEL_DEFAULTS, **user}


def fonts_dir(root):
    """Fonts: <root>/fonts, else a sibling shorts/fonts (the football plugins' folder), else FACTS_FONTS."""
    for d in [os.environ.get("FACTS_FONTS"), root / "fonts", root.parent / "shorts" / "fonts"]:
        if d and all((pathlib.Path(d) / f).exists() for f in FONTS):
            return pathlib.Path(d)
    return None


class Story:
    """story.v<N>.json plus the paths derived from it."""

    def __init__(self, path):
        self.path = pathlib.Path(path).resolve()
        if not self.path.exists():
            sys.exit("story not found: %s" % self.path)
        self.data = json.loads(self.path.read_text())
        self.dir = self.path.parent
        self.build = self.dir / "build"
        self.root = content_dir(self.dir)
        m = re.search(r"\.v(\d+)\.json$", self.path.name)
        self.version = self.data.get("version") or (int(m.group(1)) if m else 1)
        self.slug = self.data.get("slug") or self.dir.name

    def p(self, rel):
        """Resolve a story-relative path and refuse anything outside the edit folder."""
        q = (self.dir / rel).resolve()
        if self.dir not in q.parents and q != self.dir:
            sys.exit("refusing path outside the edit folder: %s" % rel)
        return q

    @property
    def mp4(self):
        return self.dir / ("%s_v%d.mp4" % (self.slug, self.version))

    def rendered(self):
        return self.mp4.exists()

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False) + "\n")

    @property
    def lines(self):
        return self.data["narration"]["lines"]

    def script_words(self):
        """[(line_id, index, word)] from each line's caption text."""
        return [(l["id"], i, w) for l in self.lines for i, w in enumerate(l["text"].split())]


def load_env(path):
    out = {}
    p = pathlib.Path(path)
    if p.exists():
        for ln in p.read_text().splitlines():
            if "=" in ln and not ln.lstrip().startswith("#"):
                k, v = ln.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def gemini_key(tier):
    """tier 'free' -> GEMINI_FREE_KEY, 'paid' -> GEMINI_PAID_KEY: env, then ~/.config/facts-shorts/.env,
    then the football-stories .env (same Google project); paid also falls back to gemini-image's key."""
    name = "GEMINI_%s_KEY" % tier.upper()
    files = [CONFIG / ".env", pathlib.Path.home() / ".config/football-stories/.env"]
    if tier == "paid":
        files.append(pathlib.Path.home() / ".config/gemini-image/.env")
    if os.environ.get(name):
        return os.environ[name], None
    for f in files:
        env = load_env(f)
        k = env.get(name) or (env.get("GEMINI_API_KEY") if "gemini-image" in str(f) else None)
        if k:
            return k, f
    return None, None


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0
