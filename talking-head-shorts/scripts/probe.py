#!/usr/bin/env python3
"""Intake: probe the ORIGINAL video and write <slug>/probe.json, <slug>/blink.json, <slug>/intake_frames.png.

  probe.py <video> <slug folder> [--no-link]

- fps, size, rotation, audio, duration (ffprobe). Links the original as <slug>/source.<ext> (symlink; the
  file is never re-encoded or edited).
- blink pre-pass: per-frame mean brightness / clip median; < 0.93 = "blink" (black jump-cut frames some
  phones and editors leave in). blink.json is {"fps": 30, "values": [..]} on the 30 fps grid (even source
  frames of a 60 fps clip), 1 = normal picture, 0 = black. The Remotion template dips the WHOLE picture
  with it when the background is swapped, otherwise the black frames are simply in the video.
- aspect: if not 9:16, a speaker-centred 9:16 crop box is suggested from face detection (OpenCV Haar), and
  intake_frames.png shows the crop and the blurred-fill options side by side so the choice is made by eye.
Python with numpy + OpenCV (setup.sh venv python).
"""
import argparse, json, os, pathlib, subprocess, sys
import numpy as np, cv2


def ffprobe(path):
    j = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path],
                                  capture_output=True, text=True, check=True).stdout)
    v = next(s for s in j["streams"] if s["codec_type"] == "video")
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), None)
    n, d = v["avg_frame_rate"].split("/")
    rot = 0
    for sd in v.get("side_data_list", []) or []:
        if "rotation" in sd:
            rot = int(sd["rotation"])
    return {"w": int(v["width"]), "h": int(v["height"]), "fps": float(n) / float(d) if float(d) else 30.0,
            "duration": float(j["format"]["duration"]), "rotation": rot, "codec": v["codec_name"],
            "audio": ({"codec": a["codec_name"], "rate": int(a.get("sample_rate", 0)), "channels": a.get("channels")} if a else None)}


def blink_scan(path, fps):
    cap = cv2.VideoCapture(path)
    means = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        means.append(float(cv2.resize(f, (96, 96), interpolation=cv2.INTER_AREA).mean()))
    cap.release()
    m = np.array(means)
    level = np.clip(m / max(np.median(m), 1e-6), 0, 1)
    return level, fps


def faces(path, times):
    """Median face box (x, y, w, h) over a few frames, or None."""
    casc = cv2.CascadeClassifier(os.path.join(cv2.data.haarcascades, "haarcascade_frontalface_default.xml"))
    if casc.empty():
        return None
    cap = cv2.VideoCapture(path)
    boxes = []
    for t in times:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * (cap.get(cv2.CAP_PROP_FPS) or 30))))
        ok, f = cap.read()
        if not ok:
            continue
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        found = casc.detectMultiScale(g, 1.1, 5, minSize=(max(40, f.shape[1] // 12),) * 2)
        if len(found):
            boxes.append(max(found, key=lambda b: b[2] * b[3]))
    cap.release()
    return [int(v) for v in np.median(np.array(boxes), axis=0)] if boxes else None


def frame_at(path, t):
    cap = cv2.VideoCapture(path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(round(t * (cap.get(cv2.CAP_PROP_FPS) or 30))))
    ok, f = cap.read()
    cap.release()
    return f if ok else None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("folder"); ap.add_argument("--no-link", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.video).expanduser().resolve()
    out = pathlib.Path(a.folder).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    info = ffprobe(str(src))
    w, h = (info["h"], info["w"]) if abs(info["rotation"]) in (90, 270) else (info["w"], info["h"])
    link = out / ("source" + src.suffix.lower())
    if not a.no_link and not link.exists():
        link.symlink_to(src)
    level, fps = blink_scan(str(src), info["fps"])
    step = max(1, int(round(fps / 30)))
    grid = [round(float(v), 3) for v in level[::step]]
    json.dump({"fps": 30, "values": grid}, open(out / "blink.json", "w"))
    blinks, run = [], None
    for i, v in enumerate(level):
        if v < 0.93:
            run = run or [i / fps, i / fps]
            run[1] = i / fps
        elif run:
            blinks.append([round(run[0], 3), round(run[1], 3)]); run = None
    if run:
        blinks.append([round(run[0], 3), round(run[1], 3)])
    nine = abs(w / h - 9 / 16) < 0.02
    res = {"path": str(src), "link": str(link), "width": w, "height": h, "fps": info["fps"], "duration": round(info["duration"], 3),
           "audio": info["audio"], "codec": info["codec"], "nine_sixteen": nine, "blink_spans": blinks, "blink_threshold": 0.93,
           "low_res": h < 1000}
    crop = None
    if not nine:
        fb = faces(str(src), [info["duration"] * k for k in (0.1, 0.3, 0.5, 0.7, 0.9)])
        cw = min(w, int(round(h * 9 / 16)))
        cx = (fb[0] + fb[2] / 2) if fb else w / 2
        x = int(min(max(cx - cw / 2, 0), w - cw))
        crop = [x, 0, cw, h] if cw < w else None
        res.update({"face_box": fb, "suggested_crop": crop,
                    "note": "not 9:16: decide with the user between fit=crop (suggested_crop) and fit=blurfill" if crop else "wider-than-tall source needs a crop or blurfill; no crop fits"})
    json.dump(res, open(out / "probe.json", "w"), indent=1)
    # decision frames: the source, the crop, the blurred-fill, at the middle of the clip
    f = frame_at(str(src), info["duration"] / 2)
    if f is not None:
        tiles = [f.copy()]
        if crop:
            tiles.append(f[crop[1]:crop[1] + crop[3], crop[0]:crop[0] + crop[2]].copy())
            bg = cv2.GaussianBlur(cv2.resize(f, (f.shape[1], f.shape[0])), (0, 0), 25)
            tiles.append(bg)
        H = 640
        tiles = [cv2.resize(t, (int(t.shape[1] * H / t.shape[0]), H)) for t in tiles]
        if crop:  # blurfill preview: the full frame centred in a 9:16 canvas over its own blur
            cw9 = int(H * 9 / 16)
            canvas = cv2.resize(cv2.GaussianBlur(f, (0, 0), 25), (cw9, H))
            fh = int(cw9 * f.shape[0] / f.shape[1])
            canvas[(H - fh) // 2:(H - fh) // 2 + fh] = cv2.resize(f, (cw9, fh))
            tiles[2] = canvas
        labels = ["source %dx%d" % (w, h), "crop", "blurfill"]
        for t, lab in zip(tiles, labels):
            cv2.putText(t, lab, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
        cv2.imwrite(str(out / "intake_frames.png"), np.hstack(tiles))
    print(json.dumps({k: res[k] for k in res if k not in ("path", "link")}, indent=1))
    print("blink frames: %s" % (blinks or "none"))
    print("wrote", out / "probe.json", out / "blink.json", out / "intake_frames.png")


if __name__ == "__main__":
    main()
