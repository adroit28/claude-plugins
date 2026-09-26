---
name: build
description: Turn a narrated football story (story.vN.json with aligned narration) into a finished 1080×1920 YouTube Short - animated cards from a template library (calendar gap, name plate, rule card, stat stack, transfer path, stat compare, timeline, quote card, headline), word-timed captions, optional muted real footage clips in a framed box, whips, whooshes and bass hits, loudness to -14 LUFS - then verify it and hand over with title, description, hashtags, the AI-voice note and the session cost. Use when the user says "build the video", "make the short from the script", "render the story", "add real clips", or invokes /football-stories:build.
---

# Build a story Short

Cards → (footage) → compose → (clips) → finish → check → hand over. Every decision lives in
the story file, so `revise` can change any of it later.

## Paths

| What | Where |
|---|---|
| Story | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/story.v<N>.json` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{setup.sh,validate.py,cards.py,compose.py,clips.py,finish.py,check.py,cost.py}` |
| Python | `PY=<shorts dir>/.venv/bin/python` from setup.sh (Pillow, faster-whisper) |
| Footage tools | the football-shorts plugin: `ytsearch.py`, `fetch.py`, `sheets.py`. Find them with `find "${CLAUDE_PLUGIN_ROOT}/../.." ~/.claude/plugins -path "*football-shorts*" \( -name ytsearch.py -o -name fetch.py -o -name sheets.py \) 2>/dev/null`. If they're missing, ask the user to install football-shorts; don't improvise a downloader |
| Shared | `shorts/fonts/` (Anton, Barlow Condensed, Montserrat; OFL), Google Chrome (card screenshots) |
| References | `references/story-format.md` · `references/templates.md` · `references/channel-style.md` · `references/template-demo.json` |
| Output | `graphics/v<N>/`, `build/`, `src/` (footage), `<slug>_v<N>.mp4`, `notes.md` in the edit folder |

## Inputs

| Input | Default |
|---|---|
| Story path | latest `story.v*.json` in the most recent `shorts/<slug>/` |
| Photo | none; only own/cc/licensed assets |
| Footage | none, unless the user asks for real clips and says yes to downloads for this video (`handoff.md` may already record that yes) |
| Music bed | none (the user adds one at upload) unless a licensed/CC asset is given |

## Procedure

1. **Set up and check.** `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh` (note `PY=`). The story needs `narration.audio` and `narration.words`; if not, run the narrate skill first. If this version is already rendered, stop and use `revise`.
2. **Design the scenes** (skip if `scenes` already exist). Read `references/templates.md` and the channel rules. Map lines to 4–8 scenes, one template each, in spoken order:
   - Each scene's first step anchors to its first word; later steps anchor to the word the reveal illustrates (the number, the club, the date). A visual change every 1.5–2.5 s; nothing static longer than 2.5 s.
   - The hook scene starts at L1 word 0. The last scene is a `headline_card` on the payoff line, with `captions.hide_in_scenes` set to it.
   - Card text comes from the facts; no extra claims on cards that the narration and facts don't support. Keep card text short (it's read in under 2 s; see "Fitting text" in templates.md).
   - 2–3 bass `hits` on the biggest reveals (the constraint, the peak fact, the payoff).
   - With footage (step 3): lines covered by a full-box clip get one quiet scene across all back-to-back clips, never two scenes in a row under footage.
   - Write them into the story, then `python3 validate.py <story> --stage build`.
