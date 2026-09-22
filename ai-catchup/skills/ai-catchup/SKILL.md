---
name: catchup
description: Keep up with what is new in Claude, Claude Code, OpenAI and Gemini. Use when the user wants to know what came out recently, asks "what's new in Claude Code", wants a concept or feature explained (a new flag, API, model, agent pattern), or wants to log an AI learning. Four modes - discover recent changes when no topic is given, explain one named topic, answer a follow-up question about a topic already covered, or run unattended with --auto and pick one topic itself for a scheduled daily email - and all write to one markdown note per topic to a personal notes folder outside the skill and record it in that folder's INDEX.md so nothing is surfaced twice.
---

# AI catch-up

Find what changed recently across Claude, Claude Code, OpenAI and Gemini, explain
one thing at a time properly, and keep a note per topic so the learning sticks.

The reader is the user, who is keeping up for their own understanding. They use
Claude Code daily, so they are comfortable with tools in general, but treat
them as new to the *specific* mechanism a note explains — most of these
topics really are things nobody has explained to them before. Write so
someone with very little background in that one thing can follow every
sentence: define a term the first time it appears, reach for a concrete
analogy before the mechanics, and never assume the reader already knows why
something exists. Not a beginner's guide to computing, and not a marketing
audience either — no hype, no padding, just nothing left unexplained.

## Paths

| What | Where |
|---|---|
| Notes directory | `$AI_CATCHUP_NOTES_DIR` if set, else `~/Documents/ai-learning/personal projects/ai-learnings/` |
| Notes, one per topic | `<notes dir>/YYYY-MM-DD-<slug>.md` |
| Ledger and index | `<notes dir>/INDEX.md` |
| Source list | `references/sources.md` next to this file |
| Note template | `references/note-template.md` next to this file |
| Runner, mailer, authorize, schedule installer | `${CLAUDE_PLUGIN_ROOT}/scripts/` |
| Mailer venv, OAuth client, token, recipient, `runs.csv`, `logs/` | `~/.config/ai-catchup/` |

Notes are personal and live outside this skill directory, so the skill can be
shared or packaged as a plugin without them. Resolve the notes dir first thing
and create it, with an empty `INDEX.md` from the header below, if missing.
Never write user content inside the skill directory.

```
# AI catch-up ledger

| date | slug | vendor | status | what | note |
|---|---|---|---|---|---|
```

## Hard rules

- **Never explain from memory.** Your training data is stale for this task by
  definition. Every claim in a note comes from something you fetched this run,
  and every note ends with the URLs you used. If you cannot verify something,
  put it under "Unverified" in the note rather than dropping or guessing it.
- **Sources for facts, your own words for the explanation.** Verification
  says what is true; it does not say how to teach it. Do not stitch notes
  together out of quotations. Read the sources, understand the mechanism,
  then explain it the way you would to a smart friend who has never touched
  this specific feature before: plain sentences, an analogy or mental model
  before the mechanics, a comparison to something the user already uses, a
  "the gist is" line before the detail. Name the problem the thing solves
  before naming the thing, since a solution means nothing without the gap it
  closes. Quote a source only when the exact wording matters, such as a
  command, an error message, a limit, or a vendor claim you want to
  attribute rather than endorse. Draw on your general understanding of how
  these systems work to make the new thing click; just do not use it to
  assert facts about the new thing.
- **No unexplained jargon.** The first time a note uses a term the reader
  would not already know — a protocol name, an internal component, a
  pattern's name — say what it is in the same sentence or the one after.
  A reader should never have to already know what MCP, a token, a sandbox,
  or a schema is to follow the explanation of something built on top of it.
- **Official first, community second.** Docs, changelogs and vendor blogs
  establish what a thing is. Hacker News, Reddit, Simon Willison and similar
  establish why people care and where it breaks. Label which is which.
- **Dates on everything.** Run `date +%F` at the start. A candidate is "new"
  only if it was announced or changed inside the window. Quote the source date.
- **One note per topic.** Do not bundle five things into one file. If a
  release contains several distinct ideas, pick the one worth understanding and
  list the rest as candidates in the index.
- **Web search is generic search.** It cannot see LinkedIn or most of X. If the
  user saw something there, ask them to paste the gist and run explain mode.

## Mode selection

