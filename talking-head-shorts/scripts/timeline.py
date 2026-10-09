#!/usr/bin/env python3
"""Multi-clip timeline: several takes as chunks, gaps compressed, holds, picture-only inserts, marks -> cues. One source of truth.

  timeline.py init  <slug folder> [--joined NAME]   write a starter <slug>/timeline.py
  timeline.py run   <slug folder>                    run <slug>/timeline.py (writes timeline.json + cues.json, prints the chunk table)
  timeline.py check <slug folder>                    validate the written timeline.json (ranges, order, captions, marks, sfx)

<slug>/timeline.py imports this module and describes the cut (data contract: docs/multi-clip.md):

  import sys; sys.path.insert(0, "<plugin>/scripts")
  from timeline import Timeline
  T = Timeline(__file__, hook=0.9, tail=1.5, joined=None)      # joined="combined": picture AND voice come from the user's joined file
  T.add("G1", "good_news", 0.86, 1.72, z=[[0.86, 1.0], [1.72, 1.05]])    # id, clip, source in, out, zoom steps [src s, scale]
  T.add("V1", "good_news", 8.30, 9.55, voice=False)                      # picture-only insert (b-roll), no audio taken
  T.add("R1", "reel_share", 1.2, 9.8, hold=0.8, speed=1.0)               # hold: freeze the last frame, voice silent
  T.cap("G1", "SARJAPUR WALON,", 0.98, 1.64, hot=[])                     # caption phrase in the chunk's source seconds
  T.mark("makeup", T.O("G3", 4.62))                                       # named moment (output s): graphics, sfx, shakes hang off it
  T.shake(t, d, amp); T.flash(t, "#fff"); T.whip(t, d, dir)
  T.sfx(t, "boom", 0.9, maxlen=None); T.keep(a, b)                       # cue; window where cues may sound over speech
  T.music([[0, 0.0], [0.05, 0.9]], bed=None)                              # gain keys over output seconds
  T.finish()

Source times are seconds in the ORIGINAL clip, output times are seconds in the reel. Gap compression is automatic: output time
only advances by each chunk's own length (+ hold), so everything between chunks of one clip is simply not there; the table prints
what was skipped. Moving a chunk moves every mark, caption, cue and music key that was built with O()/mark().
"""
import argparse, json, pathlib, runpy, subprocess, sys

FPS = 30
STARTER = '''#!/usr/bin/env python3
import sys; sys.path.insert(0, "%(scripts)s")
from timeline import Timeline
T = Timeline(__file__, hook=0.0, tail=1.5, joined=%(joined)s)

# chunks: id, clip (a file in clips/), source in, out, zoom steps; alternate framing (1.0 / 1.1 / 1.2) across jump cuts
# T.add("A1", "take1", 0.5, 3.2, z=[[0.5, 1.0], [3.2, 1.05]])
# T.add("V1", "take1", 8.0, 9.0, voice=False)            # picture-only insert
# captions: chunk, text, source in, out, hot words (UPPERCASE as written)
# T.cap("A1", "HELLO EVERYONE", 0.6, 1.4, hot=["HELLO"])
# marks, cues, music
# T.mark("hello", T.O("A1", 0.6))
# T.sfx(T.marks["hello"], "swoosh", 0.4)
# T.keep(T.marks["hello"], T.marks["hello"] + 1.0)       # scenes that may carry sound over speech (ASK the user which)
# T.music([[0, 0.0], [0.1, 0.8], [T.end - 0.3, 0.8], [T.total, 0.0]])
T.finish()
'''


