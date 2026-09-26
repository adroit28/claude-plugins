---
name: research
description: Find and verify story ideas for narrated football Shorts (no footage), write ranked story cards with two sources per fact, and once the user picks one, draft the fact-cited script as story.v1.json. Uses news RSS, Reddit RSS, Wikipedia on-this-day, dated web searches and Commons photo licences. Use when the user says "find a football story", "story ideas", "what story should we narrate", "on this day football", "write the script for", or invokes /football-stories:research.
---

# Story research

Two stops: **cards** (verified candidates for the user to pick from), then **script** (the
picked story as `story.v1.json` with facts and lines). Search first; never write a fact from
memory.

## Paths

| What | Where |
|---|---|
| Leads bundle | `${CLAUDE_PROJECT_DIR}/shorts/briefs/discover-YYYY-MM-DD.json` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Story cards | `shorts/briefs/stories-YYYY-MM-DD.md` |
| Script | `shorts/<slug>/story.v1.json` |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{discover.py,validate.py}` (stdlib, `python3` is fine) |
| References | `references/formats.md` (F1–F13) · `references/story-card.md` (gates, score, card format) · `references/sources.md` (sources, verification, photos) · `../build/references/story-format.md` · `../build/references/channel-style.md` |
| Channel rules | `${CLAUDE_PROJECT_DIR}/yt-insights/style.md` if present (wins), else `channel-style.md` |
| Past research | `shorts/narrative-research/07-story-candidates.md`, `football-story-engine.html` §04–05 (worked examples, known corrections) |

## Inputs

| Input | Default |
|---|---|
| Focus (`focus: chelsea`, `focus: anniversaries`, a named story) | none: whole football world |
| Window | 72 h for timely stories; evergreen and on-this-day (today + 3 days) always included |
| Count | 5–8 cards |
| A picked card (`card 3`, or "the Keane one") | none: stop after cards |

## Procedure: cards

1. **Timestamp.** `date; TZ=Asia/Kolkata date; TZ=UTC date`. Put "Research conducted at" (IST and UTC) at the top of the cards file. Fix the window from that time.
2. **Read** `references/story-card.md`, `references/formats.md`, the channel rules. If `yt-insights/data/summary.json` exists, note its top titles (what this audience rewards). Check `shorts/briefs/stories-*.md` and existing `shorts/*/story.v*.json` so you don't pitch a story already made.
3. **Collect leads.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/discover.py --out shorts/briefs` (news RSS, r/soccer, on-this-day). Then 8–12 WebSearch queries worded with real dates (`references/sources.md`): records and "first since" from this week, anniversaries for today to +3 days, rule quirks, young players' routes, this week's quotes. Collect 12–20 candidates.
4. **Gate and verify.** For each candidate, apply both gates. For the survivors, open the sources (WebFetch) and write each fact with its URLs; aim for two independent sources, mark single-source facts. Compute ages and gaps yourself and say so. Check today's state of any club/manager/loan you mention.
5. **Photos.** `discover.py --commons "<player>"` for the main person. Record licence and rights_guess; do not plan a `doubtful` photo.
6. **Score and match a format** (story-card.md, formats.md). Draft the hook line and a title per card.
7. **Write** `shorts/briefs/stories-YYYY-MM-DD.md` in the card format, best first, then Rejected and Method/caveats. Cut weak cards rather than pad.
8. **Report in chat:** one line per card (name · format · score · confidence · why now), the file path, and "pick a card number to get the script". Stop.

## Procedure: script (after the user picks)

1. **Slug** from the story, kebab-case. Refuse to write into an existing `shorts/<slug>/` from another session: pick a new slug.
2. **Write `story.v1.json`** per `../build/references/story-format.md`: `facts` (from the card, `signed_off` empty), `narration.style` (delivery prompt), and `narration.lines`:
   - Follow the format's beats. First line = the hook, said in ~1.5 s. Last line = short payoff, `"no_claim": true`.
   - 65–75 words total (20–30 s at pace 0.93). One idea per line, 3–14 words per line.
   - Every other line cites its fact ids. Nothing in a line that its facts don't support.
   - Write for the ear: numbers as spoken ("eighteen"), no brackets, no abbreviations. `tts` only where emphasis (CAPS) or a pause (`...`, `<short pause>`) helps.
   - Names the voice may get wrong: add to `shorts/lexicon.json` if not there (respelling, `verified_by_ear: false`).
   - Also fill `publish` (title per channel rules, 1–2 sentence description with sources in short form) and `disclosure` (`"description_note": "Narration voice is AI-generated."`).
3. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py shorts/<slug>/story.v1.json` and fix every ERROR.
4. **Show the user** the script as a table (line · text · facts) and the fact table with sources, the estimated length, and anything unverified. Ask them to approve or edit. When they approve, set `signed_off` to today's date on each fact. Next step: `/football-stories:narrate shorts/<slug>/story.v1.json`.

## Hard rules

- Never fabricate a fact, number, quote, URL, date or policy. Unverified = not in the script, listed under "Not verified".
- Every claim line cites a fact with a source; `validate.py` must pass before narration.
- Stats in your own words; quotes verbatim with source and date. No allegation about a real person beyond what the sources say.
- This skill downloads no video and uploads nothing.
- Every number in the cards says where it was read.
