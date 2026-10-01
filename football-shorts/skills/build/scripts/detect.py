#!/usr/bin/env python3
"""Player and ball tracks found by a detector, instead of a CSRT box or hand keys, for track.py render.

  detect.py <video> --from 25.78 --to 26.76 --box 1300,745,95,200 --out build/messi.json   player that overlaps --box
  detect.py <video> --from 25.78 --to 26.76 --out build/players.json                      every ID; look at the sheet, then
  detect.py <video> --from 25.78 --to 26.76 --id 3 --out build/messi.json                 ... pick one by number
  detect.py <video> --from 26.72 --to 29.6 --ball --out build/ball.json                   ball in flight
  detect.py <video> --from 26.72 --to 28.88 --auto --out build/flight.json                 where the play is (for reframe)
  detect.py <video> --from 5.8 --to 8.52 --auto --area 478,254,0,298 --upscale 2 --out build/g3.json   inside a picture box

Every frame of the window goes through RF-DETR Medium (Apache 2.0, COCO weights: person and sports ball);
people are linked into IDs by ByteTrack (roboflow/trackers, Apache 2.0). All IDs and every ball candidate go
to <out>.all.json, and <out>.ids.png shows the first and last frame with each ID boxed and numbered.
The written track file has the same shape as track.py's: {"fps", "points": [[t, cx, cy, w, h], ...]} in source
seconds and source pixels, so fx.json layers use it unchanged. Players keep gaps up to 0.5 s filled.

--ball starts from the most confident ball (or the one nearest --seed t,x,y) and walks forward and back,
taking each frame the candidate nearest to where the ball's velocity puts it; a candidate too far off is a
glove, a boot or an advertising board and is skipped, gaps up to 0.25 s are filled, and after 0.25 s with
no match the track ends instead of jumping to something else. Works on replay and close angles where the
ball is ~20 px or more (messi-fk-76 replay: 161/174 frames, 2-7 px from good hand keys). On a wide live
shot the ball is a few pixels and the track is not reliable: key it by hand with `track.py keys`.
Replays are often frame-doubled (two equal points in a row); velocity is taken over ~0.1 s so that is fine.

--auto writes the track a `"crop": {"reframe": ...}` window follows (render.py): per frame the ball when the
ball walk has it, else the dominant group of players (1-D mean-shift on person centres, bandwidth 25 % of the
width, weighted by box area, ties toward the ball's last side); w,h = the group's extent. A ball that never
moves and sits more than that bandwidth from the players (a spare by the touchline) is ignored. `--area` detects only
inside a picture box (letterboxed uploads) and `--upscale` enlarges it first (players there are ~20 px tall).
With detections in under 30 % of frames it prints LOOK and uses a frame-difference motion centroid instead, so
a track always exists. <out>.auto.png shows four frames with the chosen target boxed (ball yellow, players
cyan, motion magenta); look at it before rendering.

Needs its own venv (torch does not suit the shorts venv): `setup.sh --detect` prints PYD=. First run
downloads the weights (~130 MB, ~/.roboflow/models). About 25 frames/s on Apple silicon (MPS).
"""
import argparse, json, math, os, sys


def iou(a, b):
    ix = max(0, min(a[2], b[2]) - max(a[0], b[0])); iy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    u = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - ix * iy
    return ix * iy / u if u else 0

def fill_gaps(pts, fps, max_gap):
    """Linear points for missing frames in gaps up to max_gap seconds; longer gaps stay empty."""
    out = pts[:1]
    for p in pts[1:]:
        q = out[-1]; n = int(round((p[0] - q[0]) * fps))
        if 1 < n <= max_gap * fps:
            for k in range(1, n): out.append([round(q[0] + (p[0] - q[0]) * k / n, 4)] + [round(q[i] + (p[i] - q[i]) * k / n, 1) for i in range(1, 5)])
        out.append(p)
    return out

