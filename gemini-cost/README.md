# gemini-cost

Checks Google AI Studio / Gemini API usage and billing for a project by
reading the same dashboards a human would, through your own signed-in
Chrome. One skill:

- `/gemini-cost:check` — requests and tokens per model (per day), cost
  before and after credits from Cloud Billing grouped by SKU, Developer
  Program credit remaining and expiry, prepaid balance, cost per typical
  call, and rate-limit tier. Read-only throughout.

## No credentials, by design

This plugin does not use, ask for, or store an API key, OAuth client,
service account, or any other secret. It never calls the Gemini generative
API (no image generation, no TTS) — it only reads AI Studio's Usage/Spend/
Rate Limit pages and Cloud Console's Billing Reports/Credits/Transactions
pages, the way you would by clicking around, via your browser's own Google
sign-in. There is no `secrets/` folder, no `.env`, nothing to accidentally
commit or leak.

The one thing worth knowing: it reads a couple of the Usage page's charts
by hooking `XMLHttpRequest` inside the page itself (see
`skills/check/SKILL.md`) rather than via the MCP browser tool's own
network-inspection calls — those calls surface the tab's live session
cookies into the conversation, so this skill deliberately avoids them and
never does. Everything it reads comes back as small, already-parsed JSON
from inside the tab; nothing is written to disk.

## Setup

Needs the `chrome-studio` MCP tool (a Chrome DevTools MCP server attached
to your real, already-signed-in Chrome — not the isolated `chrome-devtools`
tool other skills use for sandboxed browsing). If it's already installed
for another plugin (e.g. `yt-insights`) there's nothing more to do. If not:

```
claude mcp add chrome-studio -s user -- npx -y chrome-devtools-mcp@latest --autoConnect
```

Then in Chrome (version 144+) open `chrome://inspect/#remote-debugging`,
turn on "Allow remote debugging", and restart the Claude Code session.
Never give the assistant your Google password — it isn't needed; the skill
rides on whatever Google account is already signed in to that Chrome.

## Use

```
/gemini-cost:check
/gemini-cost:check gen-lang-client-0308887214
```

Defaults to whichever project is currently active in AI Studio; name a
project (by name or id) to check a different one.
