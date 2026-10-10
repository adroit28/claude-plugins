#!/usr/bin/env python3
"""Synthesize the sound-effect library with ffmpeg lavfi (no downloads, no licences to track).

  sfx.py <story.vN.json | out dir> [--only ring,ding] [--list]

Writes <edit>/anim/public/sfx/<name>.wav (or into the given folder), 48 kHz. Use them in the scene
with <Sfx at={...} src="ring" vol={0.45} />. Re-running overwrites only these generated files.

  ring    old phone bell, 0.55 s (hook; again before the loop)   click   receiver pick-up / tap
  riser   rising sweep, 2.6 s (build-up before a reveal)        bass    low hit on a reveal word
  horn    ship horn, 1.1 s                                       whoosh  card slide / transition
  ding    bright bell, 0.8 s (a correct answer, a light bulb)   buzz    wrong-answer buzzer
  stamp   heavy thud (a stamp slam)                              waves   sea wash, 1.6 s
  pop     soft pop (emoji/props appearing)                       tick    clock tick (counters)
  coin    coin clink (money topics)                              sparkle shimmer (a discovery)

  0.8.0:
  boom      deep impact boom, 1.0 s (a big reveal)             revwhoosh  reverse whoosh into a hit, 1.4 s
  glitch    digital stutter, 0.35 s (Glitch slam)              scratch    record scratch, 0.55 s (a myth stops)
  sadbone   sad trombone, 2.6 s (a failed fix; use once)       boing      slide-whistle boing, 0.55 s
  notify    phone notification chime, 0.7 s (Notify)           kaching    cash-register click + bell, 1.0 s
  confetti  confetti pop with chime, 0.9 s (Confetti)          shutter    camera shutter double click, 0.16 s
  tick2     tiny counter tick, 0.03 s

  sfx.py <story.vN.json | out dir> --music [--seconds 62]   writes music.wav, a 108 BPM A-minor bed (stdlib only,
  deterministic); anim.py render mixes it ducked under the narration when the story has "video": {"music": true}
"""
import argparse, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

