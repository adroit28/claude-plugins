#!/usr/bin/env python3
"""Finish a multi-clip version: optional outro, contact sheet, loudness check, hand-over file (no edit.vN.json needed).

  finish_tl.py <slug folder> [--outro none|subscribe] [--version N]

Takes <slug>/build_v<N>.mp4 (latest N unless --version), optionally appends the 3 s like & subscribe card (default none: the Remotion
project has its own end card), writes <slug>/<slug>_v<N>.mp4 (never overwrites), a 12-frame sheet <slug>_v<N>_sheet.png, and measures
integrated LUFS and true peak (flagged outside -16..-12 LUFS / above -1 dBTP). Prints the hand-over facts. Slug name = folder name.
"""
import argparse, json, pathlib, re, shutil, subprocess, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from finish import measure

HERE = pathlib.Path(__file__).resolve().parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug"); ap.add_argument("--outro", choices=["none", "subscribe"], default="none"); ap.add_argument("--version", type=int)
    a = ap.parse_args()
    folder = pathlib.Path(a.slug).expanduser().resolve(); slug = folder.name
    builds = sorted((int(m.group(1)), p) for p in folder.glob("build_v*.mp4") if (m := re.fullmatch(r"build_v(\d+)\.mp4", p.name)))
    if not builds: sys.exit("no build_v<N>.mp4 in %s (run mix_multi.py first)" % folder)
    pick = [b for b in builds if b[0] == a.version] if a.version else builds[-1:]
    if not pick: sys.exit("no build_v%s.mp4 in %s" % (a.version, folder))
    v, build = pick[0]
    final = folder / ("%s_v%d.mp4" % (slug, v))
    if final.exists(): sys.exit("%s exists: versions are never overwritten (bump the version, or move that file)" % final)
    if a.outro == "subscribe":
        subprocess.run([sys.executable, str(HERE / "outro.py"), str(build), "--out", str(final), "--seconds", "3"], check=True)
    else:
        shutil.copyfile(build, final)
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
