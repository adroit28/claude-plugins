#!/usr/bin/env python3
"""2D explainer Shorts with Remotion: scaffold, sync, render, check.

  anim.py init   <story.vN.json> [--force-scene] [--no-install]   scaffold <edit>/anim/ from templates/remotion-2d, npm ci
  anim.py sync   <story>                     narration -> public/narration.wav, words -> src/words.json,
                                             channel.json -> src/channel.json, src/ images -> public/ (sizes -> src/images.json)
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

0.8.0 story options ("video" block, all optional): "captions": false | "hotCaptions": true (word-by-word captions, the
story's CAPS words hot; "hot": ["galti", "L3:dhakel", "L5:nahi#2"] overrides them) | "music": true (a synthesized bed,
ducked under the narration, mixed in at render) | "grain": true or 0.02-0.08 (film grain, default off: it bloats the file).
sync writes them to src/options.json; render also warns when an sfx peak lands on a HOT word (sfxprobe.mjs).

check writes to build/check/: a 1 fps sheet of the whole Short, frames at --at times, the first
and last frames side by side; prints duration, loudness, true peak, and the SSIM of frame 0 vs the
last frame above the caption band (1.0 = seamless loop). Stdlib + ffmpeg + node/npm.
"""
import argparse, datetime as dt, json, math, os, pathlib, re, shutil, subprocess, sys
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


def img_size(p):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(p)], capture_output=True, text=True)
    try: w, h = (int(v) for v in r.stdout.strip().split(",")[:2]); return [w, h]
    except ValueError: return None  # svg or unreadable: the Card falls back to w x 900


