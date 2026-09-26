#!/usr/bin/env python3
"""Picture track from the card PNGs + word timings -> build/graphics_v<N>.mp4 (video only),
the voice + whoosh mix -> build/voice_fx_v<N>.wav, and build/timeline_v<N>.json for finish.py.

  <venv>/bin/python compose.py <story.vN.json>

Every scene step is anchored to a word ({line, word}), so a new take or pace re-times everything.
Per frame: the current state image, a slow zoom per scene, a crossfade + punch on each reveal
inside a scene, a vertical whip between scenes, and a word-page caption with the spoken word in
yellow. Whooshes are synthesised filtered noise at each scene change (own sound).
"""
import json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import H, W, Story
from cards import states
from PIL import Image, ImageDraw, ImageFilter, ImageFont

MOTION = {"lead": 0.06, "tail": 0.75, "fade": 4, "whip": 6, "punch": 9, "zoom": 0.035, "zoom_center": [505, 760]}
CAPTIONS = {"max_words": 3, "max_chars": 18, "y": 1330, "max_width": 800, "size": 84, "active_color": "#FFD400", "hide_in_scenes": []}


def main():
    st = Story(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
    fps = st.data.get("canvas", {}).get("fps", 30)
    M = {**MOTION, **st.data.get("motion", {})}; CAP = {**CAPTIONS, **st.data.get("captions", {})}
    words, at = st.words()
    wav = st.p(st.data["narration"]["audio"])
    total_frames = int(round((words[-1]["end"] + M["tail"]) * fps)); total = total_frames / fps
    font_path = str(st.fonts / "Montserrat[wght].ttf")
    def font(size):
        f = ImageFont.truetype(font_path, size); f.set_variation_by_axes([800]); return f
    FONT = font(CAP["size"])

    # ---------- cues: (time, state, scene); the first state is on screen from 0
    cues = []
    for sc in st.data["scenes"]:
        _, n = states(sc)
        steps = sc.get("steps") or [{"at": sc.get("at")}]
        for k in range(n):
            w = st.anchor(steps[k]["at"], at)
            cues.append((max(0.0, w["start"] - M["lead"]), "%s_%d" % (sc["id"], k + 1), sc["id"]))
    cues[0] = (0.0,) + cues[0][1:]
    if any(cues[i][0] > cues[i + 1][0] for i in range(len(cues) - 1)):
        sys.exit("scene steps are not in word order: " + ", ".join("%s@%.2f" % (s, t) for t, s, _ in cues))
    imgs = {s: Image.open(st.p("graphics/v%d/%s.png" % (st.version, s))).convert("RGB") for _, s, _ in cues}
    scene_of = {s: sc for _, s, sc in cues}
    scene_start = {}
    for t, s, sc in cues: scene_start.setdefault(sc, t)
    order = list(scene_start)
    scene_end = {sc: (scene_start[order[i + 1]] if i + 1 < len(order) else total) for i, sc in enumerate(order)}

    # lines spoken during hidden scenes get no captions
    first_line = {}
    for sc in st.data["scenes"]:
        steps = sc.get("steps") or [{"at": sc.get("at")}]
        first_line[sc["id"]] = steps[0]["at"]["line"]
    line_ids = [l["id"] for l in st.lines]; hidden_lines = set(CAP.get("hide_lines", []))
    for i, sc in enumerate(order):
        if sc in CAP["hide_in_scenes"]:
            a0 = line_ids.index(first_line[sc]); a1 = line_ids.index(first_line[order[i + 1]]) if i + 1 < len(order) else len(line_ids)
            hidden_lines |= set(line_ids[a0:a1])

    # ---------- captions: pages of <= max_words words and max_chars characters, broken after punctuation
    pages, cur = [], []
    for w in words:
        if cur and len(" ".join(x["w"] for x in cur + [w])) > CAP["max_chars"]: pages.append(cur); cur = []
        cur.append(w)
        if len(cur) == CAP["max_words"] or re.search(r"[.,]$", w["w"]) or w is words[-1]:
            pages.append(cur); cur = []
    pages = [p for p in pages if p[0]["line"] not in hidden_lines]
    def page_window(i):
        p = pages[i]; nxt = pages[i + 1][0]["start"] if i + 1 < len(pages) else total
        return p[0]["start"] - 0.02, min(nxt - 0.02, p[-1]["end"] + 0.45)
    windows = [page_window(i) for i in range(len(pages))]
    clean = lambda s: re.sub(r"[.,]", "", s).upper()
    cap_cache = {}
    def caption(pi, active):
        if (pi, active) in cap_cache: return cap_cache[(pi, active)]
        toks = [clean(w["w"]) for w in pages[pi]]
        im = Image.new("RGBA", (W, 240), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        f = FONT; sp = d.textlength(" ", font=f)
        widths = [d.textlength(x, font=f) for x in toks]; tw = sum(widths) + sp * (len(toks) - 1)
        if tw > CAP["max_width"]:
            f = font(int(CAP["size"] * CAP["max_width"] / tw))
            sp = d.textlength(" ", font=f); widths = [d.textlength(x, font=f) for x in toks]; tw = sum(widths) + sp * (len(toks) - 1)
        x = (W - tw) / 2
        for j, (tok, wd) in enumerate(zip(toks, widths)):
            d.text((x, 120), tok, font=f, anchor="lm", fill=CAP["active_color"] if j == active else "white", stroke_width=9, stroke_fill="black")
            x += wd + sp
        cap_cache[(pi, active)] = im; return im

    cx, cy = M["zoom_center"]
    def zoomed(im, z):
        if abs(z - 1) < 1e-4: return im.copy()  # never draw captions onto the cached state image
        w, h = W / z, H / z; x0 = min(max(cx - w / 2, 0), W - w); y0 = min(max(cy - h / 2, 0), H - h)
        return im.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + w, y0 + h))
    def scene_zoom(s, t):
        sc = scene_of[s]; p = (t - scene_start[sc]) / max(scene_end[sc] - scene_start[sc], 0.1)
        return 1.0 + M["zoom"] * min(max(p, 0), 1)
    ease = lambda x: 1 - (1 - x) ** 3

    v = st.version
    out = st.out("build/graphics_v%d.mp4" % v)
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(fps),
                           "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], stdin=subprocess.PIPE)
    ci = 0; FADE, WHIP, PUNCH = M["fade"], M["whip"], M["punch"]
    for n in range(total_frames):
        t = n / fps
        while ci + 1 < len(cues) and cues[ci + 1][0] <= t: ci += 1
        t0, s, _ = cues[ci]; k = int(round((t - t0) * fps)); frame = zoomed(imgs[s], scene_zoom(s, t))
        if ci > 0:
            _, ps, _ = cues[ci - 1]
            if scene_of[ps] != scene_of[s] and k < WHIP:                # whip: old slides up, new slides in from below
                e = ease((k + 1) / WHIP); off = int(H * (1 - e))
                prev = zoomed(imgs[ps], scene_zoom(ps, t0))
                canvas = Image.new("RGB", (W, H)); canvas.paste(prev, (0, off - H)); canvas.paste(frame, (0, off))
                frame = canvas.filter(ImageFilter.GaussianBlur(10 * (1 - e))) if e < 0.95 else canvas
            elif scene_of[ps] == scene_of[s]:
                if k < FADE: frame = Image.blend(zoomed(imgs[ps], scene_zoom(ps, t)), frame, (k + 1) / FADE)
                if k < PUNCH: frame = zoomed(frame, 1 + 0.03 * (1 - ease((k + 1) / PUNCH)))
        for pi, (a0, a1) in enumerate(windows):
            if a0 <= t < a1:
                act = max([j for j, w in enumerate(pages[pi]) if w["start"] - 0.02 <= t] or [0])
                cap = caption(pi, act); age = t - a0
                if age < 0.1:                                          # small pop on each new page
                    sc = 0.88 + 0.12 * ease(age / 0.1); cw, chh = int(W * sc), int(240 * sc)
                    cap = cap.resize((cw, chh), Image.BILINEAR); frame.paste(cap, ((W - cw) // 2, CAP["y"] - chh // 2), cap)
                else: frame.paste(cap, (0, CAP["y"] - 120), cap)
                break
        ff.stdin.write(frame.tobytes())
    ff.stdin.close(); ff.wait()
    print("video", out.relative_to(st.dir), "%.3fs" % total, "%d frames" % total_frames)

    # ---------- voice + whooshes -> voice_fx
    au = st.data.get("audio", {})
    whooshes = [scene_start[sc] for sc in order[1:]] if au.get("whoosh", "scene_change") == "scene_change" else []
    inputs, fc, mix = ["-i", str(wav)], "", ["[0:a]"]
    for i, wt in enumerate(whooshes):
        inputs += ["-f", "lavfi", "-t", "0.35", "-i", "anoisesrc=color=pink:amplitude=0.6:r=24000"]
        ms = max(int((wt - 0.12) * 1000), 0)
        fc += "[%d:a]highpass=f=500,lowpass=f=6000,afade=t=in:d=0.15,afade=t=out:st=0.15:d=0.2,volume=0.22,adelay=%d[w%d];" % (i + 1, ms, i)
        mix.append("[w%d]" % i)
    fc += "%samix=inputs=%d:duration=longest:normalize=0,apad=whole_dur=%.3f[a]" % ("".join(mix), len(mix), total)
    fx = st.out("build/voice_fx_v%d.wav" % v)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "[a]", "-ar", "48000", str(fx)], check=True)
    hits = [{"at": round(st.anchor(h["at"], at)["start"], 2), "volume": h.get("volume", 0.9)} for h in au.get("hits", [])]
    tl = {"version": v, "total": round(total, 3), "fps": fps, "video": str(out.relative_to(st.dir)), "voice_fx": str(fx.relative_to(st.dir)),
          "scenes": [{"id": sc, "start": round(scene_start[sc], 3), "end": round(scene_end[sc], 3)} for sc in order],
          "cues": [{"state": s, "at": round(t, 3)} for t, s, _ in cues], "whooshes": [round(x, 2) for x in whooshes], "hits": hits}
    st.out("build/timeline_v%d.json" % v).write_text(json.dumps(tl, indent=1))
    print("audio", fx.relative_to(st.dir), "whooshes at", tl["whooshes"])
    print("TOTAL=%.3f" % total); print("HITS=" + json.dumps([h["at"] for h in hits]))


if __name__ == "__main__":
    main()
