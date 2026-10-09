#!/usr/bin/env python3
"""Synthesize the extra sound-effect library and a music bed (numpy only, no downloads, no licences, deterministic).

  synth.py <out dir> [--only siren,boom] [--list] [--force] [--music] [--music-bed-seconds 60]

Writes <name>.wav (48 kHz mono) into the folder. Names that the older sfx.py library already owns
(ring click riser bass horn whoosh ding buzz stamp waves pop tick coin sparkle) are skipped unless --force.
--music also writes music.wav (108 BPM A-minor groove) of the given length. mix_multi.py calls ensure() for the cues it finds.
Own copy inside talking-head-shorts (no dependency on the other video plugins). Ported from the Westside reel.
"""
import argparse, pathlib, sys, wave, zlib
import numpy as np
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

SR = 48000
rng = np.random.default_rng(7)


def T(d): return np.arange(int(SR * d)) / SR
def silence(d): return np.zeros(int(SR * d))
def noise(d): return rng.uniform(-1, 1, int(SR * d))
def saw(f): return 2 * ((np.cumsum(f) / SR) % 1) - 1
def sine(f): return np.sin(2 * np.pi * np.cumsum(f) / SR)


def save(path, x, peak=0.9):
    x = np.asarray(x, float); m = np.max(np.abs(x)) or 1; x = x / m * peak
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))


def fade(x, a=0.005, b=0.02):
    x = x.copy(); na, nb = int(SR * a), int(SR * b)
    if na: x[:na] *= np.linspace(0, 1, na)
    if nb: x[-nb:] *= np.linspace(1, 0, nb)
    return x


def bell(freq, d, dec):
    t = T(d); return np.exp(-dec * t) * (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.76 * t))
def click(d, g): return fft_filter(noise(d), 1500, 8000) * np.exp(-g * T(d))
def honk(f, d): return fade(np.sign(np.sin(2 * np.pi * f * T(d))) * 0.4 + np.sign(np.sin(2 * np.pi * f * 1.26 * T(d))) * 0.35, 0.004, 0.02)
def wah(f0, d, wob=0):
    t = T(d); f = f0 * (1 + wob * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / d * 3, 0, 1))
    x = fft_filter(saw(f), None, 1100)
    return fade(x * (0.5 + 0.5 * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 0.5), 0.03, 0.05)


# name -> (one-line description, builder). Each builder re-seeds, so a name always renders identically.
def _siren():
    t = T(1.1); f = 760 + 260 * np.sin(2 * np.pi * 2.6 * t)
    return fade(0.6 * (sine(f) + 0.35 * sine(2 * f)) * (1 - np.exp(-t * 40)) * np.clip(1.15 - t, 0, 1), 0.01, 0.15)
def _boom():
    t = T(1.0); return 0.95 * np.exp(-4.5 * t) * np.sin(2 * np.pi * (60 - 22 * t) * t) + 0.5 * fft_filter(noise(1.0), None, 900) * np.exp(-9 * t)
def _swoosh():
    t = T(0.7); return fade(fft_filter(noise(0.7), 400, 7000) * np.sin(np.pi * t / 0.7) ** 2)
def _revwhoosh():
    t = T(1.4); return fade(fft_filter(noise(1.4), 300, 9000) * (t / 1.4) ** 2.2, 0.01, 0.01)
def _riser2():
    t = T(2.6); return fade(0.5 * saw(120 * 2 ** (t * 1.6)) * (t / 2.6) ** 1.5 + 0.4 * fft_filter(noise(2.6), 800, 9000) * (t / 2.6) ** 2, 0.02, 0.05)
def _shutter(): return np.concatenate([click(0.04, 90), silence(0.05), 0.7 * click(0.07, 60)])
def _notify(): return np.concatenate([bell(1319, 0.18, 14), bell(1760, 0.5, 7)])
def _beep(): return fade(0.6 * np.sin(2 * np.pi * 1000 * T(0.07)), 0.003, 0.01)
def _kaching(): return np.concatenate([click(0.03, 80) * 0.8, silence(0.04), bell(2093, 0.9, 5) + 0.6 * bell(3136, 0.9, 5)])
def _vanish():
    t = T(0.6); return fade(fft_filter(noise(0.6), 200, 5000) * np.exp(-6 * t) * 0.8 + 0.5 * sine(900 * np.exp(-5 * t) + 80) * np.exp(-8 * t))
def _sadbone(): return np.concatenate([wah(233, 0.42), wah(220, 0.42), wah(207.7, 0.42), wah(196, 1.3, 0.025)]) * 0.9
def _scratch():
    t = T(0.55); f = 500 * np.exp(-3 * t) * (1 + 0.8 * np.sin(2 * np.pi * 9 * t))
    return fade(fft_filter(saw(np.abs(f) + 60) * 0.5 + noise(0.55) * 0.5, 300, 6500) * np.clip(1 - t / 0.55, 0, 1) ** 0.5, 0.005, 0.05)
