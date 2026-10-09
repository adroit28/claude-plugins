#!/usr/bin/env python3
"""Mix the voice, synthesized sfx cues and a low drone under the rendered picture, loudnorm to about -14 LUFS.

  mix.py <slug folder | edit.vN.json> [--raw anim/out/raw_vN.mp4]

Reads the spec (the cue times are in it) and the ORIGINAL video's audio:
  voice   highpass 90 Hz + afftdn (hum/hiss cleanup), the source window, delayed by the hook length
  hook    cold open: the same clip's audio at 0 s; image/slam hook with hook.voice [a, b]: that stretch of the
          source (it may lie outside the window), placed so it ends where the hook ends
  sfx     spec.sfx   [name, source s, vol]  -> output time = hook + (s - window start)
          spec.hook_sfx [name, s into the hook, vol]
  drone   55/82/110 Hz sines, lowpassed, faded in/out, when spec.music.drone
Writes <slug>/build_v<N>.mp4 (picture copied, AAC 192k/48k). Cleaning with Demucs etc. is out of scope.
"""
import argparse, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import hook_seconds, load_spec, out_seconds
from sfx import ensure


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target"); ap.add_argument("--raw")
    a = ap.parse_args()
    specpath, spec = load_spec(pathlib.Path(a.target).expanduser())
    folder = specpath.parent
    v = spec["version"]
    raw = pathlib.Path(a.raw) if a.raw else folder / "anim" / "out" / ("raw_v%d.mp4" % v)
    if not raw.exists():
        sys.exit("%s missing: run build.py --render first" % raw)
    out = folder / ("build_v%d.mp4" % v)
    if out.exists():
        sys.exit("%s exists: versions are never overwritten (bump the spec)" % out)
    s0, s1 = spec["source"]["start"], spec["source"]["end"]
    H = hook_seconds(spec)
    total = out_seconds(spec)
    src = (folder / spec["source"]["file"]).resolve()
    sfx = ensure([c[0] for c in spec["sfx"] + spec["hook_sfx"]], folder / "sfx")

    inp, fc, labels = ["-i", str(raw), "-i", str(src)], [], []
    clean = "highpass=f=90,afftdn=nf=-30"
    fc.append("[1:a]%s,atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[v0]" % (clean, s0, s1, int(H * 1000), int(H * 1000)))
    labels.append("[v0]")
    k = 2
    h = spec["hook"]
    if h["kind"] == "cold":
        a0, b0 = h["clip"]
        fc.append("[1:a]%s,atrim=%.3f:%.3f,asetpts=PTS-STARTPTS[hv]" % (clean, a0, b0)); labels.append("[hv]")
    elif h.get("voice"):
        a0, b0 = h["voice"]
        d = max(0, int((H - (b0 - a0)) * 1000))
        fc.append("[1:a]%s,atrim=%.3f:%.3f,asetpts=PTS-STARTPTS,adelay=%d|%d[hv]" % (clean, a0, b0, d, d)); labels.append("[hv]")
    cues = [(n, H + (t - s0), vol) for n, t, vol in spec["sfx"]] + [(n, t, vol) for n, t, vol in spec["hook_sfx"]]
    for i, (n, at, vol) in enumerate(cues):
        inp += ["-i", str(sfx[n])]
        ms = max(0, int(at * 1000))
        fc.append("[%d:a]volume=%.2f,adelay=%d|%d[s%d]" % (k, vol * 0.55, ms, ms, i))
        labels.append("[s%d]" % i); k += 1
    if spec["music"].get("drone"):
        inp += ["-f", "lavfi", "-t", "%.2f" % (total + 0.1), "-i", "aevalsrc='0.05*sin(2*PI*55*t)+0.03*sin(2*PI*82.4*t)+0.02*sin(2*PI*110.5*t)':s=48000"]
        fc.append("[%d:a]lowpass=f=300,volume=%.2f,afade=t=in:d=1.5,afade=t=out:st=%.2f:d=2.4[drone]" % (k, spec["music"].get("vol", 1.0), max(0, total - 2.43)))
        labels.append("[drone]")
    fc.append("%samix=inputs=%d:duration=longest:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=9,atrim=0:%.3f[a]" % ("".join(labels), len(labels), total))
    cmd = ["ffmpeg", "-v", "error", "-y"] + inp + ["-filter_complex", ";".join(fc), "-map", "0:v", "-map", "[a]",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)]
    subprocess.run(cmd, check=True)
    print("mixed:", out, "(%.2f s, %d sfx cues, drone %s)" % (total, len(cues), bool(spec["music"].get("drone"))))


if __name__ == "__main__":
    main()
