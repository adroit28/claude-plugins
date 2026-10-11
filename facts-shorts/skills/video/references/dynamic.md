# Dynamic by default (0.9.0)

Rule for every animated facts Short: **no beat is a still picture, and the picture is never silent.** v1 of Burj Khalifa Reel 1 had pop-ins on a static
frame, four sound effects and no ambience, and the verdict was "very static, plain, little sound effects". v2 added the points below and the verdict
was "much, much better". (Talking-head and real-footage edits keep their own restraint rules in their own plugin; this file is for animated explainers.)

## 1. Motion budget

- **Every beat has something moving ALL the time**: a camera (push, tilt, roll, drift), parallax layers, drifting particles (dust, leaves, clouds, stars), a pulsing glow, a
  ticking counter. A pop-in is an entrance, not the beat. Allow a held, calm second only after a hit, on purpose.
- The storyboard table has two extra columns: **What moves** (camera / layers / particles, per beat) and **Sound (vol)**. A beat whose "What moves" is empty is not approved.
- **Check it, don't claim it**: `anim.py check` prints "static spans" (>= 1 s where the picture above the caption band barely changes). Fix every span or say why it is a deliberate hold.
- Effects that punctuate (Transition, Glitch, Flash, LightLeakCut, Confetti) go at the story's turns; continuous motion (camera, parallax, particles) is everywhere.
  The old "keep effects rare" limits apply to the punctuation, not to the motion under it.

## 2. The first 3 seconds are a visual hook

Never rely on the audio hook alone. Frame 0 is the feed thumbnail and must already look alive. Pick one or combine:
- the key photo **filmed**: a push-in with a tilt along the subject on its word (`CamPhoto`), a faster foreground strip, drifting wisps, a pulsing flare, a light sweep;
- **the hit word lands visually**: glitch + shake + flash + stamp (`Glitch`, `Shake`, `Flash`, `Stamp`) on the boring/shocking word, then a whip-pan or flash-cut on the turn (`Transition whip`);
- a **number that builds**: a slot-machine flip through the digits with ticks and a riser, glowing on its word, exploding on the payoff word (`SlotCounter`, `slotTicks`, `Burst`, `Confetti`);
- a 3D-look title with light sweeps (`Title3D`).
Keep frame 0 and the last frame matching (loop): ease the camera back to its first state during the outro (`CamPhoto settle`).
A flat photo has no real depth layers: fake depth with the strip, wisps and a camera move; if a layer edge shows, fall back to push + tilt only.

## 3. One camera, many layers; one hero asset

- **Rig**: one camera (zoom z, how far it has moved k, how far the world has scrolled) and each layer gets its own parallax factor p (sun 0.08, far skyline 0.22, mid 0.55,
  hero 1, clouds 1.2, foreground 1.3): `rigTransform(rig, p)` returns the CSS transform and a `project(x, y)` for pinning flares and markers to a layer. A "ride", a "climb" or a
  "zoom into" becomes one variable instead of ten hand-animated objects, and speed lines, a curved horizon and clouds passing sell it.
- **Draw the hero asset once** (the building, the bottle, the phone) as a parametrised component and reuse it in EVERY beat: props for lights per row, bend/flex, rim light,
  glow, ghost outline. Test it first on a contact sheet next to the reference photo (proportions: a slim tapering tower, not wide blocks) before building beats on it.
  Different drawings per beat read as different objects and were the "looks like a fort" bug.
- **Split screens must be explained top to bottom**: the subject on one side, the gauge/scale on the other, a marker or camera that rides, and a bracket that joins the two readings
  before the number pops. Label with visual words already in the narration; no new claims.
- Real phenomena get real motion: wind = curved streamlines that bend around the object + debris; a flexing tower = tiers displaced progressively (top most), not a rigid rotation.
- **3D**: only after a quick 2D-vs-3D test frame; a crude three.js model loses to a polished 2D drawing. Default 2D; at most one 3D beat, 2-4 s.

## 4. Sound design that never covers the voice

| Layer | Peak volume | Examples |
|---|---|---|
| Ambience bed under a setting | 0.10-0.25 | `air` (open sky), `wind`, `hum` (heat, an empty void), `waves` |
| Short hit | 0.20-0.35 | `stamp`, `boom`, `pop`, `ding`, `glitch`, `sparkle`, `confetti` |
| Move | 0.15-0.30 | `whoosh` on every camera/prop move, `revwhoosh` into a push |
| Build | about 0.22 | `riser` (2.6 s) timed to END at the reveal; one riser per reveal at most |
| Counter | 0.20 | `tick` per step, timed to the visual (`slotTicks`, the gauge crossing a mark) |

- **Voice stays on top**: aim for the sfx about 8-12 LU under the voice (`anim.py check` prints voice / sfx LUFS and the gap, warns under 6 or over 18). Re-balance beds first, hits second.
- **Hot words**: short hits never peak on a HOT word; hits go just before or just after. Risers and beds may build into it but must peak before it starts (end the riser ~0.1 s early); ambience may play under it.
- **Beds follow the picture**: use `Bed` and drive its volume from the SAME variable as the visual (wind strength, camera speed, a gauge), so the sound swells with each gust and fades as the motion calms. Add a creak/rumble at the extreme of a sway, a riser into every reveal and into the closing comment ask, a sparkle on a sunrise.
- Still no music bed unless the user asks. New synthesized sounds: `sfx.py` (wind, air, creak, rumble, hum). `sfx.py <story>` regenerates the library.

## 5. Process that kept it cheap and right

1. Storyboard table (with What moves + Sound columns) -> user's OK. Timings from `build/words_segments.json` via `at("L3", "word")`; for a repeated word pass `nth` (the sunset beat matched "suraj" the first time and fired early).
2. Build ONE module per beat (`hookbeat.tsx`, `fact1beat.tsx`, ...) that exports a component taking `t`; `Scene.tsx` just composes them. Shared helpers in `kit/cinema.tsx`; the hero asset in its own file.
3. After each beat: `anim.py still <story> --at <8-11 key words> --montage` and Read ONE montage. Fix, then the next beat. Render the full video once at the end (`anim.py render`), then `check`.
4. Stop after each step with its cost (see the step protocol), and read the montage, not the numbers.

## 6. Pitfalls found

- A colour-mix helper that only parsed `#rrggbb` returned NaN when fed another mix's `rgb()` output (skies went dark): `kit/cinema.mix` takes both.
- Word lookup by text returns the FIRST match: use the `nth` argument for repeats.
- Any wrapper with a transform is `position: absolute; inset: 0` (a `Layer`), or its children land below the screen. Reveals: `clip-path: inset(...)` on a wrapper.
- Check text near panel edges (a "6°" and a tag were clipped at first); tags beside a moving marker go on the roomy side.
- `rigTransform` layers need `transformOrigin: "0 0"`.
- Emoji and tags must disappear when their moment is over (a sweating face stayed through the cool part).
- `sfxprobe.mjs` (hot-word check) now expands beat components, so cues in `fact2beat.tsx` etc. are checked too.