def _roar():
    t = T(1.9); amp = np.clip(t / 0.25, 0, 1) ** 0.5 * np.clip((1.9 - t) / 0.7, 0, 1)
    f0 = 85 + 40 * np.sin(np.pi * np.clip(t / 1.9, 0, 1)); rattle = 0.55 + 0.45 * np.sin(2 * np.pi * 27 * t)
    x = fft_filter(saw(f0) * rattle + 0.8 * noise(1.9) * rattle, 120, 2600)
    x = x + 0.7 * fft_filter(x, 500, 900) + 0.5 * fft_filter(x, 1100, 1500)
    return fade(x * amp, 0.01, 0.1)
def _crowd():
    t = T(2.4); m = fft_filter(noise(2.4), 250, 2200)
    for k in range(14): m += 0.25 * fft_filter(noise(2.4), 300 + 80 * k, 600 + 90 * k) * (0.5 + 0.5 * np.sin(2 * np.pi * (3 + k * 0.7) * t + k))
    return fade(m * np.clip(t / 1.8, 0, 1) ** 1.5, 0.05, 0.25)
def _honks(): return fft_filter(np.concatenate([honk(420, 0.22), silence(0.05), honk(480, 0.12), silence(0.04), honk(380, 0.35), silence(0.12), honk(520, 0.18)]), 200, 3500)
def _rev():
    t = T(1.3); rpm = 38 + 150 * np.clip(t / 0.9, 0, 1) ** 1.6 - 60 * np.clip((t - 1.0) / 0.3, 0, 1)
    return fade(fft_filter(saw(rpm) + 0.6 * saw(rpm * 2.01) + 0.3 * noise(1.3), 40, 1400) * np.clip(t / 0.05, 0, 1), 0.01, 0.12)
def _gps(): return np.concatenate([bell(988, 0.22, 9), bell(1319, 0.22, 9), bell(1568, 0.6, 6)]) * 0.9
def _dhol():
    t = T(0.6); return 0.9 * np.exp(-7 * t) * np.sin(2 * np.pi * (95 - 40 * t) * t) + 0.35 * click(0.6, 45)
def _boing():
    t = T(0.55)
    return fade(0.7 * np.exp(-2.5 * t) * sine(300 + 700 * np.exp(-6 * t) * np.sin(2 * np.pi * 14 * t * np.exp(-t)) + 250 * np.exp(-3 * t)), 0.005, 0.1)
def _confetti():
    t = T(0.9); return fade(fft_filter(noise(0.9), 1500, 9000) * np.exp(-5 * t) + 0.5 * bell(1760, 0.9, 6))
def _glitch():
    g = noise(0.35); st = np.zeros_like(g)
    for i in range(0, len(g), 1200): st[i:i + 1200] = np.resize(g[i:i + 1200][:int(rng.integers(40, 400))], 1200)
    return fade(fft_filter(st, 300, 9000) * 0.8, 0.002, 0.05)
def _screech():
    t = T(0.8); return fade(fft_filter(noise(0.8), 1800, 5500) * (0.5 + 0.5 * np.sin(2 * np.pi * 70 * t)) * np.clip(1 - t / 0.8, 0, 1) ** 0.7, 0.01, 0.1)
def _tick2(): return fade(0.6 * np.sin(2 * np.pi * 2400 * T(0.03)) * np.exp(-90 * T(0.03)), 0.001, 0.005)

GEN = {
    "siren": ("breaking-news siren, 1.1 s", _siren), "boom": ("deep impact boom, 1.0 s", _boom),
    "swoosh": ("soft whoosh for a card or cut, 0.7 s", _swoosh), "revwhoosh": ("reverse whoosh into a hit, 1.4 s", _revwhoosh),
    "riser2": ("rising synth + noise build-up, 2.6 s", _riser2), "shutter": ("camera shutter double click, 0.16 s", _shutter),
    "notify": ("phone notification two-note chime, 0.7 s", _notify), "beep": ("keypad beep, 0.07 s", _beep),
    "kaching": ("cash-register click + bell, 1.0 s", _kaching), "vanish": ("money vanishes, downward zip, 0.6 s", _vanish),
    "sadbone": ("sad trombone, 2.6 s", _sadbone), "scratch": ("record scratch, 0.55 s", _scratch),
    "roar": ("lion roar, 1.9 s", _roar), "crowd": ("crowd murmur swelling, 2.4 s", _crowd),
    "honks": ("traffic car honks, 1.0 s", _honks), "rev": ("engine rev, 1.3 s", _rev),
    "gps": ("navigation chime, 1.0 s", _gps), "dhol": ("dhol thud, 0.6 s", _dhol),
    "boing": ("slide-whistle boing, 0.55 s", _boing), "confetti": ("confetti pop with chime, 0.9 s", _confetti),
    "glitch": ("digital glitch stutter, 0.35 s", _glitch), "screech": ("tyre screech, 0.8 s", _screech),
    "tick2": ("tiny counter tick, 0.03 s", _tick2),
}


