#!/usr/bin/env python3
"""Verify a rendered Short before handing it over.

  check.py <out.mp4> [--every 0.5] [--at 3.3 5.0] [--timeline build/timeline_v2.json]

Prints duration / frames / resolution / size, audio peak and mean, black-frame
runs, and writes a labelled contact sheet (one frame every --every seconds, plus
one frame 0.1 s into every segment when a timeline is given) next to the video
as build/check_<name>.png. Look at that PNG with the Read tool and confirm the
subject is in frame at each cut and every caption is legible before you say the
edit is done. Needs ffmpeg + Pillow.
"""
import argparse, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sheets import probe, frames_at, tile, label

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--every", type=float, default=0.5); ap.add_argument("--at", type=float, nargs="*", default=[])
    ap.add_argument("--timeline", help="build/timeline_vN.json from render.py"); ap.add_argument("--cols", type=int, default=8)
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
    if W / H != 9 / 16 and abs(W / H - 0.5625) > 0.01: warn.append("not 9:16")
    if dur > 35: warn.append("over 35 s (channel rule 13-30 s)")
    if dur < 10: warn.append("under 10 s")
    if peak and float(peak.group(1)) > -1.0: warn.append("peak above -1 dBFS")
    if mean and float(mean.group(1)) < -24: warn.append("quiet: mean below -24 dB")
    if blacks: warn.append("black frames at " + ", ".join("%s-%s" % b for b in blacks))
    tl = json.load(open(a.timeline)) if a.timeline else None
    if tl and abs(tl["total"] - dur) > 0.2: warn.append("duration %.2f differs from planned %.2f" % (dur, tl["total"]))
    print("  " + ("WARN: " + "; ".join(warn) if warn else "no warnings"))
    times = a.at or [round(k * a.every, 3) for k in range(int(dur / a.every) + 1) if k * a.every < dur]
    frames = frames_at(a.video, times, 240)
    if tl:
        cut_t = [min(r["start"] + 0.1, dur - 0.05) for r in tl["segments"]]
        cuts = frames_at(a.video, cut_t, 240)
        for fr, r in zip(cuts, tl["segments"]): label(fr, "%d %s %s" % (r["i"], r["type"], r["label"]), 20)
        frames += cuts
    out = os.path.join(os.path.dirname(os.path.abspath(a.video)), "build", "check_%s.png" % os.path.splitext(os.path.basename(a.video))[0])
    os.makedirs(os.path.dirname(out), exist_ok=True); tile(frames, a.cols, out); print("  sheet:", out)

if __name__ == "__main__":
    main()
