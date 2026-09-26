---
name: revise
description: Apply the user's numbered feedback to a narrated football story Short built by /football-stories:build - card text or layout, caption text, script wording, voice, pace, timing, hits, length - as a new story version, re-rendering only what changed and proving each fix with before/after frames. Use when the user says "change the card", "slower voice", "try another voice", "cut it to 25 seconds", "the name is wrong", "different ending", or invokes /football-stories:revise.
---

# Revise a story Short

Feedback in, next version out, with proof. The story file is the source of truth; each
revision is `story.v<N+1>.json` and `<slug>_v<N+1>.mp4`.

## Paths

| What | Where |
|---|---|
| Edit folder | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/` (highest `story.v<N>.json`, `build/timeline_v<N>.json`, `notes.md`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{tts.py,align.py,validate.py,cards.py,compose.py,clips.py,finish.py,check.py,cost.py}` with `PY=<shorts dir>/.venv/bin/python` |
| References | `../build/references/{story-format,templates,channel-style}.md` · `../narrate/references/voices.md` |

## Inputs

| Input | Default |
|---|---|
| Feedback (numbered, or prose you number yourself) | required |
| `slug:` | the edit folder most recently rendered under `shorts/` |

## Procedure

1. **Locate.** Highest `story.v<N>.json`, its mp4, `build/timeline_v<N>.json`, `notes.md`. A time the user names ("at 14 s") maps to a scene and state through the timeline's `cues`; say which.
2. **Translate** each item into one line: `#k "<their words>" → <field> : <change> → <steps to re-run>`.

   | Change | Edit | Re-run | Cost |
   |---|---|---|---|
   | Card text / layout / colour | `scenes[i].props` | cards (changed cards only) → compose → (clips) → finish | free |
   | Which word a reveal lands on | `scenes[i].steps[k].at` | compose → finish | free |
   | Caption spelling / punctuation (same words spoken) | the line's `text`; copy the old text into `tts` first if the line has none, so the voice input is unchanged | align (existing audio) → compose → finish | free |
   | Caption with different words than spoken | not possible: captions are the spoken words. Offer a card change or a new take | — | — |
   | Pace ("slower") | `--from-take` with new pace | tts (no API) → align → compose → finish | free |
   | Script wording, length ("make it 25 s") | `narration.lines` (+ facts if content changes) | validate → new take → align → compose → finish | free tier / ~₹0.65 paid, one take |
   | Voice | narrate with the new voice | take → align → compose → finish | per voice |
   | Name pronunciation | `shorts/lexicon.json` or the line's `tts` | take → align → … | one take |
   | Hits, whooshes, loudness, bed | `audio` | compose (whoosh) / finish | free |
   | Hold at the end, lead, motion | `motion` | compose → finish | free |
   | Footage: window, crop, a logo or score bug still showing, slow-mo | `clips[i]` (`from`/`to`, `crop`, `pre: delogo=…`, `slow`) | clips → finish | free |
   | Add or swap footage | new `assets` (kind video, after the user's yes for this video) + `clips` | fetch → clips → finish (build step 3) | free |

   Whenever compose re-runs and the story has `clips`, run clips.py after it (finish.py refuses otherwise).
3. **New version.** Copy `story.v<N>.json` to `story.v<N+1>.json`, set `"version": N+1`, apply the edits, then run only the steps the table lists. For new content, verify the new facts first: call `football-stories:fact-finder` with `mode: verify` and the numbered claims, spot-check what it returns (research skill rules), add the facts to the story, then run `validate.py --stage build`. If a new take is needed, confirm with the user when it's on the paid key.
4. **Prove it.** `check.py <slug>_v<N+1>.mp4 --timeline build/timeline_v<N+1>.json` (Read the sheet), then `check.py <new.mp4> --ref <old.mp4> --at <seconds of each item>` and Read the compare sheet (ref left, new right). Timing moves when pace or words change, so pick times inside the same scene in both. If an item is not visibly fixed, adjust once more before handing over.
5. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "revise v<N+1>" --slug <slug>`.
6. **Hand over.** `open` the new mp4. Per item: done / done differently (why) / not done (why), with the scene and seconds; new duration and any rule it now breaks (over 30 s or `length.max` etc.); new path; the previous version kept; the cost lines. Invite the next numbered list.
7. **Record.** Append to `notes.md`: version, date, feedback verbatim, changes, voice cost and Claude cost, checks.

## Hard rules

- Never overwrite an earlier story file, `graphics/v<N>/` folder or mp4; versions only go up.
- Every item gets an explicit outcome. Show changed seconds on a sheet; don't claim a fix from numbers alone.
- Paid takes: one per request unless the user asks for more; state the cost.
- New or changed claims need facts with sources before they are narrated or put on a card.
- Channel rules still apply (20–30 s or up to `length.max` ≤ 40, hook first, clean final card); if the user asks for something that breaks one, do it and note the rule in one line.
