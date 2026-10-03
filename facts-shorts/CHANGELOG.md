# Changelog

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
