#!/usr/bin/env python3
"""Final mux: picture track + voice/whoosh mix + bass hits (+ optional music bed) -> <slug>_v<N>.mp4.

  finish.py <story.vN.json>

Reads build/timeline_v<N>.json from compose.py (and clips.py, which points it at the footage track). The video stream is copied (it was encoded once by
compose.py). Audio: the voice mix, 48 Hz sine hits at the anchored words, an optional music bed
from the story's assets, then loudnorm to -14 LUFS / -1.5 dBTP. AAC 160k 48 kHz stereo, +faststart.
"""
import json, pathlib, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import Story


def main():
    st = Story(sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__))
    tl = json.loads(st.p("build/timeline_v%d.json" % st.version).read_text())
    if st.data.get("clips") and not tl.get("clips"):
        sys.exit("the story has clips but timeline_v%d.json points at the card-only track: run clips.py after compose.py" % st.version)
    total = tl["total"]; au = st.data.get("audio", {})
    # A silent stereo track goes first so amix (duration=first) runs the exact length and mixes in stereo.
    inputs = ["-i", str(st.p(tl["video"])), "-f", "lavfi", "-t", "%.3f" % total, "-i", "anullsrc=r=48000:cl=stereo",
              "-ss", "0", "-t", "%.3f" % total, "-i", str(st.p(tl["voice_fx"]))]
    fc = "[1:a]volume=0[a0];[2:a]volume=%s,afade=t=out:st=%.3f:d=%.3f[a2];" % (au.get("voice_volume", 1.0), max(total - 0.25, 0), 0.25)
    mix, n = ["[a0]", "[a2]"], 3
    bed = au.get("bed")
    if bed:
        asset = st.data["assets"][bed["asset"]]
        if asset.get("rights", {}).get("class") in (None, "unknown", "doubtful"):
            sys.exit("music bed %r has rights class %r: use a licensed or CC track" % (bed["asset"], asset.get("rights", {}).get("class")))
        fo = bed.get("fade_out", 1.0)
        inputs += ["-ss", str(bed.get("ss", 0)), "-t", "%.3f" % total, "-i", str(st.p(asset["path"]))]
        fc += "[%d:a]volume=%s,afade=t=out:st=%.3f:d=%.3f[a%d];" % (n, bed.get("volume", 0.12), max(total - fo, 0), fo, n)
        mix.append("[a%d]" % n); n += 1
    for h in tl["hits"]:
        inputs += ["-f", "lavfi", "-t", "1", "-i", "sine=f=%s:d=%s" % (h.get("freq", 48), h.get("dur", 0.6))]
        ms = int(h["at"] * 1000)
        fc += "[%d:a]afade=t=out:st=0.05:d=0.5,adelay=%d|%d,volume=%s[a%d];" % (n, ms, ms, h.get("volume", 0.9), n)
        mix.append("[a%d]" % n); n += 1
    L = au.get("loudness", {"I": -14, "TP": -1.5, "LRA": 11})
    fc += "%samix=inputs=%d:duration=first:normalize=0,loudnorm=I=%s:TP=%s:LRA=%s[a]" % ("".join(mix), len(mix), L["I"], L["TP"], L["LRA"])
    out = st.mp4
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", fc, "-map", "0:v", "-map", "[a]", "-c:v", "copy",
                    "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", "-t", "%.3f" % total, str(out)], check=True)
    print("finished", out, "%.2fs" % total, "hits", [h["at"] for h in tl["hits"]])


if __name__ == "__main__":
    main()
