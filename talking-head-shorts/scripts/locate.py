#!/usr/bin/env python3
"""Pre-joined source mode: find each original take's chunks inside the user's joined/cleaned file by cross-correlating audio.

  locate.py <slug folder> --joined NAME [--no-rerun] [--min-score 0.3]

NAME is the joined file's name in clips/ (normalize.py must have run: it writes audio16/<NAME>.wav and audio16/<clip>.wav).
For every voiced chunk of timeline.json whose clip is not NAME, the chunk's audio (16 kHz, pre-emphasised so denoise level
differences matter less) is slid over the joined audio; the best normalised correlation gives its start in the joined file.
Each clip sits at a constant offset (joined time = clip time + offset), so the clip's offset is the score-weighted median of its
chunks; chunks that disagree with it by more than 0.05 s are flagged. Writes offsets.json and combined_map.json, prints the
chunk -> start/end table with NOT FOUND flags (score < --min-score or less than 0.05 above the runner-up elsewhere), then re-runs
timeline.py so every chunk gets vid/ca (snapped to the 30 fps grid): picture AND voice then come from the one joined file.
"""
import argparse, json, pathlib, subprocess, sys, wave
import numpy as np

SR = 16000


def rd(p):
    with wave.open(str(p)) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float64) / 32768


def whiten(x):
    return np.append(x[0], x[1:] - 0.95 * x[:-1])


def xc(a, b):
    """Normalised cross-correlation of template a over b via FFT."""
    n, m = len(b), len(a)
    L = 1 << (n + m).bit_length()
    cc = np.fft.irfft(np.fft.rfft(a[::-1], L) * np.fft.rfft(b, L), L)[m - 1:n]
    c1 = np.cumsum(np.r_[0, b ** 2])
    en = np.sqrt(np.maximum(c1[m:] - c1[:-m], 1e-12))
    return cc / (en * np.sqrt((a ** 2).sum()) + 1e-12)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"); ap.add_argument("--joined", required=True); ap.add_argument("--no-rerun", action="store_true")
    ap.add_argument("--min-score", type=float, default=0.3)
    a = ap.parse_args()
    slug = pathlib.Path(a.slug).expanduser().resolve()
    tl = json.loads((slug / "timeline.json").read_text())
    comb_p = slug / "audio16" / (a.joined + ".wav")
    if not comb_p.exists():
        sys.exit("%s missing: run normalize.py first" % comb_p)
    comb = whiten(rd(comb_p))
    src, res = {}, {}
    for c in tl["chunks"]:
        if not c["voice"] or c["clip"] == a.joined:
            continue
        if c["clip"] not in src:
            p = slug / "audio16" / (c["clip"] + ".wav")
            if not p.exists():
                sys.exit("%s missing: run normalize.py first" % p)
            src[c["clip"]] = whiten(rd(p))
        t = src[c["clip"]][int(c["a"] * SR):int(c["b"] * SR)]
        r = xc(t, comb)
        i = int(np.argmax(r))
        second = float(np.max(np.r_[r[:max(0, i - 8000)], r[i + 8000:]]))
        res[c["id"]] = dict(clip=c["clip"], a=c["a"], b=c["b"], start=round(i / SR, 3), end=round(i / SR + (c["b"] - c["a"]), 3),
                            score=round(float(r[i]), 3), second=round(second, 3))
    offsets, flags = {}, {}
    for clip in {v["clip"] for v in res.values()}:
        rows = [(v["start"] - v["a"], v["score"]) for v in res.values() if v["clip"] == clip and v["score"] >= a.min_score]
        if not rows:
            continue
        o = sorted(rows)
        tot, acc = sum(s for _, s in o), 0.0
        for off, s in o:                                  # score-weighted median
            acc += s
            if acc >= tot / 2:
                offsets[clip] = round(off, 3)
                break
    print("%-5s %-12s %12s %20s  score   2nd  flag" % ("chunk", "clip", "src a-b", "joined start-end"))
    bad = 0
    for k, v in res.items():
        flag = ""
        if v["score"] < a.min_score or v["score"] - v["second"] < 0.05:
            flag = "NOT FOUND"
        elif v["clip"] in offsets and abs(v["start"] - v["a"] - offsets[v["clip"]]) > 0.05:
            flag = "OFFSET DISAGREES (%+.3f s)" % (v["start"] - v["a"] - offsets[v["clip"]])
        bad += bool(flag)
        print("%-5s %-12s %5.2f-%-6.2f   %8.3f-%-9.3f  %.3f %.3f  %s" % (k, v["clip"], v["a"], v["b"], v["start"], v["end"], v["score"], v["second"], flag))
    (slug / "combined_map.json").write_text(json.dumps(res, indent=1))
    (slug / "offsets.json").write_text(json.dumps(offsets, indent=1))
    print("\noffsets (joined = clip + offset): %s" % json.dumps(offsets))
    if bad:
        print("%d chunk(s) flagged: NOT FOUND usually means that stretch was cut out of the joined file or re-ordered; check it by ear/eye before trusting the timeline." % bad)
    if not a.no_rerun and (slug / "timeline.py").exists():
        subprocess.run([sys.executable, str(slug / "timeline.py")], check=True)


if __name__ == "__main__":
    main()
