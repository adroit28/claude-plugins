#!/usr/bin/env python3
"""Write spec.vN.json from a beat plan (references/plan-format.md), then print the dry-run timeline.

  plan.py <edit_dir>/plan.v1.md                writes <edit_dir>/spec.v1.json
  plan.py plan.v1.md --out build/check/spec.v1.json
  plan.py plan.v1.json                          same keys as the .md, JSON shaped

The plan is one line per beat (source, in, out, effect, caption, hit, extras); this script does the
frame snapping, the start times, caption windows, hit placement, the loop ending and the JSON. A
version whose render exists is never overwritten; bump the version in the plan instead.
"""
import argparse, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speclib as L

SECTIONS = ("beats", "overlays", "hits")

def read_md(path):
    head, sec = [], {k: [] for k in SECTIONS}; cur = None
    for raw in open(path, encoding="utf-8"):
        line = raw.rstrip("\n")
        m = re.match(r"^\s*(?:#{1,3}\s*)?(beats|overlays|hits)\s*$", line, re.I)
        if m: cur = m.group(1).lower(); continue
        if not line.strip() or line.lstrip().startswith("#"): continue
        line = strip_comment(line)
        if not line.strip(): continue
        (sec[cur] if cur else head).append(line.strip())
    return head, sec

def strip_comment(line):
    """drop `  # note` at the end of a line; a # inside quotes or glued to text (bg=#111111) stays"""
    q = None
    for i, ch in enumerate(line):
        if q: q = None if ch == q else q
        elif ch in "\"'": q = ch
        elif ch == "#" and (i == 0 or line[i - 1].isspace()) and (i + 1 == len(line) or line[i + 1].isspace()): return line[:i]
    return line

def read_json(path):
    j = json.load(open(path)); head = []
    for k, v in j.items():
        if k in SECTIONS: continue
        if k == "sources":
            for kk, vv in v.items(): head.append("source %s %s" % (kk, vv))
        elif isinstance(v, dict): head.append("%s %s" % (k, json.dumps(v)))
        else: head.append("%s %s" % (k, json.dumps(v) if not isinstance(v, str) else v))
    sec = {k: list(j.get(k, [])) for k in SECTIONS}
    return head, sec

def header(head):
    spec = {"slug": None, "version": 1, "fps": 25, "size": [1080, 1920], "max_duration": 30, "sources": {}}
    opts = {"end": "loop", "bpm": None, "bpm_offset": 0.0}
    for line in head:
        toks = L.tokens(line); key = toks[0].rstrip(":").lower(); rest = toks[1:]
        if key == "source":
            if len(rest) < 2: sys.exit("source needs: source <key> <path>")
            spec["sources"][rest[0]] = L.unquote(" ".join(rest[1:]))
        elif key == "size":
            m = re.match(r"^(\d+)x(\d+)$", rest[0]); spec["size"] = [int(m.group(1)), int(m.group(2))] if m else L.value(rest[0])
        elif key in ("fill", "audio", "spine", "bed"):
            if rest and rest[0].lower() in ("none", "false"): spec[key] = False if key == "fill" else None; continue
            pos, kv = L.parse_kv(rest)
            if pos and pos[0].startswith("{"): kv = json.loads(L.unquote(" ".join(pos))); pos = []
            if pos: sys.exit("%s takes key=value pairs (got %r)" % (key, pos))
            if key == "spine" and "turn" in kv: kv["turn"] = int(kv["turn"])
            if key == "bed": spec.setdefault("audio", {})["bed"] = kv
            else: spec[key] = kv
        elif key == "end": opts["end"] = rest[0].lower()
        elif key == "bpm":
            opts["bpm"] = float(rest[0]); pos, kv = L.parse_kv(rest[1:]); opts["bpm_offset"] = float(kv.get("offset", 0))
        elif key in ("version", "fps", "max_duration", "crf"): spec[key] = L.value(rest[0])
        else: spec[key] = L.value(" ".join(rest)) if len(rest) > 1 and not any("=" in r for r in rest) else (L.value(rest[0]) if len(rest) == 1 else L.parse_kv(rest)[1])
    if not spec.get("slug"): sys.exit("plan needs `slug <name>`")
    if not spec["sources"]: sys.exit("plan needs at least one `source <key> <path>`")
    if "spine" not in spec:
        sys.exit("plan needs a spine line: spine question=\"<what the first second asks>\" turn=<beat index at 60-70%> button=<last beat index>\n"
                 "(the story spine comes before the cuts; see enhance/references/hook-playbook.md)")
    return spec, opts

