---
name: build
description: Turn a researched idea (or the user's own clips and URLs) into a finished 1080×1920 YouTube Short with ffmpeg + Pillow. Fetches one or many source videos with explicit authorisation, finds the exact moments with labelled contact sheets, writes a versioned JSON edit spec (cuts, pans, freezes, slow-mo, reverse, split-screen, boomerang, captions, emoji, audio bed, bass hits), renders, verifies frames and loudness, and hands over the file. Use when the user says "make the short", "build idea 2", "cut this into a short", "edit these clips", or invokes /football-shorts:build.
---

# Build a Short

From a brief idea or a set of sources to a verified `.mp4`, fully scripted, with
every decision recorded so the `revise` skill can change it later.

## Paths

| What | Where |
|---|---|
| Edit folder | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Inside it | `src/` sources · `sources.json` · `plan.v1.md` · `spec.v1.json` · `build/` (segments, overlays, sheets, timelines) · `<slug>_v1.mp4` · `notes.md` |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{setup.sh,fetch.py,sheets.py,plan.py,spec.py,render.py,check.py,cost.py}` (`speclib.py` is shared by plan/spec/check) |
| Frame reader | subagent `football-shorts:spotter` (`agents/spotter.md`, `model: sonnet`) |
| Python | `PY=<shorts dir>/.venv/bin/python` created by `setup.sh` (Pillow; pip needs `-i https://pypi.org/simple`) |
| Tracked overlays | `track.py` (render, keys, CSRT) · `detect.py` finds players by ID and the ball in replays/close angles and writes the same track file; runs on `PYD=` from `setup.sh --detect` (separate venv, only when an overlay follows a player or the ball) · `detect.py --auto` writes the track a `{"reframe": ...}` crop follows (window pans with the ball or the main group; spec-format.md) |
| References | `references/plan-format.md` (always: the plan grammar and spec ops) · `references/spec-format.md` (when a field's meaning is unclear) · `references/channel-style.md` (always) · `references/ffmpeg-recipes.md` (only for a `vf` filter or effect spec-format does not cover) |

## Inputs

| Input | Default |
|---|---|
| Brief path + `idea <n>` | latest `shorts/briefs/*.md`, idea 1 |
| Or sources: YouTube URLs and/or local files, with a one-line idea | required if no brief |
| `slug:` | from the idea title, kebab-case |
| `length:` | 20 s (channel rule 13–30 s) |
| Download authorisation | none: ask before any fetch (see rule 1) |

## Procedure

1. **Authorisation first.** Downloading from YouTube breaks its Terms of Service, and broadcaster or club footage carries a High Content ID risk that no edit removes. If the user's message does not already say to download, ask once, in two lines, and stop until they answer. Local files and files the user already downloaded need no question. Never claim cropping, mirroring, speed changes, short excerpts, music, or combining make footage safe.
2. **Set up.** `bash ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/setup.sh` and note the `PY=` line. Create `shorts/<slug>/`. Read the brief's SOURCES and EDIT PLAN for the chosen idea, and the channel rules. Ideas ranked 4 and below are one-liners in the brief: write their EDIT PLAN into `notes.md` first (a source and time per beat, 2–5 s per source, open on the moment), then carry on.
3. **Ingest sources, all of them in one pass.** For each URL: `fetch.py <edit_dir> --info <url>` to show what it is, then `fetch.py <edit_dir> --accept-terms --name <key> --rights <class> [--section a-b] <url>`. Use `--section` when the brief gives an approximate time in a long broadcast (a 200 s window around it is plenty). For local files, reference them by absolute path in the spec `sources` map or copy them into `src/`. A letterboxed or landscape local file: run `enhance/scripts/analyse.py` for its picture box and use spec `fill` (spec-format.md). To re-edit one finished video rather than assemble a new Short, use `/football-shorts:enhance`. `sources.json` is the record of origin and rights per clip. **Quality gate:** `fetch.py` and `analyse.py` end with a `QUALITY:` line; if any source says `LOW`, tell the user in one line (resolution, that it will look soft at 1080 wide, a better-source option if the brief has one) and wait for a go before rendering.
4. **Find the moments (delegated).** Contact sheets are images, and every image read here would be paid for again on every later turn, so the looking is done by the `football-shorts:spotter` subagent. Call the Agent tool with `subagent_type: football-shorts:spotter`, `run_in_background: false`, and:

   ```
   Mode: moments. PY=<venv python>  sheets.py: <abs path>/skills/build/scripts/sheets.py
   Edit folder: <abs shorts/<slug>>
   Sources: <key> = <abs path> — find: <beat from the EDIT PLAN, approx time if the brief gave one>; ... (one line per beat)
   ```

   Then Read only its verification sheet and check that each decisive frame shows what the table says. If a row looks wrong, open that one sheet it listed, or `sheets.py frames --at` the disputed second yourself, and correct the row. Copy the moments table (source key, seconds, what happens, crop) into `notes.md`. If the Agent tool is unavailable, do it inline: `sheets.py fine --from --to --width 240` around the brief's time (`coarse` only without one), then `sheets.py frames --at ...` for crops (9:16 window on 1080p is 608 wide: x = subject centre − 304; faces inside 500×889).
5. **Write `plan.v1.md`, not JSON.** One line per beat (source, in, out, effect, caption, hit, extras) plus header, overlays and hits sections per `references/plan-format.md`; the header needs a `spine` line (question at 0 s, turn beat at 60–70 %, button = last beat). Structure: open on the moment itself at 0 s (never a still or title card first), one story beat per 1.5–3 s, captions from the brief's HOOK TEXT and IN-VIDEO TEXT, at most six words per overlay inside the safe zones, a crowd or music bed, bass hits on the freeze and the reveal, last beat cutting back to the opening so it loops (`end loop` does this for you). Total 13–30 s. Segments that need mixing (`split`, `boomerang`, `reverse`, `slowmo`, `ramp`, `card`) are for the comic or contrast beats; plain `clip` for the action. Then `$PY plan.py shorts/<slug>/plan.v1.md`: it snaps lengths to frames, places captions and hits from the computed starts, writes `spec.v1.json` and prints the timeline and warnings. Read that printout, not the JSON. Fix anything by editing the plan and re-running (or with `spec.py` ops once a version exists). Do not hand-write or hand-edit spec JSON; if the plan cannot express something, say so in the hand-over.
6. **Render and verify.** `$PY render.py spec.v1.json`, then `$PY check.py <slug>_v1.mp4 --timeline build/timeline_v1.json --spec spec.v1.json`. Read the check sheet (about one frame per segment) and confirm: subject in frame at every cut, no cropped faces, captions legible and inside safe zones. The numbers (black or mostly-dark frames, peak about −1.5 dB, duration, retention) are in the printout and its `verdict` line. Fix what you see and re-render once (cached segments make this fast); on that re-render, if you only moved captions, timing or audio, read the sheet only when the verdict says LOOK, otherwise `sheets.py compare <new> --ref <old> --at <changed seconds>`. Then hand over and let the user steer.
7. **Record.** `notes.md` has two parts. `## State` on top, at most 20 lines: slug and idea in one line, latest version with length and verdict, sources with rights class and resolution (QUALITY line), the user's standing decisions, open questions, next step. `## Appendix` below it: sources table, moments table, plan decisions, version log (v1: date, length, what it contains), findings. Revise reads only State by default and may run in a fresh session that has just this file, the plan, the spec and the timeline, so anything the user said that matters later goes into State.
8. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/cost.py --step build --slug <slug>`.
9. **Hand over.** `open <mp4>`. In chat: file path, duration, the timeline table (start · beat · source), captions in order, a title/description/hashtag set that follows the channel rules (or point to `/yt-insights:metadata` if that plugin exists), per-source rights class and risk, what was not verified, and the cost lines. End with: send changes as numbered points; for a cheaper revision start a new session and paste `/football-shorts:revise slug: <slug>` followed by the list (everything revise needs is on disk), or reply here to continue.

## Hard rules

- No download without the user's explicit yes in this conversation; `--accept-terms` is that yes, not a default.
- Never touch an edit folder another session is working in; create a new slug instead.
- One spec per version; never edit a rendered version's spec in place (`plan.py` and `spec.py` refuse). The model writes plans and ops; the scripts write JSON.
- All text via Pillow (no drawtext); every segment frame-pinned; loudnorm on; `+faststart`.
- Mute or duck broadcaster commentary; use the match crowd or a user-supplied bed.
- Report what the check sheet shows, including problems you could not fix.
