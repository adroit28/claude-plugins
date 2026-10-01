#!/usr/bin/env python3
"""3D-animated Shorts with Remotion + three.js: scaffold, sync, render, check.

  anim.py init   <story.vN.json> [--force-scene]   scaffold <edit>/anim/ from templates/remotion-3d, npm install
  anim.py sync   <story>                            copy narration.audio -> anim/public/narration.wav, words -> anim/src/words.json
  anim.py render <story> [--frames 0-120]           remotion render (--gl=angle) + loudnorm -> <slug>_vN.mp4, then check
  anim.py check  <story> [--at 3.2 7.5]             contact sheets of the mp4 + loudness + loop match

init copies the template (kit/, timing.ts, Short.tsx, fonts.ts, examples/) and keeps an existing
src/Scene.tsx (the topic's scene) unless --force-scene. It writes a local .npmrc
(registry.npmjs.org: a global ~/.npmrc may point at a private registry), copies Anton and Barlow
Condensed from <shorts>/fonts, runs npm ci, approves esbuild's install script and rebuilds it.
The story gets "anim": {"dir", "template", "composition"}.

render refuses to overwrite <slug>_vN.mp4 (versions only go up; revise makes vN+1). --frames
renders a silent preview to anim/out/preview_<a>-<b>.mp4 and stops. The final file is the raw
render with loudnorm I=-14:TP=-1.5:LRA=11 (story audio.loudness overrides), video stream copied,
AAC 192k, +faststart.

check writes to build/check/: a 1 fps sheet of the whole Short, a frame sheet at every spoken
number (+0.35 s, once the pop has landed) plus --at times, the first and last frames; prints the
integrated loudness and true peak, and an SSIM of frame 0 vs the last frame above the caption
band (1.0 = a seamless loop). Sheets come from the football-shorts plugin's sheets.py.
"""
import argparse, datetime as dt, json, os, pathlib, re, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import PLUGIN, Story, duration

TEMPLATE = PLUGIN / "templates" / "remotion-3d"
FONTS = ["Anton-Regular.ttf", "BarlowCondensed-ExtraBold.ttf", "BarlowCondensed-SemiBold.ttf"]
NUMS = set("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen "
           "eighteen nineteen twenty thirty forty fifty sixty seventy eighty ninety hundred thousand million billion".split())
CAPTION_TOP = 1300


def anim_dir(st):
    return st.dir / st.data.get("anim", {}).get("dir", "anim")


def run(cmd, cwd=None, check=True):
    print("$", " ".join(str(c) for c in cmd))
    return subprocess.run([str(c) for c in cmd], cwd=cwd, check=check)


def sheets_py():
    near = PLUGIN.parent / "football-shorts" / "skills" / "build" / "scripts" / "sheets.py"
    if near.exists(): return near
    for p in (pathlib.Path.home() / ".claude/plugins").glob("**/football-shorts/**/skills/build/scripts/sheets.py"):
        return p
    sys.exit("sheets.py not found: install the football-shorts plugin (its build/scripts/sheets.py makes the check sheets)")


def sync(st):
    d = anim_dir(st); nar = st.data["narration"]
    if not nar.get("audio") or not nar.get("words"):
        sys.exit("story has no narration.audio / narration.words: run tts.py, align.py and tighten.py first")
    (d / "public").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(st.p(nar["audio"]), d / "public" / "narration.wav")
    shutil.copyfile(st.p(nar["words"]), d / "src" / "words.json")
    print("synced %s -> public/narration.wav, %s -> src/words.json (%.2f s)" % (nar["audio"], nar["words"], duration(st.p(nar["audio"]))))


def init(st, a):
    d = anim_dir(st)
    for src in TEMPLATE.rglob("*"):
        if src.is_dir() or src.name == ".gitkeep": continue
        rel = src.relative_to(TEMPLATE); dst = d / rel
        if rel.as_posix() == "src/Scene.tsx" and dst.exists() and not a.force_scene:
            print("kept   src/Scene.tsx (topic scene; --force-scene replaces it with the starter)"); continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = None
        if src.suffix == ".json" and src.name.startswith("package"):
            text = src.read_text().replace("__SLUG__", st.slug)
        if text is None: shutil.copyfile(src, dst)
        else: dst.write_text(text)
    (d / "public").mkdir(parents=True, exist_ok=True)
    for f in FONTS:
        p = st.fonts / f
        if not p.exists(): sys.exit("missing font %s (setup.sh lists the fonts)" % p)
        shutil.copyfile(p, d / "public" / f)
    (d / "out").mkdir(exist_ok=True)
    sync(st)
    if a.no_install: return
    if run(["npm", "ci", "--no-audit", "--no-fund"], cwd=d, check=False).returncode:
        run(["npm", "install", "--no-audit", "--no-fund"], cwd=d)
    run(["npm", "install-scripts", "approve", "esbuild"], cwd=d, check=False)
    run(["npm", "rebuild", "esbuild"], cwd=d)
    if not st.rendered():
        st.data["anim"] = {**st.data.get("anim", {}), "dir": d.name, "template": "remotion-3d", "composition": "Short"}
        st.save()
    print("ready: %s  (edit src/Scene.tsx; preview with: npx remotion studio src/index.ts)" % d)


