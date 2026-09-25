---
name: multishot
description: Write a production-ready multi-shot video brief for Kling 3.0 on Higgsfield from a theme and an idea. Use when the user wants a short video script or prompt for Higgsfield, Kling, a multi-shot clip, a dialogue between recurring characters (the toddler footballer set, or any Elements they have), or asks to fact-check the claims a script makes. Produces per-shot prompts that fit the Custom multi-shot limits, per-shot Element and voice assignments, a verified fact table with sources, a settings checklist, and a single-box Auto fallback. Does not call the Higgsfield API yet; that is scaffolded in scripts/ for later.
---

# Higgsfield multi-shot brief

Turn a theme plus an idea into something the user can paste into Higgsfield's
Kling 3.0 Custom multi-shot panel and generate once, without burning credits on
avoidable mistakes. Every rule in `references/kling-rules.md` was learned from a
failed or wasted generation, so treat that file as the spec, not as advice.

The reader of the brief is the user at the Higgsfield panel, credits in hand.
They want to copy, paste, tick a checklist and press Generate. Keep the brief
tight and copyable. Explanations go in the conversation, not in the brief.

## Paths

| What | Where |
|---|---|
| Rules and limits for the Higgsfield UI | `references/kling-rules.md` next to this file |
| Prompt grammar and shot templates | `references/prompt-grammar.md` |
| Character registry (Elements, descriptions, voice tags, image paths) | `references/characters.md` |
| Fact-check procedure | `references/fact-check.md` |
| Brief template | `references/brief-template.md` |
| Shot validator | `${CLAUDE_PLUGIN_ROOT}/scripts/shotcheck.py` |
| API scaffold (not wired yet) | `${CLAUDE_PLUGIN_ROOT}/scripts/generate.py` |
| Briefs (output) | `$HIGGSFIELD_BRIEFS_DIR` if set, else `~/Documents/ai-learning/ai videos/briefs/` |
| Generation (future) | Higgsfield MCP (`https://mcp.higgsfield.ai/mcp`, OAuth) or the Higgsfield CLI token; no API key exists. Token, if any, lives in `~/.config/higgsfield-video/.env` |

Briefs are user content and live outside the plugin. Create the briefs dir if
missing. Never write user content or keys inside the plugin directory, and
never print the contents of the `.env` file.

## Inputs

Parse these from the user's message. Ask only when a missing answer would
change the shots materially; otherwise pick the default and say so in the
brief's "Assumptions" line.

| Input | Default |
|---|---|
| Theme and idea | required |
| Characters | infer from the idea; must exist in `references/characters.md` or the user names new Elements |
| Total duration | 15 s |
| Aspect ratio | 9:16 |
| Fact-check | on whenever the script states a real-world fact (a number, a record, a date, a quote, a ranking); off for pure fiction. The user can force with `--facts` or `--no-facts` |
| Start frame | a still exists for the opening composition, or none |
| Tone | comedic banter unless told otherwise |

## Procedure

1. **Read the rules.** Load `references/kling-rules.md` and
   `references/prompt-grammar.md` before writing a word of prompt.
2. **Pin the characters.** Look each one up in `references/characters.md`.
   Use the Element name exactly as registered (lowercase, e.g. `ronaldo`,
   `messi`, `mbappe`). Reuse the registered voice tag verbatim. If a character
   is not registered, draft a registry entry (name, description, voice tag,
   image path) and show it to the user before continuing.
3. **Fact-check first, write second.** If fact-check is on, follow
   `references/fact-check.md` and build the fact table before drafting any
   dialogue. A line of dialogue may only assert what the table verifies.
   Anything unverified either becomes an opinion in the character's mouth
   ("I'm the best!") or is dropped. Do not write the joke and check later.
4. **Structure the beats.** Decide the exchanges. For a debate or banter
   piece every claim needs a direct answer in the next beat, so the audience
   never hears a number that nobody replies to. Keep rounds balanced unless
   the user wants a winner.
5. **Cut into shots.** Apply the limits: 3 s minimum per shot, at most 5
   shots, total equals the requested duration. Budget about 1.5 s per short
   spoken line plus 1 s per gesture or camera move. Two speakers may share a
   shot only when both lines are short; give that shot the extra seconds.
   Prefer shot / reverse-shot for anything longer.
6. **Write each shot** with the grammar file: scene line only in shot 1,
   one camera instruction per shot, action, then bracketed speaker tags with
   the registered voice wording, `Immediately,` before any reply. One Element
   chip per character per shot, at first mention; plain names afterwards and
   in speaker tags. Tag only the characters who appear in that shot.
7. **Validate.** Write the shots into the brief and run:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/shotcheck.py" "<brief path>"
   ```

   It checks per-shot stored length (text plus 50 per chip against the
   budget), the 3 s minimum, the total duration, the shot count, words per
   second, that no `@mbappe`-style chip appears for a character not in the
   shot's Element list, that voice tags are identical across shots, and that
   no shot asks for counted fingers. Fix every failure before showing the
   brief. Warnings go into the brief's "Watch for" section.
8. **Write the brief** from `references/brief-template.md` to the briefs
   dir as `YYYY-MM-DD-<slug>.md`, and show the shot table plus the checklist
   in the conversation. If a start-frame still does not exist yet, include a
   still prompt the user can run through their image pipeline.
9. **Offer the single-box Auto fallback** at the end of the brief, generated
   from the same shots, for when Custom misbehaves.

## Hard rules

- **Never invent a statistic.** Numbers, records, trophies, dates and rankings
  come from sources fetched this run, with URLs in the brief. Your memory is a
  hypothesis, not a source.
- **Never hand-count on screen.** No "holds up four fingers". Video models
  miscount. Put the number in the line and give the hands something else.
- **Never describe a voice two different ways.** The voice tag is copied from
  the registry and repeated identically in every shot that character speaks in.
  Changing the wording gives the model permission to change the voice.
- **Never split one script across generations.** One generation, one audio
  track, one voice per character. Separate clips pick separate voices.
- **Never send the user to generate without the checklist.** Start frame
  loaded, End frame empty, Multi-shot on and Custom, Audio on (set in Auto
  before switching), 720p for the first run, every card scrolled to its last
  line, total on the Generate button matching the duration.
- **One shot, one camera move.** Two moves get neither.
- **No speech in a shared frame.** Two or more Elements in one shot means
  "mouth closed" on each and "No speech in this shot." Every spoken line is
  a solo shot. Shared frames are for the silent opener and the closing
  freeze only.

## Output in the conversation

Lead with the shot table (shot, seconds, Elements, first words). Then the
fact table if any. Then the checklist. Then the path of the saved brief. Keep
prose to what the user must decide. The full prompt text lives in the brief
and in fenced blocks so it can be copied card by card.
