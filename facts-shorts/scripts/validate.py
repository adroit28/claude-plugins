#!/usr/bin/env python3
"""Check a facts story file before narration or the video. Exit 1 on any error.

  validate.py <story.vN.json> [--stage script|video]

script stage: schema tag, unique line ids, verify.md next to the story, no sources or URLs in the
story (they live in verify.md), every line whose caption has digits has a `tts` with the number
spelled out, a length estimate inside the channel's 30-40 s, the disclosure line, and warnings for
gimmick phrasing, quote marks around more than a couple of words (paraphrases must not look like
quotes), Devanagari script (narration is Roman-script Hinglish), and lines that are too long.
video stage adds: narration audio and words exist and cover every script word, the anim project
exists, every image in anim/public is logged in src/sources.json with a usable licence.
"""
import argparse, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story, channel

WPS = 2.95     # Short #1: 90 words in 30.5 s of speech at pace 1.0 (en-in-commercial-1, Hinglish)
GIMMICK = [r"shock kar de", r"hil jaoge", r"dimaag hil", r"yakeen nahi hoga", r"you won'?t believe", r"lost an argument",
           r"99% log", r"koi nahi jaanta", r"nobody knows", r"secret jo", r"mind[- ]?blow"]
IMG = (".jpg", ".jpeg", ".png", ".webp")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--stage", choices=["script", "video"], default="script")
    a = ap.parse_args()
    st = Story(a.story); d = st.data; ch = channel(st.root); err, warn = [], []

    if d.get("schema") != "facts-story/1.0": warn.append("schema should be facts-story/1.0")
    if not (st.dir / "verify.md").exists(): err.append("no verify.md next to the story (research writes it; sources live there)")
    raw = json.dumps(d, ensure_ascii=False)
    if re.search(r"https?://", raw): err.append("URL in the story file: sources belong in verify.md / src/sources.json, not the story")
    if d.get("facts"): warn.append("story has a facts list: this channel keeps facts and sources in verify.md")
    ids = [l["id"] for l in st.lines]
    if len(set(ids)) != len(ids): err.append("duplicate line ids")
    for l in st.lines:
        t, s = l["text"], l.get("tts")
        if re.search(r"\d", t) and not s: err.append("line %s has digits in its caption but no tts: spell the number out in tts (\"eighteen seventy-seven\")" % l["id"])
        if s and re.search(r"\d", re.sub(r"<[^>]+>", "", s)): err.append("line %s tts still has digits: write them as spoken words" % l["id"])
        if re.search(r"[ऀ-ॿ]", t + (s or "")): err.append("line %s has Devanagari: narration is Roman-script Hinglish" % l["id"])
        for g in GIMMICK:
            if re.search(g, t, re.I): warn.append("line %s: gimmick phrasing %r (the channel avoids fake shock promises)" % (l["id"], g))
        for q in re.findall(r'"([^"]+)"', t):
            if len(q.split()) > 3: warn.append("line %s: %r is in quote marks: only exact words someone said go in quotes" % (l["id"], q))
        n = len(t.split())
        if n > 22: warn.append("line %s has %d words: split it (one idea per line)" % (l["id"], n))
    n = len(st.script_words()); pace = d["narration"].get("pace", ch["pace"])
    lo, hi = ch["length"]["min"], d.get("length", {}).get("max", ch["length"]["max"])
    est = n / WPS / pace
    print("%d words, estimated %.1f s of speech at pace %g (channel %g-%g s, plus the 3 s card)" % (n, est, pace, lo, hi))
    if est > hi: warn.append("estimated %.1f s: over %g s, cut about %d words" % (est, hi, int((est - hi) * WPS * pace) + 1))
    if est < lo - 4: warn.append("estimated %.1f s: short (the channel runs %g-%g s)" % (est, lo, hi))
    if "AI-generated" not in raw: warn.append('disclosure should say "Narration voice is AI-generated."')

    if a.stage == "video":
        nar = d["narration"]
        for k in ("audio", "words"):
            if not nar.get(k) or not st.p(nar[k]).exists(): err.append("narration.%s missing: run tts.py then segalign.py" % k)
        if nar.get("words") and st.p(nar["words"]).exists():
            got = {(w["line"], w["i"]) for w in json.loads(st.p(nar["words"]).read_text())}
            need = {(l, i) for l, i, _ in st.script_words()}
            if got != need: err.append("words file does not match the script (%d vs %d words): re-run segalign.py" % (len(got), len(need)))
        an = st.dir / d.get("anim", {}).get("dir", "anim")
        if not (an / "src" / "Scene.tsx").exists(): err.append("no anim project: run anim.py init")
        log = st.dir / "src" / "sources.json"
        srcs = json.loads(log.read_text()) if log.exists() else {}
        for p in sorted((an / "public").glob("*")) if an.exists() else []:
            if p.suffix.lower() not in IMG: continue
            e = srcs.get(p.name)
            if not e: err.append("image %s is not logged in src/sources.json (title, page, licence)" % p.name)
            elif e.get("rights") in ("unusable", "doubtful"): err.append("image %s has rights %s" % (p.name, e["rights"]))
            elif e.get("rights") == "cc" and not e.get("attribution"): warn.append("image %s is CC: put its attribution in the description" % p.name)

    for w in warn: print("warn:", w)
    for e in err: print("ERROR:", e)
    print("OK" if not err else "%d error(s)" % len(err))
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
