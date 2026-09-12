# yt-insights

Read-only YouTube channel analytics for Claude Code. Three skills:

- `/yt-insights:report` — pulls every upload plus Analytics API metrics, renders a ranked HTML report with daily views, per-video audience retention curves (top vs bottom), traffic, audience, title-pattern comparison, experiments and written insights.
- `/yt-insights:experiment` — registers paired uploads (length, title shape, slot) and scores them on views per day with a noise threshold. Results show up in the report.
- `/yt-insights:metadata` — drafts titles, description, hashtags, pinned comment and a posting slot for an upcoming video, in the voice learned from the channel's top performers (`yt-insights/style.md`).

Everything user-facing lives in `<project>/yt-insights/`: `secrets/`, `data/`, `reports/`, `drafts/`, `style.md`, `.venv/`. Nothing is written back to YouTube; the OAuth token only carries read scopes.

## One-time Google setup

1. Create a Google Cloud project and enable **YouTube Data API v3** and **YouTube Analytics API**.
2. Google Auth Platform → configure an External app, add these scopes, add yourself as a test user:
   `youtube.readonly`, `yt-analytics.readonly`, `yt-analytics-monetary.readonly`
3. Create an OAuth client of type **Desktop app**, download the JSON, save it as `<project>/yt-insights/secrets/client_secret.json`.
4. Run the report skill once. A browser tab opens; click Advanced → Go to app → tick all scopes.

While the app stays in Testing status the refresh token expires every 7 days and the fetch script reopens the browser for you. To stop that, fill in the Branding page (homepage and privacy URLs can be any HTTPS page you control) and click Publish app; no verification submission is needed.

## Studio export (optional)

Impressions, click-through rate and the Shorts viewed-vs-swiped rate exist only in YouTube Studio. In Studio go to Analytics → Content → Advanced mode → Export (CSV), drop the file in `<project>/yt-insights/studio/`, and the next report run merges it per video. Column names are matched loosely, so any locale works.

## Data the report uses

`fetch.py` writes `data/videos.json` (every upload, lifetime and window analytics), `data/channel.json` (daily series, traffic, audience), `data/retention.json` (per-video curves, cached after 14 days). `summarize.py` reduces them to `data/summary.json`; the skills read only its printed digest.
