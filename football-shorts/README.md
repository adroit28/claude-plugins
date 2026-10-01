# football-shorts

Four skills that take a football YouTube Short from "what is trending right now"
(or from a video you already have) to a finished, revised `.mp4`, all scripted and reproducible.

| Skill | What it does |
|---|---|
| `/football-shorts:research` | Searches the web, YouTube (view velocity via yt-dlp, no API key), Reddit and the browser for moments from the last 24–72 h; writes a brief with the 5 strongest ideas: sources, second-by-second edit plan, hook text, caption, music, rights risk. |
| `/football-shorts:build` | Fetches one or many sources (only with your explicit OK), finds moments with labelled contact sheets, writes a JSON edit spec, renders 1080×1920 with ffmpeg + Pillow (cuts, pans, freezes, slow-mo, reverse, split-screen, boomerang, captions, emoji, audio bed, bass hits), verifies, hands over. |
| `/football-shorts:enhance` | Takes a video you already have (clip, compilation, re-upload; letterboxed or vertical; with or without sound), maps its shots, bars and dead air, offers three hooks, and re-edits it without changing its story: cold open, counters, slow-mo on each chance, punch-ins, freeze + shake, synthesised whoosh/riser/bass/ding, blurred-fill 9:16 layout, loop ending, retention score. |
| `/football-shorts:revise` | Applies numbered feedback to the spec, bumps the version, re-renders only what changed, shows before/after frames. |
| `football-shorts:scout` (agent) | The cheap worker behind `research`: runs the web searches, one `sweep.py` run (YouTube view velocity + yt-dlp verification), browser scrapes, on `sonnet`; writes `shorts/briefs/sweep-<date>.md`. The session model only ranks, designs and writes the brief. |
| `football-shorts:spotter` (agent) | The cheap frame reader behind `build` and `enhance`: runs `sheets.py`, looks at the contact sheets on `sonnet`, returns a moments or beat table and one verification sheet, so dozens of images stay out of the main conversation. |

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
/football-shorts:enhance ~/Downloads/ronaldo-misses.mp4
/football-shorts:enhance ~/Downloads/clip.mp4 hook: counter length: 18
/football-shorts:enhance ~/Downloads/misses.mp4 beats: 0-2 run-up · 2-6 miss 1 · 6-9 replay of miss 1 · 9-12 miss 2
/football-shorts:revise 1. drop the opening still 2. at 7 s his face is cut off 3. make it ~20 s
```

Output lives in your project, not in the plugin: `shorts/briefs/` for research,
`shorts/<slug>/` per edit (`src/`, `sources.json`, `spec.vN.json`, `build/`,
`<slug>_vN.mp4`, `notes.md`). Set `FOOTBALL_SHORTS_DIR` to move it.

## Cost and models

Where the money goes: tokens on the session model, and above all re-reading the
conversation on every turn (search results, pages and contact-sheet images pile up).
What the plugin does about it:

- **Plans and ops, not JSON.** Build and enhance write a line-per-beat `plan.v1.md` and
  `plan.py` turns it into the spec (frame-snapped lengths, caption and hit times from the
  computed starts); revise translates feedback into `spec.py` ops (`bump -- shift fan-angle
  +0.6 -- hit add @flight+0.1 whoosh`) that print what moved. Hand-written spec JSON was
  the biggest output-token cost.
- **One feedback round per session.** After a revise hand-over, the next round goes to a
  fresh session (say `continue here` to override). `notes.md` opens with a `## State`
  block of at most 20 lines, and revise reads only that by default.
- **Cost after every step.** `skills/build/scripts/cost.py` prices the session transcript
  and its subagents at API list rates and prints this step / this session / this video;
  research, build, enhance and each revise run it and log to `shorts/cost_log.jsonl`
  (shared with football-stories). On a Claude subscription the figures are list-price
  equivalents that count against plan limits instead.
- **Fresh session per stage.** Research ends with a paste-ready `/football-shorts:build …`
  prompt for a new session, and build/enhance end with a `/football-shorts:revise slug: …`
  one. Everything the next stage needs is on disk (brief, spec, timeline, `notes.md`).
- **Cheap agents for the legwork.** `scout` (research sweep) and `spotter` (frame reading)
  run on `sonnet`; the YouTube half of the sweep is one `sweep.py` call.
- **Give enhance your beat list.** `beats: 0-2 run-up · 2-6 miss 1 · …` skips the spotter's
  shot-by-shot mapping: enhance only checks the strike and outcome frames and the crops
  (about 2–3 sheets instead of 10–20), and your count and grouping are final.
- **Fewer images.** `check.py` samples about one frame per segment and prints a `verdict`
  line (black / mostly-dark frames, loudness, duration, retention), so re-renders that only
  moved captions or timing need no sheet; revisions use one side-by-side
  `sheets.py compare <new> --ref <old>` sheet. One internal fix pass, not two.
- **Shorter brief.** Only the top three ideas are designed in full; build designs idea 4 or 5
  if you pick it.
- **Revise on Sonnet.** `skills/revise/SKILL.md` has `model: sonnet` in its frontmatter;
  delete that line to revise on the session model.

Options:

