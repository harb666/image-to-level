#!/usr/bin/env bash
# ONE COMMAND on a fresh Ubuntu 22.04 GPU machine (1x H100 80GB or A100 80GB, ~150GB disk):
#   curl -sL https://raw.githubusercontent.com/harb666/image-to-level/main/gpu_run.sh | HF_TOKEN=hf_xxx GH_TOKEN=ghp_xxx bash
# Installs Lyra 2.0 (per Lyra-2/INSTALL.md), downloads checkpoints, builds levels for every image in inputs/
# (or just $IMAGE), and pushes levels/<name>-lyra/ back to GitHub if GH_TOKEN is set. Re-running skips finished steps.
set -e
W=${WORK:-$HOME/work}; mkdir -p "$W"; cd "$W"
[ -d image-to-level ] || git clone https://github.com/harb666/image-to-level
[ -d lyra ] || git clone --recursive https://github.com/harb666/lyra
export LYRA_DIR="$W/lyra/Lyra-2"
# conda
if [ ! -d "$HOME/miniconda3" ]; then
  curl -sL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o mc.sh && bash mc.sh -b -p "$HOME/miniconda3"; fi
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda tos accept >/dev/null 2>&1 || true
if ! conda env list | grep -q '^lyra2 '; then
  conda create -n lyra2 python=3.10 pip cmake ninja libgl ffmpeg packaging -c conda-forge -y
  conda activate lyra2
  CONDA_BACKUP_CXX="" conda install gcc=13.3.0 gxx=13.3.0 eigen zlib -c conda-forge -y
  conda install cuda -c nvidia/label/cuda-12.8.0 -y
fi
conda activate lyra2
export CUDA_HOME=$CONDA_PREFIX SITE=$CONDA_PREFIX/lib/python3.10/site-packages
export CPATH="$CUDA_HOME/include:$SITE/nvidia/cudnn/include:$SITE/nvidia/nccl/include:$CPATH"
export LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$SITE/torch/lib:$SITE/nvidia/cuda_runtime/lib:$SITE/nvidia/cudnn/lib:$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-gcc" CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-g++"
cd "$LYRA_DIR"
if [ ! -f "$W/.lyra_installed" ]; then
  pip install torch==2.7.1 torchvision==0.22.1 --extra-index-url https://download.pytorch.org/whl/cu128
  pip install --no-deps -r requirements.txt
  pip install "git+https://github.com/microsoft/MoGe.git"
  pip install --no-build-isolation "transformer_engine[pytorch]"
  ln -sf "$SITE/nvidia/cuda_runtime" "$SITE/nvidia/cudart"
  MAX_JOBS=16 pip install --no-build-isolation --no-binary :all: flash-attn==2.6.3
  USE_SYSTEM_EIGEN=1 pip install --no-build-isolation -e 'lyra_2/_src/inference/vipe'
  pip install --no-build-isolation -e 'lyra_2/_src/inference/depth_anything_3[gs]'
  touch "$W/.lyra_installed"
fi
[ -d checkpoints/model ] || { pip install -q huggingface_hub; huggingface-cli download nvidia/Lyra-2.0 --include "checkpoints/*" --local-dir . ${HF_TOKEN:+--token $HF_TOKEN}; }
cd "$W/image-to-level"
pip install -q numpy pillow scipy trimesh plyfile
for img in ${IMAGE:-inputs/*.png inputs/*.jpg inputs/*.jpeg}; do [ -f "$img" ] && ./make_level.sh "$img"; done
if [ -n "$GH_TOKEN" ]; then
  git add levels && git -c user.name=level-bot -c user.email=level-bot@users.noreply.github.com commit -m "Lyra levels" \
  && git push "https://x-access-token:$GH_TOKEN@github.com/harb666/image-to-level" HEAD:main
fi
echo "DONE. Results in $W/image-to-level/levels/*-lyra/"
