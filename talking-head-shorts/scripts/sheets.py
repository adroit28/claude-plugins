#!/usr/bin/env python3
"""Labelled contact sheets and before/after frames (Pillow + OpenCV only).

  sheets.py grid   <video> <out.png> [--n 12] [--start S --end E] [--cols 6]    evenly spaced frames, time-labelled
  sheets.py at     <video> <out.png> --at 1.2 3.4 7.0 [--cols 6]                chosen seconds
  sheets.py compare <new.mp4> <out.png> --ref <old.mp4> --at 3.0 9.1            same seconds, old on top, new below
  sheets.py strip  <video> <out.png> --start S --end E [--n 8]                  frames around a moment

Times are seconds in the given video (output seconds). Frames land by index, never by milliseconds.
"""
import argparse, sys
import cv2, numpy as np


def grab(path, t):
    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, min(n - 1, int(round(t * fps)))))
    ok, f = cap.read()
    cap.release()
    return f if ok else np.zeros((640, 360, 3), np.uint8)


def duration(path):
    cap = cv2.VideoCapture(path)
    d = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30)
    cap.release()
    return d


def tile(f, label, h=480):
    f = cv2.resize(f, (int(f.shape[1] * h / f.shape[0]), h), interpolation=cv2.INTER_AREA)
    cv2.rectangle(f, (0, 0), (f.shape[1], 26), (0, 0, 0), -1)
    cv2.putText(f, label, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1, cv2.LINE_AA)
    return f


def sheet(tiles, cols):
    rows = []
    for i in range(0, len(tiles), cols):
        r = tiles[i:i + cols]
        while len(r) < cols:
            r.append(np.zeros_like(tiles[0]))
        rows.append(np.hstack(r))
    return np.vstack(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["grid", "at", "compare", "strip"]); ap.add_argument("video"); ap.add_argument("out")
    ap.add_argument("--n", type=int, default=12); ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--start", type=float, default=0.0); ap.add_argument("--end", type=float)
    ap.add_argument("--at", type=float, nargs="*"); ap.add_argument("--ref"); ap.add_argument("--h", type=int, default=480)
    a = ap.parse_args()
    if a.mode in ("grid", "strip"):
        end = a.end or duration(a.video)
        ts = [a.start + (end - a.start) * (i + 0.5) / a.n for i in range(a.n)]
        cols = a.cols if a.mode == "grid" else min(a.n, 8)
        img = sheet([tile(grab(a.video, t), "%.2fs" % t, a.h) for t in ts], cols)
    elif a.mode == "at":
        img = sheet([tile(grab(a.video, t), "%.2fs" % t, a.h) for t in a.at], a.cols)
    else:
        if not a.ref:
            sys.exit("compare needs --ref <old.mp4>")
        old = [tile(grab(a.ref, t), "before %.2fs" % t, a.h) for t in a.at]
        new = [tile(grab(a.video, t), "after %.2fs" % t, a.h) for t in a.at]
        img = np.vstack([np.hstack(old), np.hstack(new)])
    cv2.imwrite(a.out, img)
    print("wrote", a.out, img.shape[1], "x", img.shape[0])


if __name__ == "__main__":
    main()
