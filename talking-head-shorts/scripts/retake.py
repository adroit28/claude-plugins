#!/usr/bin/env python3
"""Retake hint: is the opening line of a take repeated later in the same take? (a hint, never an automatic cut)

  retake.py <slug folder> [--model small] [--lang hi|en]

Runs local faster-whisper (cache only, never downloads) on <slug>/audio16/<name>.wav, takes the first 5 words
as a phrase and slides a window of the same length over the rest of the words (difflib ratio >= 0.75). A
match means the speaker started again: the real take may begin there. Prints one RETAKE? line per clip and
writes <slug>/retakes.json {"name": {"phrase", "repeat_at", "ratio"}}. Ask the user before cutting anything.
"""
import argparse, difflib, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import content_dir  # noqa: E402


def norm(w):
    return re.sub(r"[^\w]", "", w.lower())


def find_repeat(words, n=5, thr=0.75, min_gap=1.0):
    """words = [(text, start, end)]. Returns (phrase, time, ratio) of the best later match of the first n words, or None."""
    if len(words) < 2 * n:
        n = max(3, len(words) // 2)
    if len(words) < 2 * n:
        return None
    head = " ".join(norm(w[0]) for w in words[:n])
    best = None
    for i in range(n, len(words) - n + 1):
        if words[i][1] - words[0][1] < min_gap:
            continue
        r = difflib.SequenceMatcher(None, head, " ".join(norm(w[0]) for w in words[i:i + n])).ratio()
        if r >= thr and (best is None or r > best[2]):
            best = (" ".join(w[0] for w in words[:n]), words[i][1], r)
    return best


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--model", default="small"); ap.add_argument("--lang", default="hi")
    a = ap.parse_args()
    root = pathlib.Path(a.folder).expanduser()
    if not root.is_absolute() and not root.exists():
        root = content_dir() / a.folder
    root = root.resolve()
    wavs = sorted((root / "audio16").glob("*.wav"))
    if not wavs:
        sys.exit("no audio16/*.wav in %s (run normalize.py first)" % root)
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(a.model, device="cpu", compute_type="int8", local_files_only=True)
    except Exception as e:
        sys.exit("whisper model %r is not in the local cache (%s). Nothing is downloaded here; ask the user before fetching it." % (a.model, type(e).__name__))
    found = {}
    for wav in wavs:
        segs, _ = model.transcribe(str(wav), language=a.lang, word_timestamps=True, vad_filter=False,
                                   condition_on_previous_text=False)
        words = [(w.word.strip(), w.start, w.end) for s in segs for w in s.words or []]
        hit = find_repeat(words)
        if hit:
            ph, t, r = hit
            found[wav.stem] = {"phrase": ph, "repeat_at": round(t, 2), "ratio": round(r, 2)}
            print("RETAKE? %s: opening '%s' at 0.0s is repeated at %.1fs -> the real take may start there; ask the user" % (wav.stem, ph, t))
        else:
            print("%s: no repeated opening (%d words)" % (wav.stem, len(words)))
    (root / "retakes.json").write_text(json.dumps(found, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
