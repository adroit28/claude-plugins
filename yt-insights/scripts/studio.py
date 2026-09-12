"""Import YouTube Studio CSV exports (Content tab → Export) into data/studio.json.
Usage: studio.py --project-dir <dir>
Reads every *.csv in <project>/yt-insights/studio/, matches rows to videos by the
'Content' column (video id), and keeps the metrics the API does not expose:
impressions, click-through rate, and the Shorts 'viewed vs swiped away' rate.
Column names vary by Studio locale and tab, so headers are matched fuzzily."""
import argparse, csv, json, os, re
from pathlib import Path

PATTERNS = {  # normalised header substring -> key
    "impressions click-through": "ctr", "click-through rate": "ctr", "ctr": "ctr",
    "shown in feed": "shown_in_feed", "impressions": "impressions",
    "viewed vs swiped": "stayed_pct", "stayed to watch": "stayed_pct", "swiped away": "swiped_pct",
    "average view duration": "studio_avd", "average percentage viewed": "studio_avp",
    "watch time (hours)": "watch_hours", "views": "studio_views", "subscribers": "studio_subs",
}
ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def norm(h): return re.sub(r"\s+", " ", h.strip().lower().replace("﻿", ""))


def num(x):
    if x in (None, "", "—", "-"): return None
    x = str(x).replace(",", "").replace("%", "").strip()
    try: return float(x)
    except ValueError: return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    a = ap.parse_args()
    root = Path(a.project_dir) / "yt-insights"
    files = sorted((root / "studio").glob("*.csv"), key=lambda p: p.stat().st_mtime)
    out, report = {}, []
    for f in files:
        with open(f, newline="", encoding="utf-8-sig") as fh:
            rows = list(csv.DictReader(fh))
        if not rows: report.append(f"{f.name}: empty"); continue
        headers = {norm(h): h for h in rows[0].keys() if h}
        colmap = {}
        for nh, orig in headers.items():
            for pat, key in PATTERNS.items():
                if pat in nh and key not in colmap.values():
                    colmap[orig] = key; break
        id_col = next((h for nh, h in headers.items() if nh == "content"), None)
        title_col = next((h for nh, h in headers.items() if "title" in nh), None)
        matched = 0
        for r in rows:
            vid = (r.get(id_col) or "").strip() if id_col else ""
            if not ID_RE.match(vid) or vid.lower() == "total": continue
            rec = out.setdefault(vid, {})
            for orig, key in colmap.items():
                v = num(r.get(orig))
                if v is not None: rec[key] = v
            if title_col and r.get(title_col): rec["studio_title"] = r[title_col]
            rec["source"] = f.name
            matched += 1
        report.append(f"{f.name}: {matched} videos, columns kept: {sorted(set(colmap.values())) or 'none recognised'}")
    (root / "data").mkdir(exist_ok=True)
    (root / "data" / "studio.json").write_text(json.dumps(out, indent=1))
    print("\n".join(report) if report else "no CSV files in yt-insights/studio/")
    print(f"studio.json: {len(out)} videos")


if __name__ == "__main__":
    main()
