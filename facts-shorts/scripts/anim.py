#!/usr/bin/env python3
"""2D explainer Shorts with Remotion: scaffold, sync, render, check.

  anim.py init   <story.vN.json> [--force-scene] [--no-install]   scaffold <edit>/anim/ from templates/remotion-2d, npm ci
  anim.py sync   <story>                     narration -> public/narration.wav, words -> src/words.json,
                                             channel.json -> src/channel.json, src/ images -> public/
  anim.py render <story> [--frames 0-120]    remotion render + loudnorm -> <slug>_vN.mp4, Scene.tsx snapshot, then check
  anim.py still  <story> --at 3.2 7.5        single frames -> build/check/still_<t>.png (fast look at a moment)
  anim.py check  <story> [--at 3.2 7.5]      sheets of the mp4 + loudness + loop match

init copies the template and keeps an existing src/Scene.tsx unless --force-scene. It writes a
local .npmrc (registry.npmjs.org; a global ~/.npmrc may point at a private registry), copies Anton
and Barlow Condensed from the fonts folder (<content>/fonts or ../shorts/fonts), syncs, runs npm ci
and approves esbuild's install script. The story gets "anim": {"dir", "template", "composition"}.

render refuses to overwrite <slug>_vN.mp4 (versions only go up; revise makes vN+1) and copies
src/Scene.tsx to build/scene_vN.tsx so every version's scene is kept. --frames renders a silent
preview to anim/out/preview_<a>-<b>.mp4 and stops. The final file is the raw render with loudnorm
I=-14:TP=-1.5:LRA=11, video stream copied, AAC 192k, +faststart.

check writes to build/check/: a 1 fps sheet of the whole Short, frames at --at times, the first
and last frames side by side; prints duration, loudness, true peak, and the SSIM of frame 0 vs the
last frame above the caption band (1.0 = seamless loop). Stdlib + ffmpeg + node/npm.
"""
import argparse, datetime as dt, json, pathlib, re, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import FONTS, PLUGIN, Story, channel, duration, fonts_dir

TEMPLATE = PLUGIN / "templates" / "remotion-2d"
CAPTION_TOP = 1300
IMG = (".jpg", ".jpeg", ".png", ".webp", ".svg")


def anim_dir(st):
    return st.dir / st.data.get("anim", {}).get("dir", "anim")


def run(cmd, cwd=None, check=True, quiet=False):
    if not quiet: print("$", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=cwd, check=check)


def sync(st):
    d = anim_dir(st); nar = st.data["narration"]
    if not nar.get("audio") or not nar.get("words"):
        sys.exit("story has no narration.audio / narration.words: run tts.py and segalign.py first")
    (d / "public").mkdir(parents=True, exist_ok=True); (d / "src").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(st.p(nar["audio"]), d / "public" / "narration.wav")
    shutil.copyfile(st.p(nar["words"]), d / "src" / "words.json")
    ch = channel(st.root)
    # captions are optional: story "video": {"captions": false} hides them (default on)
    (d / "src" / "options.json").write_text(json.dumps({"captions": st.data.get("video", {}).get("captions", True)}))
    (d / "src" / "channel.json").write_text(json.dumps({k: ch[k] for k in ("name", "tagline", "avatar")}, ensure_ascii=False))
    imgs = [p for p in sorted((st.dir / "src").glob("*")) if p.suffix.lower() in IMG] if (st.dir / "src").exists() else []
    for p in imgs: shutil.copyfile(p, d / "public" / p.name)
    print("synced narration (%.2f s), words, channel card, %d image(s) from src/" % (duration(st.p(nar["audio"])), len(imgs)))


def init(st, a):
    d = anim_dir(st)
    for src in TEMPLATE.rglob("*"):
        if src.is_dir() or src.name == ".gitkeep" or "node_modules" in src.parts: continue
        rel = src.relative_to(TEMPLATE); dst = d / rel
        if rel.as_posix() == "src/Scene.tsx" and dst.exists() and not a.force_scene:
            print("kept   src/Scene.tsx (topic scene; --force-scene replaces it with the starter)"); continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.name == "package.json": dst.write_text(src.read_text().replace("__SLUG__", st.slug))
        else: shutil.copyfile(src, dst)
    (d / "public").mkdir(parents=True, exist_ok=True); (d / "out").mkdir(exist_ok=True)
    fd = fonts_dir(st.root)
    if not fd: sys.exit("fonts not found: put %s in %s/fonts (Google Fonts, OFL) or set FACTS_FONTS" % (", ".join(FONTS), st.root))
    for f in FONTS: shutil.copyfile(fd / f, d / "public" / f)
    sync(st)
    if not a.no_install:
        if run(["npm", "ci", "--no-audit", "--no-fund"], cwd=d, check=False).returncode:
            run(["npm", "install", "--no-audit", "--no-fund"], cwd=d)
        run(["npm", "install-scripts", "approve", "esbuild"], cwd=d, check=False)
        run(["npm", "rebuild", "esbuild"], cwd=d, check=False)
    if not st.rendered():
        st.data["anim"] = {**st.data.get("anim", {}), "dir": d.name, "template": "remotion-2d", "composition": "Short"}
        st.save()
    print("ready: %s  (write src/Scene.tsx; check types with: npx tsc --noEmit -p .)" % d)


def probe(mp4):
    v = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate",
                                   "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
    num, den = v["r_frame_rate"].split("/"); fps = float(num) / float(den); n = int(v["nb_frames"])
    return fps, n / fps, round((n - 1) / fps, 3)


