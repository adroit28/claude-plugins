---
name: script
description: Write the Hinglish (Roman script) narration for a facts-channel Short from its verify.md - beats as a table (hook question, twist, payoff, each beat leading to the next, aim 40-45 s, hard max 60 s), iterate with the user, then write story.v1.json with a caption text and a spoken tts per line (numbers as words, pauses, CAPS emphasis) and no source citations, validate it, and hand off to narrate. Use when the user says "write the script", "draft the Hinglish script", "make the beats", "change line 3", pastes a facts-shorts script handoff, or invokes /facts-shorts:script.
---

# Script

`verify.md` in, approved `story.v1.json` out.

## Paths

| What | Where |
|---|---|
| Short folder | `<root>/<slug>/` with `verify.md` (`<root>` = `${CLAUDE_PROJECT_DIR}/facts-channel`, `FACTS_DIR` overrides) |
| Style guide | `${CLAUDE_PLUGIN_ROOT}/skills/script/references/style.md` (read it every time) |
| Channel | `<root>/channel.json` (length, style prompt, pace) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{validate.py,cost.py}` |
| Example | `<root>/hello-short/story.v1.json` (schema differs: football-story/1.0; copy its lines, not its schema) |

`<story>` is the FULL path to `story.v<N>.json` (a file, never the folder). Pass that file to every script.

## Inputs

| Input | Default |
|---|---|
| Slug + handoff notes | most recent `picked` topic |
| Length | channel.json (aim 40–45 s, hard max 60 s) |

## Procedure

1. **Read** style.md, `verify.md`, channel.json. **Pick the mode:** if the topic is a habit or belief viewers practise and it is wrong or harmful, use Myth-buster mode from style.md (accusation hook, stakes beat, open loop, fix, payoff that sends the hand back to the habit) and say so in one line; otherwise the normal explainer shape. If the user says to skip verification, still never state anything verify.md marks unverified or invents; drama is framing, not new claims. Only VERIFIED claims become statements; myths only as myths; interpretations only hedged ("shayad isliye") or cut.
2. **Beats table → iterate.** Show:
   `| # | Beat | Hinglish line | Leads into next because | Claim (verify.md #) |`
   6–9 lines, aim 120–135 words (40–45 s), hard max 60 s (~175 words) (`words / 2.95` ≈ seconds at pace 1.0). Line 1 = the hook question (accusation in Myth-buster mode); the twist by ~8 s; the last line pays off and echoes the hook. Under the table: estimated length, any claim you softened, and 1–2 alternative hooks. Then ask for edits. Apply the user's edits literally; when they cut a beat, check the next line still follows. Keep iterating until they approve. Self-check before every draft: no gimmick phrases, no beat that repeats a point, no paraphrase in quote marks, no word that confuses in context (e.g. "bell" right after Alexander Graham Bell: "ghanti").
   Add a column `needs from earlier` to the table: a beat may only refer to things already said (Bell's Ahoy must be introduced before the payoff).
   Re-read the note under each claim in verify.md (disputed dates, 'only one opened source', 'say reportedly'); the line must respect it.
3. **Write `story.v1.json`** once approved:
   ```json
   {"schema": "facts-story/1.0", "id": "facts-<slug>", "slug": "<slug>", "version": 1, "format": "explainer-2d",
    "status": "script", "title": "<working title>", "category": "<category>",
    "narration": {"style": "<channel.json style unless the user changed it>", "pace": 1.0, "lead": 0.5,
      "lines": [{"id": "L1", "no_claim": true, "text": "<caption>", "tts": "<spoken, only if it differs>"}]},
    "disclosure": "Narration voice is AI-generated.", "length": {"max": 60}}
   ```
   - Every line has `"no_claim": true` (claims are traced in verify.md, not cited here). No URLs, no facts list.
   - `text` = caption: digits OK ("1877", "10-20 feet"), quote marks only around exact words.
   - `tts` whenever the spoken form differs: numbers and years as words ("eighteen seventy-seven", "das-bees feet"), `...` or `<short pause>` before a reveal, CAPS on one surprising word. Lines with digits in `text` must have `tts` (validate.py checks).
   - `lead`: 0.5 s of silence before the voice when the opening has a sound (ring, click, whoosh); 0 otherwise.
4. `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/validate.py <slug>/story.v1.json`; fix every ERROR, judge each warn.
5. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "script" --slug <slug>`.
6. **Hand over.** Write `<slug>/NEXT.md`, show it in a code block, and suggest a fresh session:
   ```
   /facts-shorts:narrate <slug>/story.v1.json
   Script approved on <date>. Voice: en-in-commercial-1, no audition, pace 1.0. Lead: <0.5|0> s (<opening sound>).
   Then /facts-shorts:video. Visual ideas: <per line, 1 short phrase>. Report the cost after each step.
   ```

## Hard rules

- No claim in the script that verify.md doesn't mark VERIFIED (or present as myth/hedged interpretation).
- Roman-script Hinglish only; mostly English words, light Hindi glue.
- No source citations in the story file (the user's rule); sources stay in verify.md.
- Versions only go up: after narration exists, script changes go through `revise` (story.v2.json).
