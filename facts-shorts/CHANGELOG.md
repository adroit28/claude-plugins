# Changelog

## 0.9.0 (dynamic by default; additive, old scenes render as before)
Lessons from Burj Khalifa Reel 1 v1 -> v2 ("very static, plain, little sound effects" -> "much, much better").
- **Rule change**: animated explainers are dynamic by default. `skills/video/references/dynamic.md` (new, read before the storyboard): motion budget (every beat moves all the time; the storyboard gets "What moves" and "Sound (peak volume)" columns), a VISUAL hook in the first 3 s (filmed photo, hit word that lands, a counter that builds; frame 0 = last frame), one camera with parallax layers, ONE shared hero asset reused in every beat, split screens explained top to bottom, real motion for real phenomena, 3D only after a 2D-vs-3D test, sound design (beds 0.10-0.25, hits 0.20-0.35, voice about 8-12 LU above the sfx, hits never on a HOT word, beds follow the picture), process (one module per beat, stills montage, one full render) and pitfalls. Video skill (description, storyboard columns, effects wording, hard rules) and revise skill (visual feedback = storyboard table + step build) updated; the "effects rare / calm beats" wording now applies to punctuation only
- **kit/cinema.tsx**: `rigTransform` (one camera, layers by parallax factor), `CamPhoto` (a filmed photo: tilt/push/roll, foreground strip, wisps, dust, flares, light sweep, punches, loop `settle`), `SlotCounter` + `slotTicks`, `Cloud`, `Stars`, `Wisps`, `Dust`, `mix` (hex or `rgb()`), `rnd`, `lerp`. **kit/audio.tsx**: `Bed` (a sound bed whose volume is a per-frame function of time). Both exported from `kit/index.ts`
- **sfx.py**: `wind` (14 s, slow gusts, filtered noise), `air`, `hum`, `creak`, `rumble`; render re-runs sfx.py when any is missing
- **anim.py**: `check` prints the VOICE vs SFX balance (raw render minus narration; warns under 6 LU or over 18 LU) and the STATIC SPANS (>= 1 s where the picture above the caption band barely changes; on Burj v1 it finds 11 spans, on v2 three); `still --at ... --montage` tiles all stills into `build/check/still_montage.png`; **sfxprobe.mjs** now expands function components, so Scenes split into beat modules are hot-word-checked too (Burj v2: 64 cues found)
- `templates/remotion-2d/src/examples/burj-reel/` (Burj.tsx + the five beat modules, type-checked, not imported): the worked example of all of the above

