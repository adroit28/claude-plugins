---
name: narrate
description: Voice a football story script. Lists and auditions voices (free Gemini TTS en-IN voices, local Kokoro, macOS say, the paid Gemini key, or the user's own recording), makes one take, slows it to the chosen pace (default 0.93), aligns every word with Whisper and flags probable mispronunciations. Use when the user says "narrate this", "voice options", "try another voice", "use my recording", "slower", "faster", "the name sounds wrong", or invokes /football-stories:narrate.
---

# Narrate a story

Script in, timed narration out: `build/narration_<voice>_p<pace>.wav` + `build/words_*.json`,
registered in the story file so `build` picks them up.

## Paths

| What | Where |
|---|---|
| Story | `${CLAUDE_PROJECT_DIR}/shorts/<slug>/story.v<N>.json` (latest version) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{tts.py,align.py,setup.sh,cost.py}` |
| Python | `PY=<shorts dir>/.venv/bin/python` (setup.sh; faster-whisper, kokoro-onnx) |
| Keys | `~/.config/football-stories/.env`: `GEMINI_FREE_KEY=` (AI Studio key from a project **without billing**), `GEMINI_PAID_KEY=` (falls back to `~/.config/gemini-image/.env`). Never in the plugin or the story. |
| Lexicon | `shorts/lexicon.json` (name respellings, shared by all stories) |
| Reference | `references/voices.md` (options, verified status, costs, pronunciation) |

## Inputs

| Input | Default |
|---|---|
| Story path | latest `story.v*.json` in the most recent `shorts/<slug>/` |
| `voice:` | `free` = Gemini free key + `en-in-tutor-1`, else Kokoro `bm_george` |
| `pace:` | 0.93 (1.0 for `own:` recordings) |
| `audition:` voices | none |
| A recording (m4a, wav…) | none |

## Procedure

1. **Check the story.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py <story>`; stop on errors (facts must be cited and signed off). If this version is already rendered, tell the user to use `revise` (it creates the next version).
2. **Voice choice.** If the user did not name one, say what `free` resolves to right now (run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/setup.sh` and read the GEMINI_FREE_KEY / Kokoro lines), and always add: the paid key gives the same Gemini voice for about ₹0.65 per 30 s. For choosing among Gemini voices: `python3 tts.py --list [--persona storyteller] [--gender female]` (free metadata call). Auditions (`tts.py <story> --audition v1,v2`) make one short line per voice: free on the free key; on the paid key only when the user asked, with `--voice-tier paid --yes-paid`, and say the count first.
3. **One take.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/tts.py <story> --voice <v> [--pace p]` (use `$PY` for `kokoro:`). One call per request; never loop takes to pick the best unless the user asked for several. For `own:<file>` the user's recording is converted, not synthesised. On HTTP 429 (free tier limit) say so and offer: wait, Kokoro, or the paid key.
4. **Length.** Read tts.py's duration line. Over 30 s (or the story's `length.max`, at most 40): propose which words to cut from which lines (don't speed up; pace 1.0 is the fastest to offer). Under ~18 s: fine, but mention it.
5. **Align.** `$PY ${CLAUDE_PLUGIN_ROOT}/scripts/align.py <story>` (first run downloads Whisper small.en once). Report matched/total.
6. **Pronunciation.** For each `CHECK` line, tell the user the second where the word is spoken and what Whisper heard, and ask them to listen (`open <narration wav>`). If they say it's wrong: add a respelling to `shorts/lexicon.json`, make one new take (paid = one more generation: say so), re-align. Mark `verified_by_ear: true` once they confirm.
7. **Pace changes** ("slower", "a bit faster") need no new take: `tts.py <story> --from-take <build/take_*.wav> --pace <p>`, then align again.
8. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step narrate --slug <slug>`.
9. **Hand over.** Voice, engine and tier, voice cost (free / ≈₹), duration, words matched, pronunciation flags, the wav path (`open` it), the Claude cost lines from step 8. Next: `/football-stories:build`.

## Hard rules

- Paid generations: one take per request unless the user asks for more. State the cost of every paid call.
- Tell the user the paid key gives the same voice for ~₹0.65 whenever `free` is used.
- Free-tier prompts may be used to improve Google products: mention it the first time the free key is used.
- Keys only in `~/.config/…/.env`; never print them.
- An AI voice narrating true facts: the description must carry "Narration voice is AI-generated." (the story's `disclosure` field). No voice cloning of real people.
- Never write into another session's edit folder.
