---
name: check
description: Check Google AI Studio / Gemini API usage and billing for a project — requests and tokens per model, cost before and after credits, Developer Program credit remaining, prepaid balance, and rate-limit tier. Read-only. Use when the user says "check my Gemini API spending", "how much have I spent on Gemini", "AI Studio billing", "Gemini API costs", "check my Google AI Studio usage", or asks about their Gemini/AI Studio bill, credits or prepaid balance.
---

# Gemini API cost check

Reads Google AI Studio's usage/billing pages and the linked Cloud Billing
account through the user's own signed-in Chrome, the same way a human would
by clicking around. It never uses an API key, OAuth client, or any stored
credential — there is nothing here to leak because nothing is stored.

## Hard rules — do not bend these

1. **Read-only, always.** Never click Save/Apply on a spend cap, budget,
   API key, or payment method. Never submit a form that changes state.
   Switching a time-range/grouping filter on the Reports page, or switching
   the "Project" dropdown, is a view filter — that's fine.
2. **Never call the Gemini generative API.** No `generateContent`, no image
   generation, no TTS — this only reads AI Studio's and Cloud Console's own
   dashboard pages.
3. **Use `mcp__chrome-studio__*` tools, never `mcp__chrome-devtools__*`.**
   AI Studio and Cloud Console need the user's real Google sign-in; the
   isolated `chrome-devtools` browser can't authenticate and Google blocks
   sign-in attempts inside it. If `chrome-studio` isn't connected or has no
   signed-in Google tab, say so and stop (see yt-insights' README for the
   one-time `claude mcp add chrome-studio -s user -- npx -y
   chrome-devtools-mcp@latest --autoConnect` setup — do this only if the
   user asks; don't run MCP setup commands on your own).
4. **Never call `get_network_request` or `list_network_requests` in this
   skill.** They dump the page's live request/response headers — including
   session auth cookies — straight into the conversation, on every call.
   Everything this skill needs is either visible page text (read with
   `take_snapshot`) or comes back through the in-page interceptor in step 2
   (which returns only response *bodies*, never headers, and never leaves
   the browser tab). If you ever feel tempted to reach for
   `get_network_request` to see "just one more field," that's a sign the
   right move is to extend the interceptor, not to read headers.
5. **Never write anything from this skill to disk.** No scratch files, no
   exported HAR, no saved cookies. Everything is parsed in-browser via
   `evaluate_script` and returned to you as small, already-aggregated JSON —
   never raw network dumps (those can be large enough to itself become a
   problem: filter and aggregate *inside* the injected script, not after).
6. **No API key or credential belongs in this plugin, ever.** If a step
   seems to need one, stop and tell the user — that means the approach is
   wrong, not that a key should be added here.

## Which project

Default to whatever project is currently active in AI Studio. If the user
names a project (by name or `gen-lang-client-...` id), open the "Project"
combobox on the Usage page and select it before continuing — that is a view
filter, not a change to anything billable.

## Steps

### 1. Open AI Studio Usage

Find an existing `aistudio.google.com` tab with `list_pages`, or open one
with `new_page` to `https://aistudio.google.com/usage`. Close any promo
dialog. Confirm the project from the URL's `project=` query param and the
"Project" combobox value — this is what you'll quote in the report.

### 2. Per-model requests/tokens, via an in-page interceptor

The per-model/per-day numbers behind the "Requests per model", "Input
Tokens per model" and "Output Tokens per model" charts are not present as
plain page text — they load through internal RPCs
(`MakerSuiteService/FetchMetricTimeSeries`) whose response bodies are
plain JSON, but whose *headers* carry the session cookie. Read the bodies
only, via `navigate_page` with `type: reload` and this `initScript` (hooks
`XMLHttpRequest`, since this API uses grpc-web over XHR, not `fetch`):

```js
(() => {
  window.__mcpLog = [];
  const OrigXHR = window.XMLHttpRequest;
  const origOpen = OrigXHR.prototype.open;
  const origSend = OrigXHR.prototype.send;
  OrigXHR.prototype.open = function(method, url, ...rest) {
    this.__mcpUrl = url;
    return origOpen.call(this, method, url, ...rest);
  };
  OrigXHR.prototype.send = function(body) {
    this.__mcpReqBody = body;
    this.addEventListener('load', () => {
      try {
        if (this.__mcpUrl && this.__mcpUrl.includes('MakerSuiteService')) {
          window.__mcpLog.push({ url: this.__mcpUrl, reqBody: this.__mcpReqBody, bodyText: this.responseText });
        }
      } catch (e) {}
    });
    return origSend.call(this, body);
  };
})();
```

Then, with `evaluate_script`, wait ~3-4s for calls to land, and return only
a filtered, mapped-down result — never dump `window.__mcpLog` raw (it
includes unrelated RPCs and can blow past the tool's output limit):

```js
() => {
  const log = window.__mcpLog || [];
  return log
    .filter(e => e.url.includes('FetchMetricTimeSeries'))
    .map(e => ({ reqBody: e.reqBody, bodyText: e.bodyText }));
}
```

Each `bodyText` is plain JSON: an array of `[[["<epoch-seconds>"], ["<value>"]], ...], "<model-name>"]`
series keyed by the last element(s) of the request body's breakdown-id array. Decode
epoch seconds with `date -u -r <ts>` (or Python) — these are UTC day
boundaries.

**Metric-id map** (reverse-engineered by observation on 2026-09-26 —
undocumented, and Google can change it without notice; verify before
trusting it, see below):

| Breakdown id(s) | Meaning |
|---|---|
| `[1]` | Requests per model (GenerateContent/BidiGenerateContent only) |
| `[2]` | Input tokens per model |
| `[7]` | Output tokens per model |
| `[3],[2]` | Total API requests per day, all request types, keyed by API key |
| `[4]` | Error count per day, broken down by HTTP status code |
| `[11]` | Success rate (0–1) |
| `[5] [6] [8] [9]` | Imagen / Veo / embedding metrics — null when unused |

**Verify before trusting the map.** Each Usage-page chart's accessibility
snapshot states its own range, e.g. `"Data values on this chart range from
a minimum of 0 to a maximum of 11.794k."` for "Output Tokens per model".
The max value you decode for the id you think is that metric must match.
If it doesn't, the ids have shifted — fall back to clicking each chart's
"Populate data for table" button and reading the accessible grid directly
(slower, but reads the same numbers with no interception), and say in the
report that the id map needed rediscovery.

Cross-check: Cloud Console's per-modality SKU costs (step 4) for *output*
tokens should sum to the same total as this page's output-token total for
that model — text-output-SKU-units + image-output-SKU-units ==
sum of this metric's daily values. If they don't reconcile, say so rather
than picking one number silently.

### 3. AI Studio Spend page

Navigate to `https://aistudio.google.com/spend` (same project). This page's
"Your Total Cost" block (Cost / Savings / Total cost, for a stated date
range) and the "Monthly spend cap" line are plain visible text — read them
with `take_snapshot`, no interception needed.

### 4. Cloud Billing Reports, grouped by SKU

Navigate to `https://console.cloud.google.com/billing?project=<projectId>`
— Cloud Console redirects to that project's linked billing account
overview; read the `billingAccounts/<id>` segment out of the resulting URL.
Then navigate to
`https://console.cloud.google.com/billing/<id>/reports;grouping=GROUP_BY_SKU;timeRange=LAST_30_DAYS?project=<projectId>`.
The SKU table, savings column and subtotal are plain visible text/grid
content — read with `take_snapshot`. Note any model/modality visible in
step 2's AI Studio numbers that has **no** SKU row here yet: Cloud Billing
can lag several hours (the page says so), so today's — or even yesterday's
— calls may not have posted. Say that plainly rather than guessing a cost
for it.

### 5. Credits

Navigate to `https://console.cloud.google.com/billing/<id>/credits/all?project=<projectId>`.
Read the credit rows (name, status, % remaining, remaining value, original
value, expiry) with `take_snapshot`. Ignore `Expired` rows from years past
unless the user asks about history.

### 6. Prepaid balance

Navigate to `https://console.cloud.google.com/billing/<id>/history/prepaidTransactions?project=<projectId>`.
Click the "Prepay - AI Studio" tab if it isn't already selected. The
statement (starting balance, top-ups, ending balance) renders inside an
iframe but is still readable with `take_snapshot`.

### 7. Rate limit / tier

Navigate to `https://aistudio.google.com/rate-limit?project=<projectId>`.
Read the "Tier" badge and, per model, peak RPM/TPM/RPD against their limits
over the selected window — all plain visible text.

## Report

One chat report (no artifact needed — this is for the user, not for
sharing), structured as:

1. **Table:** model/SKU → requests or tokens → cost before credit → credit
   applied → net paid. Cross-check the SKU total against AI Studio's Spend
   total and call out any gap.
2. **Credit and prepaid balance remaining**, with the credit's expiry date.
3. **Cost per typical call**, derived only from numbers actually read —
   e.g. total SKU cost for a model ÷ its request count. If a modality's
   cost hasn't posted yet (step 4's lag), say plainly that no figure is
   available rather than estimating from published price sheets.
4. **Rate-limit tier** and how close usage came to any limit.
5. **Anything odd**: elevated error days, no spend cap configured,
   reconciliation gaps between pages, unexpected models.

Label every number with the page it came from (Usage / Spend / Reports /
Credits / Transactions / Rate Limit) so the user can verify it themselves.
