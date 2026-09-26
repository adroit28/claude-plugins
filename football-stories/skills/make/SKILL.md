---
name: make
description: End-to-end narrated football story Short with checkpoints - research story cards, the user picks one and approves facts and script, then a handoff prompt for a fresh session, pick a voice and approve the take, then build (optionally with real footage clips) and hand over, reporting the Claude cost after each step. Use when the user says "make a story short", "do the whole thing", "story short from scratch", pastes a football-stories handoff prompt, or invokes /football-stories:make.
---

# Make a story Short, start to finish

Runs the four skills in order and stops at each checkpoint for the user. Read each skill's
SKILL.md when you reach it and follow it exactly; this file only sets the order and the stops.

| Step | Skill | Checkpoint (stop and wait) |
|---|---|---|
| 1 | `research` (cards) | the user picks a card |
| 2 | `research` (script) | the user approves the facts and the script table (edits welcome) → set `signed_off`, then write `handoff.md` and show the prompt for a fresh session (research step 5). Stop there, even if the user said "do the whole thing": they choose a new session (cheaper) or "continue here" |
| 3 | `narrate` | the user picks a voice (default `free`; mention the paid key ≈₹0.65) and approves the take after listening, including any pronunciation flags |
| 4 | `build` | ask about footage if the handoff or the user wants real clips and no yes to downloads is recorded for this video; otherwise none inside: hand over the mp4 with metadata |
| 5 | `revise` | on the user's numbered feedback |

Skill files: `${CLAUDE_PLUGIN_ROOT}/skills/{research,narrate,build,revise}/SKILL.md`.

After every step, run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "<step>" [--slug <slug>]`
from the project root and put its lines in that step's report (each skill says where).

## Inputs

| Input | Default |
|---|---|
| Focus or a named story ("Keane × Haaland anniversary") | none: open research |
| A story path + "script is approved" (the handoff prompt) | none |
| Voice / pace | `free` / 0.93 |

If the user already named a story, skip the card list: research and verify that story, then go
straight to the script checkpoint.

**Starting from a handoff prompt** (a story path and "the script is approved"): don't redo
research. Read the story file and `shorts/<slug>/handoff.md`, run `validate.py` (every fact must be
signed off), and start at step 3 with the voice, pace, length limit, footage decision, deadline and
notes from the prompt. A footage yes recorded in the handoff covers this video only.

## Hard rules

All hard rules of the four skills apply. In particular: no fact without a source, one paid take
per request, no downloads without an explicit yes (per video), uploads stay manual, and the description
carries "Narration voice is AI-generated."
