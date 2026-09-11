---
name: shop
description: Search Amazon.in and Flipkart for a product through the real browser, filter by rating and review-count rules, and build a ranked HTML catalog. Use when the user says "shop for", "find me a", "search Amazon and Flipkart", "I want to buy", or asks for product options with a minimum rating or review count.
---

# Shop

Search both retailers, keep only what clears the user's rules, and hand back a
short catalog. The scripts do the fetching and arithmetic; you make the calls
that need taste.

## Steps

**0. Confirm the browser is reachable.** Call `list_pages` from the
`chrome-devtools` MCP server. If that tool is unavailable, stop immediately and
tell the user this plugin cannot work without it, quoting the install command:

```bash
claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest
```

Do not attempt the search without it — every navigation will fail, and a wall
of tool errors is a worse message than one clear sentence.

**1. Read the rules.** `cat "${CLAUDE_PROJECT_DIR}/shopping/rules.toml"` (seeded
from the shipped defaults on first run — if it is missing, step 4 creates it).
Note the category thresholds so you can explain what was applied.

**2. Extract from Amazon.** Navigate ONCE to
`https://www.amazon.in/s?k=<url-encoded query>` (no `&page`), then
`cat "${CLAUDE_PLUGIN_ROOT}/scripts/extract/amazon.js"` and pass its contents as
the `function` arg of `evaluate_script`, with `filePath`
`shopping/.tmp/amazon-all.json` and `waitForStableDom: true`.

The extractor walks the remaining pages itself with same-origin `fetch`, so one
call covers all of them — do not navigate page by page. Set its `const PAGES`
line to `[search].pages` from rules.toml before passing it.

**3. Extract from Flipkart.** Same, navigating to
`https://www.flipkart.com/search?q=<url-encoded query>` and using
`scripts/extract/flipkart.js` -> `shopping/.tmp/flipkart-all.json`.

**4. Build the catalog.**

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/catalog.py" \
  --query "<query>" \
  --amazon shopping/.tmp/amazon-*.json \
  --flipkart shopping/.tmp/flipkart-*.json \
  --rules "${CLAUDE_PLUGIN_ROOT}/config/rules.default.toml" \
  --project-dir "${CLAUDE_PROJECT_DIR}"
```

The script picks the output path itself —
`<project>/shopping/catalogs/<slug>-<date>.html` — so catalogs accumulate and
can be compared over time. It prints the path it used.

**5. Clean up:** `rm -rf shopping/.tmp`.

**6. Report.** Give the file path, then 2-4 sentences on what survived and why.
Name the products; do not paste the JSON.

## Judgment

- **`should_relax: true` in the output** means fewer than three products
  survived. Rerun step 4 with `--relax` and say plainly that you loosened the
  thresholds and by how much. Never silently hand over a one-item catalog.
- **Default order is each site's own ranking, interleaved** (Amazon #1,
  Flipkart #1, Amazon #2, ...). The storefronts encode sales and relevance
  signals a star average cannot, and this is the order the user browses in.
  Quote the site rank when discussing a product. Only when `[ranking] order`
  is `"score"` does the Bayesian shrink drive the sort — then a 5.0★ with 3
  ratings sinking below a 4.3★ with 49,000 is deliberate, not a bug.
- **Report depth honestly.** Quote `pages_read`, `cross_page_dupes_dropped` and
  any `extractor_notes` (a note means a page loop stopped early — bot check or
  HTTP error). A shallow scan passing as a deep one is the failure to avoid.
- **If a site contributes zero survivors, check before blaming its stock.**
  Confirm from the raw JSON whether its ratings genuinely fail the threshold or
  the extractor is dropping them. Measured 2026-09-12: Amazon.in earbuds top out
  at 4.3 for anything with 1,000+ ratings, so a 4.5 Amazon rule admits nothing
  in that category — real, not a bug. Say which it is.
- **Say something useful about the shape of the results** — a 10x price spread,
  one brand taking four of six slots, Flipkart contributing nothing. That
  observation is the part a plain list cannot give them.
- **Do not recommend a single winner unless asked.** The user wants a catalog to
  judge for themselves; they said so.

## Constraints

- Everything user-facing lives in `${CLAUDE_PROJECT_DIR}/shopping/` — rules,
  catalogs, scratch. Nothing goes in the plugin data dir. `evaluate_script`'s
  `filePath` is sandboxed to workspace roots anyway, so this keeps one path
  rather than two.
- Extraction yields nothing on a bot-check page. If a run returns zero rows for
  a site, screenshot it, tell the user, and continue with the other site rather
  than retrying in a loop.
- Selectors are pinned to `data-component-type`/`aria-label` (Amazon) and
  `data-id` plus the `4.3(1,234)` badge shape (Flipkart). If one site suddenly
  yields no ratings, that site's extractor needs re-anchoring — a one-file fix.
