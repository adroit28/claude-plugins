#!/usr/bin/env python3
"""Per-frame positions for moving overlays, and an alpha video of those overlays for render.py.

  track.py track  <video> --from 25.8 --to 26.72 --box 1300,745,95,200 --out build/messi.json   OpenCV CSRT
  track.py keys   --fps 59.94 --keys "26.72:1130,850 26.8:1074,731 ..." --out build/ball.json    hand keys, spline
  track.py cam    <video> --from 26.6 --to 29.7 --mask 1500,0,420,170 --out build/cam_fk.json    camera motion
  track.py render fx.json --spec spec.v1.json [--out build/fx_v1.mov]                           RGBA overlay video

Track files hold source seconds and source pixels: {"fps", "points": [[t, cx, cy, w, h], ...]}.
`render` maps them through each segment's crop, ss and speed (from the spec and its dry-run timeline), so an
overlay stays on the subject however the segment is cut. The output is a full-length 1080x1920 qtrle .mov
with alpha; add it to the spec as an overlay: {"video": "build/fx_v1.mov", "from": 0, "to": <total>}.

fx.json: {"layers": [ ... ]}, drawn in order. Times `from`/`to` are output seconds; `seg` limits a layer to
one segment (index in the spec). Layer types:
  tag      {"track" | "xy":[sx,sy], "text", "seg", "brackets": true}      pill above the subject, lock-on corners
  trail    {"track", "seg", "len": 0.3, "color": "#FFD400"}               glowing comet behind the tracked point
  tracer   {"track", "cam", "seg", "from_t", "spacing": 26, "dot_r": 6}   TV-style dotted path from from_t to now that
           stays pinned to the pitch while the camera pans/zooms: `cam` (from `track.py cam`) holds chained per-frame
           homographies, and every earlier point is warped into the current frame before it is drawn
  ring     {"track" | "xy", "seg", "r": 34, "color", "label"}             pulsing ring on a point (works on stills)
  counter  {"label", "values": [[t, "75"], [4.1, "76*", "*unofficial count"]], "x", "y"}   pops on change
  timer    {"seg", "t0", "t1", "scale": 1, "fmt": "est. {:.1f} s", "x", "y"}  seconds from source frame times
Add a type by writing a draw_<type>(self, im, layer, ctx) method. Point layers follow the segment's `zoom` and
`shake` (render.py post effects), so they stay on the subject through punch-ins and impact jolts.
Segments with a `{"reframe": ...}` crop map through the moving window, so overlays stay put on reframed shots.
`cam` works for a broadcast camera that pans/tilts/zooms from a fixed spot (a homography is exact then); mask
static screen graphics (score bug, channel logo) with --mask x,y,w,h so they do not pull the estimate to "no motion".
Needs the shorts venv: Pillow, numpy, opencv-contrib-python (track mode only).
"""
import argparse, json, math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BIG = os.environ.get("FS_FONT_BIG", "/System/Library/Fonts/Supplemental/Impact.ttf")
FONT_SMALL = os.environ.get("FS_FONT_SMALL", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")


# ---------- track files
def load_track(path):
    d = json.load(open(path)); return d["points"]

def at(points, t):
    """Interpolated [cx, cy, w, h] at source time t, or None outside the track."""
    if not points or t < points[0][0] - 1e-6 or t > points[-1][0] + 1e-6: return None
    lo, hi = 0, len(points) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if points[mid][0] <= t: lo = mid
        else: hi = mid
    a, b = points[lo], points[hi]
    k = 0 if b[0] == a[0] else min(max((t - a[0]) / (b[0] - a[0]), 0), 1)
    return [a[i] + (b[i] - a[i]) * k for i in range(1, 5)]

def cmd_track(a):
    import cv2
    cap = cv2.VideoCapture(a.video); fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_MSEC, a.t0 * 1000)
    ok, frame = cap.read()
    if not ok: sys.exit("cannot read %s at %s" % (a.video, a.t0))
    box = tuple(int(v) for v in a.box.split(","))
    mk = getattr(cv2, "TrackerCSRT_create", None) or cv2.legacy.TrackerCSRT_create
    tr = mk(); tr.init(frame, box)
    t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - 1 / fps
    pts = [[round(t, 4), box[0] + box[2] / 2, box[1] + box[3] / 2, box[2], box[3]]]; lost = 0
    while t < a.t1:
        ok, frame = cap.read()
        if not ok: break
        t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - 1 / fps
        ok, b = tr.update(frame)
        if ok: pts.append([round(t, 4), b[0] + b[2] / 2, b[1] + b[3] / 2, b[2], b[3]])
        else: lost += 1
    json.dump({"video": a.video, "fps": fps, "mode": "csrt", "points": pts}, open(a.out, "w"))
    print("tracked %d frames (%d lost) %.2f-%.2f -> %s" % (len(pts), lost, pts[0][0], pts[-1][0], a.out))

