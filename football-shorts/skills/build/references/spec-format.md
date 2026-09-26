# Edit spec format

One JSON file per version: `spec.v1.json`, `spec.v2.json`, ... in the edit folder
`shorts/<slug>/`. `render.py` reads it and writes `<slug>_v<version>.mp4` next to
it plus `build/timeline_v<version>.json`. Paths are relative to the edit folder.

```json
{
 "slug": "ronaldo-wales", "version": 2,
 "fps": 25, "size": [1080, 1920], "max_duration": 35,
 "sources": {"por": "src/sonyliv_por_wal.mp4", "fan": "src/fancam_tunnel.mp4"},
 "segments": [ ... ],
 "overlays": [ ... ],
 "audio": { ... }
}
```

## Segments (played in order; the output length is their sum)

| type | required | optional | notes |
|---|---|---|---|
| `clip` | `src`, `ss`, `t` | `crop`, `vf`, `speed`, `mute`, `label` | `speed` = setpts factor (2 = half speed, audio muted). Simple slow-mo; use `slowmo` for smooth. |
| `still` | `t` and either `image` or `src`+`at` | `crop`, `zoom` (0.06), `blur`, `dark` | Frame frozen with a slow push-in. `blur`/`dark` (0–1) make a background plate. |
| `card` | `t`, `lines` | `bg`, `y0`, `gap`, `zoom` | Text card. `bg` = colour string or `{"src","at","crop","blur":12,"dark":0.45}`. `lines` = `[{"text","size":110,"fill":"white","font":"big|small"}]`; size < 80 uses the small font. |
| `reverse` | `src`, `ss`, `t` | `crop`, `slow` (1.25) | Plays the moment backwards, audio reversed and slowed. |
| `split` | `t`, `top{src,ss,crop}`, `bottom{src,ss,crop}` | `audio`: `top`/`bottom`/`none` | Two 1080×960 halves stacked. Crops should be 16:9-ish halves, e.g. `[608,540,x,y]`. |
| `boomerang` | `src`, `ss`, `t` | `crop`, `loops` (2), `pulse` (0.07) | Forward+back, repeated, with a punch-zoom pulse. Length = `t × 2 × loops`. Keep `t` ≤ 0.7. |
| `slowmo` | `src`, `ss`, `t` | `crop`, `factor` (3) | Motion-interpolated slow motion, silent. Length = `t × factor`. Slow to encode; keep `t` ≤ 1. |

**Durations are whole frames.** Every segment length is snapped to a whole number of frames with round-half-up
(3.3 s at 25 fps = 82.5 frames → 83 → 3.32 s) and the timeline shows the snapped value, so caption `from`/`to`
times should be taken from `--dry-run`, not from the arithmetic in your head. Prefer multiples of 0.04 s
(0.64, 0.84, 1.52, 2.48 …); render.py prints a note for any length that is not. `speed` clips read one extra source
frame and `slowmo` reads two (a stretched clip of N frames yields fewer than k·N frames otherwise), so leave at
least 0.08 s of clean footage after the window you chose. render.py counts the frames of every segment after
encoding and prints a WARN if any is off; never hand over a render that warned.

`crop` forms (source pixels, applied before scaling to 1080×1920):
- `[w, h, x, y]` — fixed window. A full-height 9:16 window on 1080p is `608×1080`; x = subject centre − 304. Tighter: `[500, 889, x, y]`.
- `{"w":608,"h":1080,"x_from":896,"x_to":696,"y":0}` — linear pan across the segment.
- `"crop=608:1080:x='if(lt(t,1.7),896-200*t/1.7,696+300*(t-1.7)/1.5)':y=0"` — any ffmpeg crop expression.
- omitted — centred 9:16 crop.

`vf` appends extra filters after the crop (e.g. `"eq=contrast=1.1"`). `label` shows in the timeline and on check sheets; always set it.

### Fill (letterboxed or landscape sources)