def _clean(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def _words(st):
    j = json.loads(st.p(st.data["narration"]["words"]).read_text())
    return j.get("words", j) if isinstance(j, dict) else j


def hot_words(st):
    """[[line, word index]] of the HOT caption words: the story's `video.hot` list if given ("galti" = every match,
    "L3:dhakel", "L5:nahi#2" = second match in that line, or a [line, i] pair), else the CAPS words of each line's tts
    (the spoken text; falls back to the caption text). A CAPS token is matched to the same word (nth occurrence) in the
    line's caption words, so a spelled-out number or a <pause> tag never shifts it."""
    words = _words(st); out = []
    def find(line, key, nth):
        hits = [w for w in words if w["line"] == line and _clean(w["w"]) == key]
        return [hits[nth - 1]["i"]] if len(hits) >= nth else []
    override = st.data.get("video", {}).get("hot")
    if override is not None:
        for item in override:
            if isinstance(item, (list, tuple)): out.append([item[0], int(item[1])]); continue
            line, _, rest = item.rpartition(":"); key, _, nth = rest.partition("#"); key = _clean(key)
            lines = [line] if line else sorted({w["line"] for w in words})
            for l in lines:
                n = int(nth) if nth else None
                hits = [w for w in words if w["line"] == l and _clean(w["w"]) == key]
                for h in (hits[n - 1:n] if n else hits): out.append([l, h["i"]])
        return out
    for ln in st.data["narration"].get("lines", []):
        toks = re.sub(r"<[^>]*>", " ", ln.get("tts") or ln.get("text", "")).split(); seen = {}
        for tok in toks:
            key = _clean(tok); letters = re.sub(r"[^A-Za-z]", "", tok)
            if not key: continue
            seen[key] = seen.get(key, 0) + 1
            if len(letters) >= 2 and letters.isupper(): out += [[ln["id"], i] for i in find(ln["id"], key, seen[key])]
    return out


def hot_labels(st, hot):
    byk = {(w["line"], w["i"]): w["w"] for w in _words(st)}
    return [(l, byk.get((l, i), "?").strip(".,!?:;").lower()) for l, i in hot]


def sync(st):
    d = anim_dir(st); nar = st.data["narration"]
    if not nar.get("audio") or not nar.get("words"):
        sys.exit("story has no narration.audio / narration.words: run tts.py and segalign.py first")
    (d / "public").mkdir(parents=True, exist_ok=True); (d / "src").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(st.p(nar["audio"]), d / "public" / "narration.wav")
    shutil.copyfile(st.p(nar["words"]), d / "src" / "words.json")
    ch = channel(st.root)
    # captions are optional: story "video": {"captions": false} hides them (default on)
    vid = st.data.get("video", {})
    hot = hot_words(st) if vid.get("hotCaptions") else []
    grain = vid.get("grain", 0); grain = 0.06 if grain is True else min(float(grain or 0), 0.08)
    (d / "src" / "options.json").write_text(json.dumps({"captions": vid.get("captions", True), "hotCaptions": bool(vid.get("hotCaptions")),
                                                        "hot": hot, "music": bool(vid.get("music")), "grain": grain}))
    if hot: print("hot words:", " ".join("%s:%s" % (l, w) for l, w in hot_labels(st, hot)))
    (d / "src" / "channel.json").write_text(json.dumps({k: ch[k] for k in ("name", "tagline", "avatar")}, ensure_ascii=False))
    imgs = [p for p in sorted((st.dir / "src").glob("*")) if p.suffix.lower() in IMG] if (st.dir / "src").exists() else []
    for p in imgs: shutil.copyfile(p, d / "public" / p.name)
    # pixel size of every photo, so a Card without h takes the photo's shape instead of cropping it
    (d / "src" / "images.json").write_text(json.dumps({p.name: s for p in imgs if (s := img_size(p))}, ensure_ascii=False))
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
    # a negative time counts back from the end of the file (-0.05 = the last frame): `-ss <last frame time>` can seek past
    # the final frame, give no frame, and crash the xstack with ffmpeg exit 234
    for t in times: cmd += (["-sseof", "%.3f" % t] if t < 0 else ["-ss", "%.3f" % t]) + ["-i", str(mp4)]
    fc = ";".join("[%d:v]trim=end_frame=1,scale=%d:-2[v%d]" % (i, w, i) for i in range(len(times)))
    rows = (len(times) + cols - 1) // cols; pad = rows * cols - len(times)
    if pad:
        fc += ";" + ";".join("color=black:s=%dx%d:d=1,trim=end_frame=1[p%d]" % (w, w * 16 // 9, k) for k in range(pad))
    tiles = ["[v%d]" % i for i in range(len(times))] + ["[p%d]" % k for k in range(pad)]
    layout = "|".join("%d_%d" % (c * w, r * (w * 16 // 9)) for r in range(rows) for c in range(cols))
    fc += ";" + "".join(tiles) + ("xstack=inputs=%d:layout=%s[out]" % (len(tiles), layout) if len(tiles) > 1 else "null[out]")
    subprocess.run(cmd + ["-filter_complex", fc, "-map", "[out]", "-frames:v", "1", "-q:v", "3", str(out)], check=True)
    print("  %s: %s" % (out.name, " ".join("%g" % t for t in times)))


def loop_ssim(mp4, last):
    """SSIM of frame 0 vs the last frame above the caption band (1.0 = seamless loop); None if ffmpeg gives no number.
    The crop scales with the frame, and a second try seeks slightly earlier in case the last frame can't be decoded."""
    crop = "crop=iw:ih*%d/1920:0:0" % CAPTION_TOP
    for seek in (["-sseof", "-0.05"], ["-ss", str(max(last - 0.05, 0))]):
        ss = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4)] + seek + ["-i", str(mp4), "-filter_complex",
                             "[0:v]trim=end_frame=1,%s[a];[1:v]trim=end_frame=1,%s[b];[a][b]ssim" % (crop, crop), "-f", "null", "-"],
                            capture_output=True, text=True).stderr
        m = re.search(r"All:\s*([\d.]+|inf)", ss)
        if m: return 1.0 if m.group(1) == "inf" else float(m.group(1))
    return None


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
    loop = out / ("%s_loop.jpg" % tag)
    sheet(mp4, loop, [0, -0.05], cols=2, w=360)
    ln = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(mp4), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    j = json.loads(ln[ln.rindex("{"):ln.rindex("}") + 1])
    sim = loop_ssim(mp4, last)
    print("duration %.2f s · loudness %s LUFS · true peak %s dBTP · loop SSIM %s (frame 0 vs last frame, above y %d)"
          % (dur, j["input_i"], j["input_tp"], "%.4f" % sim if sim is not None else "?", CAPTION_TOP))
    if sim is None: print("WARN: loop SSIM could not be measured; compare the first and last tiles in %s_loop.jpg by eye" % tag)
    elif sim < 0.7: print("WARN: loop SSIM %.2f < 0.7: the last frame does not match the first (a stamp/badge left on screen? an object not back in place?)" % sim)
    target = float({"I": -14, **st.data.get("audio", {}).get("loudness", {})}["I"])
    try: lufs = float(j["input_i"])
    except ValueError: lufs = None
    if lufs is None or abs(lufs - target) > 2: print("WARN: loudness %s LUFS is more than 2 LU from the target %g" % (j["input_i"], target))
    print("sheets in %s (tiles left to right, top to bottom, times as listed above; Read them)" % out)


def still(st, a):
    d = anim_dir(st); out = st.build / "check"; out.mkdir(parents=True, exist_ok=True)
    for t in a.at or []:
        f = round(float(t) * 30)
        run(["npx", "remotion", "still", "src/index.ts", "Short", os.path.relpath(out / ("still_%s.png" % t), d), "--frame=%d" % f], cwd=d)  # relative: remotion cuts absolute paths at a space


def sfx_check(st, d):
    """Warn (never drop) when a sound effect's PEAK lands on a HOT caption word: an sfx on the key word hides it. Needs the
    story's hotCaptions; finds the <Sfx at src> elements by running Scene.Overlays at many times (sfxprobe.mjs, esbuild from
    the Short's node_modules). A scene it can't probe is skipped with a note."""
    if not st.data.get("video", {}).get("hotCaptions"): return
    probe = PLUGIN / "scripts" / "sfxprobe.mjs"
    try: r = subprocess.run(["node", str(probe), str(d), str(duration(st.p(st.data["narration"]["audio"])))], capture_output=True, text=True, timeout=90)
    except subprocess.TimeoutExpired:
        print("sfx check skipped: probing the scene timed out"); return
    try: cues = json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        print("sfx check skipped: could not read the scene's Sfx times (%s)" % (r.stderr.strip().splitlines() or ["no output"])[-1][:160]); return
    import wave
    hot = set(map(tuple, json.loads((d / "src" / "options.json").read_text()).get("hot", []))); wl = _words(st); bad = 0
    def peak(src):
        try:
            with wave.open(str(d / "public" / "sfx" / ("%s.wav" % src))) as w:
                raw = w.readframes(w.getnframes()); sr = w.getframerate()
            vals = [abs(int.from_bytes(raw[i:i + 2], "little", signed=True)) for i in range(0, len(raw) - 1, 2 * 8)]
            return vals.index(max(vals)) * 8 / sr
        except (OSError, ValueError, wave.Error): return 0.0
    for c in cues:
        pk = c["at"] + peak(c["src"])
        for w in wl:
            if (w["line"], w["i"]) in hot and w["start"] - 0.03 <= pk <= w["end"]:
                bad += 1; print("WARN sfx %r at %.2f s peaks at %.2f s on the HOT word %r (%s, %.2f-%.2f s): move it before the word or after it" % (c["src"], c["at"], pk, w["w"], w["line"], w["start"], w["end"]))
    print("sfx check: %d cue(s), %d on a hot word" % (len(cues), bad))


def render(st, a):
    d = anim_dir(st)
    if not (d / "node_modules").exists(): sys.exit("no %s/node_modules: run anim.py init first" % d)
    sync(st)
    import sfx as sfxlib
    missing = [n for n in sfxlib.LIB if not (d / "public" / "sfx" / ("%s.wav" % n)).exists()]
    if missing:   # first render, or a Short made before 0.8.0 that has not got the new sounds yet
        print("sound effects missing in %s (%s): running sfx.py" % (d / "public" / "sfx", " ".join(missing[:6]) + (" ..." if len(missing) > 6 else "")))
        run([sys.executable, PLUGIN / "scripts" / "sfx.py", st.path])
    sfx_check(st, d)
    if a.frames:
        out = d / "out" / ("preview_%s.mp4" % a.frames)
        run(["npx", "remotion", "render", "src/index.ts", "Short", "out/preview_%s.mp4" % a.frames, "--frames=%s" % a.frames, "--muted"], cwd=d)
        print("preview:", out); return
    if st.rendered(): sys.exit("%s exists: versions only go up (the revise skill makes v%d)" % (st.mp4.name, st.version + 1))
    raw = d / "out" / ("raw_v%d.mp4" % st.version)
    # relative output: Remotion runs in anim/ and has cut an absolute path at a space ("personal projects")
    run(["npx", "remotion", "render", "src/index.ts", "Short", "out/%s" % raw.name], cwd=d)
    if not raw.exists():
        sys.exit("render output not found; look for %s in the parent folder (and %s), then move it to %s" % (raw.name, d, raw))
    st.build.mkdir(exist_ok=True)
    shutil.copyfile(d / "src" / "Scene.tsx", st.build / ("scene_v%d.tsx" % st.version))
    L = {"I": -14, "TP": -1.5, "LRA": 11, **st.data.get("audio", {}).get("loudness", {})}
    norm = "loudnorm=I=%s:TP=%s:LRA=%s" % (L["I"], L["TP"], L["LRA"])
    out_opts = ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", st.mp4]
    if st.data.get("video", {}).get("music"):
        # music bed: synthesized once per Short, ducked by the narration (sidechain: the voice is the key), mixed with the
        # raw render's own audio (narration + sfx), then loudnorm over everything so the file lands on -14 LUFS / TP -1.5
        mus = d / "public" / "music.wav"; need = math.ceil(duration(raw)) + 1
        if not mus.exists() or duration(mus) < need - 0.5:
            run([sys.executable, PLUGIN / "scripts" / "sfx.py", st.path, "--music", "--seconds", need])
        gain = float(st.data.get("video", {}).get("musicGain", 0.45))
        fc = ("[1:a]volume=%g,afade=t=in:d=0.6,afade=t=out:st=%.2f:d=0.8[m];[m][2:a]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=400:makeup=1[dk];"
              "[0:a][dk]amix=inputs=2:duration=first:normalize=0,%s[a]") % (gain, duration(raw) - 0.8, norm)
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-i", mus, "-i", d / "public" / "narration.wav", "-filter_complex", fc, "-map", "0:v", "-map", "[a]"] + out_opts)
    else:
        run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", norm] + out_opts)
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
