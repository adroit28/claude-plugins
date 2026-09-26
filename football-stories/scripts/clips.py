#!/usr/bin/env python3
"""Muted footage clips over the card track: build/graphics_v<N>.mp4 -> build/graphics_v<N>_clips.mp4.

  <venv>/bin/python clips.py <story.vN.json> [--plan]

Run after compose.py and before finish.py. compose.py rewrites the timeline, so run this again
after every compose. Each entry in the story's "clips" list puts one window of a source video
into a gold-framed box above the caption band. Narration, captions and audio are untouched
(clips are always muted).

  {"id": "c1", "asset": "src_key", "ss": 298.0, "from": {"line": "L1", "word": 0}, "to": {"line": "L2", "word": 0},
   "crop": "w:h:x:y", "box": "full" | "top" | "bottom" | [x, y, w, h], "slow": 2.0, "pre": "delogo=x=2:y=2:w=560:h=118"}

from / to: a word anchor or a time in seconds. With an anchor, the clip starts or ends
motion.lead s before that word starts; the first word of the script means 0 s. "to": "end"
runs to the end of the video. Anchors follow a new take or pace; seconds don't.
ss: the source time the clip starts at.
slow: 2.0 plays the clip at half speed (good for a banner that is on screen for half a second).
pre: an ffmpeg filter applied to the source first. Use delogo for a logo or score bug that a
crop would cut through.
The crop's aspect ratio should match the box (full 988:888, top/bottom 988:438); a mismatch
is flagged because the clip would be stretched.

--plan prints the windows and warnings without rendering. A render writes the clips into
timeline_v<N>.json, points its "video" at the clips track, and prints CHECK_AT= (the start,
middle and end of every window) for check.py --at.
"""
import argparse, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story, duration

