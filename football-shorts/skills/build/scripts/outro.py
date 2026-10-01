#!/usr/bin/env python3
"""Append the channel's like & subscribe end card to a finished video. Every video the plugins make ends with it.

  outro.py <video.mp4>                   in place (re-run is a no-op: the file is tagged)
  outro.py <video.mp4> --out <new.mp4>   keep the original
  outro.py <video.mp4> --seconds 3.5     longer card (default 3.0, never below 2.5)
  outro.py <video.mp4> --force           add it again even if the file is tagged

The last frame is held and dimmed for the card's length, a white card slides in (channel name, handle,
a thumbs-up that gets tapped and turns blue, a red SUBSCRIBE button that gets pressed with a shine),
and two soft ticks land on the taps. The picture, fps and size of the original are kept; audio gets
silence under the card plus the ticks. Needs Pillow (the plugin venv python) and ffmpeg/ffprobe.
Same look as the 3D explainers' kit/Outro.tsx. One copy of this file lives in each video plugin.
"""
import argparse, glob, json, math, os, shutil, subprocess, sys, tempfile
try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("Pillow missing: run the plugin's setup.sh and use its venv python")

CHANNEL = os.environ.get("OUTRO_CHANNEL", "The Football Adda")
HANDLE = os.environ.get("OUTRO_HANDLE", "@footballaddaclub")
TAG = "like-subscribe-outro"
MIN_S = 2.5
FPS_OUT = 30  # the card is drawn at this rate; ffmpeg resamples it to the video's fps
S = 2         # supersampling for the card sprite


def sh(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    num, den = v["avg_frame_rate"].split("/")
    fps = float(num) / float(den) if float(den) else 25.0
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": fps, "dur": float(j["format"]["duration"]),
            "audio": any(s["codec_type"] == "audio" for s in j["streams"]),
            "tagged": TAG in (j["format"].get("tags", {}).get("comment", "") or "")}


# ---------- fonts: the channel's own (shorts/fonts), else system fallbacks
def font_dirs():
    out = []
    for base in (os.environ.get("FOOTBALL_SHORTS_DIR"), os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", ""), "shorts") if os.environ.get("CLAUDE_PROJECT_DIR") else None,
                 os.path.join(os.getcwd(), "shorts")):
        if base: out.append(os.path.join(base, "fonts"))
    return out


def find_font(names, fallbacks):
    for d in font_dirs():
        for n in names:
            p = os.path.join(d, n)
            if os.path.exists(p): return p
    for p in fallbacks:
        if os.path.exists(p): return p
    return None


F_BOLD = find_font(["BarlowCondensed-ExtraBold.ttf", "Anton-Regular.ttf"],
                   ["/System/Library/Fonts/Supplemental/Impact.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"])
F_SEMI = find_font(["BarlowCondensed-SemiBold.ttf"], ["/System/Library/Fonts/Supplemental/Arial Bold.ttf"])


def font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


# ---------- keyframes and easing
def kf(u, keys):
    """Piecewise-linear [(t, v), ...], clamped at both ends."""
    if u <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if u <= t1: return v0 + (v1 - v0) * (u - t0) / (t1 - t0)
    return keys[-1][1]


def out_back(x, s=1.8):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def out_quad(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 2


# ---------- the card, drawn at S x its size
CW, CH = 880, 344        # card size in px at 1x
PAD_X, PAD_Y, GAP = 40, 34, 28
STRIP_W, STRIP_H = 1080, 560


def thumb(d, cx, cy, size, color):
    k = size / 48.0
    ox, oy = cx - 24 * k, cy - 24 * k
    P = lambda pts: [(ox + x * k, oy + y * k) for x, y in pts]
    d.rounded_rectangle([ox + 4 * k, oy + 20 * k, ox + 13 * k, oy + 42 * k], radius=2 * k, fill=color)
    d.polygon(P([(16, 22), (23.5, 8.5), (25.5, 5.8), (28.8, 5.6), (31.6, 7.6), (32, 10.4), (29.4, 18.5), (39.5, 18.5),
                 (43, 19.6), (43.9, 22.2), (41.3, 37.6), (39.6, 41), (36.2, 42), (16, 42)]), fill=color)


def ball(d, cx, cy, r):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill="white", outline="#111", width=max(2, int(r * 0.08)))
    pent = [(cx + r * 0.36 * math.sin(math.radians(a)), cy - r * 0.36 * math.cos(math.radians(a))) for a in range(0, 360, 72)]
    d.polygon(pent, fill="#111")
    for a in range(0, 360, 72):
        s, c = math.sin(math.radians(a)), -math.cos(math.radians(a))
        d.line([(cx + r * 0.36 * s, cy + r * 0.36 * c), (cx + r * 0.7 * s, cy + r * 0.7 * c)], fill="#111", width=max(2, int(r * 0.08)))
        d.ellipse([cx + r * 0.8 * s - r * 0.14, cy + r * 0.8 * c - r * 0.14, cx + r * 0.8 * s + r * 0.14, cy + r * 0.8 * c + r * 0.14], fill="#111")


