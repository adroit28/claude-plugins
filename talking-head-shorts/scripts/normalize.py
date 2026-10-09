#!/usr/bin/env python3
"""Multi-clip step 1: normalise every take to 1080x1920 / CFR 30 and split out the audio.

  normalize.py <slug folder> [--only a,b] [--no-sharpen] [--force] [--fit cover|crop|blurfill] [--cx 0.5]

For every video in <slug>/clips/ (mp4 mov m4v mkv) writes
  <slug>/norm/<name>.mp4       video only, 30 fps, 1080x1920, libx264 crf 14 (lanczos; a light unsharp only when upscaled > 1.3x)
  <slug>/audio/<name>.wav      48 kHz mono 16-bit, untouched (the voice is cut from these)
  <slug>/audio16/<name>.wav    16 kHz mono (locate.py / whisper)
A source that is not about 9:16 is NEVER cropped silently: the script prints its size and stops until the
user picks --fit (cover = scale to fill and centre-crop, crop = same but centred at --cx of the width,
blurfill = whole picture over a blurred copy of itself). Existing outputs are skipped unless --force.
"""
import argparse, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import content_dir  # noqa: E402

EXTS = {".mp4", ".mov", ".m4v", ".mkv"}
W, H = 1080, 1920


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in j["streams"])
    w, h = int(v["width"]), int(v["height"])
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    if abs(rot) % 180 == 90:  # ffmpeg autorotates, so the picture it hands out is swapped
        w, h = h, w
    n, d = v["avg_frame_rate"].split("/")
    return w, h, (float(n) / float(d) if float(d) else 30.0), has_audio


def vfilter(w, h, fit, cx, sharpen):
    up = W / w if abs(w / h - 9 / 16) < 0.03 else max(W / w, H / h)
    if fit == "blurfill":
        f = ("split[a][b];[a]scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=40:5[bg];"
             "[b]scale=%d:-2:flags=lanczos[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2" % (W, H, W, H, W))
        up = W / w
    elif fit in ("cover", "crop"):
        c = cx if fit == "crop" else 0.5
        f = "scale=%d:%d:force_original_aspect_ratio=increase:flags=lanczos,crop=%d:%d:'min(max(iw*%.3f-%d,0),iw-%d)':(ih-%d)/2" % (W, H, W, H, c, W // 2, W, H)
    else:
        f = "scale=%d:%d:flags=lanczos" % (W, H)
    sharp = sharpen and up > 1.3
    if sharp:
        f += ",unsharp=5:5:0.6:5:5:0.0"
    return f + ",fps=30,format=yuv420p", up, sharp


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--only", default=""); ap.add_argument("--no-sharpen", action="store_true")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--fit", choices=["cover", "crop", "blurfill"])
    ap.add_argument("--cx", type=float, default=0.5)
    a = ap.parse_args()
    root = pathlib.Path(a.folder).expanduser()
    if not root.is_absolute() and not root.exists():
        root = content_dir() / a.folder
    root = root.resolve()
    only = {s.strip() for s in a.only.split(",") if s.strip()}
    clips = [p for p in sorted((root / "clips").glob("*")) if p.suffix.lower() in EXTS and (not only or p.stem in only)]
    if not clips:
        sys.exit("no videos in %s/clips" % root)
    info = {p: probe(p) for p in clips}
    bad = [(p, i) for p, i in info.items() if abs(i[0] / i[1] - 9 / 16) >= 0.03 and not a.fit]
    if bad:
        for p, i in bad:
            print("NOT 9:16: %s is %dx%d" % (p.name, i[0], i[1]))
        sys.exit("ASK the user how to fit these (cover = crop to fill, crop = crop around --cx, blurfill = blurred sides), then rerun with --fit.")
    for d in ("norm", "audio", "audio16"):
        (root / d).mkdir(exist_ok=True)
    for p, (w, h, fps, has_audio) in info.items():
        n = p.stem
        vf, up, sharp = vfilter(w, h, a.fit, a.cx, not a.no_sharpen)
        out = root / "norm" / (n + ".mp4")
        if a.force or not out.exists():
            if "blurfill" == a.fit and "[a]" in vf:
                ff("-i", str(p), "-an", "-filter_complex", vf.replace("split[a][b]", "[0:v]split[a][b]", 1), "-r", "30",
                   "-c:v", "libx264", "-crf", "14", "-preset", "fast", "-pix_fmt", "yuv420p", str(out))
            else:
                ff("-i", str(p), "-an", "-vf", vf, "-r", "30", "-c:v", "libx264", "-crf", "14", "-preset", "fast",
                   "-pix_fmt", "yuv420p", str(out))
        status = "written" if a.force or not out.exists() else "kept"
        if has_audio:
            for sub, rate in (("audio", 48000), ("audio16", 16000)):
                o = root / sub / (n + ".wav")
                if a.force or not o.exists():
                    ff("-i", str(p), "-vn", "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", str(o))
        print("%s: %dx%d %.2ffps -> norm/%s.mp4 1080x1920 30fps, upscale x%.2f, %s [%s]"
              % (n, w, h, fps, n, up, "sharpened" if sharp else "no sharpen", status))
        if w < 720:
            print("  WARNING soft source (%d px wide): keep punch-in zoom <= 1.2, no tiny text" % w)
        if not has_audio:
            print("  WARNING %s has no audio stream (no audio/ or audio16/ file written)" % p.name)


if __name__ == "__main__":
    main()
