#!/usr/bin/env python3
"""Generate/refresh the Remotion project from the plugin's template and render the spec. No TSX editing per video.

  build.py <slug folder | edit.vN.json> [--render] [--concurrency 4] [--still SEC] [--frames A-B] [--node-modules DIR] [--force]

1. <slug>/anim/ is created from templates/remotion (package.json, tsconfig, a local .npmrc pointing at
   registry.npmjs.org because ~/.npmrc may point at a dead private registry). On every run the template's
   src/*.ts(x) and fonts are refreshed, so a plugin fix reaches old projects.
2. node_modules: a symlink to --node-modules / $THS_NODE_MODULES / ~/.cache/talking-head-shorts/node_modules
   (setup.sh --node installs it once; that is a download and needs the user's yes).
3. public/: the ORIGINAL video (hard link), the matte frames dir (hard-linked per file, when spec.matte), and every image the
   spec uses (copied from <slug>/ or <slug>/assets/). Missing cutaway w/h are filled from the image size.
4. src/edit.json = the spec, src/blink.json = probe's blink.json. Typecheck with tsc, then (with --render)
   render to anim/out/raw_v<N>.mp4 at 30 fps. Never overwrites an earlier raw_vN.mp4 (--force to redo the same N).
   --still SEC renders one PNG at output second SEC; --frames A-B renders only those frames to a preview file.
Matte PNGs are ~400 MB per 27 s of video: matte.py warns before writing them.

Multi-clip mode (docs/multi-clip.md): build.py <slug folder> --timeline   (automatic when <slug>/timeline.py exists)
   stages <slug>/timeline.json -> anim/src/timeline.json, <slug>/track.json (if any) -> anim/src/track.json,
   <slug>/norm/*.mp4 -> anim/public/clips/<name>.mp4 (hard links), files in <slug>/assets/ -> anim/public/, refreshes the
   template (Multi.tsx, Root.tsx, kit/, fonts, grain.png) but NEVER overwrites anim/src/Scenes.tsx (copied the first time only),
   typechecks, and with --render renders composition `Multi` to anim/out/raw_v<N>.mp4 (N = next free number; --force redoes the
   latest). --still SEC and --frames A-B work as above (outputs still_v<N>_<frame>.png / preview_v<N>_<A-B>.mp4).
"""
import argparse, json, os, pathlib, re, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import PLUGIN, FPS, load_spec, out_seconds, sec

TEMPLATE = PLUGIN / "templates" / "remotion"
REFRESH = ["src/Short.tsx", "src/Root.tsx", "src/index.ts", "src/fonts.ts", "src/types.ts", "tsconfig.json", "remotion.config.ts", "src/Multi.tsx"]


def refresh_kit(anim):
    """Root.tsx registers the Multi composition too, so every project needs the kit + placeholders. User files are never replaced."""
    shutil.copytree(TEMPLATE / "src" / "kit", anim / "src" / "kit", dirs_exist_ok=True)
    for rel in ("src/timeline.json", "src/track.json", "src/Scenes.tsx"):
        if not (anim / rel).exists():
            shutil.copy2(TEMPLATE / rel, anim / rel)
    shutil.copytree(TEMPLATE / "public" / "fonts", anim / "public" / "fonts", dirs_exist_ok=True)
    if (TEMPLATE / "public" / "grain.png").exists():
        shutil.copy2(TEMPLATE / "public" / "grain.png", anim / "public" / "grain.png")


