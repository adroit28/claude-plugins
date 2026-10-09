---
name: intake
description: First stage of a talking-head Short - probe the user's ORIGINAL video (fps, size, audio, black blink frames), decide with them how a non-9:16 video becomes vertical (crop to the speaker or blurred fill), transcribe locally with Whisper (small, then large-v3 for the retry) with word timestamps, list every unclear stretch with its timestamp and ask the user for the words, then align the user's confirmed words to the audio as caption timing. Use when the user gives a video path to edit, says "transcribe this", "what did I say at 12 s", or invokes /talking-head-shorts:intake.
---

# Intake and transcription

Inputs the user may give: the video path (required, any aspect ratio, with sound), optional images / logos / clips for cutaways,
an optional background image, a time window (default: the whole video), a slug. Never ask for more than is missing.

## 0. Ask first, before probing (saves a round trip)

Ask these once, in one message, unless the user already said:
1. **Background noise:** "Have you already removed the noise (and joined the takes) in your editor?" If yes, use THAT file as the source and do NOT run
   denoise (afftdn) on it. If no, say the noise reduction here is limited (a spectral denoiser cannot remove traffic or crowd under speech) and ask them
   to clean it in their editor first; re-editing a noisy source costs a full extra version.
2. **Final cut already made?** If the user joined and trimmed takes themselves, their file is the timeline: do not re-cut from the originals.
3. **Several takes?** More than one clip of the same script, or a joined file plus the takes: switch to the `timeline` skill (T1-T11) after this stage's questions; it adds CFR/upscale intake, a retake hint and word QA.
4. **Language of the words:** the user's own transcript beats Whisper for Hinglish captions; ask them for it when stretches are unclear.

## 1. Probe

```
$PY -I $S/probe.py "<video>" shorts/<slug>
```
Links the original as `shorts/<slug>/source.<ext>` (never re-encoded) and writes `probe.json`, `blink.json`, `intake_frames.png`.
Report: size, fps, duration, audio yes/no, `low_res` (a sharper original may exist: ask once whether the user has one), and the blink spans
(black jump-cut frames: brightness / clip median < 0.93). No audio: stop and tell the user (captions need the voice).

**Not 9:16** (`nine_sixteen: false`): look at `intake_frames.png` (source, speaker-centred crop, blurred fill) and ask the user to choose.
`crop` keeps the speaker big and sharp (use `suggested_crop` only if the head and both hands stay inside; otherwise move x); `blurfill` keeps the
whole frame over its own blur. A background swap needs `cover` or `crop`. Create the spec:
```
$PY -I $S/spec.py init shorts/<slug> [--fit crop --crop x,y,w,h | --fit blurfill] --start S --end E
```

## 2. Transcribe (free, local)

```
$PY -I $S/transcribe.py shorts/<slug> --model small --start S --end E
```
Writes `transcript.json/.md` and `unclear.json`. Whisper cannot spell Hinglish; its words are only used for WHEN a word was said.
If `unclear.json` has stretches, retry them once with `--model large-v3` (if it is not in the local cache the script says so: a download needs the
user's yes). Then **ask**: show the numbered list `?1 12.40-13.10 s heard: '...'` and ask for the words of each stretch.
**Never fill a gap with your own guess**, not even a likely one. Ask for the whole text instead if most of it is shaky (the user can paste
their script or type it).

## 3. Confirmed captions

Write `shorts/<slug>/captions.txt`: ONE caption phrase per line (3-6 words, break at the speaker's breath), the user's exact words and spelling,
digits for numbers. Then:
```
$PY -I $S/captions.py shorts/<slug> --window S E
```
It matches each confirmed word to a Whisper word when they look alike and spreads the rest over the audio that is actually loud, then writes
`captions.json` and lists the **interpolated** words with their times. Those are the ones to check later on the sheet (Whisper times are
coarse on long or mumbled words; `retime`/`caption` ops in revise fix them).

## Stop

Report: file facts, fit decision, window, the transcript in one block, the answered/unanswered `?` stretches, `captions.json` summary
(phrases, matched vs interpolated). Wait until nothing is unanswered. Write `notes.md` State; cost; offer the fresh session (the plan stage
is the big-context one).
