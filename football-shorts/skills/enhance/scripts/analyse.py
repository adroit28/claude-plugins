#!/usr/bin/env python3
"""Read a finished clip the user hands over and map its beats, so an edit can be planned on facts.

  analyse.py <video> [--out <edit_dir>/build] [--cut 0.3] [--step 0.25]

Prints and writes <out>/analysis.json:
  - format: size, fps, duration, whether there is an audio track at all
  - picture box: letterbox / pillarbox bars found by cropdetect (a 16:9 broadcast inside a
    vertical upload is common), with the crop to use as `fill.box` in the spec
  - shots: hard cuts found by scene score inside the picture box (bars dilute the score, so the
    box is cropped first), each shot's length and mean motion
  - motion curve per --step seconds; long low-motion stretches are flagged as trim candidates
  - loudness curve per --step (only when there is audio); the loudest windows are usually the
    crowd reacting to the chance, i.e. the moment to freeze or punch in on
and a shot sheet <out>/sheets/<name>_shots.png: first / middle / last frame of every shot,
labelled with shot number and source seconds. Read that PNG before writing a spec.
Needs ffmpeg + Pillow (the build skill's setup.sh venv).
"""
import argparse, json, os, re, statistics, subprocess, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build", "scripts"))
from sheets import probe, frames_at, tile, label

def ff(args):
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True).stderr

def has_audio(v):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", v],
                         capture_output=True, text=True).stdout.strip()
    return bool(out)

def picture_box(v, W, H):
    crops = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", ff(["-i", v, "-vf", "cropdetect=limit=24:round=2:reset=0", "-f", "null", "-"]))
    if not crops: return [W, H, 0, 0]
    best = max(set(crops), key=crops.count)
    return [int(x) for x in best]

def frame_scores(v, box):
    """Per-frame scene score (0-1, how different a frame is from the previous one) inside the picture box."""
    w, h, x, y = box
    err = ff(["-i", v, "-vf", "crop=%d:%d:%d:%d,select='gte(scene,0)',metadata=print:key=lavfi.scene_score" % (w, h, x, y), "-f", "null", "-"])
    ts = [float(t) for t in re.findall(r"pts_time:([\d.]+)", err)]
    sc = [float(s) for s in re.findall(r"lavfi.scene_score=([\d.]+)", err)]
    return list(zip(ts, sc))

def cuts_from(scores, thr, min_gap=0.4):
    """A cut is a frame whose score clears thr, or clears 0.18 while standing well above its neighbours
    (a soft broadcast cut). Inside a busy stretch (a fast pan, or low-frame-rate footage that jumps every
    few frames) only hard cuts count, so pans and gradual transitions stay one shot."""
    cuts = []
    for i, (t, s) in enumerate(scores):
        near = [q for tt, q in scores[max(0, i - 8):i + 9] if tt != t]
        med = statistics.median(near) if near else 0
        busy = sum(q >= 0.12 for tt, q in scores if abs(tt - t) <= 1.0 and tt != t) > 3
        if s >= thr or (not busy and s >= 0.18 and s >= 3 * max(med, 0.02)):
            if not cuts or t - cuts[-1] >= min_gap: cuts.append(round(t, 3))
    return cuts

def curve(scores, dur, step):
    bins = [[] for _ in range(int(dur / step) + 1)]
    for t, s in scores: bins[min(int(t / step), len(bins) - 1)].append(s)
    return [round(statistics.mean(b), 4) if b else 0 for b in bins]