def hard_link(dst, src):
    """Remotion's static server 404s on symlinked files, so use a hard link (no extra disk), else copy."""
    if dst.is_symlink() or dst.is_file():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def main_timeline(a, tgt):
    folder = tgt if tgt.is_dir() else tgt.parent
    folder = folder.resolve()
    tl = folder / "timeline.json"
    if not tl.exists():
        sys.exit("%s is missing: run timeline.py first" % tl)
    timeline = json.loads(tl.read_text())
    anim = folder / "anim"
    if not anim.exists():
        shutil.copytree(TEMPLATE, anim, ignore=shutil.ignore_patterns("node_modules", "out"))
        pj = anim / "package.json"
        pj.write_text(pj.read_text().replace("__SLUG__", folder.name))
    for rel in REFRESH:
        (anim / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / rel, anim / rel)
    refresh_kit(anim)  # Scenes.tsx is only copied when missing
    if not (anim / ".npmrc").exists():
        shutil.copy2(TEMPLATE / ".npmrc", anim / ".npmrc")
    pub = anim / "public"
    nm = anim / "node_modules"
    if not nm.exists():
        cand = a.node_modules or os.environ.get("THS_NODE_MODULES") or str(pathlib.Path.home() / ".cache/talking-head-shorts/node_modules")
        if not pathlib.Path(cand).is_dir():
            sys.exit("no node_modules for the Remotion project. Pass --node-modules <dir with remotion 4.0.530> or run setup.sh --node "
                     "(a download: needs the user's yes).")
        nm.symlink_to(pathlib.Path(cand).resolve())
    # Root.tsx also registers `Short`, which imports edit.json/blink.json: give a timeline-only project inert stubs (never replaced)
    st = anim / "src"
    if not (st / "edit.json").exists():
        (st / "edit.json").write_text(json.dumps({
            "schema": "talking-head-shorts/1", "slug": folder.name, "version": 1,
            "source": {"file": "none.mp4", "start": 0, "end": 1, "w": 1080, "h": 1920, "fit": "cover"},
            "style": {"font": "Anton", "fontFile": "fonts/Anton-Regular.ttf", "accent": "#FF2D2D", "current": "#FFD60A", "text": "#FFFFFF",
                      "captionSize": 100, "captionTop": 1300, "captionWidth": 900, "captionStroke": 12, "captionGap": 30, "grade": "none", "vignette": False},
            "hook": {"kind": "none"}, "phrases": [], "hot": [], "steps": [[0, 1]], "drift": 0, "origin": "540px 1000px", "shakes": [], "flashes": [],
            "cutaways": [], "pills": [], "counters": [], "slams": [], "bg": None, "matte": None, "sfx": [], "hook_sfx": [],
            "music": {"drone": False}, "outro": {"seconds": 0}}))
    if not (st / "blink.json").exists():
        (st / "blink.json").write_text(json.dumps({"fps": 30, "values": []}))
    # stage data, clips and the user's images
    shutil.copy2(tl, anim / "src" / "timeline.json")
    tr = folder / "track.json"
    (anim / "src" / "track.json").write_text(tr.read_text() if tr.exists() else "{}")
    (pub / "clips").mkdir(parents=True, exist_ok=True)
    clips = sorted((folder / "norm").glob("*.mp4"))
    for f in clips:
        hard_link(pub / "clips" / f.name, f)
    need = {pathlib.Path(v["video"]).name for v in timeline.get("files", {}).values() if v.get("video")}
    missing = sorted(n for n in need if not (pub / "clips" / n).exists())
    if missing:
        sys.exit("timeline.json needs clips %s but %s/norm has no such file: run normalize.py" % (missing, folder))
    assets = folder / "assets"
    nassets = 0
    if assets.is_dir():
        for f in assets.iterdir():
            if f.is_file():
                shutil.copy2(f, pub / f.name); nassets += 1
    total = timeline["total"]
    print("project:", anim, "| timeline %.2f s (%d frames) | %d clips, %d assets" % (total, sec(total), len(clips), nassets))

    if not a.no_tsc and (nm / ".bin" / "tsc").exists():
        r = subprocess.run([str(nm / ".bin" / "tsc"), "-p", str(anim)], capture_output=True, text=True)
        if r.returncode:
            sys.exit("typecheck failed:\n" + (r.stdout + r.stderr)[:2000])
        print("typecheck ok")
    if not (a.render or a.still is not None or a.frames):
        return
    rem = str(nm / ".bin" / "remotion")
    out = anim / "out"
    out.mkdir(exist_ok=True)
    have = [int(m.group(1)) for f in out.glob("raw_v*.mp4") for m in [re.fullmatch(r"raw_v(\d+)\.mp4", f.name)] if m]
    n = (max(have) if (a.force and have) else (max(have) + 1 if have else 1))
    if a.still is not None:
        f = min(sec(total) - 1, sec(a.still))
        dst = out / ("still_v%d_%04d.png" % (n, f))
        subprocess.run([rem, "still", "src/index.ts", "Multi", str(dst), "--frame=%d" % f], cwd=anim, check=True)
        print("still:", dst); return
    dst = out / ("raw_v%d.mp4" % n if not a.frames else "preview_v%d_%s.mp4" % (n, a.frames))
    cmd = [rem, "render", "src/index.ts", "Multi", str(dst), "--concurrency=%d" % a.concurrency]
    if a.frames: cmd.append("--frames=" + a.frames)
    subprocess.run(cmd, cwd=anim, check=True)
    print("rendered:", dst)


def find_asset(folder, name):
    for d in (folder, folder / "assets"):
        if (d / name).exists():
            return d / name
    return None


def image_size(p):
    import cv2
    im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
    return (im.shape[1], im.shape[0]) if im is not None else None


