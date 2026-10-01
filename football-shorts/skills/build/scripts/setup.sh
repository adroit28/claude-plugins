#!/bin/bash
# One-time environment check + venv for the football-shorts build scripts.
# Usage: setup.sh [--detect] [shorts_dir]   (default: $FOOTBALL_SHORTS_DIR or $CLAUDE_PROJECT_DIR/shorts or ./shorts)
#   --detect  also create <shorts_dir>/.venv-detect for detect.py (torch + rfdetr + trackers, ~1.2 GB) and print PYD=
set -e
DETECT=0; [ "$1" = "--detect" ] && { DETECT=1; shift; }
DIR="${1:-${FOOTBALL_SHORTS_DIR:-${CLAUDE_PROJECT_DIR:-.}/shorts}}"
mkdir -p "$DIR/briefs"
ok=1
for t in ffmpeg ffprobe python3; do
  if command -v $t >/dev/null; then echo "ok   $t  $(command -v $t)"; else echo "MISSING $t  (brew install ffmpeg)"; ok=0; fi
done
if command -v yt-dlp >/dev/null; then echo "ok   yt-dlp $(yt-dlp --version)"; else echo "note yt-dlp not installed (only needed to fetch sources: brew install yt-dlp)"; fi
if ffmpeg -hide_banner -filters 2>/dev/null | grep -q " drawtext "; then echo "ok   drawtext available"; else echo "note ffmpeg has no drawtext; all text is rendered with Pillow (this is expected on Homebrew builds)"; fi
for f in "/System/Library/Fonts/Supplemental/Impact.ttf" "/System/Library/Fonts/Supplemental/Arial Bold.ttf" "/System/Library/Fonts/Apple Color Emoji.ttc"; do
  [ -f "$f" ] && echo "ok   font $(basename "$f")" || echo "MISSING font $f (set FS_FONT_BIG / FS_FONT_SMALL / FS_FONT_EMOJI)"
done
if [ ! -x "$DIR/.venv/bin/python" ]; then
  echo "creating venv at $DIR/.venv"
  python3 -m venv "$DIR/.venv"
fi
# -i pypi.org: some machines point pip at a private index that rejects anonymous installs
"$DIR/.venv/bin/pip" install -q -i https://pypi.org/simple pillow >/dev/null && echo "ok   Pillow in $DIR/.venv"
n=$(find "$DIR/sfx" -type f \( -name '*.wav' -o -name '*.ogg' -o -name '*.mp3' -o -name '*.flac' \) 2>/dev/null | wc -l | tr -d ' ')
if [ "$n" -gt 0 ]; then echo "ok   sfx pack: $n samples in $DIR/sfx ($(ls "$DIR/sfx" | grep -v LICENSES | tr '\n' ' '))"
else echo "note no sfx pack in $DIR/sfx: hits are synthesised (see LICENSES.md there once a CC0 pack is added)"; fi
if [ $DETECT = 1 ]; then
  # torch and rfdetr lag the newest Python, so use the newest of 3.13/3.12/3.11 that is installed
  if [ ! -x "$DIR/.venv-detect/bin/python" ]; then
    PYB=""; for v in 3.13 3.12 3.11; do command -v python$v >/dev/null && { PYB=python$v; break; }; done
    [ -z "$PYB" ] && { echo "MISSING python3.11-3.13 for detect.py (brew install python@3.12)"; exit 1; }
    echo "creating detect venv at $DIR/.venv-detect with $PYB (torch, ~1.2 GB)"
    $PYB -m venv "$DIR/.venv-detect"
  fi
  "$DIR/.venv-detect/bin/pip" install -q -i https://pypi.org/simple rfdetr trackers supervision >/dev/null \
    && echo "ok   rfdetr + trackers in $DIR/.venv-detect" && echo "PYD=$DIR/.venv-detect/bin/python"
fi
[ $ok = 1 ] && echo "ready: PY=$DIR/.venv/bin/python" || { echo "fix the MISSING items above"; exit 1; }
