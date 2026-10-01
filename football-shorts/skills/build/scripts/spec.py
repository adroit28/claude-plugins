#!/usr/bin/env python3
"""Patch an edit spec with small ops instead of rewriting JSON. Every op prints what moved.

  spec.py spec.v7.json bump                                  -> spec.v8.json (then more ops apply to v8)
  spec.py spec.v8.json shift fan-angle +0.6                  longer beat; later captions/hits ripple
  spec.py spec.v8.json set seg:net-cam.crop=[608,1080,900,0] audio.clip_volume=0.8
  spec.py spec.v8.json drop ov:"SLOW-MO" -- hit add @flight+0.1 whoosh volume=0.4
  spec.py spec.v8.json replace 11-13 with v 24.0 +1.64 clip - - label="G9 free kick" flash=0.08
  spec.py spec.v8.json insert after:messi-runup fk 26.5 +0.8 ramp:26.72:x3 - impact
  spec.py spec.v8.json caption set ov:"TWO SHORT" text="TWO SHORT OF THE|RECORD" to=@fan-angle.end
  spec.py spec.v3.json --ops build/v3to4.ops                  one op per line (or - for stdin)

Ops in one call are separated by `--`. Segments: index or label (unique part is enough). Overlays:
ov:<index> or ov:"text start". Hits: hit:<index> or hit@<at>[:kind]. Times: seconds, end, @seg,
@seg.end, each with +-offset. Beat lines use the plan grammar (references/plan-format.md). A spec
whose render exists is frozen: the first op must be `bump`. Nothing is written with --dry.
"""
import argparse, copy, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import speclib as L

