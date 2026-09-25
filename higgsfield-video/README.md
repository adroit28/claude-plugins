# higgsfield-video

Turns a theme and an idea into a ready-to-paste multi-shot brief for Kling 3.0
on Higgsfield. Fact-checks real-world claims with sources, writes per-shot
prompts inside the Custom multi-shot limits, assigns Elements and voice tags
per shot, validates the brief, and gives a pre-Generate checklist.

## Install

```
/plugin marketplace add adroit28/claude-plugins
/plugin install higgsfield-video@adroit-plugins
```

## Use

```
/higgsfield-video:multishot theme: toddler footballers arguing; idea: who is the GOAT, ronaldo vs messi, 15 s 9:16
/higgsfield-video:multishot --no-facts theme: kitchen; idea: two toddlers fight over the last biscuit
```

The skill writes `YYYY-MM-DD-<slug>.md` into `~/Documents/ai-learning/ai videos/briefs/`
(override with `HIGGSFIELD_BRIEFS_DIR`) and prints the shot table, fact table
and checklist. Paste each shot into its card on Higgsfield.

## Validate a brief by hand

```
python3 skills/multishot/scripts/shotcheck.py "<brief.md>"
```

## Generation (later)

Higgsfield has no API key. Generation goes through its hosted MCP server
(`claude mcp add higgsfield https://mcp.higgsfield.ai/mcp`, OAuth with the
normal account) or the Higgsfield CLI, which Higgsfield recommends for Claude
Code. `scripts/generate.py --dry-run <brief.md>` shows the payload the skill
would hand to either; submission is not wired yet.

## Layout

```
.claude-plugin/plugin.json
skills/multishot/SKILL.md
skills/multishot/references/{kling-rules,prompt-grammar,characters,fact-check,brief-template}.md
skills/multishot/scripts/{shotcheck,generate}.py
```

Character registry lives in `references/characters.md`. Add new Elements there
with the exact Higgsfield Element name and a fixed voice tag.
