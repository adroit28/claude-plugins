---
name: finish
description: Finish stage of a talking-head Short - clean the voice (highpass + denoise), mix synthesized sound effects and a low drone, loudnorm to about -14 LUFS, append the 3-second like & subscribe outro, make a 12-frame contact sheet, check loudness and true peak, and hand over <slug>_v<N>.mp4 without overwriting any earlier version. Use after build, when the user says "finish it", "mix and export", "add the outro", or invokes /talking-head-shorts:finish.
---

# Mix and finish

```
$PY -I $S/finish.py shorts/<slug>            # mix.py -> build_v<N>.mp4, outro.py -> <slug>_v<N>.mp4, sheet, loudness
```
Needs `anim/out/raw_v<N>.mp4` for the latest spec. It refuses to overwrite `<slug>_v<N>.mp4`.

- **Voice**: the ORIGINAL's audio, highpass 90 Hz + afftdn, trimmed to the spec window, delayed by the hook length. Cold-open hook: the same clip's audio
  plays under the hook; image/slam hook: `hook.voice [a,b]` (a line from the source, may lie outside the window) ends where the hook ends.
- **Sfx**: synthesized (ffmpeg lavfi, no licences): pop whoosh stamp bass riser tick ding sparkle click coin buzz horn ring waves; cue times are in the spec.
  Volume = spec volume x 0.55 under the voice. A sfx pack download needs the user's yes.
- **Drone**: 55/82/110 Hz sines, lowpassed, `music.vol` scales it. **Loudness**: loudnorm I=-14, TP=-1.5; the finisher flags anything outside
  -16..-12 LUFS or above -1 dBTP.
- **Outro**: `outro.py` appends the held last frame dimmed + a card (channel and handle from `OUTRO_CHANNEL`/`OUTRO_HANDLE` or
  `~/.config/talking-head-shorts/channel.json`; neither = "Like & Subscribe"), two soft ticks on the taps. `spec.outro.seconds` (min 2.5). Needs Pillow (the venv python).

Look at the contact sheet yourself (the finisher prints its path): captions legible, nothing under the outro card, hook readable in frame 1, cutaways
not cut off, no black frame. Fix problems as a new version through `revise`, not by editing the mp4.

Hand over: path, duration, loudness, the sheet, anything you noticed (interpolated caption words that look early or late, a low-res source). `open` the file.
End with: for changes, `/talking-head-shorts:revise slug: <slug>` with a numbered list. `notes.md` State, cost, `NEXT.md`.

Multi-clip slugs: `finish_tl.py` (after `mix_multi.py`), see `timeline/SKILL.md` T10-T11.
