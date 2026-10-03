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
}


def make(name, out):
    src, af = LIB[name]
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", src] + (["-af", af] if af else []) + [str(out)]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", nargs="?"); ap.add_argument("--only"); ap.add_argument("--list", action="store_true")
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
    names = [n.strip() for n in a.only.split(",")] if a.only else list(LIB)
    for n in names:
        if n not in LIB: sys.exit("unknown sfx %r (sfx.py --list)" % n)
        make(n, out / ("%s.wav" % n))
    print("wrote %d sounds to %s: %s" % (len(names), out, " ".join(names)))


if __name__ == "__main__":
    main()
