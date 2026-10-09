#!/usr/bin/env python3
"""Audio mix for the multi-clip flow (docs/multi-clip.md): voice cut from cues.json, sfx policed against speech, ducked music, loudnorm.

  mix_multi.py <slug folder> [--out build_v<N>.mp4] [--raw anim/out/raw_vN.mp4] [--denoise] [--no-music] [--voice-only] [--version N] [--no-ask]

Voice: each voiced chunk is cut from cues.files[chunk.vid].audio at chunk.ca for chunk.d s, placed at chunk.o, 8 ms fades;
chain highpass 80 + 3.2 kHz presence + light compressor (--denoise adds afftdn first); level = speech RMS ~ -15 dBFS.
SFX policy: a cue may not sound over speech unless it starts inside a cues.keep window: shifted <= 0.12 s into a gap, else trimmed
(90 ms fade) if >= 0.25 s clean time survives, else dropped. Per-cue maxlen is cue[3]. Table -> stdout and <slug>/sfx_resolved.json.
Music: cues.music.bed (path rel. to slug, default sfx/music.wav made by synth.py), gain keys, ducked 14 dB under the voice.
Then tanh limiter, two-pass loudnorm I=-14 TP=-1.5 LRA=9. With a raw Remotion render the audio is muxed into build_v<N>.mp4
(video copied, AAC 192k); never overwrites. Without one, <slug>/mix_v<N>.wav is written instead.
"""
import argparse, json, pathlib, re, subprocess, sys, tempfile, wave
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import synth

SR = 48000
CHAIN = "highpass=f=80,equalizer=f=3200:width_type=q:w=0.9:g=2.5,acompressor=threshold=-21dB:ratio=2:attack=6:release=90:makeup=2"
HOP = SR // 100


def read_wav(p):
    w = wave.open(str(p)); n, ch, sw = w.getnframes(), w.getnchannels(), w.getsampwidth()
    assert w.getframerate() == SR, (p, w.getframerate())
    x = np.frombuffer(w.readframes(n), dtype={2: "<i2", 4: "<i4"}[sw]).astype(np.float64) / (2 ** (8 * sw - 1))
    return x.reshape(-1, ch).mean(1)