def catmull(p0, p1, p2, p3, u):
    return 0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3)

def cmd_keys(a):
    ks = []
    for tok in a.keys.split():
        t, xy = tok.split(":"); x, y = xy.split(","); ks.append((float(t), float(x), float(y)))
    ks.sort()
    if len(ks) < 2: sys.exit("need at least two keys")
    pts, n = [], int(round((ks[-1][0] - ks[0][0]) * a.fps))
    for f in range(n + 1):
        t = ks[0][0] + f / a.fps; i = max(j for j in range(len(ks) - 1) if ks[j][0] <= t + 1e-9) if t < ks[-1][0] else len(ks) - 2
        k0, k1, k2, k3 = ks[max(i - 1, 0)], ks[i], ks[i + 1], ks[min(i + 2, len(ks) - 1)]
        u = min(max((t - k1[0]) / (k2[0] - k1[0]), 0), 1)
        pts.append([round(t, 4), catmull(k0[1], k1[1], k2[1], k3[1], u), catmull(k0[2], k1[2], k2[2], k3[2], u), a.size, a.size])
    json.dump({"fps": a.fps, "mode": "keys", "keys": ks, "points": pts}, open(a.out, "w"))
    print("%d keys -> %d frames %.2f-%.2f -> %s" % (len(ks), len(pts), pts[0][0], pts[-1][0], a.out))

def cmd_cam(a):
    """Frame-to-frame homographies (LK optical flow on corners + RANSAC, forward-backward checked), chained so
    C[t] maps pixels of the first frame into frame t. Players and the ball are outliers to RANSAC."""
    import cv2, numpy as np
    cap = cv2.VideoCapture(a.video); fps = cap.get(cv2.CAP_PROP_FPS)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(a.t0 * fps)))
    prev, C, out, worst = None, np.eye(3), [], 1 << 30
    while True:
        f = int(cap.get(cv2.CAP_PROP_POS_FRAMES)); ok, fr = cap.read()
        if not ok or f / fps > a.t1 + 1e-6: break
        g = cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY)
        if prev is None:
            mask = np.full(g.shape, 255, np.uint8)
            for m in a.mask or []:
                x, y, w, h = (int(v) for v in m.split(",")); mask[y:y + h, x:x + w] = 0
        else:
            p0 = cv2.goodFeaturesToTrack(prev, 1500, 0.01, 12, mask=mask)
            p1, st, _ = cv2.calcOpticalFlowPyrLK(prev, g, p0, None, winSize=(21, 21), maxLevel=4)
            pb, _, _ = cv2.calcOpticalFlowPyrLK(g, prev, p1, None, winSize=(21, 21), maxLevel=4)
            good = (st[:, 0] == 1) & (np.linalg.norm((pb - p0)[:, 0], axis=1) < 1.0)
            H, inl = cv2.findHomography(p0[good], p1[good], cv2.RANSAC, 1.5)
            if H is None: sys.exit("no homography at %.3f s: too few static features" % (f / fps))
            C = H @ C; worst = min(worst, int(inl.sum()))
        out.append([round(f / fps, 4), [round(v, 8) for v in C.flatten()]]); prev = g
    json.dump({"video": a.video, "fps": fps, "mask": a.mask, "frames": out}, open(a.out, "w"))
    print("cam: %d frames %.2f-%.2f, fewest RANSAC inliers %d -> %s" % (len(out), out[0][0], out[-1][0], worst, a.out))


