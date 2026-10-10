# remotion-2d template

`templates/remotion-2d/` is copied to `<slug>/anim/` by `anim.py init`. Only `src/Scene.tsx` is
written per Short; everything else is generic and refreshed by a re-run of `init` (which keeps
Scene.tsx).

```
anim/
  .npmrc                     registry=https://registry.npmjs.org/
  package.json + lock        remotion, @remotion/cli 4.0.534, @remotion/lottie, @remotion/effects, @remotion/motion-blur, @remotion/three + three (only bundled when a Scene imports kit/hero3d), react 19
  public/                    fonts, narration.wav, src/ photos, sfx/*.wav  (anim.py sync, sfx.py)
  src/index.ts, Root.tsx     composition "Short", 1080x1920, 30 fps, DURATION_S from timing.ts
  src/Short.tsx              background + narration + <Overlays/> + Caption + SubscribeBadge
  src/timing.ts              word helpers and the Short's length
  src/words.json             narration.words (synced)      src/channel.json   name/tagline/avatar (synced)
  src/Scene.tsx              THE TOPIC: exports BACKGROUND (CSS) and Overlays({t})
  src/kit/                   anim.ts, overlays.tsx, props.tsx, motion.tsx, lottie.tsx, world.tsx, burst.tsx, fx.tsx, phone.tsx, Outro.tsx, index.ts (barrel), hero3d.tsx (by path only)
  src/lottie/                animated Noto emoji (sun, eye, nose, relieved, sneeze, zap) + CREDITS.md
  src/examples/hello-phone.tsx   Short #1's full scene (not imported)   kit-0.8-demo.tsx   every 0.8 component once (not imported)
```

## timing.ts

| Export | Use |
|---|---|
| `at(line, word, nth?)` / `endOf(...)` | start / end of a word by 0-based index (negative from the line end) or caption text without punctuation (`"Ahoy!"` → `"ahoy"`, `"hello-girls"` → `"hellogirls"`); `nth` for a repeat in the line |
| `lineStart(line)`, `lineEnd(line)` | first start / last end in a line |
| `WORDS` | every word `{line, i, w, start, end}` |
| `END`, `OUTRO_AT`, `DURATION_S`, `LAST_T` | last spoken word, badge start (END + 0.05), length incl. the 3 s badge, time of the last frame |

Word times come from segalign.py (pause segments, words spread by length inside each), so a word
inside a long phrase can be ±0.2 s off. Anchor big moments to the **first word after a pause**
(line starts, words after a comma) where timing is exact; for mid-phrase words, use the word and
check the frame.

## kit/props.tsx

