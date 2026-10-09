#!/usr/bin/env python3
"""Multi-clip: face position per frame of every normalised clip -> <slug>/track.json.

  track.py <slug folder> [--only a,b] [--method auto|cv2|vision] [--check name]

Reads <slug>/norm/<name>.mp4 and writes <slug>/track.json {"name": [[x, y, w], ...one per frame]} in 1080x1920
pixels (face centre x, y and face width). Missing frames are interpolated, then each series gets a 13-tap
moving average with edge padding. Methods: cv2 = OpenCV Haar (fast, frontal faces), vision = Apple Vision via
face.swift (compiled once to ~/.cache/talking-head-shorts/face), auto = cv2 when its cascade file exists.
--check name prints only the first / middle / last face point of that clip (no file written).
"""
import argparse, json, pathlib, subprocess, sys
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from common import content_dir  # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
BIN = pathlib.Path.home() / ".cache/talking-head-shorts/face"


def cascade_path():
    try:
        import cv2
        p = pathlib.Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        return p if p.exists() else None
    except Exception:
        return None


def track_cv2(path):
    import cv2
    if not cascade_path():
        raise RuntimeError("this OpenCV build has no haarcascade_frontalface_default.xml (OpenCV 5 dropped it); use --method vision")
    casc = cv2.CascadeClassifier(str(cascade_path()))
    cap = cv2.VideoCapture(str(path)); pts = []
    while True:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(cv2.resize(f, (270, int(f.shape[0] * 270 / f.shape[1]))), cv2.COLOR_BGR2GRAY)
        r = casc.detectMultiScale(g, 1.1, 5, minSize=(60, 60))
        if len(r):
            x, y, w, h = max(r, key=lambda a: a[2]); k = 1080 / 270
            pts.append([(x + w / 2) * k, (y + h / 2) * k, w * k])
        else:
            pts.append(None)
    return pts


def track_vision(path):
    swift = HERE / "face.swift"
    if not BIN.exists() or BIN.stat().st_mtime < swift.stat().st_mtime:
        BIN.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["swiftc", "-O", "-suppress-warnings", str(swift), "-o", str(BIN)], check=True)
    rows = json.loads(subprocess.run([str(BIN), str(path)], capture_output=True, text=True, check=True).stdout)
    w, h = size(path)
    sx, sy = 1080 / w, 1920 / h  # Vision reports the video's own pixels
    return [None if r is None else [r[0] * sx, r[1] * sy, r[2] * sx] for r in rows]


def size(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True).stdout.strip()
    return [int(v) for v in o.split(",")[:2]]


def smooth(pts):
    a = np.array([p if p else [np.nan] * 3 for p in pts], float)
    if not len(a) or np.isnan(a).all():
        return a
    idx = np.arange(len(a))
    for k in range(3):
        good = ~np.isnan(a[:, k])
        a[:, k] = np.interp(idx, idx[good], a[good, k])
        a[:, k] = np.convolve(np.pad(a[:, k], 6, mode="edge"), np.ones(13) / 13, mode="valid")
    return a


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder"); ap.add_argument("--only", default="")
    ap.add_argument("--method", default="auto", choices=["auto", "cv2", "vision"]); ap.add_argument("--check")
    a = ap.parse_args()
    root = pathlib.Path(a.folder).expanduser()
    if not root.is_absolute() and not root.exists():
        root = content_dir() / a.folder
    root = root.resolve()
    method = a.method
    if method == "auto":
        method = "cv2" if cascade_path() else "vision"
    fn = {"cv2": track_cv2, "vision": track_vision}[method]
    only = {s.strip() for s in a.only.split(",") if s.strip()} | ({a.check} if a.check else set())
    vids = [p for p in sorted((root / "norm").glob("*.mp4")) if not only or p.stem in only]
    if not vids:
        sys.exit("no clips in %s/norm (run normalize.py first)" % root)
    tj = root / "track.json"
    out = json.loads(tj.read_text()) if tj.exists() and not a.check else {}
    for p in vids:
        try:
            pts = fn(p)
        except Exception as e:
            sys.exit("face tracking (%s) failed: %s. Fix: use the plugin venv python (opencv-python-headless), or on macOS install Xcode command line tools (xcode-select --install) for --method vision." % (method, e))
        arr = smooth(pts); miss = sum(q is None for q in pts)
        if a.check:
            if miss == len(pts):
                print("%s: no face found in %d frames" % (p.stem, len(pts)))
            else:
                for lab, i in (("first", 0), ("mid", len(arr) // 2), ("last", len(arr) - 1)):
                    print("%s %s frame %d: x=%.0f y=%.0f w=%.0f" % (p.stem, lab, i, *arr[i]))
            continue
        out[p.stem] = np.round(arr, 1).tolist() if not np.isnan(arr).all() else [[None] * 3] * len(pts)
        mean = "none" if np.isnan(arr).all() else "mean x/y/w %s" % np.round(arr.mean(0)).astype(int).tolist()
        print("%s [%s]: %d frames, %d missing, %s" % (p.stem, method, len(pts), miss, mean))
        if miss == len(pts):
            print("  WARNING no face found: check the framing, or try --method vision")
    if not a.check:
        tj.write_text(json.dumps(out))
        print("wrote", tj)


if __name__ == "__main__":
    main()
