# yt-insights

YouTube channel analytics and upload tooling for Claude Code. Five skills:

- `/yt-insights:report` — pulls every upload plus Analytics API metrics, renders a ranked HTML report with daily views, per-video audience retention curves (top vs bottom), traffic, audience, title-pattern comparison, experiments and written insights.
- `/yt-insights:experiment` — registers paired uploads (length, title shape, slot) and scores them on views per day with a noise threshold. Results show up in the report.
- `/yt-insights:metadata` — drafts titles, description, hashtags, pinned comment, on-screen captions, a trending-music shortlist, thumbnail ideas and a posting slot for an upcoming video, in the voice learned from the channel's top performers (`yt-insights/style.md`).
- `/yt-insights:thumbnail` — proposes three thumbnail concepts and renders the chosen one at exactly 1080x1920 (or 2160x3840 with `--hd`) with headless Chrome, from text alone, over a frame you supply (image, or video plus timestamp), or with a person photo composited on top (your face or a player) as a background-removed cutout, a circle or a tilted card; a second person can sit beside the first, and a filter can drain the colour for a gloomy reaction look. Background removal uses Apple's Vision framework on macOS (compiled once with `swiftc` into `yt-insights/.cache/`), or `rembg` if installed. Verifies size and the 2 MB cap, and writes a 216x384 grid preview for a legibility check. Needs Google Chrome (or any Chromium) installed; `ffmpeg` is optional for pulling frames from a video (`brew install ffmpeg`).

- `/yt-insights:publish` — the one skill that writes: sets a thumbnail, updates title/description/tags, or uploads a caption file on a video already on the channel. Dry run by default, `--yes` to apply, every write logged to `data/publish.log`. Uses a separate token (`secrets/token-write.json`, scope `youtube.force-ssl`) so the analytics token stays read-only. Never uploads videos, never changes privacy or schedule, never deletes.

Everything user-facing lives in `<project>/yt-insights/`: `secrets/`, `data/`, `reports/`, `drafts/`, `thumbnails/`, `style.md`, `.venv/`. The four analytics and drafting skills never write to YouTube; only `/yt-insights:publish` does, with its own token.

## One-time Google setup

1. Create a Google Cloud project and enable **YouTube Data API v3** and **YouTube Analytics API**.
2. Google Auth Platform → configure an External app, add these scopes, add yourself as a test user:
   `youtube.readonly`, `yt-analytics.readonly`, `yt-analytics-monetary.readonly`
3. Create an OAuth client of type **Desktop app**, download the JSON, save it as `<project>/yt-insights/secrets/client_secret.json`.
4. Run the report skill once. A browser tab opens; click Advanced → Go to app → tick all scopes.
5. Only if you want `/yt-insights:publish`: add the `youtube.force-ssl` scope to the app as well. The first publish run opens a second consent tab and stores `secrets/token-write.json`. Custom thumbnails also need a phone-verified channel (youtube.com/verify).

While the app stays in Testing status the refresh token expires every 7 days and the fetch script reopens the browser for you. To stop that, fill in the Branding page (homepage and privacy URLs can be any HTTPS page you control) and click Publish app; no verification submission is needed.

## Studio export (optional, automatable)

Impressions, click-through rate and the Shorts "stayed to watch" rate exist only in YouTube Studio. The report skill gets them in one of three ways, in order: a CSV already in `<project>/yt-insights/studio/` from the last 7 days; an export it performs itself in your signed-in Chrome; or a manual export you drop in the folder (Studio → Analytics → Content → Advanced mode → Export current view → CSV). Column names are matched loosely, so any locale works.

To enable the automatic export, register a second browser tool that attaches to your own Chrome instead of launching an isolated one. The default `chrome-devtools` tool stays isolated for everything else; Google refuses sign-in inside it, which is why a second tool is needed.

```bash
claude mcp add chrome-studio -s user -- npx -y chrome-devtools-mcp@latest --autoConnect
```

Then in Chrome (version 144 or later) open `chrome://inspect/#remote-debugging`, turn on "Allow remote debugging", and restart the Claude Code session. `scripts/studio_export.py check` tells you whether the connection is ready. The tool drives your real browser with your real logins, so leave it out if you would rather export by hand. Never give the assistant your Google password; it does not need it and Google would block the login anyway.

## Data the report uses

`fetch.py` writes `data/videos.json` (every upload, lifetime and window analytics), `data/channel.json` (daily series, traffic, audience), `data/retention.json` (per-video curves, cached after 14 days). `summarize.py` reduces them to `data/summary.json`; the skills read only its printed digest.

## Shorts thumbnails

`thumbnail.py` renders an HTML card in headless Chrome at the exact 9:16 size, then checks it with Pillow. Custom image uploads for Shorts are done in YouTube Studio on desktop and are rolling out gradually (Partner Program channels first). If the option is missing, bake the 1080x1920 PNG into the edit as the first frame and pick it with the frame slider in the mobile app. Thumbnails do not show in the swipe feed, only on the channel grid, search, subscriptions and the home shelf.
