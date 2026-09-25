#!/usr/bin/env python3
"""Contact sheets so the moment and the crop can be chosen by looking at frames.

  sheets.py coarse <video> [--every 4] [--out build/sheets]     one sheet per 100 s, one frame every 4 s
  sheets.py fine   <video> --from 262 --to 272 [--fps 2]          dense sheet of a window
  sheets.py frames <video> --at 263.0 263.5 264.0 [--grid 100]    labelled frames with a pixel grid
  sheets.py compare <out.mp4> --at 3.3 5.0 6.6 ...                same as frames, for a rendered Short

Every frame is stamped with its time in seconds. `frames` also draws a grid every
--grid source pixels with x labels, so a crop can be read straight off the image
(a 9:16 window on 1080p is 608 px wide: crop x = subject centre - 304).
Needs ffmpeg + Pillow (see setup.sh). Look at the PNGs with the Read tool.
"""
import argparse, json, math, os, subprocess, sys, tempfile
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("Pillow missing: run setup.sh and use its venv python")

FONT = os.environ.get("FS_FONT_SMALL", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")

def probe(v):
    p = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=width,height,r_frame_rate:format=duration", "-of", "json", v], capture_output=True, text=True)
    j = json.loads(p.stdout); s = j["streams"][0]; n, d = s["r_frame_rate"].split("/")
    return s["width"], s["height"], float(n) / float(d), float(j["format"]["duration"])

def grab(v, t, w, out):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", v, "-frames:v", "1",
                    "-vf", "scale=%d:-2" % w, out], check=True)

def label(im, text, size=28):
    d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, size)
    tw = d.textlength(text, font=f); d.rectangle([0, 0, tw + 16, size + 12], fill=(0, 0, 0, 200))
    d.text((8, 4), text, font=f, fill="#FFD400"); return im

def tile(frames, cols, out):
    w, h = frames[0].size; rows = math.ceil(len(frames) / cols)
    sheet = Image.new("RGB", (cols * (w + 4) + 4, rows * (h + 4) + 4), "white")
    for i, fr in enumerate(frames): sheet.paste(fr, (4 + (i % cols) * (w + 4), 4 + (i // cols) * (h + 4)))
    sheet.save(out); return out

def frames_at(v, times, width, grid=None, src_w=None):
    tmp = tempfile.mkdtemp(); out = []
    for t in times:
        p = os.path.join(tmp, "%08.2f.png" % t); grab(v, t, width, p); im = Image.open(p).convert("RGB")
        if grid:
            d = ImageDraw.Draw(im); f = ImageFont.truetype(FONT, 14); sc = im.width / src_w
            for gx in range(0, src_w + 1, grid):
                x = gx * sc; d.line([(x, 0), (x, im.height)], fill=(255, 255, 0, 120), width=1)
                d.text((x + 2, im.height - 18), str(gx), font=f, fill="yellow")
            for gy in range(0, int(im.height / sc) + 1, grid):
                y = gy * sc; d.line([(0, y), (im.width, y)], fill=(255, 255, 0, 90), width=1); d.text((2, y + 1), str(gy), font=f, fill="yellow")
        out.append(label(im, "%.2fs" % t))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["coarse", "fine", "frames", "compare"]); ap.add_argument("video")
    ap.add_argument("--every", type=float, default=4); ap.add_argument("--fps", type=float, default=2)
    ap.add_argument("--from", dest="t0", type=float); ap.add_argument("--to", dest="t1", type=float)
    ap.add_argument("--at", type=float, nargs="*", default=[]); ap.add_argument("--grid", type=int, default=100)
    ap.add_argument("--out", default=None, help="output dir (default: <video dir>/../build/sheets)")
    ap.add_argument("--width", type=int, default=None, help="thumbnail width px")
    a = ap.parse_args()
    W, H, fps, dur = probe(a.video)
    base = os.path.splitext(os.path.basename(a.video))[0]
    outdir = a.out or os.path.join(os.path.dirname(os.path.abspath(a.video)), "..", "build", "sheets")
    os.makedirs(outdir, exist_ok=True); made = []
    if a.mode == "coarse":
        for i, s in enumerate(range(0, int(dur), 100)):
            times = [s + k * a.every for k in range(int(100 / a.every)) if s + k * a.every < dur]
            made.append(tile(frames_at(a.video, times, a.width or 384), 5, os.path.join(outdir, "%s_coarse_%03d.png" % (base, s))))
    elif a.mode == "fine":
        if a.t0 is None or a.t1 is None: ap.error("fine needs --from and --to")
        step = 1 / a.fps; times = [round(a.t0 + k * step, 3) for k in range(int((a.t1 - a.t0) / step) + 1)]
        made.append(tile(frames_at(a.video, times, a.width or 320), 6, os.path.join(outdir, "%s_fine_%g-%g.png" % (base, a.t0, a.t1))))
    else:
        if not a.at: ap.error("give --at times")
        grid = a.grid if a.mode == "frames" else None
        made.append(tile(frames_at(a.video, a.at, a.width or 640, grid, W), 3 if a.mode == "frames" else 4,
                         os.path.join(outdir, "%s_%s_%s.png" % (base, a.mode, "_".join("%g" % t for t in a.at)[:60]))))
    print("%s: %dx%d %.3ffps %.1fs" % (a.video, W, H, fps, dur))
    for m in made: print(os.path.abspath(m))

if __name__ == "__main__":
    main()
