# remotion-3d template

`templates/remotion-3d/` is copied to `shorts/<slug>/anim/` by `anim.py init`. Only
`src/Scene.tsx` (and any topic geometry module beside it) is written per Short; everything else is
generic and is refreshed by a re-run of `init`.

```
anim/
  .npmrc                    registry=https://registry.npmjs.org/ (a global ~/.npmrc may point elsewhere)
  package.json, package-lock.json   remotion, @remotion/cli, @remotion/three = 4.0.530; three; @react-three/fiber
  remotion.config.ts        jpeg frames, overwrite
  public/                   Anton, Barlow Condensed ExtraBold + SemiBold (from shorts/fonts), narration.wav (synced)
  src/index.ts, Root.tsx    composition "Short", 1080x1920, 30 fps, DURATION_S from timing.ts
  src/Short.tsx             background + narration + <Scene/> in a ThreeCanvas + <Overlays/> + Caption + SubscribeBadge
  src/timing.ts             words.json helpers and the Short's length
  src/words.json            narration.words (synced)
  src/Scene.tsx             THE TOPIC: exports BACKGROUND, CAMERA, Scene, Overlays
  src/kit/                  anim.ts, camera.tsx, panels.tsx, pattern.tsx, Ring.tsx, overlays.tsx, Outro.tsx
  src/examples/ball.ts      example module (truncated icosahedron, honeycomb, sheet curl); not imported by kit/
```

## Scene.tsx contract

```tsx
export const BACKGROUND = "radial-gradient(...)";              // CSS behind the canvas
export const CAMERA = { fov: 40, near: 0.05, far: 100, position: [x, y, z] };  // = HERO.pos
export const Scene = () => { const t = useCurrentFrame() / useVideoConfig().fps; return <>...</>; };
export const Overlays = ({ t }: { t: number }) => <>...</>;  // counters and tags (HTML over the canvas)
```

Define the beat times once at the top: `const T = { sphere: at("L1", "sphere"), twelve: at("L4", "twelve"), ... }`.

## timing.ts

| Export | Use |
|---|---|
| `at(line, word, nth?)` / `endOf(...)` | start / end of a word: 0-based index (negative from the line end) or its text (`"isn't"` → `"isnt"`); `nth` for a repeat in the same line |
| `word(line, w)` | the word object `{line, i, w, start, end}` |
| `lineStart(line)`, `lineEnd(line)` | first start / last end in a line |
| `WORDS` | every word, for derived lists (e.g. all number words) |
| `END`, `OUTRO_AT`, `DURATION_S`, `LAST_T` | last spoken word, badge start (END + 0.05), the Short's length (badge included), time of the last frame |

## kit

| Module | Exports | Notes |
|---|---|---|
| `anim.ts` | `ramp(t,a,b,from,to,ease)`, `pulse(t,a,up,hold,down)`, `shown(t,a,b,in,out)`, `pop(t,at)`, `loopTo(raw,from,to,step)`, `ease` | `loopTo` adds a smooth correction over [from, to] so `raw(to)` lands on `raw(0)` + k·step: use step = the object's symmetry (2π/5 for the ball about a pentagon axis) with from = END, to = LAST_T |
| `camera.tsx` | `CameraRig({t, keys})`, `camAt`, `lerpCam`, types `Cam`, `CamKey` | keys `{at, dur, cam: {pos, look}}`, each eases from the current camera; first and last = HERO |
| `panels.tsx` | `Buf`, `panel(buf, pts, color, outward, {inset, K, inflate, center, radius, seam})`, `Panels({build, opacity})`, `centroid`, `newell`, `regularPolygon`, `inflater`, `SEAM` | a panel = dark seam polygon + inset panel lifted along the outward normal; `K` subdivides so `inflate` 0→1 bulges it onto the sphere (`center`, `radius`). `Panels` rebuilds one mesh per frame from `build()`; its material is keyed on transparency (a reused material turns frames after a fade grey) |
| `pattern.tsx` | `PatternSphere({cells, colA, colB, twist, opacity, radius})`, `OCTA`, `CUBE`, `TETRA`, type `Cells` | shader sphere: nearest-cell colour with seams (spherical Voronoi, ≤ 32 cells), `kinds` 0/1 pick colA/colB, `twist` curves the seams. Panel layouts, regions, maps |
| `Ring.tsx` | `Ring({opacity, color, position, radius, width})` | camera-facing highlight circle |
| `overlays.tsx` | `Caption({t, until, max, y})`, `Counter({value, label, opacity, t, hitAt, hitColor, top})`, `Tag({t, at, over, value, under, color, opacity, top})`, `STROKE(px)`, `CAPTION_Y` | captions: up to 2 words, break at punctuation, y 1330, hidden from the badge on (Short.tsx does this). Counter top 230, Tag top 210 |
| `Outro.tsx` | `SubscribeBadge({t, start})`, `OUTRO_S`, `CHANNEL`, `HANDLE`, `OUTRO_TOP` | 3.0 s (min 2.5): card in, thumbs-up pops and gets tapped blue, red SUBSCRIBE pops and is pressed with a shine, card out before the last frame. Change the length only in `OUTRO_S` |

## Patterns from the worked example (`shorts/football-shape-test/anim/src/Scene.tsx`)

- **One geometry, several states.** The L1 ball and the L3–L5 sheet are the same panels: a `curl` value (0 flat → 1 closed) and an `inflate` value (0 flat faces → 1 round) are ramped on words, and `build()` places every panel from them.
- **Reveal order.** Sort faces outward from a start face; each panel pops in with `ramp(t, ft, ft + 0.25, 0, 1, Easing.out(Easing.back(1.6)))`, and a counter counts the ones already shown.
- **Highlight on the word.** `color.lerp(GOLD, pulse(t, at("L1", "pentagons")))`.
- **Swap layouts on numbers.** `PatternSphere` with a layout per spoken number, a quick fifth-turn spin at each, and a `Tag` with the year above and the unit below.
- **Loop.** HERO camera key back before the end; layout back to the frame-0 one at END + 0.35; `loopTo` on the spin from END to LAST_T. `anim.py check` prints the loop SSIM (aim ≥ 0.98).

## Gotchas

- Render with `--gl=angle` (what the worked example used; a 28 s Short renders in ~15 s on an M-series Mac).
- Frames render in parallel tabs, and a tab carries three.js state from the frames it rendered before. Anything that changes a material's program (transparent on/off, defines) needs a new material (a `key`), or that frame will differ from the same frame rendered alone. Compare a suspicious frame with `npx remotion still ... --frame=N`.
- Overlays are HTML: keep them out of the subject's box (y ~650–1280 at the hero camera); use the top band for numbers.
- `npx tsc --noEmit -p .` before rendering: a type error stops the bundle late.
- Long camera moves across a cut read as a whip; give the eye 0.4–0.6 s per move.
