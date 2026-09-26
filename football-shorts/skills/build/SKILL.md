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
| Inside it | `src/` sources · `sources.json` · `spec.v1.json` · `build/` (segments, overlays, sheets, timelines) · `<slug>_v1.mp4` · `notes.md` |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{setup.sh,fetch.py,sheets.py,render.py,check.py}` |
| Python | `PY=<shorts dir>/.venv/bin/python` created by `setup.sh` (Pillow; pip needs `-i https://pypi.org/simple`) |
| References | `references/spec-format.md` · `references/ffmpeg-recipes.md` · `references/channel-style.md` |

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
2. **Set up.** `bash ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/setup.sh` and note the `PY=` line. Create `shorts/<slug>/`. Read the brief's SOURCES and EDIT PLAN for the chosen idea, and the channel rules.
3. **Ingest sources, all of them in one pass.** For each URL: `fetch.py <edit_dir> --info <url>` to show what it is, then `fetch.py <edit_dir> --accept-terms --name <key> --rights <class> [--section a-b] <url>`. Use `--section` when the brief gives an approximate time in a long broadcast (a 200 s window around it is plenty). For local files, reference them by absolute path in the spec `sources` map or copy them into `src/`. A letterboxed or landscape local file: run `enhance/scripts/analyse.py` for its picture box and use spec `fill` (spec-format.md). To re-edit one finished video rather than assemble a new Short, use `/football-shorts:enhance`. `sources.json` is the record of origin and rights per clip.
4. **Find the moments.** For each source: `sheets.py coarse` (or `fine --from --to` when the brief gave a time), Read the PNGs, then `sheets.py frames --at t1 t2 ...` and read the crop x/y off the grid (9:16 window on 1080p is 608 wide: x = subject centre − 304; keep faces inside a 500×889 window for close-ups). Write a moments table into `notes.md`: source key, seconds, what happens, crop.
5. **Write `spec.v1.json`** per `references/spec-format.md`. Structure: open on the moment itself at 0 s (never a still or title card first), one story beat per 1.5–3 s, captions from the brief's HOOK TEXT and IN-VIDEO TEXT, at most six words per overlay inside the safe zones, a crowd or music bed, bass hits on the freeze and the reveal, last beat cutting back to the opening so it loops. Total 13–30 s. Use whole-frame lengths (multiples of 0.04 s) and copy caption times from the dry-run timeline. Segments that need mixing (`split`, `boomerang`, `reverse`, `slowmo`, `card`) are for the comic or contrast beats; plain `clip` for the action. `render.py spec.v1.json --dry-run` and check the timeline before encoding.
6. **Render and verify.** `$PY render.py spec.v1.json`, then `$PY check.py <slug>_v1.mp4 --timeline build/timeline_v1.json` and Read the check sheet. Confirm: subject in frame at every cut, no cropped faces, captions legible and inside safe zones, no black frames, peak about −1.5 dB, duration as planned. Fix what you see and re-render (cached segments make this fast). At most two internal passes, then hand over and let the user steer.
7. **Hand over.** `open <mp4>`. In chat: file path, duration, the timeline table (start · beat · source), captions in order, a title/description/hashtag set that follows the channel rules (or point to `/yt-insights:metadata` if that plugin exists), per-source rights class and risk, and what was not verified. End with: send changes as numbered points and run `/football-shorts:revise`.
8. **Record.** `notes.md`: idea, sources with rights, moments table, spec decisions, version log (v1: date, length, what it contains).

## Hard rules

- No download without the user's explicit yes in this conversation; `--accept-terms` is that yes, not a default.
- Never touch an edit folder another session is working in; create a new slug instead.
- One spec per version; never edit a rendered version's spec in place.
- All text via Pillow (no drawtext); every segment frame-pinned; loudnorm on; `+faststart`.
- Mute or duck broadcaster commentary; use the match crowd or a user-supplied bed.
- Report what the check sheet shows, including problems you could not fix.