3. **Footage (only when the user wants real clips).** The user's yes to downloads covers one video; ask again for each new one, and say plainly that broadcast footage carries a High Content ID risk that cropping doesn't remove (Content ID matches the pictures).
   - Find: `ytsearch.py -q "<match> highlights" -q "<player> <moment>" --uploaded week --sort views` and pick sources with the moments the lines describe (official highlights for match action; fan-filmed for celebrations). Note them in `shorts/briefs/clips-<date>-<slug>.md`.
   - Download: `python3 fetch.py <edit folder> --accept-terms --name <key> --rights <broadcaster|club|fan|...> <url>` (into `src/`, logged in `src/sources.json`). Retry once on a merge error. Add each file to `assets` as `kind: video` with `rights.class` (broadcaster/club footage = `doubtful`), `origin`, `channel`, `source_url` and `accepted: <date of the yes>`.
   - Find moments and crops: `$PY sheets.py coarse src/<key>.mp4`, then `fine --from --to` and `frames --at ... --grid 100`; Read the PNGs. Crop clear of the broadcaster logo, the score bug and any watermark; where the crop would cut the subject, erase the bug with `pre: "delogo=x=..:y=..:w=..:h=.."`. Match the box aspect (full 988:888, top/bottom 988:438). A banner that is on screen for under a second (OFFSIDE, NO GOAL) gets `slow: 2.0` and starts just before it appears.
   - Map clips to lines: windows of 0.9–2.5 s anchored to the words they illustrate (`from`/`to`), a split `top`+`bottom` pair for "X and Y" hooks, and cards (not footage) for numbers, quotes and the payoff. Write `clips` into the story, then `python3 validate.py <story> --stage build`.
4. **Cards.** `$PY cards.py <story>`, then Read `graphics/v<N>/sheet.png` (cyan box = graphics safe zone, magenta = caption band). Fix overflow, cramped text or anything outside the boxes (shorter props, `\n` line breaks) and re-run; unchanged cards are skipped.
5. **Compose.** `$PY compose.py <story>` → picture track, voice + whoosh mix, `build/timeline_v<N>.json`. It fails loudly if anchors are out of order.
6. **Clips** (only with `clips`). `$PY clips.py <story> --plan`, fix every warning (whip under footage, stretched crop, source too short), then `$PY clips.py <story>` → `build/graphics_v<N>_clips.mp4`, with the timeline pointed at it. Note its `CHECK_AT=` times. compose.py resets the timeline to the card-only track, so run clips.py after every compose; finish.py refuses to run until you do.
7. **Finish.** `$PY finish.py <story>` → `<slug>_v<N>.mp4` (video stream copied, hits, optional bed, loudnorm −14 LUFS / −1.5 dBTP, +faststart).
8. **Check.** `$PY check.py <slug>_v<N>.mp4 --timeline build/timeline_v<N>.json` and Read the sheet. With clips, also run `check.py <mp4> --at <CHECK_AT times>` and Read that sheet: no logo, score bug or watermark in any window, the subject in frame, no card text flashing around the box. Confirm: duration 20–30 s (or up to `length.max`), peak about −1.5 dB, no black frames, every caption legible and in the band, the spoken word highlighted, cards readable at phone size, the final card clean. Fix what you see and re-run the affected step; at most two internal passes, then hand over.
9. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "build v<N>" --slug <slug>` (run from the project root).
10. **Hand over.** `open <mp4>`. In chat:
    - The path, the duration, and the scene timeline (start · scene · template · line). Captions are the script text.
    - Title, description and hashtags per the channel rules, with "Narration voice is AI-generated." in the description (or point to `/yt-insights:metadata`).
    - A rights table: cards own, fonts OFL, voice engine and tier, whooshes and hits synthesised, any photo with its licence and credit. For each footage source give the channel, the URL, and "High Content ID risk: a claim or block is possible; logos cropped only so their branding isn't shown".
    - Facts that are single-source, and anything unverified.
    - The cost lines from step 9.
    - End: send changes as numbered points and run `/football-stories:revise`.
11. **Record.** `notes.md` in the edit folder: story, format, facts with sources, voice and pace, assets and rights (footage sources with URLs), scene plan, clip windows, version log (v<N>: date, length, voice, what changed, Claude cost of the step).

## Hard rules

- Every claim on screen or in the narration traces to a fact id with a source.
- No photo or music with rights class doubtful/unknown unless the user explicitly accepts it; flag it in the hand-over either way. No agency photos or realistic AI images of real people (those would need the altered/synthetic label).
- Footage only through `clips`, muted, after the user's explicit yes to downloads for this video (recorded as `rights.accepted`). Never claim anything reduces Content ID risk. Uploads stay manual.
- Versions only go up; never overwrite an earlier story file, card folder or mp4. Never touch another session's edit folder (e.g. `shorts/ronaldo-wales/`).
- Report what the check sheet shows, including problems you could not fix.
