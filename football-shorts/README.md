# football-shorts

Three skills that take a football YouTube Short from "what is trending right now"
to a finished, revised `.mp4`, all scripted and reproducible.

| Skill | What it does |
|---|---|
| `/football-shorts:research` | Searches the web, YouTube (view velocity via yt-dlp, no API key), Reddit and the browser for moments from the last 24–72 h; writes a brief with the 5 strongest ideas: sources, second-by-second edit plan, hook text, caption, music, rights risk. |
| `/football-shorts:build` | Fetches one or many sources (only with your explicit OK), finds moments with labelled contact sheets, writes a JSON edit spec, renders 1080×1920 with ffmpeg + Pillow (cuts, pans, freezes, slow-mo, reverse, split-screen, boomerang, captions, emoji, audio bed, bass hits), verifies, hands over. |
| `/football-shorts:revise` | Applies numbered feedback to the spec, bumps the version, re-renders only what changed, shows before/after frames. |
| `football-shorts:scout` (agent) | The cheap worker behind `research`: runs the searches, yt-dlp view-velocity runs, browser scrapes and URL verification on `sonnet`, writes `shorts/briefs/sweep-<date>.md`. The session model only ranks, designs and writes the brief. |

## Install

```
/plugin marketplace add adroit28/claude-plugins
/plugin install football-shorts@adroit-plugins
```

Requirements: macOS with Homebrew `ffmpeg` and `yt-dlp`, Python 3, the system
fonts Impact / Arial Bold / Apple Color Emoji. `skills/build/scripts/setup.sh`
checks all of it and creates `shorts/.venv` with Pillow. The chrome-devtools MCP
is optional (Reddit, Shorts shelves, X posts).

## Use

```
/football-shorts:research
/football-shorts:research focus: ronaldo, window: 24h
/football-shorts:build shorts/briefs/2026-09-25-ronaldo-wales.md idea 1 — yes, download the sources
/football-shorts:build slug: tunnel-cam length: 18 sources: ~/Downloads/fancam.mp4 https://youtu.be/...
/football-shorts:revise 1. drop the opening still 2. at 7 s his face is cut off 3. make it ~20 s
```

Output lives in your project, not in the plugin: `shorts/briefs/` for research,
`shorts/<slug>/` per edit (`src/`, `sources.json`, `spec.vN.json`, `build/`,
`<slug>_vN.mp4`, `notes.md`). Set `FOOTBALL_SHORTS_DIR` to move it.

## Cost and models

Research is the expensive step, so its mechanical sweep is delegated to the `scout`
subagent (`agents/scout.md`, `model: sonnet`). Options:

- Change the sweep model: edit `model:` in `agents/scout.md` to `haiku` (cheapest,
  weaker at judging what is verified), `sonnet` (default), `opus`, or a full ID.
- Run the whole research skill on a cheaper model: `/model opus` (or `sonnet`)
  before `/football-shorts:research`, or add `model: opus` to the frontmatter of
  `skills/research/SKILL.md`. Ranking and brief quality drop a little; the scout
  and the spot-check step still guard against invented sources.
- Call the scout alone for a raw candidate table: `@agent-football-shorts:scout
  focus haaland, window 24h` and read `shorts/briefs/sweep-<date>.md`.
- `build` and `revise` are mostly script time; a cheaper session model is fine for
  `revise` when the feedback is mechanical (timing, text, volume).

## Scripts by hand

```
python3 skills/research/scripts/ytsearch.py -q "haaland" --uploaded day --sort views --short
PY=shorts/.venv/bin/python
$PY skills/build/scripts/fetch.py shorts/my-edit --info <url>
$PY skills/build/scripts/fetch.py shorts/my-edit --accept-terms --name por --rights broadcaster --section 240-340 <url>
$PY skills/build/scripts/sheets.py coarse shorts/my-edit/src/por.mp4
$PY skills/build/scripts/sheets.py frames shorts/my-edit/src/por.mp4 --at 263.4 297.8
$PY skills/build/scripts/render.py shorts/my-edit/spec.v1.json --dry-run
$PY skills/build/scripts/render.py shorts/my-edit/spec.v1.json
$PY skills/build/scripts/check.py shorts/my-edit/my-edit_v1.mp4 --timeline shorts/my-edit/build/timeline_v1.json
```

## Rights

Fetching from YouTube breaks its Terms of Service, and broadcaster or club
footage carries a High Content ID risk. The skills say this before any download,
record the origin class of every source in `sources.json`, and never claim that
cropping, speed changes, short excerpts, music or combining clips changes that.
Fan-shot and creator footage clears more often; the research brief rates each idea.

## Layout

```
.claude-plugin/plugin.json
agents/scout.md
skills/research/SKILL.md
skills/research/references/{research-prompt,sources,brief-template}.md
skills/research/scripts/ytsearch.py
skills/build/SKILL.md
skills/build/references/{spec-format,ffmpeg-recipes,channel-style}.md
skills/build/scripts/{setup.sh,fetch.py,sheets.py,render.py,check.py}
skills/revise/SKILL.md
```