def spaced(d, xy_center, text, fnt, fill, tracking):
    widths = [d.textlength(ch, font=fnt) for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = xy_center[0] - total / 2
    asc, desc = fnt.getmetrics() if hasattr(fnt, "getmetrics") else (0, 0)
    y = xy_center[1] - (asc + desc) / 2
    for ch, w in zip(text, widths):
        d.text((x, y), ch, font=fnt, fill=fill)
        x += w + tracking


def card(u):
    """RGBA sprite of the card at time u (seconds into the card), CW*S x CH*S, with its own animation state."""
    im = Image.new("RGBA", (CW * S, CH * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, CW * S - 1, CH * S - 1], radius=52 * S, fill=(255, 255, 255, 247))
    # row 1: avatar + names
    ay = (PAD_Y + 62) * S
    d.ellipse([PAD_X * S, ay - 62 * S, (PAD_X + 124) * S, ay + 62 * S], fill="#0b1a35")
    ball(d, (PAD_X + 62) * S, ay, 52 * S)
    tx = (PAD_X + 124 + 28) * S
    d.text((tx, ay - 62 * S + 2 * S), CHANNEL, font=font(F_BOLD, 66 * S), fill="#111")
    d.text((tx, ay + 6 * S), HANDLE, font=font(F_SEMI, 44 * S), fill="#606060")
    # row 2: like + subscribe
    ry = (PAD_Y + 124 + GAP + 62) * S
    liked = u >= 0.62
    ts = kf(u, [(0.15, 0), (0.32, 1.2), (0.42, 1), (0.56, 1), (0.62, 0.85), (0.72, 1.12), (0.84, 1)])
    if ts > 0.02:
        r = 62 * S * ts
        cx = (PAD_X + 62) * S
        d.ellipse([cx - r, ry - r, cx + r, ry + r], fill="#1e7cff" if liked else "#ececec")
        thumb(d, cx, ry, 66 * S * ts, "white" if liked else "#111")
    sx0 = (PAD_X + 124 + 26) * S
    sx1 = (CW - PAD_X) * S
    breathe = 1 + 0.018 * math.sin((u - 1.3) * 5.0) if u > 1.3 else 1
    ss = (kf(u, [(0.28, 0), (0.46, 1.12), (0.56, 1)]) if u < 0.56 else 1) * kf(u, [(0.82, 1), (0.9, 0.92), (1.02, 1.06), (1.12, 1)]) * breathe
    if ss > 0.02:
        cxm, w, h = (sx0 + sx1) / 2, (sx1 - sx0) * ss, 124 * S * ss
        pill = Image.new("RGBA", (int(w), int(h)), (0, 0, 0, 0))
        pd = ImageDraw.Draw(pill)
        pd.rounded_rectangle([0, 0, w - 1, h - 1], radius=h / 2, fill="#ff0000")
        spaced(pd, (w / 2, h / 2), "SUBSCRIBE", font(F_BOLD, int(70 * S * ss)), "white", 4 * S * ss)
        shine = kf(u, [(0.9, -30), (1.25, 130)])
        if 0.9 <= u <= 1.25:
            band = Image.new("RGBA", pill.size, (0, 0, 0, 0))
            bx, bw = w * shine / 100.0, w * 0.18
            ImageDraw.Draw(band).polygon([(bx + h * 0.2, 0), (bx + bw + h * 0.2, 0), (bx + bw - h * 0.2, h), (bx - h * 0.2, h)], fill=(255, 255, 255, 115))
            band.putalpha(Image.composite(band.getchannel("A"), Image.new("L", pill.size, 0), pill.getchannel("A")))
            pill = Image.alpha_composite(pill, band)
        im.alpha_composite(pill, (int(cxm - w / 2), int(ry - h / 2)))
    return im


_SHADOW = None


def strip(u):
    """One 1080x560 RGBA frame: the card (slide-in, scale, opacity applied) over its drop shadow."""
    global _SHADOW
    out = Image.new("RGBA", (STRIP_W, STRIP_H), (0, 0, 0, 0))
    op = min(max(u / 0.12, 0), 1)
    if op <= 0: return out
    sc = 0.7 + 0.3 * out_back(u / 0.28)
    dy = 70 * (1 - out_back(u / 0.28))
    sprite = card(u).resize((int(CW * sc), int(CH * sc)), Image.LANCZOS)
    if _SHADOW is None:
        sh_ = Image.new("RGBA", (CW + 160, CH + 160), (0, 0, 0, 0))
        ImageDraw.Draw(sh_).rounded_rectangle([80, 104, 80 + CW, 104 + CH], radius=52, fill=(0, 0, 0, 115))
        _SHADOW = sh_.filter(ImageFilter.GaussianBlur(28))
    sw = _SHADOW.resize((int((CW + 160) * sc), int((CH + 160) * sc)), Image.LANCZOS)
    cx, cy = STRIP_W / 2, STRIP_H / 2 + dy
    out.alpha_composite(sw, (int(cx - sw.width / 2), int(cy - sw.height / 2)))
    out.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))
    if op < 1: out.putalpha(out.getchannel("A").point(lambda a: int(a * op)))
    return out


