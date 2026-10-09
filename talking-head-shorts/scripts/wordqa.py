#!/usr/bin/env python3
"""Word QA on the CUT voice: what is said vs what the captions say, and where captions and speech disagree.

  wordqa.py <slug folder> [--voice voice_cut.wav] [--model small] [--langs hi,en]

Inputs: <slug>/timeline.json (+ cues.json for the sfx check). Without --voice the cut voice is built from the
voice=true chunks (files[vid].audio from ca for d seconds, placed at o, 8 ms fades, 16 kHz mono) and saved as
<slug>/voice_cut.wav. Local faster-whisper (cache only, never downloads) per language -> <slug>/words.json
{"hi": [[word, start, end]], "en": [...]}. Writes <slug>/wordqa.md with
  1. per chunk SAID(lang) next to CAPS
  2. speech >= 0.15 s with no caption         (speech mask: 20 ms RMS > 0.02 x p99 RMS, dilated 30 ms, 10 ms grid)
  3. caption on screen over silence >= 0.35 s (caption mask: [a - 0.03, b + 0.16] per phrase)
  4. sfx cues that sit inside a spoken word and outside every keep window ("sfx over a key word")
The 0.02 x p99 threshold is -34 dB under the loud speech: above room noise, below soft word endings.
Exit code is always 0; the .md is a list to look at, not a verdict.
"""
import argparse, json, pathlib, sys, wave
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import content_dir  # noqa: E402

SR, GRID = 16000, 0.01


