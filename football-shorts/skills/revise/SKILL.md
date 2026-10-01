---
name: revise
model: sonnet
description: Apply the user's numbered feedback to an existing football Short built by /football-shorts:build. Maps each comment (seconds, beats, captions, length, missing face, boring opening) to changes in the JSON edit spec, bumps the version, re-renders only what changed, verifies the changed seconds with before/after frames, and hands over the new file. Use when the user says "change the opening", "at 7 seconds his face is missing", "make it 20 seconds", "different caption", "redo the ending", or invokes /football-shorts:revise.
---

# Revise a Short

Feedback in, next version out, with proof of the change. The edit spec is the
source of truth; every revision is a new spec version and a new file.

## Paths

| What | Where |
|---|---|
| Edit folder | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/` (latest `spec.v<N>.json`, `build/timeline_v<N>.json`, `notes.md`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{spec.py,render.py,check.py,sheets.py,fetch.py,cost.py}` with `PY=<shorts dir>/.venv/bin/python` |
| Ops reference | `${CLAUDE_PLUGIN_ROOT}/skills/build/references/plan-format.md` (spec.py ops and the beat-line grammar); `spec-format.md` only when a field's meaning is unclear |

## Inputs

| Input | Default |
|---|---|
| Feedback (numbered list, or prose you number yourself) | required |
| `slug:` | the edit folder most recently rendered under `shorts/` |
| `length:` | keep current unless the feedback changes it |

## Procedure

1. **Locate the version.** Find the highest `spec.v<N>.json` in the edit folder. Read only the `## State` block of `notes.md` (`sed -n '/^## State/,/^## Appendix/p' notes.md`) and `build/timeline_v<N>.json`; open the appendix only for an item State points at. Do not read the spec JSON whole: `spec.py spec.v<N>.json --dry --quiet set x=x` is not needed, the timeline plus `grep -n` for a label or caption text is. These files are the whole context: revise is meant to work in a fresh session, so do not ask for the earlier conversation. If the user names a time ("at the 7th second"), the timeline tells you which segment that is; say so.
2. **Translate feedback into ops.** One line per item: `#k "<their words>" → <spec.py op>`. Typical mappings: "still at the start, people drop off" → `drop <still>` and `caption set ov:"HOOK" from=0`; "face missing at 7 s" → `sheets.py frames --at` around that source time, read the head position off the grid, `set seg:<label>.crop=[500,889,x,y]`; "more comic" → `replace <card> with <src> <in> +<len> reverse:x1.25 - -` (or `boomerang:x2`, `split`, `slowmo:x2`); "mostly black / tiny picture" → `set fill={...}` with the box from `enhance/scripts/analyse.py`, narrower `crop`; "needs more punch" → `set seg:<label>.zoom={"to":1.15,"dur":0.15}`, `hit add @<label>-0.3 whoosh`, `riser`; "make it 20 s" → `shift <middle beat> -0.6` per beat, keep hook and payoff (captions and hits ripple by themselves); "different caption" → `caption set ov:"OLD TEXT" text="NEW|TEXT"` (re-render takes seconds); "remove the slow-mo rebuilds" → `replace "G9 run-up".."G9 net" with v 24.0 +1.64 clip - - crop=@ label="G9"`. Anything that needs a new source goes through the build skill's fetch step and the same authorisation rule.
3. **New version by ops.** Write the ops to `build/v<N>to<N+1>.ops` (first line `bump`, one op per line, `--fx fx.v<M>.json` when the edit has track.py layers), then `$PY spec.py spec.v<N>.json --ops build/v<N>to<N+1>.ops`. It writes `spec.v<N+1>.json` and prints, per op, what moved and the new timeline; check that overlays and hits still fall inside their beats and the total is 13–30 s, then paste the diff lines that matter into the hand-over. Never open the JSON to edit it; if an op cannot express a change, say so and use `set` on the exact path.
4. **Render and prove it.** `$PY render.py spec.v<N+1>.json`, then `check.py <slug>_v<N+1>.mp4 --timeline build/timeline_v<N+1>.json --spec spec.v<N+1>.json`. Read its sheet only if the `verdict` says LOOK or the revision added new cuts, crops or sources; otherwise the numbers are enough. For the feedback items, one side-by-side sheet: `sheets.py compare <new.mp4> --ref <old.mp4> --at <t1> <t2> ...` (one time per item, the same second in each version, or the matching beat if lengths moved) and look at it. If an item is not visibly fixed, adjust once more before handing over.
5. **Record.** In `notes.md`: update the `## State` block (latest version, length, verdict, any new standing decision or open question; keep it at 20 lines or fewer) and append to the `## Appendix` version log: version, date, feedback items verbatim, the ops file name, checks.
6. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/cost.py --step "revise v<N+1>" --slug <slug>`.
7. **Hand over.** `open <new mp4>`. In chat: per item, what changed and where (segment, seconds); anything not done and why; the new timeline if lengths moved; new path; previous version kept for comparison; the cost lines. End with: for the next round start a new session and paste `/football-shorts:revise slug: <slug>` with the list (everything is on disk), or write `continue here` to stay in this one.
8. **One round per session.** If more feedback arrives in the same session after the hand-over, do not act on it: reply with one line pointing to a fresh `/football-shorts:revise slug: <slug>` session (the context here is paid for again on every turn). The exception is the user writing `continue here`, which means do it in this session.

## Hard rules

- Never overwrite an earlier spec or `.mp4`; versions only go up. The model writes ops, `spec.py` writes JSON.
- One feedback round per session unless the user writes `continue here`.
- Every item gets an explicit outcome: done, done differently (why), or not done (why).
- Show the changed seconds on a sheet; do not claim a fix from the numbers alone.
- Channel rules still apply (open on the moment, 13–30 s, captions inside safe zones); if the user asks for something that breaks one, do it and note the rule in one line.
- Rights do not change with the edit; repeat the risk line from the build hand-over.
