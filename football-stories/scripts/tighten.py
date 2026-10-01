#!/usr/bin/env python3
"""Shorten the silences in a narration take, re-align it, and patch exact times for spoken numbers.

  <venv>/bin/python tighten.py <story.vN.json> [--from build/narration_x.wav] [--out build/x.wav]
        [--between 0.35] [--within 0.25] [--numbers 0.30] [--hook 0.45] [--tail 0.6] [--pause L1:7=0.45]
  <venv>/bin/python tighten.py <story> --words-only      audio is already tight: align + number patch only

Bold Gemini voices leave 0.5-1.1 s between every line and ignore most <short pause> tags, so a
27 s script comes back at 33 s. This cuts every silence (ffmpeg silencedetect at -35 dB, gaps
under 0.12 s merged) down to a target that depends on where it falls in the script:
  between lines 0.35 s · within a line 0.25 s · within a number list (a line with 3+ spoken
  numbers) 0.30 s · the hook pause (a <pause>/<short pause> tag in the first line's tts, or any
  --pause LINE:WORD=SECONDS) 0.45 s, padded if the voice ran straight through · tail 0.6 s.
Silences already shorter than their target are kept as they are. Cuts are made in the middle of
each silence with a 10 ms crossfade, so no breath or consonant is clipped.

Output: build/<from>_tight.wav, then the same Whisper pass aligns the script to it
(build/words_<tight>.json, align.py's matcher). Whisper writes spoken numbers as digits
("fourteen" -> "14"), which align.py cannot match, so number words are re-matched with digits
and number words made comparable and get Whisper's own start/end; a run of number words heard
as one token ("twenty twenty-six" -> "2026") shares that token's span. The story gets
narration.audio, narration.words and narration.edit (the settings, the source, what was patched).
Pace is not changed. Needs the venv (faster-whisper, numpy).
"""
import argparse, json, pathlib, re, subprocess, sys, wave
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story, duration
from align import align, norm, transcribe

import difflib
import numpy as np

ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
NUM = {w: str(i) for i, w in enumerate(ONES)}
for k, t in enumerate(TENS):
    NUM[t] = str(20 + 10 * k)
    for i in range(1, 10):
        NUM[t + ONES[i]] = str(20 + 10 * k + i)
SCALE = {"hundred", "thousand", "million", "billion"}
MIN_SIL, MERGE, XFADE, SLACK, EDGE = 0.06, 0.03, 0.010, 0.08, 0.03


def canon(w):
    n = norm(w)
    return NUM.get(n, n)

def is_num(w):
    c = canon(w)
    return bool(c) and (c.isdigit() or c in SCALE or bool(re.fullmatch(r"\d+(st|nd|rd|th|s)", c)))


# ---------- silences
def silences(wav, noise):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "silencedetect=n=%gdB:d=%g" % (noise, MIN_SIL),
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    total = duration(wav)
    sil = [[max(0.0, s), ends[i] if i < len(ends) else total] for i, s in enumerate(starts)]
    merged = []
    for s, e in sil:
        if merged and s - merged[-1][1] < MERGE: merged[-1][1] = e
        else: merged.append([s, e])
    return merged, total


