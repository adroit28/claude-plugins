---
name: build
description: Turn a narrated football story (story.vN.json with aligned narration) into a finished 1080×1920 YouTube Short with no footage - animated cards from a template library (calendar gap, name plate, rule card, stat stack, transfer path, stat compare, timeline, quote card, headline), word-timed captions, whips, whooshes and bass hits, loudness to -14 LUFS - then verify it and hand over with title, description, hashtags and the AI-voice note. Use when the user says "build the video", "make the short from the script", "render the story", or invokes /football-stories:build.
---

# Build a story Short

Cards → compose → finish → check → hand over. Every decision lives in the story file, so
`revise` can change any of it later.

## Paths

| What | Where |
|---|---|
| Story | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/story.v<N>.json` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{setup.sh,validate.py,cards.py,compose.py,finish.py,check.py}` |
| Python | `PY=<shorts dir>/.venv/bin/python` from setup.sh (Pillow, faster-whisper) |
| Shared | `shorts/fonts/` (Anton, Barlow Condensed, Montserrat; OFL), Google Chrome (card screenshots) |
| References | `references/story-format.md` · `references/templates.md` · `references/channel-style.md` · `references/template-demo.json` |
| Output | `graphics/v<N>/`, `build/`, `<slug>_v<N>.mp4`, `notes.md` in the edit folder |

## Inputs

| Input | Default |
|---|---|
| Story path | latest `story.v*.json` in the most recent `shorts/<slug>/` |
| Photo | none; only own/cc/licensed assets |
| Music bed | none (the user adds one at upload) unless a licensed/CC asset is given |

## Procedure

1. **Set up and check.** `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh` (note `PY=`). The story needs `narration.audio` and `narration.words`; if not, run the narrate skill first. If this version is already rendered, stop and use `revise`.
2. **Design the scenes** (skip if `scenes` already exist). Read `references/templates.md` and the channel rules. Map lines to 4–7 scenes, one template each, in spoken order:
   - Each scene's first step anchors to its first word; later steps anchor to the word that the reveal illustrates (the number, the club, the date). A visual change every 1.5–2.5 s; nothing static longer than 2.5 s.
   - The hook scene starts at L1 word 0. The last scene is a `headline_card` on the payoff line, with `captions.hide_in_scenes` set to it.
   - Card text comes from the facts; no extra claims on cards that the narration and facts don't support. Keep card text short (it's read in under 2 s).
   - 2–3 bass `hits` on the biggest reveals (the constraint, the peak fact, the payoff).
   - Write them into the story, then `python3 validate.py <story> --stage build`.
3. **Cards.** `$PY cards.py <story>`, then Read `graphics/v<N>/sheet.png` (cyan box = graphics safe zone, magenta = caption band). Fix overflow, cramped text or anything outside the boxes (shorter props, `\n` line breaks) and re-run; unchanged cards are skipped.
4. **Compose.** `$PY compose.py <story>` → picture track, voice + whoosh mix, `build/timeline_v<N>.json`. It fails loudly if anchors are out of order.
5. **Finish.** `$PY finish.py <story>` → `<slug>_v<N>.mp4` (video stream copied, hits, optional bed, loudnorm −14 LUFS / −1.5 dBTP, +faststart).
6. **Check.** `$PY check.py <slug>_v<N>.mp4 --timeline build/timeline_v<N>.json` and Read the sheet. Confirm: duration 20–30 s, peak about −1.5 dB, no black frames, every caption legible and in the band, the spoken word highlighted, cards readable at phone size, the final card clean. Fix what you see and re-run the affected step; at most two internal passes, then hand over.
7. **Hand over.** `open <mp4>`. In chat: path, duration, the scene timeline (start · scene · template · line), captions are the script text, title / description / hashtags per the channel rules with "Narration voice is AI-generated." in the description (or point to `/yt-insights:metadata`), a rights table (cards own, fonts OFL, voice engine and tier, whooshes/hits synthesised, any photo with its licence and credit), facts that are single-source, and anything unverified. End: send changes as numbered points and run `/football-stories:revise`.
8. **Record.** `notes.md` in the edit folder: story, format, facts with sources, voice and pace, assets and rights, scene plan, version log (v<N>: date, length, voice, what changed).

## Hard rules

- Every claim on screen or in the narration traces to a fact id with a source.
- No photo or music with rights class doubtful/unknown unless the user explicitly accepts it; flag it in the hand-over either way. No broadcast footage, agency photos, or realistic AI images of real people (those would need the altered/synthetic label).
- Never claim anything reduces Content ID risk. Uploads stay manual.
- Versions only go up; never overwrite an earlier story file, card folder or mp4. Never touch another session's edit folder (e.g. `shorts/ronaldo-wales/`).
- Report what the check sheet shows, including problems you could not fix.