| Prop | Signature (main props) | Notes |
|---|---|---|
| `Card` | `src, t, a, b, from="right"\|"left"\|"zoom", w=960, h?, top?, pos, tilt, slam, sepia=.25, fit` + children | paper-framed photo; slides in at `a` (or `flip="y"\|"x"`: 3D flip-in, 0.8.0), Ken Burns, slides out at `b`. Without `h`: the photo's own shape (from `src/images.json`), fitted to and centred in the picture band, nothing cropped. With `h`: cropped, `pos` = object-position (keep the face in) |
| `Pair` | `t, a, b, first: {src, tag?, sub?}, second: {...}, stagger=.25, gap=50` | two photos for one beat, stacked vertically, both uncropped and sized to fill the band; never put two Cards side by side |
| `Hero` | `t, a, b, char, size=700, x=540, dy, wobble, crossAt?` | the main object of a beat with no photo, centred in the picture band and floating; two objects: `x` 290/790, size ~460 |
| `NameTag` | `t, a, name, sub?` | yellow name bar at the bottom of a Card (child of Card) |
| `Bubble` | `t, a, text, x, y, color, bg, size=120, tail="left"\|"right", rot` | x/y = centre, moved in so the bubble stays 40 px inside the frame; text shrinks to fit; only words someone actually said |
| `Stamp` | `t, a, text, top=690, color, size=150, rot=-9, until?, burst?` | slams down; pair with `stamp` sfx; give every Stamp an `until` (s) or it stays to the last frame; `burst` (true or a colour) throws particles as it lands |
| `Badge` | `t, a, text, x=90, y=240, bg, size=130, rot=-8, until?` | year/label tag; give every Badge an `until` (s) or it stays to the last frame |
| `Emoji` | `t, a, char, x, y, size=290, rot, wobble, crossAt?` | `crossAt`: greys out + red slash ("no bell needed") |
| `CountUp` | `t, a, b, from, to, unit?, top=860, bar=true, show=a, until, decimals` | counts from word a to word b: span a whole phrase |
| `Avatar` | `src, t, a, x, y, size=300, pos` | round face beside a diagram |
| `Rings` | `t, x, y, r0, grow, speed, n, color, width, half` | expanding rings (sound, signal); `half` = right half only |
| `HookProp` | `t, char, active, scale, y=560, opacity, size=470` | the opening object; shakes with rings while `active` |
| `Title` | `t, accent, rest, opacity, top=110, size=120` | hook title, accent in gold; always one line (shrinks to fit), ends above `PIC_TOP` |
| `Question` | `t, a, b, top=380` | giant wobbling "?" |
| `Layer` / `Shake` / `Sway` | `transform/opacity` / `t, at, amp` / `t, from, deg, speed` | full-frame wrappers (absolute, inset 0) |
| `Sfx` | `at, src, vol=0.5` | plays `public/sfx/<src>.wav` from `at` s |
| helpers | `vis(t,a,b)`, `shake`, `clamp`, `back`, `PAPER`, `GOLD`, `RED`, `W`/`H`/`EDGE`, `TITLE_TOP`, `PIC_TOP`, `picBottom()`, `aspect(src)`, `fitSize`, `textWidth` | layout bands and text measuring (Stamp/Badge/Title/Bubble already fit themselves) |

kit/anim.ts: `ramp(t,a,b,from,to,ease)`, `pulse(t,a,up,hold,down)`, `shown(t,a,b,in,out)`, `pop(t,at)`.
kit/overlays.tsx: `Caption` (Short.tsx draws it; 2 words, y 1330), `Counter`, `Tag`, `STROKE(px)`.
kit/Outro.tsx: `SubscribeBadge`, `OUTRO_S = 3.0` (min 2.5), name/tagline/avatar from `src/channel.json`.

## Patterns (from hello-phone.tsx)

- **Hook + loop.** `HookProp` + `Title` at frame 0, `active` (ringing) until the pick-up at `narration.lead`; fade out at line 2; `loopIn = ramp(t, OUTRO_AT, OUTRO_AT + 0.4)` brings them back under the badge, `active` again in the last 0.9 s, and a `ring` sfx at `LAST_T - 0.55`.
- **One beat per line.** A Card enters on the line's first word and leaves just before the next line; bubbles/badges pop on their word; a `whoosh` sfx 0.15 s before each card.
- **Show the joke.** A second card (the pirate) on "Haan, wahi jo..." with `Sway` and an emoji.
- **Numbers.** `CountUp` from the first word of the phrase to its last ("10-20 feet ... hai"), shown from the number word.
- **Negation.** `Emoji` with `wobble` and `crossAt` on "nahi", plus a `buzz`.
- **Payoff.** Two-sided ending (☎️ HELLO ✓ vs pirate AHOY sailing off), faded out under the badge.

## Gotchas

- Any wrapper div with a transform must cover the frame (`Layer`): a plain div lands below the screen.
- Photo sizes come from `src/images.json`, written by `anim.py sync`. A photo added to `src/` later needs a re-sync, or its Card falls back to w x 900 cropped.
- Emoji render with Apple Color Emoji in headless Chrome on macOS; flags and multi-codepoint emoji (🏴‍☠️) work.
- Photos: always look at `commons.py strip` first (some files come out rotated). A photo that doesn't
  read at phone size (small object on a white background) is better as an emoji or a drawn diagram.