# name -> (lavfi source, extra -af filter or None)
LIB = {
    "ring": ("aevalsrc='0.5*(sin(2*PI*1180*t)+0.6*sin(2*PI*2360*t))*(0.5+0.5*sgn(sin(2*PI*22*t)))*(1-exp(-40*t))':d=0.55:s=48000",
             "afade=t=out:st=0.45:d=0.1"),
    "click": ("anoisesrc=d=0.04:c=white:a=0.8:r=48000", "highpass=f=1500,afade=t=out:st=0.01:d=0.03"),
    "riser": ("aevalsrc='0.4*(t/2.6)*sin(2*PI*(150*t+700*t*t/2.6))':d=2.6:s=48000", "afade=t=out:st=2.5:d=0.1"),
    "bass": ("aevalsrc='0.9*exp(-6*t)*sin(2*PI*(70-25*t)*t)':d=0.7:s=48000", None),
    "horn": ("aevalsrc='0.3*(sin(2*PI*98*t)+0.7*sin(2*PI*147*t)+0.5*sin(2*PI*196*t)+0.3*sin(2*PI*294*t))':d=1.1:s=48000",
             "lowpass=f=900,afade=t=in:d=0.12,afade=t=out:st=0.75:d=0.35"),
    "whoosh": ("anoisesrc=d=0.45:c=pink:a=0.7:r=48000", "highpass=f=500,lowpass=f=6000,afade=t=in:d=0.2:curve=exp,afade=t=out:st=0.2:d=0.25"),
    "ding": ("aevalsrc='0.5*exp(-5*t)*(sin(2*PI*1568*t)+0.4*sin(2*PI*3136*t))':d=0.8:s=48000", None),
    "buzz": ("aevalsrc='0.35*sgn(sin(2*PI*140*t))':d=0.35:s=48000", "lowpass=f=1800,afade=t=out:st=0.25:d=0.1"),
    "stamp": ("aevalsrc='0.9*exp(-14*t)*sin(2*PI*85*t)+0.3*exp(-60*t)*(random(0)*2-1)':d=0.35:s=48000", None),
    "waves": ("anoisesrc=d=1.6:c=brown:a=0.5:r=48000", "lowpass=f=700,afade=t=in:d=0.4,afade=t=out:st=1.1:d=0.5"),
    "pop": ("aevalsrc='0.7*exp(-30*t)*sin(2*PI*(900-2500*t)*t)':d=0.12:s=48000", None),
    "tick": ("aevalsrc='0.6*exp(-120*t)*sin(2*PI*3000*t)':d=0.05:s=48000", None),
    "coin": ("aevalsrc='0.4*exp(-7*t)*(sin(2*PI*2093*t)+0.6*sin(2*PI*2637*t)+0.3*sin(2*PI*4186*t))':d=0.6:s=48000", None),
    "sparkle": ("aevalsrc='0.25*exp(-3*t)*(sin(2*PI*2349*t)*(0.5+0.5*sin(2*PI*14*t))+sin(2*PI*3136*t)*(0.5+0.5*sin(2*PI*17*t+1)))':d=1.0:s=48000",
                "afade=t=in:d=0.05"),
    # 0.8.0 (ported from talking-head-shorts synth.py; the ones that suit facts Shorts, as lavfi expressions)
    "boom": ("aevalsrc='0.95*exp(-4.5*t)*sin(2*PI*(60-22*t)*t)+0.4*exp(-9*t)*(random(0)*2-1)':d=1.0:s=48000", "lowpass=f=1100,volume=0.7,afade=t=out:st=0.9:d=0.1"),
    "revwhoosh": ("anoisesrc=d=1.4:c=pink:a=0.8:r=48000", "highpass=f=300,lowpass=f=9000,volume=2.5,afade=t=in:d=1.38:curve=exp,afade=t=out:st=1.38:d=0.02"),
    "glitch": ("aevalsrc='0.45*sgn(sin(2*PI*(300+2000*mod(floor(t*40)*0.618,1))*t))*(0.5+0.5*sgn(sin(2*PI*31*t)))':d=0.35:s=48000",
               "highpass=f=250,lowpass=f=9000,volume=0.6,afade=t=out:st=0.3:d=0.05"),
    "scratch": ("aevalsrc='(0.5*sgn(sin(2*PI*(60+500*exp(-3*t)*(1+0.8*sin(2*PI*9*t)))*t))+0.5*(random(0)*2-1))*sqrt(1-t/0.55)':d=0.55:s=48000",
                "highpass=f=300,lowpass=f=6500,volume=0.6,afade=t=out:st=0.5:d=0.05"),
    "sadbone": ("aevalsrc='0.55*pow(abs(sin(PI*if(lt(t,1.26),mod(t,0.42)/0.42,(t-1.26)/1.3))),0.5)*(2*mod(if(lt(t,0.42),233,if(lt(t,0.84),220,if(lt(t,1.26),207.7,196*(1+0.025*sin(2*PI*5.5*t)))))*t,1)-1)':d=2.56:s=48000",
                "lowpass=f=1100"),
    "boing": ("aevalsrc='0.7*exp(-2.5*t)*sin(2*PI*(300+700*exp(-6*t)*sin(2*PI*14*t*exp(-t))+250*exp(-3*t))*t)':d=0.55:s=48000", "afade=t=in:d=0.005,afade=t=out:st=0.45:d=0.1"),
    "notify": ("aevalsrc='0.5*if(lt(t,0.18),exp(-14*t)*(sin(2*PI*1319*t)+0.35*sin(2*PI*3640*t)),exp(-7*(t-0.18))*(sin(2*PI*1760*t)+0.35*sin(2*PI*4858*t)))':d=0.7:s=48000", None),
    "kaching": ("aevalsrc='0.5*if(lt(t,0.03),0.8*(random(0)*2-1)*exp(-80*t),if(lt(t,0.07),0,exp(-5*(t-0.07))*(sin(2*PI*2093*t)+0.6*sin(2*PI*3136*t))))':d=1.0:s=48000", None),
    "confetti": ("aevalsrc='0.6*exp(-5*t)*(random(0)*2-1)+0.5*exp(-6*t)*(sin(2*PI*1760*t)+0.35*sin(2*PI*4858*t))':d=0.9:s=48000", "highpass=f=1200,lowpass=f=9000,volume=0.75"),
    "shutter": ("aevalsrc='if(lt(t,0.04),(random(0)*2-1)*exp(-90*t),if(lt(t,0.09),0,0.7*(random(0)*2-1)*exp(-60*(t-0.09))))':d=0.16:s=48000", "highpass=f=1500,volume=0.6"),
    "tick2": ("aevalsrc='0.6*exp(-90*t)*sin(2*PI*2400*t)':d=0.03:s=48000", None),
}