- No argument, or "what's new", "catch me up", "anything recent" → **Discover**.
- A topic, feature name, URL, or pasted snippet → **Explain** that topic.
- A question about a topic that already has a note, whether the note was
  written earlier in this session or on a previous day → **Follow-up**. Signs:
  the question refers back ("how does the jitter work", "what about on
  Bedrock", "can I combine it with hooks"), or the ledger has a matching slug.
  When in doubt between Explain and Follow-up, grep the ledger; a match means
  Follow-up.
- "what have I covered", "list", "index" → print `<notes dir>/INDEX.md` and stop.
- `--days N` narrows or widens the discover window (default below).
- `--auto` → **Auto**. Unattended, picks one topic itself, never asks. See
  Auto mode.

## Discover mode

### 1. Establish the window

Read `<notes dir>/INDEX.md`. The window starts at the most recent `date` in the
ledger, or 7 days ago if the ledger is empty. Cap it at 14 days unless the user
passed `--days`. Say the window out loud before searching.

### 2. Sweep the sources

Open `references/sources.md`. For every vendor the user cares about (default:
all four) run the fetches and searches it lists. Issue independent fetches in
parallel in a single response. Ask each fetch for entries dated inside the
window only, with a one-line summary and the entry's own date.

Then run the community sweep from the same file for the same window. Its job
is to catch things the vendors under-announced and to show what people are
actually discussing.

### 3. Merge and filter

Drop anything whose slug or title already appears in `INDEX.md` with status
`covered` or `seen`. Merge duplicates across sources into one candidate.

Rank what remains. Prefer, in order:

1. Changes to how the user works day to day in Claude Code (new flags,
   hooks, skills, agents, settings, SDK).
2. New models or model capabilities from any vendor.
3. Agent patterns and tooling that cross vendors (MCP, computer use,
   tool-runner loops, memory, evals).
4. Pricing, limits and deprecations.

Everything else drops unless it is clearly being talked about a lot.

### 4. Present the shortlist

Show at most 8 candidates as a table: topic, vendor, date, one line on what it
is, one line on why it might matter. Then ask with `AskUserQuestion`
(multiSelect, the top 4 as options; the user types the rest under Other) which
ones to explain now.

Record every candidate you showed in `INDEX.md` with status `seen`, so the
next run does not resurface them. A `seen` topic can still be requested
explicitly in explain mode at any time.

### 5. Explain the picks

Run Explain mode for each pick, one at a time, in the order the user chose.

## Explain mode

### 1. Check the ledger

Search `<notes dir>/INDEX.md` for the topic. If a note exists, say so and ask whether
to open it or refresh it. Refreshing rewrites the note in place and updates the
date in the index; it does not create a second file.

### 2. Gather

Fetch, in parallel where independent:

- The primary source: the vendor's doc page, changelog entry, or launch post.
  If the user gave a URL, that is the primary source; still find the official
  doc behind it.
- At least one independent source that discusses it (HN thread, Reddit,
  Simon Willison, a maintainer's write-up). Search
  `"<topic>" site:news.ycombinator.com` and plain `"<topic>"` with the vendor
  name.
- For Claude Code topics, also check whether the installed CLI has it:
  `claude --version`, and `claude --help` or the relevant `--help` subcommand.
  Report the installed version in the note. You may delegate the doc lookup
  to the `claude-code-guide` agent if it exists in this session.

Stop gathering when you can answer all headings in the template with a cited
source, or when you have tried the primary plus two searches and still cannot.
Do not spend more than a handful of fetches on one topic.

### 3. Write the note

Copy the shape in `references/note-template.md` exactly. Fill every heading.
Keep the whole note under about 140 lines — the extra room over a denser
write-up goes to the analogy and the plain-terms explanation, not to padding.
Concrete beats abstract: a real command, a real config snippet, a real
request body, taken from the source. Where a vendor equivalent exists, name
it in "How it compares" with one line each; do not pad that section when
there is no equivalent.

Slug: lowercase, hyphens, the shortest thing a person would type to find it
again, for example `claude-code-hooks-v2`, `gpt-5-responses-api`,
`gemini-2-5-computer-use`.

Save to `<notes dir>/<today>-<slug>.md`.

### 4. Update the index

Append or update the row in `<notes dir>/INDEX.md`:

```
| YYYY-MM-DD | <slug> | <vendor> | covered | <one-line what it is> | <file> |
```

Vendor is one of `claude`, `claude-code`, `openai`, `gemini`, `cross`.

### 5. Report

Reply with the file path and the "In one paragraph" section, nothing more. The
note is the deliverable; do not restate it in chat.

## Follow-up mode

One topic, one file. A follow-up question never creates a second note.

### 1. Find the note

Match the topic against the ledger's `slug` and `what` columns, or use the
note you wrote earlier this session. Read the whole note before answering so
the follow-up builds on what is already there instead of repeating it.

### 2. Answer from sources

Same rules as Explain: fetch, do not recall. Start with the URLs already in
the note's Sources section, since they usually hold the answer. Add new
sources only if those do not cover it.

### 3. Append to the same file

Add a section at the end of the note, before Sources, in this shape:

```
## Follow-up (YYYY-MM-DD): <the question, shortened>

<answer, a few short paragraphs or a list; a code block if there is a
command or snippet; each factual line marked `official` or `community` when
it is a limit or a claim>
```

Then:

- If the answer corrects something earlier in the note, fix the earlier text
  in place as well, so the note never contradicts itself.
- Add any new URLs to the Sources list.
- If the answer resolves an item under Unverified, move it out of there.
- Never rewrite or trim the existing sections otherwise.

Several follow-ups on one day get separate sections, each with its own
heading.

### 4. Update the ledger

Update the row's `date` to today. Leave the slug, status and filename alone.

### 5. Report

Answer the question in chat as you normally would, then give the file path
in one line. The chat answer and the appended section should say the same
thing.

## Auto mode (`--auto`)

Unattended. `scripts/run.sh`, fired by launchd at noon, runs this in print
mode and `scripts/send_email.py` emails whatever note it produces, so there is
nobody to answer a question. Never call `AskUserQuestion`, never ask whether
to open or refresh, never wait for input. Decide and move on.

### 1. Window

As in Discover step 1, except the window starts at the ledger's most recent
`date` or 3 days ago, whichever is earlier, so a quiet weekend still gets
covered. Cap at 14 days.

### 2. Sweep, merge, filter, rank

Discover steps 2 and 3, unchanged.

### 3. Pick one

- Take the top-ranked fresh candidate. Record every other candidate in the
  top 8 in `INDEX.md` as `seen`; they are the backlog for future runs.
- If nothing fresh survived the filter, take the oldest `seen` row in the
  ledger instead. It becomes `covered`: update that row in place with today's
  date, the new status and the note filename. Do not add a second row.
- If there is nothing fresh and no `seen` backlog, skip to step 5 with
  status `nothing-new`.

### 4. Explain

Explain steps 2 to 4 for the pick, exactly as written. The note is read on a
phone with no chance to ask a follow-up until the next session, so it must
stand alone: fill every heading, keep the runnable example, name the limits.

### 5. Report

The final reply is one JSON object on a single line and nothing else, because
`scripts/send_email.py` parses it. No prose before or after it.

```
{"status":"note","slug":"...","topic":"...","vendor":"...","picked_from":"fresh|backlog","window":"YYYY-MM-DD..YYYY-MM-DD","candidates":N,"note":"/absolute/path/to/note.md"}
```

or

```
{"status":"nothing-new","window":"YYYY-MM-DD..YYYY-MM-DD","candidates":0}
```

Cost and token figures come from print mode's own JSON envelope; do not try to
report them yourself.

### Operating it

Run these from a terminal, not from inside a session, so `PLUGIN` below is the
plugin's actual path on disk (for this install:
`<project>/.claude/skills/ai-catchup`).

| Task | Command |
|---|---|
| One-time Gmail authorization | `~/.config/ai-catchup/.venv/bin/python $PLUGIN/scripts/authorize.py` |
| Install or reinstall the noon schedule | `$PLUGIN/scripts/install-schedule.sh` (`--remove` to uninstall) |
| Run now, ignoring the once-a-day guard | `$PLUGIN/scripts/run.sh --force` |
| Email an existing note as a test | `~/.config/ai-catchup/.venv/bin/python $PLUGIN/scripts/send_email.py --note <file>` |
| Per-run cost and tokens | `~/.config/ai-catchup/runs.csv` |
| Raw envelope and stderr of a run | `~/.config/ai-catchup/logs/` |

The runner caps a run at `$AI_CATCHUP_MAX_BUDGET_USD` (default 8) at list
price. Failures and empty windows still produce an email so a silent day is
never ambiguous.

## Quality bar for a note

A good note lets the user, a week later, re-explain the thing to someone who
has never heard of it, without opening the source, and holds every follow-up
they have asked since, so the file is the full record of what they know
about the topic. It reads like a good explainer written by someone who
understood the thing and wants a newcomer to get it too, not like a digest
of quotations aimed at someone who already knows the field. That means it
names the problem before the solution, explains the idea in plain terms
before the mechanics, defines every term on first use, shows one working
example, names the limits, and separates what the vendor claims from what
users have observed. If a note only makes sense to someone who already knew
the topic's neighbourhood, it has not cleared the bar.