def classify(st, words, sils, total, a):
    """One edit per word gap: shorten Whisper's gap (end of a word to the start of the next) to the
    target for its place in the script, removing samples only from the silence measured inside it."""
    lines = st.lines
    numlist = {l["id"] for l in lines if sum(is_num(w) for w in l["text"].split()) >= 3}
    hook = set()
    first = lines[0]
    if "tts" in first and re.search(r"<[^>]*pause[^>]*>", first["tts"]):
        n = 0
        for tok in re.split(r"(<[^>]+>)", first["tts"]):
            if re.fullmatch(r"<[^>]*pause[^>]*>", tok): hook.add((first["id"], n - 1))
            elif not tok.startswith("<"): n += len([w for w in tok.split() if norm(w)])
        if n != len(first["text"].split()):
            print("warn: %s tts and text have different word counts; hook pause placed by word count" % first["id"])
    extra = {}
    for p in a.pause or []:
        m = re.fullmatch(r"(\w+):(-?\d+)=([\d.]+)", p) or sys.exit("--pause wants LINE:WORD=SECONDS, e.g. L1:7=0.45")
        extra[(m.group(1), int(m.group(2)))] = float(m.group(3))

    plan, used = [], set()
    if sils and sils[0][0] < 0.02:      # lead-in silence
        used.add(0); plan.append({"kind": "lead", "after": None, "gap": sils[0][1], "at": 0.0, "remove": max(0.0, sils[0][1] - 0.05)})
    if sils and sils[-1][1] > total - 0.02 and len(sils) - 1 not in used:
        used.add(len(sils) - 1); tail = sils[-1][1] - sils[-1][0]
    else:
        tail = 0.0
    for k in range(len(words) - 1):
        w, nxt = words[k], words[k + 1]
        key = (w["line"], w["i"])
        if key in extra: kind, target = "pause", extra[key]
        elif key in hook: kind, target = "hook", a.hook
        elif w["line"] != nxt["line"]: kind, target = "between", a.between
        elif w["line"] in numlist: kind, target = "numbers", a.numbers
        else: kind, target = "within", a.within
        cand = [j for j, (s, e) in enumerate(sils) if j not in used and w["end"] - SLACK <= (s + e) / 2 <= nxt["start"] + SLACK]
        g = max(0.0, nxt["start"] - w["end"])
        if cand:
            j = max(cand, key=lambda j: sils[j][1] - sils[j][0]); used.add(j)
            s, e = sils[j]; g = max(g, e - s)
            remove = min(g - target, (e - s) - 2 * EDGE)
            at = (s + e) / 2
        else:
            remove, at = 0.0, (w["end"] + nxt["start"]) / 2
        if remove > 0.02:
            plan.append({"kind": kind, "after": "%s:%d" % key, "gap": g, "at": at, "remove": remove})
        elif g < target - 0.02 and kind in ("hook", "pause"):      # the voice ran through a deliberate pause: pad it
            plan.append({"kind": kind, "after": "%s:%d" % key, "gap": g, "at": at, "remove": -(target - g)})
    for j, (s, e) in enumerate(sils):  # a long silence Whisper put inside a word: cut it to the in-line target
        if j not in used and e - s > a.within + 0.05:
            plan.append({"kind": "within", "after": "~%.2fs" % s, "gap": e - s, "at": (s + e) / 2, "remove": (e - s) - a.within})
    plan.append({"kind": "tail", "after": None, "gap": tail, "at": total, "remove": tail - a.tail})
    return sorted(plan, key=lambda p: p["at"])


