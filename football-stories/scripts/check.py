#!/usr/bin/env python3
"""Verify a rendered story Short before handing it over, or compare it with another version.

  check.py <out.mp4> [--timeline build/timeline_v1.json] [--every 0.5]
  check.py <new.mp4> --ref <old.mp4> [--at 3.3 7.0] [--every 1.0]

Prints resolution, fps, duration, frame count, size, audio peak / mean / integrated loudness and
black-frame runs, with warnings against the channel rules (20-30 s, or the story's length.max from
the timeline; peak <= -1 dB). Writes a
labelled contact sheet to build/check_<name>.png (one frame every --every seconds, plus one frame
per scene when a timeline is given).

With --ref: per-frame SSIM and PSNR over the whole video (needs equal size), duration / frame /
loudness differences, and a side-by-side sheet build/compare_<new>_vs_<ref>.png (ref left, new
right) at --at times or every --every seconds. Read the sheets with the Read tool before you say
the video is done or the fix is in.
"""
import argparse, json, math, os, re, subprocess, sys, tempfile
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def probe(v):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", v], capture_output=True, text=True)
    j = json.loads(p.stdout); s = j["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(j["format"]["duration"])

def nframes(v):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
                          "-of", "csv=p=0", v], capture_output=True, text=True).stdout.strip()
    return int(out) if out.isdigit() else -1

def audio_stats(v):
    e = subprocess.run(["ffmpeg", "-v", "info", "-i", v, "-af", "ebur128=framelog=quiet,volumedetect", "-vf", "blackdetect=d=0.25:pic_th=0.98",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    g = lambda pat: (lambda m: float(m.group(1)) if m else None)(re.search(pat, e))
    ints = re.findall(r"I:\s+([-\d.]+) LUFS", e)
    return {"peak": g(r"max_volume: ([-\d.]+)"), "mean": g(r"mean_volume: ([-\d.]+)"), "lufs": float(ints[-1]) if ints else None,
            "blacks": re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", e)}

def label(im, text, size=24):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, size)
    tw = d.textlength(text, font=f); d.rectangle([0, 0, tw + 16, size + 12], fill=(0, 0, 0))
    d.text((8, 4), text, font=f, fill="#FFD400"); return im

def frames_at(v, times, width):
    tmp = tempfile.mkdtemp(); out = []
    for t in times:
        p = os.path.join(tmp, "%08.3f.png" % t)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % t, "-i", v, "-frames:v", "1", "-vf", "scale=%d:-2" % width, p], check=True)
        out.append(Image.open(p).convert("RGB"))
    return out

