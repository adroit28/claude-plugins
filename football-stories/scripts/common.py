"""Shared helpers for the football-stories scripts: paths, the story file, word anchors, keys.

A Short lives in <shorts>/<slug>/ and is described by story.v<N>.json (a subset of the
football-story/1.0 schema). Scripts take the story path and only ever write inside its folder.
"""
import json, os, pathlib, re, sys

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
CONFIG = pathlib.Path.home() / ".config/football-stories"
CACHE = pathlib.Path.home() / ".cache/football-stories"
CHROME = os.environ.get("FS_CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
W, H = 1080, 1920


def shorts_dir(edit_dir=None):
    """FOOTBALL_SHORTS_DIR, else the parent of the edit folder if it holds fonts/, else $CLAUDE_PROJECT_DIR/shorts."""
    if os.environ.get("FOOTBALL_SHORTS_DIR"):
        return pathlib.Path(os.environ["FOOTBALL_SHORTS_DIR"]).resolve()
    if edit_dir and (pathlib.Path(edit_dir).resolve().parent / "fonts").is_dir():
        return pathlib.Path(edit_dir).resolve().parent
    return (pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "shorts").resolve()


class Story:
    """story.v<N>.json plus the paths derived from it."""

    def __init__(self, path):
        self.path = pathlib.Path(path).resolve()
        if not self.path.exists():
            sys.exit("story not found: %s" % self.path)
        self.data = json.loads(self.path.read_text())
        self.dir = self.path.parent
        self.build = self.dir / "build"
        self.shorts = shorts_dir(self.dir)
        self.fonts = self.shorts / "fonts"
        m = re.search(r"\.v(\d+)\.json$", self.path.name)
        self.version = self.data.get("version") or (int(m.group(1)) if m else 1)
        self.slug = self.data.get("slug") or self.dir.name

    # ---------- paths
    def p(self, rel):
        """Resolve a story-relative path and refuse anything outside the edit folder."""
        q = (self.dir / rel).resolve()
        if self.dir not in q.parents and q != self.dir:
            sys.exit("refusing path outside the edit folder: %s" % rel)
        return q

    def out(self, rel):
        q = self.p(rel)
        q.parent.mkdir(parents=True, exist_ok=True)
        return q

    @property
    def mp4(self):
        return self.dir / ("%s_v%d.mp4" % (self.slug, self.version))

    def rendered(self):
        return self.mp4.exists()

    def save(self):
        self.path.write_text(json.dumps(self.data, indent=1, ensure_ascii=False) + "\n")

    # ---------- narration
    @property
    def lines(self):
        return self.data["narration"]["lines"]

    def script_words(self):
        """[(line_id, index, word)] from each line's caption text."""
        return [(l["id"], i, w) for l in self.lines for i, w in enumerate(l["text"].split())]

    def words(self):
        """Aligned words (build/words*.json) as {(line, i): {w, start, end}}."""
        rel = self.data["narration"].get("words")
        if not rel:
            sys.exit("no aligned words yet: run align.py on this story")
        ws = json.loads(self.p(rel).read_text())
        return ws, {(w["line"], w["i"]): w for w in ws}

    def anchor(self, a, at):
        """{line, word} -> the aligned word dict; negative word counts from the end of the line."""
        line, i = a["line"], a.get("word", 0)
        if i < 0:
            n = len(next(l for l in self.lines if l["id"] == line)["text"].split())
            i += n
        if (line, i) not in at:
            sys.exit("anchor %s word %s does not exist in the script" % (line, a.get("word", 0)))
        return at[(line, i)]


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
    """tier 'free' -> GEMINI_FREE_KEY; 'paid' -> GEMINI_PAID_KEY, falling back to gemini-image's key."""
    env = load_env(CONFIG / ".env")
    if tier == "free":
        return os.environ.get("GEMINI_FREE_KEY") or env.get("GEMINI_FREE_KEY"), CONFIG / ".env"
    k = os.environ.get("GEMINI_PAID_KEY") or env.get("GEMINI_PAID_KEY")
    if k:
        return k, CONFIG / ".env"
    other = pathlib.Path.home() / ".config/gemini-image/.env"
    k = load_env(other).get("GEMINI_API_KEY")
    return k, other if k else None


def duration(path):
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return float(out) if out else 0.0