def beats(spec, lines, fps):
    segs, caps, hits = [], [], []
    for n, line in enumerate(lines):
        if isinstance(line, dict):  # JSON plan: a ready segment, optional caption/hit keys
            d = dict(line); cap = d.pop("caption", None); hit = d.pop("hit", None)
            seg = d; capd = L.caption_dict("big", cap, {}) if cap else None
            hitd = None
            if hit: k, off, dur = L.parse_hit_tok(hit); hitd = {"kind": k, "_off": off, **({"dur": dur} if dur else {})}
        else:
            try: seg, capd, hitd = L.parse_beat(L.tokens(line), fps)
            except SystemExit as e: sys.exit("beat %d (%s): %s" % (n, line[:50], e))
        for k in ("src",):
            if seg.get(k) and seg[k] not in spec["sources"]: sys.exit("beat %d uses source %r; header has %s" % (n, seg[k], list(spec["sources"])))
        segs.append(seg); caps.append(capd); hits.append(hitd)
    return segs, caps, hits

def snap_to_bpm(spec, opts, segs):
    """move each cut onto the beat grid by trimming/extending the beat before it (within 0.25 s, never below 0.3 s)"""
    if not opts["bpm"]: return
    fps = spec["fps"]; step = 60.0 / opts["bpm"]; t = 0.0
    for i, s in enumerate(segs):
        d = L.expected(s, fps)
        if i > 0:
            g = opts["bpm_offset"] + round((t - opts["bpm_offset"]) / step) * step; dv = g - t; p = segs[i - 1]
            if 0.005 < abs(dv) <= 0.25 and p["type"] in ("clip", "still", "card", "split") and not p.get("speed"):
                nt = L.snap(p["t"] + dv, fps)
                if nt >= 0.3:
                    print("bpm: beat %d start %.3f -> %.3f (beat %d t %.2f -> %.2f)" % (i, t, t - p["t"] + nt, i - 1, p["t"], nt))
                    t += nt - p["t"]; p["t"] = L.r4(nt)
        t += d

def cap_time(v, start, rows, total, default):
    """caption window edge: absent -> default; +x/-x -> offset from the beat start; else any time atom"""
    if v is None: return default
    if isinstance(v, (int, float)): return L.r4(start + v)
    if isinstance(v, str) and re.match(r"^[+-]\d", v): return L.r4(start + float(v))
    return L.resolve_time(v, rows, total)

