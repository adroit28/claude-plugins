"""Shared helpers for the talking-head-shorts scripts: paths, the edit spec, the venv python.

A Short lives in <content root>/<slug>/ . The content root is THS_DIR, else $CLAUDE_PROJECT_DIR/shorts,
else ./shorts (found by walking up). Everything a script writes goes inside the slug folder:

  <slug>/source.<ext>       symlink or copy of the ORIGINAL video (never an edited cut)
  <slug>/probe.json         intake facts (fps, size, audio, blink frames, crop suggestion)
  <slug>/transcript.json    words with timestamps (Whisper), unclear.json = stretches to ask about
  <slug>/captions.txt       the words the user confirmed, one caption phrase per line
  <slug>/edit.v<N>.json     the edit spec (schema talking-head-shorts/1), the only thing a revision changes
  <slug>/matte/             optional RGBA frames from matte.py
  <slug>/anim/              the generated Remotion project (src/edit.json is a copy of the spec)
  <slug>/<slug>_v<N>.mp4    finished versions, never overwritten
"""
import json, os, pathlib, re, sys

PLUGIN = pathlib.Path(__file__).resolve().parent.parent
CONFIG = pathlib.Path.home() / ".config/talking-head-shorts"
FPS = 30  # Remotion composes at 30 fps; every time in the spec is in SOURCE seconds


def content_dir():
    if os.environ.get("THS_DIR"):
        return pathlib.Path(os.environ["THS_DIR"]).expanduser().resolve()
    cpd = os.environ.get("CLAUDE_PROJECT_DIR")
    if cpd and (pathlib.Path(cpd) / "shorts").is_dir():
        return (pathlib.Path(cpd) / "shorts").resolve()
    here = pathlib.Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / "shorts").is_dir():
            return d / "shorts"
    return (pathlib.Path(cpd or ".") / "shorts").resolve()


def venv_python():
    """The python that has numpy, opencv, onnxruntime, faster-whisper, Pillow (setup.sh makes it)."""
    for c in (os.environ.get("THS_PY"), CONFIG / "venv/bin/python", content_dir() / ".venv/bin/python"):
        if c and pathlib.Path(c).exists():
            return str(c)
    return sys.executable


def spec_versions(folder):
    folder = pathlib.Path(folder)
    out = []
    for p in folder.glob("edit.v*.json"):
        m = re.fullmatch(r"edit\.v(\d+)\.json", p.name)
        if m:
            out.append((int(m.group(1)), p))
    return sorted(out)


def latest_spec(folder):
    v = spec_versions(folder)
    if not v:
        sys.exit("no edit.v<N>.json in %s (run spec.py init first)" % folder)
    return v[-1][1]


def load_spec(path):
    path = pathlib.Path(path)
    if path.is_dir():
        path = latest_spec(path)
    return path, json.loads(path.read_text())


def sec(t):
    return int(round(t * FPS))


def hook_seconds(spec):
    h = spec.get("hook") or {}
    if h.get("kind") in (None, "none"):
        return 0.0
    if h.get("kind") == "cold":
        a, b = h["clip"]
        return round(b - a, 3)
    return float(h.get("seconds", 1.8))


def out_seconds(spec):
    s = spec["source"]
    return hook_seconds(spec) + (s["end"] - s["start"])
