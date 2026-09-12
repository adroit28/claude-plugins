"""Register and score paired upload experiments.
Usage:
  experiments.py --project-dir <dir> add --name "<name>" --question "<q>" --arm <video_id>=<label> --arm <video_id>=<label> [--rule 2.0] [--read-after YYYY-MM-DD]
  experiments.py --project-dir <dir> score            # prints a table for every experiment, writes results back
  experiments.py --project-dir <dir> list
Scoring uses lifetime views normalised to views-per-day-live from data/videos.json, plus retention. A
ratio between the best and worst arm below --rule (default 2.0) is reported as noise."""
import argparse, json, os, re
from datetime import date, datetime, timezone
from pathlib import Path


def load(p): return json.load(open(p)) if p.exists() else []


def iso_secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d); h, mi, s = (int(x or 0) for x in m.groups()); return h * 3600 + mi * 60 + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("add"); a_.add_argument("--name", required=True); a_.add_argument("--question", required=True)
    a_.add_argument("--arm", action="append", required=True, help="video_id=label"); a_.add_argument("--rule", type=float, default=2.0); a_.add_argument("--read-after")
    sub.add_parser("score"); sub.add_parser("list")
    a = ap.parse_args()
    root = Path(a.project_dir) / "yt-insights"; path = root / "experiments.json"
    exps = load(path)

    if a.cmd == "add":
        arms = []
        for arm in a.arm:
            vid, _, label = arm.partition("=")
            arms.append({"video_id": vid.strip(), "label": label.strip() or vid.strip()})
        exps.append({"id": f"exp-{len(exps)+1:02d}", "name": a.name, "question": a.question, "created": date.today().isoformat(),
                     "read_after": a.read_after, "rule_ratio": a.rule, "arms": arms, "status": "open", "result": None})
        path.write_text(json.dumps(exps, indent=1)); print(f"registered {exps[-1]['id']}: {a.name} ({len(arms)} arms)"); return

    score_all(exps, root, write=(a.cmd == "score"))
    for e in exps:
        print(f"\n{e['id']}  {e['name']}  [{e['status']}]  rule ≥{e['rule_ratio']}x\n  Q: {e['question']}")
        for r in e["scored"]:
            print(f"  - {r['label']:<22} " + (f"{r['views']:>6} views  {r['views_per_day']:>7}/day  ret {r['retention']:>5.1f}%  {r['secs']}s  live {r['days_live']}d" if r["live"] else "not live yet"))
        print(f"  → {e['result']['verdict']}" + (f": {e['result']['best']} over {e['result']['worst']} by {e['result']['ratio']}x" if "ratio" in e["result"] else ""))
    if not exps: print("no experiments registered")


def score_all(exps, root, write=False):
    """Attach 'scored' rows and a 'result' to every experiment. Returns exps."""
    path = root / "experiments.json"
    videos = {v["id"]: v for v in load(root / "data" / "videos.json")}
    now = datetime.now(timezone.utc)
    for e in exps:
        rows = []
        for arm in e["arms"]:
            v = videos.get(arm["video_id"])
            if not v or v["privacy"] != "public" or not v.get("analytics_lifetime"):
                rows.append({**arm, "live": False}); continue
            L = v["analytics_lifetime"]; pub = datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00"))
            days = max((now - pub).total_seconds() / 86400, 0.25)
            rows.append({**arm, "live": True, "title": v["title"], "secs": iso_secs(v["duration"]), "published": v["publishedAt"][:16],
                         "days_live": round(days, 1), "views": L.get("views", 0), "views_per_day": round(L.get("views", 0) / days, 1),
                         "retention": L.get("averageViewPercentage", 0), "likes": L.get("likes", 0), "subs": L.get("subscribersGained", 0) - L.get("subscribersLost", 0)})
        e["scored"] = rows
        live = [r for r in rows if r["live"]]
        if len(live) == len(rows) and live:
            best, worst = max(live, key=lambda r: r["views_per_day"]), min(live, key=lambda r: r["views_per_day"])
            ratio = best["views_per_day"] / max(worst["views_per_day"], 0.1)
            too_early = e.get("read_after") and date.today().isoformat() < e["read_after"]
            verdict = "too early" if too_early else ("signal" if ratio >= e["rule_ratio"] else "noise")
            e["result"] = {"scored_on": date.today().isoformat(), "best": best["label"], "worst": worst["label"], "ratio": round(ratio, 2), "verdict": verdict}
            if write and not too_early: e["status"] = "read"
        else:
            e["result"] = {"scored_on": date.today().isoformat(), "verdict": "waiting: " + ", ".join(r["label"] for r in rows if not r["live"]) + " not live yet"}
    if write: path.write_text(json.dumps(exps, indent=1))
    return exps


if __name__ == "__main__":
    main()
