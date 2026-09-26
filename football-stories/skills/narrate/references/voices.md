# Voice options

Checked on 2026-09-26. Re-check prices and tiers when a quote matters; Google changes them.

| `--voice` | Cost | Accent | Status |
|---|---|---|---|
| `free` | free | depends | Gemini on `GEMINI_FREE_KEY` with `en-in-tutor-1` if that key exists, else Kokoro `bm_george`. |
| `gemini:<voice>` | free | en-IN available | **Verified:** `gemini-3.8-flash-tts` is "Free of charge" on the Standard free tier (ai.google.dev/gemini-api/docs/pricing). Free-tier content is used to improve Google products. **Rate limits are not published**; they are per project and show on AI Studio → Rate limits; over the limit = HTTP 429 RESOURCE_EXHAUSTED. **Verified 2026-09-26:** Extended Library `en-in-*` voices work on a free key: one free call with `en-in-tutor-1` returned 7.1 s of 24 kHz mono audio of the Satpayev hook line (228 audio tokens, no charge). The response carried no rate-limit headers, so the limits still have to be read in AI Studio. |
| `gemini-paid:<voice>` | ~$0.008 (₹0.65) per 27 s | en-IN | Verified: $9 per 1M audio output tokens until 31 Dec 2026, $18 from 1 Jan 2027; 25 tokens per second of audio (27 s = 862 tokens in the Satpayev take). Same voices as free, no rate cap. **One take per request** unless the user asks for more. |
| `kokoro:<voice>` | free, offline | US/UK English only | Verified installed: `kokoro-onnx` 0.4.7 on the venv's Python 3.14 (the torch `kokoro` package does not build: spacy/thinc). Model `kokoro-v1.0.onnx` + `voices-v1.0.bin` (~350 MB) in `~/.cache/football-stories/kokoro/` via `setup.sh --kokoro`. English voices: `bm_george bm_lewis bm_daniel bm_fable bf_emma bf_alice bf_isabella bf_lily` (British, read with `en-gb`), `am_michael am_adam am_eric am_liam am_onyx am_echo af_heart af_bella af_nicole af_sarah…` (American, `en-us`). The file also has Hindi voices `hm_omega hm_psi hf_alpha hf_beta`: untested on English text (tts.py would phonemise them as en-us). **Reads slower than Gemini**: the 78-word Satpayev script took 34 s raw vs 27 s, so at the default pace 0.93 it is 37 s. Use `--pace 1.0` and a shorter script. No style prompt; CAPS emphasis is flattened. Misheard in test: "Dastan" (as "Dustin"). |
| `say:<voice>` | free | `Rishi`, `Aman` are en_IN | macOS built-in. Robotic: last resort, or for timing drafts. 36.6 s raw for the Satpayev script. |
| `own:<file>` | free | yours | Any ffmpeg-readable file (m4a voice notes from the phone work) → 24 kHz mono wav. Pace defaults to **1.0** (your own delivery is kept). The strongest candidate on paper (research §07): no disclosure needed, names right. |
| Chirp 3 HD (Cloud TTS) | not built | en-IN | Verified from docs: en-IN supported; SSML `<phoneme>`, IPA custom pronunciations and `speaking_rate` are **Preview**. Needs the Cloud TTS API + billing. Free monthly character allowance not verified (pricing page did not load). Add as an engine if Gemini names stay wrong. |
| ElevenLabs v3, OpenAI gpt-4o-mini-tts | not built | — | Later, for the blind test (research §07). |

## Gemini en-IN voices

`tts.py --list` (metadata call, no charge; cached in `~/.cache/football-stories/voices-en-IN.json`).
120 voices: 10 personas × 12 — advisor, assistant, commercial, concierge, csagent, podcaster,
storyteller, techagent, training, tutor. Each has gender, pitch and a description. Useful
starting points for story Shorts: `en-in-tutor-1` (male, low, "energetic, colorful, and fast";
the Satpayev voice), `en-in-storyteller-*`, `en-in-podcaster-*`, `en-in-commercial-1`
(male, 23, enthusiastic). Filter: `--persona storyteller --gender female`.

Accent comes from the voice choice, not the `style` prompt (Gemini docs).

## Pace

`atempo` after TTS, pitch kept, no new API call: `--from-take build/take_<voice>.wav --pace 0.90`.
Default 0.93 (the user wants it slightly slower than Gemini's natural read); 1.0 for own
recordings. When narration + 0.75 s tail > 30 s, tts.py says how many words to cut. Cut
words rather than speed the voice up.

## Pronunciation

1. After align.py, read the `CHECK` lines (script word vs what Whisper heard, e.g. Satpayev → "Satayev").
2. Listen to that second. If it is wrong, add a respelling to `shorts/lexicon.json`:
   `{"Satpayev": {"respell": "Sat-pie-ev", "ipa": "", "verified_by_ear": false}}`.
   tts.py uses it on every line without an explicit `tts` field (or put the respelling in `tts`).
3. Take again (one take), re-align, listen. Set `verified_by_ear: true` once the user confirms.
Numbers said as words ("eighteen") never match Whisper's digits; those notes are harmless.