def fit_box(w, h, maxw=1080, maxh=900):
    k = min(maxw / w, maxh / h)
    if w * k > 1080: k = 1080 / w
    return int(round(w * k)), int(round(h * k))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target"); ap.add_argument("--render", action="store_true"); ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--still", type=float); ap.add_argument("--frames"); ap.add_argument("--node-modules"); ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-tsc", action="store_true"); ap.add_argument("--timeline", action="store_true", help="multi-clip mode (automatic when <slug>/timeline.py exists)")
    a = ap.parse_args()
    tgt = pathlib.Path(a.target).expanduser().resolve()
    if a.timeline or (tgt.is_dir() and (tgt / "timeline.py").exists()):
        return main_timeline(a, tgt)
    specpath, spec = load_spec(pathlib.Path(a.target).expanduser().resolve())
    folder = specpath.parent
    anim = folder / "anim"
    first = not anim.exists()
    if first:
        shutil.copytree(TEMPLATE, anim, ignore=shutil.ignore_patterns("node_modules", "out"))
        pj = anim / "package.json"
        pj.write_text(pj.read_text().replace("__SLUG__", spec["slug"]))
    for rel in REFRESH:
        (anim / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(TEMPLATE / rel, anim / rel)
    refresh_kit(anim)
    if not (anim / ".npmrc").exists():
        shutil.copy2(TEMPLATE / ".npmrc", anim / ".npmrc")
    pub = anim / "public"

    nm = anim / "node_modules"
    if not nm.exists():
        cand = a.node_modules or os.environ.get("THS_NODE_MODULES") or str(pathlib.Path.home() / ".cache/talking-head-shorts/node_modules")
        if not pathlib.Path(cand).is_dir():
            sys.exit("no node_modules for the Remotion project. Pass --node-modules <dir with remotion 4.0.530> or run setup.sh --node "
                     "(a download: needs the user's yes).")
        nm.symlink_to(pathlib.Path(cand).resolve())

    def hard(dst, src):
        """Remotion's static server 404s on symlinked files, so use a hard link (no extra disk), else copy."""
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)

    def link(dst, src):
        src = pathlib.Path(src)
        if src.is_dir():
            if dst.is_symlink():
                dst.unlink()
            dst.mkdir(exist_ok=True)
            for f in src.iterdir():
                if f.is_file():
                    hard(dst / f.name, f)
        else:
            hard(dst, src)

    srcfile = (folder / spec["source"]["file"]).resolve()
    link(pub / spec["source"]["file"], srcfile)
    if spec.get("matte"):
        m = spec["matte"]
        mdir = (folder / m["dir"]).resolve()
        if not mdir.is_dir():
            sys.exit("spec.matte.dir %s is missing: run matte.py first" % mdir)
        link(pub / m["dir"], mdir)
        spec["matte"]["count"] = len(list(mdir.glob("f*.png")))
        if (mdir / "matte.json").exists():
            spec["matte"]["start"] = json.loads((mdir / "matte.json").read_text())["start"]

    names = [c["src"] for c in spec["cutaways"]]
    if spec["hook"]["kind"] == "image": names.append(spec["hook"]["image"])
    if spec.get("bg"): names.append(spec["bg"]["image"])
    for n in dict.fromkeys(names):
        p = find_asset(folder, n)
        if not p:
            sys.exit("image %s not found in %s or %s/assets" % (n, folder, folder))
        shutil.copy2(p, pub / n)
        sz = image_size(pub / n)
        for c in spec["cutaways"]:
            if c["src"] == n and sz and ("w" not in c or "h" not in c):
                c["w"], c["h"] = fit_box(*sz)
        if spec.get("bg") and spec["bg"]["image"] == n and sz:
            spec["bg"].setdefault("w", sz[0]); spec["bg"].setdefault("h", sz[1])
    (anim / "src").mkdir(exist_ok=True)
    (anim / "src" / "edit.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    blink = folder / "blink.json"
    (anim / "src" / "blink.json").write_text(blink.read_text() if blink.exists() else json.dumps({"fps": 30, "values": []}))
    print("project:", anim, "| spec v%d | output %.2f s (%d frames)" % (spec["version"], out_seconds(spec), sec(out_seconds(spec))))

    rem = str(nm / ".bin" / "remotion")
    if not a.no_tsc and (nm / ".bin" / "tsc").exists():
        r = subprocess.run([str(nm / ".bin" / "tsc"), "-p", str(anim)], capture_output=True, text=True)
        if r.returncode:
            sys.exit("typecheck failed:\n" + (r.stdout + r.stderr)[:2000])
        print("typecheck ok")
    if not (a.render or a.still is not None):
        return
    out = anim / "out"
    out.mkdir(exist_ok=True)
    v = spec["version"]
    if a.still is not None:
        f = min(sec(out_seconds(spec)) - 1, sec(a.still))
        dst = out / ("still_v%d_%04d.png" % (v, f))
        subprocess.run([rem, "still", "src/index.ts", "Short", str(dst), "--frame=%d" % f], cwd=anim, check=True)
        print("still:", dst); return
    name = "raw_v%d.mp4" % v if not a.frames else "preview_v%d_%s.mp4" % (v, a.frames)
    dst = out / name
    if dst.exists() and not a.force and not a.frames:
        sys.exit("%s exists: versions are never overwritten (bump the spec, or --force to redo this one)" % dst)
    cmd = [rem, "render", "src/index.ts", "Short", str(dst), "--concurrency=%d" % a.concurrency]
    if a.frames: cmd.append("--frames=" + a.frames)
    subprocess.run(cmd, cwd=anim, check=True)
    print("rendered:", dst)


if __name__ == "__main__":
    main()
