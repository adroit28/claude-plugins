---
name: publish
description: Push a finished thumbnail, title, description, tags or caption file to a video that is already on the user's YouTube channel. Use when the user says "set this thumbnail on the video", "update the title on YouTube", "change the description on my channel", "upload these captions", or asks to apply metadata directly instead of pasting it into Studio.
---

# Publish changes to a video

The only skill in this plugin that writes to YouTube. It edits videos the
user has already uploaded; it never uploads videos, never changes privacy or
schedule, never deletes anything. It uses its own token
(`secrets/token-write.json`, scope `youtube.force-ssl`); the read-only token
the other skills use is not touched.

## Paths

- Script: `${CLAUDE_PLUGIN_ROOT}/scripts/publish.py` (or
  `${CLAUDE_PROJECT_DIR}/.claude/skills/yt-insights/scripts/publish.py`)
- Python: `${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python`
- Log of every write: `${CLAUDE_PROJECT_DIR}/yt-insights/data/publish.log`

## Steps

**1. Find the video.** Never guess an id.

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/publish.py" --project-dir "${CLAUDE_PROJECT_DIR}" list --n 10
```

If the target is not in the list, the user has not uploaded it yet; say so
and stop. Private and scheduled uploads do appear.

**2. Dry run.** Every command prints what it would change and exits unless
`--yes` is given. Show the user the dry-run output.

```bash
PY="${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python"; PUB="${CLAUDE_PLUGIN_ROOT}/scripts/publish.py"
"$PY" "$PUB" --project-dir "${CLAUDE_PROJECT_DIR}" thumbnail --video <id> --file "${CLAUDE_PROJECT_DIR}/yt-insights/thumbnails/<file>.png"
"$PY" "$PUB" --project-dir "${CLAUDE_PROJECT_DIR}" metadata  --video <id> --title "..." --description-file desc.txt --tags "a,b"
"$PY" "$PUB" --project-dir "${CLAUDE_PROJECT_DIR}" captions  --video <id> --file subs.srt --lang en
```

**3. Apply with `--yes`** only for the exact change the user asked for in
this conversation. "Update the thumbnail" does not include the title. If the
user asked for one change and the draft has three, apply one.

**4. Report**: the video id, what changed, and the quota spent. For a
thumbnail add: the image can take a few minutes to update everywhere, and on
Shorts it shows on the channel grid, search and subscriptions, not in the
swipe feed.

## First run and failures

- The first write opens a browser for a second Google consent (Advanced →
  Go to app → allow). While the Cloud app is in Testing status this token
  also expires every 7 days; the script reopens the browser on its own.
- `403 forbidden` on a thumbnail means the channel is not phone-verified;
  send the user to youtube.com/verify, then retry. It is not a scope problem.
- `metadata` fetches the current snippet and sends it back with only the
  named fields changed, so category, language and schedule stay as they are.
  `--tags` replaces the whole tag list; read the dry run.
- `captions` replaces an existing track with the same language and name,
  otherwise adds one. Quota is 400 to 450 units per upload against a
  10,000 daily budget; say so if the user wants to bulk-upload.

## Constraints

- Dry run first, every time. Do not chain `--yes` onto a first attempt.
- One video per command. No loops over the channel.
- If the user asks to change privacy, schedule, delete or upload, say the
  plugin does not do that and point them to Studio.
