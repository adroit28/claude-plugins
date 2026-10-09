#!/usr/bin/env python3
"""The mechanical part of the beat map (run by the beat-mapper subagent): one compact table, no images.

  beatmap.py <slug folder> [--text captions.txt] [--start S --end E]

Reads captions.json (confirmed phrases with times) when it exists, else transcript.json, plus the audio
and probe.json. Writes <slug>/beatmap.json and prints a table:
  sentence/phrase rows  start-end, words, the pause before it, energy (dB re. loudest), tags
  tags: NUM (digits or number words), NAME (capitalised word), PEAK (loudest 20% of phrases = emphasis),
        LAUGH? (a loud short burst with no words, or "haha"), LONGPAUSE (>0.6 s before),
  dead air: silent stretches > 0.8 s inside the window, plus leading/trailing silence
  blinks: black frames from probe.json that fall in the window
"""
import argparse, json, pathlib, re, subprocess, sys, wave
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from transcribe import cut_wav, speech_regions

NUMW = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "hundred", "thousand", "million", "billion", "lakh", "crore",
        "teen", "char", "paanch", "chhe", "saat", "aath", "nau", "das", "sau", "hazaar", "first", "second", "third"}


def rms_db(x, sr, a, b):
    seg = x[int(a * sr):int(b * sr)]
    return float(20 * np.log10(np.sqrt(np.mean(seg ** 2) + 1e-12))) if len(seg) else -90.0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--start", type=float); ap.add_argument("--end", type=float)
    a = ap.parse_args()
    folder = pathlib.Path(a.folder).expanduser().resolve()
    tr = json.loads((folder / "transcript.json").read_text())
    probe = json.loads((folder / "probe.json").read_text())
    start = a.start if a.start is not None else (tr["window"][0] or 0.0)
    end = a.end or tr["window"][1] or probe["duration"]
    src = next(iter(sorted(folder.glob("source.*"))))
    wav = folder / "audio_window.wav"
    cut_wav(src, wav, start, end)
    with wave.open(str(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        sr = w.getframerate()
    peak_db = max(rms_db(x, sr, t, t + 0.05) for t in np.arange(0, len(x) / sr - 0.05, 0.05))

    rows = []
    cj = folder / "captions.json"
    if cj.exists():
        for p in json.loads(cj.read_text())["phrases"]:
            rows.append({"s": p[0][1], "e": p[-1][2], "text": " ".join(w[0] for w in p), "src": "confirmed"})
    else:  # Whisper words grouped by pauses > 0.35 s
        cur = []
        for w in tr["words"]:
            if cur and w["s"] - cur[-1]["e"] > 0.35:
                rows.append({"s": cur[0]["s"], "e": cur[-1]["e"], "text": " ".join(c["w"] for c in cur), "src": "whisper"}); cur = []
            cur.append(w)
        if cur:
            rows.append({"s": cur[0]["s"], "e": cur[-1]["e"], "text": " ".join(c["w"] for c in cur), "src": "whisper"})
    for r in rows:
        r["db"] = round(rms_db(x, sr, r["s"] - start, r["e"] - start) - peak_db, 1)
    thr = float(np.percentile([r["db"] for r in rows], 80)) if rows else 0.0
    prev_e = start
    for r in rows:
        r["pause_before"] = round(max(0, r["s"] - prev_e), 2)
        prev_e = r["e"]
        toks = re.findall(r"[\w']+", r["text"])
        tags = []
        if any(t.isdigit() or t.lower() in NUMW for t in toks): tags.append("NUM")
        if any(t[0].isupper() and i > 0 and not t.isupper() for i, t in enumerate(toks)): tags.append("NAME")
        if r["db"] >= thr and len(rows) >= 5: tags.append("PEAK")
        if r["pause_before"] > 0.6: tags.append("LONGPAUSE")
        if re.search(r"ha(ha)+|hehe", r["text"].lower()): tags.append("LAUGH?")
        r["tags"] = tags
    # dead air and loud bursts with no words
    covered = [(r["s"], r["e"]) for r in rows]
    dead = []
    t = start
    for s, e in sorted(covered):
        if s - t > 0.8:
            dead.append([round(t, 2), round(s, 2)])
        t = max(t, e)
    if end - t > 0.8:
        dead.append([round(t, 2), round(end, 2)])
    bursts = []
    for s, e in speech_regions(wav, floor_db=-9, min_len=0.12, join=0.05):
        s, e = s + start, e + start
        over = sum(max(0, min(e, c[1]) - max(s, c[0])) for c in covered)
        if over < 0.5 * (e - s):
            bursts.append([round(s, 2), round(e, 2)])
    blinks = [b for b in probe.get("blink_spans", []) if b[1] >= start and b[0] <= end]
    out = {"window": [start, end], "rows": rows, "dead_air": dead, "loud_unworded": bursts, "blinks": blinks}
    json.dump(out, open(folder / "beatmap.json", "w"), indent=1, ensure_ascii=False)

    print("beat map %.2f-%.2f s (%d phrases, peak = loudest 20%%)" % (start, end, len(rows)))
    print("%-3s %-11s %-6s %-6s %-14s %s" % ("#", "time", "pause", "dB", "tags", "words"))
    for i, r in enumerate(rows, 1):
        print("%-3d %5.2f-%5.2f %-6.2f %-6.1f %-14s %s" % (i, r["s"], r["e"], r["pause_before"], r["db"], ",".join(r["tags"]), r["text"]))
    print("dead air (>0.8 s no words):", dead or "none")
    print("loud bursts with no words (laugh / reaction?):", bursts or "none")
    print("black blink frames in window:", blinks or "none")


if __name__ == "__main__":
    main()
