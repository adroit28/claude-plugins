---
topic: <Human-readable title>
slug: <slug>
date: <YYYY-MM-DD, the day this note was written or refreshed>
vendor: claude | claude-code | openai | gemini | cross
announced: <date the vendor shipped or announced it, from the source>
installed: <for Claude Code topics, output of `claude --version`; otherwise omit>
---

# <Title>

## In one paragraph

What it is, what it replaces or changes, and who should care. Four sentences at
most. This section is what gets echoed back in chat.

## What changed

Before versus after. If it is brand new, say what people did instead until now.
Quote the vendor's own framing in one line, then say it plainly.

## How it works

The mechanism, not the pitch. Configuration, request shape, lifecycle, where it
plugs in. Use the vendor's real names for things.

## Try it

One minimal, runnable example lifted from the source. A command, a settings
snippet, a request body. Say what output to expect.

```
<example>
```

## Limits and gotchas

What it cannot do, what it costs, what is still in preview, what users report
breaking. Mark each line `official` or `community`.

## How it compares

The nearest equivalent from the other vendors, one line each, or "No direct
equivalent as of <date>." Do not pad.

## Unverified

Claims you saw but could not confirm from an official source. Leave the
heading with "Nothing." if empty.

## Follow-up (YYYY-MM-DD): <question>

Only present once the user has asked one. Appended by Follow-up mode, newest
last. Omit this heading entirely when writing a fresh note.

## Sources

- <URL> - what it is, date
- <URL> - what it is, date
