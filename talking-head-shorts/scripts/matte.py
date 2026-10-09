#!/usr/bin/env python3
"""Cut the person out of the ORIGINAL video with Robust Video Matting (ONNX): RGBA PNG frames at 30 fps.

  python -I matte.py <source video> <out dir> --start S --end E [--crop x,y,w,h] [--ratio 1.0] [--yes]

Frame i of <out dir> (f0000.png ...) is source time S + i/30. Writes <out dir>/matte.json
({"start","count","fps","ratio","blink_reused","dropout_fixed","dropout_held"}) next to the frames.

Model: --model, $THS_RVM, ~/.cache/talking-head-shorts/models/rvm_mobilenetv3_fp32.onnx
(PeterL1n/RobustVideoMatting v1.0.0, 14.98 MB, sha256 88d45312...2828). Getting it is a download: ask first.

Lessons baked in (each cost real time):
- Source videos can contain black "blink" frames. The brightness pre-pass uses <slug>/blink.json (probe.py): level < 0.93
  = blink. On a blink the last good cut-out (colour and alpha) is reused and the recurrent state is left alone; the
  Remotion template dips the WHOLE picture from blink.json. Look at the raw frame before blaming the model.
- The recurrent state's shape depends on downsample_ratio, so a ratio-1.0 state cannot feed a retry at 0.8: retries start
  from a zero state and the last good state carries on. Ratio 1.0 for ~480x850 sources (0.6 dropped the torso on fast hands).
- Dropout guard: alpha area < 92% of the 30-frame running median -> retry at 1.0, 0.8, 1.3, 0.6 from zero state; else hold
  the last alpha. On a repaired frame RVM's colour output is broken too, so source pixels are used.
- OpenCV: seek by frame index, land on an even source frame of a 60 fps clip to stay on the 30 fps grid, ~1 s lead-in.
- Matte every 2nd frame of a 60 fps source (Remotion composes at 30). PNGs are ~0.5 MB per frame at 478x850 (~400 MB / 27 s):
  the script prints the estimate and refuses to write more than 150 MB without --yes.
Run with the venv python and -I (it reads downloaded files).
"""
import argparse, json, os, pathlib, sys
import numpy as np, cv2
import onnxruntime as ort

DEFAULT_MODEL = pathlib.Path.home() / ".cache/talking-head-shorts/models/rvm_mobilenetv3_fp32.onnx"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source"); ap.add_argument("outdir")
    ap.add_argument("--start", type=float, required=True); ap.add_argument("--end", type=float, required=True)
    ap.add_argument("--crop"); ap.add_argument("--ratio", type=float, default=1.0)
    ap.add_argument("--warm", type=float, default=1.0, help="seconds of lead-in so the recurrent state settles")
    ap.add_argument("--blink", help="blink.json (default: next to the source)")
    ap.add_argument("--model"); ap.add_argument("--yes", action="store_true", help="accept a large disk estimate")
    a = ap.parse_args()
    src = pathlib.Path(a.source).expanduser()
    model = pathlib.Path(a.model or os.environ.get("THS_RVM") or DEFAULT_MODEL).expanduser()
    if not model.exists():
        sys.exit("RVM model not found at %s. It is a ~15 MB download: ask the user, then put it there." % model)
    crop = [int(v) for v in a.crop.split(",")] if a.crop else None

    cap = cv2.VideoCapture(str(src))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    W, H = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cw, ch = (crop[2], crop[3]) if crop else (W, H)
    step = int(round(fps / 30))
    n_est = int((a.end - a.start) * 30)
    mb = n_est * 0.5 * (cw * ch) / (478 * 850)
    print("matte: %.2f-%.2f s = %d frames at %dx%d, about %.0f MB of PNG in %s" % (a.start, a.end, n_est, cw, ch, mb, a.outdir))
    if mb > 150 and not a.yes:
        sys.exit("more than 150 MB: tell the user the estimate, then rerun with --yes")
    out = pathlib.Path(a.outdir).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    bj = pathlib.Path(a.blink) if a.blink else src.resolve().parent / "blink.json"
    bj = bj if bj.exists() else src.parent / "blink.json"
    grid = json.loads(bj.read_text())["values"] if bj.exists() else []
    level_at = lambda i: grid[i // step] if i // step < len(grid) else 1.0

    sess = ort.InferenceSession(str(model), providers=["CPUExecutionProvider"])
    idx0 = int(round(max(0.0, a.start - a.warm) * fps))
    idx0 -= idx0 % step
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx0)
    zero = lambda: [np.zeros((1, 1, 1, 1), dtype=np.float32) for _ in range(4)]
    rec = zero()
    areas, last_fgr, last_pha = [], None, None
    fixed = held = blinks = n_out = 0
    i, last = idx0, min(int(round(a.end * fps)), total)
    while i < last:
        ok, bgr = cap.read()
        if not ok:
            break
        if (i - idx0) % step == 0:
            if crop:
                bgr = bgr[crop[1]:crop[1] + crop[3], crop[0]:crop[0] + crop[2]]
            src_t = (cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0).transpose(2, 0, 1)[None]

            def run(state, r):
                o = sess.run(None, {"src": src_t, "r1i": state[0], "r2i": state[1], "r3i": state[2], "r4i": state[3],
                                    "downsample_ratio": np.array([r], dtype=np.float32)})
                return o[0], o[1], o[2:]

            if level_at(i) < 0.93 and last_pha is not None:
                fgr, pha = last_fgr, last_pha  # blink: reuse the last good cut-out, state untouched
                blinks += 1
            else:
                fgr, pha, new_rec = run(rec, a.ratio)
                med = np.median(areas[-30:]) if len(areas) >= 15 else None
                if med is not None and float(pha.mean()) < 0.92 * med:
                    for r in (1.0, 0.8, 1.3, 0.6):  # retry from a zero state: its shape follows the ratio
                        _, p2, _ = run(zero(), r)
                        if float(p2.mean()) >= 0.92 * med:
                            fgr, pha, new_rec = src_t, p2, rec  # RVM colour is broken on a repaired frame: source pixels
                            fixed += 1
                            break
                    else:
                        fgr, pha, new_rec = src_t, last_pha, rec
                        held += 1
                rec = new_rec
                areas.append(float(pha.mean()))
                last_fgr, last_pha = fgr, pha
            if i / fps >= a.start - 1e-6:
                rgba = np.concatenate([fgr[0].transpose(1, 2, 0), pha[0].transpose(1, 2, 0)], axis=2)
                o = cv2.cvtColor((np.clip(rgba, 0, 1) * 255).astype(np.uint8), cv2.COLOR_RGBA2BGRA)
                cv2.imwrite(str(out / ("f%04d.png" % n_out)), o, [cv2.IMWRITE_PNG_COMPRESSION, 3])
                n_out += 1
        i += 1
    i0 = int(np.ceil(a.start * fps - 1e-6))
    i0 += (-i0) % step  # the first frame written sits on the 30 fps grid
    meta = {"start": round(i0 / fps, 3), "count": n_out, "fps": 30, "ratio": a.ratio,
            "blink_reused": blinks, "dropout_fixed": fixed, "dropout_held": held, "crop": crop}
    json.dump(meta, open(out / "matte.json", "w"))
    print("frames written: %d -> %s | blink frames reused: %d | dropout retried-ok: %d, held: %d" % (n_out, out, blinks, fixed, held))
    print('spec.matte = {"dir": "%s", "start": %.3f, "count": %d}' % (out.name, meta["start"], n_out))


if __name__ == "__main__":
    main()
