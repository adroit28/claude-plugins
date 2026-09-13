"""Write changes to videos on the authorized channel: thumbnail, title/description/tags, caption tracks.

This is the only script in the plugin that writes to YouTube. It uses its own token
(secrets/token-write.json, scope youtube.force-ssl); the read-only token is untouched.
Every command is a dry run unless --yes is given. Every write is appended to data/publish.log.

Usage:
  publish.py --project-dir DIR list [--n 10]
  publish.py --project-dir DIR thumbnail --video ID --file thumb.png [--yes]
  publish.py --project-dir DIR metadata  --video ID [--title T] [--description D | --description-file F] [--tags "a,b"] [--yes]
  publish.py --project-dir DIR captions  --video ID --file subs.srt [--lang en] [--name ""] [--yes]

Never changes privacy status, never deletes, never uploads videos.
"""
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

WRITE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
MAX_THUMB = 2 * 1024 * 1024
QUOTA = {"thumbnail": 50, "metadata": 50, "captions_insert": 400, "captions_update": 450}
ROOT = SECRETS = DATA = None


def write_creds() -> Credentials:
    """Load secrets/token-write.json, refresh it, or run the browser consent flow for the write scope."""
    token = SECRETS / "token-write.json"
    if token.exists():
        creds = Credentials.from_authorized_user_file(str(token))
        try:
            if creds.expired or not creds.valid:
                creds.refresh(Request())
            if set(WRITE_SCOPES) <= set(creds.scopes or []):
                return creds
            print("write token lacks the youtube.force-ssl scope; re-authorizing", file=sys.stderr)
        except RefreshError as e:
            print(f"write token dead ({e.args[0] if e.args else e}); re-authorizing in browser...", file=sys.stderr)
        token.unlink(missing_ok=True)
    from google_auth_oauthlib.flow import InstalledAppFlow
    secret = SECRETS / "client_secret.json"
    if not secret.exists():
        sys.exit(f"missing {secret}; see the README's Google Cloud setup")
    print("opening the browser for a one-time consent to edit videos (scope youtube.force-ssl)...", file=sys.stderr)
    flow = InstalledAppFlow.from_client_secrets_file(str(secret), WRITE_SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent", open_browser=True)
    token.write_text(creds.to_json())
    token.chmod(0o600)
    return creds


def log(action, video, ok, detail):
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "publish.log", "a") as f:
        f.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "action": action,
                            "video": video, "ok": ok, "detail": detail}) + "\n")


def explain(e: HttpError) -> str:
    try:
        err = json.loads(e.content)["error"]
        reason = err["errors"][0].get("reason", ""); msg = err.get("message", "")
    except Exception:
        return str(e)
    hints = {
        "forbidden": "the channel is not allowed to do this; for thumbnails, verify the channel by phone at youtube.com/verify",
        "insufficientPermissions": "the token lacks the write scope; delete secrets/token-write.json and run again",
        "videoNotFound": "no such video on this channel; check the id with `list`",
        "quotaExceeded": "daily API quota used up; try after midnight Pacific time",
        "mediaBodyRequired": "the file could not be read",
        "invalidImage": "YouTube rejected the image; use a PNG or JPEG under 2 MB",
    }
    return f"{e.resp.status} {reason}: {msg}" + (f" -> {hints[reason]}" if reason in hints else "")


