#!/usr/bin/env python3
"""Shared helpers for plan.py, spec.py and check.py: frame snapping, segment durations, the
timeline, the beat-line grammar (references/plan-format.md), selectors, ripple and a stable
JSON writer. Import only; no CLI. Durations mirror render.py exactly (round-half-up frames)."""
import copy, difflib, json, math, os, re, sys

# ---------- frames and durations (same maths as render.py)
def frames(dur, fps): return int(math.floor(dur * fps + 0.5 + 1e-6))
def snap(dur, fps): return frames(dur, fps) / fps

def raw_dur(s):
    k = s["type"]
    if k == "clip": return s["t"] * (s.get("speed") or 1)
    if k in ("still", "card", "split"): return s["t"]
    if k == "reverse": return s["t"] * s.get("slow", 1.25)
    if k == "boomerang": return s["t"] * 2 * s.get("loops", 2)
    if k == "slowmo": return s["t"] * s.get("factor", 3)
    if k == "ramp": return ramp_total(s)
    raise SystemExit("unknown segment type %r" % k)

def expected(s, fps): return snap(raw_dur(s), fps)

# ramp: real speed -> eased slow-down to `factor`x around source time `slow_at` -> back out. Output time as a
# function of source elapsed time; shared with render.py (setpts expression) and track.py (overlay mapping).
def ramp_params(s):
    f = float(s.get("factor", 3)); hold = float(s.get("hold", 0.16)); ease = float(s.get("ease", 0.2))
    a = s["slow_at"] - s["ss"] - hold / 2 - ease  # start of ease-in (source elapsed)
    return f, hold, ease, max(a, 0.0)
def ramp_out(s, u):
    """output seconds elapsed for source seconds elapsed u"""
    f, hold, ease, a = ramp_params(s); b = a + ease; c = b + hold; d = c + ease
    def seg(x0, x1, k0, k1):  # integral of linear speed-factor ramp k0->k1 over [x0,x1]
        w = x1 - x0; return w * (k0 + k1) / 2 if w > 0 else 0
    if u <= a: return u
    if u <= b: return a + seg(a, u, 1, 1 + (f - 1) * (u - a) / ease)
    if u <= c: return a + seg(a, b, 1, f) + (u - b) * f
    if u <= d: return a + seg(a, b, 1, f) + hold * f + seg(c, u, f, f - (f - 1) * (u - c) / ease)
    return a + seg(a, b, 1, f) + hold * f + seg(c, d, f, 1) + (u - d)
def ramp_total(s): return ramp_out(s, s["t"])
def ramp_src(s, o):
    """inverse: source elapsed for output elapsed o (bisection; monotonic)"""
    lo, hi = 0.0, s["t"]
    for _ in range(40):
        m = (lo + hi) / 2
        if ramp_out(s, m) < o: lo = m
        else: hi = m
    return (lo + hi) / 2

def timeline(spec):
    fps = spec.get("fps", 25); rows = []; t = 0.0
    for i, s in enumerate(spec["segments"]):
        d = expected(s, fps)
        rows.append({"i": i, "start": t, "end": t + d, "dur": d, "type": s["type"],
                     "label": s.get("label", ""), "src": s.get("src") or (s.get("top") or {}).get("src"), "ss": s.get("ss", s.get("at"))})
        t += d
    return rows, t

def print_timeline(rows, total, file=sys.stdout):
    print("%-3s %-7s %-7s %-6s %-9s %-14s %-6s %s" % ("#", "start", "end", "dur", "type", "label", "src", "ss"), file=file)
    for r in rows:
        print("%-3d %-7.2f %-7.2f %-6.2f %-9s %-14s %-6s %s" % (r["i"], r["start"], r["end"], r["dur"], r["type"], r["label"][:14],
                                                                r["src"] or "-", r["ss"] if r["ss"] is not None else "-"), file=file)
    print("total %.2fs" % total, file=file)

# output <-> source time inside one segment (None when the mapping is not one-to-one)
def out2src(s, start, out):
    k = s["type"]; o = out - start
    if k == "clip": return s["ss"] + o / (s.get("speed") or 1)
    if k == "slowmo": return s["ss"] + o / s.get("factor", 3)
    if k == "reverse": return s["ss"] + s["t"] - o / s.get("slow", 1.25)
    if k == "ramp": return s["ss"] + ramp_src(s, o)
    if k == "still": return s.get("at")
    return None
def src2out(s, start, src):
    k = s["type"]
    if k == "clip": return start + (src - s["ss"]) * (s.get("speed") or 1)
    if k == "slowmo": return start + (src - s["ss"]) * s.get("factor", 3)
    if k == "reverse": return start + (s["ss"] + s["t"] - src) * s.get("slow", 1.25)
    if k == "ramp": return start + ramp_out(s, src - s["ss"])
    return None
