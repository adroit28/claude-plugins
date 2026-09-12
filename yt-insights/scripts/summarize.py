"""Reduce data/videos.json + data/channel.json to data/summary.json and print a compact digest.
Usage: summarize.py --project-dir <dir>
The digest is what the report/metadata skills read; never load videos.json into context."""
import argparse, json, os, re, statistics, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F1E6-\U0001F1FF]")


def iso_secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d)
    h, mi, s = (int(x or 0) for x in m.groups())
    return h * 3600 + mi * 60 + s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    a = ap.parse_args()
    data = Path(a.project_dir) / "yt-insights" / "data"
    videos = json.load(open(data / "videos.json"))
    ch = json.load(open(data / "channel.json"))
    retention = json.load(open(data / "retention.json")) if (data / "retention.json").exists() else {}
    studio = json.load(open(data / "studio.json")) if (data / "studio.json").exists() else {}
    sys.path.insert(0, str(Path(__file__).parent))
    from experiments import score_all, load as load_json
    experiments = score_all(load_json(data.parent / "experiments.json"), data.parent)
    days = ch["window"]["days"]
    wkey = f"analytics_{days}d"

    pub = [v for v in videos if v["privacy"] == "public" and v["analytics_lifetime"]]
    for v in pub:
        v["secs"] = iso_secs(v["duration"])
        v["is_short"] = v["secs"] <= 180
        dt = datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00")).astimezone(IST)
        v["ist_weekday"], v["ist_hour"] = dt.strftime("%a"), dt.hour
        L = v["analytics_lifetime"]
        v["views"] = L.get("views", 0)
        v["avp"] = L.get("averageViewPercentage", 0)
        v["avd"] = L.get("averageViewDuration", 0)
        v["eng"] = round(100 * (L.get("likes", 0) + L.get("comments", 0) + L.get("shares", 0)) / max(v["views"], 1), 2)
        v["subs"] = L.get("subscribersGained", 0) - L.get("subscribersLost", 0)
        v["hashtags"] = re.findall(r"#\w+", v["title"] + " " + v["description"])
        v["emoji_count"] = len(EMOJI.findall(v["title"]))
        v["title_len"] = len(re.sub(r"\s*#\w+", "", v["title"]).strip())
        curve = retention.get(v["id"])
        def at(ratio):
            if not curve: return None
            pt = min(curve, key=lambda c: abs(c[0] - ratio)); return round(100 * pt[1], 1)
        v["hook3s"] = at(min(3 / max(v["secs"], 1), 1.0))
        v["ret_mid"] = at(0.5)
        v["ret_end"] = round(100 * curve[-1][1], 1) if curve else None
        st = studio.get(v["id"])
        v["studio"] = {k: st[k] for k in ("impressions", "ctr", "stayed_pct", "swiped_pct") if k in st} if st else None

    by_views = sorted(pub, key=lambda v: -v["views"])
    med = statistics.median(v["views"] for v in pub)
    slim = lambda v: {k: v[k] for k in ("id", "title", "publishedAt", "secs", "views", "avp", "avd", "eng", "subs", "hashtags", "emoji_count", "title_len", "ist_weekday", "ist_hour", "thumbnail", "tags", "hook3s", "ret_mid", "ret_end", "studio")}

    # cadence
    dates = sorted(datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00")) for v in pub)
    gaps = [(b - a).total_seconds() / 86400 for a, b in zip(dates, dates[1:])]
    slot = defaultdict(list)
    for v in pub:
        slot[(v["ist_weekday"], v["ist_hour"])].append(v["views"])
    wd = defaultdict(list)
    for v in pub:
        wd[v["ist_weekday"]].append(v["views"])

    # title patterns: top quartile vs bottom quartile
    q = max(len(by_views) // 4, 1)
    top, bot = by_views[:q], by_views[-q:]
    pat = lambda vs: {"n": len(vs), "median_views": statistics.median(v["views"] for v in vs),
                      "avg_title_len": round(statistics.mean(v["title_len"] for v in vs), 1),
                      "avg_emoji": round(statistics.mean(v["emoji_count"] for v in vs), 2),
                      "avg_secs": round(statistics.mean(v["secs"] for v in vs), 1),
                      "avg_avp": round(statistics.mean(v["avp"] for v in vs), 1),
                      "pct_with_question": round(100 * sum("?" in v["title"] for v in vs) / len(vs)),
                      "avg_hook3s": round(statistics.mean(v["hook3s"] for v in vs if v["hook3s"] is not None), 1) if any(v["hook3s"] is not None for v in vs) else None,
                      "pct_with_player_name": None}
    hashtags = Counter(h.lower() for v in pub for h in v["hashtags"])

    daily = ch["daily"]
    tot = lambda k: sum(d.get(k, 0) for d in daily)
    summary = {
        "generatedAt": datetime.now(IST).isoformat(timespec="minutes"),
        "channel": {"title": ch["title"], "id": ch["id"], "customUrl": ch.get("customUrl"), "country": ch.get("country"),
                    "subscribers": int(ch["stats"]["subscriberCount"]), "lifetime_views": int(ch["stats"]["viewCount"]),
                    "public_videos": len(pub), "first_upload": dates[0].date().isoformat(), "last_upload": dates[-1].date().isoformat(),
                    "days_since_last_upload": (datetime.now(timezone.utc) - dates[-1]).days},
        "window": {**ch["window"], "views": tot("views"), "watch_minutes": tot("estimatedMinutesWatched"),
                   "subs_net": tot("subscribersGained") - tot("subscribersLost"), "likes": tot("likes"), "comments": tot("comments"), "shares": tot("shares"),
                   "best_day": max(daily, key=lambda d: d["views"]) if daily else None},
        "daily": [{"day": d["day"], "views": d["views"], "subs": d["subscribersGained"] - d["subscribersLost"]} for d in daily],
        "shorts_share": round(100 * sum(v["is_short"] for v in pub) / len(pub)),
        "median_views": med, "mean_avp": round(statistics.mean(v["avp"] for v in pub), 1),
        "top": [slim(v) for v in by_views[:8]], "bottom": [slim(v) for v in by_views[-5:]],
        "all_videos": [slim(v) for v in by_views],
        "cadence": {"uploads": len(pub), "per_week": round(len(pub) / max((dates[-1] - dates[0]).days / 7, 1), 2),
                    "median_gap_days": round(statistics.median(gaps), 2) if gaps else None, "max_gap_days": round(max(gaps), 1) if gaps else None},
        "by_weekday": {k: {"n": len(v), "median_views": statistics.median(v)} for k, v in wd.items()},
        "by_slot": [{"weekday": k[0], "hour_ist": k[1], "n": len(v), "median_views": statistics.median(v)} for k, v in sorted(slot.items(), key=lambda kv: -statistics.median(kv[1]))[:6]],
        "title_patterns": {"top_quartile": pat(top), "bottom_quartile": pat(bot)},
        "hashtags": hashtags.most_common(12),
        "retention_curves": {
            "top": [{"id": v["id"], "title": v["title"], "secs": v["secs"], "views": v["views"], "pts": [[c[0], c[1]] for c in retention[v["id"]][::2]]} for v in by_views if v["id"] in retention][:5],
            "bottom": [{"id": v["id"], "title": v["title"], "secs": v["secs"], "views": v["views"], "pts": [[c[0], c[1]] for c in retention[v["id"]][::2]]} for v in reversed(by_views) if v["id"] in retention][:5],
        },
        "studio": {"videos_matched": sum(1 for v in pub if v["studio"]), "sources": sorted({st.get("source") for st in studio.values() if st.get("source")}),
                   "avg_ctr": round(statistics.mean(v["studio"]["ctr"] for v in pub if v["studio"] and "ctr" in v["studio"]), 2) if any(v["studio"] and "ctr" in v["studio"] for v in pub) else None,
                   "avg_stayed_pct": round(statistics.mean(v["studio"]["stayed_pct"] for v in pub if v["studio"] and "stayed_pct" in v["studio"]), 1) if any(v["studio"] and "stayed_pct" in v["studio"] for v in pub) else None} if studio else None,
        "experiments": experiments,
        "traffic": ch["trafficSources"], "search_terms": ch["searchTerms"][:15], "suggested_from": ch["suggestedFrom"][:10],
        "countries": ch["countries"][:8], "devices": ch["devices"], "demographics": ch["demographics"], "subscribedStatus": ch["subscribedStatus"],
    }
    (data / "summary.json").write_text(json.dumps(summary, indent=1, default=str))

    c, w = summary["channel"], summary["window"]
    print(f"# {c['title']} — {c['public_videos']} public videos, {c['subscribers']} subs, {c['lifetime_views']:,} lifetime views")
    print(f"window {w['start']}..{w['end']}: {w['views']:,} views, {w['watch_minutes']:,} min watched, {w['subs_net']:+} subs, {w['likes']} likes, {w['comments']} comments, {w['shares']} shares")
    print(f"cadence: {summary['cadence']['per_week']}/wk, median gap {summary['cadence']['median_gap_days']}d, max gap {summary['cadence']['max_gap_days']}d, last upload {c['last_upload']} ({c['days_since_last_upload']}d ago)")
    print(f"median video views {med:,.0f}; mean retention {summary['mean_avp']}%; shorts share {summary['shorts_share']}%")
    h3 = lambda v: f"hook3s {v['hook3s']:>5.1f}%" if v.get("hook3s") is not None else "hook3s   n/a"
    print("\n## top"); [print(f"  {v['views']:>6}  {v['avp']:>5.1f}%  {h3(v)}  {v['secs']:>3}s  eng {v['eng']:>4}%  {v['ist_weekday']} {v['ist_hour']:02d}h  {v['title']}") for v in summary["top"]]
    print("## bottom"); [print(f"  {v['views']:>6}  {v['avp']:>5.1f}%  {h3(v)}  {v['secs']:>3}s  eng {v['eng']:>4}%  {v['ist_weekday']} {v['ist_hour']:02d}h  {v['title']}") for v in summary["bottom"]]
    print(f"## retention curves: {len(retention)} videos; top-5 hook@3s " + ", ".join(f"{c['pts'][min(len(c['pts'])-1, max(0, round(3/max(c['secs'],1)*50)))][1]*100:.0f}%" for c in summary["retention_curves"]["top"]) + " | bottom-5 " + ", ".join(f"{c['pts'][min(len(c['pts'])-1, max(0, round(3/max(c['secs'],1)*50)))][1]*100:.0f}%" for c in summary["retention_curves"]["bottom"]))
    if summary["studio"]: print(f"## studio: {summary['studio']['videos_matched']} videos matched from {summary['studio']['sources']}; avg CTR {summary['studio']['avg_ctr']}%, avg stayed {summary['studio']['avg_stayed_pct']}%")
    else: print("## studio: no CSV imported (drop Studio exports in yt-insights/studio/ and run studio.py)")
    for e in experiments:
        print(f"## experiment {e['id']} [{e['status']}] {e['name']} → {e['result']['verdict']}" + (f" ({e['result']['best']} over {e['result']['worst']} by {e['result']['ratio']}x)" if 'ratio' in e['result'] else ""))
        for r in e["scored"]: print(f"   - {r['label']}: " + (f"{r['views']} views, {r['views_per_day']}/day, ret {r['retention']}%, live {r['days_live']}d" if r["live"] else "not live yet"))
    print("\n## by weekday (median views)"); print("  " + ", ".join(f"{k} {v['median_views']:.0f} (n={v['n']})" for k, v in sorted(summary["by_weekday"].items(), key=lambda kv: -kv[1]["median_views"])))
    print("## best slots"); [print(f"  {s['weekday']} {s['hour_ist']:02d}h IST  median {s['median_views']:.0f}  n={s['n']}") for s in summary["by_slot"]]
    print("\n## title patterns  top-quartile vs bottom-quartile"); print("  ", summary["title_patterns"]["top_quartile"]); print("  ", summary["title_patterns"]["bottom_quartile"])
    print("## hashtags", summary["hashtags"])
    print("## traffic", [(t["insightTrafficSourceType"], t["views"]) for t in summary["traffic"]])
    print("## search", [t["insightTrafficSourceDetail"] for t in summary["search_terms"]])
    print("## suggested from", [t["insightTrafficSourceDetail"] for t in summary["suggested_from"]])
    print("## countries", [(t["country"], t["views"]) for t in summary["countries"]])
    print("## devices", [(t["deviceType"], t["views"]) for t in summary["devices"]])
    print("## subscribed", [(t["subscribedStatus"], t["views"]) for t in summary["subscribedStatus"]])
    print("## demographics", [(d["ageGroup"], d["gender"], d["viewerPercentage"]) for d in sorted(summary["demographics"], key=lambda d: -d["viewerPercentage"])[:6]])


if __name__ == "__main__":
    main()