- `npx tsc --noEmit -p .` before rendering; `anim.py still` for single frames is faster than a render.
- A 33 s Short renders in ~3 min on an M-series Mac (8 tabs).

## One import

`src/kit/index.ts` re-exports the whole kit and the timing helpers, so a scene needs one import line
(the old paths `./kit/anim`, `./kit/props`, `./kit/overlays`, `./kit/Outro`, `./timing` still work):

```ts
import { ramp, pulse, pop, Bubble, Stamp, Badge, Layer, Sfx, at, endOf, lineStart, lineEnd, WORDS, END, OUTRO_AT, LAST_T } from "./kit";
```

Give every `Stamp` and `Badge` an `until` (seconds) so it fades out; one left on screen breaks the loop
(last frame must match the first). `ramp(t, a, b)` with `b <= a` (an anchor that lands before the previous
one) no longer crashes: it becomes a near-instant step and logs a warning, so check the timing it points at.

## Motion kit (0.4.0, `kit/motion.tsx`)

Use these to stop a Short feeling like a slideshow. Rule of thumb: every beat moves (camera or type), and at least one beat per Short is kinetic type or a drawn diagram instead of an emoji.

| Component | Use |
|---|---|
| `Card kb drift punch` | Photo push-in (`kb` 0.12-0.16), sideways drift in px, `punch={[T.word]}` = fast +8 % push on a word; `pos` is the focus point |
| `Cam keys punch` | Wrap a diagram or beat: eased zoom/pan keyframes `{at, s, x, y}`, `punch` times. Keep zoom <= 1.1 or edge labels clip |
| `Kinetic text a b` | A word as the whole picture, slams in with shake; `strikeAt` draws a red strike-through (a myth), `sub` a small line under it. `\n` = stacked lines |
| `Draw d a b` | SVG path that draws itself with a glowing head (a path, a zigzag spark) |
| `Dots from to` | 10x10 people-grid that fills across a phrase, with `n / 100` readout; only for an "x out of 100" number |
| `Versus myth truth` | Top half myth, bottom half truth, gold divider wipes in |
| `Swipe at` / `Flash at` | Gold wipe over a cut (start it at `lineStart - 0.22`, pair with whoosh); impact flash. Use sparingly: one swipe at the myth-to-truth turn, not every line |
| `LottieEmoji` | `t, a, data, x, y, size=290, rot, crossAt?` | animated Noto emoji, same contract as `Emoji` (pops in at `a`, `crossAt` greys it out with a red slash), plays from `a` and loops. `data={LOTTIE.sun}`; bundled: `sun eye nose relieved sneeze zap` (🌞 👁️ 👃 😌 🤧 ⚡). Prefer it over `Emoji` whenever the emoji is bundled. CC BY 4.0: add "Animated emoji: Noto Emoji Animation by Google, CC BY 4.0." to the description |
| `LightLeakCut at, seed, hue` | a colour wash over a cut, starts 0.3 s before `at` (the next beat's start), lasts 0.8 s, changes no timing; `seed` = shape, `hue` = colour in degrees. Pair with a whoosh; use at the story's turns (3-5 per Short) and keep it at the top level of `Overlays`, never inside a `Cam`. Replaces `Swipe` where a softer, more colourful cut fits |
| `LiveBg` | Automatic in `Short.tsx`: drifting glows, dust, vignette. Scene may `export const BEATS = [secs]` so the glow kicks on story turns, or `export const LIVE_BG = false` |

Keep emoji accents out of kinetic text (they overlap); put them below it and size them <= 220.

## 0.8.0 motion + sound kit (all opt-in; an old scene renders exactly as before)

Story options (the `video` block, written to `src/options.json` by `anim.py sync`): `hotCaptions: true`, `hot: [...]`, `music: true`, `musicGain`, `grain`, `captions: false`.

| Component / option | Use and limits |
|---|---|
| `video.hotCaptions` | word-by-word captions, current word gold, HOT words (the CAPS words in each line's `tts`, or `video.hot: ["galti", "L3:dhakel", "L5:nahi#2"]`) big, red, tilted, one per chunk. Same band (y 1330). Write the script's CAPS only on the 1-2 words per line that carry the point. Render warns when an sfx peak lands on a HOT word: move the sfx before or after it |
| `video.music: true` | synthesized 108 BPM bed ducked under the narration, -14 LUFS / TP -1.5 in the final mix. Off unless the user says yes. `musicGain` (default 0.45) if the bed is too loud/quiet. No music on a Short that is mostly silence-driven |
| `Glitch t a b text sub` | RGB-split slam with scan lines for a myth reveal. One per Short. Pair with `glitch`/`scratch` sfx |
| `Title3D t accent rest opacity sweeps` | extruded hook title, drawn settled from frame 0 and static (so the last frame still matches); light sweep at each time in `sweeps` (add `LAST_T - 0.9` for a second one). Drop-in for `Title` |
| `Card flip="y"\|"x"` | 3D flip-in instead of the slide, for the key photo. Not on every card: 1-2 per Short |
| `CalendarFlip t a b from to label steps until` | page-flip number from -> to across a phrase (a year); lands on `to` at `b`. Give it an `until` |
| `Transition kind at dur color dir` | `whip` (hard turn, motion blur), `slide`, `iris` (closes on `x,y`), `flip`, `wipe`. A cut effect at a time; changes no timing; TOP LEVEL of `Overlays` (never inside Cam/Layer). **2-3 per Short, at the story's turns only**; pair with `whoosh`/`revwhoosh` |
| `Blur a b kind layers lag` + `{(t) => ...}` | motion blur (`@remotion/motion-blur`: `trail` ghosts, `camera` shutter average) for a FAST move only (a sweep, flying germs), active only between a and b; children get the (lagged) time as a function argument, so use `tt` inside, not the outer `t`; no Sfx inside. Costs about layers x (camera: samples x) the render time of that subtree for those frames: wrap one prop, keep the window under ~1 s |
| `springy` prop / `export const SPRINGY = true` | `Emoji`, `Hero`, `LottieEmoji`, `CalendarFlip`, `Notify` entrances (and `pop()` for the whole scene) use Remotion `spring()` instead of the classic curve. Use it in new scenes; leave it off to keep an old scene identical |
| `Meter t a b to label sub icon until` | danger/level gauge filling across a phrase (yellow -> red, shakes near full). Give it an `until` |
| `ChatBubbles t a msgs title until` | messages pop at their times (`[time, mine, text][]`); generic text only |
| `Notify t a app title body icon until` | phone notification card dropping in; pair with `notify` sfx |
| `ShareSheet t a sendAt friends tickAt until` | ending CTA ("share with the friend who does this"): contacts ticked, SEND fires at `sendAt`; must finish before the outro card (OUTRO_AT) |
| `Confetti t a`, `Burst`, `Stamp burst` | particles for a win or a landing; once or twice per Short |
| `Hero3D` + `EarCanal3D` (`import ... from "./kit/hero3d"`) | **at most one opt-in 3D beat per Short**, 2-4 s, at the key beat; a transparent three.js canvas in the picture band driven by `t`; captions/text stay 2D. Adds ~30-60 s render time. Build another subject by copying `EarCanal3D` |
| `video.grain` | film grain over everything. **Off by default**: noise doesn't compress and can double the file size. If on, `true` = 0.06, never above 0.08 |

New sfx (sfx.py): boom revwhoosh glitch scratch sadbone boing notify kaching confetti shutter tick2. `sadbone` once per Short at most. Worked example of everything: `src/examples/kit-0.8-demo.tsx`.
Animated emoji beyond the six bundled: candidates (with size) are in `src/lottie/CREDITS.md`; ask the user before downloading any.