- Change the sweep model: edit `model:` in `agents/scout.md` to `haiku` (cheapest,
  weaker at judging what is verified), `sonnet` (default), `opus`, or a full ID.
- Run the whole research skill on a cheaper model: `/model opus` (or `sonnet`)
  before `/football-shorts:research`, or add `model: opus` to the frontmatter of
  `skills/research/SKILL.md`. Ranking and brief quality drop a little; the scout
  and the spot-check step still guard against invented sources.
- Call the scout alone for a raw candidate table: `@agent-football-shorts:scout
  focus haaland, window 24h` and read `shorts/briefs/sweep-<date>.md`.
- Change the frame reader's model: `model:` in `agents/spotter.md`. Keep `build` and
  `enhance` on the stronger session model: moment grouping and hooks are where it pays off.
- Price table: `PRICES` in `cost.py`; `FOOTBALL_SHORTS_INR_RATE` sets the rupee rate.

## Picture and feel (1.4.0)

- **Quality gate.** `fetch.py` and `analyse.py` print `QUALITY: ... ok` or `LOW` (short side
  or picture box under 540 px); build and enhance say so and wait before rendering.
- **Reframe.** `"crop": {"reframe": "build/g3.json"}` makes the 9:16 window follow a track
  with a steady camera (holds, eased pans, no jitter); on a letterboxed source it enlarges
  the picture strip. `detect.py --auto` writes the track: ball when found, else the main
  group of players, else motion. Overlays from `track.py render` follow the window.
- **Speed ramp.** A `ramp` segment runs at real speed, eases into slow-mo around the contact
  frame and back out (`ramp:26.72:x3` in a plan).
- **Sound pack.** Hits use CC0 samples from `shorts/sfx/<kind>/` (`impact`, `sub`, `riser`,
  `whoosh`, `tick`, `tape-stop`; licences in `shorts/sfx/LICENSES.md`) and fall back to the
  built-in synth with a note. `setup.sh` says whether the pack is there.
- **Story spine.** Every spec needs `"spine": {"question", "turn", "button"}`; `check.py`
  fails a spec without one (specs from before 1.4.0 included) and warns when the turn is
  outside 60–70 % of the length. Optional `bpm` snaps cuts to a beat grid.

## Scripts by hand

```
python3 skills/research/scripts/ytsearch.py -q "haaland" --uploaded day --sort views --short
python3 skills/research/scripts/sweep.py --out shorts/briefs --date 2026-09-26 -q "haaland goal" -q "yamal skill" --channel @premierleague
python3 skills/build/scripts/cost.py --step build --slug my-edit           # Claude cost: this step / session / video
PY=shorts/.venv/bin/python
$PY skills/build/scripts/fetch.py shorts/my-edit --info <url>
$PY skills/build/scripts/fetch.py shorts/my-edit --accept-terms --name por --rights broadcaster --section 240-340 <url>
$PY skills/build/scripts/sheets.py coarse shorts/my-edit/src/por.mp4
$PY skills/build/scripts/sheets.py frames shorts/my-edit/src/por.mp4 --at 263.4 297.8
$PY skills/build/scripts/plan.py shorts/my-edit/plan.v1.md                          # plan -> spec.v1.json + timeline
$PY skills/build/scripts/spec.py shorts/my-edit/spec.v1.json bump -- shift flight +0.4  # patch a new version
PYD=shorts/.venv-detect/bin/python   # setup.sh --detect
$PYD skills/build/scripts/detect.py shorts/my-edit/src/fk.mp4 --from 26.72 --to 29.5 --auto --out shorts/my-edit/build/flight.json
$PY skills/build/scripts/track.py render shorts/my-edit/fx.v1.json --spec shorts/my-edit/spec.v1.json
$PY skills/build/scripts/render.py shorts/my-edit/spec.v1.json --dry-run
$PY skills/build/scripts/render.py shorts/my-edit/spec.v1.json
$PY skills/build/scripts/check.py shorts/my-edit/my-edit_v1.mp4 --timeline shorts/my-edit/build/timeline_v1.json --spec shorts/my-edit/spec.v1.json
$PY skills/build/scripts/sheets.py compare shorts/my-edit/my-edit_v2.mp4 --ref shorts/my-edit/my-edit_v1.mp4 --at 7 12
$PY skills/enhance/scripts/analyse.py ~/Downloads/clip.mp4 --out shorts/my-edit/build     # shots, letterbox box, dead air, loudness
$PY skills/build/scripts/sheets.py fine ~/Downloads/clip.mp4 --from 0 --to 4 --fps 4 --crop 478:302:0:274
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
agents/{scout,spotter}.md
skills/research/SKILL.md
skills/research/references/{research-prompt,sources,brief-template}.md
skills/research/scripts/{ytsearch,sweep}.py
skills/build/SKILL.md
skills/build/references/{spec-format,plan-format,ffmpeg-recipes,channel-style}.md
skills/build/scripts/{setup.sh,fetch.py,sheets.py,plan.py,spec.py,speclib.py,render.py,check.py,track.py,detect.py,cost.py}
skills/enhance/SKILL.md
skills/enhance/references/hook-playbook.md
skills/enhance/scripts/analyse.py
skills/revise/SKILL.md
```