```json
"fill": {"box": [478, 302, 0, 274], "cy": 0.47, "dark": 0.12, "blur": 6}
```
Spec-level (every segment) or per segment; `"fill": false` on a segment turns it off. `box` is the picture
inside the bars (`enhance/scripts/analyse.py` prints it). A blurred, slightly darkened copy of the box fills
the 9:16 frame and the foreground (the segment's `crop`, default the whole box) is scaled to the full width
and centred at `cy` × height. A narrower crop inside the box = a bigger foreground: full box width for wide
shots, about 300 of 478 px for a face. `split` halves ignore fill. Keep `dark` low (0.1–0.2): 0.4 turns a
green pitch into black bars again.

### Effects on any segment (timed in output seconds of that segment)

| field | form | notes |
|---|---|---|
| `zoom` | `1.15` or `{"from":1,"to":1.15,"at":0,"dur":null,"cx":0.5,"cy":0.5,"ease":"out"}` | push-in over the segment (`dur` null = to the end); a punch is `{"to":1.15,"dur":0.15}`. Not on `still`/`card`, whose `zoom` is the zoompan amount. |
| `shake` | `0.3` or `{"at":0,"dur":0.35,"amp":14}` | decaying camera shake for impacts and freezes |
| `flash` | `0.1` | fade in from white at the start of the segment; ignored on segment 0 (frame 0 is the scroll thumbnail) |

Sources without an audio track are handled: their segments get silence, so the bed and hits carry the sound.

## Overlays (captions drawn by Pillow, shown between `from` and `to` seconds)

```json
{"from": 0, "to": 1.6,
 "big": ["HIS WORST NIGHT", "IN A PORTUGAL SHIRT"], "big_size": 118, "y_big": 330,
 "small": ["PORTUGAL 1-0 WALES · 24 SEP 2026"], "small_size": 52, "y_small": 1330, "small_fill": "#FFD400",
 "emoji": "💀", "emoji_y": 1420, "emoji_size": 240,
 "extra": [{"lines": ["BEFORE VAR"], "y": 790, "size": 100}, {"lines": ["AFTER VAR"], "y": 1740, "size": 100}],
 "png": "build/custom.png"}
```
`big` = Impact, white, black stroke; `small` = Arial Bold, yellow. Lines auto-shrink to fit
the width. `extra` places any number of blocks at a given y; a block may add `"bg": "#111111"` (rounded
badge behind it, `pad` 18) and `"emoji": "❌"` (drawn inline after the last line, text + emoji centred
together, so it never collides): `{"lines": ["MISS #2"], "y": 1390, "size": 90, "bg": "#111111", "emoji": "❌"}`.
Emoji do not render inside Impact/Arial text; use `emoji` fields. `png` uses a ready
1080×1920 RGBA image instead. Overlays may overlap in time; later ones draw on top.

Safe zones on a Short: keep text out of the top 250 px (progress bar, channel row)
and the bottom 450 px (title, caption, buttons) and the right 150 px (like/comment
column). Defaults `y_big=330`, `y_small=1330` respect this; `y_small` 1500+ sits in
the caption zone and is only for a last frame.

## Audio

```json
{"clip_volume": 0.9,
 "bed": {"src": "por", "ss": 296, "volume": 0.22, "fade_out": 2.5},
 "hits": [{"at": 8.16, "volume": 0.9, "freq": 48, "dur": 0.6}, {"at": 5.2, "kind": "whoosh", "volume": 0.5}],
 "loudnorm": "I=-14:TP=-1.5:LRA=11"}
```
`bed` is a continuous track under the cuts: either `src` (a source key, e.g. crowd
noise from a quiet part of the match) or `file` (a music file the user supplied and
holds rights to). `hits` are synthesised sounds at exact seconds (no sample files to license), by `kind`:
`bass` (default thump, `freq` 48, `dur` 0.6) for freezes and reveals; `whoosh` (0.45 s noise swell, start it
0.3 s before a cut); `riser` (rising tone, `dur` 1.5–2.5 s ending on the payoff); `ding` (counter / verdict);
`tick` (tiny click). `loudnorm` is applied last; `false` disables it. Segments made with
`speed`, `slowmo`, `boomerang`, `still`, `card` are silent, so the bed carries them.

## Versioning

- Never edit a spec in place after it has been rendered; copy to the next version
  and bump `"version"`. Old outputs stay for comparison.
- Segments are cached by content hash in `build/seg_NN_<hash>.mp4`; caption-only
  changes re-render in seconds. `--force` re-encodes everything.
- `render.py spec.json --dry-run` prints the timeline (start/end per segment) without
  encoding. Use it to map feedback like "at the 7th second" to a segment.
