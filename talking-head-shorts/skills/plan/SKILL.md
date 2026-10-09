---
name: plan
description: Second stage of a talking-head Short - run the beat map on the cheap beat-mapper subagent (sentences, pauses, emphasis, numbers, names, energy peaks, dead air, blink frames; contact sheets stay in the subagent), then write the edit plan as one table for the user's OK - three hook options, punch-in steps at sentence boundaries, which images become cutaways with ring or label, which numbers become pills or counters, which words become slams, caption style and HOT words, sfx cues, drone, outro - and turn the approved table into the edit spec. Use after intake, when the user says "plan the edit", "what hooks can we use", or invokes /talking-head-shorts:plan.
---

# Beat map and edit plan

Needs from intake: `source.*`, `probe.json`, `transcript.json`, confirmed `captions.json`, `edit.v1.json` (from `spec.py init`).

## 1. Beat map (cheap model)

Spawn the `beat-mapper` subagent (sonnet; do not do this yourself, the images would stay in this context). Prompt it with the absolute slug folder,
`$S`, `$PY` and the window. It returns one compact table plus a short "what the frames show" list and writes `beatmap.md`. Read only that.

## 2. The plan table (the only thing the user must approve)

Write it as one table per group, times in SOURCE seconds, tone punchy, nothing about fact-checking or "this is my opinion". Choose from
what the beat map shows; do not invent facts or images.

| Group | What to decide | Rule of thumb |
|---|---|---|
| **Hook** (offer exactly 3) | `cold` = the user's own best line (a PEAK / NUM row, 1-2 s, cut from `clip: [a,b]`, text slammed over it); `slam` = text only over an accent burst (`seconds` 1.2-1.8); `image` = a user-supplied picture + slam (`image`, optional `box [left, top, height]`, optional `voice [a,b]` = a spoken line from the source that plays under it) | The hook line is the strongest claim, in 2-4 words, in the user's wording. The first 1.5 s decides retention |
| **Punch-in steps** | `steps: [[t, zoom], ...]`, zoom 1.0 / 1.12 / 1.14, at sentence boundaries or pauses, alternating | every 3-5 s, never mid-word; the first jump after the hook |
| **Cutaways** | each supplied image: `from`/`to` (1.0-1.6 s, on the word that names it), `ring [fx, fy]` as fractions of the picture to circle a detail, or `label` | 3-4 per 25 s at most; never over a NUM beat that has a pill |
| **Pills / counters** | digits in the speech: `pills` group (stacked, `big` number counts up when numeric, `small` label, `hot` for the money number), a `counter` for one big number | at the time the number is spoken; slide out together |
| **Slams** | one or two words the user stresses (PEAK + long pause before) | `top` 180-330 so they clear the captions at y 1240 |
| **Captions** | style from `style` (Anton 118, black stroke, current word yellow); `hot` = words that get the accent colour (numbers, names, the punchline) | 4-8 HOT words in 25 s |
| **Shake / flash** | `shakes` on one impact word, `flashes` on hard punch-ins | sparingly |
| **Sound** | `sfx` rows `[name, t, vol]`: whoosh on cutaway in, pop on pills, stamp on slams, bass on the hook and the biggest reveal; `hook_sfx` bass+stamp at 0; drone on | names: pop whoosh stamp bass riser tick ding sparkle (sfx.py --list) |
| **Outro** | the 3 s like & subscribe card | always |
| **Cleanup** | dead air > 0.8 s with nothing happening: say it (cuts are outside this plugin's scope; tell the user the cost of keeping them) | |

Also state: **fit** (cover/crop/blurfill), **background swap** yes/no (default no; only if the user asked or supplied one: then the `background`
stage follows), blinks in the source and how they are handled, and the final length (source window + hook + 3 s).

Check collisions in the table itself before showing it: slam vs pill group in the same seconds, two cutaways overlapping, cutaway ring on a
detail that is not in the picture (look at the image), a HOT word colour that will vanish on the background.

**Stop** and wait for the user's OK or changes. Revise the table, not the spec, until they approve.

## 3. Table to spec

After the OK, write `shorts/<slug>/plan.ops` (one op per line) and apply it in place (v1 has never been rendered):
```
$PY -I $S/spec.py fill shorts/<slug> --ops shorts/<slug>/plan.ops
$PY -I $S/spec.py validate shorts/<slug>
$PY -I $S/spec.py show shorts/<slug>
```
Ops used here: `set phrases @captions.json#phrases`, `set hot ["7","BEZZATI"]`, `set hook {...}`, `set steps [[0,1.0],[2.0,1.12]]`,
`append cutaways {"src":"a.png","from":3,"to":4.3,"label":"..."}` (`w`/`h` are filled from the image size when omitted), `append pills {...}`,
`append counters {...}`, `append slams {...}`, `append sfx ["whoosh",3.0,0.7]`, `set hook_sfx [["bass",0,1.0],["stamp",0.05,0.8]]`,
`set drift 0.009` (absolute zoom creep per window: ~0.03 over a 27 s clip), `bg ...` only in the background stage. Full schema: README.md.
Images must sit in `shorts/<slug>/` or `shorts/<slug>/assets/`. Fix every validate ERROR; read every warn.

Report the `spec.py show` timeline, `notes.md` State, cost, fresh-session offer.

## Restraint rules (learned on the Westside reel, 2026-10-09)

The first Westside cut had a graphic on nearly every line; the user removed half of them. Default to LESS:
- **One graphic per beat at most, and only where the visual is a real punchline.** Aim for roughly 5-7 graphics in a 50 s video, with plain talking head in between. Plain is fine; captions and jump-cut zooms already carry energy.
- **No decorative animation that only illustrates a word** (barricade for "road closed", crowd for "naach", food for "paneer", a mask or mane on the face, a loading bar for "shuru karo"). Test: would the joke still land with the graphic removed? If yes, cut it.
- **Never cover or crowd the face**, and never put a prop on the head or around it.
- **Never place a sound effect over speech.** After a held-beat gag (sad trombone, dhol) the next spoken words must start clean: leave a gap or end the sfx before the voice. Check every sfx that overlaps a voiced chunk, and duck or drop it.
- **Keep every word the speaker said** that carries meaning (names, "good news", the punchword). Before building, list the captions against a transcript of the cut and confirm none of his key words is missing; do not substitute a visual for a word.
- Show the user the proposed graphics as a short list and ask which to drop BEFORE building any of them.

## Safe zones and framing (all routes)

Graphics y 240-760, face y 900-1250 kept clear, captions top 1318 (3 lines max, 230 px), nothing important in the top 220 px, bottom 330 px or right 160 px
(app UI). Alternate the punch-in scale across every jump cut (1.00 / 1.10 / 1.20), never the same scale on both sides. Soft sources: zoom <= 1.3.
Joke-map table (line -> gag -> sfx -> mark) and the sound questions live in `timeline/SKILL.md`; use them here too when the plan has more than 2 graphics.
Several takes or a joined file: use the `timeline` skill instead of this stage.
