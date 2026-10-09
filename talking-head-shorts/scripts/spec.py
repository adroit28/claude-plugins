#!/usr/bin/env python3
"""The edit spec: create it, check it, show it as a timeline, and change it by ops (a new version each time).

  spec.py init     <slug folder> [--fit cover|crop|blurfill] [--crop x,y,w,h] [--start S --end E]
  spec.py validate <folder|edit.vN.json>
  spec.py show     <folder|edit.vN.json>                  every event in time order (the plan table, the revise map)
  spec.py fill     <folder> --ops ops.txt                 apply ops IN PLACE to the latest spec, only while that version has never been rendered
  spec.py bump     <folder> --ops ops.txt [--dry]         apply ops to the latest spec -> edit.v<N+1>.json, print the diff

Ops, one per line (# comments, blank lines ignored); paths are dotted with [i], values are JSON:
  set    <path> <json>              set steps[1][1] 1.15      set style.accent "#00E5FF"
  append <path> <json>              append cutaways {"src":"a.png","from":3,"to":4.2,"w":1080,"h":750}
  insert <path> <index> <json>
  delete <path>                     delete cutaways[2]
  caption <time> <text>             replace the caption word nearest <time> (source s) with <text>
  retime  <time> <start> <end>      move the caption word nearest <time>
  shift   <from_t> <delta>          move EVERY timed thing at or after from_t (source s) by delta seconds
  hot     add|del <WORD>
  bg      <image> [key=value ...]   turn the background swap on with the plugin defaults (scale, left, top, blur, brightness, ...)
A value may be "@file.json#key": it is read from that file in the slug folder (set phrases @captions.json#phrases).
Earlier versions are never touched. Times are SOURCE seconds.
"""
import argparse, copy, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import latest_spec, load_spec, spec_versions

SCHEMA = "talking-head-shorts/1"

DEFAULTS = {
    "schema": SCHEMA,
    "style": {"font": "Anton", "fontFile": "fonts/Anton-Regular.ttf", "accent": "#FF2D2D", "current": "#FFD60A", "text": "#FFFFFF",
              "captionSize": 118, "captionTop": 1240, "captionWidth": 980, "captionStroke": 10, "captionGap": 26,
              "grade": "contrast(1.1) saturate(1.2) brightness(0.95)", "vignette": True},
    "hook": {"kind": "none"},
    "phrases": [], "hot": [],
    "steps": [[0, 1.0]], "drift": 0.03, "origin": "50% 38%",
    "shakes": [], "flashes": [], "cutaways": [], "pills": [], "counters": [], "slams": [],
    "bg": None, "matte": None,
    "sfx": [], "hook_sfx": [], "music": {"drone": True, "vol": 1.0}, "outro": {"seconds": 3.0},
}
BG_DEFAULTS = {"scale": 3.0, "left": 0, "top": 0, "blur": 8, "brightness": 0.62, "saturate": 1.15, "origin": "540px 1000px", "parallax": 0.5,
               "creep": 0.04, "filler": ["#2a2224", "#0c0a0a"], "grade": "sepia(0.1)", "glow": "rgba(255,50,30,0.45)"}


# ---------- paths ----------
def parse_path(p):
    return [int(a) if a.isdigit() else a for a in re.findall(r"[^.\[\]]+", p)]


def walk(obj, keys):
    for k in keys:
        obj = obj[k]
    return obj


def times_of(spec):
    """Yield (container, key) for every timed number so shift can move them all."""
    s = spec
    for ph in s["phrases"]:
        for w in ph:
            yield w, 1; yield w, 2
    for st in s["steps"]:
        yield st, 0
    for k in ("cutaways", "slams"):
        for c in s[k]:
            yield c, "from"; yield c, "to"
    for g in s["pills"]:
        yield g, "from"; yield g, "to"
        for p in g["pills"]:
            yield p, "at"
    for c in s["counters"]:
        yield c, "from"; yield c, "to"
    for c in s["shakes"]:
        yield c, "at"
    for i in range(len(s["flashes"])):
        yield s["flashes"], i
    for c in s["sfx"]:
        yield c, 1
    if s.get("matte"):
        pass  # matte frames are indexed by source time and do not move


