#!/usr/bin/env python3
"""Word timings for Hinglish narration from the pauses in the take (English Whisper can't transcribe Hinglish).

  segalign.py <story.vN.json> [--audio build/narration_x.wav] [--lead 0.5]
  segalign.py <story> --segments build/segments.json      re-time from a hand-fixed segment map
  segalign.py <story> --anchors <python with faster-whisper>   let cached small.en anchor English words

1. ffmpeg silencedetect (noise -35 dB, at least 0.12 s) splits the take into speech segments.
2. The script's words are split into groups, one per segment, by a dynamic programme that keeps
   each group's length (characters) in proportion to its segment's duration, prefers group ends
   at line ends (very strongly when the pause is long) and at punctuation, and penalises a split
   mid-phrase. A blip under 0.25 s just before speech is merged into it (a word onset); other
   very short segments (a breath or a click) may stay empty.
3. Inside a segment, words share its time in proportion to their length (+2, +3 more after "...").
4. --lead S pads S seconds of silence before the voice (room for an opening sound such as a
   phone ring) -> build/<audio>_lead<ms>.wav, and shifts every word by S.

Writes build/segments.json (segment -> line, first/last word, text: read it, and if a group is in
the wrong segment, edit i0/i1/line there and re-run with --segments) and build/words_segments.json,
and sets narration.audio / narration.words / narration.lead in the story.

--anchors: a python that has faster-whisper. small.en is loaded with local_files_only (never
downloaded); the English words it hears (names, years spoken in English, loan words) pull the
groups toward their times. Without it the pauses alone decide. Stdlib + ffmpeg.
"""
import argparse, json, math, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story, duration

norm = lambda t: re.sub(r"[^a-z0-9]", "", t.lower())


def silences(wav, noise, min_sil):
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(wav), "-af", "silencedetect=noise=%sdB:d=%s" % (noise, min_sil),
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def speech_segments(wav, noise, min_sil):
    total = duration(wav); segs, t = [], 0.0
    for a, b in silences(wav, noise, min_sil):
        if a - t > 0.05: segs.append((round(t, 3), round(a, 3)))
        t = b if b is not None else total
    if total - t > 0.05: segs.append((round(t, 3), round(total, 3)))
    # a blip under 0.25 s right before speech (gap < 0.2 s) is a word onset ("A-lexander"): merge it forward
    out = []
    for s in segs:
        if out and out[-1][1] - out[-1][0] < 0.25 and s[0] - out[-1][1] < 0.2:
            s = (out.pop()[0], s[1])
        out.append(s)
    return out


def weight(w):
    return len(w.strip('".,?!:;()')) + 2 + (3 if w.endswith("...") else 0)


def words_of(st):
    """[(line, i, word, weight, boundary)] boundary: 2 line end, 1 punctuation, 0 mid-phrase."""
    out = []
    for l in st.lines:
        ws = l["text"].split()
        for i, w in enumerate(ws):
            b = 2 if i == len(ws) - 1 else (1 if re.search(r"(\.\.\.|[,.?!:;])[\"']?$", w) else 0)
            out.append((l["id"], i, w, weight(w), b))
    return out


def anchors(py, wav):
    """English words cached small.en hears: [(norm word, start, end)]. Never downloads."""
    code = ("import json,sys\nfrom faster_whisper import WhisperModel\n"
            "m=WhisperModel('small.en',device='cpu',compute_type='int8',local_files_only=True)\n"
            "s,_=m.transcribe(sys.argv[1],word_timestamps=True,language='en',beam_size=5)\n"
            "print(json.dumps([(w.word.strip(),w.start,w.end) for x in s for w in x.words]))")
    r = subprocess.run([py, "-c", code, str(wav)], capture_output=True, text=True)
    if r.returncode:
        print("anchors skipped: %s" % (r.stderr.strip().splitlines() or ["?"])[-1]); return []
    return [(norm(w), a, b) for w, a, b in json.loads(r.stdout) if len(norm(w)) >= 4 or norm(w).isdigit()]


def solve(words, segs, heard):
    """Partition words into len(segs) contiguous groups (short segments may be empty) -> [(i0, i1) or None]."""
    N, S = len(words), len(segs)
    speech = sum(b - a for a, b in segs); rate = speech / sum(w[3] for w in words)
    gaps = [segs[j + 1][0] - segs[j][1] for j in range(S - 1)] + [9.9]
    pre = [0]
    for w in words: pre.append(pre[-1] + w[3])
    # anchor: script word k heard at time tau -> it should sit in the segment containing tau
    anc = {}
    for k, w in enumerate(words):
        n = norm(w[2])
        if len(n) < 4 and not n.isdigit(): continue
        hits = [(a + b) / 2 for h, a, b in heard if h == n]
        if len(hits) == 1: anc[k] = hits[0]

    def cost(i, k, j):                    # words i..k-1 in segment j
        a, b = segs[j]; d = b - a; c = (pre[k] - pre[i]) * rate
        x = 4.0 * math.log((d + 0.15) / (c + 0.15)) ** 2
        bnd = words[k - 1][4]; g = gaps[j]
        if g >= 0.32: x += {2: 0.0, 1: 0.6, 0: 3.0}[bnd]      # long pause: expect a line end
        else: x += {2: 0.3, 1: 0.0, 0: 1.0}[bnd]
        for q in range(i, k):
            if q in anc and not (a - 0.15 <= anc[q] <= b + 0.15): x += 3.0
        return x

    INF = float("inf")
    best = [[INF] * (N + 1) for _ in range(S + 1)]; back = [[None] * (N + 1) for _ in range(S + 1)]
    best[0][0] = 0.0
    for j in range(S):
        short = segs[j][1] - segs[j][0] < 0.25
        for i in range(N + 1):
            if best[j][i] == INF: continue
            if short and best[j][i] + 0.8 < best[j + 1][i]:           # leave a breath/click empty
                best[j + 1][i] = best[j][i] + 0.8; back[j + 1][i] = (i, True)
            for k in range(i + 1, N + 1):
                if (pre[k] - pre[i]) * rate > 4 * (segs[j][1] - segs[j][0]) + 2: break
                v = best[j][i] + cost(i, k, j)
                if v < best[j + 1][k]: best[j + 1][k] = v; back[j + 1][k] = (i, False)
    if best[S][N] == INF: sys.exit("no alignment found: check the noise level (--noise) or fix build/segments.json by hand")
    groups, k = [], N
    for j in range(S, 0, -1):
        i, empty = back[j][k]; groups.append(None if empty else (i, k)); k = i
    return groups[::-1], best[S][N]


