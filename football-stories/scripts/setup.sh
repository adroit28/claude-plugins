#!/bin/bash
# One-time environment check + venv for the football-stories scripts.
# Usage: setup.sh [--kokoro] [shorts_dir]   (default: $FOOTBALL_SHORTS_DIR or $CLAUDE_PROJECT_DIR/shorts or ./shorts)
#   --kokoro  also install kokoro-onnx into the venv and download the Kokoro-82M model (~350 MB, once)
set -e
KOKORO=0
[ "$1" = "--kokoro" ] && { KOKORO=1; shift; }
DIR="${1:-${FOOTBALL_SHORTS_DIR:-${CLAUDE_PROJECT_DIR:-.}/shorts}}"
CHROME="${FS_CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
mkdir -p "$DIR/briefs"
ok=1
for t in ffmpeg ffprobe python3; do
  if command -v $t >/dev/null; then echo "ok   $t  $(command -v $t)"; else echo "MISSING $t  (brew install ffmpeg)"; ok=0; fi
done
[ -x "$CHROME" ] && echo "ok   Chrome $("$CHROME" --version 2>/dev/null)" || { echo "MISSING Google Chrome (cards are screenshots of HTML; set FS_CHROME)"; ok=0; }
for f in Anton-Regular.ttf BarlowCondensed-SemiBold.ttf BarlowCondensed-ExtraBold.ttf "Montserrat[wght].ttf"; do
  [ -f "$DIR/fonts/$f" ] && echo "ok   font $f" || { echo "MISSING $DIR/fonts/$f (Google Fonts, OFL)"; ok=0; }
done
[ -f "/System/Library/Fonts/Apple Color Emoji.ttc" ] && echo "ok   Apple Color Emoji (flags and icons on cards)"
if [ ! -x "$DIR/.venv/bin/python" ]; then
  echo "creating venv at $DIR/.venv"
  python3 -m venv "$DIR/.venv"
fi
# -i pypi.org: some machines point pip at a private index that rejects anonymous installs
"$DIR/.venv/bin/pip" install -q -i https://pypi.org/simple pillow faster-whisper >/dev/null && echo "ok   Pillow + faster-whisper in $DIR/.venv"
if [ -f "$HOME/.config/football-stories/.env" ] && grep -q '^GEMINI_FREE_KEY=.' "$HOME/.config/football-stories/.env"; then
  echo "ok   GEMINI_FREE_KEY configured (free voice = Gemini)"
else
  echo "note no GEMINI_FREE_KEY in ~/.config/football-stories/.env (free voice falls back to Kokoro)"
fi
K="$HOME/.cache/football-stories/kokoro"
if [ $KOKORO = 1 ]; then
  "$DIR/.venv/bin/pip" install -q -i https://pypi.org/simple kokoro-onnx >/dev/null && echo "ok   kokoro-onnx"
  mkdir -p "$K"
  for f in kokoro-v1.0.onnx voices-v1.0.bin; do
    [ -s "$K/$f" ] || curl -fL --progress-bar -o "$K/$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
    echo "ok   $K/$f ($(du -h "$K/$f" | cut -f1))"
  done
elif [ -s "$K/kokoro-v1.0.onnx" ]; then echo "ok   Kokoro model present"; else echo "note Kokoro not installed (setup.sh --kokoro)"; fi
[ $ok = 1 ] && echo "ready: PY=$DIR/.venv/bin/python" || { echo "fix the MISSING items above"; exit 1; }
