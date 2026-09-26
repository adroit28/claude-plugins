#!/usr/bin/env python3
"""Render a 9:16 Short from a JSON edit spec with ffmpeg + Pillow.

  render.py <edit_dir>/spec.v1.json            render to <edit_dir>/<slug>_v1.mp4
  render.py spec.json --dry-run                print the timeline only
  render.py spec.json --force                  ignore cached segments

The spec is the single source of truth for an edit; a revision is a new spec
version. Segments are encoded once each and cached by content hash, so changing
one shot or only the captions re-renders only what changed. See
references/spec-format.md for every field. Text is drawn by Pillow (Homebrew
ffmpeg has no drawtext). All segments are encoded identically (libx264 crf 18,
yuv420p, fixed fps, aac 160k 48 kHz stereo) and frame-pinned so the concat never
drifts.
"""
import argparse, hashlib, json, math, os, subprocess, sys
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
except ImportError:
    sys.exit("Pillow missing: run setup.sh and use its venv python")

FONT_BIG = os.environ.get("FS_FONT_BIG", "/System/Library/Fonts/Supplemental/Impact.ttf")
FONT_SMALL = os.environ.get("FS_FONT_SMALL", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")
FONT_EMOJI = os.environ.get("FS_FONT_EMOJI", "/System/Library/Fonts/Apple Color Emoji.ttc")

class R:
    def __init__(self, spec_path, force=False, verbose=False):
        self.spec = json.load(open(spec_path))
        self.dir = os.path.dirname(os.path.abspath(spec_path))
        self.B = os.path.join(self.dir, "build"); os.makedirs(self.B, exist_ok=True)
        self.W, self.H = self.spec.get("size", [1080, 1920]); self.fps = self.spec.get("fps", 25)
        self.force, self.verbose = force, verbose
        self.V = ["-c:v", "libx264", "-preset", self.spec.get("preset", "medium"), "-crf", str(self.spec.get("crf", 18)),
                  "-pix_fmt", "yuv420p", "-r", str(self.fps)]
        self.A = ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
        self.sources = {k: os.path.join(self.dir, v) if not os.path.isabs(v) else v for k, v in self.spec.get("sources", {}).items()}
        for k, v in self.sources.items():
            if not os.path.exists(v): sys.exit("source %r not found: %s" % (k, v))
        self._audio = {}

    # ---------- helpers
    def run(self, args):
        cmd = ["ffmpeg", "-v", "error", "-y", *args]
        if self.verbose: print(" ".join(cmd))
        subprocess.run(cmd, check=True)
    def count_frames(self, path):
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-count_frames", "-show_entries", "stream=nb_read_frames",
                              "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
        return int(out) if out.isdigit() else -1
    def sil(self, t): return ["-f", "lavfi", "-t", "%.3f" % t, "-i", "anullsrc=r=48000:cl=stereo"]
    def src(self, key):
        if key not in self.sources: sys.exit("segment refers to unknown source %r (sources: %s)" % (key, list(self.sources)))
        return self.sources[key]
    def has_audio(self, key):
        """Clips people hand over are often silent (a screen recording, a re-upload); such a source gets a silent track."""
        if key not in self._audio:
            out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", self.src(key)],
                                 capture_output=True, text=True).stdout.strip()
            self._audio[key] = bool(out)
        return self._audio[key]
    # Durations are snapped to a whole number of frames with round-half-up. Python's round() is
    # banker's rounding (82.5 -> 82), which silently drops a frame and drifts every later cut.
    def frames(self, dur): return int(math.floor(dur * self.fps + 0.5 + 1e-6))
    def snap(self, dur): return self.frames(dur) / self.fps
    def nf(self, dur): return str(self.frames(dur))
    ENGINE = None  # sha1 of this script's source; edits to render.py invalidate cached segments
    def h(self, obj, *files):
        if R.ENGINE is None: R.ENGINE = hashlib.sha1(open(__file__, "rb").read()).hexdigest()[:8]
        s = json.dumps(obj, sort_keys=True) + "".join("%s%s" % (f, os.path.getmtime(f)) for f in files if f and os.path.exists(f))
        return hashlib.sha1((s + "%dx%d@%d" % (self.W, self.H, self.fps) + R.ENGINE).encode()).hexdigest()[:8]
    def fit(self): return ",scale=%d:%d,setsar=1" % (self.W, self.H)

    def crop(self, c, t=None):
        """[w,h,x,y] | {w,h,x_from,x_to,y} pan | 'crop=...' string | None = centred 9:16."""
        if c is None: return "crop=ih*%d/%d:ih" % (self.W, self.H)
        if isinstance(c, str): return c if c.startswith("crop=") else "crop=" + c
        if isinstance(c, dict):
            x0, x1 = c["x_from"], c["x_to"]
            return "crop=%d:%d:x='%s+(%s)*t/%s':y=%d" % (c["w"], c["h"], x0, x1 - x0, t or 1, c.get("y", 0))
        w, h, x, y = c; return "crop=%d:%d:%d:%d" % (w, h, x, y)

    def fill_of(self, s):
        """`fill` on the segment, else the spec-level `fill`; `"fill": false` on a segment turns it off."""
        f = s.get("fill", self.spec.get("fill"))
        return f if isinstance(f, dict) else None

    def vf(self, s, t=None, allow_fill=True):
        f = self.fill_of(s) if allow_fill else None
        extra = ("," + s["vf"] if s.get("vf") else "")
        if not f: return self.crop(s.get("crop"), t) + extra
        # Letterboxed / landscape source: blurred, darkened copy of the picture box fills the 9:16 frame and the
        # foreground (the segment's crop, default the whole box) is scaled to the full width and centred on cy.
        # Blurring at 1/8 size and scaling up is ~20x cheaper than boxblur at 1080x1920 and looks the same.
        bw, bh, bx, by = f["box"]; fg = s.get("crop") or f.get("crop") or f["box"]
        cy = f.get("cy", 0.47); dark = f.get("dark", 0.12); blur = f.get("blur", 6)
        return ("split[fa][fb];[fa]crop=%d:%d:%d:%d,scale=%d:%d:force_original_aspect_ratio=increase,crop=%d:%d,boxblur=%d:2,"
                "eq=brightness=%.3f:saturation=1.1,scale=%d:%d,setsar=1[fbg];[fb]%s%s,scale=%d:-2,setsar=1[ffg];"
                "[fbg][ffg]overlay=(main_w-overlay_w)/2:%d-overlay_h/2" % (
                    bw, bh, bx, by, self.W // 8, self.H // 8, self.W // 8, self.H // 8, blur, -dark, self.W, self.H,
                    self.crop(fg, t), extra, self.W, int(cy * self.H)))

    def post(self, s):
        """Effects on the finished 1080x1920 frame, timed in output seconds of the segment: zoom (push-in or punch),
        shake (impact), flash (white flash at the cut). Appended after any speed change so `at` means what you see."""
        out = ""; W, H = self.W, self.H
        z = s.get("zoom") if s["type"] not in ("still", "card") else None
        if z:
            if not isinstance(z, dict): z = {"to": z}
            z0, z1, at = z.get("from", 1.0), z["to"], z.get("at", 0); d = z.get("dur") or max(self.expected(s) - at, 0.04)
            p = r"clip((t-%s)/%s\,0\,1)" % (at, d)
            if z.get("ease", "out") == "out": p = "(1-(1-%s)*(1-%s))" % (p, p)
            zz = "(%s+%s*%s)" % (z0, z1 - z0, p)
            out += (",scale=w='trunc(%d*%s/2)*2':h='trunc(%d*%s/2)*2':eval=frame,crop=%d:%d:x='(iw-%d)*%s':y='(ih-%d)*%s',setsar=1"
                    % (W, zz, H, zz, W, H, W, z.get("cx", 0.5), H, z.get("cy", 0.5)))
        sh = s.get("shake")
        if sh:
            if not isinstance(sh, dict): sh = {"dur": sh}
            a, at, d = sh.get("amp", 14), sh.get("at", 0), sh.get("dur", 0.35)
            env = r"between(t\,%s\,%s)*(1-(t-%s)/%s)" % (at, at + d, at, d)
            out += ",scale=%d:%d,crop=%d:%d:x='%d+%d*sin(t*71)*%s':y='%d+%d*cos(t*53)*%s',setsar=1" % (
                W + 2 * a, H + 2 * a, W, H, a, a, env, a, a, env)
        fl = s.get("flash") if s is not self.spec["segments"][0] else None  # frame 0 is the scroll thumbnail: never white
        if fl: out += ",fade=t=in:st=0:d=%s:color=white" % (fl if not isinstance(fl, bool) else 0.12)
        return out

    # ---------- text
    def font(self, p, s): return ImageFont.truetype(p, s)
    def text_block(self, d, lines, y, path, size, fill="white", stroke=8, gap=12, maxw=None, bg=None, pad=18, emoji=None, im=None):
        """Centred lines. `emoji` sits inline after the last line (text + emoji centred as one unit, so it never
        collides with the text); `bg` draws one rounded badge behind everything (counters, tags)."""
        es = int(size * 1.05) if emoji else 0; eg = int(size * 0.2) if emoji else 0
        maxw = maxw or self.W - 80 - (2 * pad if bg else 0)
        while size > 24 and any(d.textlength(l, font=self.font(path, size)) + (es + eg if emoji and i == len(lines) - 1 else 0) > maxw
                                for i, l in enumerate(lines)):
            size -= 4; es = int(size * 1.05) if emoji else 0; eg = int(size * 0.2) if emoji else 0
        f = self.font(path, size)
        widths = [d.textlength(l, font=f) + (es + eg if emoji and i == len(lines) - 1 else 0) for i, l in enumerate(lines)]
        if bg:  # text keeps only a thin stroke on a badge
            tw = max(widths); th = len(lines) * (size + gap) - gap
            x0 = (self.W - tw) / 2 - pad; d.rounded_rectangle([x0, y - pad * 0.6, x0 + tw + 2 * pad, y + th + pad * 1.2], radius=pad, fill=bg)
            stroke = min(stroke, 3)
        for i, ln in enumerate(lines):
            x = (self.W - widths[i]) / 2
            d.text((x, y), ln, font=f, fill=fill, stroke_width=stroke, stroke_fill="black")
            if emoji and i == len(lines) - 1 and im is not None:
                e = self.emoji_img(emoji, es); im.alpha_composite(e, (int(x + d.textlength(ln, font=f) + eg), int(y + size * 0.55 - e.height / 2)))
            y += size + gap
        return y
    def emoji_img(self, ch, size):
        f = self.font(FONT_EMOJI, 160); im = Image.new("RGBA", (220, 220), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.text((20, 10), ch, font=f, embedded_color=True); bb = im.getbbox(); im = im.crop(bb)
        return im.resize((size, max(1, int(size * im.height / im.width))), Image.LANCZOS)
    def overlay_png(self, o, i):
        if o.get("png"): return os.path.join(self.dir, o["png"])
        p = os.path.join(self.B, "ov_%02d_%s.png" % (i, self.h(o)))
        if os.path.exists(p) and not self.force: return p
        im = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        if o.get("big"): self.text_block(d, o["big"], o.get("y_big", 330), FONT_BIG, o.get("big_size", 120), o.get("big_fill", "white"))
        if o.get("small"): self.text_block(d, o["small"], o.get("y_small", 1330), FONT_SMALL, o.get("small_size", 52), o.get("small_fill", "#FFD400"), stroke=6)
        for ex in o.get("extra", []):
            self.text_block(d, ex["lines"], ex["y"], FONT_SMALL if ex.get("font") == "small" else FONT_BIG,
                            ex.get("size", 100), ex.get("fill", "white"), stroke=ex.get("stroke", 8), bg=ex.get("bg"), pad=ex.get("pad", 18),
                            emoji=ex.get("emoji"), im=im)
        if o.get("emoji"):
            e = self.emoji_img(o["emoji"], o.get("emoji_size", 220))
            im.alpha_composite(e, (o.get("emoji_x", (self.W - e.width) // 2), o.get("emoji_y", 1300)))
        im.save(p); return p

    # ---------- segment builders (each returns path of an encoded segment)
    def frame_png(self, s, out):
        self.run(["-ss", str(s["at"]), "-i", self.src(s["src"]), "-frames:v", "1", "-vf", self.vf(s) + ",scale=%d:%d" % (self.W, self.H), out]); return out

    def seg_clip(self, s, out):
        t = s["t"]; speed = s.get("speed"); dur = self.expected(s)
        vfilt = self.vf(s, t) + self.fit() + (",setpts=%s*PTS" % speed if speed else "") + self.post(s)
        # setpts=k*PTS on N frames gives kN-k+1 frames, so read one extra source frame. And do NOT put an output -t on a
        # stretched segment: it drops the final duplicated frame and the segment comes up one short. -frames:v pins the
        # video; the anullsrc input (-t dur) bounds the audio.
        t_in = t + (1.0 / self.fps if speed else 0)
        args = ["-ss", str(s["ss"]), "-t", "%.3f" % t_in, "-i", self.src(s["src"])]
        if s.get("mute") or speed or not self.has_audio(s["src"]): args += [*self.sil(dur), "-map", "0:v", "-map", "1:a"]
        tail = [] if speed else ["-t", "%.3f" % dur]
        self.run([*args, "-vf", vfilt, *self.V, "-frames:v", self.nf(dur), *self.A, *tail, out]); return dur

    def seg_still(self, s, out):
        dur = self.expected(s); n = self.frames(dur); zoom = s.get("zoom", 0.06)
        if s.get("image"): png = os.path.join(self.dir, s["image"])
        else: png = self.frame_png(s, out[:-4] + "_frame.png")
        if s.get("blur") or s.get("dark"):
            im = Image.open(png).convert("RGB")
            if s.get("blur"): im = im.filter(ImageFilter.GaussianBlur(s["blur"]))
            if s.get("dark"): im = ImageEnhance.Brightness(im).enhance(1 - s["dark"])
            png = out[:-4] + "_bg.png"; im.save(png)
        self.run(["-loop", "1", "-t", str(dur), "-i", png, *self.sil(dur),
                  "-vf", "scale=%d:%d,zoompan=z='1+%s*on/%d':d=%d:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=%dx%d:fps=%d,setsar=1"
                  % (self.W * 2, self.H * 2, zoom, n, n, self.W, self.H, self.fps) + self.post(s),
                  *self.V, "-frames:v", self.nf(dur), *self.A, "-t", "%.3f" % dur, out]); return dur

    def seg_card(self, s, out):
        bg = s.get("bg", "#000000")
        if isinstance(bg, dict):
            png = self.frame_png(bg, out[:-4] + "_frame.png"); im = Image.open(png).convert("RGB")
            im = im.filter(ImageFilter.GaussianBlur(bg.get("blur", 12))); im = ImageEnhance.Brightness(im).enhance(1 - bg.get("dark", 0.45))
        else: im = Image.new("RGB", (self.W, self.H), bg)
        d = ImageDraw.Draw(im); lines = s["lines"]; gap = s.get("gap", 30)
        total = sum(l.get("size", 110) + gap for l in lines); y = s.get("y0", (self.H - total) // 2)
        for l in lines:
            path = FONT_SMALL if l.get("font") == "small" or l.get("size", 110) < 80 else FONT_BIG
            y = self.text_block(d, [l["text"]], y, path, l.get("size", 110), l.get("fill", "white"), stroke=l.get("stroke", 8), gap=gap)
        png = out[:-4] + "_card.png"; im.save(png)
        return self.seg_still({"type": "still", "image": os.path.relpath(png, self.dir), "t": s["t"], "zoom": s.get("zoom", 0.03),
                               "flash": s.get("flash"), "shake": s.get("shake")}, out)

    def seg_reverse(self, s, out):
        slow = s.get("slow", 1.25); dur = self.expected(s)
        vfilt = self.vf(s, s["t"]) + self.fit() + ",reverse,setpts=N/%d/TB,setpts=%s*PTS" % (self.fps, slow) + self.post(s)
        if self.has_audio(s["src"]) and not s.get("mute"): aud = ["-af", "areverse,atempo=%.4f" % (1 / slow)]
        else: aud = [*self.sil(dur), "-map", "0:v", "-map", "1:a"]
        self.run(["-ss", str(s["ss"]), "-t", str(s["t"]), "-i", self.src(s["src"]), *aud,
                  "-vf", vfilt, *self.V, "-frames:v", self.nf(dur), *self.A, "-t", "%.3f" % dur, out]); return dur

    def seg_split(self, s, out):
        t = self.expected(s); top, bot = s["top"], s["bottom"]; hh = self.H // 2
        amap = {"top": ["-map", "0:a"], "bottom": ["-map", "1:a"], "none": None}[s.get("audio", "top")]
        if amap and not self.has_audio((top if s.get("audio", "top") == "top" else bot)["src"]): amap = None
        args = ["-ss", str(top["ss"]), "-t", str(t), "-i", self.src(top["src"]), "-ss", str(bot["ss"]), "-t", str(t), "-i", self.src(bot["src"])]
        if amap is None: args += self.sil(t); amap = ["-map", "2:a"]
        fc = "[0:v]%s,scale=%d:%d,setsar=1[t];[1:v]%s,scale=%d:%d,setsar=1[b];[t][b]vstack%s[v]" % (
            self.vf(top, t, False), self.W, hh, self.vf(bot, t, False), self.W, hh, self.post(s))
        self.run([*args, "-filter_complex", fc, "-map", "[v]", *amap, *self.V, "-frames:v", self.nf(t), *self.A, "-t", "%.3f" % t, out]); return t

    def seg_boomerang(self, s, out):
        loops = s.get("loops", 2); pulse = s.get("pulse", 0.07); dur = self.expected(s)
        fc = "[0:v]%s%s,split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0,loop=loop=%d:size=%d:start=0,setpts=N/%d/TB" % (
            self.vf(s, s["t"]), self.fit(), loops - 1, int(s["t"] * 2 * self.fps) + 2, self.fps)
        if pulse: fc += ",scale=w='%d*(1+%s*abs(sin(t*8)))':h=-2:eval=frame,crop=%d:%d,setsar=1" % (self.W, pulse, self.W, self.H)
        fc += self.post(s) + "[v]"
        self.run(["-ss", str(s["ss"]), "-t", str(s["t"]), "-i", self.src(s["src"]), *self.sil(dur), "-filter_complex", fc,
                  "-map", "[v]", "-map", "1:a", *self.V, "-frames:v", self.nf(dur), *self.A, "-t", "%.3f" % dur, out]); return dur

    def seg_slowmo(self, s, out):
        f = s.get("factor", 3); dur = self.expected(s)
        # Pad the input by exactly two frames (measured: minterpolate on N frames yields 3N-5 at 3x, so one frame is
        # short and two is enough). Any more pulls whatever follows the window (a blurred pan, a body crossing) into
        # the interpolation and ghosts the tail. No output -t (see seg_clip); -frames:v pins the video.
        self.run(["-ss", str(s["ss"]), "-t", "%.3f" % (s["t"] + 2.0 / self.fps), "-i", self.src(s["src"]), *self.sil(dur), "-map", "0:v", "-map", "1:a",
                  "-vf", self.vf(s, s["t"]) + self.fit() + ",minterpolate=fps=%d:mi_mode=mci:mc_mode=aobmc:vsbmc=1,setpts=%s*PTS" % (self.fps * f, f) + self.post(s),
                  *self.V, "-frames:v", self.nf(dur), *self.A, out]); return dur

    def raw_dur(self, s):
        k = s["type"]
        if k in ("clip",): return s["t"] * (s.get("speed") or 1)
        if k in ("still", "card", "split"): return s["t"]
        if k == "reverse": return s["t"] * s.get("slow", 1.25)
        if k == "boomerang": return s["t"] * 2 * s.get("loops", 2)
        if k == "slowmo": return s["t"] * s.get("factor", 3)
        sys.exit("unknown segment type %r" % k)
    # The one duration every segment builder AND the timeline use, so captions can never drift off cuts.
    def expected(self, s): return self.snap(self.raw_dur(s))

    # ---------- sound effects, all synthesised (no sample files to license)
    SFX = {  # kind: (default duration, lavfi source with %(d)s, shaping filters)
        "bass":  (0.6, "sine=f=%(freq)s:d=%(d)s", "afade=t=out:st=0.05:d=0.5,"),
        "whoosh": (0.45, "anoisesrc=d=%(d)s:c=pink:a=0.7:r=48000", "highpass=f=500,lowpass=f=6000,afade=t=in:d=%(a)s:curve=exp,afade=t=out:st=%(a)s:d=%(b)s,"),
        "riser": (1.2, "aevalsrc='0.45*(t/%(d)s)*sin(2*PI*(150*t+900*t*t/%(d)s))':d=%(d)s:s=48000", "afade=t=out:st=%(e)s:d=0.06,"),
        "ding":  (0.8, "aevalsrc='0.5*exp(-5*t)*(sin(2*PI*1568*t)+0.4*sin(2*PI*3136*t))':d=%(d)s:s=48000", ""),
        "tick":  (0.08, "aevalsrc='0.7*exp(-70*t)*sin(2*PI*2200*t)':d=%(d)s:s=48000", ""),
    }
    def sfx(self, h):
        kind = h.get("kind", "bass")
        if kind not in self.SFX: sys.exit("unknown hit kind %r (have: %s)" % (kind, ", ".join(self.SFX)))
        d0, src, shape = self.SFX[kind]; d = h.get("dur", d0)
        v = {"d": d, "freq": h.get("freq", 48), "a": round(d * 0.65, 3), "b": round(d * 0.35, 3), "e": round(max(d - 0.06, 0), 3)}
        return src % v, shape % v

    # ---------- main
    def timeline(self):
        rows, t = [], 0.0
        for i, s in enumerate(self.spec["segments"]):
            d = self.expected(s); r = self.raw_dur(s)
            if abs(r - d) > 1e-6:
                print("note: segment %d %r lasts %.4fs = %.2f frames at %dfps; rendered as %.3fs (%d frames). Use whole-frame durations to keep caption times exact."
                      % (i, s.get("label", s["type"]), r, r * self.fps, self.fps, d, self.frames(d)), file=sys.stderr)
            rows.append({"i": i, "start": round(t, 3), "end": round(t + d, 3), "dur": round(d, 3),
                                              "type": s["type"], "label": s.get("label", ""), "src": s.get("src") or (s.get("top", {}).get("src")), "ss": s.get("ss", s.get("at"))})
            t += d
        return rows, round(t, 3)

    def render(self, dry=False):
        rows, total = self.timeline()
        print("%-3s %-7s %-7s %-6s %-9s %-14s %-6s %s" % ("#", "start", "end", "dur", "type", "label", "src", "ss"))
        for r in rows: print("%-3d %-7.2f %-7.2f %-6.2f %-9s %-14s %-6s %s" % (r["i"], r["start"], r["end"], r["dur"], r["type"], r["label"][:14], r["src"] or "-", r["ss"] if r["ss"] is not None else "-"))
        print("total %.2fs" % total)
        if total > self.spec.get("max_duration", 35): print("WARNING: over %ss; the channel rule is 13-30 s" % self.spec.get("max_duration", 35))
        for o in self.spec.get("overlays", []):
            if o["to"] > total + 0.01: print("WARNING: overlay %s ends at %s, after the video (%.2f)" % (o.get("big") or o.get("small") or o.get("png"), o["to"], total))
        ver = self.spec.get("version", 1); slug = self.spec.get("slug", "short")
        out = os.path.join(self.dir, self.spec.get("out") or "%s_v%s.mp4" % (slug, ver))
        json.dump({"total": total, "segments": rows, "out": out}, open(os.path.join(self.B, "timeline_v%s.json" % ver), "w"), indent=1)
        if dry: return out
        segs, bad = [], []
        for i, s in enumerate(self.spec["segments"]):
            files = [self.sources.get(s.get("src"))] + [self.sources.get(s.get(k, {}).get("src")) for k in ("top", "bottom")]
            if s.get("image"): files.append(os.path.join(self.dir, s["image"]))
            p = os.path.join(self.B, "seg_%02d_%s.mp4" % (i, self.h(s, *files)))
            if not os.path.exists(p) or self.force:
                print("encoding %d %s %s" % (i, s["type"], s.get("label", ""))); getattr(self, "seg_" + s["type"])(s, p)
            got, want = self.count_frames(p), self.frames(self.expected(s))
            if got != want:
                bad.append(i); print("WARN segment %d %r has %d frames, expected %d: every later cut and caption will be off by %d frame(s)"
                                     % (i, s.get("label", s["type"]), got, want, got - want), file=sys.stderr)
            segs.append(p)
        lst = os.path.join(self.B, "concat_v%s.txt" % ver)
        open(lst, "w").write("".join("file '%s'\n" % p for p in segs))
        raw = os.path.join(self.B, "raw_v%s.mp4" % ver)
        self.run(["-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", raw])
        # overlays + audio in one pass
        inputs = ["-i", raw]; fc = ""; last = "[0:v]"; n = 1
        for i, o in enumerate(self.spec.get("overlays", [])):
            png = self.overlay_png(o, i)
            inputs += ["-loop", "1", "-framerate", str(self.fps), "-t", "%.3f" % total, "-i", png]
            fc += "%s[%d:v]overlay=%d:%d:eof_action=pass:enable='between(t,%s,%s)'[v%d];" % (last, n, o.get("x", 0), o.get("y", 0), o["from"], o["to"], i)
            last = "[v%d]" % i; n += 1
        au = self.spec.get("audio", {}); mix = ["[a0]"]
        fc += "[0:a]volume=%s[a0];" % au.get("clip_volume", 0.9)
        bed = au.get("bed")
        if bed:
            f = self.src(bed["src"]) if bed.get("src") else os.path.join(self.dir, bed["file"])
            inputs += ["-ss", str(bed.get("ss", 0)), "-t", "%.3f" % total, "-i", f]
            fo = bed.get("fade_out", 2.0)
            fc += "[%d:a]volume=%s,afade=t=out:st=%.3f:d=%.3f[a%d];" % (n, bed.get("volume", 0.22), max(total - fo, 0), fo, n); mix.append("[a%d]" % n); n += 1
        for hkey in au.get("hits", []):
            src, shape = self.sfx(hkey)
            inputs += ["-f", "lavfi", "-i", src]
            ms = int(max(hkey["at"], 0) * 1000)
            fc += "[%d:a]%sadelay=%d|%d,volume=%s[a%d];" % (n, shape, ms, ms, hkey.get("volume", 0.9), n); mix.append("[a%d]" % n); n += 1
        ln = au.get("loudnorm", "I=-14:TP=-1.5:LRA=11")
        if len(mix) > 1: fc += "%samix=inputs=%d:duration=first:normalize=0%s[a]" % ("".join(mix), len(mix), (",loudnorm=" + ln) if ln else "")
        else: fc += "[a0]%s[a]" % (("loudnorm=" + ln) if ln else "anull")
        vmap = "0:v" if last == "[0:v]" else last  # with no overlays there is no filter label to map
        self.run([*inputs, "-filter_complex", fc, "-map", vmap, "-map", "[a]", *self.V, *self.A, "-movflags", "+faststart", "-t", "%.3f" % total, out])
        if bad: print("WARN %d segment(s) off by frames: %s. Fix the spec (whole-frame durations, clean footage after slow-mo windows) before trusting caption times." % (len(bad), bad), file=sys.stderr)
        print("rendered", out); return out

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--force", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args(); R(a.spec, a.force, a.verbose).render(a.dry_run)

if __name__ == "__main__":
    main()