def tile(frames, cols, out):
    w, h = frames[0].size; rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 4) + 4), "white")
    for i, fr in enumerate(frames): sheet.paste(fr, (4 + (i % cols) * (w + 4), 4 + (i // cols) * (h + 4)))
    sheet.save(out); return out

def ssim(new, ref):
    """Per-frame SSIM and PSNR of new against ref."""
    tmp = tempfile.mkdtemp(); sf, pf = os.path.join(tmp, "ssim.log"), os.path.join(tmp, "psnr.log")
    subprocess.run(["ffmpeg", "-v", "error", "-i", new, "-i", ref, "-lavfi",
                    "[0:v]split[a0][a1];[1:v]split[b0][b1];[a0][b0]ssim=stats_file=%s;[a1][b1]psnr=stats_file=%s" % (sf, pf), "-f", "null", "-"], check=True)
    s = [float(m) for m in re.findall(r"All:([\d.]+)", open(sf).read())]
    p = [float(m) if m != "inf" else 99.0 for m in re.findall(r"psnr_avg:([\d.inf]+)", open(pf).read())]
    return s, p


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--timeline"); ap.add_argument("--every", type=float)
    ap.add_argument("--at", type=float, nargs="*", default=[]); ap.add_argument("--ref"); ap.add_argument("--cols", type=int, default=8)
    a = ap.parse_args()
    W, H, fps, dur = probe(a.video); nb = nframes(a.video); au = audio_stats(a.video)
    print("%s\n  %dx%d @ %.3f fps, %.3f s, %d frames, %.1f MB" % (a.video, W, H, fps, dur, nb, os.path.getsize(a.video) / 1e6))
    print("  audio peak %s dB, mean %s dB, integrated %s LUFS" % (au["peak"], au["mean"], au["lufs"]))
    warn = []
    if abs(W / H - 9 / 16) > 0.01: warn.append("not 9:16")
    tl = json.load(open(a.timeline)) if a.timeline else None
    cap = (tl or {}).get("max_seconds", 30)
    if dur > cap + 0.05: warn.append("over %g s (channel rule 20-30 s, up to 40 s when the user asked for longer; Shorts over 40 s never cleared 100 views)" % cap)
    if dur < 13: warn.append("under 13 s")
    if au["peak"] is not None and au["peak"] > -1.0: warn.append("peak above -1 dBFS")
    if au["mean"] is not None and au["mean"] < -24: warn.append("quiet: mean below -24 dB")
    if au["blacks"]: warn.append("black frames at " + ", ".join("%s-%s" % b for b in au["blacks"]))
    if tl and abs(tl["total"] - dur) > 0.1: warn.append("duration %.2f differs from planned %.2f" % (dur, tl["total"]))
    print("  " + ("WARN: " + "; ".join(warn) if warn else "no warnings"))
    build = os.path.join(os.path.dirname(os.path.abspath(a.video)), "build"); os.makedirs(build, exist_ok=True)
    name = os.path.splitext(os.path.basename(a.video))[0]

    if a.ref:
        rW, rH, rfps, rdur = probe(a.ref); rnb = nframes(a.ref); rau = audio_stats(a.ref)
        print("ref %s\n  %.3f s, %d frames, peak %s dB, mean %s dB, %s LUFS" % (a.ref, rdur, rnb, rau["peak"], rau["mean"], rau["lufs"]))
        d = lambda x, y: None if x is None or y is None else round(x - y, 2)
        print("  diff (new - ref): duration %+.3f s, frames %+d, peak %s dB, mean %s dB, loudness %s LU"
              % (dur - rdur, nb - rnb, d(au["peak"], rau["peak"]), d(au["mean"], rau["mean"]), d(au["lufs"], rau["lufs"])))
        if (W, H) == (rW, rH):
            s, p = ssim(a.video, a.ref)
            worst = sorted(range(len(s)), key=lambda i: s[i])[:5]
            print("  SSIM avg %.4f min %.4f (frames %s)  PSNR avg %.2f dB" % (sum(s) / len(s), min(s),
                  ", ".join("%d@%.2fs=%.3f" % (i, i / fps, s[i]) for i in worst), sum(p) / len(p)))
        times = a.at or [round(k * (a.every or 1.0), 3) for k in range(int(min(dur, rdur) / (a.every or 1.0)) + 1) if k * (a.every or 1.0) < min(dur, rdur) - 0.02]
        pairs = []
        for t, r, n in zip(times, frames_at(a.ref, times, 270), frames_at(a.video, times, 270)):
            im = Image.new("RGB", (r.width * 2 + 4, r.height), "white"); im.paste(r, (0, 0)); im.paste(n, (r.width + 4, 0))
            pairs.append(label(im, "%.2fs  ref | new" % t, 18))
        out = tile(pairs, 4, os.path.join(build, "compare_%s_vs_%s.png" % (name, os.path.splitext(os.path.basename(a.ref))[0])))
        print("  compare sheet:", out); return

    every = a.every or 0.5
    times = a.at or [round(k * every, 3) for k in range(int(dur / every) + 1) if k * every < dur]
    frames = [label(f, "%.2fs" % t) for f, t in zip(frames_at(a.video, times, 240), times)]
    if tl:
        cut = [min(s["start"] + 0.35, dur - 0.05) for s in tl["scenes"]]
        frames += [label(f, "%s %.2fs" % (s["id"], s["start"])) for f, s in zip(frames_at(a.video, cut, 240), tl["scenes"])]
    print("  sheet:", tile(frames, a.cols, os.path.join(build, "check_%s.png" % name)))


if __name__ == "__main__":
    main()