def src_window(s):
    if s["type"] in ("clip", "slowmo", "reverse", "boomerang", "ramp"): return s["ss"], s["ss"] + s["t"]
    if s["type"] == "still": return s["at"], s["at"]
    return None

# ---------- tokens and values
TOK = re.compile(r'''(?:[^\s"']+|"[^"]*"|'[^']*')+''')
def tokens(line): return TOK.findall(line)
def quoted(v): return len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'"
def unquote(v): return v[1:-1] if quoted(v) else v
NUM = re.compile(r"^[+-]?\d+(\.\d+)?$")
def value(v):
    """quoted -> string; else JSON (number, true/false/null, list, object); a,b,c of numbers -> list; else string"""
    if quoted(v): return v[1:-1]
    try: return json.loads(v)
    except ValueError: pass
    if "," in v and all(NUM.match(p) for p in v.split(",")): return [json.loads(p) for p in v.split(",")]
    return v
def parse_kv(toks):
    """tokens -> (positional list, {key: value}); a key may repeat as k+=v to extend a list"""
    pos, kv = [], {}
    for t in toks:
        if "=" in t and not quoted(t) and not t.startswith("=") and re.match(r"^[A-Za-z_][\w.\-]*=", t):
            k, v = t.split("=", 1); kv[k] = value(v)
        else: pos.append(t)
    return pos, kv
def r4(x): return round(x + 1e-9, 4)

def lines_of(text): return [p.strip() for p in str(text).split("|")]

# ---------- beat lines:  src in out effect caption hit [key=value ...]
EFFECTS = {"clip", "still", "slowmo", "reverse", "boomerang", "split", "card", "ramp"}
def parse_effect(tok):
    parts = tok.split(":"); kind = parts[0]
    if kind not in EFFECTS: raise SystemExit("unknown effect %r (have %s)" % (tok, ", ".join(sorted(EFFECTS))))
    seg = {"type": kind}
    nums = []
    for p in parts[1:]:
        m = re.match(r"^x?(\d+(?:\.\d+)?)x?$", p)
        if m: nums.append(float(m.group(1)))
        else: raise SystemExit("bad effect option %r in %r" % (p, tok))
    if kind == "clip" and nums: seg["speed"] = nums[0] if nums[0] != 1 else None
    if kind == "slowmo": seg["factor"] = int(nums[0]) if nums and nums[0] == int(nums[0]) else (nums[0] if nums else 2)
    if kind == "reverse" and nums: seg["slow"] = nums[0]
    if kind == "boomerang" and nums: seg["loops"] = int(nums[0])
    if kind == "ramp":
        if not nums: raise SystemExit("ramp needs ramp:<slow_at>:x<factor>, e.g. ramp:26.72:x3")
        seg["slow_at"] = nums[0]; seg["factor"] = int(nums[1]) if len(nums) > 1 and nums[1] == int(nums[1]) else (nums[1] if len(nums) > 1 else 3)
    if seg.get("speed") is None: seg.pop("speed", None)
    return seg

def parse_hit_tok(tok):
    """bass | bass-0.3 | whoosh+0.1 | riser:0.74 (dur) -> (kind, offset, dur)"""
    m = re.match(r"^([A-Za-z][\w\-]*)(?::(\d+(?:\.\d+)?))?([+-]\d+(?:\.\d+)?)?(?::(\d+(?:\.\d+)?))?$", tok)
    if not m: raise SystemExit("bad hit %r (forms: bass, bass-0.3, whoosh+0.1, riser:0.74)" % tok)
    kind, d1, off, d2 = m.groups()
    return kind, float(off or 0), float(d1 or d2) if (d1 or d2) else None