def ball_path(cands, fps, seed_t=None, seed_xy=None):
    """One ball through per-frame candidates [[t, cx, cy, w, h, conf], ...]. A candidate further than
    max(30 px, 1.5 ball sizes) + 10 px per missed frame from the prediction is skipped."""
    frames = {}
    for c in cands: frames.setdefault(c[0], []).append(c)
    ts = sorted(frames)
    if seed_xy: seed = min((c for c in cands if abs(c[0] - seed_t) < 1.5 / fps), key=lambda c: math.dist(c[1:3], seed_xy), default=None)
    else: seed = max(cands, key=lambda c: c[5], default=None)
    if not seed: return []
    def walk(order):
        path = [seed]
        for t in order:
            last = path[-1]; n = abs(t - last[0]) * fps
            if n > 0.25 * fps: break
            prev = next((q for q in reversed(path[:-1]) if abs(last[0] - q[0]) >= 0.09), path[0] if len(path) > 1 else None)
            if prev and prev[0] != last[0]:
                k = (t - last[0]) / (last[0] - prev[0]); px, py = last[1] + (last[1] - prev[1]) * k, last[2] + (last[2] - prev[2]) * k
            else: px, py = last[1], last[2]
            best = min(frames[t], key=lambda c: math.dist(c[1:3], (px, py)))
            if math.dist(best[1:3], (px, py)) <= max(30, 1.5 * max(last[3], last[4])) + 10 * max(0, n - 1): path.append(best)
        return path[1:]
    i = ts.index(seed[0])
    return sorted(walk(reversed(ts[:i])) + [seed] + walk(ts[i + 1:]))

def mean_shift(xs, ws, bw):
    """Mode of a weighted 1-D point set (flat kernel of half-width bw): [(mode, mass)], best first."""
    modes = []
    for x in xs:
        m = x
        for _ in range(30):
            near = [(xi, wi) for xi, wi in zip(xs, ws) if abs(xi - m) <= bw]
            nm = sum(xi * wi for xi, wi in near) / sum(wi for _, wi in near)
            if abs(nm - m) < 0.5: break
            m = nm
        if not any(abs(m - q) < bw / 4 for q, _ in modes): modes.append((m, sum(wi for xi, wi in zip(xs, ws) if abs(xi - m) <= bw)))
    return sorted(modes, key=lambda q: -q[1])

def motion_track(grabs, area, fps):
    """Frame-difference centroid per frame: where things move, when the detector sees nothing."""
    import cv2, numpy as np
    pts, prev = [], None
    x0, y0, aw, ah = area
    for t, fr in grabs:
        g = cv2.cvtColor(cv2.resize(fr[y0:y0 + ah, x0:x0 + aw], None, fx=0.25, fy=0.25), cv2.COLOR_BGR2GRAY)
        if prev is not None:
            d = cv2.GaussianBlur(cv2.absdiff(g, prev), (5, 5), 0); ys, xs = np.nonzero(d > 18)
            if len(xs) > 20:
                w = d[ys, xs].astype(float)
                pts.append([t, round(x0 + 4 * float((xs * w).sum() / w.sum()), 1), round(y0 + 4 * float((ys * w).sum() / w.sum()), 1),
                            round(aw * 0.3, 1), round(ah * 0.3, 1)])
        prev = g
    return pts

