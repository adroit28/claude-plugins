#!/usr/bin/env bash
# Terminal side of the Gemini-app route: moves text between the Gemini chat app and the Short's folder.
#
#   facts taken                                     copy the topic ledger (taken list + coverage) for the Facts Ideas skill
#   facts pick <slug> "<title>" "<category>" "<hook>"  record the picked topic and make its folder
#   facts save verify <slug>                        clipboard -> <slug>/verify.md (previous copy kept as verify.prev.md)
#   facts save quick <slug>                         clipboard -> <slug>/verify.md from Quick Script (unchecked facts, no audit)
#   facts save story <slug>                         clipboard -> <slug>/story.v1.json, then the checker
#   facts check <slug>                              run the checker on the latest story again
#   facts narrate <slug>                            checker, one free Gemini TTS take, word timings, open the audio
#   facts copy ideas|research|script|quick [desc]   copy a Gemini skill's instructions (or its description)
#
# Content folder: $FACTS_DIR, else ./facts-channel, else . (when it holds channel.json).
# Stdlib Python + the plugin's scripts; nothing here calls Claude or a paid API.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
S="$HERE/../scripts"

root() {
  if [[ -n "${FACTS_DIR:-}" ]]; then echo "$FACTS_DIR"
  elif [[ -f "$PWD/facts-channel/channel.json" ]]; then echo "$PWD/facts-channel"
  elif [[ -f "$PWD/channel.json" ]]; then echo "$PWD"
  else echo "can't find the content folder: set FACTS_DIR or run from the folder that holds facts-channel/" >&2; exit 1; fi
}
R="$(root)"; export FACTS_DIR="$R"

need_slug() { [[ -n "${1:-}" && "$1" =~ ^[a-z0-9-]+$ ]] || { echo "slug must be kebab-case (a-z, 0-9, -): '${1:-}'" >&2; exit 1; }; }

latest_story() {
  local f; f="$(python3 -c 'import pathlib,re,sys; v=sorted(pathlib.Path(sys.argv[1]).glob("story.v*.json"), key=lambda q: int(re.search(r"\.v(\d+)\.json$", q.name).group(1))); print(v[-1] if v else "")' "$R/$1")"
  [[ -n "$f" ]] || { echo "no story file in $R/$1: run 'facts save story $1' first" >&2; exit 1; }
  echo "$f"
}

cmd="${1:-help}"; shift || true
case "$cmd" in
  taken)
    t="$(echo "TAKEN (never suggest these or near-duplicates):"; python3 "$S/ideas.py" taken
      echo; echo "COVERAGE (made/picked per category; prefer the lowest):"; python3 "$S/ideas.py" coverage)"
    echo "$t"; printf '%s\n' "$t" | pbcopy
    echo; echo "copied: paste it into the Facts Ideas skill" ;;

  pick)
    slug="${1:-}"; title="${2:-}"; cat="${3:-}"; hook="${4:-}"; need_slug "$slug"
    [[ -n "$title" ]] || { echo 'usage: facts pick <slug> "<title>" "<category>" "<hook>"' >&2; exit 1; }
    [[ ! -e "$R/$slug" ]] || { echo "$R/$slug already exists: pick another slug" >&2; exit 1; }
    if ! out="$(python3 "$S/ideas.py" add "$title" --category "$cat" --hook "$hook" --status picked --slug "$slug" 2>&1)"; then
      case "$out" in
        *"already in the ledger (pitched)"*) python3 "$S/ideas.py" set "$title" --status picked --slug "$slug" ;;
        *) echo "$out" >&2; exit 1 ;;
      esac
    else echo "$out"; fi
    mkdir -p "$R/$slug"; echo "folder: $R/$slug" ;;

  save)
    kind="${1:-}"; slug="${2:-}"; need_slug "$slug"
    [[ "$kind" == verify || "$kind" == quick || "$kind" == story ]] || { echo "usage: facts save verify|quick|story <slug>" >&2; exit 1; }
    mkdir -p "$R/$slug"
    pbpaste | python3 "$HERE/facts_save.py" "$kind" "$R/$slug" "$slug"
    if [[ "$kind" == story ]]; then
      echo; python3 "$S/validate.py" "$R/$slug/story.v1.json" \
        && echo "checker passed: next, 'facts narrate $slug'" \
        || echo "checker found errors: copy the ERROR/warn lines above into the Facts Script skill, then save again"
    fi ;;

  check)
    need_slug "${1:-}"; st="$(latest_story "$1")"; python3 "$S/validate.py" "$st" ;;

  narrate)
    need_slug "${1:-}"; st="$(latest_story "$1")"
    python3 "$S/validate.py" "$st" || { echo "fix the errors first (paste them into the Facts Script skill)" >&2; exit 1; }
    echo; python3 "$S/tts.py" "$st"
    echo; python3 "$S/segalign.py" "$st"
    wav="$(python3 -c 'import json,sys,pathlib; p=pathlib.Path(sys.argv[1]); print(p.parent / json.loads(p.read_text())["narration"]["audio"])' "$st")"
    echo; echo "audio: $wav"; open "$wav" || true
    echo "Listen for names and Hindi words said wrong. All good? In Claude Code: /facts-shorts:video $st" ;;

  copy)
    k="${1:-}"; f="$HERE/$k-skill.md"; [[ -f "$f" ]] || { echo "usage: facts copy ideas|research|script|quick [description]" >&2; exit 1; }
    if [[ "${2:-}" == desc* ]]; then sed -n '2p' "$f" | tr -d '\n' | pbcopy; echo "copied the Facts ${k} description: paste it into Description"
    else sed '1,/^=== INSTRUCTIONS/d' "$f" | pbcopy; echo "copied the Facts ${k} instructions: paste them into Instructions"; fi ;;

  *) sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//' ;;
esac