def music(secs, out):
    """108 BPM A-minor groove (hats, kick, clap, bass, plucked chords, a riff), exactly `secs` long, stdlib only.
    Ported from talking-head-shorts synth.py music() (numpy there). Deterministic; the last 0.4 s fades so it can end anywhere.
    Each distinct sound is synthesized once and mixed in by addition, so 60 s takes a few seconds."""
    import array, math, random, wave
    SR = 48000; n = int(SR * secs); mus = array.array("f", bytes(4 * n)); rng = random.Random(7)
    beat = 60 / 108; midi = lambda m: 440 * 2 ** ((m - 69) / 12)
    def ts(d): return [i / SR for i in range(int(SR * d))]
    def noise(d): return [rng.uniform(-1, 1) for _ in range(int(SR * d))]
    def hp(x, a=0.85):  # first-order high-pass
        y = []; q = p = 0.0
        for v in x: q = a * (q + v - p); p = v; y.append(q)
        return y
    def lp(x, a=0.2):
        y = []; q = 0.0
        for v in x: q += a * (v - q); y.append(q)
        return y
    def pluck(f, d=0.28):
        t = ts(d); return [math.exp(-9 * u) * (math.sin(2 * math.pi * f * u) + 0.35 * math.sin(2 * math.pi * f * 4 * u) * math.exp(-14 * u)) for u in t]
    def bass(f, d=0.3):
        t = ts(d); x = [math.exp(-4.5 * u) * (math.sin(2 * math.pi * f * u) + 0.3 * math.sin(2 * math.pi * f * 2 * u)) for u in t]
        for i in range(min(len(x), 192)): x[i] *= i / 192
        return x
    def kick():
        t = ts(0.3); return [math.sin(2 * math.pi * (46 + 90 * math.exp(-28 * u)) * u) * math.exp(-9 * u) for u in t]
    def clap(): return [v * math.exp(-24 * i / SR) for i, v in enumerate(lp(hp(noise(0.18)), 0.5))]
    def hat(o=False):
        d = 0.12 if o else 0.04; return [v * math.exp(-(25 if o else 70) * i / SR) for i, v in enumerate(hp(noise(d), 0.95))]
    cache = {}
    def snd(key, fn): 
        if key not in cache: cache[key] = fn()
        return cache[key]
    def put(x, at, g=1.0):
        i = int(at * SR)
        if i >= n: return
        for j in range(min(len(x), n - i)): mus[i + j] += g * x[j]
    prog = [(45, [69, 72, 76]), (41, [65, 69, 72]), (43, [67, 71, 74]), (40, [68, 71, 74, 76])]
    riff = [[0, None, 3, None, 5, 3, None, 0], [7, None, 5, None, 3, 5, 3, None], [0, 3, 5, 7, 5, 3, 0, None], [-1, None, 0, 3, 7, 5, 3, None]]
    for b in range(int(secs / (4 * beat)) + 1):
        t0 = b * 4 * beat; root, chord = prog[b % 4]; full = b >= 2
        for q in range(8): put(snd(("hat", q % 2), lambda: hat(q % 2 == 1)), t0 + q * beat / 2, 0.16 if full else 0.08)
        if full:
            for k in (0, 2.0, 3.5): put(snd("kick", kick), t0 + k * beat, 0.5)
            for k in (1, 3): put(snd("clap", clap), t0 + k * beat, 0.32)
        for k, off in ((0, 0), (1.5, 12), (2, 7), (3, 0), (3.5, -1)): f = midi(root + off + 12); put(snd(("bass", f), lambda: bass(f)), t0 + k * beat, 0.46)
        for k in (0.5, 1.5, 2.5, 3.25):
            for nt in chord: f = midi(nt - 12 if nt > 71 else nt); put(snd(("pl", f), lambda: pluck(f)), t0 + k * beat, 0.14)
        if b >= 1:
            for q, st in enumerate(riff[b % 4]):
                if st is not None: f = midi(81 + st); put(snd(("rf", f), lambda: pluck(f, 0.3)), t0 + q * beat / 2, 0.16)
    nf = int(0.4 * SR)
    for i in range(nf): mus[n - nf + i] *= 1 - i / nf
    peak = max(max(mus), -min(mus)) or 1
    raw = (b"".join(int(max(-1, min(1, v / peak * 0.9)) * 32767).to_bytes(2, "little", signed=True) for v in mus))
    tmp = pathlib.Path(out).with_suffix(".raw.wav")
    with wave.open(str(tmp), "wb") as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(raw)
    # keep it out of the voice's presence band and the sub rumble (same intent as the numpy version's 60 Hz-7.5 kHz filter)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(tmp), "-af", "highpass=f=60,lowpass=f=7500", str(out)], check=True); tmp.unlink()


def make(name, out):
    src, af = LIB[name]
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src] + (["-af", af] if af else []) + [str(out)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?"); ap.add_argument("--only"); ap.add_argument("--list", action="store_true")
    ap.add_argument("--music", action="store_true", help="write music.wav (a bed) instead of the sound effects")
    ap.add_argument("--seconds", type=float, default=62.0, help="length of the music bed")
    a = ap.parse_args()
    if a.list or not a.target:
        print(__doc__.split("\n\n", 2)[2]); return
    t = pathlib.Path(a.target)
    if t.suffix == ".json":
        from common import Story
        st = Story(t); out = st.dir / st.data.get("anim", {}).get("dir", "anim") / "public" / "sfx"
    else:
        out = t
    out.mkdir(parents=True, exist_ok=True)
    if a.music:
        dst = out.parent / "music.wav" if out.name == "sfx" else out / "music.wav"
        music(a.seconds, dst); print("wrote", dst, "(%.1f s)" % a.seconds); return
    names = [n.strip() for n in a.only.split(",")] if a.only else list(LIB)
    for n in names:
        if n not in LIB: sys.exit("unknown sfx %r (sfx.py --list)" % n)
        make(n, out / ("%s.wav" % n))
    print("wrote %d sounds to %s: %s" % (len(names), out, " ".join(names)))


if __name__ == "__main__":
    main()
