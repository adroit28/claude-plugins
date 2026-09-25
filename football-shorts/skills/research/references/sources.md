# Where to look and how (verified 2026-09-25)

> Read by the `scout` subagent during `/football-shorts:research`; the session model only reads the resulting `shorts/briefs/sweep-<date>.md`.

Order of trust for "is this really trending": YouTube view velocity on the
original upload → Reddit r/soccer score in the last 24 h → repost count across
channels → X/Instagram engagement (only if you can open the post). A TRENDING
EVENT (everyone is talking) is not a TRENDING VIDEO (one specific upload is
racing); say which one you found.

## 1. Web search (WebSearch tool) – discover what happened
Phrase every query with the actual dates; recency wording alone returns evergreen
lists. Run 10–15 of these, varying competition and angle:
- `"<yesterday, e.g. 24 September 2026>" football goal viral`
- `football last night reaction video <player>` · `<player> press conference <date>`
- `r/soccer <this week>` · `football meme <month year> know your meme`
- `<competition> highlights <date>` for each competition that played in the last 48 h
  (find fixtures first: `football fixtures <date>` / `results <date>`)
- `shorts trending football <month year>` · `tiktok football sound <month year>`
- Player watch-list that always travels for this audience: Ronaldo, Messi, Haaland,
  Mbappé, Vinícius, Yamal, Bellingham, Salah, Palmer, Satpaev, Neymar, Klopp, Mourinho.

## 2. YouTube numbers (scripts/ytsearch.py, no API key, read-only)
```
PY=python3   # any python; yt-dlp must be on PATH
$PY ${CLAUDE_PLUGIN_ROOT}/skills/research/scripts/ytsearch.py \
  -q "ronaldo wales" -q "haaland" -q "klopp press conference" \
  --uploaded day --sort views --short --limit 15 --details 6 \
  --json shorts/briefs/candidates-<date>.json --md shorts/briefs/candidates-<date>.md
$PY .../ytsearch.py -q "<moment>" --uploaded week --sort views          # momentum over the week
$PY .../ytsearch.py --channel @SonyLIV --channel @premierleague --channel @ESPNFC --limit 12   # official uploads
```
Filters are YouTube's own (`sp` token): `--uploaded hour|day|week|month`, `--sort views|date`,
`--short` = under 4 min. Views/h only appears for rows that got a full extract
(`--details N` per query). Look for: views/h in the tens of thousands, several
reposts of the same moment with different titles, verified official channel high
in the list. Everything the script prints is a candidate list, not a verified
source: open the ones you will cite.

Metadata of one URL (upload time, likes, comments, resolution):
`yt-dlp -j --no-playlist <url> | python3 -c "import sys,json;d=json.load(sys.stdin);print({k:d.get(k) for k in ['title','channel','upload_date','timestamp','view_count','like_count','comment_count','duration','channel_is_verified']})"`

## 3. Browser (chrome-devtools MCP) – what yt-dlp cannot list
Use `mcp__chrome-devtools__new_page` (or `navigate_page`) then `evaluate_script`
with `waitForStableDom: false`. Scroll with `window.scrollBy(0,3000)` and wait
~1 s between scrapes for more rows. If the MCP is not connected, skip this pass and
say so in the brief.

YouTube Shorts shelf for a hashtag: `https://www.youtube.com/hashtag/<tag>/shorts`
YouTube search page with filters: take the URL `ytsearch.py` prints on stderr.

```js
// YouTube search results → [{title, url, views, age, channel, verified, len}]
() => [...document.querySelectorAll('ytd-video-renderer')].map(r => {
  const a = r.querySelector('a#video-title'); const m = r.querySelector('#metadata-line')?.innerText || '';
  const len = r.querySelector('ytd-thumbnail-overlay-time-status-renderer, badge-shape')?.innerText?.trim();
  return { title: a?.title, url: (a?.href||'').split('&pp=')[0], meta: m.replace(/\n/g,' · '),
           channel: r.querySelector('#channel-name a')?.innerText, verified: !!r.querySelector('#channel-name .badge'), len };
}).filter(x => x.url && !/Streamed|LIVE|watching/.test(x.meta))
```
```js
// Shorts lockups (hashtag shelf / shorts tab) → [{title, url, views}]
() => [...document.querySelectorAll('ytm-shorts-lockup-view-model, ytd-reel-item-renderer')].map(e => ({
  title: e.querySelector('h3')?.innerText, url: e.querySelector('a')?.href,
  views: (e.querySelector('.shortsLockupViewModelHostOutsideMetadataSubhead')?.innerText || e.innerText).match(/[\d.,]+[kKmM]? views/)?.[0] }))
```
Reddit (curl gets 403 now; the browser works): open
`https://www.reddit.com/r/soccer/top/?t=day` and run
```js
() => [...document.querySelectorAll('shreddit-post')].map(p => ({
  title: p.getAttribute('post-title'), score: +p.getAttribute('score'), comments: +p.getAttribute('comment-count'),
  created: p.getAttribute('created-timestamp'), media: p.getAttribute('content-href'),
  permalink: 'https://www.reddit.com' + p.getAttribute('permalink') }))
```
or navigate to `https://www.reddit.com/r/soccer/top.json?t=day&limit=40` and read `document.body.innerText`.

X/Twitter: search pages need a login; open a specific post URL found via web search
and read the view/like counters from the page text. Instagram: only if the browser
profile is logged in; otherwise list the account and say "not opened".

Know Your Meme: `https://knowyourmeme.com/search?q=<term>` for meme names and origin dates.

## 4. Verification checklist per cited source
- Open it. Title, channel, upload date/time (UTC and IST) copied from the page or `yt-dlp -j`.
- Event date ≠ upload date: state both.
- Timestamp: give it only if you saw it (chapter list, description, or a contact
  sheet after the file was fetched). Otherwise write "timestamp not verified".
- Origin class: broadcaster | club | player | fan | creator; verified badge yes/no.
- Is it the original upload or a repost? Prefer the original; note if only reposts remain.