class Timeline:
    def __init__(self, script, hook=0.0, tail=1.5, joined=None, fps=FPS):
        self.dir = pathlib.Path(script).resolve().parent
        self.fps, self.hook, self.tail, self.joined = fps, hook, tail, joined
        self.chunks, self.cur = [], hook
        self.phrases, self.marks = [], {}
        self.shakes, self.flashes, self.whips, self.cues, self.keeps = [], [], [], [], []
        self.music_cfg = {"keys": [], "bed": None}
        self.off = {}
        if joined:
            p = self.dir / "offsets.json"
            self.off = json.loads(p.read_text()) if p.exists() else {}

    # ---- chunks ----
    def snap(self, t):
        return round(t * self.fps) / self.fps

    def add(self, id, clip, a, b, z=None, hold=0.0, voice=True, speed=1.0, **kw):
        assert all(c["id"] != id for c in self.chunks), "duplicate chunk id %s" % id
        assert b > a, "%s: out must be after in" % id
        d = (b - a) / speed
        vid, ca = clip, self.snap(a)
        if voice and self.joined and clip != self.joined:
            vid = self.joined
            ca = self.snap(a + self.off[clip]) if clip in self.off else None   # None until locate.py has run
        self.chunks.append(dict(id=id, clip=clip, a=a, b=b, o=round(self.cur, 3), d=round(d, 3), hold=hold, voice=voice, z=z or [[a, 1.0]],
                                speed=speed, vid=vid, ca=ca, **kw))
        self.cur += d + hold
        return self

    def chunk(self, id):
        return next(c for c in self.chunks if c["id"] == id)

    def O(self, id, src_t):
        """Output second of source second src_t inside chunk id (it must lie inside the chunk)."""
        c = self.chunk(id)
        assert c["a"] - 0.001 <= src_t <= c["b"] + 0.001, "%s: %.3f is outside the chunk %.3f-%.3f" % (id, src_t, c["a"], c["b"])
        return round(c["o"] + (src_t - c["a"]) / c["speed"], 3)

    @property
    def end(self):
        return round(self.cur, 3)

    @property
    def total(self):
        return round(self.cur + self.tail, 3)

    # ---- captions, marks, effects, cues ----
    def cap(self, chunk, text, a, b, hot=(), words=None):
        """Caption phrase; words are spread over a..b by letter count unless words=[(w, a, b), ...] gives their times (source s)."""
        c = self.chunk(chunk)
        if words is None:
            ws = text.split(); wt = [max(len(w), 2) for w in ws]; tot = sum(wt); t = a; words = []
            for w, k in zip(ws, wt):
                t1 = t + (b - a) * k / tot; words.append((w, t, t1)); t = t1
        out = [dict(w=w, a=self.O(chunk, wa), b=self.O(chunk, min(wb, c["b"])), hot=w in hot) for w, wa, wb in words]
        self.phrases.append(dict(a=self.O(chunk, a), b=self.O(chunk, min(b, c["b"])), words=out))
        return self

    def mark(self, name, t):
        self.marks[name] = round(t, 3)
        return t

    def shake(self, t, d, amp):
        self.shakes.append(dict(t=round(t, 3), d=d, a=amp))

    def flash(self, t, color="#ffffff"):
        self.flashes.append(dict(t=round(t, 3), c=color))

    def whip(self, t, d=0.28, dir=1):
        self.whips.append(dict(t=round(t, 3), d=d, dir=dir))

    def sfx(self, t, name, vol=0.5, maxlen=None):
        if vol <= 0:
            return
        self.cues.append([round(t, 3), name, vol] + ([maxlen] if maxlen else []))

    def keep(self, a, b):
        self.keeps.append([round(a, 3), round(b, 3)])

    def music(self, keys, bed=None):
        self.music_cfg = {"keys": keys, "bed": bed}

    # ---- output ----
    def files(self):
        names = {c["vid"] for c in self.chunks} | {c["clip"] for c in self.chunks}
        return {n: {"video": "clips/%s.mp4" % n, "audio": "audio/%s.wav" % n} for n in sorted(names)}

    def check(self):
        errs = []
        for c in self.chunks:
            if c["voice"] and self.joined and c["clip"] != self.joined and c["ca"] is None:
                errs.append("%s: no offset for clip '%s' (run locate.py, then timeline.py again)" % (c["id"], c["clip"]))
            for t, _ in c["z"]:
                if not c["a"] - 0.001 <= t <= c["b"] + 0.001:
                    errs.append("%s: zoom step at %.2f is outside the chunk" % (c["id"], t))
        for k, v in self.marks.items():
            if not 0 <= v <= self.total + 0.001:
                errs.append("mark %s = %.2f is outside the reel (0-%.2f)" % (k, v, self.total))
        for q in self.cues:
            if not 0 <= q[0] <= self.total:
                errs.append("sfx %s at %.2f is outside the reel" % (q[1], q[0]))
        return errs

    def table(self):
        last, lines = {}, ["%-5s %-12s %13s %7s %6s %5s %-9s %7s  skipped since the previous chunk of this clip" % ("id", "clip", "src in-out", "out at", "len", "hold", "from", "ca")]
        for c in self.chunks:
            gap = ""
            if c["clip"] in last and c["voice"]:
                g = c["a"] - last[c["clip"]]
                gap = "%.2f s cut out" % g if g > 0.005 else ""
            if c["voice"]:
                last[c["clip"]] = c["b"]
            lines.append("%-5s %-12s %5.2f-%-7.2f %7.2f %6.2f %5.2f %-9s %7s  %s%s" % (
                c["id"], c["clip"], c["a"], c["b"], c["o"], c["d"], c["hold"], c["vid"] if c["voice"] else "(picture)",
                "-" if c["ca"] is None else "%.3f" % c["ca"], gap, "" if c["speed"] == 1 else "  speed x%g" % c["speed"]))
        return "\n".join(lines)

    def finish(self):
        errs = self.check()
        files = self.files()
        tl = dict(fps=self.fps, total=self.total, hook=self.hook, end=self.end, files=files, chunks=self.chunks, phrases=self.phrases,
                  marks=self.marks, shakes=self.shakes, flashes=self.flashes, whips=self.whips)
        cues = dict(total=self.total, chunks=self.chunks, files=files, sfx=sorted(self.cues), keep=self.keeps, music=self.music_cfg, marks=self.marks)
        (self.dir / "timeline.json").write_text(json.dumps(tl, indent=1))
        (self.dir / "cues.json").write_text(json.dumps(cues, indent=1))
        print(self.table())
        print("\ntotal %.2f s = %d frames; %d chunks, %d phrases, %d marks, %d sfx cues, %d keep windows" % (
            self.total, round(self.total * self.fps), len(self.chunks), len(self.phrases), len(self.marks), len(self.cues), len(self.keeps)))
        for e in errs:
            print("PROBLEM:", e)
        return errs


