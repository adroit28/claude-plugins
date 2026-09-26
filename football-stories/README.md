# football-stories

Narrated football story Shorts: a verified story, a fact-cited script, an AI (or your own)
voice, and animated cards with word-timed captions, optionally with short muted real clips in a
framed box. The sibling plugin `football-shorts` cuts whole Shorts from footage; this one uses its
search, download and contact-sheet tools only when you want clips in a story.

| Skill | What it does |
|---|---|
| `/football-stories:research` | Finds story leads (news RSS, r/soccer RSS, Wikipedia on-this-day, dated web searches), verifies each fact with two sources where possible, writes ranked story cards; after you pick one, drafts `story.v1.json` with a fact id on every line, and once you approve it writes `handoff.md`, a prompt to continue in a fresh (cheaper) session. |
| `/football-stories:narrate` | Voice options (free by default), one take, pace (default 0.93, slightly slower than Gemini's natural read), Whisper word alignment, mispronunciation flags. Also takes your own recording. |
| `/football-stories:build` | Template cards (HTML → headless Chrome), a Pillow frame loop with zooms, crossfades, whips and 3-word captions, optional muted footage clips anchored to words (logos and score bugs cropped or erased), whooshes and bass hits, loudnorm −14 LUFS, a check sheet, and a hand-over with title, description, hashtags and the AI-voice note. |
| `/football-stories:revise` | Numbered feedback → the next story version, re-rendering only what changed, with before/after frames. |
| `/football-stories:make` | All of the above in order, stopping for you to pick the story, approve facts and script, and approve the voice. |
| `football-stories:fact-finder` (agent) | The cheap worker behind `research` (and new facts in `revise`): runs discover.py and the searches, opens the sources and returns every fact with URL, publisher, date and the verbatim supporting sentence, on `sonnet`. The session model spot-checks, judges and writes. |

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

## Cost and models

- **Voice:** `free` costs nothing (Gemini free tier, or Kokoro offline); the paid key is ≈₹0.65 per Short. Rendering is all local.
- **Claude usage** is the main cost, and most of it is research. The legwork runs in `agents/fact-finder.md` on `model: sonnet`; the session model only spot-checks the evidence (re-reading one quoted sentence per core claim), ranks, and writes cards and the script.
- Change the agent's model: edit `model:` in `agents/fact-finder.md` (`haiku` is cheapest but weaker at judging independence; `opus` for hard historical stories).
- Run the whole research skill cheaper: `/model sonnet` before `/football-stories:research`, or add `model: sonnet` to `skills/research/SKILL.md`'s frontmatter. Story choice and fact judgement get weaker; the verbatim-quote rule and `validate.py` still block unsourced lines.
- Check claims directly: `@agent-football-stories:fact-finder mode: verify 1. <claim> 2. <claim>` and read `shorts/briefs/verify-*.json`.
- `build` and `revise` are mostly script time; a cheaper session model is fine for mechanical revisions (pace, card text, hits).
- **Cost after each step.** `scripts/cost.py` reads this session's Claude Code transcript (and its subagents'), prices every API message at list rates (input, output, 5-minute and 1-hour cache writes, cache reads; web searches at $10 per 1,000) and prints this step, this session and this video. Each run appends to `shorts/cost_log.jsonl`. The skills run it after cards, script, narration, build and each revision. These are list-price equivalents: on a Claude subscription the usage counts against plan limits instead. Prices live in `PRICES` in the script; `FOOTBALL_STORIES_INR_RATE` sets the rupee rate.
- **Fresh session after the script.** On a long run, the biggest cost is re-reading the conversation: research leaves evidence and source pages in context that narrate and build never need. When the script is approved, research writes `shorts/<slug>/handoff.md` and shows a prompt; paste it into a new session and `make` picks up at the voice step.

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
$PY $S/clips.py shorts/x/story.v1.json [--plan]   # only when the story has clips; after every compose
$PY $S/finish.py shorts/x/story.v1.json
$PY $S/check.py shorts/x/x_v1.mp4 --timeline shorts/x/build/timeline_v1.json
$PY $S/check.py shorts/x/x_v2.mp4 --ref shorts/x/x_v1.mp4 --at 5 12
python3 $S/cost.py --step build --slug x          # Claude cost: this step / session / video
```

Reference build: `shorts/satpayev-rebuild/` reproduces `satpayev-fifa-wait_v2.mp4` (same cards
pixel for pixel, identical picture track, same length and loudness).

## Rules the skills keep

- Every narrated claim cites a fact with a source; `validate.py` blocks uncited lines.
- One paid generation per request unless you ask for more.
- "Narration voice is AI-generated." goes in the description. No realistic AI images of real people.
- Photos and music carry a rights class; doubtful or unknown ones are refused unless you accept them.
- No video downloads without your explicit yes, asked again for every video; clips are muted and recorded with their source and your yes (`rights.accepted`). Uploads stay manual; nothing claims to reduce Content ID risk (it matches the footage, not the logo).

## Layout

```
.claude-plugin/plugin.json
agents/fact-finder.md
scripts/{setup.sh,common.py,discover.py,validate.py,tts.py,align.py,cards.py,compose.py,clips.py,finish.py,check.py,cost.py}
skills/research/SKILL.md + references/{formats,story-card,sources}.md
skills/narrate/SKILL.md  + references/voices.md
skills/build/SKILL.md    + references/{story-format,templates,channel-style}.md, template-demo.json
skills/revise/SKILL.md
skills/make/SKILL.md
```