def nearest_word(spec, t):
    best = None
    for ph in spec["phrases"]:
        for w in ph:
            d = abs(w[1] - t)
            if best is None or d < best[0]:
                best = (d, w)
    return best[1] if best and best[0] < 1.0 else None


FOLDER = pathlib.Path(".")


def jval(text):
    text = text.strip()
    if text.startswith("@"):
        f, _, key = text[1:].partition("#")
        data = json.loads((FOLDER / f).read_text())
        return data[key] if key else data
    return json.loads(text)


def apply_op(spec, line):
    parts = line.split(None, 1)
    op, rest = parts[0], parts[1] if len(parts) > 1 else ""
    if op == "set":
        path, val = rest.split(None, 1)
        keys = parse_path(path)
        walk(spec, keys[:-1])[keys[-1]] = jval(val)
    elif op == "append":
        path, val = rest.split(None, 1)
        walk(spec, parse_path(path)).append(jval(val))
    elif op == "insert":
        path, idx, val = rest.split(None, 2)
        walk(spec, parse_path(path)).insert(int(idx), jval(val))
    elif op == "delete":
        keys = parse_path(rest.strip())
        del walk(spec, keys[:-1])[keys[-1]]
    elif op == "caption":
        t, text = rest.split(None, 1)
        w = nearest_word(spec, float(t))
        if not w:
            raise ValueError("no caption word within 1 s of %s" % t)
        w[0] = text.strip()
    elif op == "retime":
        t, a, b = rest.split()
        w = nearest_word(spec, float(t))
        if not w:
            raise ValueError("no caption word within 1 s of %s" % t)
        w[1], w[2] = float(a), float(b)
    elif op == "shift":
        frm, d = (float(x) for x in rest.split())
        for c, k in times_of(spec):
            if c[k] >= frm - 1e-9:
                c[k] = round(c[k] + d, 3)
    elif op == "hot":
        a, w = rest.split()
        if a == "add" and w not in spec["hot"]:
            spec["hot"].append(w)
        elif a == "del" and w in spec["hot"]:
            spec["hot"].remove(w)
    elif op == "bg":
        img, *kv = rest.split()
        bg = {"image": img, **copy.deepcopy(BG_DEFAULTS)}
        for item in kv:
            k, v = item.split("=", 1)
            bg[k] = json.loads(v)
        spec["bg"] = bg
    else:
        raise ValueError("unknown op %r" % op)


def diff(a, b, path=""):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a: out.append("+ %s%s = %s" % (path, k, json.dumps(b[k], ensure_ascii=False)[:120]))
            elif k not in b: out.append("- %s%s" % (path, k))
            else: out += diff(a[k], b[k], "%s%s." % (path, k))
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, "%s[%d]" % (path.rstrip("."), i) + ".")
    elif a != b:
        out.append("~ %s: %s -> %s" % (path.rstrip("."), json.dumps(a, ensure_ascii=False)[:90], json.dumps(b, ensure_ascii=False)[:90]))
    return out


# ---------- init ----------
def cmd_init(a):
    folder = pathlib.Path(a.folder).expanduser().resolve()
    if spec_versions(folder):
        sys.exit("%s already has an edit spec; change it with spec.py bump" % folder)
    probe = json.loads((folder / "probe.json").read_text())
    link = pathlib.Path(probe["link"])
    fit = a.fit or ("cover" if probe["nine_sixteen"] else ("crop" if probe.get("suggested_crop") else "blurfill"))
    crop = [int(x) for x in a.crop.split(",")] if a.crop else (probe.get("suggested_crop") if fit == "crop" else None)
    spec = copy.deepcopy(DEFAULTS)
    spec.update({"slug": folder.name, "version": 1,
                 "source": {"file": link.name, "start": a.start or 0.0, "end": a.end or probe["duration"], "w": probe["width"], "h": probe["height"],
                            "fit": fit, **({"crop": crop} if crop else {})}})
    order = ["schema", "slug", "version", "source"] + [k for k in spec if k not in ("schema", "slug", "version", "source")]
    spec = {k: spec[k] for k in order}
    out = folder / "edit.v1.json"
    out.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out, "| fit:", fit, "| window %.2f-%.2f" % (spec["source"]["start"], spec["source"]["end"]))