def spread(words, segs, groups, lead):
    out = []
    for (a, b), g in zip(segs, groups):
        if not g: continue
        ws = words[g[0]:g[1]]; tot = sum(w[3] for w in ws); t = a
        for line, i, w, wt, _ in ws:
            d = (b - a) * wt / tot
            out.append({"line": line, "i": i, "w": w, "start": round(t + lead, 3), "end": round(t + d + lead, 3)})
            t += d
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("story"); ap.add_argument("--audio", help="default: narration.audio_raw")
    ap.add_argument("--lead", type=float, help="seconds of silence before the voice (default: narration.lead or 0)")
    ap.add_argument("--noise", default="-35"); ap.add_argument("--min-sil", type=float, default=0.12)
    ap.add_argument("--segments", help="hand-fixed segments.json to time from (skips the solver)")
    ap.add_argument("--anchors", help="python with faster-whisper: anchor English words with cached small.en")
    ap.add_argument("--no-update", action="store_true")
    a = ap.parse_args()
    st = Story(a.story); n = st.data["narration"]
    rel = a.audio or n.get("audio_raw") or n.get("audio")
    if not rel: sys.exit("no narration audio yet: run tts.py first")
    wav = st.p(rel); lead = a.lead if a.lead is not None else n.get("lead", 0.0)
    words = words_of(st)
    idx = {(w[0], w[1]): k for k, w in enumerate(words)}

    if a.segments:
        m = json.loads(st.p(a.segments).read_text())
        segs = [(s["start"], s["end"]) for s in m["segments"]]
        groups = [None if s.get("line") is None else (idx[(s["line"], s["i0"])], idx[(s["line"], s["i1"])] + 1) for s in m["segments"]]
        flat = [k for g in groups if g for k in range(*g)]
        if flat != list(range(len(words))): sys.exit("segments.json must cover every word once, in order (got %d of %d)" % (len(flat), len(words)))
        score = None
    else:
        segs = speech_segments(wav, a.noise, a.min_sil)
        heard = anchors(a.anchors, wav) if a.anchors else []
        if len(segs) < len(st.lines) // 2: sys.exit("only %d speech segments found: try --noise -40" % len(segs))
        groups, score = solve(words, segs, heard)
        if heard: print("anchors: %d English words heard by small.en" % len(heard))

    rows = []
    for (s, e), g in zip(segs, groups):
        r = {"start": s, "end": e}
        if g:
            w0, w1 = words[g[0]], words[g[1] - 1]
            if w0[0] != w1[0]: r.update({"line": w0[0], "i0": w0[1], "line_end": w1[0], "i1_end": w1[1]})
            else: r.update({"line": w0[0], "i0": w0[1], "i1": w1[1]})
            r["text"] = " ".join(w[2] for w in words[g[0]:g[1]])
        else: r.update({"line": None, "text": "(empty: breath or click)"})
        rows.append(r)
    st.build.mkdir(exist_ok=True)
    (st.build / "segments.json").write_text(json.dumps({"audio": rel, "noise": a.noise, "min_sil": a.min_sil, "segments": rows},
                                                       indent=1, ensure_ascii=False))
    out = spread(words, segs, groups, lead)
    assert len(out) == len(words)
    (st.build / "words_segments.json").write_text(json.dumps(out, indent=0, ensure_ascii=False))

    print("%d speech segments, %d words%s" % (len(segs), len(out), "" if score is None else ", cost %.1f" % score))
    for r in rows:
        print("  %6.2f-%6.2f  %s" % (r["start"] + lead, r["end"] + lead, r["text"]))
    cross = [r for r in rows if r.get("line_end")]
    if cross: print("check: %d segment(s) run across a line break (the voice did not pause there); fine if it sounds so" % len(cross))
    print("Wrong group? Edit build/segments.json (line/i0/i1 per segment) and re-run with --segments build/segments.json")

    audio = wav
    if lead > 0:
        audio = st.build / ("%s_lead%d.wav" % (wav.stem, round(lead * 1000)))
        ms = round(lead * 1000)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-af", "adelay=%d:all=1" % ms, str(audio)], check=True)
    if a.no_update: return
    if st.rendered():
        print("note: %s is already rendered; story not updated (revise makes the next version)" % st.mp4.name); return
    n["audio"] = str(audio.relative_to(st.dir)); n["words"] = "build/words_segments.json"; n["lead"] = lead
    n["words_note"] = "pause-segment timings (segalign.py)"
    st.save(); print("story updated: audio %s, words build/words_segments.json, lead %g s" % (n["audio"], lead))


if __name__ == "__main__":
    main()