BORDER, GOLD = 6, "0xFFD400"
BOX = {"full": (40, 250, 1000, 900), "top": (40, 250, 1000, 450), "bottom": (40, 700, 1000, 450)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--plan", action="store_true", help="print windows and warnings, render nothing")
    a = ap.parse_args()
    st = Story(a.story); v = st.version
    clips = st.data.get("clips") or sys.exit("the story has no clips")
    tl_p = st.p("build/timeline_v%d.json" % v)
    if not tl_p.exists():
        sys.exit("no build/timeline_v%d.json: run compose.py first" % v)
    tl = json.loads(tl_p.read_text()); total, fps = tl["total"], tl.get("fps", 30)
    lead = st.data.get("motion", {}).get("lead", 0.06)
    words, at = st.words(); first = (words[0]["line"], words[0]["i"])

    def when(x):
        if x == "end": return total
        if isinstance(x, (int, float)): return float(x)
        w = st.anchor(x, at)
        return 0.0 if (w["line"], w["i"]) == first else max(0.0, w["start"] - lead)

    assets, rows, warn = st.data.get("assets", {}), [], []
    for c in clips:
        asset = assets.get(c["asset"]) or sys.exit("clip %s: unknown asset %r" % (c["id"], c["asset"]))
        r = asset.get("rights", {})
        if r.get("class") in (None, "unknown", "doubtful") and not r.get("accepted"):
            sys.exit("clip %s: asset %s has rights class %r and no rights.accepted date (the user's yes for this video)"
                     % (c["id"], c["asset"], r.get("class")))
        t0, t1 = when(c["from"]), min(when(c["to"]), total)
        if t1 - t0 < 0.3:
            sys.exit("clip %s: window %.2f-%.2f s is empty or under 0.3 s" % (c["id"], t0, t1))
        box = c.get("box", "full"); x, y, w, h = BOX[box] if isinstance(box, str) else box
        if not re.fullmatch(r"\d+:\d+:\d+:\d+", c["crop"]):
            sys.exit("clip %s: crop must be w:h:x:y, got %r" % (c["id"], c["crop"]))
        cw, ch = map(int, c["crop"].split(":")[:2])
        if abs(cw / ch - (w - 2 * BORDER) / (h - 2 * BORDER)) > 0.02 * (w - 2 * BORDER) / (h - 2 * BORDER):
            warn.append("clip %s: crop %d:%d does not match the box aspect %d:%d, the picture will be stretched"
                        % (c["id"], cw, ch, w - 2 * BORDER, h - 2 * BORDER))
        slow = float(c.get("slow", 1.0)); src = st.p(asset["path"])
        if not src.exists():
            sys.exit("clip %s: source %s not found" % (c["id"], asset["path"]))
        end = c["ss"] + (t1 - t0) / slow; src_len = duration(src)
        if end > src_len + 0.05:
            warn.append("clip %s: needs the source up to %.2f s but it is %.2f s long" % (c["id"], end, src_len))
        rows.append({"id": c["id"], "src": src, "asset": c["asset"], "ss": float(c["ss"]), "a": t0, "b": t1,
                     "crop": c["crop"], "box": (x, y, w, h), "slow": slow, "pre": c.get("pre", "")})
    rows.sort(key=lambda r: r["a"])

    def overlap(p, q):
        return p[0] < q[0] + q[2] and q[0] < p[0] + p[2] and p[1] < q[1] + q[3] and q[1] < p[1] + p[3]
    for i, r in enumerate(rows):
        for q in rows[i + 1:]:
            if q["a"] < r["b"] - 0.01 and overlap(r["box"], q["box"]):
                warn.append("clips %s and %s overlap on screen at %.2f s" % (r["id"], q["id"], q["a"]))
    # A whip between two scenes that both sit under footage slides the card text around the box.
    covered = lambda t: any(r["a"] <= t < r["b"] for r in rows)
    for s in tl["scenes"][1:]:
        if covered(s["start"] - 0.05) and covered(s["start"] + 0.25):
            warn.append("scene %s starts at %.2f s with footage on both sides: its whip flashes card text around the box. "
                        "Use one scene under back-to-back clips" % (s["id"], s["start"]))

    for r in rows:
        print("%-4s %6.2f-%6.2f s  %-8s ss %.2f  crop %s  box %s%s%s" % (r["id"], r["a"], r["b"], r["asset"], r["ss"], r["crop"],
              ",".join(map(str, r["box"])), "  slow %g" % r["slow"] if r["slow"] != 1 else "", "  pre " + r["pre"] if r["pre"] else ""))
    for m in warn: print("warn:", m)
    if a.plan:
        return

    gfx, out = st.p("build/graphics_v%d.mp4" % v), st.out("build/graphics_v%d_clips.mp4" % v)
    inputs, fc, last = ["-i", str(gfx)], [], "[0:v]"
    for k, r in enumerate(rows, start=1):
        x, y, w, h = r["box"]; pre = r["pre"] + "," if r["pre"] else ""
        inputs += ["-ss", "%.3f" % r["ss"], "-t", "%.3f" % ((r["b"] - r["a"]) / r["slow"]), "-i", str(r["src"])]
        fc.append(("[%d:v]" + pre + "setpts=%.3f*PTS,crop=%s,scale=%d:%d,setsar=1,fps=%d,pad=%d:%d:%d:%d:color=%s,setpts=PTS-STARTPTS+%.3f/TB[c%d]")
                  % (k, r["slow"], r["crop"], w - 2 * BORDER, h - 2 * BORDER, fps, w, h, BORDER, BORDER, GOLD, r["a"], k))
        fc.append("%s[c%d]overlay=%d:%d:eof_action=pass:enable='between(t,%.3f,%.3f)'[v%d]" % (last, k, x, y, r["a"], r["b"] - 0.001, k))
        last = "[v%d]" % k
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc), "-map", last, "-an",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps), str(out)], check=True)
    tl["video"] = str(out.relative_to(st.dir))
    tl["clips"] = [{"id": r["id"], "asset": r["asset"], "start": round(r["a"], 3), "end": round(r["b"], 3), "ss": r["ss"],
                    "crop": r["crop"], "box": list(r["box"]), "slow": r["slow"], "pre": r["pre"]} for r in rows]
    tl_p.write_text(json.dumps(tl, indent=1))
    print("video", out.relative_to(st.dir), "and timeline_v%d.json points at it" % v)
    print("CHECK_AT=" + " ".join("%.2f %.2f %.2f" % (r["a"] + 0.1, (r["a"] + r["b"]) / 2, r["b"] - 0.1) for r in rows))


if __name__ == "__main__":
    main()