def sheet(mp4, out, times, cols=6, w=270):
    """Frames at `times` tiled left to right, top to bottom -> out (jpg). No burned-in labels (Homebrew
    ffmpeg has no drawtext), so the caller prints the times in tile order."""
    cmd = ["ffmpeg", "-v", "error", "-y"]
    for t in times: cmd += ["-ss", "%.3f" % t, "-i", str(mp4)]
    fc = ";".join("[%d:v]trim=end_frame=1,scale=%d:-2[v%d]" % (i, w, i) for i in range(len(times)))
    rows = (len(times) + cols - 1) // cols; pad = rows * cols - len(times)
    if pad:
        fc += ";" + ";".join("color=black:s=%dx%d:d=1,trim=end_frame=1[p%d]" % (w, w * 16 // 9, k) for k in range(pad))
    tiles = ["[v%d]" % i for i in range(len(times))] + ["[p%d]" % k for k in range(pad)]
    layout = "|".join("%d_%d" % (c * w, r * (w * 16 // 9)) for r in range(rows) for c in range(cols))
    fc += ";" + "".join(tiles) + ("xstack=inputs=%d:layout=%s[out]" % (len(tiles), layout) if len(tiles) > 1 else "null[out]")
    subprocess.run(cmd + ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    print("  %s: %s" % (out.name, " ".join("%g" % t for t in times)))


def check(st, a, mp4=None):
    mp4 = mp4 or st.mp4
    if not mp4.exists(): sys.exit("no %s yet: run anim.py render" % mp4.name)
    out = st.build / "check"; out.mkdir(parents=True, exist_ok=True)
    fps, dur, last = probe(mp4); tag = mp4.stem
    secs = [float(s) for s in range(0, int(dur))] + ([round(dur - 0.1, 2)] if dur % 1 > 0.2 else [])
    for k in range(0, len(secs), 24):
        sheet(mp4, out / ("%s_1fps_%02d.jpg" % (tag, k // 24 + 1)), secs[k:k + 24])
    if a.at:
        sheet(mp4, out / ("%s_at.jpg" % tag), [float(x) for x in a.at], cols=min(6, len(a.at)), w=360)
    sheet(mp4, out / ("%s_loop.jpg" % tag), [0, last], cols=2, w=360)
    ln = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    j = json.loads(ln[ln.rindex("{"):ln.rindex("}") + 1])
    crop = "crop=1080:%d:0:0" % CAPTION_TOP
    ss = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-ss", str(last), "-i", str(mp4), "-filter_complex",
                         "[0:v]trim=end_frame=1,%s[a];[1:v]trim=end_frame=1,%s[b];[a][b]ssim" % (crop, crop), "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    m = re.search(r"All:([\d.]+)", ss)
    print("duration %.2f s · loudness %s LUFS · true peak %s dBTP · loop SSIM %s (frame 0 vs last frame, above y %d)"
          % (dur, j["input_i"], j["input_tp"], m.group(1) if m else "?", CAPTION_TOP))
    print("sheets in %s (tiles left to right, top to bottom, times as listed above; Read them)" % out)


def still(st, a):
    d = anim_dir(st); out = st.build / "check"; out.mkdir(parents=True, exist_ok=True)
    for t in a.at or []:
        f = round(float(t) * 30)
        run(["npx", "remotion", "still", "src/index.ts", "Short", out / ("still_%s.png" % t), "--frame=%d" % f], cwd=d)


def render(st, a):
    d = anim_dir(st)
    if not (d / "node_modules").exists(): sys.exit("no %s/node_modules: run anim.py init first" % d)
    sync(st)
    if a.frames:
        out = d / "out" / ("preview_%s.mp4" % a.frames)
        run(["npx", "remotion", "render", "src/index.ts", "Short", out, "--frames=%s" % a.frames, "--muted"], cwd=d)
        print("preview:", out); return
    if st.rendered(): sys.exit("%s exists: versions only go up (the revise skill makes v%d)" % (st.mp4.name, st.version + 1))
    raw = d / "out" / ("raw_v%d.mp4" % st.version)
    run(["npx", "remotion", "render", "src/index.ts", "Short", raw], cwd=d)
    st.build.mkdir(exist_ok=True)
    shutil.copyfile(d / "src" / "Scene.tsx", st.build / ("scene_v%d.tsx" % st.version))
    L = {"I": -14, "TP": -1.5, "LRA": 11, **st.data.get("audio", {}).get("loudness", {})}
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=%s:TP=%s:LRA=%s" % (L["I"], L["TP"], L["LRA"]),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", st.mp4])
    st.data.setdefault("anim", {})["render"] = {"raw": str(raw.relative_to(st.dir)), "mp4": st.mp4.name, "scene": "build/scene_v%d.tsx" % st.version,
                                                 "duration": round(duration(st.mp4), 2), "date": dt.date.today().isoformat()}
    st.save()
    print("wrote", st.mp4)
    check(st, a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "sync", "render", "still", "check"]); ap.add_argument("story")
    ap.add_argument("--force-scene", action="store_true"); ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--frames", help="render a silent preview of this frame range (e.g. 0-120) and stop")
    ap.add_argument("--at", nargs="*", help="times in seconds (check: extra frame sheet; still: frames to render)")
    a = ap.parse_args()
    st = Story(a.story)
    {"init": lambda: init(st, a), "sync": lambda: sync(st), "render": lambda: render(st, a),
     "still": lambda: still(st, a), "check": lambda: check(st, a)}[a.cmd]()


if __name__ == "__main__":
    main()
