#!/usr/bin/env python3
"""Verify a rendered Short before handing it over.

  check.py <out.mp4> [--timeline build/timeline_v2.json] [--spec spec.v2.json] [--every 0.5] [--at 3.3 5.0]

Prints duration / frames / resolution / size, audio peak and mean, black-frame
runs, mostly-dark frames (black or letterbox bars filling the picture), and writes
a labelled contact sheet next to the video as build/check_<name>.png. With a
timeline the sheet holds one frame 0.1 s into every segment, one mid-segment frame
for segments over 2 s, and the last frame (about a dozen frames, not one every
0.5 s); without one, a frame every 1 s. --every or --at replace that sampling.
The last line is a verdict: "numbers clean" or "LOOK: <reasons>". Read the sheet on
the first render of a version with new cuts or crops; on a re-render that only moved
captions, timing or audio, read it only when the verdict says LOOK. With --spec (and --timeline) it also scores retention: hook text on the
first frame, the first segment moving (not a still or card), the longest stretch with
no cut, caption change or hit, and whether any sound exists besides silence; and the story spine: FAIL without
`spine`, WARN when the question is not on screen at 0 s, the turn starts outside 60-70 % or the button is not the
last beat, and (with `bpm`) cuts more than 60 ms off the beat grid.
Needs ffmpeg + Pillow.
"""
import argparse, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets import probe, frames_at, tile, label

RET_FAILS = []

def retention(spec, tl, dur, mean):
    """The things that decide whether a Short is swiped away, checked from the spec rather than guessed."""
    ov = spec.get("overlays", []); hits = spec.get("audio", {}).get("hits", []); segs = tl["segments"]
    rows = []
    first = min([o["from"] for o in ov] or [99])
    rows.append(("hook text by 0.1 s", first <= 0.1, "first caption at %.2f s" % first if first < 99 else "no captions"))
    rows.append(("opens on motion", segs[0]["type"] not in ("still", "card"), "first segment: %s %s" % (segs[0]["type"], segs[0]["label"])))
    ev = sorted({0.0, dur} | {r["start"] for r in segs} | {o["from"] for o in ov} | {h["at"] for h in hits})
    gaps = [(b - a, a) for a, b in zip(ev, ev[1:])]; g, at = max(gaps)
    rows.append(("something changes every <= 3 s", g <= 3.0, "longest still stretch %.2f s from %.2f s" % (g, at)))
    rows.append(("length 13-30 s", 13 <= dur <= 30, "%.2f s" % dur))
    heard = bool(spec.get("audio", {}).get("bed")) or bool(hits) or (mean is not None and float(mean.group(1)) > -60)
    rows.append(("has sound", heard, "bed/hits in spec" if heard else "silent: add a bed, hits, or a sound at upload"))
    print("  retention:")
    for name, ok, why in rows: print("    %-4s %-32s %s" % ("ok" if ok else "FAIL", name, why))
    RET_FAILS.extend("retention: " + name for name, ok, _ in rows if not ok)
    print("    loop: compare the last frame with the first on the sheet; the end should cut back into the opening")

def story(spec, tl, dur):
    """Spine (question / turn / button) and, with `bpm`, cuts on the beat grid. A missing spine fails."""
    segs = tl["segments"]; sp = spec.get("spine"); rows = []
    if not sp: rows.append(("FAIL", "spine", "no spine: add question/turn/button (hook-playbook.md, Spine before cuts)"))
    else:
        norm = lambda x: "".join(ch for ch in str(x).upper() if ch.isalnum())
        lines = lambda v: v if isinstance(v, list) else [v] if v else []
        text = lambda o: norm(" ".join(lines(o.get("big")) + lines(o.get("small")) + [l for e in o.get("extra", []) for l in e.get("lines", [])]))
        q = str(sp.get("question", "")); shown = bool(norm(q)) and any(o["from"] <= 0.1 and norm(q) in text(o) for o in spec.get("overlays", []))
        rows.append(("ok" if shown else "WARN", "question on screen at 0 s", repr(q) if shown else "%r not in an overlay starting at 0 s" % q))
        t = sp.get("turn")
        if t is None: rows.append(("WARN", "turn", "no turn beat"))
        elif not 0 <= t < len(segs): rows.append(("FAIL", "turn", "turn=%s is not a segment index" % t))
        else:
            share = segs[t]["start"] / dur
            rows.append(("ok" if 0.6 <= share <= 0.7 else "WARN", "turn at 60-70 %", "segment %d %s starts at %.0f %%" % (t, segs[t]["label"], 100 * share)))
        b = sp.get("button")
        rows.append(("ok" if b == len(segs) - 1 else "WARN", "button is the last beat", "button=%s, last segment %d" % (b, len(segs) - 1)))
    if spec.get("bpm"):
        step = 60.0 / spec["bpm"]; off = spec.get("beat_offset", 0.0)
        bad = ["%.2f" % r["start"] for r in segs[1:] if abs((r["start"] - off + step / 2) % step - step / 2) > 0.06]
        rows.append(("ok" if not bad else "WARN", "cuts on the %g bpm grid" % spec["bpm"], "off by >60 ms at " + ", ".join(bad) if bad else "all cuts within 60 ms"))
    print("  story:")
    for st, name, why in rows: print("    %-4s %-32s %s" % (st, name, why))
    RET_FAILS.extend("story: " + name for st, name, _ in rows if st == "FAIL")

