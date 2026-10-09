---
name: revise
model: sonnet
description: Apply the user's numbered feedback to a finished talking-head Short as a new version - maps each comment (a caption word, a timing, a punch-in, a cutaway, a number pill, a slam, the hook, sound, the background) to ops on the edit spec, writes edit.v<N+1>.json, re-renders and re-mixes, keeps every earlier version, and proves each change with before/after frames. Use when the user says "change the caption at 7 s", "the hook is weak", "move the cutaway", "make the zoom less", "different background placement", or invokes /talking-head-shorts:revise.
---

# Revise from numbered feedback

The spec is the source of truth; every revision is a new `edit.v<N+1>.json` and a new `<slug>_v<N+1>.mp4`. Earlier specs, raws, builds and finals stay.
Works in a fresh session: read `shorts/<slug>/notes.md` State, `$PY -I $S/spec.py show shorts/<slug>` and the latest sheet; do not ask for the earlier conversation.

## Procedure

1. **Locate.** Latest version, then `spec.py show` for the timeline. A time the user names ("at 7 s") is OUTPUT time unless they say source: source = output - hook length
   + window start. Say which beat it is.
2. **Translate.** One line per item: `#k "<their words>" -> <op>`. Common maps:
   - wrong or late word: `caption <t> NEW`, `retime <t> <start> <end>` (words from the audio: check against the transcript, caption in source seconds)
   - hook weak: `set hook {...}` (cold / slam / image), `set hook_sfx [...]`
   - too much zoom / too little: `set steps [[0,1.0],[2.0,1.08],...]`, `set drift 0.01`
   - cutaway too long / wrong spot / wrong ring: `set cutaways[i].from 3.1`, `set cutaways[i].ring [0.5,0.4]`, `delete cutaways[i]`
   - number pill/counter timing: `set pills[0].pills[1].at 10.5`, `set counters[0].value 10`
   - slam: `append slams {...}`, `set slams[i].top 330`
   - hot words: `hot add WORD` / `hot del WORD`; colours `set style.accent "#00E5FF"`
   - sound: `append sfx [...]`, `delete sfx[i]`, `set music {"drone":false}`
   - everything after t moves: `shift <from_t> <delta>`
   - background placement: `set bg.left -250`, `set bg.top -300`, `set bg.brightness 0.7`; a new matte window: back to the `background` stage
   - captions changed in bulk: the user's new text -> `captions.txt` -> `captions.py` -> `set phrases @captions.json#phrases`
   Write the ops to `shorts/<slug>/v<N>to<N+1>.ops`.
3. **New version.** `$PY -I $S/spec.py bump shorts/<slug> --ops shorts/<slug>/v<N>to<N+1>.ops` prints the diff and warnings. Never open the JSON to edit it.
4. **Render and prove.** `build.py shorts/<slug> --render` (a still first when the change is visual) then `finish.py shorts/<slug>`. For each item, one
   before/after sheet: `$PY -I $S/sheets.py compare shorts/<slug>/<slug>_v<N+1>.mp4 shorts/<slug>/v<N+1>_changes.png --ref shorts/<slug>/<slug>_v<N>.mp4 --at <t1> <t2> ...`
   (same output second in both; if lengths moved use the matching beat) and LOOK at it. Not visibly fixed: adjust once more before handing over.
5. **Record.** `notes.md`: State block (latest version, length, decisions, open questions) and an appended log line (version, date, the user's items verbatim, ops file).
6. **Cost.** `$PY -I $S/cost.py --step "revise v<N+1>" --slug <slug>`.
7. **Hand over.** Per item: what changed and where (seconds); anything not done and why; new path; the previous version kept for comparison; cost lines; `NEXT.md`
   with `/talking-head-shorts:revise slug: <slug>` for the next round.
8. **One round per session.** More feedback in the same session: one line pointing to a fresh `/talking-head-shorts:revise slug: <slug>` session (the context is paid for
   again on every turn), unless the user writes `continue here`.

## Hard rules

Never overwrite an earlier mp4 / spec / raw. Caption exactly the user's words. No fact-check caveats on screen. If a change is not expressible in the spec, say so and propose a
template change in the plugin instead of editing the generated project.

## Multi-clip slugs (a `timeline.py` exists)

Same rules, different source of truth: edit `shorts/<slug>/timeline.py` (cuts, captions, marks, sfx, keep windows) or `anim/src/Scenes.tsx` (graphics), never the JSON. Copy the
current file to `timeline_v<N>.py` first; run `timeline.py run`, then `wordqa.py` (changed seconds only matter, but the check is cheap), `build.py --timeline --render`,
`mix_multi.py`, `finish_tl.py`. Times the user gives are REEL seconds of the version they watched; a cut that moves things shifts later times, so say by how much.
One step at a time with the Step protocol (stop, cost line, ask) in `make/SKILL.md`. Feedback prompt the user can paste:

```
Continue <slug>. Read only shorts/<slug>/notes.md (State), timeline.py and the frames I name.
My feedback on <slug>_v<N>.mp4 (times are reel seconds):
1. [time] [what you see or hear] -> [what you want]
2. ...
Apply as v<N+1> (never overwrite earlier versions), check the changed seconds with before/after frames, report the cost after each step and ask before the next.
```