class Spec:
    def __init__(self, path, fx=None):
        self.path = os.path.abspath(path); self.dir = os.path.dirname(self.path); self.spec = L.load(path)
        self.fxpath = os.path.abspath(fx) if fx else None; self.fx = L.load(fx) if fx else None
        self.notes = []
    def rows(self): return L.timeline(self.spec)
    def fps(self): return self.spec.get("fps", 25)
    def note(self, s): self.notes.append(s); print("  " + s)

    # ---- ops
    def op_bump(self, args):
        pos, kv = L.parse_kv(args); fx = None
        if "--fx" in pos: fx = pos[pos.index("--fx") + 1]
        ver = int(self.spec.get("version", 1)); new = ver + 1; np = L.spec_path_for(self.dir, new)
        if os.path.exists(np): sys.exit("bump: %s exists already" % os.path.relpath(np))
        self.spec["version"] = new
        if self.spec.get("out"): self.spec["out"] = re.sub(r"_v%d(\.\w+)$" % ver, r"_v%d\1" % new, self.spec["out"])
        self.path = np; self.note("bump: spec.v%d -> spec.v%d" % (ver, new))
        if fx:
            fxp = os.path.join(self.dir, fx) if not os.path.isabs(fx) else fx
            m = re.search(r"\.v(\d+)\.json$", fxp)
            if not m: sys.exit("bump --fx: expected fx.v<N>.json")
            nfx = fxp[:m.start()] + ".v%d.json" % (int(m.group(1)) + 1)
            if os.path.exists(nfx): sys.exit("bump --fx: %s exists already" % os.path.relpath(nfx))
            self.fx = L.load(fxp); self.fxpath = nfx; self.note("fx: %s -> %s" % (os.path.basename(fxp), os.path.basename(nfx)))

    def resolve(self, path):
        cur = self.spec
        m = re.match(r'^(seg:(?:"[^"]*"|[^.]+)|ov:(?:"[^"]*"|[^.]+)|hit:\d+|hit@\d+(?:\.\d+)?(?::[\w\-]+)?)\.(.+)$', path)
        if m:
            sel, path = m.group(1), m.group(2)
            if sel.startswith("seg:"): cur = self.spec["segments"][L.find_seg(self.spec, sel)]
            elif sel.startswith("ov:"): cur = self.spec["overlays"][L.find_ov(self.spec, sel)]
            else: cur = self.spec["audio"]["hits"][L.find_hit(self.spec, sel)]
        elif re.match(r"^(seg:|ov:|hit:|hit@)", path): sys.exit("path %r names a whole item; add .key" % path)
        parts = [int(p[0]) if p[0] else p[1] for p in re.findall(r"\[(\d+)\]|([^.\[\]]+)", path)]
        if not parts: sys.exit("empty path")
        for p in parts[:-1]:
            if isinstance(cur, list): cur = cur[int(p)]
            else:
                if p not in cur or not isinstance(cur[p], (dict, list)): cur[p] = {}
                cur = cur[p]
        return cur, parts[-1]

    def op_set(self, args):
        for a in args:
            if "=" not in a: sys.exit("set needs path=value (got %r)" % a)
            path, v = a.split("=", 1); cur, key = self.resolve(path); val = L.value(v)
            if isinstance(cur, list): cur[int(key)] = val
            else: cur[key] = val
            self.note("set %s = %s" % (path, json.dumps(val, ensure_ascii=False)))
    def op_unset(self, args):
        for path in args:
            cur, key = self.resolve(path)
            if isinstance(cur, dict) and key in cur: del cur[key]; self.note("unset %s" % path)
            else: self.note("unset %s: not present" % path)

    def seg_delta_src(self, s, delta):
        """output-seconds delta -> source-seconds delta for this segment type"""
        k = s["type"]
        if k == "clip": return delta / (s.get("speed") or 1)
        if k in ("still", "card", "split"): return delta
        if k == "slowmo": return delta / s.get("factor", 3)
        if k == "reverse": return delta / s.get("slow", 1.25)
        if k == "boomerang": return delta / (2 * s.get("loops", 2))
        sys.exit("shift: %s segments have no simple length; set t / slow_at directly" % k)

    def op_shift(self, args):
        head = "--head" in args; args = [a for a in args if a != "--head"]
        if len(args) != 2: sys.exit("shift <seg> <+-delta> [--head]")
        i = L.find_seg(self.spec, args[0]); delta = float(args[1]); s = self.spec["segments"][i]
        rows, total = self.rows(); old_end = rows[i]["end"]; old_d = rows[i]["dur"]
        ds = self.seg_delta_src(s, delta); nt = L.r4(s["t"] + ds)
        if nt <= 0: sys.exit("shift: segment %d would be %.2f s long" % (i, nt))
        if s["type"] in ("clip", "still", "card", "split") and not s.get("speed"): nt = L.snap(nt, self.fps())
        s["t"] = L.r4(nt)
        if head:
            k = "at" if s["type"] == "still" else "ss"
            if k in s: s[k] = L.r4(s[k] - ds)
        real = L.expected(s, self.fps()) - old_d
        moved = L.ripple(self.spec, old_end, real, self.fx)
        self.note("shift seg %d %r: %+.2f s (t %s, %s%d later times moved)" % (i, s.get("label", ""), real, s["t"], "from the head, " if head else "", moved))
        if real < 0:
            new_end = old_end + real
            for o in self.spec.get("overlays", []):
                if new_end < o["from"] < old_end or new_end < o["to"] < old_end: self.note("WARN overlay %r (%g-%g) sits in the trimmed part" % (L.ov_text(o)[:24], o["from"], o["to"]))
            for h in self.spec.get("audio", {}).get("hits", []):
                if new_end <= h["at"] < old_end: self.note("WARN hit %s at %g sits in the trimmed part" % (h.get("kind", "bass"), h["at"]))

    def op_slide(self, args):
        if len(args) != 2: sys.exit("slide <seg> <+-delta>")
        i = L.find_seg(self.spec, args[0]); d = float(args[1]); s = self.spec["segments"][i]
        k = "at" if s["type"] == "still" else "ss"
        if k not in s: sys.exit("slide: segment %d has no %s" % (i, k))
        s[k] = L.r4(s[k] + d); self.note("slide seg %d %r: %s -> %s" % (i, s.get("label", ""), L.r4(s[k] - d), s[k]))

    def remove_range(self, a, b, keep_edge=True):
        """drop segments a..b inclusive. Overlays inside the range go, except (keep_edge) ones that start exactly on
        the range start, which the caller refits; overlays that run past the range clamp to its start; hits inside are
        returned with their source times so the caller can re-place them; everything later ripples back"""
        rows, total = self.rows(); start, end = rows[a]["start"], rows[b]["end"]; eps = L.EPS
        keep = []
        for o in self.spec.get("overlays", []):
            edge = keep_edge and abs(o["from"] - start) < eps
            if o["to"] <= end + eps and o["from"] >= start - eps and not edge:
                self.note("dropped overlay %r (%g-%g)" % (L.ov_text(o)[:30], o["from"], o["to"])); continue
            if start + eps < o["from"] < end - eps: o["from"] = L.r4(start)
            if start + eps < o["to"] <= end + eps: o["to"] = L.r4(start)
            keep.append(o)
        if "overlays" in self.spec: self.spec["overlays"] = keep
        inside, keep = [], []
        for h in self.spec.get("audio", {}).get("hits", []):
            if start - eps <= h["at"] < end - eps:
                j = next(r["i"] for r in rows[a:b + 1] if r["start"] - eps <= h["at"] < r["end"] + eps)
                inside.append((h, L.out2src(self.spec["segments"][j], rows[j]["start"], h["at"])))
            else: keep.append(h)
        if inside: self.spec["audio"]["hits"] = keep
        del self.spec["segments"][a:b + 1]
        L.ripple(self.spec, end, -(end - start), self.fx)
        for l in L.renumber_fx(self.fx, a, -(b - a + 1)): self.note("dropped fx layer %s (seg %s)" % (l.get("type"), l.get("seg")))
        return start, inside

    def place_hits(self, inside, seg, start, fallback_drop=True):
        w = L.src_window(seg); hits = self.spec.setdefault("audio", {}).setdefault("hits", [])
        for h, src in inside:
            new = L.src2out(seg, start, src) if (src is not None and w and w[0] - L.EPS <= src <= w[1] + L.EPS) else None
            if new is None:
                self.note("dropped hit %s at %g (source %s is outside the new beat)" % (h.get("kind", "bass"), h["at"], "%.3f" % src if src is not None else "?")); continue
            self.note("hit %s %g -> %g (source %.3f)" % (h.get("kind", "bass"), h["at"], L.r4(new), src)); h["at"] = L.r4(new); hits.append(h)
        hits.sort(key=lambda h: h["at"])

    def op_drop(self, args):
        segs = []
        for sel in args:
            if sel.startswith("ov:"):
                i = L.find_ov(self.spec, sel); o = self.spec["overlays"].pop(i); self.note("dropped overlay %d %r (%g-%g)" % (i, L.ov_text(o)[:30], o["from"], o["to"]))
            elif sel.startswith("hit"):
                i = L.find_hit(self.spec, sel); h = self.spec["audio"]["hits"].pop(i); self.note("dropped hit %d %s at %g" % (i, h.get("kind", "bass"), h["at"]))
            else: segs.append(L.find_seg(self.spec, sel))
        for i in sorted(set(segs), reverse=True):
            lab = self.spec["segments"][i].get("label", ""); start, inside = self.remove_range(i, i, keep_edge=False)
            for h, _ in inside: self.note("dropped hit %s at %g (inside the dropped beat)" % (h.get("kind", "bass"), h["at"]))
            self.note("dropped seg %d %r" % (i, lab))

    def add_beat(self, idx, toks, inherit=None):
        seg, cap, hit = L.parse_beat(toks, self.fps())
        for k, v in list(seg.items()):  # key=@ copies the value from the beat being replaced
            if v == "@":
                if not inherit or k not in inherit: sys.exit("%s=@: nothing to inherit" % k)
                seg[k] = copy.deepcopy(inherit[k])
        if seg.get("src") and seg["src"] not in self.spec.get("sources", {}): sys.exit("source %r not in spec.sources %s" % (seg["src"], list(self.spec.get("sources", {}))))
        if "t" not in seg: sys.exit("beat needs an out time or +length")
        rows, total = self.rows(); start = rows[idx]["start"] if idx < len(rows) else total
        d = L.expected(seg, self.fps())
        L.ripple(self.spec, start, d, self.fx); L.renumber_fx(self.fx, idx, 1)
        self.spec["segments"].insert(idx, seg)
        if cap:
            win = cap.pop("_win"); o = {"from": L.r4(start + float(win["from"])) if "from" in win else start, "to": L.r4(start + float(win["to"])) if "to" in win else L.r4(start + d)}
            o.update(cap); self.spec.setdefault("overlays", []).append(o); self.note("caption %r %g-%g" % (L.ov_text(o)[:30], o["from"], o["to"]))
        if hit:
            off = hit.pop("_off"); h = {"at": L.r4(start + off), **hit}; hs = self.spec.setdefault("audio", {}).setdefault("hits", []); hs.append(h); hs.sort(key=lambda x: x["at"])
        return seg, start, d

    def op_insert(self, args):
        if len(args) < 5: sys.exit("insert <after:<seg>|before:<seg>|start|end> <beat line>")
        w = args[0]; n = len(self.spec["segments"])
        if w == "start": idx = 0
        elif w == "end": idx = n
        elif w.startswith("after:"): idx = L.find_seg(self.spec, w[6:]) + 1
        elif w.startswith("before:"): idx = L.find_seg(self.spec, w[7:])
        else: idx = L.find_seg(self.spec, w) + 1
        seg, start, d = self.add_beat(idx, args[1:])
        self.note("inserted seg %d %r at %.2f (%.2f s); later times moved +%.2f" % (idx, seg.get("label", seg["type"]), start, d, d))

    def op_replace(self, args):
        if "with" not in args: sys.exit("replace <a-b | a,b,c | seg> with <beat line>")
        k = args.index("with"); sels, beat = args[:k], args[k + 1:]
        idx = set()
        for s in sels:
            m = re.match(r"^(\d+)-(\d+)$", s)
            if m: idx.update(range(int(m.group(1)), int(m.group(2)) + 1))
            elif ".." in s:
                lo, hi = (L.find_seg(self.spec, p) for p in s.split("..", 1)); idx.update(range(lo, hi + 1))
            else: idx.update(L.find_seg(self.spec, p) for p in re.split(r',(?=(?:[^"]*"[^"]*")*[^"]*$)', s))
        idx = sorted(idx)
        a, b = idx[0], idx[-1]
        if idx != list(range(a, b + 1)): sys.exit("replace: segments must be contiguous (got %s)" % idx)
        labels = [self.spec["segments"][j].get("label", "") for j in idx]
        rows, total = self.rows(); old_d = rows[b]["end"] - rows[a]["start"]
        first = copy.deepcopy(self.spec["segments"][a]); start0, end0 = rows[a]["start"], rows[b]["end"]
        edge = [(o, o["to"] <= end0 + L.EPS) for o in self.spec.get("overlays", []) if abs(o["from"] - start0) < L.EPS]
        start, inside = self.remove_range(a, b)
        seg, start2, d = self.add_beat(a, beat, inherit=first)
        for o, contained in edge:
            o["from"] = L.r4(start)
            if contained: o["to"] = L.r4(start + d)
            self.note("refit overlay %r to %g-%g" % (L.ov_text(o)[:30], o["from"], o["to"]))
        self.place_hits(inside, seg, start2)
        self.note("replaced segs %d-%d %s with %r: %.2f -> %.2f s (later times %+.2f)" % (a, b, labels, seg.get("label", seg["type"]), old_d, d, d - old_d))

    def op_hit(self, args):
        if not args: sys.exit("hit add <at> <kind[:dur]> [k=v] | hit remove <sel>")
        if args[0] == "add":
            rows, total = self.rows(); pos, kv = L.parse_kv(args[1:])
            if len(pos) < 1: sys.exit("hit add <at> <kind[:dur]|file=path> [k=v]")
            h = {"at": L.resolve_time(pos[0], rows, total)}
            if len(pos) > 1:
                k, off, dur = L.parse_hit_tok(pos[1]); h["at"] = L.r4(h["at"] + off); h["kind"] = k
                if dur: h["dur"] = dur
            elif "file" in kv: h["kind"] = "file"
            else: sys.exit("hit add: give a kind or file=")
            h.update(kv); hs = self.spec.setdefault("audio", {}).setdefault("hits", []); hs.append(h); hs.sort(key=lambda x: x["at"])
            self.note("hit %s at %g" % (h.get("kind"), h["at"]))
        elif args[0] == "remove":
            for sel in args[1:]:
                i = L.find_hit(self.spec, sel); h = self.spec["audio"]["hits"].pop(i); self.note("removed hit %d %s at %g" % (i, h.get("kind", "bass"), h["at"]))
        else: sys.exit("hit add|remove")

    def op_caption(self, args):
        if not args or args[0] != "set": sys.exit("caption set <ov> [text=\"A|B\"] [from=] [to=] [key=value]")
        rows, total = self.rows(); i = L.find_ov(self.spec, args[1]); o = self.spec["overlays"][i]; pos, kv = L.parse_kv(args[2:])
        if pos: sys.exit("caption set: stray %r" % pos)
        if "text" in kv:
            lines = L.lines_of(kv.pop("text"))
            if o.get("big"): o["big"] = lines
            elif o.get("small"): o["small"] = lines
            elif o.get("extra"): o["extra"][0]["lines"] = lines
            else: o["big"] = lines
        for k in ("from", "to"):
            if k in kv: o[k] = L.resolve_time(kv.pop(k), rows, total)
        o.update(kv); self.note("caption %d %r %g-%g" % (i, L.ov_text(o)[:30], o["from"], o["to"]))
    op_ov = op_caption

    def apply(self, toks):
        if not toks: return
        name = toks[0]; fn = getattr(self, "op_" + name.replace("-", "_"), None)
        if not fn: sys.exit("unknown op %r (bump, set, unset, shift, slide, drop, insert, replace, hit, caption)" % name)
        before = copy.deepcopy(self.spec); print("== " + " ".join(toks)); fn(toks[1:]); L.diff(before, self.spec)

    def report(self):
        rows, total = self.rows(); L.print_timeline(rows, total); md = self.spec.get("max_duration", 30)
        if total > md: print("WARN total %.2f s over max_duration %s" % (total, md))
        for o in self.spec.get("overlays", []):
            if o["to"] > total + 0.01: print("WARN overlay %r ends at %g, after the video (%.2f)" % (L.ov_text(o)[:30], o["to"], total))
        for h in self.spec.get("audio", {}).get("hits", []):
            if h["at"] > total: print("WARN hit %s at %g is after the video" % (h.get("kind", "bass"), h["at"]))

    def write(self):
        L.tidy(self.spec, self.fx); L.dump(self.spec, self.path); print("wrote", os.path.relpath(self.path))
        if self.fx: json.dump(self.fx, open(self.fxpath, "w"), indent=1, ensure_ascii=False); print("wrote", os.path.relpath(self.fxpath))

def split_ops(argv):
    ops, cur = [], []
    for a in argv:
        if a == "--": ops.append(cur); cur = []
        else: cur.append(a)
    ops.append(cur); return [o for o in ops if o]

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec"); ap.add_argument("--fx", help="fx.vN.json whose layer seg indices and times follow the edit")
    ap.add_argument("--ops", help="file with one op per line (- for stdin)"); ap.add_argument("--dry", action="store_true", help="print, write nothing")
    ap.add_argument("--quiet", action="store_true", help="no final timeline")
    a, rest = ap.parse_known_args()
    ops = split_ops(rest)
    if a.ops:
        text = sys.stdin.read() if a.ops == "-" else open(a.ops).read()
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#"): ops.append(L.tokens(line))
    if not ops: sys.exit("no ops given (see --help)")
    S = Spec(a.spec, a.fx)
    r = L.rendered(S.spec, S.dir)
    if r and ops[0][0] != "bump": sys.exit("%s is rendered (%s): a rendered version is never edited in place. Start with `bump`." % (os.path.basename(a.spec), os.path.basename(r)))
    for op in ops: S.apply(op)
    if not a.quiet: S.report()
    if a.dry: print("(dry: nothing written)")
    else: S.write()

if __name__ == "__main__":
    main()
