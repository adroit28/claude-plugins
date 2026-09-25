#!/usr/bin/env python3
"""Search YouTube for fresh football moments and rank them by view velocity.

Uses yt-dlp (no API key) against YouTube's own results page with the same `sp`
filter the site UI uses, so "uploaded today, sorted by views, under 4 minutes"
is a real server-side filter, not a guess. Flat results carry views/duration/
channel; the top few per query get a full extract so we know the exact upload
time and can compute views per hour.

Examples
  ytsearch.py -q "ronaldo wales offside" -q "haaland" --uploaded day --sort views --short
  ytsearch.py -q "premier league" --uploaded week --sort date --limit 25 --details 0
  ytsearch.py --channel @SonyLIV --channel @premierleague --limit 15
  ytsearch.py -q "vinicius" --uploaded day --json out/candidates.json --md out/candidates.md

Needs: yt-dlp on PATH (brew install yt-dlp). Read-only: nothing is downloaded.
"""
import argparse, base64, datetime as dt, json, re, shutil, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor

SORT = {"relevance": 0, "rating": 1, "date": 2, "views": 3}
UPLOADED = {"hour": 1, "day": 2, "week": 3, "month": 4, "year": 5}
DURATION = {"short": 1, "long": 2, "medium": 3}          # short = under 4 min

def _varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F; n >>= 7
        if n: out.append(b | 0x80)
        else: out.append(b); return bytes(out)

def _field(num, val): return _varint((num << 3) | 0) + _varint(val)
def _msg(num, payload): return _varint((num << 3) | 2) + _varint(len(payload)) + payload

def sp_param(sort="views", uploaded=None, short=False, video_only=True):
    """Build YouTube's search filter token. Decodes back to the UI's own values."""
    body = _field(1, SORT[sort]) if SORT[sort] else b""
    filt = b""
    if uploaded: filt += _field(1, UPLOADED[uploaded])
    if video_only: filt += _field(2, 1)
    if short: filt += _field(3, DURATION["short"])
    if filt: body += _msg(2, filt)
    return urllib.parse.quote(base64.b64encode(body).decode(), safe="")

def search_url(query, **kw):
    return "https://www.youtube.com/results?search_query=%s&sp=%s" % (
        urllib.parse.quote_plus(query), sp_param(**kw))

def ytdlp_flat(url, limit):
    cmd = ["yt-dlp", "--flat-playlist", "-j", "--playlist-end", str(limit), "--no-warnings", url]
    p = subprocess.run(cmd, capture_output=True, text=True)
    rows = []
    for line in p.stdout.splitlines():
        try: d = json.loads(line)
        except Exception: continue
        if d.get("live_status") in ("is_live", "is_upcoming"): continue
        rows.append({
            "id": d.get("id"), "title": d.get("title"), "url": d.get("url") or "https://www.youtube.com/watch?v=" + d["id"],
            "channel": d.get("channel") or d.get("uploader"), "verified": bool(d.get("channel_is_verified")),
            "views": d.get("view_count"), "duration_s": d.get("duration"),
        })
    if p.returncode and not rows:
        sys.stderr.write("yt-dlp failed for %s\n%s\n" % (url, p.stderr[-400:]))
    return rows

def ytdlp_details(video_id):
    p = subprocess.run(["yt-dlp", "-j", "--no-playlist", "--no-warnings",
                        "https://www.youtube.com/watch?v=" + video_id], capture_output=True, text=True)
    try: d = json.loads(p.stdout)
    except Exception: return {}
    ts = d.get("timestamp") or d.get("release_timestamp")
    return {"uploaded_utc": dt.datetime.fromtimestamp(ts, dt.UTC).strftime("%Y-%m-%d %H:%M") if ts else None,
            "timestamp": ts, "likes": d.get("like_count"), "comments": d.get("comment_count"),
            "views": d.get("view_count") or None, "duration_s": d.get("duration"),
            "verified": bool(d.get("channel_is_verified")), "width": d.get("width"), "height": d.get("height"),
            "description_head": (d.get("description") or "")[:200].replace("\n", " ")}

