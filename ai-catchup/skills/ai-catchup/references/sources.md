# Sources

Fetch with `WebFetch`, search with `WebSearch`. Independent fetches go in one
parallel batch. Every fetch prompt should say: "List entries dated on or after
<window start>. For each give the date, the title, and one line on what
changed. Skip anything older."

Source URLs drift. If a fetch 404s, search for the page's current location
once, then move on rather than retrying.

## Claude and Claude Code (official)

| Source | URL | Notes |
|---|---|---|
| Claude Code changelog | https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md | Most important single source. Versioned, dated. |
| Claude Code docs | https://docs.claude.com/en/docs/claude-code/overview | Fetch specific pages when explaining a feature. |
| Claude Developer Platform release notes | https://docs.claude.com/en/release-notes/overview | API, SDK, model releases. |
| Anthropic news | https://www.anthropic.com/news | Model launches, product announcements. |
| Anthropic engineering blog | https://www.anthropic.com/engineering | Agent patterns, context engineering, evals. |
| Agent SDK docs | https://docs.claude.com/en/api/agent-sdk/overview | For SDK topics. |

Searches: `Claude Code new feature <month year>`, `Anthropic announces`,
`site:docs.claude.com <topic>`.

## OpenAI (official)

| Source | URL | Notes |
|---|---|---|
| OpenAI news | https://openai.com/news/ | Launches. Often returns 403 to fetchers; if so, search `site:openai.com/index <month year>` instead. |
| API changelog | https://platform.openai.com/docs/changelog | Dated API and model changes. |
| Developer blog | https://developers.openai.com/blog | Practical write-ups, Codex, Agents SDK. |
| Codex changelog | https://developers.openai.com/codex/changelog | Closest analogue to Claude Code. |

Searches: `OpenAI announces <month year>`, `Codex CLI update`, `Responses API new`.

## Gemini (official)

| Source | URL | Notes |
|---|---|---|
| Gemini API changelog | https://ai.google.dev/gemini-api/docs/changelog | Dated. |
| Google AI blog | https://blog.google/technology/ai/ | Launches. |
| Google developers blog | https://developers.googleblog.com/ | Filter for Gemini, agents, ADK. |
| Gemini CLI releases | https://github.com/google-gemini/gemini-cli/releases | Closest analogue to Claude Code. |

Searches: `Gemini API update <month year>`, `Google DeepMind announces`,
`Gemini CLI release`.

## Community (all vendors)

| Source | How | Notes |
|---|---|---|
| Hacker News | `https://hn.algolia.com/api/v1/search_by_date?query=<term>&tags=story&numericFilters=created_at_i>UNIX_EPOCH,points>30` | One call per term: `claude`, `anthropic`, `openai`, `gemini`, `mcp`. Compute the epoch with `date -v-7d +%s`. |
| Simon Willison | https://simonwillison.net/ | Reliable, fast, dated. Good "why it matters" source. |
| Reddit | search `site:reddit.com/r/ClaudeAI <topic>`, also r/ClaudeCode, r/OpenAI, r/Bard | Use for pain points and gotchas, not for facts. |
| Latent Space | https://www.latent.space/ | Weekly recaps; useful when the window is wide. |

Treat community sources as evidence of interest and of limits. Facts about
what a feature does come from the official row above.
