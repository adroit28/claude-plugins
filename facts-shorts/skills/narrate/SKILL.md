---
name: narrate
description: Voice an approved facts-channel Hinglish script with free Gemini TTS en-IN voices - make one full take (no auditions) (default en-in-commercial-1, pace 1.0, the channel's style prompt), then time every word from the pauses in the take (segalign.py, because English Whisper can't transcribe Hinglish) with a lead-in for the opening sound, and let the user check pronunciation by ear. Use when the user says "narrate this", "voice options", "audition voices", "try another voice", "use my recording", "faster", "slower", or invokes /facts-shorts:narrate.
---

# Narrate

Approved story in, `build/narration_*_lead*.wav` + `build/words_segments.json` registered in the story.

## Paths

| What | Where |
|---|---|
| Story | `<root>/<slug>/story.v<N>.json` (`<root>` = `${CLAUDE_PROJECT_DIR}/facts-channel`, `FACTS_DIR` overrides) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{validate.py,tts.py,segalign.py,setup.sh,cost.py}` (stdlib, `python3`) |
| Keys | `~/.config/facts-shorts/.env` `GEMINI_FREE_KEY=` (AI Studio key from a project without billing); falls back to `~/.config/football-stories/.env`. Never in the plugin or the story |
| Channel | `<root>/channel.json`: `voice`, `style`, `pace` |

## Inputs

| Input | Default |
|---|---|
| Voice | Always `en-in-commercial-1`. No auditions (they cost Claude tokens for nothing); only if the user explicitly asks for other voices, run `tts.py --audition <voices>` |
| Pace | 1.0 (30 s at 1.0 was right for this channel) |
| Lead | story `narration.lead` (0.5 s when the opening has a sound) |
| Own recording | none (`own:<file>`) |

## Procedure

1. **Check.** `python3 validate.py <story>`; stop on errors. If `<slug>_v<N>.mp4` exists, use `revise`. First run in a new setup: `bash setup.sh` (fonts, key).
2. **No audition.** Use `en-in-commercial-1` straight away; don't generate audition files. Only if the user explicitly asks to hear other voices: `tts.py <story> --audition <voices>` (free tier, lines 1–2; mention once that free-tier prompts may be used to improve Google products), `open` the files and ask which. Never audition on the paid key unless asked.
3. **One take.** `python3 tts.py <story> --voice gemini:<voice> --pace 1.0`. One call per request; never loop takes to pick a best one. tts.py never overwrites a take (a second take gets `_2`). HTTP 429: say so and offer to wait, or the paid key (≈₹0.65 per 30 s, only if the user says yes).
4. **Length.** Read the duration line. Over 40 s (or `length.max`): propose words to cut (don't speed up past 1.0 unless asked). Under ~27 s: mention it.
5. **Time the words.** `python3 segalign.py <story>` (uses `narration.lead`; `--lead 0.5` to set it). It prints one row per speech segment: time, then the words it assigned. Read it: each row should be a natural phrase, line breaks at the longer pauses. If a group looks shifted (a word that belongs to the next pause), edit `build/segments.json` (`line`, `i0`, `i1` per segment) and re-run with `--segments build/segments.json`. Optional, only if available without any download: `--anchors <python with faster-whisper>` lets the cached English `small.en` model pin names and English words. **Never download a Whisper model (or any model) without asking the user first.**
6. **Pronunciation by ear.** Tell the user the seconds of the risky words (names, Hindi words the voice may anglicise like "sunai", "pehle", English loan words) from the segment table, `open` the wav, and ask them to listen. If one is wrong: change that line's `tts` (respell: "Fleming" → "Flemming", or move CAPS), and make one new take (free) only after they agree.
7. **Pace changes** need no new take: `tts.py <story> --from-take build/take_<voice>.wav --pace 0.97`, then segalign again.
8. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "narrate" --slug <slug>`.
9. **Hand over.** Voice + tier (free), duration (+ lead), the segment table summary, flags, the wav path, cost lines. Write `<slug>/NEXT.md` with `/facts-shorts:video <story>` + voice/length/visual notes, and show it.

## Hard rules

- Free tier only unless the user asks; one take per request; state the cost of any paid call.
- No model downloads (Whisper multilingual or otherwise) without the user's explicit yes.
- Keys only in `~/.config/.../.env`; never print them.
- The description must carry "Narration voice is AI-generated." (story `disclosure`). No voice cloning of real people.
