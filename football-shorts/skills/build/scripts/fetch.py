#!/usr/bin/env python3
"""Fetch source videos for an edit into <edit_dir>/src/ and log them in sources.json.

  fetch.py <edit_dir> --accept-terms --name por --rights broadcaster https://www.youtube.com/watch?v=...
  fetch.py <edit_dir> --accept-terms --name fan1 --rights fan --section 120-260 <url>
  fetch.py <edit_dir> --info <url>            # metadata only, nothing downloaded

--accept-terms is mandatory for a download. Downloading from YouTube breaks its Terms
of Service and broadcast/club footage carries a High Content ID risk that no edit
removes. The flag records that the user made that call for this source.
--rights is the origin class the researcher assigned: broadcaster | club | player |
fan | creator | own | unknown. It is copied into sources.json so the hand-off can
state the risk per clip. --section a-b downloads only that time range (seconds).
"""
import argparse, datetime as dt, json, os, re, shutil, subprocess, sys

FMT = "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b"

def info(url):
    p = subprocess.run(["yt-dlp", "-j", "--no-playlist", "--no-warnings", url], capture_output=True, text=True)
    try: d = json.loads(p.stdout)
    except Exception: sys.exit("could not read metadata: " + p.stderr[-300:])
    ts = d.get("timestamp")
    return {"url": d.get("webpage_url", url), "id": d.get("id"), "title": d.get("title"), "channel": d.get("channel"),
            "verified": bool(d.get("channel_is_verified")),
            "uploaded_utc": dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d %H:%M") if ts else None,
            "views": d.get("view_count"), "likes": d.get("like_count"), "duration_s": d.get("duration"),
            "width": d.get("width"), "height": d.get("height"), "fps": d.get("fps")}

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("edit_dir"); ap.add_argument("url")
    ap.add_argument("--name", help="short key used in the spec's sources map, e.g. por, fan1")
    ap.add_argument("--rights", default="unknown", choices=["broadcaster", "club", "player", "fan", "creator", "own", "unknown"])
    ap.add_argument("--section", help="a-b seconds; download only this range")
    ap.add_argument("--accept-terms", action="store_true"); ap.add_argument("--info", action="store_true")
    a = ap.parse_args()
    if not shutil.which("yt-dlp"): sys.exit("yt-dlp not installed (brew install yt-dlp)")
    meta = info(a.url)
    if a.info:
        print(json.dumps(meta, indent=1, ensure_ascii=False)); return
    if not a.accept_terms:
        sys.exit("Refusing to download without --accept-terms. Tell the user: this breaks YouTube ToS; "
                 "%s footage = Content ID risk that cropping/speed/music/short excerpts do not remove. "
                 "Rerun with --accept-terms once they say yes." % a.rights)
    name = a.name or re.sub(r"[^a-z0-9]+", "_", (meta["title"] or meta["id"]).lower())[:40].strip("_")
    src = os.path.join(a.edit_dir, "src"); os.makedirs(src, exist_ok=True)
    out = os.path.join(src, name + ".mp4")
    cmd = ["yt-dlp", "-f", FMT, "--merge-output-format", "mp4", "--no-playlist", "--no-warnings", "-o", out, a.url]
    if a.section:
        s, e = a.section.split("-"); cmd += ["--download-sections", "*%s-%s" % (s, e), "--force-keyframes-at-cuts"]
    print(" ".join(cmd)); subprocess.run(cmd, check=True)
    pr = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                         "stream=width,height,r_frame_rate:format=duration", "-of", "json", out], capture_output=True, text=True)
    pj = json.loads(pr.stdout or "{}")
    st = (pj.get("streams") or [{}])[0]
    meta.update({"name": name, "file": os.path.relpath(out, a.edit_dir), "rights": a.rights, "section": a.section,
                 "local": {"width": st.get("width"), "height": st.get("height"), "fps": st.get("r_frame_rate"),
                           "duration_s": round(float(pj.get("format", {}).get("duration", 0)), 2)},
                 "fetched_utc": dt.datetime.now(dt.UTC).strftime("%Y-%m-%d %H:%M")})
    man = os.path.join(a.edit_dir, "sources.json")
    lst = json.load(open(man)) if os.path.exists(man) else []
    lst = [m for m in lst if m.get("name") != name] + [meta]
    json.dump(lst, open(man, "w"), indent=1, ensure_ascii=False)
    print("saved %s  (%sx%s %s, %ss)  rights=%s  -> sources.json" % (
        meta["file"], st.get("width"), st.get("height"), st.get("r_frame_rate"), meta["local"]["duration_s"], a.rights))

if __name__ == "__main__":
    main()
