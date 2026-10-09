# Multi-clip mode (timeline), data contract

Second flow next to the single-source spec (`edit.vN.json` + `build.py` + `mix.py` + `finish.py`, unchanged).
Use it when one script was shot as several takes, when picture-only inserts/holds are needed, or when the user already joined and
cleaned the takes into one file. A slug is multi-clip when `<slug>/timeline.py` exists.

## Slug folder

```
<slug>/clips/<name>.<ext>      the ORIGINAL takes (links), plus the user's joined file when there is one
<slug>/norm/<name>.mp4         normalize.py: video only, CFR 30, 1080x1920 (lanczos + light unsharp when upscaled)
<slug>/audio/<name>.wav        normalize.py: untouched audio, 48 kHz mono 16-bit (voice is cut from these)
<slug>/audio16/<name>.wav      16 kHz copy for locate.py / whisper
<slug>/timeline.py             the single source of truth (uses scripts/timeline.py helpers)
<slug>/timeline.json           written by timeline.py, read by Remotion (anim/src/timeline.json is a copy)
<slug>/cues.json               written by timeline.py, read by mix_multi.py
<slug>/offsets.json            locate.py: {"<clip>": offset_s}   (combined time = clip time + offset)
<slug>/combined_map.json       locate.py: per chunk start/end/score/second/flag
<slug>/track.json              track.py: {"<name>": [[x,y,w] per frame, ...]} face centre in 1080x1920 px
<slug>/sfx_resolved.json       mix_multi.py: what happened to every cue
<slug>/words.json, wordqa.md   wordqa.py
<slug>/build_v<N>.mp4 / <slug>_v<N>.mp4 / cost_log.jsonl   as in the single-source flow; versions never overwritten
```

## timeline.json

```
{ "fps":30, "total":53.17, "hook":0.9, "end":51.67,
  "files": { "<name>": {"video":"clips/<name>.mp4", "audio":"audio/<name>.wav"} },   // video is relative to anim/public, audio relative to the slug
  "chunks": [ {"id":"G1","clip":"good_news","a":0.86,"b":1.72,"o":0.9,"d":0.86,"hold":0.0,"speed":1.0,"voice":true,
               "z":[[0.86,1.0],[1.72,1.05]],            // zoom steps [source time in this chunk's clip, scale], eased between
               "vid":"combined","ca":0.465 } ],          // picture AND voice come from files[vid] starting at ca (seconds in that file)
  "phrases": [ {"a":..,"b":..,"words":[{"w":"GOOD","a":..,"b":..,"hot":false}]} ],   // output seconds
  "marks":{"name":output_s}, "shakes":[{"t","d","a"}], "flashes":[{"t","c"}], "whips":[{"t","d","dir"}] }
```
- Direct mode: `vid == clip`, `ca == a` (snapped to the 30 fps grid). Pre-joined mode: `vid == "<joined name>"`, `ca = round((a + offsets[clip]) * 30) / 30`.
- `voice:false` chunks are picture-only (b-roll, inserts): `vid == clip`, `ca == a`, no audio is taken from them.
- Output time `o` accumulates `d + hold`; `d = (b - a) / speed`. A `hold` freezes the last frame (Remotion `Freeze`) and the voice stays silent.
- `end` is where the content stops; `total` = end + tail (the timeline's `END`, default 1.5 s) and may be followed by an in-Remotion end card.

## cues.json

```
{ "total":.., "chunks":[same as timeline.json], "files":{same},
  "sfx": [[t_out, "name", vol, maxlen_s?]],      // sfx names are files in the sfx library (scripts/synth.py names)
  "keep": [[a,b]],                                // windows where cues may sound over speech
  "music": {"keys":[[t_out, gain 0..1]], "bed":"music.wav|null"},
  "marks": {...} }
```

## Rules the scripts enforce

- Every talking chunk must lie inside its clip; chunks are listed in output order and may not overlap.
- Captions belong to a chunk (the helper `cap(chunk, text, a, b, hot=[])` takes source times of that chunk's clip).
- SFX policy (mix_multi.py): a cue may not sound over speech unless inside a `keep` window; otherwise it is shifted at most 0.12 s into
  a gap, trimmed with a fade, or dropped. The table is printed and written to `sfx_resolved.json`.
- Word QA (wordqa.py): speech with no caption for >= 0.15 s and a caption on screen over silence >= 0.35 s are listed. A cue on top of a key
  word hides it, so key words also get a caption.
