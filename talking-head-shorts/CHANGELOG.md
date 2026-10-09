# Changelog

## 0.2.0 (2026-10-09, uncommitted)
Additive: the single-source flow (spec.py, build.py <spec>, mix.py, finish.py) is unchanged. Source of the learnings: the Westside reel (v1-v4).
- **Step protocol** (make/SKILL.md): every step of every skill ends with a 4-line report, `cost.py` lines, one question and a STOP; build now stops too. Handoff pattern for `NEXT.md` with a cost line per step.
- **timeline skill** (T1-T11): the multi-clip route. docs/multi-clip.md is the data contract.
- **A, timeline**: `timeline.py` (Timeline class: add/O/cap/mark/shake/flash/whip/sfx/keep/music, gap compression, holds, speed, picture-only inserts; writes timeline.json + cues.json, prints the chunk table with seconds cut out; init/run/check) and `locate.py` (pre-joined source: FFT cross-correlation of each take's chunks against the user's joined file, per-clip offsets, vid/ca on the 30 fps grid, NOT FOUND / OFFSET DISAGREES flags, re-runs the timeline).
- **B, intake + words**: `normalize.py` (CFR 30, lanczos + light unsharp when upscaled > 1.3x, no silent crop of non-9:16, untouched audio + 16 kHz copy, soft-source warning), `retake.py` (repeated-opening hint), `wordqa.py` (Whisper hi+en on the cut voice, SAID vs CAPS per chunk, uncaptioned speech >= 0.15 s, caption over silence >= 0.35 s, sfx on a key word).
- **C, audio**: `mix_multi.py` (voice cut from the sources, optional denoise, ducked music bed with gain keys, sfx-vs-speech resolver: shift <= 0.12 s / trim with fade / drop, per-cue maxlen, KEEP windows, sfx_resolved.json, tanh limiter, two-pass loudnorm -14 / TP -1.5, optional mux), `synth.py` (23 extra sfx + a music bed, deterministic), `finish_tl.py` (version file, sheet, loudness check, outro off by default).
- **D, face + graphics**: `track.py` + `face.swift` (cv2 haar, else Apple Vision; track.json for zoom origin and tracked props); Remotion template gets the `Multi` composition, `src/kit/` (news hook + ticker, glow-up wipe, 3D title, shopping list, rev gauge, card + PIN, balance counter + glitch slam, share sheet, salary/calendar SMS, garland, traffic map, NAYA stamp + size bar, maps nav, chat + loading-bar CTA, bhook meter, removable extras, end card with no football outro) and a per-slug `Scenes.tsx` where each scene is one removable line; `build.py --timeline`.
- build.py: the target path is resolved to absolute (a relative `shorts/<slug>` made Remotion fail from the anim folder).
- **E, skill text**: joke map, safe zones, jump-cut zoom alternation, soft-source lessons, sound questions up front, numbered-feedback template for timeline slugs (revise), pointers in intake/plan/build/finish.

## 0.1.1 (2026-10-09)
- intake: new step 0, ask whether noise is already removed / takes already joined (use the user's combined file as the source, no denoise) and for the language/transcript.
- plan: restraint rules (few graphics, none that only illustrate a word, nothing on the face, no sfx over speech, keep key words, confirm graphics list first).

## 0.1.0 (2026-10-09, first version, uncommitted)
- New independent plugin; ideas and code copied in from facts-shorts / football-stories / the ronaldo-7-leao edit, nothing imported at runtime.
- Stages as skills: `make` (order, stops, handoffs, cost), `intake` (probe, blink pre-pass, crop/blurfill choice, Whisper, unclear stretches, caption alignment),
  `plan` (beat-mapper subagent on sonnet, plan table, table-to-spec), `background` (RVM matte test, edge sheet stop, full matte, bg spec),
  `build` (Remotion from template), `finish` (mix + outro + sheet + loudness), `revise` (numbered ops -> new version).
- scripts: probe, transcribe, captions, beatmap, sheets, spec (init/fill/validate/show/bump with ops), build, matte, edge_sheet, sfx, mix, finish, outro, cost, setup.sh.
- template: Remotion 4.0.530, `src/Short.tsx` reads `edit.json` (hook cold/image/slam, person layer with punch-in steps + drift + shakes, cutaways, pills, counters, slams,
  flashes, word-by-word captions with HOT words, bg swap with parallax/grade/glow/blink dip, fit cover/crop/blurfill). Anton font bundled (OFL).
- first use: dry run on the first 8 s of shorts/ronaldo-7-leao/source.mp4 (shorts/th-dryrun/): v1 reproduces the Ronaldo look, v2 background swap on a 5.9 s window via revise ops.
- known gaps: no silence/jump-cut remover, no inner rim light, Whisper word times are coarse on long words (interpolated words are listed for checking), music is only the drone.
