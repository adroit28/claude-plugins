#!/bin/bash
# Daily ai-catchup runner. launchd calls this at noon (see scripts/install-schedule.sh).
#
#   run.sh            normal run; exits quietly if a run already succeeded today
#   run.sh --force    run again regardless
#
# Everything user-specific lives in ~/.config/ai-catchup/: venv, credentials,
# runs.csv (one row per run) and logs/ (raw JSON envelope + stderr per run).
set -u

CONFIG="$HOME/.config/ai-catchup"
ROOT="$HOME/Documents/ai-learning/personal projects"
SKILL="$ROOT/.claude/skills/ai-catchup"
PY="$CONFIG/.venv/bin/python"
CLAUDE="$HOME/.local/bin/claude"
LOG="$CONFIG/runs.csv"
LOGDIR="$CONFIG/logs"
MAX_BUDGET_USD="${AI_CATCHUP_MAX_BUDGET_USD:-8}"
# Pinned so the scheduled run never rides whatever model the last interactive
# session happened to leave selected. Override with AI_CATCHUP_MODEL if needed.
MODEL="${AI_CATCHUP_MODEL:-sonnet}"

# launchd gives a bare environment: no shell profile, no PATH worth having.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
export LANG="${LANG:-en_US.UTF-8}"

mkdir -p "$LOGDIR"
TODAY=$(date +%F)
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$LOGDIR/$STAMP.json"
ERR="$LOGDIR/$STAMP.stderr"

if [ "${1:-}" != "--force" ] && grep -q "^$TODAY,[^,]*,ok," "$LOG" 2>/dev/null; then
  echo "already ran today, skipping (use --force to rerun)"
  exit 0
fi

cd "$ROOT" || { echo "cannot cd to $ROOT" >&2; exit 1; }

echo "[$STAMP] starting ai-catchup:catchup --auto (model: $MODEL)"
"$CLAUDE" -p "/ai-catchup:catchup --auto" \
  --model "$MODEL" \
  --output-format json \
  --max-turns 80 \
  --max-budget-usd "$MAX_BUDGET_USD" \
  --allowedTools "Skill,WebFetch,WebSearch,Read,Write,Edit,Glob,Grep,Bash(date:*),Bash(claude:*),Bash(ls:*),Bash(cat:*),Bash(mkdir:*),Bash(grep:*)" \
  > "$OUT" 2> "$ERR"
rc=$?
echo "[$STAMP] claude exited $rc"

"$PY" "$SKILL/scripts/send_email.py" --result "$OUT" --exit-code "$rc" --stderr "$ERR"
