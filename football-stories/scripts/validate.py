#!/usr/bin/env python3
"""Check a story file before narration or build. Exit 1 on any error.

  validate.py <story.vN.json> [--stage script|build]

script stage (after research): schema tag, facts have sources, every line cites existing facts
(or is marked "no_claim": true, e.g. "Remember the name."), no duplicate ids, word-count estimate
for 20-30 s at the story's pace (up to "length": {"max": 40} when the user asked for a longer cut),
disclosure note present.
build stage adds: scene templates exist, step anchors resolve and run in word order, hits anchor
to real words, every asset has a known rights class (doubtful/unknown are errors unless the
scene does not use them), a music bed is licensed or CC, and every clip has a video source with
the user's rights.accepted date (when doubtful/unknown), a w:h:x:y crop and anchors that exist.
"""
import argparse, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story

WPS = 2.7          # Gemini en-in-tutor-1: 78 words in 27 s (Satpayev), 97 words with pauses in 37.8 s (Ronaldo v Haaland)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--stage", choices=["script", "build"], default="script")
    a = ap.parse_args()
    st = Story(a.story); d = st.data; err, warn = [], []

    if d.get("schema") != "football-story/1.0": warn.append("schema should be football-story/1.0")
    facts = {f["id"]: f for f in d.get("facts", [])}
    if len(facts) != len(d.get("facts", [])): err.append("duplicate fact ids")
    for f in facts.values():
        if not f.get("sources"): err.append("fact %s has no source" % f["id"])
        if len(f.get("sources", [])) < 2 and f.get("confidence") != "high": warn.append("fact %s: one source and confidence %r" % (f["id"], f.get("confidence")))
        if not f.get("signed_off"): warn.append("fact %s not signed off by the user yet" % f["id"])
    ids = [l["id"] for l in st.lines]
    if len(set(ids)) != len(ids): err.append("duplicate line ids")
    for l in st.lines:
        cited = l.get("facts") or []
        if not cited and not l.get("no_claim"): err.append("line %s makes a claim with no fact id (cite facts or mark no_claim)" % l["id"])
        for fid in cited:
            if fid not in facts: err.append("line %s cites unknown fact %s" % (l["id"], fid))
    n = len(st.script_words()); pace = d["narration"].get("pace", 0.93)
    est = n / WPS / pace + 0.75
    cap = d.get("length", {}).get("max", 30)
    print("%d words, estimated %.1f s at pace %g (limit %g s)" % (n, est, pace, cap))
    if est > cap: warn.append("estimated %.1f s: over %g s, cut about %d words" % (est, cap, int((est - cap) * WPS * pace) + 1))
    if cap > 40: warn.append("length.max %g: the channel's Shorts over 40 s never cleared 100 views" % cap)
    if est < 18: warn.append("estimated %.1f s: short for a story (target 20-30 s)" % est)
    if "AI-generated" not in json.dumps(d.get("disclosure", {})): warn.append('disclosure.description_note should say "Narration voice is AI-generated."')

    if a.stage == "build":
        from cards import TEMPLATES
        assets = d.get("assets", {})
        for k, v in assets.items():
            cls = v.get("rights", {}).get("class")
            if cls not in ("own", "cc", "licensed", "doubtful", "unknown"): err.append("asset %s: rights class missing or invalid (%r)" % (k, cls))
        words = {(w, i) for w, i, _ in st.script_words()}
        prev = None
        for sc in d.get("scenes", []):
            if sc.get("template") not in TEMPLATES: err.append("scene %s: unknown template %r" % (sc.get("id"), sc.get("template")))
            if sc.get("photo"):
                cls = assets.get(sc["photo"], {}).get("rights", {}).get("class", "unknown")
                if cls in ("doubtful", "unknown"): err.append("scene %s uses %s with rights class %s" % (sc["id"], sc["photo"], cls))
            for s in sc.get("steps", []):
                an = s["at"]; line = an["line"]
                i = an.get("word", 0)
                if i < 0: i += len(next((l["text"] for l in st.lines if l["id"] == line), "").split())
                if (line, i) not in words: err.append("scene %s: anchor %s word %s does not exist" % (sc["id"], line, an.get("word")))
                elif prev and (ids.index(line), i) < prev: err.append("scene %s: anchor %s:%d is before the previous step" % (sc["id"], line, i))
                else: prev = (ids.index(line), i)
        for h in d.get("audio", {}).get("hits", []):
            if (h["at"]["line"], h["at"].get("word", 0)) not in words: err.append("hit anchor %s does not exist" % h["at"])
        for c in d.get("clips", []):
            src = assets.get(c.get("asset"), {}); r = src.get("rights", {})
            if src.get("kind") != "video": err.append("clip %s: asset %r is not a video asset" % (c.get("id"), c.get("asset")))
            if r.get("class") in (None, "unknown", "doubtful") and not r.get("accepted"):
                err.append("clip %s: %s needs rights.accepted (date of the user's yes for this video)" % (c.get("id"), c.get("asset")))
            if not re.fullmatch(r"\d+:\d+:\d+:\d+", str(c.get("crop", ""))): err.append("clip %s: crop must be w:h:x:y" % c.get("id"))
            for k in ("from", "to"):
                an = c.get(k)
                if isinstance(an, dict):
                    i = an.get("word", 0)
                    if i < 0: i += len(next((l["text"] for l in st.lines if l["id"] == an["line"]), "").split())
                    if (an["line"], i) not in words: err.append("clip %s: %s anchor %s does not exist" % (c.get("id"), k, an))
                elif not (isinstance(an, (int, float)) or an == "end"): err.append("clip %s: %s must be an anchor, seconds or \"end\"" % (c.get("id"), k))
        bed = d.get("audio", {}).get("bed")
        if bed and assets.get(bed["asset"], {}).get("rights", {}).get("class") not in ("licensed", "cc", "own"):
            err.append("music bed %s is not licensed/CC/own" % bed["asset"])

    for w in warn: print("warn:", w)
    for e in err: print("ERROR:", e)
    print("OK" if not err else "%d error(s)" % len(err))
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