# ---------- validate / show ----------
def problems(folder, spec):
    err, warn = [], []
    s, win = spec["source"], (spec["source"]["start"], spec["source"]["end"])
    if spec.get("schema") != SCHEMA: err.append("schema must be %s" % SCHEMA)
    if not (folder / s["file"]).exists(): err.append("source file %s missing in %s" % (s["file"], folder))
    if s["fit"] == "crop" and not s.get("crop"): err.append("fit=crop needs source.crop [x,y,w,h]")
    if s["fit"] == "blurfill" and spec.get("matte"): err.append("blurfill cannot be combined with a background swap (matte): use cover or crop")
    if spec.get("matte") and not spec.get("bg"): err.append("matte without bg")
    if spec.get("bg") and not spec.get("matte"): warn.append("bg set but matte is null: the background is not drawn until the cut-out exists")
    inw = lambda t: win[0] - 1e-6 <= t <= win[1] + 1e-6
    prev_end = -1
    for i, ph in enumerate(spec["phrases"]):
        for w in ph:
            if not (len(w) == 3 and w[2] > w[1]): err.append("phrase %d word %s has bad times %s" % (i, w[0], w[1:]))
            if not inw(w[1]): warn.append("caption %r at %.2f is outside the window %s" % (w[0], w[1], win))
        if ph and ph[0][1] < prev_end - 0.05: warn.append("phrase %d starts at %.2f before the previous phrase ends (%.2f)" % (i, ph[0][1], prev_end))
        if ph: prev_end = ph[-1][2]
    for c in spec["cutaways"]:
        if not (folder / "anim" / "public" / c["src"]).exists() and not (folder / c["src"]).exists(): warn.append("cutaway image %s not found in %s" % (c["src"], folder))
        if not (inw(c["from"]) and inw(c["to"])): warn.append("cutaway %s %.2f-%.2f outside the window" % (c["src"], c["from"], c["to"]))
    cuts = sorted((c["from"], c["to"], c["src"]) for c in spec["cutaways"])
    for x, y in zip(cuts, cuts[1:]):
        if y[0] < x[1] - 0.2: warn.append("cutaways %s and %s overlap by %.2f s (the second stacks on the first)" % (x[2], y[2], x[1] - y[0]))
    for g in spec["pills"]:
        for p in g["pills"]:
            if not (g["from"] <= p["at"] <= g["to"]): warn.append("pill %r appears at %.2f outside its group %.2f-%.2f" % (p["small"], p["at"], g["from"], g["to"]))
    for sl in spec["slams"]:
        for g in spec["pills"]:
            if sl["from"] < g["to"] and g["from"] < sl["to"] and sl["top"] < 700: warn.append("slam %r overlaps a pill group in time and both sit in the top third" % sl["text"])
    hot = {w.upper() for w in spec["hot"]}
    if spec["bg"]:
        warn.append("background swap: check hot-colour words and pills over the new background on the edge sheet")
    h = spec["hook"]
    if h["kind"] == "cold" and not (inw(h["clip"][0]) and inw(h["clip"][1])): err.append("cold-open clip must be inside the source window")
    if h["kind"] == "image" and not (folder / "anim" / "public" / h["image"]).exists() and not (folder / h["image"]).exists(): warn.append("hook image %s not found" % h["image"])
    for name, t, vol in spec["sfx"]:
        if not inw(t): warn.append("sfx %s at %.2f is outside the window" % (name, t))
    return err, warn


def cmd_validate(a):
    path, spec = load_spec(pathlib.Path(a.target).expanduser())
    err, warn = problems(path.parent, spec)
    print("%s (v%s)" % (path.name, spec.get("version")))
    for e in err: print("  ERROR", e)
    for w in warn: print("  warn ", w)
    if not err: print("  ok: %d phrases, %d cutaways, %d pill groups, %d counters, %d slams, %d sfx cues" % (
        len(spec["phrases"]), len(spec["cutaways"]), len(spec["pills"]), len(spec["counters"]), len(spec["slams"]), len(spec["sfx"])))
    sys.exit(1 if err else 0)