def auto(a, fps, n, ball, frame_people, grabs, base):
    import cv2, numpy as np
    H0, W0 = grabs[0][1].shape[:2]
    area = [int(v) for v in a.area.split(",")] if a.area else [W0, H0, 0, 0]
    aw, ah, ax, ay = area; bw = 0.25 * aw
    bp = ball_path(ball, fps) if ball and max(c[5] for c in ball) >= 0.3 else []
    if bp:  # a ball that never moves and sits away from the players is a spare by the touchline, not the play
        xs = sorted(p[1] for p in bp); allp = [q for ppl in frame_people.values() for q in ppl]
        if allp and xs[int(0.9 * (len(xs) - 1))] - xs[int(0.1 * (len(xs) - 1))] < 0.05 * aw:
            m = mean_shift([q[0] for q in allp], [q[2] * q[3] for q in allp], bw)[0][0]
            if abs(xs[len(xs) // 2] - m) > bw:
                print("ignored a static ball at x %d (players at x %d): spare ball" % (xs[len(xs) // 2], m)); bp = []
    bpts = {p[0]: p[:5] for p in fill_gaps([p[:5] for p in bp], fps, 0.25)} if bp else {}
    pts, kinds, last_ball_x = [], [], None
    for t, _ in grabs:
        if t in bpts:
            pts.append(bpts[t]); kinds.append("ball"); last_ball_x = bpts[t][1]; continue
        ppl = frame_people.get(t) or []
        if not ppl: continue
        modes = mean_shift([p[0] for p in ppl], [p[2] * p[3] for p in ppl], bw)
        m = modes[0][0]
        if len(modes) > 1 and modes[1][1] > 0.9 * modes[0][1] and last_ball_x is not None:
            m = min(modes[:2], key=lambda q: abs(q[0] - last_ball_x))[0]
        mem = [p for p in ppl if abs(p[0] - m) <= bw]
        x0 = min(p[0] - p[2] / 2 for p in mem); x1 = max(p[0] + p[2] / 2 for p in mem)
        y0 = min(p[1] - p[3] / 2 for p in mem); y1 = max(p[1] + p[3] / 2 for p in mem)
        pts.append([t, round(m, 1), round((y0 + y1) / 2, 1), round(x1 - x0, 1), round(y1 - y0, 1)]); kinds.append("players")
    if len(pts) < 0.3 * n:
        print("LOOK: sparse detections (%d of %d frames); using the motion centroid instead" % (len(pts), n))
        pts = motion_track(grabs, area, fps); kinds = ["motion"] * len(pts)
    if not pts: sys.exit("nothing detected and no motion in %.2f-%.2f; use a fixed crop" % (a.t0, a.t1))
    json.dump({"video": a.video, "fps": fps, "mode": "auto", "area": area, "points": pts, "kinds": kinds}, open(a.out, "w"))
    nb = kinds.count("ball"); npl = kinds.count("players")
    print("auto: %d of %d frames (ball %d, players %d, motion %d), %.2f-%.2f -> %s" % (len(pts), n, nb, npl, kinds.count("motion"), pts[0][0], pts[-1][0], a.out))
    col = {"ball": (0, 212, 255), "players": (255, 220, 60), "motion": (255, 60, 255)}
    by_t = {p[0]: (p, k) for p, k in zip(pts, kinds)}; tiles = []
    for t, fr in [grabs[int(i)] for i in np.linspace(0, len(grabs) - 1, 4)]:
        im = fr.copy(); hit = by_t.get(t)
        if hit:
            (_, cx, cy, w, h), k = hit; w, h = max(w, 24), max(h, 24)
            cv2.rectangle(im, (int(cx - w / 2), int(cy - h / 2)), (int(cx + w / 2), int(cy + h / 2)), col[k], 4)
            cv2.line(im, (int(cx), 0), (int(cx), im.shape[0]), col[k], 2)
        cv2.putText(im, "%.2fs %s" % (t, hit[1] if hit else "-"), (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3)
        tiles.append(cv2.resize(im, (960, int(960 * im.shape[0] / im.shape[1]))))
    cv2.imwrite(base + ".auto.png", np.vstack([np.hstack(tiles[:2]), np.hstack(tiles[2:])]))
    print("look at %s.auto.png" % base)

def run(a):
    import cv2, numpy as np
    from rfdetr import RFDETRMedium
    from trackers import ByteTrackTracker
    model = RFDETRMedium(); PERSON, BALL = 1, 37  # COCO ids in rfdetr's class map
    cap = cv2.VideoCapture(a.video); fps = cap.get(cv2.CAP_PROP_FPS); cap.set(cv2.CAP_PROP_POS_MSEC, a.t0 * 1000)
    tracker = ByteTrackTracker(frame_rate=fps, lost_track_buffer=int(fps), track_activation_threshold=0.4)
    box4 = lambda x0, y0, x1, y1: [round(float(v), 1) for v in ((x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0)]
    ax, ay = 0, 0; up = a.upscale if a.auto else 1
    if a.area: aw, ah, ax, ay = [int(v) for v in a.area.split(",")]
    people, ball, frame_people, grabs, first, last, n = {}, [], {}, [], None, None, 0
    while True:
        ok, frame = cap.read()
        if not ok: break
        t = round(cap.get(cv2.CAP_PROP_POS_MSEC) / 1000 - 1 / fps, 4)
        if t > a.t1 + 1e-6: break
        img = frame[ay:ay + ah, ax:ax + aw] if a.area else frame
        if up != 1: img = cv2.resize(img, None, fx=up, fy=up, interpolation=cv2.INTER_CUBIC)
        det = model.predict(img[:, :, ::-1].copy(), threshold=a.threshold); n += 1
        if len(det): det.xyxy = det.xyxy / up + np.array([ax, ay, ax, ay])
        if a.auto:
            pdet = det[(det.class_id == PERSON) & (det.confidence >= 0.3)]
            frame_people[t] = [box4(*xyxy) for xyxy in pdet.xyxy]
            grabs.append((t, frame))
        pd = tracker.update(det[det.class_id == PERSON])
        for xyxy, tid in zip(pd.xyxy, pd.tracker_id):
            if tid >= 0: people.setdefault(int(tid), []).append([t] + box4(*xyxy))
        bd = det[det.class_id == BALL]
        for xyxy, cf in zip(bd.xyxy, bd.confidence): ball.append([t] + box4(*xyxy) + [round(float(cf), 3)])
        if first is None: first = frame.copy()
        last = frame
    if first is None: sys.exit("cannot read %s at %s" % (a.video, a.t0))
    people = {k: pts for k, pts in people.items() if len(pts) >= 3}
    base = os.path.splitext(a.out)[0]
    json.dump({"video": a.video, "fps": fps, "from": a.t0, "to": a.t1, "people": people, "ball": ball}, open(base + ".all.json", "w"))
    tiles = []
    for fr, pick in ((first, 0), (last, -1)):
        im = fr.copy()
        for k, pts in people.items():
            _, cx, cy, w, h = pts[pick]
            cv2.rectangle(im, (int(cx - w / 2), int(cy - h / 2)), (int(cx + w / 2), int(cy + h / 2)), (0, 212, 255), 2)
            cv2.putText(im, str(k), (int(cx - w / 2), int(cy - h / 2) - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 212, 255), 2)
        tiles.append(cv2.resize(im, (960, int(960 * im.shape[0] / im.shape[1]))))
    cv2.imwrite(base + ".ids.png", np.hstack(tiles))
    print("%d frames, %d person IDs, ball candidates in %d frames -> %s.all.json, %s.ids.png" % (n, len(people), len(set(b[0] for b in ball)), base, base))
    if a.auto: return auto(a, fps, n, ball, frame_people, grabs, base)
    if a.ball:
        seed = [float(v) for v in a.seed.split(",")] if a.seed else None
        path = ball_path(ball, fps, *((seed[0], seed[1:3]) if seed else (None, None)))
        if not path: sys.exit("no ball detected; key it by hand with `track.py keys`")
        pts = fill_gaps([p[:5] for p in path], fps, 0.25)
        json.dump({"video": a.video, "fps": fps, "mode": "detect-ball", "points": pts}, open(a.out, "w"))
        print("ball: %d of %d frames detected, %d after filling gaps, %.2f-%.2f -> %s" % (len(path), n, len(pts), pts[0][0], pts[-1][0], a.out))
        if len(pts) < 0.6 * n: print("LOOK: ball found in under 60%% of the window; check %s against a frames sheet or key it by hand" % a.out)
        return
    pick = a.id
    if pick is None and a.box:
        x, y, w, h = [float(v) for v in a.box.split(",")]; ref = (x, y, x + w, y + h)
        score = lambda pts: max((iou(ref, (p[1] - p[3] / 2, p[2] - p[4] / 2, p[1] + p[3] / 2, p[2] + p[4] / 2)) for p in pts if p[0] <= a.t0 + 0.2), default=0)
        pick, best = max(((k, score(v)) for k, v in people.items()), key=lambda kv: kv[1], default=(None, 0))
        if best < 0.3: sys.exit("no ID overlaps --box at --from (best IoU %.2f); look at %s.ids.png and pass --id" % (best, base))
        print("--box matched ID %d (IoU %.2f)" % (pick, best))
    if pick is None: print("look at %s.ids.png and rerun with --id N (or --box) to write %s" % (base, a.out)); return
    if pick not in people: sys.exit("no ID %d; IDs: %s" % (pick, " ".join(map(str, sorted(people)))))
    pts = fill_gaps(people[pick], fps, 0.5)
    json.dump({"video": a.video, "fps": fps, "mode": "detect", "id": pick, "points": pts}, open(a.out, "w"))
    print("ID %d: %d points %.2f-%.2f -> %s" % (pick, len(pts), pts[0][0], pts[-1][0], a.out))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video"); ap.add_argument("--from", dest="t0", type=float, required=True); ap.add_argument("--to", dest="t1", type=float, required=True)
    ap.add_argument("--box", help="x,y,w,h source px at --from: write the ID that overlaps it")
    ap.add_argument("--id", type=int, help="write this ID (numbers are on <out>.ids.png)")
    ap.add_argument("--ball", action="store_true", help="write the ball track instead of a player")
    ap.add_argument("--seed", help="ball only: t,x,y of a frame where the ball is clear (default: most confident detection)")
    ap.add_argument("--auto", action="store_true", help="ball when found, else the main group of players: the track a reframe crop follows")
    ap.add_argument("--area", help="w,h,x,y source px: detect only inside this picture box (same order as fill.box)")
    ap.add_argument("--upscale", type=float, default=1, help="auto: enlarge the --area picture this much before detection")
    ap.add_argument("--threshold", type=float, default=0.15, help="detection confidence (low on purpose: the ball walk rejects strays)")
    ap.add_argument("--out", required=True)
    run(ap.parse_args())

if __name__ == "__main__":
    main()