def parse_beat(toks, fps):
    """-> (segment, caption dict without from/to or None, hit dict without at or None, extras for caption/hit)
    Times: `in` is source seconds (ss, or `at` for a still); `out` is absolute source seconds or +length."""
    if len(toks) < 4: raise SystemExit("beat needs at least: src in out effect  (got %r)" % " ".join(toks))
    pos, kv = parse_kv(toks[6:])
    if pos: raise SystemExit("stray tokens %r in beat %r; extras are key=value" % (pos, " ".join(toks)))
    src, tin, tout, eff = toks[0], toks[1], toks[2], toks[3]
    cap = toks[4] if len(toks) > 4 else "-"; hit = toks[5] if len(toks) > 5 else "-"
    seg = parse_effect(eff); kind = seg["type"]
    if src != "-": seg["src"] = src
    if tin != "-":
        tin = float(tin); seg["at" if kind == "still" else "ss"] = tin
    else: tin = 0.0
    if tout.startswith("+"): length = float(tout[1:])
    elif tout == "-": length = None
    else: length = float(tout) - tin
    if length is not None:
        if kind in ("clip", "still", "card", "split") and not seg.get("speed"): length = snap(length, fps)
        seg["t"] = r4(length)
    # extras: cap.* -> caption, hit.* -> hit, rest -> segment (JSON values, so any spec key works)
    capkv, hitkv = {}, {}
    for k, v in kv.items():
        if k.startswith("cap."): capkv[k[4:]] = v
        elif k.startswith("hit."): hitkv[k[4:]] = v
        else: seg[k] = v
    if kind == "still" and "ss" in seg: seg["at"] = seg.pop("ss")
    caption = None
    if cap != "-":
        text = unquote(cap); style = "big"
        for pre in ("small:", "badge:", "text:"):
            if text.startswith(pre): style, text = pre[:-1], text[len(pre):]
        caption = caption_dict(style, text, capkv)
    hitd = None
    if hit != "-":
        hk, off, dur = parse_hit_tok(unquote(hit)); hitd = {"kind": hk, "_off": off}
        if dur: hitd["dur"] = dur
        hitd.update(hitkv)
    return seg, caption, hitd

EXTRA_KEYS = ("y", "size", "bg", "pad", "emoji", "font", "stroke", "fill")
def caption_dict(style, text, kv):
    """style big|small|badge|text -> overlay dict (no from/to). kv keys: y, size, from, to plus raw overlay keys."""
    o = {}; kv = dict(kv); win = {k: kv.pop(k) for k in ("from", "to") if k in kv}
    if style in ("badge", "text"):
        ex = {"lines": lines_of(text)}
        if style == "badge": ex["bg"] = "#111111"
        for k in EXTRA_KEYS:
            if k in kv: ex[k] = kv.pop(k)
        ex.setdefault("y", 1240 if style == "badge" else 900); ex.setdefault("size", 64 if style == "badge" else 100)
        o["extra"] = [ex]
    else:
        o[style] = lines_of(text)
        if "y" in kv: o["y_%s" % style] = kv.pop("y")
        if "size" in kv: o["%s_size" % style] = kv.pop("size")
    o.update(kv); o["_win"] = win
    return o

def overlay_from_kv(kv):
    """overlays-section line keys -> overlay dict (times resolved by the caller)"""
    kv = dict(kv); o = {}
    for key, style in (("badge", "badge"), ("text", "text"), ("big", "big"), ("small", "small")):
        if key in kv:
            t = kv.pop(key); c = caption_dict(style, t, {}); c.pop("_win"); o.update(c)
            if style in ("badge", "text"):
                for k in EXTRA_KEYS:
                    if k in kv: o["extra"][0][k] = kv.pop(k)
            break
    o.update(kv); return o

# ---------- selectors
def find_seg(spec, sel):
    segs = spec["segments"]; s = str(sel)
    if s.startswith("seg:"): s = s[4:]
    s = unquote(s)
    if re.match(r"^-?\d+$", s):
        i = int(s)
        if not -len(segs) <= i < len(segs): raise SystemExit("no segment %d (have 0..%d)" % (i, len(segs) - 1))
        return i % len(segs)
    exact = [i for i, g in enumerate(segs) if g.get("label") == s]
    if len(exact) == 1: return exact[0]
    part = [i for i, g in enumerate(segs) if s.lower() in g.get("label", "").lower()]
    if len(part) == 1: return part[0]
    raise SystemExit("segment %r: %s (labels: %s)" % (sel, "ambiguous" if part else "not found", ", ".join(repr(g.get("label", "")) for g in segs)))

def ov_text(o):
    if o.get("big"): return " ".join(o["big"])
    if o.get("small"): return " ".join(o["small"])
    if o.get("extra"): return " ".join(" ".join(e.get("lines", [])) for e in o["extra"])
    return o.get("png") or o.get("video") or o.get("emoji") or "?"
def find_ov(spec, sel):
    ovs = spec.get("overlays", []); s = str(sel)
    if s.startswith("ov:"): s = s[3:]
    s = unquote(s)
    if re.match(r"^\d+$", s):
        i = int(s)
        if i >= len(ovs): raise SystemExit("no overlay %d (have 0..%d)" % (i, len(ovs) - 1))
        return i
    hits = [i for i, o in enumerate(ovs) if ov_text(o).lower().startswith(s.lower())]
    if len(hits) == 1: return hits[0]
    raise SystemExit("overlay %r: %s (%s)" % (sel, "ambiguous" if hits else "not found", "; ".join("%d %s %s-%s" % (i, ov_text(o)[:24], o["from"], o["to"]) for i, o in enumerate(ovs))))