# ---------- overlay video
class FX:
    def __init__(self, fx_path, spec_path):
        self.fx = json.load(open(fx_path)); self.spec = json.load(open(spec_path))
        self.dir = os.path.dirname(os.path.abspath(spec_path))
        self.W, self.H = self.spec.get("size", [1080, 1920]); self.fps = self.spec.get("fps", 25)
        tl = os.path.join(self.dir, "build", "timeline_v%s.json" % self.spec.get("version", 1))
        if not os.path.exists(tl): sys.exit("run render.py %s --dry-run first (needs %s)" % (spec_path, tl))
        self.rows = json.load(open(tl))["segments"]; self.total = json.load(open(tl))["total"]
        self.tracks = {}
        self.fonts = {}

    def font(self, path, size):
        k = (path, size)
        if k not in self.fonts: self.fonts[k] = ImageFont.truetype(path, size)
        return self.fonts[k]

    def track(self, p):
        if p not in self.tracks: self.tracks[p] = load_track(os.path.join(self.dir, p))
        return self.tracks[p]

    def seg_at(self, T):
        for r in self.rows:
            if r["start"] - 1e-6 <= T < r["end"] - 1e-6: return r
        return None

    def mapping(self, i, T=None):
        """(src time of output time T, source px -> output px) for segment i. A reframe crop moves, so the
        px mapping uses the window at output time T (render.py's Reframe path, the same maths as its crop)."""
        s = self.spec["segments"][i]; r = self.rows[i]
        if s.get("fill") or (self.spec.get("fill") and s.get("fill") is not False): sys.exit("segment %d uses fill: not supported by track.py" % i)
        if s["type"] == "still": tfun = lambda T: s["at"]
        elif s["type"] == "clip":
            k = s.get("speed") or 1; tfun = lambda T: s["ss"] + (T - r["start"]) / k
        elif s["type"] == "ramp":
            from speclib import ramp_src
            tfun = lambda T: s["ss"] + ramp_src(s, min(max(T - r["start"], 0), r["dur"]))
        else: sys.exit("segment %d: type %s not supported" % (i, s["type"]))
        c = s.get("crop")
        if isinstance(c, dict) and c.get("reframe"):
            from render import reframe_of
            src = self.spec["sources"][s["src"]]; src = src if os.path.isabs(src) else os.path.join(self.dir, src)
            rf = reframe_of(c, s, self.dir, src, None, self.W, self.H)
            u = 0 if s["type"] == "still" or T is None else tfun(T) - s["ss"]
            cw, ch, cx, cy = rf.w, rf.h, rf.x(u), rf.y
        elif c is None or isinstance(c, (dict, str)):
            if c is not None: sys.exit("segment %d: only fixed [w,h,x,y] or reframe crops are supported" % i)
            sys.exit("segment %d: give an explicit [w,h,x,y] crop" % i)
        else: cw, ch, cx, cy = c
        sx, sy = self.W / cw, self.H / ch
        return tfun, (lambda x, y: ((x - cx) * sx, (y - cy) * sy)), sx

    def post_xy(self, i, T, x, y):
        """Output px after render.py's post effects on segment i (still zoompan, clip zoom, shake), same formulas."""
        s = self.spec["segments"][i]; r = self.rows[i]; t = T - r["start"]; W, H = self.W, self.H
        if s["type"] == "still":
            n = int(math.floor(r["dur"] * self.fps + 0.5)); z = 1 + s.get("zoom", 0.06) * round(t * self.fps) / n
            x, y = W / 2 + (x - W / 2) * z, H / 2 + (y - H / 2) * z
        elif s.get("zoom"):
            zd = s["zoom"] if isinstance(s["zoom"], dict) else {"to": s["zoom"]}
            z0, z1, a0 = zd.get("from", 1.0), zd["to"], zd.get("at", 0); d = zd.get("dur") or max(r["dur"] - a0, 0.04)
            p = min(max((t - a0) / d, 0), 1)
            if zd.get("ease", "out") == "out": p = 1 - (1 - p) * (1 - p)
            z = z0 + (z1 - z0) * p
            x, y = x * z - W * (z - 1) * zd.get("cx", 0.5), y * z - H * (z - 1) * zd.get("cy", 0.5)
        sh = s.get("shake")
        if sh:
            if not isinstance(sh, dict): sh = {"dur": sh}
            a, a0, d = sh.get("amp", 14), sh.get("at", 0), sh.get("dur", 0.35)
            env = (1 - (t - a0) / d) if a0 <= t <= a0 + d else 0
            x = x * (W + 2 * a) / W - a - a * math.sin(t * 71) * env
            y = y * (H + 2 * a) / H - a - a * math.cos(t * 53) * env
        return x, y

    def active(self, L, T, seg):
        if "from" in L and T < L["from"] - 1e-6: return False
        if "to" in L and T >= L["to"] - 1e-6: return False
        if "seg" in L and (seg is None or seg["i"] != L["seg"]): return False
        return True

    def point(self, L, ctx, t=None):
        tfun, m, s = ctx["map"]; t = tfun(ctx["T"]) if t is None else t
        if "xy" in L: x, y = L["xy"]; w = h = L.get("size", 40)
        else:
            p = at(self.track(L["track"]), t)
            if p is None: return None
            x, y, w, h = p
        ox, oy = self.post_xy(ctx["seg"]["i"], ctx["T"], *m(x, y)); return ox, oy, w * s, h * s

    # layers
    def draw_tag(self, im, L, ctx):
        p = self.point(L, ctx)
        if not p: return
        x, y, w, h = p; d = ImageDraw.Draw(im); col = L.get("color", "#FFD400")
        if L.get("brackets", True):
            l = max(min(w, h) * 0.28, 16); x0, y0, x1, y1 = x - w / 2 - 8, y - h / 2 - 8, x + w / 2 + 8, y + h / 2 + 8
            for (px, py, dx, dy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
                d.line([(px, py), (px + dx * l, py)], fill=col, width=6); d.line([(px, py), (px, py + dy * l)], fill=col, width=6)
        f = self.font(FONT_SMALL, L.get("size", 46)); txt = L["text"]
        tw = d.textlength(txt, font=f); pad = 22; bh = L.get("size", 46) + 26
        bx = min(max(x - tw / 2 - pad, 20), self.W - 170 - tw - 2 * pad)  # keep off the right-hand button column
        by = y - h / 2 - 30 - bh
        d.rounded_rectangle([bx, by, bx + tw + 2 * pad, by + bh], radius=bh / 2, fill=(10, 10, 10, 225), outline=col, width=4)
        d.polygon([(x - 14, by + bh - 1), (x + 14, by + bh - 1), (x, by + bh + 18)], fill=col)
        d.text((bx + pad, by + bh / 2), txt, font=f, fill="white", anchor="lm")

    def draw_trail(self, im, L, ctx):
        tfun = ctx["map"][0]; t = tfun(ctx["T"]); pts = self.track(L["track"])
        if t < pts[0][0]: return
        t = min(t, pts[-1][0]); ln = L.get("len", 0.3); n = 24
        xy = [self.point(L, ctx, t - ln + ln * k / n) for k in range(n + 1)]
        xy = [p[:2] for p in xy if p]
        if len(xy) < 2: return
        col = ImageColorRGB(L.get("color", "#FFD400"))
        xs, ys = [p[0] for p in xy], [p[1] for p in xy]; pad = 60
        box = (int(max(min(xs) - pad, 0)), int(max(min(ys) - pad, 0)), int(min(max(xs) + pad, self.W)), int(min(max(ys) + pad, self.H)))
        if box[2] <= box[0] or box[3] <= box[1]: return
        lay = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        loc = [(x - box[0], y - box[1]) for x, y in xy]; wmax = L.get("width", 22)
        for k in range(1, len(loc)):
            u = k / (len(loc) - 1)
            d.line([loc[k - 1], loc[k]], fill=col + (int(255 * u ** 1.4),), width=max(int(wmax * u), 2))
        glow = lay.filter(ImageFilter.GaussianBlur(L.get("glow", 12)))
        core = Image.new("RGBA", lay.size, (0, 0, 0, 0)); dc = ImageDraw.Draw(core)
        for k in range(1, len(loc)):
            u = k / (len(loc) - 1)
            dc.line([loc[k - 1], loc[k]], fill=(255, 255, 255, int(230 * u ** 2)), width=max(int(wmax * 0.35 * u), 1))
        hx, hy = loc[-1]; r = wmax * 0.55
        dc.ellipse([hx - r, hy - r, hx + r, hy + r], outline=(255, 255, 255, 255), width=4)
        im.alpha_composite(glow, box[:2]); im.alpha_composite(glow, box[:2]); im.alpha_composite(lay, box[:2]); im.alpha_composite(core, box[:2])

    def cam(self, p):
        if p not in self.tracks:
            import numpy as np
            fr = json.load(open(os.path.join(self.dir, p)))["frames"]
            self.tracks[p] = (np, np.array([f[0] for f in fr]), [np.array(f[1]).reshape(3, 3) for f in fr])
        return self.tracks[p]

    def draw_tracer(self, im, L, ctx):
        tfun, m, _ = ctx["map"]; t = tfun(ctx["T"]); pts = self.track(L["track"])
        t0 = L.get("from_t", pts[0][0]); t = min(t, pts[-1][0])
        if t < t0: return
        np, ct, CH = self.cam(L["cam"])
        Ct = CH[int(np.argmin(abs(ct - t)))]
        path = []
        for p in pts:
            if p[0] < t0 - 1e-6 or p[0] > t + 1e-6: continue
            M = Ct @ np.linalg.inv(CH[int(np.argmin(abs(ct - p[0])))])
            v = M @ np.array([p[1], p[2], 1.0]); path.append(self.post_xy(ctx["seg"]["i"], ctx["T"], *m(v[0] / v[2], v[1] / v[2])))
        if not path: return
        # resample at a fixed on-screen spacing so dots stay evenly spaced however fast the ball moved
        sp = L.get("spacing", 26); dots = [path[0]]; carry = 0.0
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            seg = math.hypot(x1 - x0, y1 - y0); u = sp - carry
            while u <= seg:
                dots.append((x0 + (x1 - x0) * u / seg, y0 + (y1 - y0) * u / seg)); u += sp
            carry = (carry + seg) % sp if seg else carry
        r = L.get("dot_r", 6); col = ImageColorRGB(L.get("color", "#FFFFFF")); gcol = ImageColorRGB(L.get("glow_color", "#3DDCFF"))
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
        d, dg = ImageDraw.Draw(lay), ImageDraw.Draw(glow)
        for x, y in dots:
            if -20 < x < self.W + 20 and -20 < y < self.H + 20:
                dg.ellipse([x - r - 3, y - r - 3, x + r + 3, y + r + 3], fill=gcol + (200,))
                d.ellipse([x - r - 2, y - r - 2, x + r + 2, y + r + 2], fill=(0, 0, 0, 200))
                d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
        if L.get("head", True):
            hx, hy = path[-1]; hr = L.get("head_r", 22)
            dg.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], outline=gcol + (255,), width=8)
            d.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], outline=(255, 255, 255, 255), width=4)
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(L.get("glow", 5)))); im.alpha_composite(lay)

    def draw_ring(self, im, L, ctx):
        p = self.point(L, ctx)
        if not p: return
        x, y = p[:2]; age = ctx["T"] - ctx["seg"]["start"]
        r = L.get("r", 34) * (1 + 0.12 * math.sin(age * 12)); col = ImageColorRGB(L.get("color", "#FFD400"))
        lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        d.ellipse([x - r, y - r, x + r, y + r], outline=col + (255,), width=7)
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(6))); im.alpha_composite(lay)
        if L.get("label"):
            f = self.font(FONT_SMALL, L.get("size", 40)); d = ImageDraw.Draw(im)
            lx, ly = x + L.get("lx", r + 18), y + L.get("ly", -r - 40)
            d.text((lx, ly), L["label"], font=f, fill=col + (255,), stroke_width=6, stroke_fill="black", anchor=L.get("anchor", "ls"))

    def draw_counter(self, im, L, ctx):
        T = ctx["T"]; cur, since = None, 0
        for v in L["values"]:
            if T >= v[0] - 1e-6: cur, since = v, v[0]
        if cur is None: return
        age = T - since; pop = L.get("pop", 0.3)
        k = 1 + 0.45 * max(0, 1 - age / pop) ** 2 if since > 0 else 1
        x, y = L.get("x", 40), L.get("y", 270); d = ImageDraw.Draw(im)
        fl = self.font(FONT_SMALL, L.get("label_size", 30)); lw = d.textlength(L["label"], font=fl)
        vs = int(L.get("size", 84) * k); fv = self.font(FONT_BIG, vs)
        vw = d.textlength(cur[1], font=fv); bw = max(lw, d.textlength(cur[1], font=self.font(FONT_BIG, L.get("size", 84)))) + 40
        bh = L.get("label_size", 30) + L.get("size", 84) + 34
        d.rounded_rectangle([x, y, x + bw, y + bh], radius=22, fill=(10, 10, 10, 215))
        d.text((x + 20, y + 14), L["label"], font=fl, fill="#FFD400")
        vc = "#FFD400" if since > 0 and age < pop * 1.5 else "white"
        d.text((x + 20 + (bw - 40) / 2, y + 14 + L.get("label_size", 30) + 8 + L.get("size", 84) / 2), cur[1], font=fv, fill=vc, anchor="mm")
        if len(cur) > 2 and cur[2]:
            fn = self.font(FONT_SMALL, L.get("note_size", 26)); d.text((x + 6, y + bh + 10), cur[2], font=fn, fill="white", stroke_width=4, stroke_fill="black")

    def draw_timer(self, im, L, ctx):
        t = ctx["map"][0](ctx["T"]); v = min(max(t - L["t0"], 0), L["t1"] - L["t0"]) * L.get("scale", 1)
        d = ImageDraw.Draw(im); f = self.font(FONT_SMALL, L.get("size", 48)); txt = L.get("fmt", "est. {:.1f} s").format(v)
        x, y = L.get("x", 540), L.get("y", 1300)
        d.text((x, y), txt, font=f, fill="white", stroke_width=6, stroke_fill="black", anchor="mm")

    def render(self, out):
        n = int(math.floor(self.total * self.fps + 0.5)); blank = bytes(self.W * self.H * 4); drawn = 0
        p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", "%dx%d" % (self.W, self.H),
                              "-r", str(self.fps), "-i", "-", "-c:v", "qtrle", "-pix_fmt", "argb", out], stdin=subprocess.PIPE)
        for f in range(n):
            T = f / self.fps; seg = self.seg_at(T); im = None
            for L in self.fx["layers"]:
                if not self.active(L, T, seg): continue
                ctx = {"T": T, "seg": seg}
                if L["type"] in ("tag", "trail", "tracer", "ring", "timer"):
                    if seg is None: continue
                    ctx["map"] = self.mapping(seg["i"], T)
                if im is None: im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
                getattr(self, "draw_" + L["type"])(im, L, ctx)
            if im is None: p.stdin.write(blank)
            else: p.stdin.write(im.tobytes()); drawn += 1
        p.stdin.close(); p.wait()
        if p.returncode: sys.exit("ffmpeg failed")
        print("fx: %d frames (%d with overlays) %.2fs -> %s" % (n, drawn, n / self.fps, out))


