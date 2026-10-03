---
name: revise
description: Apply the user's numbered feedback to a facts-channel Short as a new version (story.vN+1.json, <slug>_vN+1.mp4) - script wording, a cut beat, voice or pace, word timing, visuals, props, sound effects, photos - re-voicing only when the words change, keeping every earlier story, scene and mp4, and proving each fix with before/after frames. Use when the user says "change line 3", "at 12 s the photo is wrong", "cut the phone-book beat", "faster", "different hook", "the counter jumps", or invokes /facts-shorts:revise.
---

# Revise

Numbered feedback in, the next version out, with proof. Nothing earlier is overwritten.

## Paths

| What | Where |
|---|---|
| Short folder | `<root>/<slug>/`: highest `story.v<N>.json`, `<slug>_v<N>.mp4`, `build/scene_v<N>.tsx`, `build/segments.json`, `notes.md` |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{validate.py,tts.py,segalign.py,anim.py,sfx.py,commons.py,cost.py}` |
| References | `../script/references/style.md`, `../video/references/template.md` |

## Procedure

1. **Locate.** Latest story and mp4. Map each time the user names ("at 12 s") to a line and word via `build/words_segments.json` (subtract nothing: the words already include the lead). Say which.
2. **Translate** each item into one line: `#k "<their words>" → <change> → <steps to re-run>`.

   | Change | Edit | Re-run | Voice cost |
   |---|---|---|---|
   | Visual, prop, photo position, sfx, timing of a pop | `anim/src/Scene.tsx` | render | none |
   | New photo | Commons search → user's yes → `commons.py get` | sync → render | none |
   | Caption spelling (same words spoken) | the line's `text` (copy the old text into `tts` first if it has none) | segalign `--segments` (same audio) → render | none |
   | A word lands early/late | `build/segments.json` groups, or the scene's anchor word | segalign `--segments` → render | none |
   | Pace | `tts.py --from-take ... --pace p` | segalign → render | none |
   | Script wording, cut/add a beat, new hook | `narration.lines` (new claims: verify first) | validate → one new take → segalign → scene anchors → render | one free take |
   | Voice | narrate with the new voice | take → segalign → render | one free take per voice |
3. **New version.** Copy `story.v<N>.json` → `story.v<N+1>.json`, set `"version": N+1`, drop `anim.render`, apply edits. Scene changes: edit `anim/src/Scene.tsx` (v<N>'s scene is kept as `build/scene_v<N>.tsx`). New claims: `facts-shorts:fact-finder` in verify mode, spot-check, add to `verify.md` (a dated "Revision" section) before they're narrated. Re-voice only if the spoken words change; confirm first if it would be on the paid key.
4. **Render + prove.** `python3 anim.py render story.v<N+1>.json --at <the seconds of each item in the new timing>`. Then a before/after: `anim.py check` on the old mp4 is already in `build/check/`; compare the `_at` sheets of both versions at the same beats (times move when words change, so pick the same word's time in each). Read them; if an item isn't visibly fixed, adjust once more.
5. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "revise v<N+1>" --slug <slug>`.
6. **Hand over.** `open` the new mp4. Per item: done / done differently (why) / not done (why), with seconds; new duration; any channel rule it now breaks (over 40 s etc., one line); the previous version kept; cost lines. Append to `notes.md` (version, date, feedback verbatim, changes, cost). If metadata depends on changed lines, suggest `/facts-shorts:metadata`.

## Hard rules

- Never overwrite an earlier story, scene snapshot or mp4; versions only go up.
- Every item gets an explicit outcome, shown on a frame sheet, not claimed from numbers.
- One free take per request; paid only if asked. No downloads without a yes.
- The like & subscribe card stays (3 s, never under 2.5 s).
