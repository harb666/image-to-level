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
   - solid cells → greedy rectangle cover → **Building_NN** (group: `_Body`, `_Trim`, `_Roof` gable, `_Chimney`
     if big, `_Door` + up to 8 `_Window_NN` panels on the face that looks at the most walkable floor) if h > 3 m;
     **Tower_NN** (same but `_Spire` pyramid) if > 10 m, ≥ 1.6× footprint and near-square;
     **Wall_NN** if thin/low, **Platform_NN** if ≤ 1.6 m, **Prop_NN** cylinder if small, else **Block_NN**;
   - landmarks: compact raised point blobs on open floor (>1.5 m from buildings) → **Fountain_NN** (Basin, Water,
     Column, Bowl cylinders) if wide & < 3.5 m, else **Pillar_NN** cylinder;
   - **Overhang_NN** slabs (roofs/bridges over walkable floor, ≥ 1.5 m wide);
   - **Path_NN** thin slabs where floor material differs from the ground;
   - **Ground** flat slab over the play rectangle; **Terrain** heightfield (2 m cells): flat inside, cliff band
     (2–5 m) then fbm rolling hills outside; builder splits it: steep faces → `Terrain` (rock, flat-shaded),
     flat faces → `Terrain_Top` (`top_material`, grass, smooth); **Boundary_N/S/E/W** invisible collider walls;
   - material per object from colour (hue/sat/value → grass, sand, soil, cobblestone, concrete, plaster,
     stone_brick, wood, painted_wood, metal, rock, roof_tiles).
3. `pipeline/build_level.py` — level.json → glb. One node per object (children under parent groups), one shared
   PBR material per material type with a 256 px stylised procedural texture × colour, stored as JPEG; UVs in world
   metres / `tile_m` (no stretching when resized). Identical parts (same type+size+material, e.g. windows/doors)
   share one mesh (glTF instancing). Texture kinds: cobblestone, stone_brick, plaster, wood, painted_wood,
   trim_wood, door_wood, window, roof_tiles, roof_slate, metal, grass, rock, water, sand, soil, concrete. Writes `build_stats` (tris, objects, KB) into level.json, draws topdown.png.
   Supported object `type`s: `group`, `box`, `cylinder`, `roof` (gable along longer side), `ramp` (rises to +z),
   `stairs` (climbs to +z, 0.25 m steps), `panel` (flat quad facing +z, texture once —
   windows/doors/signs), `spire` (4-sided pyramid), `terrain` (+ optional `top_material`) (`heights` rows, `cell`), `boundary` (invisible).

## level.json schema (edit this to change the level)
- `objects[]`: `name`, `type`, `parent` (optional; position is then relative to parent), `position` = centre of the
  object's BASE [x,y,z] m, `rotation` = degrees [x,y,z], `size` = [width x, height y, depth z], `material`.
  Move a building → change its group `position`; resize → `_Body.size` (+ move `_Roof.position[1]` to new height).
- `materials{}`: name → `type` (texture pattern), `color` [r,g,b 0–1], `tile_m`. Adding a new name is fine.
- `spawn` {position, yaw_deg}, `bounds`, `walkable[]` rects {min[x,z], max[x,z], y}, `sky_color`, `build_stats`.
- Units: metres, y-up, -z = forward from spawn. Player eye 1.7 m.

## Mobile notes
Town square test: 129 objects, ~2.5k tris, 11 materials, ~255 KB glb. Engines: mark static & batch
(draw calls ≈ materials). Colliders: use Body/Wall/Platform/Ground boxes; Boundary_* are invisible (alpha 0).

## Lyra 2.0 (kept, not current priority)
`pipeline/lyra_stage.sh` / `gpu_run.sh`: image → Lyra video → 3DGS `reconstructed_scene.ply` (needs H100/A100 ≥43 GB,
untested). `make_level.sh` uses it when `LYRA_DIR` is set and `nvidia-smi` exists; the .ply feeds image_to_scene.py
the same way (output `levels/<name>-lyra/`). `points_to_level.py` main() = old blocky voxel export (legacy).

## Known limits
Depth scale is a guess; building detail is a fixed recipe (door/windows/trim), not read from the image; small props
< 1 m² are lost; arches/bridges not specially detected; anything not connected to the walkable area is dropped; material guess is colour-only.
