---
name: make
description: End-to-end editor for ANY talking-head video - the user's own video (any aspect ratio, with sound) becomes a punchy 1080x1920 Short with a hook, word-by-word captions, punch-ins, cutaways, counters and slams, sound design, an optional background swap and a like & subscribe outro, in stages with an approval stop after each and the Claude cost reported after every stage. Use when the user says "edit my video", "make a short from this talking-head clip", "add captions and punch-ins to ~/x.mp4", pastes a talking-head-shorts handoff (NEXT.md), or invokes /talking-head-shorts:make.
---

# Talking-head Short, start to finish

One independent plugin: its own scripts, its own Remotion template (spec-driven, no per-video TSX edits),
nothing imported from football-shorts, facts-shorts or football-stories. The topic is whatever the user
says in the video; nothing here is football-specific.

Read each stage's SKILL.md when you reach it and follow it exactly; this file only sets the order and the stops.

| Stage | Skill | Stop and wait for |
|---|---|---|
| 1 | `intake` | the user has answered: fit for a non-9:16 source (crop to the speaker / blurred fill), the unclear words (never guessed), and the confirmed caption text |
| 2 | `plan` | the user's OK on the edit plan table (3 hook options, punch-ins, cutaways, counters, slams, captions + HOT words, sfx, drone, outro) |
| 3 | `background` | ONLY if the user asks or supplies a background: the 5-second matte test and edge sheet are shown and the user says go |
| 4 | `build` | the user's OK to go on to finish (offer to show the raw first; a re-render is cheap) |
| 5 | `finish` | the user watches `<slug>_v<N>.mp4` |
| T | `timeline` | MULTI-CLIP route (several takes, a joined file, inserts, a graphics kit): its own steps T1-T11, one stop each, see that skill |
| - | `revise` | numbered feedback at any time after stage 5: a new version, never an overwrite |

Route choice: one video file with one continuous take -> stages 1-5. Several takes of one script, a joined file made from takes, picture-only inserts or a
graphics kit -> the `timeline` skill (it replaces stages 2-5; intake's questions and transcript still apply). Say which route you chose and why.

Skill files: `${CLAUDE_PLUGIN_ROOT}/skills/{intake,plan,background,build,finish,revise,timeline}/SKILL.md`.

## Paths and tools (set these once per session)

- Work from the personal-projects root (project-scoped skills vanish in subfolders): the folder that contains `shorts/`.
- `S=${CLAUDE_PLUGIN_ROOT}/scripts`. `PY` = the venv python with numpy, opencv, onnxruntime, faster-whisper, Pillow:
  `$THS_PY`, else `~/.config/talking-head-shorts/venv/bin/python`, else `shorts/.venv/bin/python`. Run every script as `$PY -I $S/<script>.py ...`
  (`-I`: Python that reads the user's downloaded files must not load code from the current folder).
- `bash $S/setup.sh` checks the environment (no downloads without flags).
- One Short = one folder `shorts/<slug>/` (slug = kebab-case of the topic, ask only if unclear). Everything lives there:
  `source.<ext>` (link to the ORIGINAL), `probe.json`, `blink.json`, `transcript*.json`, `unclear.json`, `captions.txt`/`.json`,
  `beatmap.json/.md`, `edit.v<N>.json` (the spec, see `${CLAUDE_PLUGIN_ROOT}/README.md`), `matte/`, `anim/`, `build_v<N>.mp4`,
  `<slug>_v<N>.mp4`, `notes.md`, `NEXT.md`, `cost_log.jsonl`.
- `notes.md` has a `## State` block (20 lines max: latest version, stage done, decisions the user made, open questions) that every
  stage rewrites, and an append-only log below it. A fresh session needs only that file, the latest spec and the latest sheet.

## Step protocol (EVERY step, in every skill, no exceptions)

A step is one numbered section of a skill (or one row of the `timeline` skill's T1-T11). Never run two steps back to back on your own.
After each step, in this order:

1. Do the step, check its output (look at the frame / table / loudness, do not just trust the exit code).
2. Tell the user in at most 4 lines what was done, what you saw, and anything odd or undecided.
3. `$PY -I $S/cost.py --step "<stage/step>" --slug <slug>`: paste its three lines (this step / this session / this video) into the reply.
4. Ask one question: "go on to <next step name>?" with the one decision the next step needs (if any). Then STOP and wait. The user may answer
   "continue", give a change (re-do this step), or skip ahead.
5. Rewrite `notes.md` State (and `NEXT.md` for a handoff) before the question, so a crash or a new session loses nothing.

At a stage boundary also offer a fresh session: "a new session in `<root>` with this prompt is cheaper", show the prompt (saved as
`shorts/<slug>/NEXT.md`): `/talking-head-shorts:make slug: <slug>` + one line naming the next step and anything not on disk. Always offer it after
`plan`/T7 (the context is large with transcripts and sheets) and after `build`. Continue here only if the user says so. A user saying "continue"
once means that step only; ask again after the next one.

Handoff pattern: `NEXT.md` = the slug, the route, the next step id, the files it reads (State block, latest spec or timeline.py, latest sheet),
decisions already made, what is NOT on disk, and a final line "report cost with cost.py after the step and ask before the following one".

## Starting from a handoff prompt

A pasted `NEXT.md` names the slug and the next stage: read `notes.md` State and the latest spec, do not redo earlier stages.

## Hard rules (all stages)

- Use the ORIGINAL file the user gives, never an edited cut. Never overwrite an earlier mp4, spec or raw render: versions only go up.
- Never guess unclear speech. List the stretches with timestamps and ASK for the words; caption exactly what the user writes
  (Hinglish spelled as they spell it: "bezzati", not "behzati").
- Tone: punchy. No fact-check caveats, no "this is my opinion" text on screen.
- Downloads (Whisper models, the RVM model, npm packages, sfx packs, stock) need the user's explicit yes; if they already said yes this
  session, do not ask again. No paid generation (images/video) unless asked, one image at a time.
- Cheap models do the mechanical work: the `beat-mapper` subagent (sonnet) for frame reading and the beat table; transcription and
  caption alignment are local scripts (free). The main session is for decisions and the edit plan.
- Matte PNGs are ~400 MB per 27 s of video: warn first with the estimate (matte.py prints it).
- Ask before committing or pushing. Commit messages end with the Co-Authored-By trailer from the system reminder.
- If a command fails twice with the same error, stop: re-read the script's `--help`, change the arguments, never repeat the identical call.
