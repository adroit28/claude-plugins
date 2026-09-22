# ai-catchup

Tracks what changed recently in Claude, Claude Code, OpenAI and Gemini,
explains one thing at a time from primary sources, and keeps a note per topic
so nothing gets re-explained twice. One skill, four modes:

- `/ai-catchup:catchup` — no argument: sweeps official changelogs, docs and a
  community pass (Hacker News, Simon Willison, Reddit) since the last note,
  shows a shortlist, and writes a note for whichever ones you pick.
- `/ai-catchup:catchup <topic>` — explains one named topic, feature, URL or
  pasted snippet the same way, skipping the sweep.
- A follow-up question on a topic already covered appends to that topic's
  note instead of creating a new one.
- `/ai-catchup:catchup --auto` — unattended: picks the top candidate itself
  (or the oldest backlogged one on a quiet day), never asks a question, and
  ends with one line of JSON that a caller can parse.

Every note lands in a personal notes folder outside the plugin
(`$AI_CATCHUP_NOTES_DIR`, default `~/Documents/ai-learning/personal
projects/ai-learnings/`), one markdown file per topic plus an `INDEX.md`
ledger that doubles as the dedup list. Nothing user-specific is ever written
inside the plugin.

## Daily email (optional)

`scripts/` turns `--auto` into an unattended job: a launchd agent runs
`run.sh` once a day, which calls the skill in print mode, then
`send_email.py` emails the full note plus a cost-and-token footer through the
Gmail API. Failures and empty windows still send an email, so a silent day is
never ambiguous.

Everything user-specific — the OAuth client, the mail-send token, the
recipient address, the venv, the run log and per-run logs — lives in
`~/.config/ai-catchup/`, never inside this plugin, so the plugin stays safe to
publish or share.

### One-time setup

1. Create (or reuse) a Google Cloud OAuth **Desktop app** client, add scope
   `gmail.send`, and save the downloaded JSON as
   `~/.config/ai-catchup/oauth_client.json`.
2. Build the mailer's own virtualenv:
   ```bash
   python3 -m venv ~/.config/ai-catchup/.venv
   ~/.config/ai-catchup/.venv/bin/pip install -r "$PLUGIN/scripts/requirements.txt"
   ```
   (`$PLUGIN` is this plugin's path on disk, e.g.
   `<project>/.claude/skills/ai-catchup`.)
3. Authorize once — opens a browser, tick every box including "Send email on
   your behalf":
   ```bash
   ~/.config/ai-catchup/.venv/bin/python "$PLUGIN/scripts/authorize.py"
   ```
4. Install the daily schedule (12:00 local time):
   ```bash
   "$PLUGIN/scripts/install-schedule.sh"
   ```
   `--remove` uninstalls it. `AI_CATCHUP_MODEL` (default `sonnet`) and
   `AI_CATCHUP_MAX_BUDGET_USD` (default `8`) can be set as environment
   variables in the installed `launchd` plist to change the model or the
   per-run spending cap.

While the Google app is in Testing status its refresh token expires every 7
days. Publish the app (Google Cloud Console → OAuth consent screen → Publish
app; no verification needed for personal use) to remove that limit.

### Operating it

| Task | Command |
|---|---|
| Run now, ignoring the once-a-day guard | `"$PLUGIN/scripts/run.sh" --force` |
| Email an existing note as a test | `~/.config/ai-catchup/.venv/bin/python "$PLUGIN/scripts/send_email.py" --note <file>` |
| Per-run cost and tokens | `~/.config/ai-catchup/runs.csv` |
| Raw envelope and stderr of a run | `~/.config/ai-catchup/logs/` |

`macOS Full Disk Access` for `/bin/bash` is required if the notes folder is
under a protected location (Documents, Desktop, iCloud Drive): System
Settings → Privacy & Security → Full Disk Access → add `/bin/bash`. Without
it, `launchd` runs but the script cannot read the project folder.
