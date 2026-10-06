# Image → editable level pipeline (read this first; don't re-scan the repo or Lyra)

Concept image (e.g. AI-generated) → **editable scene description** (`level.json`) → textured low-poly `level.glb`.
Not a photo scan: the depth estimate is only spatial guidance for placing clean, named primitives.

## Commands
```
./make_level.sh inputs/<image>.png [name]        # full run -> levels/<name>/   (~10 s, CPU)
python3 pipeline/build_level.py levels/<name>    # rebuild glb after editing level.json (~1 s)
```
Outputs: `level.json` (THE source of truth — edit this), `level.glb`, `topdown.png` (footprints, red = invisible
boundary, blue dot = spawn), `depth.png`, `reference.*`, `index.html` (three.js walk viewer; touch stick + drag).

## Stages
1. `pipeline/image_to_points.py` — MiDaS-small depth (CPU) → camera-space points. Sky = far pixels connected to the
   image top; depth-edge "flying pixels" dropped. (Lyra 2.0 .ply can replace this; see Lyra section.)
2. `pipeline/image_to_scene.py` — uses `analyse()` from `points_to_level.py` (ground plane RANSAC, 1.7 m eye-height
   scale, grid rotated to the main floor direction, 0.5 m cells: floor / solid / overhang masks, heights, colours,
   play area connected to the camera, spawn). Then:
   - facades extruded up to 6 m away from the floor into building mass;
   - solid cells → greedy rectangle cover → **Building_NN** (group: `_Body` box + `_Roof` gable) if h > 3 m,
     **Wall_NN** if thin/low, **Platform_NN** if ≤ 1.6 m, **Prop_NN** cylinder if small, else **Block_NN**;
   - **Overhang_NN** slabs (roofs/bridges over walkable floor, ≥ 1.5 m wide);
   - **Path_NN** thin slabs where floor material differs from the ground;
   - **Ground** flat slab over the play rectangle; **Terrain** heightfield (2 m cells): flat inside, rock hills
     rising outside as the visible boundary; **Boundary_N/S/E/W** invisible collider walls;
   - material per object from colour (hue/sat/value → grass, sand, soil, cobblestone, concrete, plaster,
     stone_brick, wood, painted_wood, metal, rock, roof_tiles).
3. `pipeline/build_level.py` — level.json → glb. One node per object (children under parent groups), one shared
   PBR material per material type with a 128 px procedural tileable texture × colour; UVs in world metres / `tile_m`
   (no stretching when resized). Writes `build_stats` (tris, objects, KB) into level.json, draws topdown.png.
   Supported object `type`s: `group`, `box`, `cylinder`, `roof` (gable along longer side), `ramp` (rises to +z),
   `stairs` (climbs to +z, 0.25 m steps), `terrain` (`heights` rows, `cell`), `boundary` (invisible).

## level.json schema (edit this to change the level)
- `objects[]`: `name`, `type`, `parent` (optional; position is then relative to parent), `position` = centre of the
  object's BASE [x,y,z] m, `rotation` = degrees [x,y,z], `size` = [width x, height y, depth z], `material`.
  Move a building → change its group `position`; resize → `_Body.size` (+ move `_Roof.position[1]` to new height).
- `materials{}`: name → `type` (texture pattern), `color` [r,g,b 0–1], `tile_m`. Adding a new name is fine.
- `spawn` {position, yaw_deg}, `bounds`, `walkable[]` rects {min[x,z], max[x,z], y}, `sky_color`, `build_stats`.
- Units: metres, y-up, -z = forward from spawn. Player eye 1.7 m.

## Mobile notes
Town square test: 42 objects, ~2k tris, 5–6 materials/textures, ~200 KB glb. Engines: mark static & batch
(draw calls ≈ materials). Colliders: use Body/Wall/Platform/Ground boxes; Boundary_* are invisible (alpha 0).

## Lyra 2.0 (kept, not current priority)
`pipeline/lyra_stage.sh` / `gpu_run.sh`: image → Lyra video → 3DGS `reconstructed_scene.ply` (needs H100/A100 ≥43 GB,
untested). `make_level.sh` uses it when `LYRA_DIR` is set and `nvidia-smi` exists; the .ply feeds image_to_scene.py
the same way (output `levels/<name>-lyra/`). `points_to_level.py` main() = old blocky voxel export (legacy).

## Known limits
Depth scale is a guess; buildings are boxes + gable roofs (no windows/detail); small features (fountains, props
< 1 m²) are often lost; anything not connected to the walkable area is dropped; material guess is colour-only.
