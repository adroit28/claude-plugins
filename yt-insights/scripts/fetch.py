"""Pull every upload plus channel/video analytics into data/. Read-only. Re-auths automatically if the token is dead.

Usage: fetch.py --project-dir <dir> [--days 90] [--no-retention]
  --days N  window for the per-video and daily analytics (default 90; lifetime totals are always fetched too)
  --full    ignore cached video list and refetch everything
"""
import argparse, json, os, subprocess, sys
from datetime import date, timedelta
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

HERE = Path(__file__).parent
ROOT = None  # set from --project-dir
DATA = None
TOKEN = None
VIDEO_METRICS = "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,likes,dislikes,comments,shares,subscribersGained,subscribersLost"


def creds_or_reauth() -> Credentials:
    if TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN))
        try:
            if creds.expired or not creds.valid:
                creds.refresh(Request())
            return creds
        except RefreshError as e:
            print(f"token dead ({e.args[0] if e.args else e}); re-authorizing in browser...", file=sys.stderr)
            TOKEN.unlink(missing_ok=True)
    subprocess.run([sys.executable, str(HERE / "auth.py"), str(ROOT.parent)], check=True)
    return Credentials.from_authorized_user_file(str(TOKEN))


def list_uploads(yt) -> list[dict]:
    ch = yt.channels().list(part="snippet,statistics,contentDetails,brandingSettings", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, page = [], None
    while True:
        r = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50, pageToken=page).execute()
        ids += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            break
    videos = []
    for i in range(0, len(ids), 50):
        r = yt.videos().list(part="snippet,contentDetails,statistics,status,topicDetails", id=",".join(ids[i:i + 50])).execute()
        for v in r["items"]:
            sn, st = v["snippet"], v.get("statistics", {})
            videos.append({
                "id": v["id"], "title": sn["title"], "description": sn["description"], "tags": sn.get("tags", []),
                "publishedAt": sn["publishedAt"], "duration": v["contentDetails"]["duration"],
                "categoryId": sn.get("categoryId"), "defaultLanguage": sn.get("defaultLanguage") or sn.get("defaultAudioLanguage"),
                "privacy": v["status"]["privacyStatus"], "publishAt": v["status"].get("publishAt"), "madeForKids": v["status"].get("madeForKids"),
                "thumbnail": sn["thumbnails"].get("maxres", sn["thumbnails"].get("high", {})).get("url"),
                "topics": v.get("topicDetails", {}).get("topicCategories", []),
                "stats": {k: int(st[k]) for k in ("viewCount", "likeCount", "commentCount") if k in st},
            })
    return ch, videos


def analytics_rows(ya, **q) -> list[dict]:
    r = ya.reports().query(ids="channel==MINE", **q).execute()
    cols = [c["name"] for c in r["columnHeaders"]]
    return [dict(zip(cols, row)) for row in r.get("rows", [])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    ap.add_argument("--no-retention", action="store_true", help="skip the per-video retention curve queries")
    a = ap.parse_args()
    global ROOT, DATA, TOKEN
    ROOT = Path(a.project_dir) / "yt-insights"; DATA = ROOT / "data"; TOKEN = ROOT / "secrets" / "token.json"
    DATA.mkdir(parents=True, exist_ok=True)

    creds = creds_or_reauth()
    yt = build("youtube", "v3", credentials=creds)
    ya = build("youtubeAnalytics", "v2", credentials=creds)
    end = date.today() - timedelta(days=2)  # analytics lag ~48h
    start = end - timedelta(days=a.days)
    lifetime_start = "2005-01-01"

    ch, videos = list_uploads(yt)
    print(f"channel {ch['snippet']['title']!r}: {len(videos)} uploads")

    # per-video: lifetime + window
    common = dict(dimensions="video", metrics=VIDEO_METRICS, filters="video==" + ",".join(v["id"] for v in videos))
    life = {r["video"]: r for r in analytics_rows(ya, startDate=lifetime_start, endDate=str(end), **common)}
    win = {r["video"]: r for r in analytics_rows(ya, startDate=str(start), endDate=str(end), **common)}
    for v in videos:
        v["analytics_lifetime"] = {k: x for k, x in life.get(v["id"], {}).items() if k != "video"}
        v[f"analytics_{a.days}d"] = {k: x for k, x in win.get(v["id"], {}).items() if k != "video"}

    # channel-level breakdowns for the window
    channel = {
        "fetchedAt": date.today().isoformat(), "window": {"start": str(start), "end": str(end), "days": a.days},
        "id": ch["id"], "title": ch["snippet"]["title"], "description": ch["snippet"]["description"],
        "customUrl": ch["snippet"].get("customUrl"), "country": ch["snippet"].get("country"),
        "keywords": ch.get("brandingSettings", {}).get("channel", {}).get("keywords"),
        "stats": ch["statistics"],
        "daily": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="day",
                                metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost,likes,comments,shares"),
        "trafficSources": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="insightTrafficSourceType",
                                         metrics="views,estimatedMinutesWatched", sort="-views"),
        "countries": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="country",
                                    metrics="views,estimatedMinutesWatched", sort="-views", maxResults=15),
        "devices": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="deviceType", metrics="views"),
        "demographics": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="ageGroup,gender", metrics="viewerPercentage"),
        "subscribedStatus": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="subscribedStatus",
                                           metrics="views,estimatedMinutesWatched"),
        "searchTerms": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="insightTrafficSourceDetail",
                                      filters="insightTrafficSourceType==YT_SEARCH", metrics="views", sort="-views", maxResults=25),
        "suggestedFrom": analytics_rows(ya, startDate=str(start), endDate=str(end), dimensions="insightTrafficSourceDetail",
                                        filters="insightTrafficSourceType==RELATED_VIDEO", metrics="views", sort="-views", maxResults=25),
    }
    # per-video audience retention curves (one query per video; empty for videos with too few views)
    ret_path = DATA / "retention.json"
    retention = json.load(open(ret_path)) if ret_path.exists() else {}
    if not a.no_retention:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc); refreshed = 0
        for v in videos:
            if v["privacy"] != "public":
                continue
            age_days = (now - datetime.fromisoformat(v["publishedAt"].replace("Z", "+00:00"))).days
            if v["id"] in retention and age_days > 14:
                continue  # curves settle after two weeks; reuse the cached one
            refreshed += 1
            try:
                rows = analytics_rows(ya, startDate=lifetime_start, endDate=str(end), dimensions="elapsedVideoTimeRatio",
                                      metrics="audienceWatchRatio,relativeRetentionPerformance", filters=f"video=={v['id']}")
                if rows:
                    retention[v["id"]] = [[r["elapsedVideoTimeRatio"], round(r["audienceWatchRatio"], 4), round(r.get("relativeRetentionPerformance") or 0, 4)] for r in rows]
            except Exception as e:  # quota or not-enough-data; keep going
                print(f"retention skipped for {v['id']}: {str(e)[:80]}", file=sys.stderr)
        ret_path.write_text(json.dumps(retention))
        print(f"retention curves for {len(retention)} videos ({refreshed} refreshed, rest cached)")

    (DATA / "channel.json").write_text(json.dumps(channel, indent=2))
    (DATA / "videos.json").write_text(json.dumps(videos, indent=2))
    print(f"wrote data/channel.json ({len(channel['daily'])} days) and data/videos.json ({len(videos)} videos)")


if __name__ == "__main__":
    main()
