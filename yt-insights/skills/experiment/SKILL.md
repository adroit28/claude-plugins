---
name: experiment
description: Register or score a paired YouTube upload experiment (two or more videos posted to test one variable such as length, title shape or posting slot). Use when the user says "track this experiment", "compare these two uploads", "which one won", "score the test", "A/B my shorts", or describes posting two videos to see which performs.
---

# Upload experiments

Paired uploads compared on views per day live, with a ratio rule so a small
gap is called noise instead of a finding. State lives in
`${CLAUDE_PROJECT_DIR}/yt-insights/experiments.json`; the report skill renders
every experiment automatically.

## Register

Find the video ids first. Scheduled uploads already appear in the pull as
`private`:

```bash
python3 -c "import json;[print(v['id'],v['privacy'],v['duration'],v['title'][:60]) for v in json.load(open('${CLAUDE_PROJECT_DIR}/yt-insights/data/videos.json'))]" | tail -8
```

Then:

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/experiments.py" --project-dir "${CLAUDE_PROJECT_DIR}" add \
  --name "<one line: what differs>" --question "<what a win would prove>" \
  --arm <video_id>="<label incl. the variable, e.g. 'Kane 47s 7:45pm'>" --arm <video_id>="<label>" \
  --rule 2.0 --read-after <YYYY-MM-DD, at least 3 days after the later post>
```

Push back before registering if more than one thing differs between arms
(subject and length and slot). Name the confound in the `--name` so the
verdict is read with it in mind. Register anyway if the user wants to.

## Score

```bash
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/fetch.py" --project-dir "${CLAUDE_PROJECT_DIR}" --no-retention
"${CLAUDE_PROJECT_DIR}/yt-insights/.venv/bin/python" "${CLAUDE_PLUGIN_ROOT}/scripts/experiments.py" --project-dir "${CLAUDE_PROJECT_DIR}" score
```

Report the verdict, the ratio, and views per day for each arm in a short
table. Then say what it means for `style.md` and edit the specific line if a
rule was confirmed or weakened. `too early` means analytics have not caught
up; give the read-after date. `noise` is a real answer: say the test did not
separate the arms and suggest what would.

## Constraints

- Views per day live is the comparison, not raw views; arms posted hours
  apart are otherwise unfair to the later one.
- Never delete an experiment; mark it in the name if it was abandoned.
