#!/usr/bin/env bash
# One-time CPU setup: python deps + MiDaS small depth model (all from GitHub/PyPI).
set -e
cd "$(dirname "$0")/.."
pip install -q torch numpy pillow scipy trimesh timm plyfile
mkdir -p .cache
[ -d .cache/MiDaS ] || git clone -q --depth 1 https://github.com/isl-org/MiDaS .cache/MiDaS
[ -d .cache/gen-efficientnet-pytorch ] || git clone -q --depth 1 https://github.com/rwightman/gen-efficientnet-pytorch .cache/gen-efficientnet-pytorch
[ -f .cache/midas_small.pt ] || curl -sSL -o .cache/midas_small.pt \
  https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.pt
echo "setup ok"
