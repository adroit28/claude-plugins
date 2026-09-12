---
name: metadata
description: Draft a YouTube title, description, hashtags, pinned comment and posting slot for an upcoming video in the channel's own voice, using its top performers as the style reference. Use when the user says "title for this video", "write a description", "caption for my short", "hashtags for", "metadata for my upload", or pastes a clip idea, transcript or rough title.
---

# Video metadata

Turn a clip idea, transcript or rough title into upload-ready metadata that
sounds like this channel, not like generic SEO copy.

## Inputs

1. `${CLAUDE_PROJECT_DIR}/yt-insights/style.md` — the voice and rules. Read it every time.
2. The `top` and `search_terms` arrays from
   `${CLAUDE_PROJECT_DIR}/yt-insights/data/summary.json`:

```bash
python3 -c "import json;s=json.load(open('${CLAUDE_PROJECT_DIR}/yt-insights/data/summary.json'));print(*[v['title'] for v in s['top']],sep='\n');print([t['insightTrafficSourceDetail'] for t in s['search_terms']])"
```

If `summary.json` is missing or older than 14 days, run the `report` skill's
steps 1-2 first.

3. What the user gave you: an idea, a transcript, a draft title, a player or
   match. If the clip length is not stated, ask for it in one line before
   drafting; the length rule in `style.md` is the one that most often needs
   a warning.

## Output

Write `${CLAUDE_PROJECT_DIR}/yt-insights/drafts/<slug>-<date>.md` and echo it in chat:

- **Titles** — five options, each ≤45 characters before hashtags, each with
  the standard hashtag stack appended. Mark the one you would pick and say
  why in one line. Vary the angle across the five (player-led, fan-voice
  reaction, stat shock, rivalry), not just the wording.
- **Description** — two or three lines per `style.md`, full player names
  spelled out for search.
- **Hashtags** — the fixed stack plus one or two specific tags, 4-6 total.
- **Pinned comment** — one line, a question that invites a take.
- **Posting slot** — the next best day and hour in IST from `style.md`.
- **Warnings** — if the clip is over 35 seconds, a question title was
  requested, or the idea is fee-debate framing, say so plainly and offer the
  nearest alternative. Draft anyway; the call is theirs.

## Constraints

- Every title must follow `style.md`. If the user's own words override a rule,
  their words win, but note the rule you broke.
- Search-term spellings matter: if the analytics show `satpaev` and `satpayev`
  both being searched, put the common spelling in the title and the other in
  the description.
- No writes to YouTube. The user pastes the text into Studio themselves.