## 0.8.0 (motion + sound kit; additive and opt-in, old scenes render exactly as before)
- **Hot-word captions**: `HotCaption` (kit/overlays.tsx). Words show as spoken, the current word is gold, HOT words are bigger, red and tilted and get a chunk of their own. HOT = the CAPS words of each line's `tts` (matched to the caption word, nth occurrence), or `video.hot` (`"galti"`, `"L3:dhakel"`, `"L5:nahi#2"`). Story `video.hotCaptions: true`; `captions: false` and the y 1330 band unchanged
- **Music bed**: `sfx.py <story> --music` writes a deterministic 108 BPM bed (pure stdlib port of talking-head synth.py music(); no numpy); with `video.music: true` (optional `musicGain`, default 0.45) `anim.py render` ducks it under narration.wav with a sidechain compressor, mixes it with the raw render's audio and loudnorms to -14 LUFS / TP -1.5. Off by default. **sfx-vs-key-word check**: with hotCaptions, render warns (never drops) when an `<Sfx>` peak lands on a HOT word (`scripts/sfxprobe.mjs` reads the scene's Sfx times with the Short's esbuild)
- **sfx.py**: boom, revwhoosh, glitch, scratch, sadbone, boing, notify, kaching, confetti, shutter, tick2 (lavfi, deterministic, no downloads); render re-runs sfx.py when any library sound is missing, so older Shorts pick them up
- **kit/fx.tsx**: `Glitch` (RGB-split slam + scan lines), `Title3D` (extruded one-line hook title + light sweep, static so the loop frame matches), `CalendarFlip` (rotateX page flip from -> to across a phrase), `Transition` (whip / slide / iris / flip / wipe at a time, no timing change), `Blur` (`@remotion/motion-blur` Trail or CameraMotionBlur, active only between a and b), `Meter` (danger gauge filling across a phrase)
- **kit/burst.tsx**: `Burst`, `Confetti`; `Stamp burst`
- **kit/phone.tsx**: `ChatBubbles`, `Notify`, `ShareSheet` (ending CTA), generic text props
- **Card `flip="y"|"x"`**: 3D flip-in instead of the slide
- **spring()**: `springPop`, `popClassic`, `enter`; `Emoji`/`Hero`/`LottieEmoji`/`CalendarFlip`/`Notify` take `springy`; a Scene can `export const SPRINGY = true` to switch `pop()` for the whole scene. Default stays the classic curve
- **kit/hero3d.tsx** (not in the barrel, import by path): `Hero3D` drops ONE transparent three.js canvas into the picture band (driven by `t`), `EarCanal3D` is the worked example (canal, eardrum, wax pushed by a swab). Skill rule: "2D, at most one opt-in 3D beat"
- **Film grain**: `video.grain: true` (0.06) or 0.02-0.08, capped at 0.08; OFF by default (noise doesn't compress and can double the file); `public/grain.png`
- **Fix `anim.py check`**: the loop sheet and the loop SSIM seek with `-sseof -0.05` instead of `-ss <last frame>`, which got no frame on some files (59.000 s file, seek 58.967) and crashed with ffmpeg exit 234
- template deps (all pinned to Remotion 4.0.534): `@remotion/motion-blur`, `@remotion/three`, `three ^0.186.1`, `@react-three/fiber ^9.8.1`, `@types/three`; lockfile regenerated through the local `.npmrc`. Old Shorts keep their pinned deps until `anim.py init` is re-run in them
- `src/examples/kit-0.8-demo.tsx` (every new component once, not imported); `template.md` and the video skill document each with when-to-use rules and limits
- not ported on purpose: matting, face tracking, speaker punch-ins, maps/traffic, finance/shopping widgets, news ticker, brand end cards, @remotion/noise
- animated emoji candidates (Noto Emoji Animation, CC BY 4.0) are listed in `src/lottie/CREDITS.md`; none downloaded without the user's yes

## 0.7.0 (myth-buster script mode; additive)
- script skill + style.md + gemini/script-skill.md: "Myth-buster mode" for habits viewers do wrong (earbuds after a bath): accusation hook, why-it-feels-right line, stakes beat, open loop, VERIFIED free fix, payoff that sends the hand back to the habit. Drama comes from structure only; still no unverified "doctors kehte hain", no invented danger, no fake-shock phrases
- the script skill picks the mode itself and announces it; Gemini skill prints "Mode: myth-buster|explainer" above the table
- first use: earbuds-cleaning
- Gemini users: re-paste the script skill (`facts copy script`) into the Gemini skill/Gem

## 0.6.0 (animated emoji + light-leak cuts; additive, old scenes render as before)
- kit/lottie.tsx: `LottieEmoji` (animated Noto emoji, same contract as `Emoji`), `LOTTIE` (sun, eye, nose, relieved, sneeze, zap in src/lottie/, CC BY 4.0, CREDITS.md), `LightLeakCut` (@remotion/effects light leak over a cut, no timing change); exported from kit/index.ts
- template: Remotion 4.0.530 -> 4.0.534, adds @remotion/lottie + @remotion/effects (lockfile regenerated), remotion.config.ts sets the "angle" WebGL renderer for the effects
- video skill + template.md document both; credit line for the description
- first use: sun-sneeze v5 (6 emoji animated, 5 light-leak cuts, same 43.17 s); the facts-shorts v5 test folder is facts-channel/sun-sneeze/remotion-skills-test/. Old Shorts keep their pinned 4.0.530 until `anim.py init` is re-run in them
- to test: next 3-4 Shorts with these vs 3-4 static, compare average % viewed and 3 s hold

## 0.5.1 (DepthWorld ruler + slam easing; additive, off by default)
- kit/world.tsx: `rulerSpan` prop - the ruler gets its own zoom, capped so the screen always spans at least that fraction of the camera value (0.4: ticks 150/160/170 km at 160 km, every 2,000 km at 35,040 km). Fixes ticks that were metres apart and rounded to the same label at true-size stops. 0 (default) keeps the old behaviour
- kit/world.tsx: `ease` ("in" | "out" | "lin") on a world key shapes the move that ends at it ("in" = accelerates into a slam); tick labels get thousands separators and more digits
- first use: space-climb v2 (ruler fix; cold-open dive that slams onto the runner on a word, running figure, lift-off, loop back to the far-out frame)

## 0.5.0 (scale-axis worlds; additive, 0.4.0 files untouched)
- kit/world.tsx: DepthWorld (camera follows a value along a height/depth axis, eased with ramp in log space by default, px per metre keyed per time; sky gradient blended by value; ruler ticks at 1/2/5 steps; ground; live metre + km counter; true-scale flat objects (emoji or custom art, drawn as a dot, never enlarged, when under 16 px); pinned labels with optional off-screen edge chips; dashed reference lines; Cam punches), plus worldAt, skyAt, fmtM helpers; exported from kit/index.ts
- first use: space-climb (how high is space?), a scale-axis Short in the style of the ocean-depth references

## 0.4.0 (motion kit; additive, old scenes render as before)
- kit/motion.tsx: Cam, Kinetic, Draw, Dots, Versus, Swipe, Flash, LiveBg; Card gains kb/drift/punch; Short.tsx draws LiveBg under every scene (opt out with LIVE_BG = false)
- prototype: sun-sneeze v2 (camera pushes, kinetic AANKH BAND / struck SNEEZE, 35/100 dot grid, swipes); v1 kept
- fix: cost.py (via common.content_dir) finds the real content root by walking up to channel.json and no longer creates a stray facts-channel/cost_log.jsonl in whatever folder it was run from (CLAUDE_PROJECT_DIR is unset in the Bash tool); it warns and skips logging if no root is found
- not yet: cutout/parallax layers (needs rembg model download), Lottie stickers

## 0.3.0 (Gemini-app route; additive, skills unchanged)
- gemini/: Gemini skill (or Gem) description + instructions for ideas, research and script (`*-skill.md`, `facts copy`), with the worked examples inside the instructions (Gemini skills can't attach files); GUIDE.md
- research-skill.md tightened after the red-light trial (Gemini invented quotes, 404 pages, homepage URLs, exam-prep sources, LaTeX book quotes when corrected): exact-page URLs only, banned source list, quote must state the claim, no MYTH without a source, self-check before answering, corrections never add unread sources
- facts save verify audits the file: opens every URL (404/410/DNS = invented), flags homepages, banned domains, LaTeX, 'Status:' layout, missing sections/Wording lines; exit 2 on problems
- quick-skill.md: optional Facts Quick Script skill (topic → beats → story JSON + an UNCHECKED facts file + visual ideas, no web research, lists the facts to check); `facts save quick <slug>` saves its facts file as verify.md without the source audit; `facts copy quick`
- gemini/facts.sh + facts_save.py: `taken` (ledger to clipboard), `pick` (ledger + folder), `save verify|story` (clipboard -> file, takes the right fenced block from a whole reply, fills fixed story fields, runs validate.py, refuses to overwrite a narrated story), `check`, `narrate` (validate, one free take, segalign, open audio)

## 0.2.2 (phase 2, text only; appended lines, nothing reworded)
- video: never run `npx remotion` directly; `<story>` is the full file path; text-prop, caption-band, edge and `until` rules in step 5; read the last frame sheet in step 6
- make: stop after the same error twice; fresh session also at narrate -> video; trim long tool output; `<story>` definition
- script: `needs from earlier` column and re-read verify.md notes per claim; `<story>` definition
- narrate: `<story>` definition

## 0.2.1 (phase 1, code only; additive)
- anim.py still: relative Remotion output path too (an absolute path was cut at the space and wrote a stray file next to "personal projects"; found in the 0.2.1 retest)
- anim.py render: relative Remotion output path, stops before ffmpeg if the raw file is missing; runs sfx.py when anim/public/sfx has no .wav
- anim.py check: robust loop-SSIM parse (WARN < 0.7), WARN when loudness is >2 LU from target (the pipeline's single-pass loudnorm normally lands near -15); the loop comparison sheet is retried slightly earlier when the exact last frame yields no image (it was listed but never written)
- kit: ramp()/pop() no longer throw when the range is not increasing; kit/index.ts barrel; optional `until` on Stamp and Badge
- common.py: a story folder resolves to its highest story.v*.json; a non-JSON file gets a clear usage message
- cost.py: "cost: n/a (no Claude session log)" and exit 0 when there is no session log
- validate.py: WARN for lines whose claim (line "claim" id) is weak in verify.md but carry no hedge word

## 0.2.0
- first version
