#!/usr/bin/env bash
# Usage: ./make_level.sh <image> [name] [caption]
# Image -> levels/<name>/ (level.glb, level.json, topdown.png, index.html viewer).
# Uses Lyra 2.0 when LYRA_DIR is set and a CUDA GPU is present, else the CPU depth fallback.
set -e
cd "$(dirname "$0")"
IMG="$1"; NAME="${2:-$(basename "${IMG%.*}")}"; CAPTION="${3:-}"
[ -f "$IMG" ] || { echo "usage: $0 <image> [name] [caption]"; exit 1; }
OUT="levels/$NAME"; mkdir -p "$OUT"
[ -d .cache/MiDaS ] || pipeline/setup.sh
cp "$IMG" "$OUT/reference.${IMG##*.}"
if [ -n "$LYRA_DIR" ] && command -v nvidia-smi >/dev/null; then
  PLY=$(pipeline/lyra_stage.sh "$IMG" "$OUT/lyra" "$CAPTION" | tail -1)
  python3 pipeline/points_to_level.py "$PLY" "$OUT"
else
  python3 pipeline/image_to_points.py "$IMG" "$OUT/points.npz" 2>/dev/null
  python3 pipeline/points_to_level.py "$OUT/points.npz" "$OUT"
  rm -f "$OUT/points.npz"; mv "$OUT/points_depth.png" "$OUT/depth.png"
fi
cp pipeline/viewer.html "$OUT/index.html"
echo "done: $OUT/level.glb"
