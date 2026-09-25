---
name: revise
description: Apply the user's numbered feedback to an existing football Short built by /football-shorts:build. Maps each comment (seconds, beats, captions, length, missing face, boring opening) to changes in the JSON edit spec, bumps the version, re-renders only what changed, verifies the changed seconds with before/after frames, and hands over the new file. Use when the user says "change the opening", "at 7 seconds his face is missing", "make it 20 seconds", "different caption", "redo the ending", or invokes /football-shorts:revise.
---

# Revise a Short

Feedback in, next version out, with proof of the change. The edit spec is the
source of truth; every revision is a new spec version and a new file.

## Paths

| What | Where |
|---|---|
| Edit folder | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/` (latest `spec.v<N>.json`, `build/timeline_v<N>.json`, `notes.md`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{render.py,check.py,sheets.py,fetch.py}` with `PY=<shorts dir>/.venv/bin/python` |
| Spec reference | `${CLAUDE_PLUGIN_ROOT}/skills/build/references/spec-format.md` |

## Inputs

| Input | Default |
|---|---|
| Feedback (numbered list, or prose you number yourself) | required |
| `slug:` | the edit folder most recently rendered under `shorts/` |
| `length:` | keep current unless the feedback changes it |

## Procedure

1. **Locate the version.** Find the highest `spec.v<N>.json` in the edit folder, read it, `notes.md`, and `build/timeline_v<N>.json`. If the user names a time ("at the 7th second"), the timeline tells you which segment that is; say so.
2. **Translate feedback.** One line per item: `#k "<their words>" → segment i / overlay j / audio: <concrete change>`. Typical mappings: "still at the start, people drop off" → delete the opening `still`, start on the action clip and move the hook overlay onto it; "face missing at 7 s" → `sheets.py frames --at` around that source time, read the head position off the grid, tighten to `[500,889,x,y]` or shift x; "more comic" → replace a card with `reverse`, `boomerang`, `split` or `slowmo` of a reaction; "make it 20 s" → trim durations from the middle beats, keep hook and payoff, re-time overlays and hits; "different caption" → overlay text only (re-render takes seconds). Anything that needs a new source goes through the build skill's fetch step and the same authorisation rule.
3. **New version.** Copy `spec.v<N>.json` to `spec.v<N+1>.json`, bump `"version"`, apply the changes, `render.py --dry-run` and check that overlays and hits still fall inside their beats and the total is 13–30 s.
4. **Render and prove it.** `$PY render.py spec.v<N+1>.json`, then `check.py <slug>_v<N+1>.mp4 --timeline build/timeline_v<N+1>.json` and Read the sheet. For each feedback item, `sheets.py compare <old.mp4> --at <t>` and `sheets.py compare <new.mp4> --at <t>` at the same seconds, and look at both. If an item is not visibly fixed, adjust once more before handing over.
5. **Hand over.** `open <new mp4>`. In chat: per item, what changed and where (segment, seconds); anything not done and why; the new timeline if lengths moved; new path; previous version kept for comparison. Invite the next numbered list.
6. **Record.** Append to `notes.md`: version, date, feedback items verbatim, changes, checks.

## Hard rules

- Never overwrite an earlier spec or `.mp4`; versions only go up.
- Every item gets an explicit outcome: done, done differently (why), or not done (why).
- Show the changed seconds on a sheet; do not claim a fix from the numbers alone.
- Channel rules still apply (open on the moment, 13–30 s, captions inside safe zones); if the user asks for something that breaks one, do it and note the rule in one line.
- Rights do not change with the edit; repeat the risk line from the build hand-over.