def append_outro(src, dst=None, seconds=3.0, force=False):
    """Append the end card to src (written to dst, default in place). Returns the card length added (0 if already there)."""
    seconds = max(float(seconds), MIN_S)
    info = probe(src)
    if info["tagged"] and not force:
        print("outro: %s already ends with the like & subscribe card, left as is" % src)
        return 0.0
    dst = dst or src
    D = info["dur"]
    # the card starts exactly one frame after the last picture so the held frame is never dropped
    tmp = tempfile.mkdtemp(prefix="outro_")
    try:
        n = int(round(seconds * FPS_OUT))
        for i in range(n):
            strip(i / FPS_OUT).save(os.path.join(tmp, "f_%03d.png" % i))
        total = D + seconds
        # card geometry: centred horizontally, lower third (below the subject, where captions sit)
        y0 = int(info["h"] * 0.68) - STRIP_H // 2
        x0 = (info["w"] - STRIP_W) // 2
        fc = ("[0:v]tpad=stop_mode=clone:stop_duration=%.3f,eq=brightness=-0.16:enable='gte(t,%.3f)'[bg];"
              "[1:v]format=rgba,setpts=PTS-STARTPTS+%.3f/TB[card];"
              "[bg][card]overlay=%d:%d:eof_action=pass:format=auto,format=yuv420p[v];" % (seconds, D, D, x0, y0))
        inputs = ["-i", src, "-framerate", str(FPS_OUT), "-i", os.path.join(tmp, "f_%03d.png")]
        # audio: the original, silence to the end, two soft ticks on the taps (like at 0.62 s, subscribe at 0.95 s)
        if info["audio"]:
            fc += "[0:a]apad=whole_dur=%.3f[a0];" % total
        else:
            inputs += ["-f", "lavfi", "-t", "%.3f" % total, "-i", "anullsrc=r=48000:cl=stereo"]
            fc += "[2:a]anull[a0];"
        k = 3 if not info["audio"] else 2
        mix = ["[a0]"]
        for j, (at, f) in enumerate(((0.62, 1250), (0.95, 880))):
            inputs += ["-f", "lavfi", "-t", "0.3", "-i", "sine=f=%d:d=0.12" % f]
            ms = int((D + at) * 1000)
            fc += "[%d:a]afade=t=out:st=0.03:d=0.09,volume=0.22,adelay=%d|%d[t%d];" % (k + j, ms, ms, j)
            mix.append("[t%d]" % j)
        fc += "%samix=inputs=%d:duration=first:normalize=0[a]" % ("".join(mix), len(mix))
        tmp_out = os.path.join(tmp, "out.mp4")
        sh(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", "%g" % round(info["fps"], 3),
            "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-metadata", "comment=" + TAG,
            "-movflags", "+faststart", "-t", "%.3f" % total, tmp_out])
        shutil.move(tmp_out, dst)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("outro: added %.1f s like & subscribe card -> %s (%.2f s total)" % (seconds, dst, D + seconds))
    return seconds


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--out"); ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    append_outro(a.video, a.out, a.seconds, a.force)


if __name__ == "__main__":
    main()
