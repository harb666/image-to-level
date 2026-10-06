# Image → Level pipeline (read this first; don't re-scan the Lyra repo)

## Commands
```
./make_level.sh inputs/<image>.jpg [name] ["caption for Lyra"]   # -> levels/<name>/
```
iPhone: upload an image into `inputs/` via the GitHub app → Action `make-level` builds and commits `levels/<name>/`.
Or ask Claude: "make a level from inputs/<file>".

## Stages
1. **3D points** (one of):
   - **Lyra 2.0 (GPU, preferred quality)** — `pipeline/lyra_stage.sh`, used automatically when `LYRA_DIR`
     (path to a Lyra checkout's `Lyra-2/`, installed per its INSTALL.md + checkpoints) is set and `nvidia-smi` exists.
     Runs `lyra_2._src.inference.lyra2_zoomgs_inference` (image + caption → zoom-in/out exploration video), then
     `vipe_da3_gs_recon` (video → `reconstructed_scene.ply` 3D Gaussians). Needs H100/A100, ≥43GB VRAM, ~10 min
     (`LYRA_FAST=1` → `--use_dmd`, ~1 min). Verified against Lyra source (args, output paths `zoomgs/videos/00.mp4`,
     `gs/reconstructed_scene.ply`, PLY fields x,y,z,f_dc_*,opacity) and converter tested on a synthetic Lyra-format PLY;
     **not yet run on a GPU**. Output goes to `levels/<name>-lyra/` so the CPU level stays for comparison.
     **One command on a rented GPU box:** `gpu_run.sh` (installs Lyra per INSTALL.md, downloads checkpoints, runs, pushes back).
     Caption for Lyra: arg 3, else `inputs/<name>.txt`. Lyra PLY assumed OpenCV frame with first camera ≈ origin.
     Upstream: github.com/harb666/lyra (fork of nv-tlabs/lyra). Lyra-1 = GEN3C-based, older; we use Lyra-2.
   - **CPU fallback** — `pipeline/image_to_points.py`: MiDaS-small monocular depth (weights from GitHub releases;
     HuggingFace is blocked in cloud sessions) → back-projected point cloud, 60° FOV, depth mapped to 1.5–200 m,
     far pixels connected to the image top = sky (dropped); pixels on sharp depth edges ("flying pixels") dropped. Only sees what's in the photo (no behind-occluder content).
2. **Level conversion** — `pipeline/points_to_level.py` (shared by both paths):
   RANSAC ground plane → rotate to y-up → scale so camera height = 1.7 m (player eye) → 0.5 m grid →
   per cell: floor tile (points <0.5 m), solid column (wall/building, 95th pct height), or overhang slab
   (structure points all >2.2 m above a seen floor, e.g. roofs) → points below ground dropped (void: cliffs/clouds)
   → floor holes closed → **only the walkable area connected to the camera is kept** (+ buildings touching it;
   rejects clouds/backdrop) → specks <1 m² removed, heights median-smoothed → colours snapped to an 8-colour palette
   (in level.json) → 2D greedy box merge → invisible 3 m `Boundary_collider` walls round open edges →
   spawn = open cell (≥1 m clearance) nearest the camera, facing the play area → `level.glb`.
3. **Outputs** in `levels/<name>/`: `level.glb` (nodes Floor / Structures / Overhangs / Boundary_collider / Spawn_marker),
   `level.json` (spawn, facing −Z, sky colour, bounds, tri count), `topdown.png`, `depth.png`, `index.html`
   (three.js walk viewer: `?level=<dir>`; touch stick + drag look; orbit mode).

## Tuning knobs
`points_to_level.py --cell 0.5 --max-extent 80 --max-height 30`; `image_to_points.py --fov 60 --near 1.5 --far 200`.
Mobile budget: pagoda = 6.6k tris, 141 KB.

## Using in an engine
glb is metres, y-up. Unity/Godot/Unreal import directly; use mesh colliders on Floor+Structures.
Vertex colours only (no textures) — assign real materials per node when dressing.

## Known limits
Monocular depth scale is a guess; anything not connected to the walkable area is dropped (distant islands/backdrop);
thin things become 0.5 m blocks; no geometry behind occluders.
