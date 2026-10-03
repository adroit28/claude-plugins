#!/bin/bash
# One-time environment check for the facts-shorts scripts. Changes nothing except creating the
# content folder and copying the fonts into it when they already exist in a sibling shorts/fonts.
# Usage: setup.sh [content_dir]   (default: $FACTS_DIR or $CLAUDE_PROJECT_DIR/facts-channel or ./facts-channel)
set -e
DIR="${1:-${FACTS_DIR:-${CLAUDE_PROJECT_DIR:-.}/facts-channel}}"
mkdir -p "$DIR"
ok=1
for t in ffmpeg ffprobe python3 node npm; do
  if command -v $t >/dev/null; then echo "ok   $t  $(command -v $t)"; else echo "MISSING $t  (brew install ffmpeg node)"; ok=0; fi
done
FONTS="Anton-Regular.ttf BarlowCondensed-ExtraBold.ttf BarlowCondensed-SemiBold.ttf"
have=1; for f in $FONTS; do [ -f "$DIR/fonts/$f" ] || have=0; done
if [ $have = 0 ] && [ -d "$DIR/../shorts/fonts" ]; then
  mkdir -p "$DIR/fonts"
  for f in $FONTS OFL.txt; do [ -f "$DIR/../shorts/fonts/$f" ] && cp "$DIR/../shorts/fonts/$f" "$DIR/fonts/"; done
  echo "ok   fonts copied from ../shorts/fonts"
fi
for f in $FONTS; do
  [ -f "$DIR/fonts/$f" ] && echo "ok   font $f" || { echo "MISSING $DIR/fonts/$f (Google Fonts, OFL: Anton, Barlow Condensed)"; ok=0; }
done
[ -f "/System/Library/Fonts/Apple Color Emoji.ttc" ] && echo "ok   Apple Color Emoji (emoji props render in headless Chrome)"
[ -f "$DIR/channel.json" ] && echo "ok   $DIR/channel.json" || echo "note no channel.json yet: the plugin defaults apply (copy one from the README to change name, avatar, voice)"
if grep -qs '^GEMINI_FREE_KEY=.' "$HOME/.config/facts-shorts/.env" "$HOME/.config/football-stories/.env"; then
  echo "ok   GEMINI_FREE_KEY configured (free Gemini TTS voices)"
else
  echo "MISSING GEMINI_FREE_KEY in ~/.config/facts-shorts/.env (AI Studio key from a project without billing)"; ok=0
fi
[ $ok = 1 ] && echo "ready: content folder $DIR" || { echo "fix the MISSING items above"; exit 1; }
