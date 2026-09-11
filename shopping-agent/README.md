# Shopping Agent

A Claude Code plugin that searches Amazon.in and Flipkart through a real
browser, filters listings against rating/review rules, and builds a ranked
HTML catalog.

## Why a real browser

Neither site has a usable public API (Amazon's PA-API needs an Associates
account with qualifying sales; Flipkart's affiliate API is closed to new
signups). Headless scrapers get bot-checked. Driving your own Chrome via the
`chrome-devtools` MCP server sidesteps that: the sites see an ordinary visitor
on a residential IP. Measured on 2026-09-12, 56 listings came back across both
sites with no CAPTCHA.

## Requires

- The `chrome-devtools` MCP server, with a Chrome instance running.
- Python 3.11+ (`tomllib`). No pip install — stdlib only, deliberately.

## Skills

| Skill | Does |
| --- | --- |
| `/shopping-agent:shop <query>` | Search both sites, filter, rank, write an HTML catalog |

## Rules

Thresholds live in `config/rules.default.toml`, which is copied to
`<project>/shopping/rules.toml` on first run. **Edit the copy** — the shipped
file is overwritten on plugin updates. Defaults are ★4.0 / 500+ ratings, with
stricter per-category overrides (electronics is ★4.2 / 1,000+).

Ranking uses a Bayesian shrink toward a 3.9 prior, so a 5.0★ backed by three
ratings cannot outrank a 4.3★ backed by 49,000. Raw star sorting is useless on
these sites; that is the whole point of the score.

## Layout

```
.claude-plugin/plugin.json   manifest (this file only)
skills/shop/SKILL.md         the procedure + judgment
scripts/catalog.py           filter, rank, dedupe, render
scripts/extract/*.js         DOM extractors, injected per site
config/rules.default.toml    shipped defaults
```

Everything the user touches lives in the project, not in a dotfolder:

```
<project>/shopping/
├── rules.toml            your config — edit this
├── catalogs/<slug>-<date>.html
└── .tmp/                 scratch, deleted after each run
```

Three homes, three purposes: `${CLAUDE_PLUGIN_ROOT}` for shipped code (replaced
on update), `${CLAUDE_PROJECT_DIR}` for anything the user reads or edits, and
`${CLAUDE_PLUGIN_DATA}` for machine state nobody opens. This plugin needs the
third for nothing, so it uses none of it. Set `[output] dir` in rules.toml to
send catalogs elsewhere if you run /shop from unrelated repos.

## Maintenance

Amazon anchors on `data-component-type` and `aria-label`, both stable. Flipkart
ships hashed class names, so its extractor anchors on `div[data-id]` and the
literal `4.3(1,234)` badge shape instead. Flipkart redesigns will eventually
break it; the fix is confined to `scripts/extract/flipkart.js`.

Automated access is against both sites' terms of service. This is built for
personal, hand-triggered, low-volume use.
