---
name: animate
description: Turn an approved football story (story.vN.json from research) into a 3D-animated narrated YouTube Short with Remotion + three.js - optional reference-video breakdown, a one-shot-per-line storyboard for approval, a fixed Gemini voice with silences tightened in post and exact times for spoken numbers, a scene built on the plugin's remotion-3d template (camera rig, panel builder, shader pattern sphere, ring, counters, tags, word-timed captions), a like & subscribe outro that loops back to frame 0, render, loudnorm, frame checks, cost and hand-over. Use when the user says "animate this story", "3D explainer", "make an animated short", "explain it with 3D animation", or invokes /football-stories:animate.
---

# Animate a story (3D explainer Short)

Approved story → (reference breakdown) → storyboard ✋ → voice → tighten → scaffold → scene →
render → check → cost → hand over. Research, fact checks and script approval happen in
`/football-stories:research`; this skill never redoes them.

## Paths

| What | Where |
|---|---|
| Story | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/story.v<N>.json` (`FOOTBALL_SHORTS_DIR` overrides `shorts/`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{validate.py,tts.py,align.py,tighten.py,anim.py,cost.py}` |
| Template | `${CLAUDE_PLUGIN_ROOT}/templates/remotion-3d/` (read `references/template.md` before writing a scene) |
| Python | `PY=<shorts dir>/.venv/bin/python` (setup.sh: Pillow, faster-whisper, numpy) |
| Reference tools | football-shorts plugin: `build/scripts/fetch.py`, `build/scripts/sheets.py`, `enhance/scripts/analyse.py`. Find them with `find "${CLAUDE_PLUGIN_ROOT}/.." ~/.claude/plugins -path "*football-shorts*" \( -name fetch.py -o -name sheets.py -o -name analyse.py \) 2>/dev/null`. Missing: ask the user to install football-shorts |
| Worked example | `shorts/football-shape/` (story.v1.json, script-storyboard.md, reference-breakdown.md, anim/) and its rebuild on the template, `shorts/football-shape-test/` |
| Output | `storyboard.md`, `reference-breakdown.md`, `build/`, `anim/`, `<slug>_v<N>.mp4`, `notes.md` in the edit folder |

## Inputs

| Input | Default |
|---|---|
| Story path | latest `story.v*.json` in the most recent `shorts/<slug>/`; it must have signed-off facts |
| Reference video URL | none. Only when the user gives one |
| Voice | always `gemini:alnilam` (free), pace 1.0, no audition |
| Music | none (the user adds it at upload) |

If the user gives only an idea or a topic, stop and send them to `/football-stories:research`
(story cards → script → approval → handoff). Then come back with the story path.

## Procedure

1. **Check the story.** `python3 validate.py <story>`; stop on errors or unsigned facts. Set `"format": "explainer-3d"` if it isn't. If `<slug>_v<N>.mp4` exists, use `revise` (next version).

2. **Reference video (only if the user gave one).** Ask for an explicit yes before downloading, and say that the yes covers this one video only. Then:
   - `python3 fetch.py <edit folder> --accept-terms --rights creator --name ref <url>` (→ `src/ref.mp4`, logged in `src/sources.json`)
   - `$PY analyse.py src/ref.mp4 --out build` and `$PY sheets.py fine src/ref.mp4 --from 0 --to <dur> --fps 1 --out build/sheets`; Read the sheets.
   - Write `reference-breakdown.md`: header (title, channel, length, views, date, "reference only, not for reuse"), a beat table `| s | Visual | Narration |`, **what makes it work** (pace, words/s, how often the picture changes, backgrounds, caption style, loop), **what's wrong or missing** (factual errors, unexplained steps).
   - Its footage is never reused, and the script never mentions the other video or its creator: the Short must stand on its own for a viewer who hasn't seen it. Set `anim.reference` to the breakdown file.

3. **Storyboard → wait for OK.** Write `storyboard.md` and show it as a table:
   `| # | Line | Words (s) | 3D shot | Camera | Overlay (counter / tag / ring) | Lands on |`
   - One 3D shot per narration line, in order. The shot shows the claim itself (a mechanism, a count, a comparison), not decoration. The picture changes every 1.5–2.5 s.
   - A counter or tag wherever a number is spoken, popping in on that word; the tag carries the fact behind the number (year, unit).
   - The hook line opens on the hero object at the hero camera; the last frame matches the first (camera back to HERO, object back to its frame-0 state, spin corrected to its symmetry), with the outro badge over the closing seconds.
   - Simplified, generic designs for real products (no logos or brand artwork); no realistic people.
   - Note what is computer-generated for the disclosure.
   Stop and wait for the user's OK or edits. Nothing gets built before that.

4. **Voice (no audition).** Set `narration.style` to exactly:
   `Confident, clear YouTube explainer revealing a secret. Firm and commanding but never rushed; speak every word distinctly. Real pauses where marked. Hit the CAPS words and the numbers hard.`
   Then `python3 tts.py <story> --voice gemini:alnilam --pace 1.0` (one take; free key: mention once that free-tier prompts may be used to improve Google products), and `$PY align.py <story>`. Report `CHECK` pronunciation flags as the narrate skill does (lexicon respelling + one new take if the user hears a problem). Ignore `note` lines for number words: step 5 fixes them.

