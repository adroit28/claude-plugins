#!/bin/bash
# One-time environment check + venv for the football-shorts build scripts.
# Usage: setup.sh [shorts_dir]   (default: $FOOTBALL_SHORTS_DIR or $CLAUDE_PROJECT_DIR/shorts or ./shorts)
set -e
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
[ $ok = 1 ] && echo "ready: PY=$DIR/.venv/bin/python" || { echo "fix the MISSING items above"; exit 1; }
