#!/usr/bin/env python3
"""Local Whisper (free) with word timestamps, plus a list of stretches it cannot be trusted on.

  transcribe.py <slug folder> [--model small|large-v3] [--start S --end E] [--lang en] [--allow-download]

Reads <slug>/source.* (the original), cuts the window to a 16 kHz wav, runs faster-whisper and writes
  <slug>/transcript[.<model>].json   {"model", "window", "words": [{"w","s","e","p"}], "segments": [...]}
  <slug>/transcript[.<model>].md     readable, with [!] on shaky words
  <slug>/unclear.json                stretches to ASK THE USER about (never guess them)
Times are SOURCE seconds. First pass is `small`; for the retry on unclear stretches use --model large-v3.
Hinglish: Whisper writes it badly (and may hear English words that were not said). The words that go on
screen come from the user (captions.py); Whisper is only used for WHEN each word was spoken.
Models load from the local Hugging Face cache; nothing is downloaded unless --allow-download is given
(and the user said yes).
"""
import argparse, json, pathlib, subprocess, sys, wave
import numpy as np

HINT = "Hinglish, spelled in Roman script as a young Indian would type it: bhai, matlab, yaar, nahi, kitne, besharam, bezzati."


def cut_wav(src, dst, start, end):
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", "%.3f" % start]
    if end:
        cmd += ["-to", "%.3f" % end]
    cmd += ["-i", str(src), "-vn", "-ac", "1", "-ar", "16000", "-af", "highpass=f=80", str(dst)]
    subprocess.run(cmd, check=True)


def speech_regions(wav, floor_db=-38.0, win=0.03, min_len=0.25, join=0.2):
    """[(start, end)] where the audio is louder than floor_db re. the loudest 30 ms window."""
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        sr = w.getframerate()
    n = int(sr * win)
    rms = np.sqrt(np.convolve(x * x, np.ones(n) / n, "same")[::n // 2] + 1e-12)
    db = 20 * np.log10(rms / rms.max())
    hop = (n // 2) / sr
    on = db > floor_db
    out, cur = [], None
    for i, v in enumerate(on):
        t = i * hop
        if v:
            cur = [t, t] if cur is None else [cur[0], t]
        elif cur and t - cur[1] > join:
            out.append(cur); cur = None
    if cur:
        out.append(cur)
    return [(a, b) for a, b in out if b - a >= min_len]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--model", default="small")
    ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float, default=0.0)
    ap.add_argument("--lang", default="en"); ap.add_argument("--allow-download", action="store_true")
    a = ap.parse_args()
    folder = pathlib.Path(a.folder).expanduser().resolve()
    src = next(iter(sorted(folder.glob("source.*"))), None)
    if not src:
        sys.exit("no source.* in %s: run probe.py first" % folder)
    wav = folder / "audio_window.wav"
    cut_wav(src, wav, a.start, a.end or None)
    from faster_whisper import WhisperModel
    try:
        model = WhisperModel(a.model, device="cpu", compute_type="int8", local_files_only=not a.allow_download)
    except Exception as e:
        sys.exit("model %r is not in the local cache (%s). Downloads need the user's yes; then rerun with --allow-download." % (a.model, type(e).__name__))
    segs, info = model.transcribe(str(wav), language=a.lang, word_timestamps=True, initial_prompt=HINT,
                                  beam_size=5, vad_filter=False, condition_on_previous_text=False)
    words, segments = [], []
    for s in segs:
        segments.append({"s": round(s.start + a.start, 2), "e": round(s.end + a.start, 2), "text": s.text.strip(),
                         "logprob": round(s.avg_logprob, 2), "no_speech": round(s.no_speech_prob, 2)})
        for w in s.words or []:
            words.append({"w": w.word.strip(), "s": round(w.start + a.start, 2), "e": round(w.end + a.start, 2), "p": round(w.probability, 2)})
    tag = "" if a.model == "small" else "." + a.model
    window = [a.start, a.end or None]
    json.dump({"model": a.model, "window": window, "lang": a.lang, "words": words, "segments": segments},
              open(folder / ("transcript%s.json" % tag), "w"), indent=1, ensure_ascii=False)

    # stretches to ask about: shaky words, and speech the model produced no word for
    unclear = []
    for i, w in enumerate(words):
        if w["p"] < 0.5:
            unclear.append({"s": w["s"], "e": w["e"], "why": "low confidence %.2f" % w["p"], "heard": w["w"]})
    for (rs, re_) in speech_regions(wav):
        rs, re_ = rs + a.start, re_ + a.start
        t = rs  # walk the region; every stretch no word covers and longer than 0.45 s is a question
        for w in sorted(words, key=lambda w: w["s"]):
            if w["e"] <= t:
                continue
            if w["s"] >= re_:
                break
            if w["s"] - t > 0.45:
                unclear.append({"s": round(t, 2), "e": round(w["s"], 2), "why": "speech with no word heard", "heard": ""})
            t = max(t, w["e"])
        if re_ - t > 0.45:
            unclear.append({"s": round(t, 2), "e": round(re_, 2), "why": "speech with no word heard", "heard": ""})
    unclear.sort(key=lambda u: u["s"])
    merged = []
    for u in unclear:  # merge touching stretches into one question
        if merged and u["s"] - merged[-1]["e"] < 0.35 and u["e"] - merged[-1]["s"] < 4.0:
            m = merged[-1]; m["e"] = max(m["e"], u["e"]); m["heard"] = (m["heard"] + " " + u["heard"]).strip()
            m["why"] = m["why"] if u["why"] in m["why"] else m["why"] + "; " + u["why"]
        else:
            merged.append(dict(u))
    json.dump(merged, open(folder / "unclear.json", "w"), indent=1, ensure_ascii=False)

    lines = ["# transcript (%s, window %s)" % (a.model, window), ""]
    for s in segments:
        lines.append("[%6.2f-%6.2f] %s" % (s["s"], s["e"], " ".join(("%s[!]" % w["w"]) if w["p"] < 0.5 else w["w"]
                                                                   for w in words if s["s"] - 0.01 <= w["s"] <= s["e"] + 0.01)))
    (folder / ("transcript%s.md" % tag)).write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print("\n%d words, %d unclear stretch(es) -> %s" % (len(words), len(merged), folder / "unclear.json"))
    for i, u in enumerate(merged, 1):
        print("  ?%d  %.2f-%.2f s  %s  heard: %r" % (i, u["s"], u["e"], u["why"], u["heard"]))
    if merged:
        print("ASK the user for the words in each ? stretch; do not build captions over them until answered.")


if __name__ == "__main__":
    main()