5. **Tighten + number times.** `$PY tighten.py <story>` cuts the silences (0.35 s between lines, 0.25 within a line, 0.30 in number lists, 0.45 for the hook pause from a `<pause>` tag in the first line or `--pause L1:7=0.45`, 0.6 s tail) → `build/narration_alnilam_p100_tight.wav`, re-aligns it, and patches spoken numbers to Whisper's own times. Target 20–30 s: over 30, propose words to cut (don't speed up); a hook that needs more air gets `--pause`. Check that every number word was patched (`warn: number ... not found` means look at that line), then `open` the wav for the user if any cut sounds abrupt. Re-running is safe: it reads `narration.edit.from`. Don't run align.py after this step: it rewrites the words file without the number patch (use `tighten.py --words-only`).

6. **Scaffold.** `python3 anim.py init <story>` → `anim/` (template copy, local `.npmrc` with registry.npmjs.org, remotion/@remotion/cli/@remotion/three pinned to 4.0.530, three, @react-three/fiber, `npm ci`, `npm install-scripts approve esbuild`, `npm rebuild esbuild`, fonts from `shorts/fonts`, narration + words synced). It keeps an existing `src/Scene.tsx`.

7. **Write the scene.** Replace `anim/src/Scene.tsx` (the starter) with the storyboard, using `references/template.md`:
   - Anchor every change to a word: `at("L3", "pentagon")`, `at("L6", -1)`, `lineEnd("L4")`. No hard-coded seconds.
   - Use the kit: `CameraRig` keys (HERO first and last), `Buf`/`panel`/`Panels` for polygon solids and tilings (seam + inset panel + inflate), `PatternSphere` for panel/region layouts, `Ring`, `Counter`, `Tag`, `ramp`/`pulse`/`shown`/`pop`, `loopTo` for the spin.
   - Topic geometry goes in its own module next to Scene.tsx (copy the pattern of `examples/ball.ts`; import the ball module only when the topic is the ball).
   - Overlays: numbers/tags in the top band (y 200–560), captions at y 1330, the subject between; nothing on the subject.
   - `npx tsc --noEmit -p .` must pass. Preview tricky moments with `python3 anim.py render <story> --frames a-b` or `npx remotion still src/index.ts Short out/x.png --frame=N --gl=angle` and Read them.

8. **Outro.** Nothing to write: `Short.tsx` shows `SubscribeBadge` (thumbs-up tap, red SUBSCRIBE pop, "The Football Adda", @footballaddaclub) for `OUTRO_S` = 3.0 s after the last word (one constant in `kit/Outro.tsx`; channel rule: at least 2.5 s, never shorten it), no voice, gone on the last frame. The scene must finish its loop during it (`LAST_T`).

9. **Render + check.** `python3 anim.py render <story>`: `npx remotion render ... --gl=angle` → `anim/out/raw_v<N>.mp4` → loudnorm I=-14:TP=-1.5:LRA=11 (video copied, AAC 192k) → `<slug>_v<N>.mp4`, then the check: a 1 fps sheet of the whole Short, frames at every spoken number (+0.35 s) and the first/last frame in `build/check/`, loudness, and the loop SSIM (frame 0 vs last frame above the captions; aim ≥ 0.98). Add `--at` for tag moments on non-number words (`anim.py check <story> --at ...`). Read every sheet and confirm: nothing clipped at the frame edges, overlays never on the main object, each change lands on its word, captions legible, the badge clean. Fix and re-render before showing the user (the mp4 can't be overwritten: for a re-render of the same version, the user may delete it, or copy the story to the next version as revise does). At most two internal passes; report what you could not fix.

10. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "animate v<N>" --slug <slug>`.

11. **Hand over.** `open <mp4>`. In chat: the path and duration; a beat table `| s | Line | Shot | Overlay |`; known limits (simplified designs, interpolated words, anything the check showed); voice (Gemini alnilam, free tier) and "Narration voice is AI-generated; animations are computer-generated." for the description; the cost lines; then suggest `/yt-insights:metadata` for the title, description and hashtags, and `/football-stories:revise` with numbered points for changes. Write `notes.md` (story, facts, voice + edit settings, storyboard, render log with Claude cost).

## Story fields this skill adds

| Field | Written by | Meaning |
|---|---|---|
| `format: "explainer-3d"` | step 1 | no `scenes`/cards: the picture is `anim/` |
| `narration.edit` | tighten.py | `{from, between, within, numbers, hook, tail, pauses, duration, numbers_patched}`: the untightened source and the settings, so a re-run starts from the source |
| `anim.dir`, `anim.template`, `anim.composition` | anim.py init | the Remotion project folder (`anim`), `remotion-3d`, `Short` |
| `anim.storyboard`, `anim.reference` | steps 2–3 | `storyboard.md`, `reference-breakdown.md` |
| `anim.render` | anim.py render | `{raw, mp4, duration, date}` |
| `disclosure.altered_or_synthetic: true` | step 3 | computer-generated animation, with the note above |

## Hard rules

- Every narrated claim traces to a signed-off fact; no new claims on screen beyond the narration and facts.
- No download without the user's explicit yes, asked for each reference video; reference footage is never reused, and the Short never mentions the other video.
- One free take per request; never loop takes. No paid voice unless the user asks.
- Versions only go up; never overwrite an earlier story file or mp4. Never touch another session's edit folder.
- Keys stay in `~/.config/…/.env`; none in the story, the anim project or the plugin.
- Every video ends with the like & subscribe card for at least 2.5 s (`OUTRO_S` = 3.0 in `kit/Outro.tsx`). Never remove `SubscribeBadge` from `Short.tsx` or shorten `OUTRO_S` below 2.5. An `anim/` project made before this rule keeps its old `OUTRO_S`: copy the template's `src/kit/Outro.tsx` over it before rendering a new version.
