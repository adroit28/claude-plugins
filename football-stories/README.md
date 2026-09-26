# football-stories

Narrated football story Shorts with no footage: a verified story, a fact-cited script, an AI
(or your own) voice, and animated cards with word-timed captions. The sibling plugin
`football-shorts` cuts footage from video links; this one never needs footage.

| Skill | What it does |
|---|---|
| `/football-stories:research` | Finds story leads (news RSS, r/soccer RSS, Wikipedia on-this-day, dated web searches), verifies each fact with two sources where possible, writes ranked story cards; after you pick one, drafts `story.v1.json` with a fact id on every line. |
| `/football-stories:narrate` | Voice options (free by default), one take, pace (default 0.93, slightly slower than Gemini's natural read), Whisper word alignment, mispronunciation flags. Also takes your own recording. |
| `/football-stories:build` | Template cards (HTML → headless Chrome), a Pillow frame loop with zooms, crossfades, whips and 3-word captions, whooshes and bass hits, loudnorm −14 LUFS, a check sheet, and a hand-over with title, description, hashtags and the AI-voice note. |
| `/football-stories:revise` | Numbered feedback → the next story version, re-rendering only what changed, with before/after frames. |
| `/football-stories:make` | All of the above in order, stopping for you to pick the story, approve facts and script, and approve the voice. |

## Install

```
/plugin marketplace add adroit28/claude-plugins
/plugin install football-stories@adroit-plugins
```

Requirements: macOS, Homebrew `ffmpeg`, Google Chrome, Python 3, the OFL fonts Anton,
Barlow Condensed (SemiBold, ExtraBold) and Montserrat in `shorts/fonts/`.
`scripts/setup.sh` checks everything and creates `shorts/.venv` with Pillow and faster-whisper;
`setup.sh --kokoro` adds the offline Kokoro voice (~350 MB model, once).

## Voices

| `--voice` | Cost | Notes |
|---|---|---|
| `free` (default) | free | Gemini `gemini-3.8-flash-tts` on a free-tier key with `en-in-tutor-1` if `GEMINI_FREE_KEY` is set, otherwise Kokoro |
| `gemini:<voice>` | free | 120 Indian-English voices (`tts.py --list`). Free-tier content may be used to improve Google products; rate limits per project in AI Studio |
| `gemini-paid:<voice>` | ≈₹0.65 per 30 s | same voices, no rate cap; one take per request |
| `kokoro:<voice>` | free, offline | US/UK English; reads slower, so use pace 1.0 |
| `own:<file.m4a>` | free | your recording; pace 1.0 by default |
| `say:Rishi` | free | macOS; robotic, last resort |

Keys live in `~/.config/football-stories/.env`:

```
GEMINI_FREE_KEY=...   # AI Studio key from a Google Cloud project WITHOUT billing
GEMINI_PAID_KEY=...   # optional; falls back to ~/.config/gemini-image/.env
```

Details and verification dates: `skills/narrate/references/voices.md`.

## Use

```
/football-stories:make focus: anniversaries this week
/football-stories:research
/football-stories:research card 2
/football-stories:narrate shorts/keane-haaland/story.v1.json voice: gemini:en-in-storyteller-11
/football-stories:narrate use my recording ~/Downloads/voice-note.m4a
/football-stories:build
/football-stories:revise 1. slower 2. the timeline card says 1997 twice 3. hit on "faking"
```

Output lives in your project: `shorts/briefs/` (leads and story cards), `shorts/<slug>/`
per Short (`story.vN.json`, `build/`, `graphics/vN/`, `<slug>_vN.mp4`, `notes.md`),
`shorts/lexicon.json` (name respellings). Set `FOOTBALL_SHORTS_DIR` to move `shorts/`.

## Scripts by hand

```
PY=shorts/.venv/bin/python; S=.claude/skills/football-stories/scripts
python3 $S/discover.py --out shorts/briefs                 # leads
python3 $S/discover.py --commons "Cole Palmer"             # CC photos + rights guess
python3 $S/validate.py shorts/x/story.v1.json [--stage build]
python3 $S/tts.py --list --persona storyteller
python3 $S/tts.py shorts/x/story.v1.json --voice free
python3 $S/tts.py shorts/x/story.v1.json --from-take build/take_en-in-tutor-1.wav --pace 0.90
$PY $S/align.py shorts/x/story.v1.json
$PY $S/cards.py shorts/x/story.v1.json          # or --demo /tmp/fs-demo for every template
$PY $S/compose.py shorts/x/story.v1.json
$PY $S/finish.py shorts/x/story.v1.json
$PY $S/check.py shorts/x/x_v1.mp4 --timeline shorts/x/build/timeline_v1.json
$PY $S/check.py shorts/x/x_v2.mp4 --ref shorts/x/x_v1.mp4 --at 5 12
```

Reference build: `shorts/satpayev-rebuild/` reproduces `satpayev-fifa-wait_v2.mp4` (same cards
pixel for pixel, identical picture track, same length and loudness).

## Rules the skills keep

- Every narrated claim cites a fact with a source; `validate.py` blocks uncited lines.
- One paid generation per request unless you ask for more.
- "Narration voice is AI-generated." goes in the description. No realistic AI images of real people.
- Photos and music carry a rights class; doubtful or unknown ones are refused unless you accept them.
- No video downloads without your explicit yes; uploads stay manual; nothing claims to reduce Content ID risk.

## Layout

```
.claude-plugin/plugin.json
scripts/{setup.sh,common.py,discover.py,validate.py,tts.py,align.py,cards.py,compose.py,finish.py,check.py}
skills/research/SKILL.md + references/{formats,story-card,sources}.md
skills/narrate/SKILL.md  + references/voices.md
skills/build/SKILL.md    + references/{story-format,templates,channel-style}.md, template-demo.json
skills/revise/SKILL.md
skills/make/SKILL.md
```