def check_file(slug):
    tl = json.loads((slug / "timeline.json").read_text())
    errs, prev_end = [], 0.0
    for c in tl["chunks"]:
        if c["o"] + 0.001 < prev_end:
            errs.append("%s overlaps the previous chunk" % c["id"])
        prev_end = c["o"] + c["d"] + c["hold"]
        if c["voice"] and c.get("ca") is None:
            errs.append("%s has no ca (locate.py not run)" % c["id"])
    for p in tl["phrases"]:
        if not any(c["o"] - 0.05 <= p["a"] <= c["o"] + c["d"] + c["hold"] + 0.05 for c in tl["chunks"]):
            errs.append("caption '%s' at %.2f is outside every chunk" % (" ".join(w["w"] for w in p["words"]), p["a"]))
    return errs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["init", "run", "check"]); ap.add_argument("slug"); ap.add_argument("--joined")
    a = ap.parse_args()
    slug = pathlib.Path(a.slug).expanduser().resolve()
    f = slug / "timeline.py"
    if a.cmd == "init":
        if f.exists():
            sys.exit("%s exists" % f)
        slug.mkdir(parents=True, exist_ok=True)
        f.write_text(STARTER % dict(scripts=str(pathlib.Path(__file__).resolve().parent), joined=repr(a.joined) if a.joined else "None"))
        print("wrote", f)
    elif a.cmd == "run":
        if not f.exists():
            sys.exit("%s missing: timeline.py init %s" % (f, slug))
        runpy.run_path(str(f), run_name="__main__")
    else:
        errs = check_file(slug)
        print("\n".join(errs) if errs else "timeline ok")
        sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
