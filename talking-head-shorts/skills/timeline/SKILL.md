---
name: timeline
description: Multi-clip route for talking-head Shorts - several takes of one script cut into chunks with gaps compressed, picture-only inserts and holds, optionally against a joined/cleaned file the user already made (locate.py finds each take inside it), with CFR 30 + lanczos intake, a Whisper word check of the cut voice, a graphics kit (every scene one removable line), Apple Vision face tracking, a mix with ducked music and a no-sfx-over-speech resolver, and one stop with a cost report after EVERY step. Use when the user has several clips of one reel, a joined/cleaned file plus the original takes, wants b-roll inserts or graphics on a talking head, or invokes /talking-head-shorts:timeline. The single-take flow stays in intake/plan/build/finish.
---

# Multi-clip timeline (steps T1-T11)

Data contract and folder layout: `${CLAUDE_PLUGIN_ROOT}/docs/multi-clip.md` (read it once). Scripts in `$S`, python `$PY -I`, slug folder `shorts/<slug>/`.
The Step protocol in `make/SKILL.md` applies to EVERY step below: do it, check it, 4 lines, `cost.py`, ask "go on to <next>?", STOP.
Fresh-session offers after T7 and T9. Use a sonnet subagent for mechanical runs (normalize, transcribe, tracking, renders of stills); decisions stay here.

| # | Step | What happens | The user decides |
|---|---|---|---|
| T1 | **Clips and questions** | Link every original take into `clips/` (never re-encode them). One message, only what is missing: is there a joined/cleaned file (it becomes the joined source: picture AND voice, no denoise)? is noise already removed? language/transcript (their words beat Whisper for Hinglish)? **which scenes get sound** (see Sound)? graphics at all (restraint, see below)? | answers |
| T2 | **Normalize** | `normalize.py shorts/<slug>`: video-only CFR 30, 1080x1920 (lanczos, light unsharp when upscaled > 1.3x), untouched 48 kHz audio and 16 kHz copy. A non-9:16 source is NOT cropped silently: ask fit cover/crop/blurfill. Report each clip's size, fps, soft-source warning | fit for non-9:16 |
| T3 | **Words** | Transcribe each take (local Whisper small). `retake.py` flags a repeated opening line (a retake: ask which take is real). List unclear stretches with timestamps and ASK; caption exactly what the user writes. Never guess | unclear words, which take |
| T4 | **Cut** | Write `timeline.py` (`timeline.py init`): chunks (id, clip, in, out, zoom steps), holds, picture-only inserts, captions with HOT words. Cut at sentence boundaries / pauses, drop retakes and dead air, alternate framing across every jump cut (1.00 -> 1.10 -> 1.20 -> back; never the same scale on both sides of a cut). `timeline.py run` prints the chunk table with the seconds cut out of each take: show it | the cut |
| T5 | **Locate** (joined file only) | `locate.py shorts/<slug> --joined <name>`: finds every chunk in the joined file, prints the table, writes `offsets.json`, re-runs the timeline so chunks get `vid`/`ca` (picture and voice from the joined file). Any NOT FOUND / OFFSET DISAGREES chunk: look at it before going on (usually a stretch the user cut from the joined file) | what to do with flagged chunks |
| T6 | **Word QA** | `wordqa.py shorts/<slug>`: Whisper hi + en on the CUT voice, SAID next to CAPS per chunk, speech with no caption >= 0.15 s, caption over silence >= 0.35 s, sfx over a key word. Fix the timeline, re-run until clean. Spoken words that a removed graphic used to carry need captions. A cue on a key word hides it (the "kangali" bug) | nothing unless a word is unclear |
| T7 | **Plan graphics (joke map)** | One table: line -> visual gag -> sfx -> mark (see Joke map). Propose few; the user drops/keeps each BEFORE any is built. Face tracking is needed only for props that follow the face | which graphics, which scenes get sound |
| T8 | **Track faces** | `track.py shorts/<slug>` (cv2 haar, else Apple Vision via face.swift). Check with `--check <clip>`: face y should sit in the safe face zone | none |
| T9 | **Build** | `build.py shorts/<slug> --timeline --still <t>` for 3-4 stills first (graphics, captions, face zone), then `--render` -> `anim/out/raw_v<N>.mp4`. Scenes live in `anim/src/Scenes.tsx`, one `s(from, to, <Scene/>)` line each: removing a scene = deleting its line | looks right? |
| T10 | **Sound** | `mix_multi.py shorts/<slug>`: voice cut from the sources, ducked music, sfx resolver table (kept/shifted/trimmed/dropped), `keep` windows for the scenes the user chose, loudnorm -14 / TP -1.5. Show the table. If the middle is quiet, add KEEP windows or sfx under keywords at about -18 dB, with the user's OK | which cues to allow over speech |
| T11 | **Finish** | `finish_tl.py shorts/<slug>`: `<slug>_v<N>.mp4`, 12-frame sheet, loudness check. Never overwrite an earlier version. Then feedback via `revise` (timeline form) | feedback |

Every re-run after feedback is a NEW version: `raw_v<N+1>.mp4`, `build_v<N+1>.mp4`, `<slug>_v<N+1>.mp4`. Keep a copy of the previous `timeline.py` as `timeline_v<N>.py`
before editing.

## Joke map (T7)

For each spoken line that could get a visual: `line (time) -> gag (what appears, 1 s) -> sfx (name, where) -> mark (named moment it hangs off)`. Test every row: does the joke
land without the graphic? Then cut it. Roughly 5-7 graphics per 50 s; plain talking head between them is correct. Never a graphic that only illustrates a word. Never on the face
(crowds, masks, manes, props on the head) unless the user asks and the tracked face point is checked. A graphic must end before the next spoken word it would cover.

## Safe zones (1080x1920)

Graphics y 240-760 (above the face). Face y 900-1250 (keep it clear; check with track.json). Captions y 1318-1548 (top 1318, 3 lines never taller than 230 px).
Instagram/Shorts UI margins: nothing important in the top 220 px, bottom 330 px, or the right 160 px strip. Soft sources (e.g. 478x850 upscaled): zoom no more than about 1.3,
no thin text, keep graphics crisp and let the picture be slightly soft.

## Sound

Strict no-sfx-over-speech leaves the middle of a near-continuous talker too quiet (Westside v3: 42 of 51 cues dropped). So at T1/T7 ask the user which scenes get sound
(e.g. "meter, traffic, size reveal, maps, share"). Those become `T.keep(a, b)` windows where cues play as designed over speech; every other cue obeys the resolver. Cue length is
capped per cue (`maxlen`) and a cue that would cover a key word is shifted or dropped. After a held-beat gag (sad trombone, dhol) the next words start clean.

## Rules

- Original takes and the user's joined file are never edited. Earlier versions are never overwritten.
- Caption exactly the user's words; no fact-check caveats on screen; no football outro or logo unless asked (`finish_tl.py --outro subscribe` is the optional like & subscribe card).
- Downloads (Whisper models, npm packages) need an explicit yes; a model not in the cache is a stop, not a download.
- If a script fails twice with the same error, stop and read its `--help`.
