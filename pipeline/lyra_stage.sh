#!/usr/bin/env bash
# GPU stage (H100/A100, >=43GB): image -> Lyra 2.0 exploration video -> 3DGS .ply. Prints the .ply path last.
# Requires Lyra-2 installed per $LYRA_DIR/INSTALL.md with checkpoints in $LYRA_DIR/checkpoints/model.
# Verified against Lyra-2 source (arg names, output paths, PLY fields); not yet run on a GPU.
set -e
IMG=$(realpath "$1"); OUT=$(realpath -m "$2"); CAPTION="${3:-A wide, static, explorable environment.}"
mkdir -p "$OUT/in"; cp "$IMG" "$OUT/in/00.png"; echo "$CAPTION" > "$OUT/in/00.txt"
cd "$LYRA_DIR"
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
PYTHONPATH=. python -m lyra_2._src.inference.lyra2_zoomgs_inference \
  --input_image_path "$OUT/in" --sample_id 0 --experiment lyra2 \
  --checkpoint_dir checkpoints/model --prompt_dir "$OUT/in" --output_path "$OUT/zoomgs" \
  --num_frames_zoom_in 81 --num_frames_zoom_out 241 --zoom_in_strength 0.5 --zoom_out_strength 1.5 ${LYRA_FAST:+--use_dmd} >&2
PYTHONPATH=. python -m lyra_2._src.inference.vipe_da3_gs_recon \
  --input_video_path "$OUT/zoomgs/videos/00.mp4" --output_dir "$OUT/gs" >&2
echo "$OUT/gs/reconstructed_scene.ply"
