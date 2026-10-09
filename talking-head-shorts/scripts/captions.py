#!/usr/bin/env python3
"""Turn the words the USER confirmed into caption phrases timed from the audio.

  captions.py <slug folder> [--text captions.txt] [--transcript transcript.json] [--window S E]

captions.txt: one caption phrase per line, exactly the words and spelling the user wants on screen
("bezzati", not "behzati"). Numbers stay as digits. Blank lines and lines starting with # are ignored.

Whisper cannot spell Hinglish, so its words are only used as TIME anchors: each confirmed word is matched
to a Whisper word when they look alike (monotonic alignment, difflib similarity >= 0.6). Words with no
match are spread over the audio that is actually loud between their neighbours' anchors (so a pause is not
eaten by a caption), weighted by letters. Output:
  <slug>/captions.json   {"phrases": [[[word, start, end], ...], ...]}   source seconds, paste into edit.json
  and a report: matched / interpolated counts and every interpolated word with its time, so shaky timing
  is something to LOOK at (sheet around those seconds), never silently trusted.
"""
import argparse, difflib, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import cut_wav, speech_regions


def norm(w):
    return re.sub(r"[^a-z0-9ãõéíóúç]", "", w.lower())


def sim(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if a.isdigit() or b.isdigit():
        return 1.0 if a == b else 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def align(tokens, words, thr=0.6):
    """Monotonic alignment (Needleman-Wunsch on similarity). Returns {token index: whisper index}."""
    n, m = len(tokens), len(words)
    S = [[sim(tokens[i], words[j]["w"]) for j in range(m)] for i in range(n)]
    H = [[0.0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            s = S[i - 1][j - 1]
            H[i][j] = max(H[i - 1][j], H[i][j - 1], H[i - 1][j - 1] + (s if s >= thr else -9))
    out, i, j = {}, n, m
    while i > 0 and j > 0:
        s = S[i - 1][j - 1]
        if s >= thr and abs(H[i][j] - (H[i - 1][j - 1] + s)) < 1e-9:
            out[i - 1] = j - 1; i -= 1; j -= 1
        elif H[i][j] == H[i - 1][j]:
            i -= 1
        else:
            j -= 1
    return out


def spread(tokens_idx, tokens, t0, t1, active):
    """Place tokens_idx (consecutive tokens) over the loud parts of [t0, t1], weighted by letters."""
    segs = [(max(a, t0), min(b, t1)) for a, b in active if b > t0 and a < t1]
    segs = [(a, b) for a, b in segs if b - a > 0.02] or [(t0, t1)]
    total = sum(b - a for a, b in segs)
    wts = [max(2, len(norm(tokens[i]))) for i in tokens_idx]
    W = sum(wts)
    out, cum = [], 0.0
    def at(x):  # position x (0..total of loud time) -> seconds
        for a, b in segs:
            if x <= b - a + 1e-9:
                return a + x
            x -= b - a
        return segs[-1][1]
    for i, w in zip(tokens_idx, wts):
        out.append((i, at(cum / W * total), at((cum + w) / W * total)))
        cum += w
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--text"); ap.add_argument("--transcript")
    ap.add_argument("--window", nargs=2, type=float, metavar=("S", "E"))
    a = ap.parse_args()
    folder = pathlib.Path(a.folder).expanduser().resolve()
    text = pathlib.Path(a.text or folder / "captions.txt").read_text()
    tr = json.loads(pathlib.Path(a.transcript or folder / "transcript.json").read_text())
    words = tr["words"]
    start, end = a.window or (tr["window"][0] or 0.0, tr["window"][1])
    src = next(iter(sorted(folder.glob("source.*"))))
    wav = folder / "audio_window.wav"
    cut_wav(src, wav, start, end)
    active = [(s + start, e + start) for s, e in speech_regions(wav, floor_db=-34, min_len=0.06, join=0.12)]

    phrases = [ln.split() for ln in (l.strip() for l in text.splitlines()) if ln and not ln.startswith("#")]
    tokens = [w for p in phrases for w in p]
    m = align(tokens, words)
    t = [[None, None] for _ in tokens]
    for i, j in m.items():
        t[i] = [words[j]["s"], words[j]["e"]]
    # unmatched runs: spread between the neighbours' anchors over loud time
    interp, i = [], 0
    while i < len(tokens):
        if t[i][0] is not None:
            i += 1; continue
        j = i
        while j < len(tokens) and t[j][0] is None:
            j += 1
        t0 = t[i - 1][1] if i > 0 else start
        t1 = t[j][0] if j < len(tokens) else (end or (words[-1]["e"] + 0.5))
        for k, s, e in spread(list(range(i, j)), tokens, t0, max(t1, t0 + 0.1), active):
            t[k] = [s, e]; interp.append(k)
        i = j
    # a word ends when the next starts, unless a pause follows (then keep its own end)
    for k in range(len(tokens) - 1):
        gap = t[k + 1][0] - t[k][1]
        if 0 <= gap < 0.25:
            t[k][1] = t[k + 1][0]
        if t[k][1] <= t[k][0]:
            t[k][1] = t[k][0] + 0.12
    for k in range(len(tokens) - 1):  # never overlap: a word that ends after the next one starts is cut there
        if t[k][1] > t[k + 1][0]:
            t[k][1] = max(t[k + 1][0], t[k][0] + 0.06)
            if t[k + 1][0] < t[k][1]:
                t[k + 1][0] = t[k][1]
        if t[k + 1][1] <= t[k + 1][0]:
            t[k + 1][1] = t[k + 1][0] + 0.12
    out, k = [], 0
    for p in phrases:
        out.append([[w, round(t[k + n][0], 2), round(t[k + n][1], 2)] for n, w in enumerate(p)])
        k += len(p)
    json.dump({"phrases": out}, open(folder / "captions.json", "w"), ensure_ascii=False)
    print("captions: %d phrases, %d words; %d matched to Whisper timing, %d interpolated from the audio" % (len(out), len(tokens), len(m), len(interp)))
    for p in out:
        print("  %5.2f-%5.2f  %s" % (p[0][1], p[-1][2], " ".join(w[0] for w in p)))
    if interp:
        print("interpolated (no Whisper match; check these on a sheet): " + ", ".join("%s@%.2f" % (tokens[k], t[k][0]) for k in interp))


if __name__ == "__main__":
    main()
