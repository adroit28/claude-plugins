# Brief template — `shorts/briefs/YYYY-MM-DD-<slug>.md`

```
Research conducted at: <DD Mon YYYY, HH:MM IST (HH:MM UTC)>
Window searched: last 48 h (events from <date> to <date>) · Tools: WebSearch ×N, ytsearch.py ×N queries, browser: yes/no

## TOP 3 I WOULD MAKE TODAY
1. <IDEA title> — one line why now · risk Low/Med/High
2. ...
3. ...

## RANKED IDEAS (5: 1–3 in full, 4–5 one line each)

### 1. IDEA: <title>
- TREND SCORE: 1–10 (freshness · momentum · visual hook · emotion · story · vertical fit)
- RECENCY: event <date, time, competition> · fastest upload <date time UTC>, <views> in <hours> (~<views/h>)
- WHY NOW: TRENDING EVENT / TRENDING VIDEO — two lines
- STORY: the arc in three beats (setup → turn → payoff/loop)
- SOURCES:
  | # | URL | Platform | Account (class, verified) | Uploaded | Timestamp | What happens | Use for |
  |---|-----|----------|---------------------------|----------|-----------|--------------|---------|
- EDIT PLAN (second by second, source per beat):
  | s | beat | source# @ time | frame/crop note | text on screen |
- HOOK TEXT: 2–3 options (≤ 6 words)
- IN-VIDEO TEXT: one line per beat
- CAPTION: title 25–45 chars + emoji pair + hashtags
- DESCRIPTION: 2–3 lines, full player names
- MUSIC: 2–3 sounds, each marked verified-in-Shorts-library / unverified
- TRANSFORMATIVE ANGLE: what the edit adds (juxtaposition, timeline, stat, reaction, comic beat)
- RIGHTS / RISK: per source class → Low / Med / High, one line why. No claims that the edit reduces it.

### 2. …  (same fields)
### 3. …  (same fields)

### 4. <title> — trend <n>/10 · event <date> · <best source URL> · risk Low/Med/High · why it ranks below the top 3
### 5. …  (same one line; build writes the EDIT PLAN if the user picks it)

## RESEARCHED BUT REJECTED
- <idea> — reason (stale / no clean source / weak visual / all reposts / rights)

## CANDIDATE TABLE
(paste from the sweep's Videos table, top 20 rows by views/h)

## METHOD & CAVEATS
- queries run, browser pass yes/no, what could not be verified
- reminder: fetching sources breaks YouTube ToS; broadcaster/club footage = Content ID risk regardless of edits
```
Keep the field names exactly; the build skill reads SOURCES and EDIT PLAN by name.
Ideas 4–5 are one-liners to save output from the expensive model; the build skill
designs their EDIT PLAN if the user picks one.
