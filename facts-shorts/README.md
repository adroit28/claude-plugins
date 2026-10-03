# facts-shorts

Narrated 30–40 s YouTube Shorts in Hinglish (Roman script) about the surprising story behind
everyday things: a verified story, a script that sounds like a friend telling a fun fact, a free
AI voice, and a 2D animated explainer with real public-domain photos, built with Remotion.

| Skill | What it does |
|---|---|
| `/facts-shorts:ideas` | Topic cards (hook question, twist, payoff, category, why Indian viewers care, myth to check) and a ledger, `IDEAS.md`, so a topic is never pitched or made twice. |
| `/facts-shorts:research` | Sends the legwork to the `fact-finder` agent (Haiku): opened pages, a verbatim quote and URL per claim, myths and who debunked them, Commons image candidates with licences. The session model re-checks the key claims and writes `verify.md`: verified / myth / interpretation / unverified. |
| `/facts-shorts:script` | Beats table (hook → twist → payoff, each beat leading to the next), iterated with you, then `story.v1.json`: caption `text` and spoken `tts` per line (numbers as words, pauses, CAPS emphasis). Sources stay in verify.md. |
| `/facts-shorts:narrate` | No auditions: one full take with `en-in-commercial-1`, pace 1.0, word timings from the pauses in the take (`segalign.py`). |
| `/facts-shorts:video` | Storyboard for your OK, Commons photos (downloaded only after your yes, licences logged), a 2D Remotion scene on the kit, synthesized sound effects, render, −14 LUFS, frame and loop checks. |
| `/facts-shorts:metadata` | Titles, Hinglish + English description with sources and photo credits, hashtags, pinned comment, posting slot, "Narration voice is AI-generated." |
| `/facts-shorts:revise` | Numbered feedback → the next version (story, scene snapshot, mp4), re-voicing only when the words change. |
| `/facts-shorts:make` | All of it in order, with approval stops and a fresh-session handoff prompt after the heavy steps. |
| `facts-shorts:fact-finder` (agent) | The cheap evidence collector behind research and revise. |

Every step writes a handoff prompt (`<slug>/NEXT.md`) so the next one can start in a fresh, cheaper
session, and reports the Claude cost so far (`scripts/cost.py`, list prices from the session transcript).

## Install

```
/plugin marketplace add adroit28/claude-plugins
/plugin install facts-shorts@adroit-plugins
```

Requirements: macOS, Homebrew `ffmpeg`, Node + npm (Remotion renders in headless Chrome, which it
downloads on first render), Python 3 (scripts are stdlib only), and the OFL fonts Anton and Barlow
Condensed (ExtraBold, SemiBold) in `<content>/fonts/`. `scripts/setup.sh` checks everything.

## Content folder

`$CLAUDE_PROJECT_DIR/facts-channel/` (or `FACTS_DIR`):

```
channel.json      name, tagline, avatar (outro card), voice, style prompt, pace, length, categories
IDEAS.md          topic ledger
fonts/            Anton-Regular.ttf, BarlowCondensed-ExtraBold.ttf, BarlowCondensed-SemiBold.ttf
cost_log.jsonl    one line per cost report
<slug>/           verify.md, story.vN.json, src/ (photos + sources.json), build/, anim/, <slug>_vN.mp4,
                  metadata.md, notes.md, NEXT.md
```

`channel.json` (all keys optional; these are the defaults):

```json
{"name": "", "tagline": "for more surprising stories", "avatar": "☎️",
 "voice": "gemini:en-in-commercial-1", "pace": 1.0, "length": {"min": 30, "max": 40},
 "style": "AUDIO PROFILE: ... DELIVERY: ...", "timezone": "Asia/Kolkata",
 "categories": ["money/objects", "medicine/science", "superstitions", "words/habits", "India history"]}
```

An empty `name` makes the outro say "Like & Subscribe".

## Voice

Gemini `gemini-3.8-flash-tts` on a free-tier key (`GEMINI_FREE_KEY` in `~/.config/facts-shorts/.env`;
an AI Studio key from a Google Cloud project without billing). The en-IN voices read Roman-script
Hinglish; CAPS words get emphasis, `...` and `<short pause>` give pauses. Free-tier prompts may be
used to improve Google products. `gemini-paid:<voice>` (~₹0.65 per 30 s) only when you ask;
`own:<file>` for your own recording.

## Why word timing comes from pauses

English Whisper models translate Hinglish instead of transcribing it ("It was a phone call that
said hello..."), so their word times are wrong. `segalign.py` finds the speech segments between
pauses (ffmpeg silencedetect), assigns the script's words to segments with a small dynamic
programme (phrase lengths vs segment lengths, line breaks at the longer pauses), and spreads the
words inside each segment by length. It prints the segment table and writes `build/segments.json`,
which you can fix by hand. If a Python with faster-whisper and a cached English model is around,
`--anchors` lets the English words it does catch (names, loan words) pin the groups; nothing is
ever downloaded.

## Rules built in

Verified facts only (sources in verify.md, none in the story file) · downloads only after an
explicit yes · public-domain photos and drawn graphics over generated people · one free take per
request · versions only go up · every video ends with a 3 s like & subscribe card ·
"Narration voice is AI-generated." in every description.
