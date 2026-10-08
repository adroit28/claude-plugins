# Changelog

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