def read_wav(p):
    with wave.open(str(p)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        sr, ch = w.getframerate(), w.getnchannels()
    x = x.reshape(-1, ch).mean(1)
    if sr != SR:  # linear resample, enough for an envelope / whisper
        x = np.interp(np.arange(0, len(x) / sr, 1 / SR), np.arange(len(x)) / sr, x).astype(np.float32)
    return x


def write_wav(p, x):
    with wave.open(str(p), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())


def build_voice(root, tl):
    buf = np.zeros(int(round(tl["total"] * SR)), np.float32)
    cache = {}
    for c in tl["chunks"]:
        if not c.get("voice"):
            continue
        f = tl["files"][c["vid"]]["audio"]
        if f not in cache:
            cache[f] = read_wav(root / f)
        s, n = int(round(c["ca"] * SR)), int(round(c["d"] * SR))
        seg = cache[f][s:s + n].copy()
        k = min(int(0.008 * SR), len(seg) // 2)
        if k:
            ramp = np.linspace(0, 1, k); seg[:k] *= ramp; seg[-k:] *= ramp[::-1]
        o = int(round(c["o"] * SR)); seg = seg[:max(0, len(buf) - o)]
        buf[o:o + len(seg)] += seg
    return buf


def mask(intervals, n):
    m = np.zeros(n, bool)
    for a, b in intervals:
        m[max(0, int(round(a / GRID))):max(0, int(round(b / GRID)))] = True
    return m


def speech_mask(x, n):
    k = int(0.02 * SR)
    rms = np.sqrt(np.convolve(x * x, np.ones(k) / k, "same")[::int(GRID * SR)])
    on = rms > 0.02 * np.percentile(rms, 99)
    on = np.convolve(on, np.ones(7), "same") > 0  # +-30 ms dilation
    return np.pad(on, (0, max(0, n - len(on))))[:n]


def runs(m, min_len):
    out, i = [], 0
    while i < len(m):
        if m[i]:
            j = i
            while j < len(m) and m[j]:
                j += 1
            if (j - i) * GRID >= min_len - 1e-9:
                out.append((i * GRID, j * GRID))
            i = j
        else:
            i += 1
    return out


def nearest(words, t):
    w = min(words, key=lambda w: abs((w[1] + w[2]) / 2 - t)) if words else None
    return "'%s' at %.2fs" % (w[0], w[1]) if w else "no word"


def analyse(tl, cues, x, words):
    """Returns the markdown lines and the three counts."""
    n = int(tl["total"] / GRID) + 1
    sp = speech_mask(x, n)
    cm = mask([(p["a"] - 0.03, p["b"] + 0.16) for p in tl["phrases"]], n)
    allw = [w for ws in words.values() for w in ws]
    L = ["## speech with no caption (>= 0.15 s)"]
    A = runs(sp & ~cm, 0.15); B = runs(cm & ~sp, 0.35)
    L += ["- %.2f-%.2f s (%.2f s), nearest word %s" % (a, b, b - a, nearest(allw, (a + b) / 2)) for a, b in A] or ["- none"]
    L += ["", "## caption on screen over silence (>= 0.35 s)"]
    L += ["- %.2f-%.2f s (%.2f s), nearest word %s" % (a, b, b - a, nearest(allw, (a + b) / 2)) for a, b in B] or ["- none"]
    L += ["", "## sfx over a key word"]
    keep = (cues or {}).get("keep", []); C = []
    for s in (cues or {}).get("sfx", []):
        t = s[0]
        if any(a <= t <= b for a, b in keep):
            continue
        for w in allw:
            if w[1] <= t <= w[2]:
                C.append("- sfx over a key word '%s' at %.2f s (%s)" % (w[0], t, s[1])); break
    return L + (C or ["- none"]), (len(A), len(B), len(C))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--voice"); ap.add_argument("--model", default="small")
    ap.add_argument("--langs", default="hi,en")
    a = ap.parse_args()
    root = pathlib.Path(a.folder).expanduser()
    if not root.is_absolute() and not root.exists():
        root = content_dir() / a.folder
    root = root.resolve()
    tl = json.loads((root / "timeline.json").read_text())
    cj = root / "cues.json"; cues = json.loads(cj.read_text()) if cj.exists() else None
    if a.voice:
        x = read_wav(root / a.voice if not pathlib.Path(a.voice).is_absolute() else a.voice)
    else:
        x = build_voice(root, tl); write_wav(root / "voice_cut.wav", x); print("wrote voice_cut.wav")
    words = {}
    try:
        from faster_whisper import WhisperModel
        model = WhisperModel(a.model, device="cpu", compute_type="int8", local_files_only=True)
        wavp = str(root / "voice_cut.wav") if not a.voice else str(root / a.voice)
        for lang in [l for l in a.langs.split(",") if l]:
            segs, _ = model.transcribe(wavp, language=lang, word_timestamps=True, vad_filter=False,
                                       condition_on_previous_text=False)
            words[lang] = [[w.word.strip(), round(w.start, 2), round(w.end, 2)] for s in segs for w in s.words or []]
        (root / "words.json").write_text(json.dumps(words, ensure_ascii=False))
    except Exception as e:
        print("whisper not available (%s: %s): word lists are empty, only the mask checks ran. Nothing is downloaded here." % (type(e).__name__, e))
    md = ["# word QA", ""]
    for lang, ws in words.items():
        md.append("## %s" % lang)
        for c in tl["chunks"]:
            if not c.get("voice"):
                continue
            said = " ".join(w[0] for w in ws if c["o"] - 0.05 <= (w[1] + w[2]) / 2 <= c["o"] + c["d"] + 0.05)
            caps = " | ".join(" ".join(q["w"] for q in p["words"]) for p in tl["phrases"] if c["o"] - 0.01 <= p["a"] < c["o"] + c["d"])
            md += ["%-3s %5.2f-%5.2f  SAID(%s): %s" % (c["id"], c["o"], c["o"] + c["d"], lang, said), "%16sCAPS: %s" % ("", caps)]
        md.append("")
    lines, (na, nb, nc) = analyse(tl, cues, x, words)
    md += lines
    (root / "wordqa.md").write_text("\n".join(md) + "\n")
    print("\n".join(md))
    print("\nsummary: %d uncaptioned speech stretch(es), %d caption(s) over silence, %d sfx over a word -> %s"
          % (na, nb, nc, root / "wordqa.md"))


if __name__ == "__main__":
    main()