def dark_share(im):
    """Share of the frame that is near-black (letterbox bars, fades, black frames)."""
    h = im.convert("L").resize((64, 114)).histogram()
    return sum(h[:20]) / sum(h)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--every", type=float, default=None); ap.add_argument("--at", type=float, nargs="*", default=[])
    ap.add_argument("--timeline", help="build/timeline_vN.json from render.py"); ap.add_argument("--cols", type=int, default=8)
    ap.add_argument("--spec", help="spec.vN.json: adds the retention checks (needs --timeline)")
    a = ap.parse_args()
    W, H, fps, dur = probe(a.video); size = os.path.getsize(a.video) / 1e6
    nb = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", a.video],
                        capture_output=True, text=True).stdout.strip()
    vd = subprocess.run(["ffmpeg", "-v", "info", "-i", a.video, "-af", "volumedetect", "-vf", "blackdetect=d=0.25:pic_th=0.98", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    peak = re.search(r"max_volume: ([-\d.]+)", vd); mean = re.search(r"mean_volume: ([-\d.]+)", vd)
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", vd)
    print("%s\n  %dx%d @ %.3f fps, %.2f s, %s frames, %.1f MB" % (a.video, W, H, fps, dur, nb, size))
    print("  audio peak %s dB, mean %s dB" % (peak.group(1) if peak else "?", mean.group(1) if mean else "?"))
    warn = []
    tl = json.load(open(a.timeline)) if a.timeline else None
    outro = (tl or {}).get("outro_s", 0.0); body = dur - outro  # the like & subscribe card is not counted in the channel's length rule
    if outro: print("  incl. %.1f s like & subscribe card (content %.2f s)" % (outro, body))
    elif (tl or {}).get("outro_overlay_s"): print("  like & subscribe card overlaid on the last %.1f s (content %.2f s)" % (tl["outro_overlay_s"], dur))
    elif tl is not None: warn.append("no like & subscribe end card: every video must end with one (outro.py)")
    if W / H != 9 / 16 and abs(W / H - 0.5625) > 0.01: warn.append("not 9:16")
    if body > 35: warn.append("over 35 s (channel rule 13-30 s)")
    if body < 10: warn.append("under 10 s")
    if peak and float(peak.group(1)) > -1.0: warn.append("peak above -1 dBFS")
    if mean and float(mean.group(1)) < -24: warn.append("quiet: mean below -24 dB")
    if blacks: warn.append("black frames at " + ", ".join("%s-%s" % b for b in blacks))
    if tl and abs(tl["total"] - body) > 0.2: warn.append("duration %.2f differs from planned %.2f" % (body, tl["total"]))
    print("  " + ("WARN: " + "; ".join(warn) if warn else "no warnings"))
    if a.spec and tl: sp = json.load(open(a.spec)); retention(sp, tl, body, mean); story(sp, tl, body)
    every = a.every or (None if tl else 1.0)
    times = a.at or ([round(k * every, 3) for k in range(int(dur / every) + 1) if k * every < dur] if every else [])
    if tl and not a.at:
        times += [round(r["start"] + r["dur"] / 2, 2) for r in tl["segments"] if r.get("dur", 0) > 2]
        times.append(round(max(dur - 0.08, 0), 2))
    times = sorted(set(times))
    frames = frames_at(a.video, times, 240) if times else []
    if tl:
        cut_t = [min(r["start"] + 0.1, dur - 0.05) for r in tl["segments"]]
        cuts = frames_at(a.video, cut_t, 240)
        for fr, r in zip(cuts, tl["segments"]): label(fr, "%d %s %s" % (r["i"], r["type"], r["label"]), 20)
        pairs = sorted(list(zip(times, frames)) + list(zip(cut_t, cuts)), key=lambda p: p[0])
        times, frames = [p[0] for p in pairs], [p[1] for p in pairs]
    card = lambda t: tl and any(r["type"] == "card" and r["start"] <= t < r["end"] for r in tl["segments"])
    dark = ["%.2f s (%d%%)" % (t, 100 * d) for t, fr in zip(times, frames) if not card(t) for d in [dark_share(fr)] if d > 0.55]
    if dark: warn.append("mostly dark or bars at " + ", ".join(dark))
    out = os.path.join(os.path.dirname(os.path.abspath(a.video)), "build", "check_%s.png" % os.path.splitext(os.path.basename(a.video))[0])
    os.makedirs(os.path.dirname(out), exist_ok=True); tile(frames, a.cols, out); print("  sheet:", out, "(%d frames)" % len(frames))
    fails = RET_FAILS + (["mostly dark frames"] if dark else [])
    print("  verdict: " + ("LOOK: " + "; ".join(warn + [f for f in fails if f not in warn]) if warn or fails else
                         "numbers clean (faces, crops and caption legibility still need eyes on the first render of new cuts)"))

if __name__ == "__main__":
    main()
