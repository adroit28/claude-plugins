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
| Clean speech (optional) | `${CLAUDE_PLUGIN_ROOT}/skills/enhance/scripts/clean_speech.py` · own venv `<shorts dir>/.venv-demucs` (not `.venv`) |
| Render, sheets, check, cost | `${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/{setup.sh,render.py,sheets.py,check.py,cost.py}` |
| Frame reader | subagent `football-shorts:spotter` (`agents/spotter.md`, `model: sonnet`) |
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
| `beats:` the user's own beat list, e.g. `0-2 run-up · 2-6 miss 1 · 6-9 replay of miss 1 · 9-12 miss 2 · 12-14 crowd` | none: the spotter maps the video (step 2). When given, step 2 takes the fast path: far fewer frames, no spotter call, and the user's count and grouping are final |

## Procedure

1. **Set up and look.** `bash setup.sh`, create `shorts/<slug>/`, reference the video by absolute path in the spec `sources` (do not copy or modify the user's file). Run `$PY analyse.py <video> --out shorts/<slug>/build` and read what it prints: audio or none, the picture box (letterbox), the `QUALITY:` line, shots with motion, low-motion stretches, loud peaks. Read the shot sheet it writes. If QUALITY says `LOW`, tell the user in one line (picture box size, that it will look soft, a better source if they have one) and wait for a go before rendering; a `{"reframe": ...}` crop (spec-format.md) enlarges the pitch strip of a small picture box.
2. **Map the beats.**

   **Fast path, when the user gave `beats:`.** Their list is the beat table: count, grouping (which clip is a replay of which moment) and dead stretches are theirs and are not re-derived. Only three things still need frames, all read by you (no spotter):
   - **Snap the boundaries.** The user's times are approximate (±0.5 s). Match each boundary to the nearest cut in `analysis.json`; where there is none within 0.5 s, keep the user's time.
   - **Strike and outcome of each key moment.** One `sheets.py fine <video> --from a --to b --fps 10 --width 240 --crop <box>` per key moment, over the ~1.5 s where the strike and outcome should be (not the whole beat). Note the frame the ball leaves the foot and the first frame the outcome is visible. Replays: only when the replay will get its own slow-mo.
   - **Crops.** One `sheets.py frames <video> --at <one time per beat> --crop <box>` for the whole video; read x ranges off the grid.
   If a frame contradicts the list (the "miss" is a goal, a beat shows a different chance, a boundary is off by more than a second), do not silently fix it: note it and raise it in step 3. Write the table into `notes.md` with the user's wording kept, the snapped seconds, strike/outcome frames and x ranges. Then go to step 3.

   **Full mapping (delegated), when there is no `beats:` list.** Looking at every shot frame by frame is the most image-heavy step in the plugin, so the `football-shorts:spotter` subagent does it and only its table comes back. Call the Agent tool with `subagent_type: football-shorts:spotter`, `run_in_background: false`, and:

   ```
   Mode: beats. PY=<venv python>  sheets.py: <abs path>/skills/build/scripts/sheets.py
   Edit folder: <abs shorts/<slug>>
   Video: <abs path>  analysis: <abs>/build/analysis.json  box: <w:h:x:y or none>
   What it is (from the user): <match, player, what the moments are, the user's count if given>
   ```

   Read its verification sheet (the decisive frame of each key moment) and check the grouping against the definitions below; for any row marked unsure or that looks wrong, `sheets.py fine --from --to --fps 10 --crop <box>` that stretch yourself. Copy the corrected beat table into `notes.md`: source seconds, what happens, who is where in the box (x range for the crop). If the Agent tool is unavailable, map it inline: per shot `sheets.py fine --fps 2 --width 240 --crop <box>`, 10 fps only across the strike. Definitions:
   - **Key moments** are what the user made the video for (misses, goals, saves, skills). Count them, and for each note where the shot is and where the outcome is visible (ball past the post, keeper holding it).
   - **Count events, not clips.** A moment is usually shown live, then as an aftermath close-up, then as a slow-mo replay from another angle: that is one moment. Match clips by who is where (same keeper, same post, same shirt numbers, same end position) before calling anything a new chance; when unsure, ask.
   - **Replays belong to their moment**, and are often its only clear view.
   - **Dead stretches** are only what shows no key moment: crowd pans, walking back, graphics.
   - **The payoff** is the most striking frame (often an aftermath or reaction, not the last shot).
   - Analysis numbers are hints: low motion can be a wide replay of the best moment and a soft cut inside a pan can be missed. Decide from the frames, never from the numbers.
3. **Confirm the beats and offer three hooks, then stop.** First the beat list in a few lines: "I count N <misses>: #1 a–b s, #2 …; c–d s is the replay of #k; I will cut <x> (why); planned length ~L s", so the user can correct the count and the grouping before anything is rendered. The user filmed or picked these moments and knows them; their count wins. With a `beats:` list, don't present a count of your own: repeat their list in one line with the snapped times ("your 5 beats, snapped to cuts at 2.08 / 5.92 / …; cutting 12–14 crowd"), plus any frame that contradicted it as a question. A contradiction always stops here, even after "just do it". Then pick the three strongest from `references/hook-playbook.md` for this video (flash-forward, counter, stakes line, question-free challenge, reaction first, etc.), each as one line: what the first 1.5 s shows and says. Recommend one. Wait for the user's pick unless they already said "just do it" or named a hook.
4. **Write `plan.v1.md`, run `plan.py`.** Beats, captions and hits go into a plan (grammar: `../build/references/plan-format.md`, header needs `spine`), and `$PY ../build/scripts/plan.py <edit_dir>/plan.v1.md` writes `spec.v1.json` and prints the timeline; do not hand-write spec JSON. Same order of events as the original unless the hook moves the payoff to the front. Rules:
   - Letterboxed or landscape source → spec-level `"fill": {"box": [...]}` from the analysis; per segment `crop` inside the box picks the foreground window (full box width for wide shots, ~300 px wide on a 478 px box for faces). Never hand over a render that is mostly bars.
   - Open on motion at 0 s with the hook text on frame 1. No flash, fade or title card on the first segment (render.py ignores `flash` there: frame 0 is the scroll thumbnail).
   - Every key moment stays in, complete: build (0.6–1.6 s real speed) → the decisive 0.7–0.8 s in `slowmo` factor 2 with a `zoom` push-in → the outcome at real speed (ball wide, save, players down) → only then the counter or verdict badge with a `bass` + `ding` hit. Never cut a moment before its outcome is on screen. The slow-mo is on the shot itself (find the frame the ball leaves the foot), not on the aftermath. A counter badge shows from the outcome until the next moment's build starts, then clears, so an old number is never on screen during a new chance. A replay of a moment follows it with a "SLOW-MO REPLAY" / "ANOTHER ANGLE" badge and never gets a new number; a source that is already slow-mo plays at its own speed.
   - Reactions: 0.7–1.2 s, tight crop on the face, `zoom` punch (`{"to":1.15,"dur":0.15}`).
   - The funniest or most absurd frame: `boomerang` (t ≤ 0.7) or a `still` freeze with `shake`.
   - Cut dead stretches (as defined in step 2) entirely; do not speed them up.
   - A `whoosh` 0.3 s before each hard cut into a new chance, a `riser` into the final beat, `bass` on freezes and reveals. Silent source → these hits are the whole soundtrack; say that the user should add a sound at upload (Shorts "Add sound") or pass `bed.file`.
   - Captions: a persistent context line at the top (`y_big` 270), badges for counters and verdicts just under the picture (`extra` with `bg`, `emoji` inline), at most six words each, inside the safe zones. Only claims the user or the footage supports: no scores, dates or stats you have not verified.
   - Last beat cuts back into the opening (same moment or same framing) so it loops.
   `plan.py` snaps lengths to frames and places captions and hits from the computed beat starts; read its printed timeline and warnings.
4b. **Clean speech (optional, offer it, never assume it).** Offer it only when a clip you are keeping has speech (a commentator, an interview, a player quote, an anchor) over music or crowd, or when the user asks for "remove the background audio". Not for a plain match clip: the crowd is the sound there.
   - **Needs an explicit yes first.** It installs Demucs and torch into its own venv (`<shorts dir>/.venv-demucs`, ~1 GB) and downloads the `htdemucs` model (~80 MB) once. Ask in one line ("Clean the speech with Demucs? One-time install and model download, ~1 GB, then ~1 min of CPU per 10 s"), wait for a yes, and treat it as covering that install only. Without a yes, keep the original audio and say so. `clean_speech.py` downloads nothing unless run with `--install`; without the venv it prints the install line and exits 2.
   - **Run it only on the speech seconds**, one call per section, with the same in/out as the segments (about 10 s in total, not the whole file): `python3 clean_speech.py <video> --ss <src s> --t <len> --out build/clean/<label>.wav --keep-work` (the first call after `--install` may take longer while the model loads). It cuts, separates the voice, then (default `--strength strong`) removes the music tones and sub-bass Demucs leaves in the voice stem (steady-spectrum mask + 110 Hz highpass; `mid` is gentler, `off` is Demucs only), matches the loudness to the original cut with a limiter, writes a 48 kHz wav, and prints a verdict from measurements: voice body 300–3000 Hz (thin if it drops over 1.5 dB), speech-to-floor gap (should widen), spectral holes at 1–8 kHz (a coarse watery signal: flagged above +40 points, and background removal raises it too, so ears decide).
   - **Still too loud?** Demucs alone widens the speech-to-background gap only to ~10 dB on a music bed; the mask takes it to ~14-17 dB. A second Demucs pass or a gate adds nothing (tried). If the voice turns watery, use `--strength mid`, then `off`.
   - **Fallback: keep the original.** On `verdict: KEEP ORIGINAL`, or when the user says it sounds thin, watery or robotic, leave the clip's own audio as it is. The script measures, it does not listen: say that, and give the user `build/clean/<label>.orig.wav` next to `<label>.wav` to compare by ear.
   - **Use it in the spec** with ops, not by editing JSON: `spec.py spec.vN.json bump -- set seg:<label>.mute=true -- hit add @<label> file=build/clean/<label>.wav volume=1.0` (in a plan: `mute=true` on the beat plus a `hits` line `<at> file=build/clean/<label>.wav volume=1.0`). `loudnorm` still runs last, so the usual target holds. A `file` hit lands at the exact second, which also removes the small lag segment concatenation can add to a clip's own audio.
   - Speech cut into pieces or sped up: clean each piece from the source, not the rendered file. Separation costs the background and a little air, so never run it on audio that is already clean.
5. **Render and score.** `$PY render.py spec.v1.json`, then `$PY check.py <slug>_v1.mp4 --timeline build/timeline_v1.json --spec spec.v1.json` and Read the sheet. Fix any FAIL in the retention block, black or mostly-bar frames (`verdict` line), cropped faces, emoji colliding with text, captions over the subject. At most one internal pass (a new version; compare it with `sheets.py compare <new> --ref <old> --at <changed seconds>` rather than a whole new sheet when only captions, timing or sound moved), then hand over.
6. **Hand over.** Write the step 8 record first (revise may run in a fresh session that has only the files), then run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/build/scripts/cost.py --step enhance --slug <slug>` from the project root. `open <mp4>`. In chat: path, length vs original, the beat table (output time · source time · beat · effect), captions in order, the hook chosen and why, what was cut from the original, sound situation, rights (below), what was not verified, the cost lines. End with: send changes as numbered points; for a cheaper revision start a new session and paste `/football-shorts:revise slug: <slug>` followed by the list, or reply here to continue.
7. **Upload kit (when asked, or offer it).** Title, description, hashtags, pinned comment and a sound: use `/yt-insights:metadata` when that plugin is installed (channel voice from its top performers), otherwise `../build/references/channel-style.md`. For sound, name tracks to pick from the Shorts "Add sound" library at upload (licensed there for Shorts) and say where the drop should land on the edit's timeline; never download or mux commercial music into the file.
8. **Record.** `notes.md` with a `## State` block on top (≤20 lines: latest version, source with rights and QUALITY line, standing decisions, open questions) and an `## Appendix`: source file, analysis summary, the user's `beats:` list verbatim if given, beat table (with moment grouping), hook options offered and the pick, version log with the user's corrections verbatim.

## Hard rules

- Never modify, move or re-encode the user's original file; it is only a source.
- Never drop or truncate a key moment the user captured, and never cut a stretch you have not looked at frame by frame. If the edit must lose a moment (length), ask.
- Keep the story: do not cut a moment so it implies something that did not happen (e.g. show a miss that was a goal, or a reaction to a different chance), and do not caption facts the footage does not show.
- Broadcaster or club footage keeps its Content ID risk however it is edited. Say so once; never claim zooms, speed changes, mirroring, sound effects or overlays make it safe.
- One spec per version; never edit a rendered version's spec in place.
- Demucs (step 4b) is installed and its model downloaded only after an explicit yes for that install; any other download needs its own yes. Keep the original audio whenever the cleaned speech is flagged or sounds worse.
- Report what the check sheet and retention block show, including problems you could not fix.
- Every Short ends with the channel's like & subscribe card, 3 s by default and never under 2.5 s (spec `outro_s`). the build skill's `render.py` appends it with `outro.py`, so a normal render has it; `check.py` warns when it is missing. Never set `"outro": false` unless the user says so for that video. The 13–30 s length rule counts the content, not the card.