def build(plan_path, out=None, force=False):
    head, sec = read_json(plan_path) if plan_path.endswith(".json") else read_md(plan_path)
    spec, opts = header(head); fps = spec["fps"]
    segs, caps, hits = beats(spec, sec["beats"], fps)
    if not segs: sys.exit("plan has no beats")
    snap_to_bpm(spec, opts, segs)
    # loop ending: the last frame should lead back into the first; when the edit does not already end on its opening
    # source, hold the opening frame for 0.4 s
    if opts["end"] == "loop" and segs[-1].get("src") != segs[0].get("src"):
        f = segs[0]; ret = {"type": "still", "src": f.get("src"), "at": f.get("ss", f.get("at", 0)), "t": L.snap(0.4, fps), "zoom": 0, "label": "loop-return"}
        if f.get("crop") is not None: ret["crop"] = f["crop"]
        if "fill" in f: ret["fill"] = f["fill"]
        segs.append(ret); caps.append(None); hits.append(None); print("end loop: added a 0.4 s still of the opening frame (end none to skip)")
    spec["segments"] = segs
    rows, total = L.timeline(spec)
    overlays, hitlist = [], []
    for line in sec["overlays"]:
        if isinstance(line, dict): overlays.append(line); continue
        toks = L.tokens(line)
        if len(toks) < 3: sys.exit("overlay line needs: <from> <to> key=value ... (got %r)" % line)
        pos, kv = L.parse_kv(toks[2:])
        if pos: sys.exit("stray tokens %r in overlay line %r" % (pos, line))
        o = {"from": L.resolve_time(toks[0], rows, total), "to": L.resolve_time(toks[1], rows, total)}; o.update(L.overlay_from_kv(kv)); overlays.append(o)
    for i, c in enumerate(caps):
        if not c: continue
        win = c.pop("_win"); r = rows[i]
        o = {"from": cap_time(win.get("from"), r["start"], rows, total, r["start"]), "to": cap_time(win.get("to"), r["start"], rows, total, r["end"])}
        o.update(c); overlays.append(o)
    for i, h in enumerate(hits):
        if not h: continue
        off = h.pop("_off"); hitlist.append({"at": L.r4(rows[i]["start"] + off), **h})
    for line in sec["hits"]:
        if isinstance(line, dict): hitlist.append(line); continue
        toks = L.tokens(line)
        if len(toks) < 2: sys.exit("hit line needs: <at> <kind> [key=value ...] (got %r)" % line)
        pos, kv = L.parse_kv(toks[1:]); h = {"at": L.resolve_time(toks[0], rows, total)}
        if pos:
            k, off, dur = L.parse_hit_tok(pos[0]); h["at"] = L.r4(h["at"] + off); h["kind"] = k
            if dur: h["dur"] = dur
        elif "file" in kv: h["kind"] = "file"
        h.update(kv); hitlist.append(h)
    hitlist.sort(key=lambda h: h["at"])
    audio = spec.pop("audio", None) or {}
    audio.setdefault("clip_volume", 1.0)
    if hitlist: audio["hits"] = hitlist
    audio.setdefault("loudnorm", "I=-15:TP=-3:LRA=11")
    # assemble in the reference order
    order = ["slug", "version", "fps", "size", "max_duration", "sources", "fill", "spine", "bpm", "preset", "crf", "out"]
    final = {k: spec[k] for k in order if k in spec and spec[k] is not None}
    if opts["bpm"]: final["bpm"] = opts["bpm"]; final["beat_offset"] = opts["bpm_offset"]
    for k, v in spec.items():
        if k not in final and k not in ("segments", "overlays", "audio", "end") and v is not None: final[k] = v
    final["segments"] = segs; final["overlays"] = overlays; final["audio"] = audio
    sp = final.get("spine") or {}
    if isinstance(sp, dict):
        sp.setdefault("button", len(segs) - 1)
        if "turn" in sp:
            if not 0 <= sp["turn"] < len(segs): sys.exit("spine turn=%s is not a beat index (0..%d)" % (sp["turn"], len(segs) - 1))
            share = rows[sp["turn"]]["start"] / total if total else 0
            if not 0.6 <= share <= 0.7: print("WARN spine: turn (beat %d) starts at %.0f%% of the video; the playbook wants 60-70%%" % (sp["turn"], share * 100))
        else: print("WARN spine: no turn beat; add turn=<index> once the story has one")
    # write
    edit_dir = os.path.dirname(os.path.abspath(plan_path))
    path = out or L.spec_path_for(edit_dir, final["version"])
    if not os.path.isabs(path): path = os.path.join(edit_dir, path)
    if os.path.exists(path):
        try: r = L.rendered(json.load(open(path)), os.path.dirname(path))
        except ValueError: r = None
        if r and not force: sys.exit("refusing: %s is rendered (%s). Bump `version` in the plan; one spec per version." % (os.path.basename(path), os.path.basename(r)))
    os.makedirs(os.path.dirname(path), exist_ok=True); L.dump(final, path)
    # report
    L.print_timeline(rows, total)
    for o in overlays:
        print("  ov %6.2f-%-6.2f %s" % (o["from"], o["to"], L.ov_text(o)[:40]))
        if o["to"] > total + 0.01: print("WARN overlay %r ends after the video (%.2f)" % (L.ov_text(o)[:30], total))
        if o.get("big") and o.get("y_big", 330) < 250: print("WARN overlay %r y_big %s is inside the top safe zone (250 px)" % (L.ov_text(o)[:30], o.get("y_big")))
    print("  hits: %d (%s)" % (len(hitlist), ", ".join(sorted({h.get("kind", "bass") for h in hitlist}))))
    if total > final.get("max_duration", 30): print("WARN total %.2f s over max_duration %s" % (total, final.get("max_duration")))
    if total < 13: print("WARN total %.2f s under the 13 s channel rule" % total)
    print("wrote", os.path.relpath(path))
    return path

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan"); ap.add_argument("--out", help="write the spec here instead of <edit_dir>/spec.v<version>.json")
    ap.add_argument("--force", action="store_true", help="overwrite even a rendered version (normally never)")
    a = ap.parse_args(); build(a.plan, a.out, a.force)

if __name__ == "__main__":
    main()
