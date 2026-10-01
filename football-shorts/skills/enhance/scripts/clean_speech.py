#!/usr/bin/env python3
"""Clean speech: cut a section out of a video, split the voice from music/crowd with Demucs,
loudness-match it to the original cut, write a wav and say whether it is worth using.

  clean_speech.py --install [shorts_dir]                      one-time: venv + demucs + model (ASK THE USER FIRST)
  clean_speech.py <video> --ss 12.4 --t 6.2 --out build/clean/quote.wav [--strength off|mid|strong] [--keep-work]

Demucs alone leaves music tones and sub-bass in the voice stem, so a second stage subtracts the steady
(per-frequency, slowly changing) component and cuts below 110 Hz: --strength strong (default) or mid
(gentler, fewer artifacts), off = Demucs only.
Runs only on the seconds you give (cut first, ~10 s total is a minute of CPU), never the whole file.
Output: 48 kHz stereo wav, same length as the cut, gain-matched to the original's loudness with a
limiter. Plays in a spec as a `file` hit on a muted clip (see SKILL.md). The last line is
`verdict: USE CLEAN` or `verdict: KEEP ORIGINAL (reason)`; keep the original when it says so.
Exit 0 = use clean, 1 = keep original, 2 = not installed (nothing is downloaded unless --install was passed).
"""
import argparse, os, re, subprocess, sys, tempfile

def shorts_dir(a=None):
    return os.path.abspath(a or os.environ.get("FOOTBALL_SHORTS_DIR") or os.path.join(os.environ.get("CLAUDE_PROJECT_DIR", "."), "shorts"))

def venv_py(d): return os.path.join(d, ".venv-demucs", "bin", "python")

def install(d):
    py = venv_py(d)
    if not os.path.exists(py):
        # torch lags the newest Python: newest of 3.13/3.12/3.11 installed
        for v in ("3.13", "3.12", "3.11"):
            for p in ("python" + v, "/Library/Frameworks/Python.framework/Versions/%s/bin/python%s" % (v, v)):
                if subprocess.call(["sh", "-c", "command -v %s >/dev/null" % p]) == 0 or os.path.exists(p):
                    base = p; break
            else: continue
            break
        else: sys.exit("need python3.11-3.13 (brew install python@3.12)")
        subprocess.check_call([base, "-m", "venv", os.path.join(d, ".venv-demucs")])
    # -i pypi.org: some machines point pip at a private index that rejects anonymous installs
    subprocess.check_call([os.path.join(d, ".venv-demucs", "bin", "pip"), "install", "-q", "-i", "https://pypi.org/simple", "demucs", "soundfile"])
    subprocess.check_call([py, "-c", "from demucs.pretrained import get_model; get_model('htdemucs'); print('ok   demucs + htdemucs model ready')"])
    print("PYDM=" + py)

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)

def lufs(path):
    r = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", "ebur128", "-f", "null", "-"])
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None

def separate(src, dst):
    import numpy as np, soundfile as sf, torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    m = get_model("htdemucs"); m.eval()
    x, sr = sf.read(src, dtype="float32"); x = x.T
    ref = x.mean(0); sd = ref.std() + 1e-8
    w = torch.from_numpy((x - ref.mean()) / sd)[None]
    with torch.no_grad(): out = apply_model(m, w, split=True, overlap=0.25, device="cpu")[0]
    v = out[m.sources.index("vocals")].numpy() * sd + ref.mean()
    sf.write(dst, (v / max(1.0, float(abs(v).max()) / 0.98)).T, sr)   # no clipping in the raw stem

