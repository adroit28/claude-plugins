"""Helpers around the YouTube Studio CSV export, which no API exposes.

Usage:
  studio_export.py check  --project-dir <dir>   # is the signed-in Chrome reachable? prints READY / NOT_READY
  studio_export.py url    --project-dir <dir> [--period week|4_week|4_weeks]   # Advanced-mode URL to open
  studio_export.py ingest --project-dir <dir> [--max-age-min 30]   # newest Studio zip in ~/Downloads -> studio/*.csv -> studio.py

The export itself is a browser action (Export current view -> CSV) done with the
`chrome-studio` MCP tools, which attach to the user's own signed-in Chrome. The
isolated `chrome-devtools` browser cannot sign in to Google, so never use it here.
"""
import argparse, glob, json, os, subprocess, sys, time, zipfile
from pathlib import Path

REMOTE_DEBUG_HELP = ("Chrome remote debugging is off. In Chrome open chrome://inspect/#remote-debugging, "
                     "turn on 'Allow remote debugging', then restart the Claude Code session so the "
                     "chrome-studio tool can attach.")


def chrome_port_file():
    return Path.home() / "Library/Application Support/Google/Chrome/DevToolsActivePort"


def cmd_check(_):
    f = chrome_port_file()
    if f.exists():
        print(f"READY port={f.read_text().splitlines()[0]} (real Chrome, remote debugging on)")
        return 0
    print("NOT_READY " + REMOTE_DEBUG_HELP)
    return 1


def cmd_url(a):
    ch = json.load(open(Path(a.project_dir) / "yt-insights/data/channel.json"))
    cid = ch["id"]
    period = {"week": "week", "4_week": "4_week", "4_weeks": "4_week"}.get(a.period, "week")
    metrics = ["EXTERNAL_VIEWS", "ENGAGED_VIEWS", "SHORTS_FEED_IMPRESSIONS_VTR", "VIDEO_THUMBNAIL_IMPRESSIONS",
               "VIDEO_THUMBNAIL_IMPRESSIONS_VTR", "AVERAGE_WATCH_TIME", "AVERAGE_WATCH_PERCENTAGE",
               "EXTERNAL_WATCH_TIME", "SUBSCRIBERS_NET_CHANGE"]
    q = (f"entity_type=CHANNEL&entity_id={cid}&ur_dimensions=CREATOR_CONTENT_TYPE&ur_values=%27SHORTS%27"
         f"&ur_inclusive_starts=&ur_exclusive_ends=&time_period={period}&explore_type=TABLE_AND_CHART"
         f"&metric=EXTERNAL_VIEWS&granularity=DAY&" + "&".join(f"t_metrics={m}" for m in metrics) +
         "&dimension=VIDEO&o_column=EXTERNAL_VIEWS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC")
    print(f"https://studio.youtube.com/channel/{cid}/analytics/tab-content/period-{period}/explore?{q}")
    return 0


def cmd_ingest(a):
    root = Path(a.project_dir) / "yt-insights"
    studio = root / "studio"; studio.mkdir(exist_ok=True)
    zips = sorted(glob.glob(str(Path.home() / "Downloads" / "Content *.zip")), key=os.path.getmtime, reverse=True)
    zips = [z for z in zips if time.time() - os.path.getmtime(z) < a.max_age_min * 60]
    if not zips:
        print(f"NO_EXPORT no 'Content *.zip' in ~/Downloads newer than {a.max_age_min} min"); return 1
    z = zips[0]
    # "Content 2026-09-10_2026-09-17 The Football Adda.zip" -> content-2026-09-10_2026-09-17.csv
    stem = Path(z).stem.split(" ")
    dates = stem[1] if len(stem) > 1 else time.strftime("%Y-%m-%d")
    dest = studio / f"content-{dates}.csv"
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        table = next((n for n in names if n.lower().startswith("table")), None)
        if not table:
            print(f"BAD_ZIP no Table data.csv in {z}: {names}"); return 1
        dest.write_bytes(zf.read(table))
        totals = next((n for n in names if n.lower().startswith("totals")), None)
        if totals:
            print("daily totals:\n" + zf.read(totals).decode("utf-8-sig").strip())
    print(f"wrote {dest.relative_to(Path(a.project_dir))} from {Path(z).name}")
    py = root / ".venv/bin/python"
    r = subprocess.run([str(py), str(Path(__file__).with_name("studio.py")), "--project-dir", a.project_dir])
    return r.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["check", "url", "ingest"])
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--period", default="week")
    ap.add_argument("--max-age-min", type=int, default=30)
    a = ap.parse_args()
    sys.exit({"check": cmd_check, "url": cmd_url, "ingest": cmd_ingest}[a.cmd](a))


if __name__ == "__main__":
    main()
