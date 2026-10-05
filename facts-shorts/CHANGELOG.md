# Changelog

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