def suppress(path, strength):
    """Soft mask from the per-bin steady (30th-percentile over ~0.8 s) spectrum: music tones and hum stay,
    speech moves too fast to be in it. Smoothed over time and frequency to limit musical-noise artifacts."""
    import numpy as np, soundfile as sf, torch
    alpha, beta = {"mid": (1.2, 0.25), "strong": (2.0, 0.10)}[strength]
    N, H = 2048, 512; x, sr = sf.read(path, dtype="float32"); outc = []
    for c in range(x.shape[1]):
        w = torch.hann_window(N); X = torch.stft(torch.from_numpy(np.ascontiguousarray(x[:, c])), N, H, window=w, return_complex=True)
        A = X.abs(); k = int(0.8 * sr / H) | 1
        M = torch.nn.functional.pad(A[None], (k // 2, k // 2), mode="replicate")[0].unfold(1, k, 1).quantile(0.3, dim=-1)
        m = (1 - alpha * M / (A + 1e-9)).clamp(min=beta)
        m = torch.nn.functional.avg_pool1d(m[None], 3, 1, 1)[0]; m = torch.nn.functional.avg_pool1d(m.T[None], 3, 1, 1)[0].T
        outc.append(torch.istft(X * m, N, H, window=w, length=x.shape[0]).numpy())
    sf.write(path, np.stack(outc, 1), sr)

def judge(orig, clean):
    """Numbers, not ears (clean = the gain-matched output): mid band intact (not thin), floor lower, spectral holes (watery) not blown up."""
    import numpy as np, soundfile as sf
    from numpy.lib.stride_tricks import sliding_window_view as win
    def load(p):
        x, sr = sf.read(p, dtype="float32"); return x.mean(1), sr
    def spec(x, n=1024, h=256): return np.abs(np.fft.rfft(win(x, n)[::h] * np.hanning(n), axis=1)).T + 1e-9
    (o, sr), (c, sc) = load(orig), load(clean); f = np.fft.rfftfreq(1024, 1 / sr); fc = np.fft.rfftfreq(1024, 1 / sc)
    So, Sc = spec(o), spec(c)
    mid, midc = (f >= 300) & (f < 3000), (fc >= 300) & (fc < 3000)
    d_mid = 20 * np.log10(np.sqrt((Sc[midc] ** 2).mean()) / np.sqrt((So[mid] ** 2).mean()))
    def gap(x):
        db = 20 * np.log10(np.sqrt((win(x, 2048)[::512] ** 2).mean(1)) + 1e-9); return np.percentile(db, 90) - np.percentile(db, 10)
    def holes(S, f):
        k = (f >= 1000) & (f < 8000); d = 20 * np.log10(S[k] / S.max(0, keepdims=True)); act = S.max(0) > np.percentile(S.max(0), 40)
        return 100 * (d[:, act] < -50).mean()
    g0, g1, h0, h1 = gap(o), gap(c), holes(So, f), holes(Sc, fc)
    print("  voice body 300-3000 Hz: %+.1f dB | speech-to-floor gap: %.1f -> %.1f dB | spectral holes 1-8k: %.0f%% -> %.0f%%" % (d_mid, g0, g1, h0, h1))
    if d_mid < -1.5: return "KEEP ORIGINAL (voice sounds thin: body %+.1f dB)" % d_mid
    if h1 - h0 > 40: return "KEEP ORIGINAL (watery artifacts: holes +%.0f points; try --strength mid)" % (h1 - h0)
    if g1 - g0 < 1.5: return "KEEP ORIGINAL (background barely reduced: gap +%.1f dB)" % (g1 - g0)
    return "USE CLEAN"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?"); ap.add_argument("--install", nargs="?", const="", metavar="SHORTS_DIR")
    ap.add_argument("--ss", type=float); ap.add_argument("--t", type=float); ap.add_argument("--out")
    ap.add_argument("--strength", choices=["off", "mid", "strong"], default="strong"); ap.add_argument("--shorts-dir"); ap.add_argument("--keep-work", action="store_true", help="keep <out>.orig.wav / .vocals.wav for A/B listening")
    ap.add_argument("--_inner", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()
    d = shorts_dir(a.install or a.shorts_dir)
    if a.install is not None: return install(d)
    if not (a.video and a.ss is not None and a.t and a.out): ap.error("video, --ss, --t and --out are required")
    try:
        import demucs, soundfile  # noqa
    except ImportError:
        py = venv_py(d)
        if os.path.exists(py) and not a._inner: os.execv(py, [py, os.path.abspath(__file__)] + sys.argv[1:] + ["--_inner"])
        print("Demucs is not installed. It needs the user's explicit yes (pip install + ~80 MB model download), then:\n  python3 %s --install %s" % (os.path.abspath(__file__), d))
        return 2
    out = os.path.abspath(a.out); os.makedirs(os.path.dirname(out), exist_ok=True); base = out[:-4]
    orig, voc = base + ".orig.wav", base + ".vocals.wav"
    r = run(["ffmpeg", "-v", "error", "-y", "-ss", str(a.ss), "-t", str(a.t), "-i", a.video, "-vn", "-ac", "2", "-ar", "44100", orig])
    if r.returncode or not os.path.getsize(orig) > 1000: sys.exit("no audio in %s at %s+%s: %s" % (a.video, a.ss, a.t, r.stderr.strip()))
    print("cut %.2f s, separating (CPU)..." % a.t); separate(orig, voc)
    if a.strength != "off": suppress(voc, a.strength)
    lo, lv = lufs(orig), lufs(voc)   # gain from the stem as written, after the mask
    gain = (lo - lv) if lo is not None and lv is not None else 0.0
    r = run(["ffmpeg", "-v", "error", "-y", "-i", voc, "-af", "%svolume=%.2fdB,alimiter=limit=0.89" % ("" if a.strength == "off" else "highpass=f=110:poles=2,", gain), "-ar", "48000", out])
    if r.returncode: sys.exit(r.stderr)
    print("loudness: original %.1f LUFS, vocals %.1f -> gain %+.1f dB -> %s" % (lo, lv, gain, os.path.relpath(out)))
    v = judge(orig, out); print("verdict: " + v)
    if not a.keep_work:
        for p in (orig, voc): os.remove(p)
    return 0 if v == "USE CLEAN" else 1

if __name__ == "__main__":
    sys.exit(main())