def find_hit(spec, sel):
    hits = spec.get("audio", {}).get("hits", []); s = str(sel)
    if s.startswith("hit:"): s = s[4:]
    elif s.startswith("hit@"): s = s[3:]
    if re.match(r"^\d+$", s): return int(s)
    m = re.match(r"^@?(\d+(?:\.\d+)?)(?::([\w\-]+))?$", s)
    if m:
        at, kind = float(m.group(1)), m.group(2)
        c = [i for i, h in enumerate(hits) if abs(h["at"] - at) < 0.011 and (not kind or h.get("kind", "bass") == kind)]
        if len(c) == 1: return c[0]
        raise SystemExit("hit %r: %s" % (sel, "ambiguous, add :kind" if c else "not found"))
    raise SystemExit("hit selector %r (forms: hit:3, hit@8.56, hit@8.56:ding)" % sel)

def resolve_time(atom, rows, total, default=None):
    """number | end | @<seg>[.end] with optional +-offset -> output seconds"""
    a = str(atom)
    if a == "-" and default is not None: return default
    m = re.match(r"^(.*?)([+-]\d+(?:\.\d+)?)?$", a); base, off = m.group(1), float(m.group(2) or 0)
    if base == "" and m.group(2): return r4(off)
    if NUM.match(base): return r4(float(base) + off)
    if base == "end": return r4(total + off)
    if base.startswith("@"):
        b = base[1:]; end = b.endswith(".end"); b = b[:-4] if end else b
        i = find_seg({"segments": [{"label": r["label"]} for r in rows]}, b)
        return r4((rows[i]["end"] if end else rows[i]["start"]) + off)
    raise SystemExit("bad time %r (number, end, @seg, @seg.end, each with +-offset)" % atom)

# ---------- ripple: everything timed at or after `boundary` moves by delta
EPS = 0.002  # well under a frame; boundaries are exact, stored times are 3-4 dp
def ripple(spec, boundary, delta, fx=None, eps=EPS):
    """overlay starts and hits at or after the boundary move; overlay ends move only when strictly after it"""
    moved = 0
    for o in spec.get("overlays", []):
        if o["from"] >= boundary - eps: o["from"] = o["from"] + delta; moved += 1
        if o["to"] > boundary + eps: o["to"] = o["to"] + delta; moved += 1
    for h in spec.get("audio", {}).get("hits", []):
        if h["at"] >= boundary - eps: h["at"] = h["at"] + delta; moved += 1
    if fx:
        for l in fx.get("layers", []):
            for k in ("from", "to"):
                if isinstance(l.get(k), (int, float)) and l[k] >= boundary - eps: l[k] = r4(l[k] + delta)
            for v in l.get("values", []):
                if isinstance(v, list) and v and isinstance(v[0], (int, float)) and v[0] >= boundary - eps: v[0] = v[0] + delta
    return moved

def tidy(spec, fx=None):
    """round every output time to 4 dp (ripple keeps full precision so chained ops do not drift)"""
    for o in spec.get("overlays", []):
        for k in ("from", "to"): o[k] = r4(o[k])
    for h in spec.get("audio", {}).get("hits", []): h["at"] = r4(h["at"])
    for l in (fx or {}).get("layers", []):
        for k in ("from", "to"):
            if isinstance(l.get(k), float): l[k] = r4(l[k])
        for v in l.get("values", []):
            if isinstance(v, list) and v and isinstance(v[0], float): v[0] = r4(v[0])

def renumber_fx(fx, at, n):
    """segment indices >= at move by n (n<0 drops layers that pointed inside the removed range)"""
    if not fx: return []
    kept, dropped = [], []
    for l in fx.get("layers", []):
        s = l.get("seg")
        if isinstance(s, int) and s >= at:
            if n < 0 and s < at - n: dropped.append(l); continue
            l["seg"] = s + n
        kept.append(l)
    fx["layers"] = kept; return dropped

# ---------- diff of two specs (segments, overlays, hits) printed compactly
def seg_key(s): return json.dumps(s, sort_keys=True)
def ov_key(o): return json.dumps({k: v for k, v in o.items() if k not in ("from", "to")}, sort_keys=True)
def hit_key(h): return json.dumps({k: v for k, v in h.items() if k != "at"}, sort_keys=True)