def cut(src, out, plan):
    with wave.open(str(src)) as w:
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        if sw != 2: sys.exit("tighten.py expects 16-bit PCM wav, got %d-byte samples" % sw)
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch).astype(np.float32)
    n, f = len(x), int(XFADE * sr) // 2 * 2; pieces, pos = [], 0
    for p in plan:
        r, c = int(abs(p["remove"]) * sr), int(p["at"] * sr)
        if p["kind"] == "lead":
            pos = r
        elif p["kind"] == "tail":
            rest = x[pos:]
            pieces.append(rest[:len(rest) - r] if p["remove"] > 0 else np.concatenate([rest, np.zeros((r, ch), np.float32)])); pos = n
        elif p["remove"] < 0:
            pieces.append(x[pos:c]); pieces.append(np.zeros((r, ch), np.float32)); pos = c
        else:
            a0, b0 = c - r // 2, c + (r - r // 2)
            ramp = np.linspace(0, 1, f, dtype=np.float32)[:, None]
            pieces.append(x[pos:a0 - f // 2])
            pieces.append(x[a0 - f // 2:a0 + f // 2] * (1 - ramp) + x[b0 - f // 2:b0 + f // 2] * ramp)
            pos = b0 + f // 2
    if pos < n: pieces.append(x[pos:])
    y = np.clip(np.concatenate(pieces), -32768, 32767).astype(np.int16)
    with wave.open(str(out), "wb") as w:
        w.setnchannels(ch); w.setsampwidth(2); w.setframerate(sr); w.writeframes(y.tobytes())


# ---------- numbers
def patch_numbers(st, words, heard):
    """Give spelled-out number words Whisper's times (it heard them as digits)."""
    A = [canon(w["w"]) for w in words]; B = [canon(h[0]) for h in heard]
    blocks = difflib.SequenceMatcher(a=A, b=B, autojunk=False).get_matching_blocks()
    done, pa, pb = [], 0, 0
    def setw(k, s, e):
        old = (words[k]["start"], words[k]["end"])
        words[k]["start"], words[k]["end"] = round(s, 3), round(e, 3)
        done.append({"word": "%s:%d" % (words[k]["line"], words[k]["i"]), "w": words[k]["w"], "was": old, "now": (words[k]["start"], words[k]["end"])})
    for a0, b0, n in blocks:
        R, Hh = list(range(pa, a0)), heard[pb:b0]
        if R and Hh and all(is_num(words[k]["w"]) for k in R) and all(is_num(h[0]) for h in Hh):
            s0, s1 = Hh[0][1], Hh[-1][2]; lens = [len(norm(words[k]["w"])) or 1 for k in R]; acc = 0
            for k, L in zip(R, lens):
                setw(k, s0 + (s1 - s0) * acc / sum(lens), s0 + (s1 - s0) * (acc + L) / sum(lens)); acc += L
        for j in range(n):
            k = a0 + j
            if A[k].isdigit() and not norm(words[k]["w"]).isdigit():
                setw(k, heard[b0 + j][1], heard[b0 + j][2])
        pa, pb = a0 + n, b0 + n
    missed = [w for w in words if is_num(w["w"]) and canon(w["w"]).isdigit() and not norm(w["w"]).isdigit()
              and "%s:%d" % (w["line"], w["i"]) not in {d["word"] for d in done}]
    return done, missed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--from", dest="src"); ap.add_argument("--out")
    ap.add_argument("--between", type=float, default=0.35); ap.add_argument("--within", type=float, default=0.25)
    ap.add_argument("--numbers", type=float, default=0.30); ap.add_argument("--hook", type=float, default=0.45)
    ap.add_argument("--tail", type=float, default=0.6)
    ap.add_argument("--noise", type=float, default=-30, help="silence threshold in dB (default -30)")
    ap.add_argument("--pause", action="append", help="LINE:WORD=SECONDS after that word (0-based word index), repeatable")
    ap.add_argument("--words-only", action="store_true", help="the audio is already tight: align and patch numbers only")
    ap.add_argument("--model", default="small.en"); ap.add_argument("--no-update", action="store_true")
    a = ap.parse_args()
    st = Story(a.story); nar = st.data["narration"]
    from faster_whisper import WhisperModel
    model = WhisperModel(a.model, device="cpu", compute_type="int8")

    edit = nar.get("edit") if isinstance(nar.get("edit"), dict) else {}
    if a.words_only:
        tight = st.p(a.src or nar.get("audio") or sys.exit("no narration.audio: run tts.py first"))
        src = None
    else:
        rel = a.src or edit.get("from") or nar.get("audio") or sys.exit("no narration.audio: run tts.py first")
        src = st.p(rel)
        if src.stem.endswith("_tight") and not a.src: sys.exit("%s is already tight; pass --from <untightened wav>" % rel)
        tight = st.out(a.out) if a.out else st.build / ("%s_tight.wav" % src.stem)
        wf = st.build / ("words_%s.json" % src.stem)
        if wf.exists() and json.loads(wf.read_text()) and len(json.loads(wf.read_text())) == len(st.script_words()):
            words = json.loads(wf.read_text())
        else:
            words, _ = align(st, src, transcribe(src, model))
        sils, total = silences(src, a.noise)
        plan = classify(st, words, sils, total, a)
        cut(src, tight, plan)
        for p in plan:
            if abs(p["remove"]) > 0.005:
                print("  %-8s after %-7s %.2f s -> %.2f s" % (p["kind"], p["after"] or "-", p["gap"], p["gap"] - p["remove"]))
        print("%s %.2f s -> %s %.2f s" % (src.name, total, tight.name, duration(tight)))

    heard = transcribe(tight, model)
    words, report = align(st, tight, heard)
    done, missed = patch_numbers(st, words, heard)
    wpath = st.p(report["words"])
    wpath.write_text(json.dumps(words, indent=1))
    print("aligned %d/%d words before the number patch -> %s" % (report["matched"], report["total"], wpath.relative_to(st.dir)))
    for d in done:
        if tuple(d["was"]) != tuple(d["now"]): print("  number %-6s %-10s %.2f-%.2f -> %.2f-%.2f" % (d["word"], d["w"], *d["was"], *d["now"]))
    for w in missed:
        print("warn: number %s:%d %r not found in the Whisper pass; timing interpolated" % (w["line"], w["i"], w["w"]))
    for f in report["flags"]:
        if f["heard"] and f["similarity"] >= 0.5:
            print("CHECK %s word %d: script %r, heard %r: possible mispronunciation" % (f["line"], f["i"], f["script"], f["heard"]))
    d = duration(tight)
    print("duration %.2f s%s" % (d, "" if 20 <= d <= st.data.get("length", {}).get("max", 30) else "  (target 20-%g s)" % st.data.get("length", {}).get("max", 30)))

    if a.no_update or a.out or st.rendered():
        if st.rendered(): print("note: %s is already rendered, so the story was not updated" % st.mp4.name)
        return
    rel = lambda p: str(p.relative_to(st.dir))
    if src is not None:
        edit = {"from": rel(src), "between": a.between, "within": a.within, "numbers": a.numbers, "hook": a.hook, "tail": a.tail,
                "pauses": a.pause or [], "duration": round(d, 2)}
    edit["numbers_patched"] = [x["word"] for x in done]
    nar["audio"], nar["words"], nar["edit"] = rel(tight), rel(wpath), edit
    st.save()


if __name__ == "__main__":
    main()
