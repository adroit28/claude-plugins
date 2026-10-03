---
name: video
description: Build the 1080x1920 video for a narrated facts-channel Short with Remotion (2D, no 3D) - a storyboard table for the user's OK, public-domain Commons photos (download only after a yes, logged with licences, contact strip for rotation), emoji props and simple diagrams, a scene on the plugin's remotion-2d kit (photo cards with name tags, speech bubbles, stamps, badges, counters across a phrase, an opening ring hook and a loop back to frame 0), synthesized sound effects, render, loudness and frame checks, and a hand-over. Use when the user says "make the video", "build the short", "storyboard", "animate this", pastes a facts-shorts video handoff, or invokes /facts-shorts:video.
---

# Video

Narrated story → storyboard ✋ → assets ✋ (downloads) → scaffold → scene → sfx → render → check → hand over.

## Paths

| What | Where |
|---|---|
| Story | `<root>/<slug>/story.v<N>.json` with `narration.audio` + `narration.words` (`<root>` = `${CLAUDE_PROJECT_DIR}/facts-channel`, `FACTS_DIR` overrides) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{validate.py,commons.py,anim.py,sfx.py,cost.py}` (`python3`) |
| Template | `${CLAUDE_PLUGIN_ROOT}/templates/remotion-2d/` — read `references/template.md` before writing a scene |
| Worked example | `templates/remotion-2d/src/examples/hello-phone.tsx` (Short #1's whole scene on the kit) |
| Facts | `<slug>/verify.md` (Images section: Commons candidates) |
| Output | `storyboard.md`, `src/` (photos + `sources.json`), `anim/`, `build/check/`, `<slug>_v<N>.mp4`, `notes.md` |

`<story>` is the FULL path to `story.v<N>.json` (a file, never the folder). Pass that file to every script.

## Procedure

1. **Check.** `python3 validate.py <story>` (script stage). Needs `narration.words`; if missing, run narrate first. If `<slug>_v<N>.mp4` exists, use `revise`.
2. **Storyboard → wait for OK.** Read the words file for each line's start time. Write `storyboard.md` and show it:
   `| # | Line (caption) | s | Visual | Prop / overlay | SFX | Lands on (word) |`
   - The picture changes every 1.5–2.5 s and shows the claim (who, what, when, how many), not decoration.
   - Visual types: **photo card** (real public-domain photo of the person/object, with a NameTag); **emoji prop** (☎️ 🔔 🍋 🌶️ 💰 🦠: renders in headless Chrome); **diagram** (simple shapes/text built in the scene) when an archive photo wouldn't read at phone size (the 1876 telephone photo didn't: the hook used ☎️); **bubble** for a word someone said; **stamp**/**badge** for a label or a year; **CountUp** for a spoken number, run across the whole phrase.
   - Opening: hook prop + title in the first frame (the frame viewers see in the feed), an opening sound (ring/whoosh) during `narration.lead`. Ending: the payoff, then the hook prop returns under the like & subscribe card so the last frame matches the first.
   - No generated images of real people. Paid image generation only if the user asks, one image per request, after asking.
   **Ask the user whether this Short needs captions** (AskUserQuestion: captions on / off; don't assume). Off → set the story's `"video": {"captions": false}` (on → `true`); `anim.py sync` passes it to the kit (`src/options.json`) and the Short draws no caption band, so give the picture the freed space (y up to ~1700) and keep key words on screen as badges/stamps.
   Stop until the user approves or edits.
3. **Assets → ask before downloading.** For each photo: pick from verify.md's Images or `python3 commons.py search "<query>"` (metadata only). Check the title/date mean what the story means ("Hello Girls" on Commons is the 1918 US Army unit, not the 1880s operators). Show the list (file · licence · what it shows) and ask for a yes. Then per file: `python3 commons.py get <story> "File:..." --as <name>.jpg --yes` (logs title/page/licence/author/attribution to `src/sources.json`). `python3 commons.py strip <story>` and Read the strip: a sideways photo → delete it and `get` again with `--rotate 1|2|3` under a new name. CC BY/BY-SA files need their attribution in the description (metadata step).
4. **Scaffold.** `python3 anim.py init <story>` → `anim/` (template copy, local `.npmrc` → registry.npmjs.org, fonts, `npm ci`, esbuild approved; narration, words, channel card and `src/` images synced into `anim/public`). Then `python3 sfx.py <story>` → `anim/public/sfx/*.wav` (ring click riser bass horn whoosh ding buzz stamp waves pop tick coin sparkle).
5. **Write the scene.** Replace `anim/src/Scene.tsx` (the starter) following the storyboard and `references/template.md`:
   - Beat times once at the top: `const T = { ahoy: at("L3", "ahoy"), l4: lineStart("L4"), ... }`. Words are matched by caption text without punctuation (`"hellogirls"`, `"1877"`). No hard-coded seconds except the lead (`pick: <narration.lead>`).
   - Use the kit: `Card`+`NameTag`, `Bubble`, `Stamp`, `Badge`, `Emoji` (`wobble`, `crossAt`), `CountUp`, `Avatar`, `Rings`, `HookProp`, `Title`, `Question`, `Shake`/`Sway`/`Layer`, `Sfx`. Any wrapper with a transform is a `Layer` (absolute, inset 0).
   - Layout: title/badges y 120–560, the picture y 300–1280, captions at y 1330 (the kit draws them). Keep text off faces.
   - `cd anim && npx tsc --noEmit -p .` must pass. Look at tricky moments with `python3 anim.py still <story> --at 3.2 11.5` (Read the PNGs) or `anim.py render <story> --frames 0-120`.
   - Text props are plain strings: write real line breaks, never a literal `\n`. Keep every tag/badge/overlay out of the caption band (y > 1300) and at least 40 px inside the screen edges. Every Stamp/Badge gets an `until`.
6. **Render + check.** `python3 anim.py render <story> [--at <times of key moments>]` → `anim/out/raw_v<N>.mp4` → loudnorm −14 LUFS → `<slug>_v<N>.mp4`, `build/scene_v<N>.tsx` snapshot, then the check: 1 fps sheets, `--at` frames, first vs last frame, loudness, loop SSIM. Read every sheet: nothing clipped at the edges, text never on a face, each change on its word, captions legible, the badge clean, loop close (SSIM ~0.88 is normal while the badge covers the end). Fix and re-render before showing the user; the mp4 can't be overwritten, so for an internal re-render of the same version delete only the mp4 you just made (never an earlier version's). At most two internal passes; report what you couldn't fix.
   In step 6, read the LAST frame sheet specifically for leftover overlays.
7. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "video v<N>" --slug <slug>`.
8. **Hand over.** `open <mp4>`. Path, duration (narration + 3 s card), a beat table `| s | Line | Visual |`, photo credits (from `src/sources.json`), known limits, cost lines. Write `notes.md` (storyboard, assets, voice, render log, cost) and `NEXT.md` with `/facts-shorts:metadata <story>` (and `/facts-shorts:revise` for numbered feedback); show it.

## Hard rules

- No download (images, models, videos) without the user's explicit yes for that list.
- Prefer public-domain photos and drawn graphics/emoji over generated people; paid generations only on request, one per request.
- Every claim on screen is in the narration and VERIFIED in verify.md; a paraphrase is never shown in quote marks.
- Versions only go up; never overwrite an earlier story file or mp4.
- Every video ends with the like & subscribe card, 3 s (`OUTRO_S` in `kit/Outro.tsx`; never below 2.5 s, never removed).
- Never run `npx remotion` directly; render only with `anim.py render`.
