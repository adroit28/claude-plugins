---
name: research
description: Verify the facts for a picked facts-channel topic on a cheap Haiku subagent (fact-finder: opened pages, verbatim quote + URL per claim, myths and who debunked them, Commons image candidates with licences), then judge what is verified, what is a myth and what is only interpretation, and write verify.md in the Short's folder with a handoff prompt for the script step. Use when the user says "research this topic", "verify the facts for", "is this true", "check these claims", pastes a facts-shorts research handoff, or invokes /facts-shorts:research.
---

# Research a topic

Topic in, `verify.md` out. The subagent collects; the session model judges. The script step reads
only `verify.md`, never the raw evidence.

## Paths

| What | Where |
|---|---|
| Short folder | `<root>/<slug>/` (`<root>` = `${CLAUDE_PROJECT_DIR}/facts-channel`, `FACTS_DIR` overrides) |
| Evidence (agent) | `<slug>/evidence.{json,md}` (sweep), `<slug>/verify-claims.json` (verify) |
| Output | `<slug>/verify.md` |
| Agent | `facts-shorts:fact-finder` (`${CLAUDE_PLUGIN_ROOT}/agents/fact-finder.md`, `model: haiku`) |
| Scripts | `${CLAUDE_PLUGIN_ROOT}/scripts/{commons.py,ideas.py,cost.py}` |
| Example | `<root>/hello-short/verify.md` (the format to copy) |

## Inputs

| Input | Default |
|---|---|
| Slug (and the handoff's topic, twist, questions) | the most recent `picked` row in `ideas.py list` |
| Extra claims to check | none |

## Procedure

1. **Timestamp.** `TZ=Asia/Kolkata date`. Put "Read on <date>" in the verify.md title.
2. **Delegate the sweep.** Resolve absolute paths. Agent tool, `subagent_type: facts-shorts:fact-finder`, `run_in_background: false`:
   ```
   mode: sweep
   Topic: <title>. Angle: <expected twist / hook>. Research time: <IST>.
   Questions: <numbered, from the handoff or written now: origin, first record, who/when/where, why it spread, the popular myth, an India link>.
   Fact budget: 8-14. Output dir: <abs>/<slug>   commons.py: <abs>/scripts/commons.py
   Write evidence.json/.md there and return the short report.
   ```
   If the agent fails twice or the tool is unavailable, do the same legwork inline (same rules: only opened pages count).
3. **Spot-check.** Read `evidence.md`. Re-open (WebFetch) the source of every claim the script is likely to use: the hook fact, the twist, every year/number/name. Confirm the quote is on the page and says what the claim says. A wrong quote: fix or drop it; more than one wrong: send the agent back (`SendMessage`) for those. Gaps: a second `mode: verify` call with numbered claims.
4. **Judge.** For each claim decide:
   - **VERIFIED**: two independent opened sources, or one strong primary (museum, archive, central bank, the original document).
   - **MYTH**: opened sources say it's false. Note how widespread it is: a famous myth can be the hook ("log kehte hain... par sach ye hai").
   - **INTERPRETATION**: someone's argument for *why*; usable only as "shayad" / attributed, or cut.
   - **CONFLICT**: sources disagree (often years); use the safer wording ("1880s tak") or the attested date.
   - **UNVERIFIED**: seen only in search snippets, blocked pages, weak blogs: do not use.
5. **Write `verify.md`** (copy the hello-short format): a header saying which pages could not be opened; one section per claim (`## N. <claim>: VERDICT`) with the bullet quotes (publisher, date, verbatim quote) and a one-line note on wording; "Popular myths worth a hook"; "Do not use"; and a compact table `| # | verdict | best source | note |`. Add an **Images** section with the Commons candidates (title, licence, page) and what each would show; flag misleading matches. Sources live here and nowhere in the story file.
6. **Show the user** the compact table, the myths, and the story spine you now believe (hook → twist → payoff, one line each) with anything that changed from the idea card. Ask whether to go to the script.
7. **Cost.** `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "research" --slug <slug>`.
8. **Hand over.** Write `<slug>/NEXT.md` and show it in a code block; say a fresh session is cheaper (research leaves a large context):
   ```
   /facts-shorts:script <slug>
   verify.md is done (<date>): use only VERIFIED claims; myths only as myths. Spine: <hook> → <twist> → <payoff>.
   Notes: <what the user liked or wants avoided>. Report the cost after the step.
   ```

## Hard rules

- Never fabricate a fact, quote, URL, date or licence. Unread = unverified.
- The agent collects; you judge. Every claim the script will use is re-checked by you on its page.
- Explain in your own words; quotes in verify.md are evidence, not script lines.
- No downloads here (Commons search is metadata only). Images are downloaded in the video step after the user's yes.
- Religious/cultural customs: record beliefs as beliefs, attributed.