def cmd_list(yt, a):
    ch = yt.channels().list(part="snippet,contentDetails", mine=True).execute()["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    items = yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=min(a.n, 50)).execute()["items"]
    ids = [i["contentDetails"]["videoId"] for i in items]
    vids = yt.videos().list(part="snippet,status,contentDetails", id=",".join(ids)).execute()["items"]
    vids.sort(key=lambda v: v["status"].get("publishAt") or v["snippet"]["publishedAt"], reverse=True)
    print(f"channel {ch['snippet']['title']!r}, newest {len(vids)} uploads:")
    for v in vids:
        st = v["status"]; sn = v["snippet"]
        when = st.get("publishAt") or sn["publishedAt"]
        print(f"  {v['id']}  {st['privacyStatus']:<9} {when}  {v['contentDetails']['duration']:<8} {sn['title'][:60]}")
    print("(the API does not say whether a thumbnail is custom or auto-picked; Studio does)")


def get_video(yt, vid):
    r = yt.videos().list(part="snippet,status", id=vid).execute()["items"]
    if not r:
        sys.exit(f"video {vid} not found on this channel")
    return r[0]


def cmd_thumbnail(yt, a):
    from PIL import Image
    p = Path(a.file)
    if not p.exists():
        sys.exit(f"no such file: {p}")
    size = p.stat().st_size
    if size > MAX_THUMB:
        sys.exit(f"{p.name} is {size/1024/1024:.2f} MB; YouTube's limit is 2 MB (re-render, or use the JPEG fallback)")
    im = Image.open(p)
    fmt = im.format
    if fmt not in ("PNG", "JPEG", "GIF", "BMP"):
        sys.exit(f"{p.name} is {fmt}; YouTube accepts PNG, JPEG, GIF or BMP")
    w, h = im.size
    ratio = w / h
    shape = "9:16 (Short)" if abs(ratio - 9 / 16) < 0.01 else "16:9" if abs(ratio - 16 / 9) < 0.01 else f"{ratio:.2f} (unusual)"
    v = get_video(yt, a.video)
    print(f"video   : {a.video}  {v['status']['privacyStatus']}  {v['snippet']['title']!r}")
    print(f"file    : {p}  {w}x{h}  {fmt}  {size/1024:.0f} KB  {shape}")
    print(f"quota   : {QUOTA['thumbnail']} units")
    if not a.yes:
        print("dry run; add --yes to set this thumbnail")
        return
    mime = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "BMP": "image/bmp"}[fmt]
    try:
        r = yt.thumbnails().set(videoId=a.video, media_body=MediaFileUpload(str(p), mimetype=mime)).execute()
    except HttpError as e:
        log("thumbnail", a.video, False, explain(e)); sys.exit("failed: " + explain(e))
    urls = {k: x["url"] for k, x in r.get("items", [{}])[0].items()} if r.get("items") else {}
    log("thumbnail", a.video, True, {"file": str(p), "size": size, "wh": [w, h]})
    print(json.dumps({"ok": True, "video": a.video, "thumbnail": urls.get("maxres") or urls.get("high") or urls}, indent=2))
    print("note: YouTube can take a few minutes to swap the image everywhere; for Shorts the custom image shows on the "
          "channel grid, search and subscriptions, not in the swipe feed")


def cmd_metadata(yt, a):
    if not (a.title or a.description or a.description_file or a.tags):
        sys.exit("nothing to change: pass --title, --description/--description-file and/or --tags")
    v = get_video(yt, a.video)
    sn = v["snippet"]
    new = {"title": sn["title"], "description": sn["description"], "tags": sn.get("tags", [])}
    if a.title:
        new["title"] = a.title
    if a.description_file:
        new["description"] = Path(a.description_file).read_text()
    elif a.description:
        new["description"] = a.description
    if a.tags is not None:
        new["tags"] = [t.strip() for t in a.tags.split(",") if t.strip()]
    if len(new["title"]) > 100:
        sys.exit(f"title is {len(new['title'])} chars; YouTube's limit is 100")
    if len(new["description"]) > 5000:
        sys.exit(f"description is {len(new['description'])} chars; YouTube's limit is 5000")
    if any(c in new["title"] for c in "<>"):
        sys.exit("title contains < or >, which YouTube rejects")
    print(f"video   : {a.video}  {v['status']['privacyStatus']}")
    for k in ("title", "description", "tags"):
        old, cur = sn.get(k, [] if k == "tags" else ""), new[k]
        flag = "CHANGE" if old != cur else "same  "
        show = lambda x: (", ".join(x) if isinstance(x, list) else x).replace("\n", " / ")[:160]
        print(f"{flag}  {k:<11} old: {show(old)}")
        if old != cur:
            print(f"        {'':<11} new: {show(cur)}")
    print(f"quota   : {QUOTA['metadata']} units (privacy, schedule and category are left as they are)")
    if not a.yes:
        print("dry run; add --yes to apply")
        return
    body = {"id": a.video, "snippet": {**sn, **new}}  # keep categoryId, defaultLanguage etc. exactly as they are
    for k in ("thumbnails", "publishedAt", "channelId", "channelTitle", "liveBroadcastContent", "localized"):
        body["snippet"].pop(k, None)
    try:
        r = yt.videos().update(part="snippet", body=body).execute()
    except HttpError as e:
        log("metadata", a.video, False, explain(e)); sys.exit("failed: " + explain(e))
    log("metadata", a.video, True, {k: new[k] for k in new if new[k] != sn.get(k, [] if k == "tags" else "")})
    print(json.dumps({"ok": True, "video": a.video, "title": r["snippet"]["title"]}, indent=2))


