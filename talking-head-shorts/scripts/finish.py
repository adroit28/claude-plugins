#!/usr/bin/env python3
"""Finish a version: mix, append the like & subscribe outro, contact sheet, loudness check, hand-over file.

  finish.py <slug folder | edit.vN.json> [--skip-mix] [--no-outro]

1. mix.py  -> build_v<N>.mp4   (skipped when it exists and --skip-mix)
2. outro.py -> <slug>_v<N>.mp4 (3 s card, spec.outro.seconds); refuses to overwrite an earlier version
3. sheets.py grid -> <slug>_v<N>_sheet.png (12 frames)
4. ffmpeg loudnorm measurement: integrated LUFS and true peak, flagged when outside -16..-12 LUFS / above -1 dBTP
Prints the facts the hand-over needs (duration, size, fps, loudness, path).
"""
import argparse, json, pathlib, re, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import load_spec

HERE = pathlib.Path(__file__).resolve().parent


def measure(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "loudnorm=I=-14:TP=-1.5:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True)
    j = json.loads(re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", r.stderr, re.S).group(0))
    return float(j["input_i"]), float(j["input_tp"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target"); ap.add_argument("--skip-mix", action="store_true"); ap.add_argument("--no-outro", action="store_true")
    a = ap.parse_args()
    specpath, spec = load_spec(pathlib.Path(a.target).expanduser())
    folder, v, slug = specpath.parent, spec["version"], spec["slug"]
    final = folder / ("%s_v%d.mp4" % (slug, v))
    if final.exists():
        sys.exit("%s exists: versions are never overwritten (bump the spec, or move that file)" % final)
    build = folder / ("build_v%d.mp4" % v)
    if not (a.skip_mix and build.exists()):
        subprocess.run([sys.executable, str(HERE / "mix.py"), str(specpath)], check=True)
    if a.no_outro:
        build.rename(final)
    else:
        subprocess.run([sys.executable, str(HERE / "outro.py"), str(build), "--out", str(final), "--seconds", str(spec["outro"]["seconds"])], check=True)
    sheet = folder / ("%s_v%d_sheet.png" % (slug, v))
    subprocess.run([sys.executable, str(HERE / "sheets.py"), "grid", str(final), str(sheet), "--n", "12", "--cols", "6", "--h", "420"], check=True)
    lufs, tp = measure(final)
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=width,height,r_frame_rate,duration", "-of", "json", str(final)],
                                     capture_output=True, text=True, check=True).stdout)["streams"][0]
    flag = "" if -16 <= lufs <= -12 and tp <= -1.0 else "  <-- OUT OF RANGE"
    print("\nfinished: %s\n  %sx%s @ %s fps, %.2f s | loudness %.1f LUFS, true peak %.1f dBTP%s\n  contact sheet: %s" % (
        final, info["width"], info["height"], info["r_frame_rate"], float(info["duration"]), lufs, tp, flag, sheet))


if __name__ == "__main__":
    main()