def fmt_n(n):
    if n is None: return "?"
    if n >= 1_000_000: return "%.1fM" % (n / 1e6)
    if n >= 1_000: return "%.0fk" % (n / 1e3)
    return str(n)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-q", "--query", action="append", default=[], help="search query (repeatable)")
    ap.add_argument("--channel", action="append", default=[], help="@handle or channel URL: list its latest uploads")
    ap.add_argument("--sort", choices=SORT, default="views")
    ap.add_argument("--uploaded", choices=UPLOADED, default=None, help="upload window filter")
    ap.add_argument("--short", action="store_true", help="under 4 minutes only")
    ap.add_argument("--limit", type=int, default=15, help="flat results per query")
    ap.add_argument("--details", type=int, default=6, help="full extract for the top N per query (upload time, likes)")
    ap.add_argument("--min-views", type=int, default=0)
    ap.add_argument("--json", help="write candidates JSON here")
    ap.add_argument("--md", help="write a markdown table here")
    a = ap.parse_args()
    if not shutil.which("yt-dlp"): sys.exit("yt-dlp not found: brew install yt-dlp")
    if not a.query and not a.channel: ap.error("give at least one -q or --channel")

    now = dt.datetime.now(dt.UTC)
    cands, seen = {}, set()
    jobs = [(q, search_url(q, sort=a.sort, uploaded=a.uploaded, short=a.short)) for q in a.query]
    for c in a.channel:
        u = c if c.startswith("http") else "https://www.youtube.com/%s/videos" % (c if c.startswith("@") else "@" + c)
        jobs.append(("channel:" + c, u))
    for label, url in jobs:
        rows = ytdlp_flat(url, a.limit)
        sys.stderr.write("%-40s %3d results  %s\n" % (label[:40], len(rows), url))
        for r in rows:
            if (r["views"] or 0) < a.min_views: continue
            r.setdefault("found_by", []).append(label)
            if r["id"] in cands: cands[r["id"]]["found_by"].append(label); continue
            cands[r["id"]] = r
    # details for the top N per query by views
    want = set()
    for label, _ in jobs:
        top = sorted([c for c in cands.values() if label in c["found_by"]], key=lambda c: -(c["views"] or 0))[: a.details]
        want.update(c["id"] for c in top)
    if want:
        with ThreadPoolExecutor(4) as ex:
            for vid, det in zip(want, ex.map(ytdlp_details, want)):
                for k, v in det.items():
                    if v is not None: cands[vid][k] = v
    for c in cands.values():
        if c.get("timestamp"):
            c["age_h"] = round((now.timestamp() - c["timestamp"]) / 3600, 1)
            c["views_per_h"] = round((c["views"] or 0) / max(c["age_h"], 0.5))
    ranked = sorted(cands.values(), key=lambda c: (-(c.get("views_per_h") or -1), -(c["views"] or 0)))

    hdr = "| # | Title | Channel | Views | Age h | Views/h | Len | URL |\n|---|---|---|---|---|---|---|---|\n"
    lines = []
    for i, c in enumerate(ranked, 1):
        ttl = re.sub(r"\|", "/", c["title"] or "")[:70]
        ch = (c["channel"] or "?")[:22] + (" ✓" if c.get("verified") else "")
        lines.append("| %d | %s | %s | %s | %s | %s | %ss | %s |" % (
            i, ttl, ch, fmt_n(c["views"]), c.get("age_h", "?"), fmt_n(c.get("views_per_h")), c.get("duration_s", "?"), c["url"]))
    table = "Searched at %s UTC · sort=%s uploaded=%s short=%s\n\n%s%s\n" % (
        now.strftime("%Y-%m-%d %H:%M"), a.sort, a.uploaded, a.short, hdr, "\n".join(lines))
    print(table)
    if a.md: open(a.md, "w").write(table)
    if a.json: json.dump({"searched_at_utc": now.isoformat(timespec="minutes"), "args": vars(a), "candidates": ranked},
                         open(a.json, "w"), indent=1, ensure_ascii=False)
    sys.stderr.write("%d unique candidates; views/h is only known where a full extract ran (Age h shown)\n" % len(ranked))

if __name__ == "__main__":
    main()
