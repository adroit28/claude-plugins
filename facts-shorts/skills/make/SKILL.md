---
name: make
description: End-to-end facts-channel Short with approval stops - topic ideas, fact research on a cheap subagent, Hinglish script, voice take (no audition), storyboard and video, metadata - offering a fresh session at each handoff and reporting the Claude cost after every step. Use when the user says "make a facts short", "do the whole thing", "next facts short from scratch", pastes any facts-shorts handoff prompt (NEXT.md), or invokes /facts-shorts:make.
---

# Make a facts Short, start to finish

Runs the skills in order and stops at each checkpoint. Read each skill's SKILL.md when you reach it
and follow it exactly; this file only sets the order and the stops.

| Step | Skill | Stop and wait for |
|---|---|---|
| 1 | `ideas` | the user picks a card (skip if they named a topic) |
| 2 | `research` | the user has seen the verdict table and the spine → handoff (fresh session offered) |
| 3 | `script` | the user approves the beats → `story.v1.json` → handoff (fresh session offered) |
| 4 | `narrate` | the user approves the take and the pronunciation (voice is always en-in-commercial-1) |
| 5 | `video` | the user approves the storyboard; then says yes to the image downloads |
| 6 | `metadata` | none: hand over the mp4 with metadata.md |
| — | `revise` | on numbered feedback at any point after step 5 |

Skill files: `${CLAUDE_PLUGIN_ROOT}/skills/{ideas,research,script,narrate,video,metadata,revise}/SKILL.md`.

`<story>` is the FULL path to `story.v<N>.json` (a file, never the folder). Pass that file to every script.

After every step: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "<step>" --slug <slug>` from the
project root, and its lines in that step's report.

## Starting from a handoff prompt

A pasted `NEXT.md` prompt names the next skill and the slug/story: read the story folder
(`verify.md`, latest `story.v*.json`, `notes.md`), don't redo earlier steps, and start at that skill
with the notes from the prompt.

## Fresh sessions

Research and video leave large contexts. At the research → script and script → narrate handoffs,
say "a new session in `<project root>` with this prompt is cheaper" and show the prompt. Continue
here only if the user says so.
Also offer a fresh session at the narrate → video handoff (video is the largest context).
Pipe long tool output through `head -30`; don't Read whole files you only need a part of.

## Hard rules

All hard rules of the skills apply, in particular: verified facts only, Roman-script Hinglish,
no sources in the story file, downloads only after an explicit yes, free TTS (one take per request),
versions only go up, and every video ends with the 3 s like & subscribe card.

- If a command fails twice with the same error, stop: re-read the script's usage (`--help`), change the arguments, never repeat the identical call.
