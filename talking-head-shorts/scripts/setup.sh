#!/bin/bash
# One-time environment check for talking-head-shorts. Nothing is downloaded unless a flag asks for it.
#   setup.sh                 check ffmpeg/ffprobe/node/python, the venv, Whisper models in the HF cache, the RVM model, node_modules
#   setup.sh --venv          create ~/.config/talking-head-shorts/venv with numpy, opencv, onnxruntime, faster-whisper, Pillow (pip: download)
#   setup.sh --node          npm install remotion into ~/.cache/talking-head-shorts/node (local .npmrc -> registry.npmjs.org; download)
#   setup.sh --rvm           fetch the Robust Video Matting ONNX (~15 MB, PeterL1n/RobustVideoMatting v1.0.0; download)
# The user must have said yes to the download flags. THS_PY / THS_NODE_MODULES / THS_RVM override the locations.
set -e
CFG="$HOME/.config/talking-head-shorts"; CACHE="$HOME/.cache/talking-head-shorts"
VENV="$CFG/venv"; NODE="$CACHE/node"; RVM="$CACHE/models/rvm_mobilenetv3_fp32.onnx"
SHA=88d45312971180f0cbbd2828
for a in "$@"; do case $a in --venv) V=1;; --node) N=1;; --rvm) R=1;; esac; done
for t in ffmpeg ffprobe node python3; do
  command -v $t >/dev/null && echo "ok   $t  $(command -v $t)" || echo "MISSING $t  (brew install ffmpeg node)"
done
if [ -n "$V" ]; then
  mkdir -p "$CFG"; [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -i https://pypi.org/simple numpy opencv-python-headless onnxruntime faster-whisper pillow && echo "ok   venv packages"
fi
PY="${THS_PY:-$VENV/bin/python}"
[ -x "$PY" ] && echo "ok   python  $PY" || echo "note no venv yet: setup.sh --venv, or set THS_PY (e.g. the shorts/.venv python that already has these)"
[ -x "$PY" ] && "$PY" -c "import numpy,cv2,onnxruntime,faster_whisper,PIL;print('ok   imports: numpy cv2 onnxruntime faster_whisper PIL')" 2>&1 | tail -1
for m in small large-v3; do
  d=$(ls -d "$HOME/.cache/huggingface/hub/models--Systran--faster-whisper-$m/snapshots/"*/model.bin 2>/dev/null | head -1)
  [ -n "$d" ] && echo "ok   whisper $m cached" || echo "note whisper $m not cached (transcribe.py --allow-download after the user's yes)"
done
if [ -n "$R" ]; then
  mkdir -p "$(dirname "$RVM")"
  curl -fL --progress-bar -o "$RVM" "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"
fi
if [ -f "$RVM" ]; then
  [ "$(shasum -a 256 "$RVM" | cut -c1-12,53-64 | tr -d ' ')" = "$SHA" ] && echo "ok   RVM model ($(du -h "$RVM" | cut -f1)), sha256 matches" || echo "WARN RVM sha256 differs from v1.0.0 (expected 88d45312...2828)"
else echo "note no RVM model at $RVM (only needed for a background swap)"; fi
if [ -n "$N" ]; then
  mkdir -p "$NODE"; cp "$(dirname "$0")/../templates/remotion/package.json" "$NODE/package.json"
  printf 'registry=https://registry.npmjs.org/\n' > "$NODE/.npmrc"   # ~/.npmrc may point at a dead private registry
  (cd "$NODE" && npm install --no-audit --no-fund >/dev/null) && echo "ok   remotion installed in $NODE"
fi
NM="${THS_NODE_MODULES:-$NODE/node_modules}"
[ -d "$NM" ] && echo "ok   node_modules  $NM" || echo "note no node_modules: setup.sh --node, or pass build.py --node-modules <dir with remotion 4.0.530>"