def diff(before, after, file=sys.stdout):
    r0, t0 = timeline(before); r1, t1 = timeline(after)
    p = lambda *a: print(*a, file=file)
    k0 = [seg_key(s) for s in before["segments"]]; k1 = [seg_key(s) for s in after["segments"]]
    sm = difflib.SequenceMatcher(a=k0, b=k1, autojunk=False); n = 0
    row = lambda r: "%-2d %6.2f-%-6.2f %-8s %s" % (r["i"], r["start"], r["end"], r["type"], r["label"][:22])
    for tag, i0, i1, j0, j1 in sm.get_opcodes():
        if tag == "equal":
            for a, b in zip(range(i0, i1), range(j0, j1)):
                if abs(r0[a]["start"] - r1[b]["start"]) > 1e-6: p("  ~ seg", row(r1[b]), "(was %.2f-%.2f)" % (r0[a]["start"], r0[a]["end"])); n += 1
        else:
            for a in range(i0, i1): p("  - seg", row(r0[a])); n += 1
            for b in range(j0, j1): p("  + seg", row(r1[b]), json.dumps({k: v for k, v in after["segments"][b].items() if k in ("ss", "at", "t", "speed", "factor", "crop")})); n += 1
    def lst(kind, A, B, key, tm, txt):
        nonlocal n
        ka, kb = [key(x) for x in A], [key(x) for x in B]
        for tag, i0, i1, j0, j1 in difflib.SequenceMatcher(a=ka, b=kb, autojunk=False).get_opcodes():
            if tag == "equal":
                for a, b in zip(range(i0, i1), range(j0, j1)):
                    if tm(A[a]) != tm(B[b]): p("  ~ %s %-26s %s -> %s" % (kind, txt(B[b])[:26], tm(A[a]), tm(B[b]))); n += 1
            else:
                for a in range(i0, i1): p("  - %s %-26s %s" % (kind, txt(A[a])[:26], tm(A[a]))); n += 1
                for b in range(j0, j1): p("  + %s %-26s %s" % (kind, txt(B[b])[:26], tm(B[b]))); n += 1
    lst("ov ", before.get("overlays", []), after.get("overlays", []), ov_key, lambda o: "%g-%g" % (o["from"], o["to"]), ov_text)
    lst("hit", before.get("audio", {}).get("hits", []), after.get("audio", {}).get("hits", []), hit_key, lambda h: "%g" % h["at"],
        lambda h: "%s%s" % (h.get("kind", "bass"), (" " + os.path.basename(h["file"])) if h.get("file") else ""))
    if abs(t0 - t1) > 1e-6: p("  total %.2f -> %.2f s" % (t0, t1)); n += 1
    if n == 0: p("  (no timeline change)")
    return n

# ---------- files
def load(path): return json.load(open(path))
def js(o): return json.dumps(o, ensure_ascii=False, separators=(", ", ": "))
def dump(spec, path):
    """one segment / overlay / hit per line, top-level keys in order: readable diffs, small files"""
    out = ["{"]; keys = list(spec)
    for n, k in enumerate(keys):
        v = spec[k]; comma = "," if n < len(keys) - 1 else ""
        if k in ("segments", "overlays") and isinstance(v, list):
            out.append(' "%s": [' % k)
            for j, it in enumerate(v): out.append("  " + js(it) + ("," if j < len(v) - 1 else ""))
            out.append(" ]" + comma)
        elif k == "audio" and isinstance(v, dict) and isinstance(v.get("hits"), list):
            out.append(' "audio": {')
            ak = list(v)
            for m, a in enumerate(ak):
                c2 = "," if m < len(ak) - 1 else ""
                if a == "hits":
                    out.append('  "hits": [')
                    for j, it in enumerate(v[a]): out.append("   " + js(it) + ("," if j < len(v[a]) - 1 else ""))
                    out.append("  ]" + c2)
                else: out.append('  "%s": %s%s' % (a, js(v[a]), c2))
            out.append(" }" + comma)
        else: out.append(' "%s": %s%s' % (k, js(v), comma))
    out.append("}")
    open(path, "w").write("\n".join(out) + "\n")

def rendered(spec, spec_dir):
    """the mp4 (or raw concat) of this spec version exists -> the version is frozen"""
    ver = spec.get("version", 1); slug = spec.get("slug", "short")
    cands = [os.path.join(spec_dir, spec.get("out") or "%s_v%s.mp4" % (slug, ver)), os.path.join(spec_dir, "build", "raw_v%s.mp4" % ver)]
    return next((c for c in cands if os.path.exists(c)), None)

def spec_path_for(spec_dir, ver): return os.path.join(spec_dir, "spec.v%s.json" % ver)