def ImageColorRGB(c):
    from PIL import ImageColor
    return ImageColor.getrgb(c)[:3]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("track"); t.add_argument("video"); t.add_argument("--from", dest="t0", type=float, required=True)
    t.add_argument("--to", dest="t1", type=float, required=True); t.add_argument("--box", required=True, help="x,y,w,h source px at --from")
    t.add_argument("--out", required=True)
    k = sub.add_parser("keys"); k.add_argument("--keys", required=True, help='"t:x,y t:x,y ..." source seconds and px')
    k.add_argument("--fps", type=float, required=True, help="source fps (one point per source frame)")
    k.add_argument("--size", type=float, default=24, help="object size px (w=h) for tags/rings"); k.add_argument("--out", required=True)
    c = sub.add_parser("cam"); c.add_argument("video"); c.add_argument("--from", dest="t0", type=float, required=True)
    c.add_argument("--to", dest="t1", type=float, required=True); c.add_argument("--out", required=True)
    c.add_argument("--mask", nargs="*", help="x,y,w,h source px boxes to ignore (static screen graphics)")
    r = sub.add_parser("render"); r.add_argument("fx"); r.add_argument("--spec", required=True); r.add_argument("--out")
    a = ap.parse_args()
    if a.cmd == "track": cmd_track(a)
    elif a.cmd == "keys": cmd_keys(a)
    elif a.cmd == "cam": cmd_cam(a)
    else:
        fx = FX(a.fx, a.spec)
        out = a.out or os.path.join(fx.dir, "build", "fx_v%s.mov" % fx.spec.get("version", 1))
        fx.render(out)

if __name__ == "__main__":
    main()
