#!/usr/bin/env python3
"""The mechanical half of a research sweep in one run: YouTube searches, momentum, URL verification.

  sweep.py --out shorts/briefs --date 2026-09-26 \\
           -q "ronaldo al nassr goal" -q "yamal skill" ... \\
           [--channel @premierleague ...] [--url https://youtu.be/... ...] [--details 6]

For every -q it runs two ytsearch.py searches (uploaded today and this week, Shorts length,
sorted by views), lists the latest uploads of each --channel, then runs a full
`yt-dlp -j` extract on the top --details rows per query and on every --url. That
extract is the verification: title, channel, verified badge, exact upload time, views,
likes and duration are copied from it; a row whose extract failed says `not verified`.

Per query it also marks the earliest upload (likely original) and counts how many
different channels uploaded it (reposts = momentum). The query text stands in for the
moment; the scout maps queries to moments and adds the origin class.

Writes <out>/candidates-<date>.json (every row) and <out>/videos-<date>.md (verified rows,
sorted by views/h, ready to paste into the sweep file), and prints the top 20.
Read-only: nothing is downloaded. Needs yt-dlp on PATH.
"""
import argparse, datetime as dt, json, os, re, shutil, sys
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ytsearch import search_url, ytdlp_flat, ytdlp_details, fmt_n

YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/)([\w-]{11})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--query", action="append", default=[], help="one per candidate moment (repeatable)")
    ap.add_argument("--channel", action="append", default=[], help="@handle of an official account that owns footage")
    ap.add_argument("--url", action="append", default=[], help="a YouTube URL found elsewhere (web search, Reddit) to verify")
    ap.add_argument("--out", required=True); ap.add_argument("--date", required=True, help="date tag YYYY-MM-DD")
    ap.add_argument("--limit", type=int, default=12, help="flat results per search")
    ap.add_argument("--details", type=int, default=6, help="full extract (= verification) for the top N per query")
    ap.add_argument("--no-week", action="store_true", help="skip the uploaded-this-week search")
    a = ap.parse_args()
    if not shutil.which("yt-dlp"): sys.exit("yt-dlp not found: brew install yt-dlp")
    if not (a.query or a.channel or a.url): ap.error("give -q, --channel or --url")
    os.makedirs(a.out, exist_ok=True)
    now = dt.datetime.now(dt.UTC)

    jobs = []
    for q in a.query:
        jobs.append((q, "day", search_url(q, sort="views", uploaded="day", short=True)))
        if not a.no_week: jobs.append((q, "week", search_url(q, sort="views", uploaded="week", short=True)))
    for c in a.channel:
        h = c if c.startswith("@") else "@" + c
        jobs.append(("channel:" + h, "latest", "https://www.youtube.com/%s/videos" % h))

    cands, log = {}, []
    with ThreadPoolExecutor(4) as ex:
        for (label, window, url), rows in zip(jobs, ex.map(lambda j: ytdlp_flat(j[2], a.limit), jobs)):
            log.append("%-44s %-6s %3d results" % (label[:44], window, len(rows)))
            for r in rows:
                c = cands.setdefault(r["id"], dict(r, found_by=[]))
                if label not in c["found_by"]: c["found_by"].append(label)
                c.setdefault("windows", set()).add(window)
    for u in a.url:
        m = YT_ID.search(u)
        if not m: log.append("skipped (not a YouTube URL, open it yourself): %s" % u); continue
        c = cands.setdefault(m.group(1), {"id": m.group(1), "title": None, "url": "https://www.youtube.com/watch?v=" + m.group(1),
                                          "channel": None, "views": None, "found_by": [], "windows": set()})
        c["found_by"].append("url")

    want = {c["id"] for c in cands.values() if "url" in c["found_by"]}
    for label in dict.fromkeys(c for c in (j[0] for j in jobs)):
        top = sorted((c for c in cands.values() if label in c["found_by"]), key=lambda c: -(c["views"] or 0))[: a.details]
        want.update(c["id"] for c in top)
    with ThreadPoolExecutor(6) as ex:
        for vid, det in zip(want, ex.map(ytdlp_details, want)):
            c = cands[vid]; c["verified_extract"] = bool(det.get("timestamp"))
            for k, v in det.items():
                if v is not None: c[k] = v
    for c in cands.values():
        c["windows"] = sorted(c.get("windows", []))
        if c.get("timestamp"):
            c["age_h"] = round((now.timestamp() - c["timestamp"]) / 3600, 1)
            c["views_per_h"] = round((c["views"] or 0) / max(c["age_h"], 0.5))

    # per query: how many channels uploaded it, and which upload came first
    for label in {l for c in cands.values() for l in c["found_by"]}:
        group = [c for c in cands.values() if label in c["found_by"]]
        chans = {c["channel"] for c in group if c.get("channel")}
        dated = [c for c in group if c.get("timestamp")]
        first = min(dated, key=lambda c: c["timestamp"])["id"] if dated else None
        for c in group:
            c["channels_for_query"] = max(c.get("channels_for_query", 0), len(chans))
            if c["id"] == first: c["earliest_for"] = c.get("earliest_for", []) + [label]

    ranked = sorted(cands.values(), key=lambda c: (-(c.get("views_per_h") or -1), -(c["views"] or 0)))
    json.dump({"searched_at_utc": now.isoformat(timespec="minutes"), "queries": a.query, "channels": a.channel,
               "log": log, "candidates": ranked}, open(os.path.join(a.out, "candidates-%s.json" % a.date), "w"),
              indent=1, ensure_ascii=False)

    hdr = ("| # | query (moment) | URL | channel | badge | verified? | uploaded UTC | age h | views | views/h | likes | len s | first? | channels |\n"
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n")
    rows = []
    for c in [c for c in ranked if c.get("verified_extract")]:
        q = next((l for l in c["found_by"] if l != "url"), "url")
        rows.append("| %d | %s | %s | %s | %s | yes (yt-dlp -j) | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            len(rows) + 1, q[:40], c["url"], re.sub(r"\|", "/", c.get("channel") or "?")[:28], "✓" if c.get("verified") else "",
            c.get("uploaded_utc"), c.get("age_h"), fmt_n(c.get("views")), fmt_n(c.get("views_per_h")), fmt_n(c.get("likes")),
            c.get("duration_s", "?"), "earliest" if c.get("earliest_for") else "later", c.get("channels_for_query", "?")))
    failed = [c for c in cands.values() if c["id"] in want and not c.get("verified_extract")]
    empty = [l for l in log if " 0 results" in l]
    md = ("Swept at %s UTC · %d queries · %d channels · %d URLs · %d unique videos, %d verified\n\n%s%s\n\n"
          "Not verified (extract failed): %s\n\nSearches with no results: %s\n" % (
              now.strftime("%Y-%m-%d %H:%M"), len(a.query), len(a.channel), len(a.url), len(cands), len(rows),
              hdr, "\n".join(rows), ", ".join(c["url"] for c in failed) or "none", "; ".join(empty) or "none"))
    open(os.path.join(a.out, "videos-%s.md" % a.date), "w").write(md)

    print("\n".join(log))
    print("\n%s%s" % (hdr, "\n".join(rows[:20])))
    print("\n%d unique videos, %d verified, %d extracts failed" % (len(cands), len(rows), len(failed)))
    print("wrote", os.path.join(a.out, "candidates-%s.json" % a.date), "and", os.path.join(a.out, "videos-%s.md" % a.date))


if __name__ == "__main__":
    main()