def render(name):
    global rng
    rng = np.random.default_rng(7 + zlib.crc32(name.encode()) % 1000)
    return GEN[name][1]()


def music(secs):
    """108 BPM A-minor groove (kit + bass + stabs + riff), exactly `secs` long, last 0.4 s faded so it can end anywhere."""
    global rng
    rng = np.random.default_rng(7)
    BPM = 108; beat = 60 / BPM; n = int(SR * secs); mus = np.zeros(n)
    def put(x, at, g=1.0):
        i = int(at * SR)
        if i < n: j = min(n, i + len(x)); mus[i:j] += g * x[: j - i]
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    def pluck(f, d=0.28): t = T(d); return np.exp(-9 * t) * (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-14 * t))
    def bass(f, d=0.3): t = T(d); return fade(np.exp(-4.5 * t) * (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)), 0.004, 0.03)
    def kick(): t = T(0.3); return np.sin(2 * np.pi * (46 + 90 * np.exp(-28 * t)) * t) * np.exp(-9 * t)
    def clap(): return fft_filter(noise(0.18), 900, 6500) * np.exp(-24 * T(0.18))
    def hat(o=False): d = 0.12 if o else 0.04; return fft_filter(noise(d), 6500, None) * np.exp(-(25 if o else 70) * T(d))
    prog = [(45, [69, 72, 76]), (41, [65, 69, 72]), (43, [67, 71, 74]), (40, [68, 71, 74, 76])]
    riff = [[0, None, 3, None, 5, 3, None, 0], [7, None, 5, None, 3, 5, 3, None], [0, 3, 5, 7, 5, 3, 0, None], [-1, None, 0, 3, 7, 5, 3, None]]
    for b in range(int(secs / (4 * beat)) + 1):
        t0 = b * 4 * beat; root, chord = prog[b % 4]; full = b >= 2
        for q in range(8): put(hat(q % 2 == 1), t0 + q * beat / 2, 0.16 if full else 0.08)
        if full:
            for k in (0, 2.0, 3.5): put(kick(), t0 + k * beat, 0.5)
            for k in (1, 3): put(clap(), t0 + k * beat, 0.32)
        for k, off in ((0, 0), (1.5, 12), (2, 7), (3, 0), (3.5, -1)): put(bass(midi(root + off + 12)), t0 + k * beat, 0.46)
        for k in (0.5, 1.5, 2.5, 3.25):
            for nt in chord: put(pluck(midi(nt - 12 if nt > 71 else nt)), t0 + k * beat, 0.14)
        if b >= 1:
            for q, s in enumerate(riff[b % 4]):
                if s is not None: put(pluck(midi(81 + s), 0.3), t0 + q * beat / 2, 0.16)
    return fade(fft_filter(mus, 60, 7500), 0, 0.4)  # low-pass keeps it out of the voice's presence band


def _old_names():
    try:
        import sfx
        return set(sfx.LIB)
    except ImportError:
        return set()


def ensure(names, folder, force=False, music_seconds=60):
    """Make missing wavs in folder; looks in synth first, then in sfx.LIB. Returns {name: path}."""
    folder = pathlib.Path(folder); folder.mkdir(parents=True, exist_ok=True)
    out = {}
    for n in dict.fromkeys(names):
        p = folder / ("%s.wav" % n)
        if n == "music":
            if not p.exists(): save(p, music(music_seconds), 0.8)
        elif n in GEN and (n not in _old_names() or force):
            if not p.exists() or force: save(p, render(n), 0.9)
        else:
            import sfx  # older library: ffmpeg lavfi
            out.update(sfx.ensure([n], folder)); continue
        out[n] = p
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", nargs="?"); ap.add_argument("--only"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--force", action="store_true"); ap.add_argument("--music", action="store_true")
    ap.add_argument("--music-bed-seconds", type=float, default=60)
    a = ap.parse_args()
    if a.list:
        for n, (desc, fn) in GEN.items(): print("%-10s %5.2f s  %s" % (n, len(render(n)) / SR, desc))
        print("%-10s %5s    music bed, 108 BPM A-minor groove (--music, length from --music-bed-seconds)" % ("music", "var"))
        return
    if not a.out: ap.error("out dir required")
    names = [n.strip() for n in a.only.split(",")] if a.only else list(GEN)
    old = _old_names(); folder = pathlib.Path(a.out); folder.mkdir(parents=True, exist_ok=True); done = []
    for n in names:
        if n not in GEN and n in old: print("skip %s: name belongs to sfx.py" % n); continue
        if n not in GEN: sys.exit("unknown synth sfx %r (synth.py --list)" % n)
        if n in old and not a.force: print("skip %s: name belongs to sfx.py (use --force)" % n); continue
        save(folder / ("%s.wav" % n), render(n), 0.9); done.append(n)
    print("wrote %d sfx to %s: %s" % (len(done), folder, " ".join(done)))
    if a.music:
        save(folder / "music.wav", music(a.music_bed_seconds), 0.8); print("music.wav %.1f s" % a.music_bed_seconds)


if __name__ == "__main__":
    main()
