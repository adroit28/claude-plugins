#!/usr/bin/env python3
"""The edge-check sheet: STOP and show this to the user before the background swap goes on.

  python -I edge_sheet.py <matte dir> <out.png> [--bg image] [--source video --start S] [--times 0.5 2 3.5 4.8]

Row 1  four full frames composited over the (blurred, darkened) new background, as the video will look.
Row 2  3x crops of the hair line over pure green (a green fringe or a hard cut shows here).
Row 3  3x crops of the hands (the fastest-moving, hardest part) over green.
Frame times are seconds into the matte folder. The crops follow the alpha: hair = the top of the body's
bounding box, hands = the two outer lower thirds.
"""
import argparse, json, pathlib
import cv2, numpy as np


def comp(rgba, bg):
    a = rgba[..., 3:4].astype(np.float32) / 255
    return (rgba[..., :3] * a + bg * (1 - a)).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matte"); ap.add_argument("out"); ap.add_argument("--bg"); ap.add_argument("--times", type=float, nargs="*")
    a = ap.parse_args()
    d = pathlib.Path(a.matte)
    meta = json.loads((d / "matte.json").read_text()) if (d / "matte.json").exists() else {"count": len(list(d.glob("f*.png")))}
    n = meta["count"]
    times = a.times or [n / 30 * k for k in (0.1, 0.35, 0.6, 0.9)]
    first = cv2.imread(str(d / "f0000.png"), cv2.IMREAD_UNCHANGED)
    h, w = first.shape[:2]
    if a.bg:
        bg = cv2.imread(a.bg)
        k = max(w / bg.shape[1], h / bg.shape[0])
        bg = cv2.resize(bg, (int(bg.shape[1] * k) + 1, int(bg.shape[0] * k) + 1), interpolation=cv2.INTER_CUBIC)[:h, :w]
        bg = (cv2.GaussianBlur(bg, (0, 0), 6) * 0.62).astype(np.uint8)
    else:
        bg = np.full((h, w, 3), (40, 40, 40), np.uint8)
    green = np.zeros((h, w, 3), np.uint8); green[:] = (0, 200, 0)
    full, hair, hands = [], [], []
    for t in times:
        f = cv2.imread(str(d / ("f%04d.png" % min(n - 1, int(round(t * 30))))), cv2.IMREAD_UNCHANGED)
        al = f[..., 3]
        ys, xs = np.where(al > 128)
        full.append(cv2.putText(comp(f, bg.astype(np.float32)), "%.2fs" % t, (8, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2))
        if len(ys) == 0:
            hair.append(green.copy()); hands.append(green.copy()); continue
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        bh, bw = y1 - y0, x1 - x0
        cx = (x0 + x1) // 2
        hc = comp(f, green.astype(np.float32))
        hair.append(hc[max(0, y0 - 10):y0 + int(bh * 0.22), max(0, cx - int(bw * 0.3)):cx + int(bw * 0.3)])
        # hands: the lower-left and lower-right of the body box
        lo = slice(y0 + int(bh * 0.45), y1)
        hands.append(np.hstack([cv2.resize(hc[lo, x0:x0 + int(bw * 0.35)], (200, 300)), cv2.resize(hc[lo, x1 - int(bw * 0.35):x1], (200, 300))]))
    cw = full[0].shape[1]
    row1 = np.hstack(full)
    def tiles(imgs, size):
        t = [cv2.resize(i, size, interpolation=cv2.INTER_CUBIC) for i in imgs]
        return np.hstack(t)
    tw = row1.shape[1] // len(times)
    row2 = tiles(hair, (tw, int(tw * 0.55)))
    row3 = tiles(hands, (tw, int(tw * 0.75)))
    sheet = np.vstack([row1, row2, row3])
    cv2.imwrite(a.out, sheet)
    print("wrote", a.out, sheet.shape[1], "x", sheet.shape[0], "| rows: full frames over bg / hair x3 over green / hands x3 over green")


if __name__ == "__main__":
    main()