def number_times(st):
    ws = json.loads(st.p(st.data["narration"]["words"]).read_text())
    out = []
    for w in ws:
        n = re.sub(r"[^a-z0-9]", "", w["w"].lower())
        if n.isdigit() or n in NUMS or any(n == a + b for a in NUMS for b in NUMS if a.endswith("ty")):
            out.append(round(w["start"] + 0.35, 2))
    return out


def check(st, a, mp4=None):
    mp4 = mp4 or st.mp4
    if not mp4.exists(): sys.exit("no %s yet: run anim.py render" % mp4.name)
    out = st.build / "check"; out.mkdir(parents=True, exist_ok=True)
    py = st.shorts / ".venv" / "bin" / "python"; sh = sheets_py()
    v = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames,r_frame_rate",
                                   "-of", "json", str(mp4)], capture_output=True, text=True).stdout)["streams"][0]
    num, den = v["r_frame_rate"].split("/"); fps = float(num) / float(den)
    dur = int(v["nb_frames"]) / fps; last = round((int(v["nb_frames"]) - 1) / fps, 3)
    run([py, sh, "fine", mp4, "--from", 0, "--to", round(dur - 0.05, 2), "--fps", 1, "--out", out])
    at = sorted(set(number_times(st) + [float(x) for x in a.at or []]))
    for i in range(0, len(at), 12):
        run([py, sh, "compare", mp4, "--at", *at[i:i + 12], "--out", out])
    run([py, sh, "compare", mp4, "--at", 0, last, "--out", out])
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
    print("number moments checked: %s" % " ".join("%g" % t for t in at))
    print("sheets in %s (Read them)" % out)


def render(st, a):
    d = anim_dir(st)
    if not (d / "node_modules").exists(): sys.exit("no %s/node_modules: run anim.py init first" % d)
    sync(st)
    if a.frames:
        out = d / "out" / ("preview_%s.mp4" % a.frames)
        run(["npx", "remotion", "render", "src/index.ts", "Short", out, "--gl=angle", "--frames=%s" % a.frames, "--muted"], cwd=d)
        print("preview:", out); return
    if st.rendered(): sys.exit("%s exists: versions only go up (the revise skill makes v%d)" % (st.mp4.name, st.version + 1))
    raw = d / "out" / ("raw_v%d.mp4" % st.version)
    run(["npx", "remotion", "render", "src/index.ts", "Short", raw, "--gl=angle"], cwd=d)
    L = {"I": -14, "TP": -1.5, "LRA": 11, **st.data.get("audio", {}).get("loudness", {})}
    run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=%s:TP=%s:LRA=%s" % (L["I"], L["TP"], L["LRA"]),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", "-movflags", "+faststart", st.mp4])
    st.data.setdefault("anim", {})["render"] = {"raw": str(raw.relative_to(st.dir)), "mp4": st.mp4.name,
                                                 "duration": round(duration(st.mp4), 2), "date": dt.date.today().isoformat()}
    st.save()
    print("wrote", st.mp4)
    check(st, a)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "sync", "render", "check"]); ap.add_argument("story")
    ap.add_argument("--force-scene", action="store_true"); ap.add_argument("--no-install", action="store_true")
    ap.add_argument("--frames", help="render a silent preview of this frame range (e.g. 0-120) and stop")
    ap.add_argument("--at", nargs="*", help="extra check times in seconds")
    a = ap.parse_args()
    st = Story(a.story)
    {"init": lambda: init(st, a), "sync": lambda: sync(st), "render": lambda: render(st, a), "check": lambda: check(st, a)}[a.cmd]()


if __name__ == "__main__":
    main()
