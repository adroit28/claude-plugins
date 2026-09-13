---
name: report
description: Pull every upload on the user's YouTube channel with Analytics API metrics and build a ranked HTML channel report with insights and next steps. Use when the user says "youtube report", "how is my channel doing", "channel analytics", "which videos performed", "yt insights", or asks about views, retention, traffic sources or posting times for their own channel.
---

# YouTube channel report

Scripts pull and reduce the data; you write the narrative. Never load
`videos.json` or `channel.json` into context — the digest printed by
`summarize.py` is everything you need.

## Paths

- Plugin scripts: `${CLAUDE_PLUGIN_ROOT}/scripts/`
- User data: `${CLAUDE_PROJECT_DIR}/yt-insights/` — `secrets/` (OAuth client and token), `data/` (pulled JSON), `reports/` (output), `style.md` (channel voice), `.venv/`
- Python: `${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python`

## Steps

**0. Check the venv.** If `${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python` is missing:

```bash
python3 -m venv "${CLAUDE_PROJECT_DIR}/yt-insights/.venv" && \
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/pip" install -q -r "${CLAUDE_PLUGIN_ROOT}/scripts/requirements.txt"
```

If `secrets/client_secret.json` is missing, stop and point the user at the
README's Google Cloud setup. Do not guess at credentials.

**1. Fetch.** Default window is 90 days; use `--days N` if the user asks for a
different range.

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/fetch.py" --project-dir "${CLAUDE_PROJECT_DIR}" --days 90
```

The first run fetches a retention curve per video (about 15 seconds each);
later runs reuse cached curves for videos older than two weeks. Add
`--no-retention` for a quick refresh of views only.

If it prints `token dead ... re-authorizing in browser`, a browser tab has
opened. Tell the user to complete the Google sign-in (Advanced → Go to app →
tick all scopes) and wait; the script continues on its own. This happens
every 7 days while the Cloud app is in Testing status.

**1b. Studio export, if any.** If `${CLAUDE_PROJECT_DIR}/yt-insights/studio/` contains CSV
files, import them; this is the only source of impressions, click-through rate and
the Shorts viewed-vs-swiped rate.

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/studio.py" --project-dir "${CLAUDE_PROJECT_DIR}"
```

**2. Summarize.** Read the printed digest carefully; it is the whole evidence base.

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/summarize.py" --project-dir "${CLAUDE_PROJECT_DIR}"
```

**3. Write the notes.** Create `${CLAUDE_PROJECT_DIR}/yt-insights/reports/notes-<date>.md`
with exactly two top-level sections: `# What the numbers say` (4-6 `##`
subsections, each one finding backed by a number from the digest) and
`# What to do next` (5-7 bullets, each an action with a threshold or a slot).
Plain markdown only: `#`, `##`, paragraphs, `-` bullets, `**bold**`.

**4. Render.**

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/report.py" --project-dir "${CLAUDE_PROJECT_DIR}" --notes "${CLAUDE_PROJECT_DIR}/yt-insights/reports/notes-<date>.md"
```

It prints the HTML path. If the Artifact tool is available, publish that file
(favicon ⚽ on first publish, same path on later runs) and give the user the
link. If it is not (this session may authenticate with an API key), give the
local path and open it with `open <path>`.

**5. Update `style.md`** only if the digest contradicts it — a new winning
title shape, a shifted best slot. Edit the specific line; do not rewrite the
file. Say what changed.

**6. Report** in chat: the artifact link, then the three findings that most
change what the user should do next. Numbers go in a short table, not prose.

## Judgment

- **Hook at 3s above 100% is normal for Shorts.** The retention curve counts
  rewatches, so a looping clip reads above 100% from the first second. Compare
  hooks between videos; do not read them as a share of viewers.
- **The retention chart is the first thing to write about** when the top and
  bottom curves separate early. Say where the bottom curves fall away, in
  seconds, using each video's length.
- **Experiments:** if the digest lists one as `read`, state the verdict and
  the ratio in the notes, then say what rule in `style.md` it confirms or
  weakens. If it says `too early`, name the read-after date and move on.

- **Retention above 100% means the Short looped.** Call it a loop, not an error.
- **Small n is the norm.** A weekday median built on two uploads is a hint;
  say so every time you cite it.
- **Engagement rate is inflated on tiny videos.** A 23% rate on 17 views means
  four likes. Compare engagement only among videos above the median.
- **Distinguish lifetime from window.** Video ranks use lifetime numbers;
  KPI tiles use the window. Do not mix them in one sentence.
- **Impressions and click-through rate are not in the API.** If the user asks
  about CTR or thumbnails, say the number lives only in Studio and ask them
  to export the CSV; do not estimate it.
- **Never write to YouTube from this skill.** Its token is read-only by design. If the user
  asks to change a title, hand them the text to paste.
