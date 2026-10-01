---
name: research
description: Real-time football Shorts researcher. Searches the web, YouTube (view velocity via yt-dlp), Reddit and the browser for moments from the last 24–72 hours, verifies sources, and writes a ranked brief of the 5 strongest Short ideas with sources, second-by-second edit plan, hook text, caption, music and rights risk. Use when the user says "what's trending in football", "find viral football moments", "shorts ideas for today", "research brief", or invokes /football-shorts:research.
---

# Football Shorts research

Deliver five ranked, verified Short ideas for today, in the format of
`references/research-prompt.md` (the contract) and `references/brief-template.md`
(the file layout). Search first; never answer from memory.

## Paths

| What | Where |
|---|---|
| Brief | `${CLAUDE_PROJECT_DIR}/shorts/briefs/YYYY-MM-DD-<slug>.md` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Candidate table | `shorts/briefs/candidates-YYYY-MM-DD.json` + `videos-YYYY-MM-DD.md` from `sweep.py` |
| Search scripts | `${CLAUDE_PLUGIN_ROOT}/skills/research/scripts/{sweep.py,ytsearch.py}` (need `yt-dlp`, read-only) |
| Cost | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/cost.py` (logs to `shorts/cost_log.jsonl`) |
| Channel rules | `${CLAUDE_PROJECT_DIR}/yt-insights/style.md` if present, else `../build/references/channel-style.md` |

## Inputs

| Input | Default |
|---|---|
| Focus (`focus: ronaldo`, `focus: premier league weekend`) | none: whole football world |
| Window (`window: 24h`) | 72 h, ranked 24 h > 48 h > 3–5 days |
| Count (`count: 8`) | 5 ideas, plus a rejected list |
| `--no-browser` | browser pass on when the chrome-devtools MCP is connected |

## Who does what

The expensive part of research is the sweep: dozens of searches, yt-dlp runs and page
reads. That runs in the plugin subagent `football-shorts:scout` (`agents/scout.md`,
`model: sonnet` by default), and its YouTube half is one `sweep.py` call rather than
many agent turns. The session model keeps the judgement: spot-checking the
sweep, ranking, edit plans, hooks, rights and the brief. Change the scout's model by
editing `model:` in `agents/scout.md` (`haiku`, `sonnet`, `opus`, or a full model ID).

## Procedure

1. **Timestamp.** Run `date; TZ=Asia/Kolkata date; TZ=Europe/London date` and put "Research conducted at" with IST and UTC at the top of everything. Fix the window from that time, not from what feels recent.
2. **Read the contract.** `references/research-prompt.md`, `references/brief-template.md`, and the channel rules file. If `yt-insights/data/summary.json` exists, print its `top` titles: that is what this audience already rewards. Do not read `sources.md` yourself; the scout gets it.
3. **Delegate the sweep.** Resolve the absolute paths first (`echo ${CLAUDE_PLUGIN_ROOT}`; `mkdir -p` the briefs dir). Then call the Agent tool with `subagent_type: football-shorts:scout`, `run_in_background: false`, and this prompt filled in:

   ```
   Research time: <IST> / <UTC>. Window: <72h>. Focus: <none|...>. Candidates wanted: 15–20.
   sweep.py: <abs path>/skills/research/scripts/sweep.py
   sources.md (read §1 queries, §3 scrapers, §4 checklist): <abs path>/skills/research/references/sources.md
   Output dir: <abs path>/shorts/briefs   Date tag: YYYY-MM-DD
   Browser pass: <allowed|not allowed (--no-browser)>
   Audience already rewards: <top titles from summary.json, or "unknown">
   Write sweep-<date>.md (plus sweep.py's candidates-<date>.json and videos-<date>.md) there and return the 60-line report.
   ```

   If the Agent tool is unavailable or the scout returns an error twice, do the sweep inline using the **Inline fallback** below.
4. **Spot-check the sweep.** Read `sweep-<date>.md`. For the top 5 videos run `yt-dlp -j --no-playlist <url> | python3 -c 'import sys,json;d=json.load(sys.stdin);print(d["title"],d["channel"],d["upload_date"],d["view_count"])'` and compare. Anything that does not match, or any URL marked `not verified` that you want to cite, is either re-verified by you or dropped. If more than one row is wrong, send the scout back with `SendMessage` naming the rows; do not silently trust the rest.
5. **Design the top 3 in full, the rest in one line.** Full design is output from the expensive model and only the idea the user picks gets built, so ideas 4–5 get a one-line entry (title · trend score · recency · best source URL · risk · why it ranks lower); `build` writes the edit plan if the user picks one of them. Design against the channel rules: 13–30 s, open on the moment by second 2, player-led, loopable ending, title 25–45 chars with an emoji pair and no question, hashtags per rule. The EDIT PLAN names a source and time for every beat and uses 2–5 s per source from 2–4 sources; it is never a re-upload of one Short. Where the scout wrote `timestamp not verified`, the plan says "find with sheets.py" rather than inventing a second.
6. **Rights.** Per source: broadcaster/club/player/fan/creator → Low/Med/High. Broadcaster and club footage is High regardless of how it will be cut. Do not write that trimming, mirroring, speed, music, or combining reduces the risk.
7. **Write the brief** to `shorts/briefs/YYYY-MM-DD-<slug>.md` in the template order: header, TOP 3, ideas 1–3 with every field, ideas 4–5 as one-liners, rejected list, candidate table (copied from the sweep, with "collected by scout, spot-checked rows marked ✓"), method and caveats (including the scout's caveats and which model ran it). Delete weak ideas rather than pad to five.
8. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/cost.py --step research`.
9. **Report in chat:** the header line, TOP 3 as three lines, then each of the five ideas compressed to title · trend score · recency · risk · best source URL, the brief path, the cost lines, and the next step as a prompt for a **fresh session** (the brief holds everything build needs; the searches and pages in this conversation would otherwise be re-read, and paid for, on every build turn):

   ```
   Start a new session (/clear or a new chat) and paste:
   /football-shorts:build <abs brief path> idea <n> — <yes, download the sources | ask me before downloading>
   ```

   Say "or reply `continue here`" for users who prefer one conversation.

## Inline fallback (only when the scout cannot run)

- Discover events with 10–15 WebSearch queries worded with actual dates (`sources.md` §1); collect 15–20 candidate moments with event date, what happened, who.
- Quantify and verify: one `sweep.py --out <briefs> --date <date>` run with a `-q` per candidate, a `--channel` per official account and a `--url` per YouTube link from the searches.
- Browser pass if the MCP is present: r/soccer top of the day, Shorts hashtag shelves, any X post surfaced (`sources.md` §3). Note in the brief if skipped.
- Verify every cited source per `sources.md` §4 and write the same `sweep-<date>.md` the scout would.

## Hard rules

- SEARCH FIRST. Three verified moments from the last 24–48 h beat ten generic ideas.
- Never fabricate a URL, count, upload time, or timestamp. Unverified fields say so.
- State event date and upload date separately; say whether each idea is a TRENDING EVENT or a TRENDING VIDEO.
- This skill downloads nothing. It only reads pages and metadata.
- Every number in the brief comes with where it was read and when (IST).
- The scout collects; you judge. Never cite a scout row you or the scout did not verify, and always spot-check the top 5 yourself.
