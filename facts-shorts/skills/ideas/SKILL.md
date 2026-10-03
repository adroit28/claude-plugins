---
name: ideas
description: Suggest topic cards for a "surprising story behind everyday things" Hinglish Shorts channel - title, hook question, twist, payoff, category, why Indian viewers would care, and any famous myth - while keeping a ledger (IDEAS.md) so no topic is ever pitched or made twice. Use when the user says "facts short ideas", "what should the next facts short be", "topic ideas", "pick a topic", "add this to the ideas list", or invokes /facts-shorts:ideas.
---

# Topic ideas

Ledger in, 5–8 topic cards out; the user picks one, it becomes `picked` with a slug, and research
starts (fresh session or here).

## Paths

| What | Where |
|---|---|
| Content root | `${CLAUDE_PROJECT_DIR}/facts-channel/` (`FACTS_DIR` overrides) |
| Ledger | `<root>/IDEAS.md` via `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/ideas.py` |
| Channel | `<root>/channel.json` (promise, categories, length) |
| Style | `${CLAUDE_PLUGIN_ROOT}/skills/script/references/style.md` |
| Cost | `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py` |

## Inputs

| Input | Default |
|---|---|
| Category or theme (`category: superstitions`, "something about money") | none: balance the categories |
| Count | 6 cards |
| A topic the user already has | none |

## Procedure

1. **Read the ledger and balance.** `python3 ideas.py taken` and `python3 ideas.py coverage`. Never suggest anything in the ledger (any status, including rejected), including near-duplicates (same object, same origin story). During the 5-Short test, favour categories with nothing made or picked.
2. **Draft cards from what you know, mark them unverified.** Ideas are leads, not facts. A card's twist is what you *expect* research to confirm; write "to verify" on any specific year, name or number. Don't run web searches here unless the user asks: research does that on a cheaper model.
3. **Card format** (one block per card, best first):
   ```
   ### 3. Why lemon and chillies hang at shop doors · superstitions
   Hook (L1): Dukaan ke bahar nimbu-mirchi kyun latakte hain?
   Twist: <the surprising turn, to verify>
   Payoff: <last line idea>
   Why India cares: <seen daily, a festival, money, school memory...>
   Visuals: <public-domain photo / emoji / diagram ideas>
   Myth to check: <popular false version, if any>
   Risk: <thin sources, sensitive (religion, caste, politics), hard to show>
   ```
   Good topics: something almost every Indian has seen or said; one clear twist; a payoff that fits in one line; checkable in encyclopaedias, museums, archives or primary sources. Skip: topics needing medical or legal advice, active political disputes, anything mocking a faith or community.
4. **Record.** Add every suggested card as `pitched` (`ideas.py add "<title>" --category <c> --hook "<L1>"`) so it isn't suggested twice. When the user picks one: choose a short kebab-case slug, check `<root>/<slug>/` doesn't exist, `ideas.py set "<title>" --status picked --slug <slug>`, and `mkdir <root>/<slug>`. Cards the user dislikes: `--status rejected` with their reason as `--note`.
5. **Cost.** From the project root: `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/cost.py --step "ideas" [--slug <slug>]`.
6. **Hand over.** The picked card, the cost lines, and this prompt in a code block (also written to `<root>/<slug>/NEXT.md`), telling the user a fresh session is cheaper:
   ```
   /facts-shorts:research <slug>
   Topic: <title> (<category>). Hook idea: <L1>. Expected twist: <twist> (unverified).
   Questions to answer: <3-6 specific questions: origin, first record, who/when, why it spread, the myth>.
   Notes: <what the user said about the angle>. Report the cost after the step.
   ```

## Hard rules

- No topic twice: the ledger is checked before every suggestion and updated after it.
- Cards are pitches: no specific claim is presented as fact before research verifies it.
- No web research or downloads in this skill unless the user asks.
