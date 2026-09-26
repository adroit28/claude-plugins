#!/usr/bin/env python3
"""Word timings for the story's narration -> build/words_<audio>.json, plus likely mispronunciations.

  <venv>/bin/python align.py <story.vN.json> [--audio build/narration_x.wav]

Whisper (faster-whisper small.en, CPU int8) supplies times; the words themselves come from the
script, because Whisper's spelling of names and numbers is not trusted. Words are matched in
order by normalised text with difflib, and unmatched script words are interpolated between
their matched neighbours. A script word that Whisper heard as a different word in the same gap
is flagged as a possible mispronunciation (e.g. Satpayev heard as Satayev): check it by ear, and
if it is wrong add a respelling to shorts/lexicon.json and take again.
"""
import argparse, difflib, json, pathlib, re, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story

norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--audio"); ap.add_argument("--model", default="small.en")
    ap.add_argument("--no-update", action="store_true")
    a = ap.parse_args()
    st = Story(a.story)
    wav = st.p(a.audio or st.data["narration"].get("audio") or sys.exit("no narration.audio: run tts.py first"))
    from faster_whisper import WhisperModel
    m = WhisperModel(a.model, device="cpu", compute_type="int8")
    segs, _ = m.transcribe(str(wav), word_timestamps=True, language="en", beam_size=5)
    heard = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words]
    want = st.script_words()
    sm = difflib.SequenceMatcher(a=[norm(w) for _, _, w in want], b=[norm(h[0]) for h in heard], autojunk=False)
    blocks = sm.get_matching_blocks()
    t = [None] * len(want)
    for a0, b0, n in blocks:
        for k in range(n): t[a0 + k] = heard[b0 + k][1:]

    # possible mispronunciations: unmatched script runs paired with the unmatched heard run in the same gap
    flags, pa, pb = [], 0, 0
    for a0, b0, n in blocks:
        gap_w, gap_h = list(range(pa, a0)), heard[pb:b0]
        for i in gap_w:
            w = want[i][2]
            best = max(gap_h, key=lambda h: difflib.SequenceMatcher(None, norm(w), norm(h[0])).ratio(), default=None)
            flags.append({"line": want[i][0], "i": want[i][1], "script": w, "heard": best[0] if best else None,
                          "similarity": round(difflib.SequenceMatcher(None, norm(w), norm(best[0])).ratio(), 2) if best else 0})
        pa, pb = a0 + n, b0 + n

    for i in range(len(want)):
        if t[i] is None:
            p = next((j for j in range(i - 1, -1, -1) if t[j]), None); q = next((j for j in range(i + 1, len(want)) if t[j]), None)
            s0 = t[p][1] if p is not None else 0.0; s1 = t[q][0] if q is not None else s0 + 0.4
            gap = list(range(p + 1 if p is not None else 0, q if q is not None else len(want)))
            k = gap.index(i); step = (s1 - s0) / len(gap); t[i] = (s0 + k * step, s0 + (k + 1) * step)

    out = [{"line": L, "i": i, "w": w, "start": round(x, 3), "end": round(y, 3)} for (L, i, w), (x, y) in zip(want, t)]
    words_path = st.build / ("words_%s.json" % wav.stem)
    words_path.write_text(json.dumps(out, indent=1))
    matched = sum(n for _, _, n in blocks)
    report = {"audio": str(wav.relative_to(st.dir)), "matched": matched, "total": len(want), "heard": " ".join(h[0] for h in heard), "flags": flags}
    (st.build / ("align_%s.json" % wav.stem)).write_text(json.dumps(report, indent=1, ensure_ascii=False))

    print("heard:", report["heard"])
    print("matched %d/%d script words -> %s" % (matched, len(want), words_path.relative_to(st.dir)))
    for L in st.lines:
        ws = [o for o in out if o["line"] == L["id"]]
        print("%s %6.2f-%6.2f  %s" % (L["id"], ws[0]["start"], ws[-1]["end"], L["text"]))
    lex = json.loads((st.shorts / "lexicon.json").read_text()) if (st.shorts / "lexicon.json").exists() else {}
    for f in flags:
        clean = re.sub(r"[^\w'-]", "", f["script"])
        if f["heard"] and f["similarity"] >= 0.5:
            tip = "respelling already in lexicon" if clean in lex else "if it sounds wrong, add a respelling to shorts/lexicon.json"
            print("CHECK %s word %d: script %r, heard %r (similarity %.2f): possible mispronunciation; %s"
                  % (f["line"], f["i"], f["script"], f["heard"], f["similarity"], tip))
        else:
            print("note  %s word %d %r not matched (heard %r); timing interpolated" % (f["line"], f["i"], f["script"], f["heard"]))

    if not a.no_update and not st.rendered():
        st.data["narration"]["words"] = str(words_path.relative_to(st.dir)); st.save()


if __name__ == "__main__":
    main()