def cmd_captions(yt, a):
    p = Path(a.file)
    if not p.exists():
        sys.exit(f"no such file: {p}")
    if p.suffix.lower() not in (".srt", ".vtt", ".sbv"):
        sys.exit("caption file must be .srt, .vtt or .sbv")
    v = get_video(yt, a.video)
    existing = yt.captions().list(part="snippet", videoId=a.video).execute().get("items", [])
    match = next((c for c in existing if c["snippet"]["language"] == a.lang and c["snippet"].get("name", "") == a.name), None)
    action = "captions_update" if match else "captions_insert"
    print(f"video   : {a.video}  {v['status']['privacyStatus']}  {v['snippet']['title']!r}")
    print(f"file    : {p}  {p.stat().st_size} bytes  lang={a.lang} name={a.name!r}")
    print(f"tracks  : {[(c['snippet']['language'], c['snippet'].get('name', ''), c['snippet']['trackKind']) for c in existing] or 'none'}")
    print(f"action  : {'replace existing track' if match else 'add new track'}   quota: {QUOTA[action]} units")
    if not a.yes:
        print("dry run; add --yes to upload")
        return
    media = MediaFileUpload(str(p), mimetype="application/octet-stream")
    try:
        if match:
            r = yt.captions().update(part="snippet", body={"id": match["id"], "snippet": {"isDraft": False}}, media_body=media).execute()
        else:
            r = yt.captions().insert(part="snippet", body={"snippet": {"videoId": a.video, "language": a.lang,
                                                                      "name": a.name, "isDraft": False}}, media_body=media).execute()
    except HttpError as e:
        log(action, a.video, False, explain(e)); sys.exit("failed: " + explain(e))
    log(action, a.video, True, {"file": str(p), "lang": a.lang, "id": r["id"]})
    print(json.dumps({"ok": True, "video": a.video, "captionId": r["id"], "status": r["snippet"].get("status")}, indent=2))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project-dir", default=os.environ.get("CLAUDE_PROJECT_DIR", "."))
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("list"); s.add_argument("--n", type=int, default=10)
    s = sub.add_parser("thumbnail"); s.add_argument("--video", required=True); s.add_argument("--file", required=True); s.add_argument("--yes", action="store_true")
    s = sub.add_parser("metadata"); s.add_argument("--video", required=True); s.add_argument("--title"); s.add_argument("--description")
    s.add_argument("--description-file"); s.add_argument("--tags", help="comma separated; replaces the whole tag list"); s.add_argument("--yes", action="store_true")
    s = sub.add_parser("captions"); s.add_argument("--video", required=True); s.add_argument("--file", required=True)
    s.add_argument("--lang", default="en"); s.add_argument("--name", default=""); s.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    global ROOT, SECRETS, DATA
    ROOT = Path(a.project_dir) / "yt-insights"; SECRETS = ROOT / "secrets"; DATA = ROOT / "data"
    yt = build("youtube", "v3", credentials=write_creds())
    {"list": cmd_list, "thumbnail": cmd_thumbnail, "metadata": cmd_metadata, "captions": cmd_captions}[a.cmd](yt, a)


if __name__ == "__main__":
    main()