def cmd_show(a):
    path, spec = load_spec(pathlib.Path(a.target).expanduser())
    ev = []
    for ph in spec["phrases"]:
        ev.append((ph[0][1], ph[-1][2], "caption", " ".join(w[0] for w in ph)))
    for t, z in spec["steps"]: ev.append((t, t, "punch-in", "zoom %.2f" % z))
    for c in spec["cutaways"]: ev.append((c["from"], c["to"], "cutaway", c["src"] + (" ring" if c.get("ring") else "") + (" '%s'" % c["label"] if c.get("label") else "")))
    for g in spec["pills"]:
        for p in g["pills"]: ev.append((p["at"], g["to"], "pill", "%s %s" % (p["big"], p["small"])))
    for c in spec["counters"]: ev.append((c["from"], c["to"], "counter", "%s %s" % (c["value"], c["label"])))
    for m in spec["slams"]: ev.append((m["from"], m["to"], "slam", m["text"]))
    for k in spec["shakes"]: ev.append((k["at"], k["at"] + k["dur"], "shake", "amp %s" % k["amp"]))
    for f in spec["flashes"]: ev.append((f, f, "flash", ""))
    for n, t, v in spec["sfx"]: ev.append((t, t, "sfx", "%s %.1f" % (n, v)))
    ev.sort(key=lambda e: (e[0], e[2]))
    h = spec["hook"]
    print("v%s  window %.2f-%.2f  fit=%s  hook=%s  bg=%s  hot=%s" % (spec["version"], spec["source"]["start"], spec["source"]["end"], spec["source"]["fit"],
          h["kind"] + (" " + " / ".join(l["text"] for l in h.get("lines", [])) if h["kind"] != "none" else ""), "swap" if spec.get("bg") else "none", ",".join(spec["hot"]) or "-"))
    for s, e, k, d in ev:
        print("  %6.2f-%6.2f  %-8s %s" % (s, e, k, d))


def cmd_fill(a):
    global FOLDER
    folder = FOLDER = pathlib.Path(a.folder).expanduser().resolve()
    path = latest_spec(folder)
    spec = json.loads(path.read_text())
    v = spec["version"]
    if (folder / "anim/out" / ("raw_v%d.mp4" % v)).exists() or (folder / ("%s_v%d.mp4" % (spec["slug"], v))).exists():
        sys.exit("v%d was already rendered: use bump (a new version), never edit a rendered one" % v)
    for n, line in enumerate(pathlib.Path(a.ops).read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"): continue
        try: apply_op(spec, line)
        except Exception as e: sys.exit("ops line %d failed (%s): %s" % (n, e, line))
    err, warn = problems(folder, spec)
    for w in warn: print("  warn", w)
    if err: sys.exit("not written, fix: " + "; ".join(err))
    path.write_text(json.dumps(spec, indent=1, ensure_ascii=False) + "\n")
    print("filled", path)


def cmd_bump(a):
    global FOLDER
    folder = FOLDER = pathlib.Path(a.folder).expanduser().resolve()
    path = latest_spec(folder)
    old = json.loads(path.read_text())
    new = copy.deepcopy(old)
    for n, line in enumerate(pathlib.Path(a.ops).read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"): continue
        try: apply_op(new, line)
        except Exception as e: sys.exit("ops line %d failed (%s): %s" % (n, e, line))
    new["version"] = old["version"] + 1
    out = folder / ("edit.v%d.json" % new["version"])
    if out.exists(): sys.exit("%s exists: versions are never overwritten" % out)
    err, warn = problems(folder, new)
    for l in diff(old, new): print(l)
    for w in warn: print("  warn", w)
    if err: sys.exit("not written, fix: " + "; ".join(err))
    if a.dry: print("dry run: nothing written"); return
    out.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("init"); p.add_argument("folder"); p.add_argument("--fit", choices=["cover", "crop", "blurfill"]); p.add_argument("--crop")
    p.add_argument("--start", type=float); p.add_argument("--end", type=float)
    p = sp.add_parser("validate"); p.add_argument("target")
    p = sp.add_parser("show"); p.add_argument("target")
    p = sp.add_parser("fill"); p.add_argument("folder"); p.add_argument("--ops", required=True)
    p = sp.add_parser("bump"); p.add_argument("folder"); p.add_argument("--ops", required=True); p.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    {"init": cmd_init, "validate": cmd_validate, "show": cmd_show, "bump": cmd_bump, "fill": cmd_fill}[a.cmd](a)


if __name__ == "__main__":
    main()
