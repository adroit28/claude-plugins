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
most, in plain language — this is what a newcomer reads if they read nothing
else. This section is what gets echoed back in chat.

## What's new

One or two sentences: the concrete thing that shipped or changed, stated
plainly. "X now does Y." No mechanism yet, no justification yet — just the
headline, the way you'd say it out loud to someone.

## The problem it solves

What was missing, broken, or annoying before this existed — the gap this
fills. If people worked around it, say how, and why the workaround was
imperfect. A change means nothing until the reader feels the itch it
scratches. Someone who has never needed this before should still understand
*why* someone would.

## In plain terms

The heart of the note. Explain the idea itself using an analogy or a mental
model, assuming the reader has never encountered this specific mechanism —
even though they use these tools daily. Define every term the first time it
appears; a protocol name, a component, a pattern's name all need one clause
of explanation before they get used again. Quote the vendor's own framing in
one line if it helps, then say it in your own words. No mechanics yet — this
section should make sense to someone who will never open a config file.

## Why it's useful

Who benefits, and in what real situation. One or two concrete scenarios
beat an abstract claim — "if you maintain a repo two different AI tools both
touch" lands harder than "improves interoperability."

## How it works

Now the mechanism, for the reader who wants to actually use it. Configuration,
request shape, lifecycle, where it plugs in. Use the vendor's real names for
things, since the reader now has the concept to hang them on.

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
