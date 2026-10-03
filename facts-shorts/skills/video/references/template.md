# remotion-2d template

`templates/remotion-2d/` is copied to `<slug>/anim/` by `anim.py init`. Only `src/Scene.tsx` is
written per Short; everything else is generic and refreshed by a re-run of `init` (which keeps
Scene.tsx).

```
anim/
  .npmrc                     registry=https://registry.npmjs.org/
  package.json + lock        remotion, @remotion/cli 4.0.530, react 19 (no three.js)
  public/                    fonts, narration.wav, src/ photos, sfx/*.wav  (anim.py sync, sfx.py)
  src/index.ts, Root.tsx     composition "Short", 1080x1920, 30 fps, DURATION_S from timing.ts
  src/Short.tsx              background + narration + <Overlays/> + Caption + SubscribeBadge
  src/timing.ts              word helpers and the Short's length
  src/words.json             narration.words (synced)      src/channel.json   name/tagline/avatar (synced)
  src/Scene.tsx              THE TOPIC: exports BACKGROUND (CSS) and Overlays({t})
  src/kit/                   anim.ts, overlays.tsx, props.tsx, Outro.tsx, index.ts (barrel)
  src/examples/hello-phone.tsx   Short #1's full scene (not imported)
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
| `Card` | `src, t, a, b, from="right"\|"left"\|"zoom", w=780, h=900, top=300, pos, tilt, slam, sepia=.25, fit` + children | paper-framed photo; slides in at `a`, Ken Burns, slides out at `b`; `pos` = object-position (keep the face in) |
| `NameTag` | `t, a, name, sub?` | yellow name bar at the bottom of a Card (child of Card) |
| `Bubble` | `t, a, text, x, y, color, bg, size=120, tail="left"\|"right", rot` | x/y = centre; only words someone actually said |
| `Stamp` | `t, a, text, top=690, color, size=150, rot=-9, until?` | slams down; pair with `stamp` sfx; give every Stamp an `until` (s) or it stays to the last frame |
| `Badge` | `t, a, text, x=90, y=240, bg, size=130, rot=-8, until?` | year/label tag; give every Badge an `until` (s) or it stays to the last frame |
| `Emoji` | `t, a, char, x, y, size=290, rot, wobble, crossAt?` | `crossAt`: greys out + red slash ("no bell needed") |
| `CountUp` | `t, a, b, from, to, unit?, top=860, bar=true, show=a, until, decimals` | counts from word a to word b: span a whole phrase |
| `Avatar` | `src, t, a, x, y, size=300, pos` | round face beside a diagram |
| `Rings` | `t, x, y, r0, grow, speed, n, color, width, half` | expanding rings (sound, signal); `half` = right half only |
| `HookProp` | `t, char, active, scale, y=560, opacity, size=470` | the opening object; shakes with rings while `active` |
| `Title` | `t, accent, rest, opacity, top=120, size=120` | hook title, accent in gold |
| `Question` | `t, a, b, top=380` | giant wobbling "?" |
| `Layer` / `Shake` / `Sway` | `transform/opacity` / `t, at, amp` / `t, from, deg, speed` | full-frame wrappers (absolute, inset 0) |
| `Sfx` | `at, src, vol=0.5` | plays `public/sfx/<src>.wav` from `at` s |
| helpers | `vis(t,a,b)`, `shake`, `clamp`, `back`, `PAPER`, `GOLD`, `RED` | |

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