def loudness(v, dur, step):
    err = ff(["-i", v, "-af", "asetnsamples=n=%d,astats=metadata=1:reset=1,ametadata=print:key=lavfi.astats.Overall.RMS_level" % int(48000 * step),
              "-ar", "48000", "-f", "null", "-"])
    vals = [float(x) if x not in ("-inf", "inf") else -90.0 for x in re.findall(r"RMS_level=(-?[\w.]+)", err)]
    return [round(x, 1) for x in vals[:int(dur / step) + 1]]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--out", help="default: ./build next to the video")
    ap.add_argument("--cut", type=float, default=0.3, help="scene score for a hard cut (default 0.3)")
    ap.add_argument("--step", type=float, default=0.25, help="curve resolution in seconds")
    a = ap.parse_args()
    W, H, fps, dur = probe(a.video); audio = has_audio(a.video)
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "build"); os.makedirs(os.path.join(out, "sheets"), exist_ok=True)
    box = picture_box(a.video, W, H); boxed = box[0] * box[1] < 0.9 * W * H
    scores = frame_scores(a.video, box); cuts = cuts_from(scores, a.cut)
    edges = [0.0] + cuts + [round(dur, 3)]
    shots = []
    for k in range(len(edges) - 1):
        s0, s1 = edges[k], edges[k + 1]
        m = [s for t, s in scores if s0 < t < s1]
        shots.append({"shot": k + 1, "from": s0, "to": s1, "dur": round(s1 - s0, 2), "motion": round(statistics.mean(m), 4) if m else 0})
    mot = curve(scores, dur, a.step)
    # low motion = under a third of the clip's median motion for at least 1.5 s
    med = statistics.median([x for x in mot if x > 0] or [0]); slow, run = [], None
    for i, x in enumerate(mot + [99]):
        if x < med / 3:
            run = i if run is None else run
        else:
            if run is not None and (i - run) * a.step >= 1.5: slow.append([round(run * a.step, 2), round(i * a.step, 2)])
            run = None
    loud = loudness(a.video, dur, a.step) if audio else []
    peaks = []
    if loud:
        thr = sorted(loud)[int(len(loud) * 0.9)]
        peaks = [round(i * a.step, 2) for i, x in enumerate(loud) if x >= thr and x > -60]
    res = {"video": os.path.abspath(a.video), "size": [W, H], "fps": fps, "duration": round(dur, 3), "audio": audio,
           "picture_box": box, "letterboxed": boxed, "cuts": cuts, "shots": shots, "step": a.step,
           "motion": mot, "low_motion": slow, "loudness_db": loud, "loud_peaks": peaks}
    json.dump(res, open(os.path.join(out, "analysis.json"), "w"), indent=1)

    print("%s\n  %dx%d @ %.3f fps, %.2f s, audio: %s" % (a.video, W, H, fps, dur, "yes" if audio else "NONE (every sound must come from the edit)"))
    if boxed:
        print("  picture box %dx%d at x=%d y=%d (bars around it): use \"fill\": {\"box\": %s} so the output is not mostly black" % (*box, json.dumps(box)))
    if min(box[0], box[1]) < 540: print("  low resolution picture (%dx%d): punch-ins above ~1.3x will look soft" % (box[0], box[1]))
    print("  %-4s %-7s %-7s %-6s %s" % ("shot", "from", "to", "dur", "motion"))
    for s in shots: print("  %-4d %-7.2f %-7.2f %-6.2f %.3f" % (s["shot"], s["from"], s["to"], s["dur"], s["motion"]))
    if slow: print("  low-motion stretches (trim candidates): " + ", ".join("%.2f-%.2f" % tuple(r) for r in slow))
    if peaks: print("  loudest windows (s): " + ", ".join("%.2f" % p for p in peaks[:12]))

    frames = []
    for s in shots:
        ts = sorted({round(min(s["from"] + 0.1, dur - 0.05), 2), round((s["from"] + s["to"]) / 2, 2), round(max(s["to"] - 0.1, s["from"]), 2)})
        for fr, t in zip(frames_at(a.video, ts, 300), ts): frames.append(label(fr, "shot %d  %.2fs" % (s["shot"], t), 22))
    sheet = os.path.join(out, "sheets", "%s_shots.png" % os.path.splitext(os.path.basename(a.video))[0].replace(" ", "_"))
    tile(frames, 6, sheet); print("  shot sheet:", sheet); print("  analysis:", os.path.join(out, "analysis.json"))

if __name__ == "__main__":
    main()