def write_wav(p, x):
    w = wave.open(str(p), "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    y = (np.clip(x, -1, 1) * 32767).astype("<i2"); w.writeframes(np.repeat(y[:, None], 2, 1).tobytes()); w.close()


def frames_rms(x, n=None):
    """RMS per 10 ms frame."""
    n = len(x) // HOP if n is None else n
    return np.sqrt(np.mean(x[:n * HOP].reshape(n, HOP) ** 2, axis=1))


def follower(d, att=0.012, rel=0.28):
    """Attack/release follower, run at 1 kHz (48x fewer steps than per-sample) and interpolated back."""
    k = SR // 1000; m = len(d) // k
    dd = d[:m * k].reshape(m, k).max(1); a, r = np.exp(-1 / (att * 1000)), np.exp(-1 / (rel * 1000))
    sm = np.zeros(m); s = 0.0
    for i in range(m):
        s = a * s + (1 - a) * dd[i] if dd[i] > s else r * s + (1 - r) * dd[i]
        sm[i] = s
    return np.interp(np.arange(len(d)) / k, (np.arange(m) + 0.5), sm)


def loudnorm(raw, out):
    m = subprocess.run(["ffmpeg", "-v", "info", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", m, re.S).group(0))
    af = ("loudnorm=I=-14:TP=-1.5:LRA=9:measured_I=%s:measured_TP=%s:measured_LRA=%s:measured_thresh=%s:offset=%s:linear=true"
          % (j["input_i"], j["input_tp"], j["input_lra"], j["input_thresh"], j["target_offset"]))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", af, "-ar", str(SR), "-c:a", "pcm_s16le", out], check=True)
    return j["input_i"], j["input_tp"]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"); ap.add_argument("--out"); ap.add_argument("--raw"); ap.add_argument("--denoise", action="store_true")
    ap.add_argument("--no-music", action="store_true"); ap.add_argument("--voice-only", action="store_true")
    ap.add_argument("--version", type=int); ap.add_argument("--no-ask", action="store_true")
    a = ap.parse_args()
    slug = pathlib.Path(a.slug).expanduser().resolve(); cues = json.loads((slug / "cues.json").read_text())
    if "keep" not in cues and not a.no_ask:
        print("no KEEP windows: every sfx obeys the no-sfx-over-speech rule; if the middle feels quiet ask the user which scenes may carry sound")
    keep = cues.get("keep", [])
    total = cues["total"]; N = int(SR * (total + 0.5)); tmp = pathlib.Path(tempfile.mkdtemp(prefix="mixmulti-"))

    # ---- voice: cut every voiced chunk from its file
    src = {}
    for c in cues["chunks"]:
        if c["voice"] and c["vid"] not in src:
            f = tmp / (c["vid"] + ".wav")
            af = ("afftdn=nf=-30," if a.denoise else "") + CHAIN
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(slug / cues["files"][c["vid"]]["audio"]), "-vn", "-ac", "1", "-ar", str(SR), "-af", af, "-c:a", "pcm_s16le", str(f)], check=True)
            src[c["vid"]] = read_wav(f)
    voice = np.zeros(N)
    for c in cues["chunks"]:
        if not c["voice"]: continue
        seg = src[c["vid"]][int(round(c["ca"] * SR)):int(round((c["ca"] + c["d"]) * SR))].copy()
        f = int(0.008 * SR); seg[:f] *= np.linspace(0, 1, f); seg[-f:] *= np.linspace(1, 0, f)
        i = int(round(c["o"] * SR)); voice[i:i + len(seg)] += seg[:max(0, N - i)]
    speech = voice[np.abs(voice) > 0.01]
    voice *= 0.18 / (np.sqrt(np.mean(speech ** 2)) + 1e-9)           # speech RMS ~ -15 dBFS
    if a.voice_only:
        write_wav(slug / "voice_cut.wav", voice[:int(total * SR)]); print("voice ->", slug / "voice_cut.wav"); return

    # ---- duck curve and speech mask (10 ms frames, 20 ms rms > 0.012, dilated 30 ms each side)
    win = int(0.02 * SR); e = np.sqrt(np.convolve(voice ** 2, np.ones(win) / win, "same"))
    duck = 10 ** (-14 * np.clip(follower(np.clip(e / 0.04, 0, 1)) * 1.4, 0, 1) / 20)
    nfr = N // HOP; r10 = frames_rms(voice, nfr); r10 = np.maximum(r10, np.r_[r10[1:], 0])
    mask = np.convolve((r10 > 0.012).astype(float), np.ones(7), "same") > 0

    def audible(x, g): r = frames_rms(x) * g; return r > 0.03 * max(r.max(), 1e-9)
    def overlap_ms(am, at):
        k0 = int(round(at * 100)); m = am[:max(0, min(len(am), nfr - k0))]
        return int(np.sum(m & mask[k0:k0 + len(m)])) * 10

    # ---- sfx resolved against speech
    paths = synth.ensure([c[1] for c in cues["sfx"]], slug / "sfx"); sfx = np.zeros(N); resolved = []
    print("%6s %-10s %6s %10s  result" % ("t", "cue", "aud s", "overlap ms"))
    for cue in cues["sfx"]:
        at, name, g = cue[0], cue[1], cue[2]; trim = cue[3] if len(cue) > 3 else None
        x = read_wav(paths[name]); fo = int(0.09 * SR)
        if trim: x = x[:int(trim * SR)].copy(); x[-fo:] *= np.linspace(1, 0, fo)
        am = audible(x, g); last = np.nonzero(am)[0]; alen = (last[-1] + 1) / 100 if len(last) else 0
        ov0 = overlap_ms(am, at); best = None; forced = any(p <= at <= q for p, q in keep)
        if ov0 == 0 or forced: best = 0.0
        else:
            for sh in sorted([k / 100 for k in range(-12, 13)], key=abs):
                if at + sh >= 0 and overlap_ms(am, at + sh) == 0: best = sh; break
        trimmed = None
        if best is None:                                              # clean start, tail runs into speech: trim + fade if >= 0.25 s survives
            k0 = int(round(at * 100)); L = min(len(am), nfr - k0); hit = np.nonzero(am[:L] & mask[k0:k0 + L])[0]
            if len(hit) and hit[0] >= 30 and not (am[:int(hit[0])] & mask[k0:k0 + int(hit[0])]).any():
                trimmed = (hit[0] - 2) / 100; best = 0.0; x = x[:int(trimmed * SR)].copy(); x[-fo:] *= np.linspace(1, 0, fo)
        res = ("kept (allowed over speech)" if forced and ov0 else f"trimmed to {trimmed:.2f}s" if trimmed else "kept" if best == 0.0
               else f"shifted {best:+.2f}s" if best is not None else "DROPPED (over speech)")
        print("%6.2f %-10s %6.2f %10d  %s" % (at, name, alen, ov0, res))
        resolved.append(dict(t=at, name=name, vol=g, aud=round(alen, 2), overlap_ms=ov0, result=res, final_t=None if best is None else round(at + best, 3)))
        if best is None: continue
        i = int((at + best) * SR)
        if i < N: x = x[:N - i]; sfx[i:i + len(x)] += x * g * 0.5
    (slug / "sfx_resolved.json").write_text(json.dumps(resolved, indent=1))
    R = [r["result"] for r in resolved]
    print("kept/shifted/trimmed/dropped:", sum(s.startswith("kept") for s in R), sum(s.startswith("shifted") for s in R),
          sum(s.startswith("trimmed") for s in R), sum(s.startswith("DROP") for s in R))

    # ---- music: gain keys, ducked under the voice
    music = np.zeros(N); mus_cfg = cues.get("music") or {}
    if not a.no_music and mus_cfg.get("keys"):
        bed = mus_cfg.get("bed")
        bp = slug / bed if bed else synth.ensure(["music"], slug / "sfx", music_seconds=total + 1)["music"]
        mus = read_wav(bp)
        if len(mus) < N: mus = np.tile(mus, N // len(mus) + 1)         # loop a short bed
        mus = mus[:N]; kt, kg = zip(*mus_cfg["keys"]); gain = np.interp(np.arange(N) / SR, kt, kg)
        gain = np.convolve(gain, np.ones(int(0.01 * SR)) / int(0.01 * SR), "same"); music = mus * gain * duck * 0.55

    mix = voice + music + sfx; mix = np.tanh(mix * 0.5) / np.tanh(0.5); mix[int(total * SR):] = 0
    raw_wav = tmp / "mix_raw.wav"; write_wav(raw_wav, mix[:int(total * SR)])

    # ---- version, raw render, output
    out_dir = slug / "anim/out"; raws = sorted(out_dir.glob("raw_v*.mp4"), key=lambda p: int(re.search(r"(\d+)", p.stem).group(1))) if out_dir.is_dir() else []
    raw = pathlib.Path(a.raw) if a.raw else (raws[-1] if raws else None)
    if raw and not raw.is_absolute(): raw = slug / raw
    v = a.version or (int(re.search(r"raw_v(\d+)", raw.name).group(1)) if raw and re.search(r"raw_v(\d+)", raw.name) else 1)
    wav_out = tmp / "mix.wav"; i_, tp_ = loudnorm(str(raw_wav), str(wav_out)); print("pre-norm I", i_, "TP", tp_)
    if not raw:
        dst = slug / ("mix_v%d.wav" % v); subprocess.run(["cp", str(wav_out), str(dst)], check=True); print("no raw render found; audio ->", dst); return
    dst = pathlib.Path(a.out) if a.out else slug / ("build_v%d.mp4" % v)
    if not dst.is_absolute(): dst = slug / dst
    if dst.exists(): sys.exit("%s exists: versions are never overwritten" % dst)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw), "-i", str(wav_out), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest", str(dst)], check=True)
    print("mix ->", dst)


if __name__ == "__main__":
    main()
