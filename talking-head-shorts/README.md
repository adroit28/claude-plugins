# talking-head-shorts

Edits any talking-head video of yours (any aspect ratio, with sound) into a punchy 1080x1920 Short. Independent plugin:
own scripts, own Remotion template, own version (`VERSION`, `.claude-plugin/plugin.json`). Topic-agnostic; the topic is whatever you say.

```
/talking-head-shorts:make   -> intake -> plan -> [background] -> build -> finish   (+ revise any time after)
```

| Stage | What happens | Stop |
|---|---|---|
| intake | probe the ORIGINAL (fps, size, audio, black blink frames), crop/blurfill choice, Whisper small (large-v3 retry), unclear stretches listed and asked, your words aligned to the audio | your words + fit |
| plan | `beat-mapper` subagent (sonnet) -> table of sentences/pauses/numbers/peaks/dead air; edit plan table with 3 hook options; table -> spec | your OK on the table |
| background | only on request: RVM 5 s test, edge sheet, then the full matte and `bg` in the spec | your go after the edge sheet |
| build | Remotion project from the template, still previews, render to `raw_vN.mp4` | none |
| finish | voice cleanup, sfx, drone, loudnorm -14 LUFS, 3 s outro, 12-frame sheet, loudness check -> `<slug>_vN.mp4` | you watch it |
| revise | numbered feedback -> ops -> `edit.v<N+1>.json` -> new version + before/after frames | |

Every STEP (not just stage) ends with `cost.py` (Claude cost at list prices, this step / session / video), one question and a stop; stage boundaries also offer a fresh-session handoff (`NEXT.md`).

## Multi-clip route (v0.2): `/talking-head-shorts:timeline`

For several takes of one script, a joined/cleaned file, picture-only inserts, or a graphics kit. Steps T1-T11 (clips and questions, normalize, words, cut, locate, word QA,
joke-map plan, face tracking, build, sound, finish), one stop and cost report each. Contract and folder layout: `docs/multi-clip.md`.

| Script | Does |
|---|---|
| `timeline.py init/run/check` | `<slug>/timeline.py` (chunks, holds, inserts, captions, marks, cues) -> `timeline.json` + `cues.json`, chunk table with the seconds cut |
| `normalize.py` | CFR 30, 1080x1920 lanczos (+ light unsharp), untouched audio and a 16 kHz copy |
| `retake.py`, `wordqa.py` | repeated-opening hint; Whisper hi+en on the cut voice, caption-vs-speech coverage, sfx over key words |
| `locate.py` | find each take's chunks inside the user's joined file (cross-correlation), offsets, `vid`/`ca` |
| `track.py` (+ `face.swift`) | face centre per frame: cv2 haar, else Apple Vision |
| `build.py <slug> --timeline` | Remotion composition `Multi`; graphics in `anim/src/Scenes.tsx`, one removable line per scene (`src/kit/`) |
| `mix_multi.py`, `synth.py` | voice from sources, ducked music, sfx-vs-speech resolver with KEEP windows, loudnorm; 23 extra sfx + music bed |
| `finish_tl.py` | `<slug>_v<N>.mp4`, sheet, loudness check (outro off by default) |

## Setup

`bash scripts/setup.sh` checks everything. The Python (numpy, opencv, onnxruntime, faster-whisper, Pillow) can be `shorts/.venv` (set `THS_PY`) or
`setup.sh --venv`. Whisper models load from the local Hugging Face cache; RVM model: `~/.cache/talking-head-shorts/models/rvm_mobilenetv3_fp32.onnx`
(sha256 88d45312...2828); Remotion 4.0.530 in `THS_NODE_MODULES` or `~/.cache/talking-head-shorts/node_modules`. Downloads only with the user's yes.
Outro channel: `~/.config/talking-head-shorts/channel.json` `{"channel": "...", "handle": "@..."}` or `OUTRO_CHANNEL` / `OUTRO_HANDLE`.

## The edit spec (`shorts/<slug>/edit.v<N>.json`, schema `talking-head-shorts/1`)

All times are SOURCE seconds. Output time = hook length + (source time - `source.start`).

| Key | Meaning |
|---|---|
| `source` | `file`, `start`, `end`, `w`, `h`, `fit` (`cover` / `crop` + `crop [x,y,w,h]` / `blurfill`) |
| `style` | `font`, `fontFile`, `accent` (HOT words, slams, pills), `current` (word being spoken), `text`, `captionSize/Top/Width/Stroke/Gap`, `grade` (css filter), `vignette` |
| `hook` | `{"kind":"cold","clip":[a,b],"lines":[...]}` your own best line - `{"kind":"image","seconds","image","box":[left,top,height],"voice":[a,b],"lines"}` - `{"kind":"slam","seconds","lines"}` - `{"kind":"none"}`; a line is `{"text","color"}` (`"accent"` or css) |
| `phrases`, `hot` | `[[[word,start,end],...],...]` from `captions.json`; HOT words get the accent colour |
| `steps`, `drift`, `origin` | punch-in `[[t, zoom],...]` (hard cuts), slow zoom creep over the window, transform origin |
| `shakes`, `flashes` | `{"at","dur","amp"}`, `[t,...]` |
| `cutaways` | `{"src","from","to","w","h","ring":[fx,fy],"label","top"}` (ring = fractions of the picture; `w`/`h` filled from the image when omitted) |
| `pills` | groups `{"from","to","top","left","pills":[{"big":234,"small":"MATCHES","at","count","hot"}]}` (numeric `big` counts up) |
| `counters`, `slams` | `{"from","to","value","count","label","top"}`, `{"from","to","text","color","top"}` |
| `bg`, `matte` | background swap: `bg` image + placement/blur/brightness/parallax/grade/glow, `matte` `{"dir","start","count"}` (see the background skill) |
| `sfx`, `hook_sfx`, `music`, `outro` | `[name, source t, vol]`, `[name, t into hook, vol]`, `{"drone":true,"vol"}`, `{"seconds":3}` |

`spec.py` verbs: `init`, `fill` (in place until first render), `validate`, `show`, `bump --ops` (new version + diff). Ops: `set append insert delete caption retime shift hot bg`.

## Lessons baked in

- Black "blink" frames in the source (brightness / clip median < 0.93): the cut-out reuses the last good frame and the whole picture dips from `blink.json`.
- RVM: the recurrent state's shape depends on `downsample_ratio`; retries start from zero state; ratio 1.0 for ~480x850; dropout guard at 92% of the running median alpha area;
  repaired frames use source pixels. Seek by frame index, land on even frames of a 60 fps source, ~1 s lead-in; matte every 2nd frame (Remotion composes at 30 fps).
- Matte PNGs are ~400 MB per 27 s: the script warns and wants `--yes` above 150 MB.
- Remotion: JSON import needs `resolveJsonModule`; images go into `public/`; the static server 404s on symlinks (build.py hard-links); `~/.npmrc` may point at a dead registry (local `.npmrc`).
- Whisper cannot spell Hinglish: unclear stretches are asked, captions come from the user's words, Whisper only times them. Python that reads downloaded files runs with `-I`.

## Not done (yet)

Silence / jump-cut removal, true inner rim light, music beyond the drone, pitch-accurate Hinglish timing without Whisper anchors.
