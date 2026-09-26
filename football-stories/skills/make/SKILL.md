---
name: make
description: End-to-end narrated football story Short with checkpoints - research story cards, the user picks one and approves facts and script, pick a voice and approve the take, then build and hand over. Use when the user says "make a story short", "do the whole thing", "story short from scratch", or invokes /football-stories:make.
---

# Make a story Short, start to finish

Runs the four skills in order and stops at each checkpoint for the user. Read each skill's
SKILL.md when you reach it and follow it exactly; this file only sets the order and the stops.

| Step | Skill | Checkpoint (stop and wait) |
|---|---|---|
| 1 | `research` (cards) | the user picks a card |
| 2 | `research` (script) | the user approves the facts and the script table (edits welcome) → set `signed_off` |
| 3 | `narrate` | the user picks a voice (default `free`; mention the paid key ≈₹0.65) and approves the take after listening, including any pronunciation flags |
| 4 | `build` | none inside: hand over the mp4 with metadata |
| 5 | `revise` | on the user's numbered feedback |

Skill files: `${CLAUDE_PLUGIN_ROOT}/skills/{research,narrate,build,revise}/SKILL.md`.

## Inputs

| Input | Default |
|---|---|
| Focus or a named story ("Keane × Haaland anniversary") | none: open research |
| Voice / pace | `free` / 0.93 |

If the user already named a story, skip the card list: research and verify that story, then go
straight to the script checkpoint. If they already approved a script, start at step 3.

## Hard rules

All hard rules of the four skills apply. In particular: no fact without a source, one paid take
per request, no downloads without an explicit yes, uploads stay manual, and the description
carries "Narration voice is AI-generated."
