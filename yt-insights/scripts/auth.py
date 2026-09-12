"""One-time OAuth flow. Usage: auth.py <project-dir>. Writes secrets/token.json and prints the channel it authorized."""
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

import os, sys
ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CLAUDE_PROJECT_DIR", ".")) / "yt-insights"
SECRET = ROOT / "secrets" / "client_secret.json"
TOKEN = ROOT / "secrets" / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/yt-analytics-monetary.readonly",
]

flow = InstalledAppFlow.from_client_secrets_file(str(SECRET), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent", open_browser=True)
TOKEN.write_text(creds.to_json())
TOKEN.chmod(0o600)

yt = build("youtube", "v3", credentials=creds)
ch = yt.channels().list(part="snippet,statistics", mine=True).execute()["items"][0]
s = ch["statistics"]
print(f"AUTH_OK channel={ch['snippet']['title']!r} id={ch['id']} videos={s.get('videoCount')} subs={s.get('subscriberCount')} views={s.get('viewCount')}")
