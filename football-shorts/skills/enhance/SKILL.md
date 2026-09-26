---
name: enhance
description: Take a football video the user already has (a clip, a compilation, a re-upload, a screen recording, landscape or vertical, with or without sound) and re-edit it into a more watchable 9:16 Short without changing its story. Maps the video's shots, letterbox and dead air, offers three hook options, then adds a cold open, counters, slow-mo on each chance, punch-ins, reaction beats, a freeze, synthesised sound effects and a loop ending, renders it with the build skill's renderer and scores retention. Use when the user says "make this video more attractive", "add hooks to my video", "edit this clip", "spice up this video", "polish this short", "enhance ~/Downloads/x.mp4", or invokes /football-shorts:enhance.
---

# Enhance a video the user hands over

`build` makes a Short from sources and a brief. `enhance` starts from one finished
video and keeps its story: same moments, same order of events, but with a hook in
the first second, something new every 1.5–3 s, and an ending that loops. The
output is an ordinary spec version, so `/football-shorts:revise` works on it
unchanged.

## Paths

| What | Where |
|---|---|
| Edit folder | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Inside it | `spec.vN.json` · `build/analysis.json` · `build/sheets/` · `<slug>_vN.mp4` · `notes.md` |
| Analyse | `${CLAUDE_PLUGIN_ROOT}/skills/enhance/scripts/analyse.py` |
| Render, sheets, check | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{setup.sh,render.py,sheets.py,check.py}` |
| Python | `PY=<shorts dir>/.venv/bin/python` from `setup.sh` |
| References | `references/hook-playbook.md` (this skill) · `../build/references/spec-format.md` · `../build/references/channel-style.md` |

## Inputs

| Input | Default |
|---|---|
| Video path (local file) | required; a URL goes through the build skill's fetch step and its authorisation rule |
| `slug:` | from the file name, kebab-case |
| `length:` | follows the content: every key moment kept complete, only the gaps between them trimmed; usually close to the original. Over 30 s: say so and offer a shorter cut, do not decide alone |
| `hook:` | ask (three options, step 3) unless the user named one |
| What the video is about (match, player, date) | from the user's message; never invented |

## Procedure

1. **Set up and look.** `bash setup.sh`, create `shorts/<slug>/`, reference the video by absolute path in the spec `sources` (do not copy or modify the user's file). Run `$PY analyse.py <video> --out shorts/<slug>/build` and read what it prints: audio or none, the picture box (letterbox), shots with motion, low-motion stretches, loud peaks. Read the shot sheet it writes.
2. **Map the beats.** For every shot, including the low-motion ones, `sheets.py fine <video> --from a --to b --fps 4 --crop <box as w:h:x:y>` and read the frames (10 fps around a shot to find the frame the ball leaves the foot). Write a beat table in `notes.md`: source seconds, what happens, who is where in the box (x range for the crop). Then:
   - **Key moments** are what the user made the video for (misses, goals, saves, skills). Count them, and for each note where the shot is and where the outcome is visible (ball past the post, keeper holding it).
   - **Count events, not clips.** A moment is usually shown live, then as an aftermath close-up, then as a slow-mo replay from another angle: that is one moment. Match clips by who is where (same keeper, same post, same shirt numbers, same end position) before calling anything a new chance; when unsure, ask.
   - **Replays belong to their moment**, and are often its only clear view.
   - **Dead stretches** are only what shows no key moment: crowd pans, walking back, graphics.
   - **The payoff** is the most striking frame (often an aftermath or reaction, not the last shot).
   - Analysis numbers are hints: low motion can be a wide replay of the best moment and a soft cut inside a pan can be missed. Decide from the frames, never from the numbers.
3. **Confirm the beats and offer three hooks, then stop.** First the beat list in a few lines: "I count N <misses>: #1 a–b s, #2 …; c–d s is the replay of #k; I will cut <x> (why); planned length ~L s", so the user can correct the count and the grouping before anything is rendered. The user filmed or picked these moments and knows them; their count wins. Then pick the three strongest from `references/hook-playbook.md` for this video (flash-forward, counter, stakes line, question-free challenge, reaction first, etc.), each as one line: what the first 1.5 s shows and says. Recommend one. Wait for the user's pick unless they already said "just do it" or named a hook.
4. **Write `spec.v1.json`.** Same order of events as the original unless the hook moves the payoff to the front. Rules:
   - Letterboxed or landscape source → spec-level `"fill": {"box": [...]}` from the analysis; per segment `crop` inside the box picks the foreground window (full box width for wide shots, ~300 px wide on a 478 px box for faces). Never hand over a render that is mostly bars.
   - Open on motion at 0 s with the hook text on frame 1. No flash, fade or title card on the first segment (render.py ignores `flash` there: frame 0 is the scroll thumbnail).
   - Every key moment stays in, complete: build (0.6–1.6 s real speed) → the decisive 0.7–0.8 s in `slowmo` factor 2 with a `zoom` push-in → the outcome at real speed (ball wide, save, players down) → only then the counter or verdict badge with a `bass` + `ding` hit. Never cut a moment before its outcome is on screen. The slow-mo is on the shot itself (find the frame the ball leaves the foot), not on the aftermath. A counter badge shows from the outcome until the next moment's build starts, then clears, so an old number is never on screen during a new chance. A replay of a moment follows it with a "SLOW-MO REPLAY" / "ANOTHER ANGLE" badge and never gets a new number; a source that is already slow-mo plays at its own speed.
   - Reactions: 0.7–1.2 s, tight crop on the face, `zoom` punch (`{"to":1.15,"dur":0.15}`).
   - The funniest or most absurd frame: `boomerang` (t ≤ 0.7) or a `still` freeze with `shake`.
   - Cut dead stretches (as defined in step 2) entirely; do not speed them up.
   - A `whoosh` 0.3 s before each hard cut into a new chance, a `riser` into the final beat, `bass` on freezes and reveals. Silent source → these hits are the whole soundtrack; say that the user should add a sound at upload (Shorts "Add sound") or pass `bed.file`.
   - Captions: a persistent context line at the top (`y_big` 270), badges for counters and verdicts just under the picture (`extra` with `bg`, `emoji` inline), at most six words each, inside the safe zones. Only claims the user or the footage supports: no scores, dates or stats you have not verified.
   - Last beat cuts back into the opening (same moment or same framing) so it loops.
   `render.py spec.v1.json --dry-run`, copy overlay and hit times from the timeline.
5. **Render and score.** `$PY render.py spec.v1.json`, then `$PY check.py <slug>_v1.mp4 --timeline build/timeline_v1.json --spec spec.v1.json` and Read the sheet. Fix any FAIL in the retention block, black or mostly-bar frames, cropped faces, emoji colliding with text, captions over the subject. At most two internal passes (each a new version), then hand over.
6. **Hand over.** `open <mp4>`. In chat: path, length vs original, the beat table (output time · source time · beat · effect), captions in order, the hook chosen and why, what was cut from the original, sound situation, rights (below), what was not verified. End with: send changes as numbered points and run `/football-shorts:revise`.
7. **Upload kit (when asked, or offer it).** Title, description, hashtags, pinned comment and a sound: use `/yt-insights:metadata` when that plugin is installed (channel voice from its top performers), otherwise `../build/references/channel-style.md`. For sound, name tracks to pick from the Shorts "Add sound" library at upload (licensed there for Shorts) and say where the drop should land on the edit's timeline; never download or mux commercial music into the file.
8. **Record.** `notes.md`: source file, analysis summary, beat table (with moment grouping), hook options offered and the pick, version log with the user's corrections verbatim.

## Hard rules

- Never modify, move or re-encode the user's original file; it is only a source.
- Never drop or truncate a key moment the user captured, and never cut a stretch you have not looked at frame by frame. If the edit must lose a moment (length), ask.
- Keep the story: do not cut a moment so it implies something that did not happen (e.g. show a miss that was a goal, or a reaction to a different chance), and do not caption facts the footage does not show.
- Broadcaster or club footage keeps its Content ID risk however it is edited. Say so once; never claim zooms, speed changes, mirroring, sound effects or overlays make it safe.
- One spec per version; never edit a rendered version's spec in place.
- Report what the check sheet and retention block show, including problems you could not fix.
