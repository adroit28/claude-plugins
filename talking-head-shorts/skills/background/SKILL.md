---
name: background
description: Optional stage of a talking-head Short - replace the speaker's background with the user's image using Robust Video Matting. Runs a 5-second test matte on a window with moving hands, builds the edge-check sheet (full frames over the blurred new background plus 3x hair and hand crops over green), STOPS for the user's go, then matts the whole window and sets the spec's bg and matte (placement behind head and shoulders, blur, darken, half-zoom parallax, warm grade and glow, blink dips). Only when the user asks for a background swap or supplies a background image. Use when the user says "change the background", "put this image behind me", "remove the wall", or invokes /talking-head-shorts:background.
---

# Background swap (only on request)

Skip this stage entirely unless the user asked for a new background or supplied a background image.
Needs: `source.*`, `blink.json`, an approved plan, the background image in `shorts/<slug>/` (or `assets/`), a `fit` of `cover` or `crop`
(blurred fill cannot be matted), and the RVM model at `~/.cache/talking-head-shorts/models/rvm_mobilenetv3_fp32.onnx`
(`bash $S/setup.sh --rvm` downloads it, ~15 MB: needs the user's yes; the script checks the sha256 of v1.0.0).

## 1. Test (5 seconds, a window with moving hands)

Pick the 5 s window of the speech where the hands move most (the beat map's PEAK rows, or a sheet: `sheets.py grid`). Then:
```
$PY -I $S/matte.py shorts/<slug>/source.<ext> shorts/<slug>/matte_test --start S --end S+5 [--crop x,y,w,h]
$PY -I $S/edge_sheet.py shorts/<slug>/matte_test shorts/<slug>/matte_edges.png --bg shorts/<slug>/<bg image> --times <4 times in the window>
```
(The crop must equal `source.crop` when fit is `crop`.) Look at `matte_edges.png` yourself first: hair line fringe or a green halo,
fingers merging into the shirt, a torso that drops out on fast hands, a flickering shoulder. Then **STOP** and show it to the user with the
numbers from `matte.json` (blink frames reused, dropout retried/held). Continue only after they say go.

If the edges are bad: `--ratio` is the first knob (1.0 is right for ~480x850 sources; 0.6 dropped the torso on fast hands). A source that is
low-res or very blurred will always give soft edges: say so, offer blurred fill or the original file instead.

## 2. The full matte (after the go)

Warn with the estimate first (matte.py prints it and refuses > 150 MB without `--yes`): about 0.5 MB per frame at 478x850, ~400 MB per 27 s.
```
$PY -I $S/matte.py shorts/<slug>/source.<ext> shorts/<slug>/matte --start S --end E --yes
```
It prints the `spec.matte` JSON. `matte.json` keeps start/count; `build.py` re-reads both.

## 3. Spec

```
bg <image> scale=<3.0 for a low-res picture> left=<px> top=<px>        (defaults: blur 8, brightness 0.62, saturate 1.15, parallax 0.5,
                                                                        creep 0.04, filler dark strip, grade sepia(0.1), glow rgba(255,50,30,0.45))
set matte {"dir":"matte","start":<from matte.json>,"count":<n>}
```
apply with `spec.py fill` (v1 never rendered) or `spec.py bump` (a version that exists). Placement: put the interesting part of the picture behind
the head and shoulders (the speaker sits around x 540, y 900-1300 in the 1080x1920 frame); the image is scaled by `scale` and offset by `left`/`top`
from the frame's top-left. Low-res backgrounds need the 3x upscale plus blur; add the dark `filler` strip if the placement exposes the picture's
bottom edge. Warm the grade to the picture's light (`grade`, `glow` colour). A true inner rim light was never done (only the warm tint and an
outer glow): an optional upgrade, say so if the user wants it.

Blinks: the black source frames are handled by matte.py (last good cut-out reused) and the template dips the WHOLE picture, background included,
from `blink.json`. If a black frame still shows, look at the raw source frame before blaming the model.

Check hot-colour words and pills over the new picture (a red accent on a red tunnel needed the black stroke; if a word vanishes change `style.accent`
or the word's `hot` status) on a still: `build.py <slug> --still <output s>`.
Then `notes.md` State, cost, and on to `build`.
