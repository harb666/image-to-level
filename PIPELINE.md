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
   glTF PBR material per level.json material; UVs in world metres / `tile_m` (no stretching when resized). Identical
   parts (same type+size+material) share one mesh. After export `glb_tools.dedupe_images` merges identical images
   and repacks the binary. Writes `build_stats` (tris, nodes, draw-call + texture-memory ESTIMATES) into level.json,
   draws topdown.png. Object `type`s: `group`, `box`, `cylinder` (+`sections`), `roof`, `spire`, `ramp` (rises to +z),
   `stairs` (+z, 0.25 m steps), `panel` (flat quad facing +z, texture once), `terrain` (+`top_material`), `boundary`.

## Materials (Stage 1) — `pipeline/materials.py`
Each level.json material → base colour (jpeg, sRGB) + normal map (from a procedural height field) + ORM image
(R=AO, G=roughness, B=metallic; used for both glTF metallicRoughness and occlusion) + emissive mask if it glows.
All tileable, CPU-generated, deterministic. Standard glTF 2.0 PBR → Godot 4 StandardMaterial3D on import (Godot
re-compresses textures to GPU formats per its import settings; no KTX2 encoder is available here yet — see PLAN.md).
- Material fields: `type`, `color`, `tile_m`, optional `res` (px; defaults 512 for big hero surfaces
  industrial_metal/painted/damaged/scifi_floor/rock, 256 others, 128 glow — use 128 for distant objects),
  `emissive` [r,g,b] factor, `accent` [r,g,b] light colour (machinery_panel, trim_light), `wear` 0..1.
- PBR kinds: industrial_metal, painted_metal, damaged_metal, scifi_floor, grating (perforated), concrete, rock, sand,
  dirt, grass, toxic (emissive), glow (emissive tube), machinery_panel (red indicator + white light slots),
  trim_light (red light lines + white lamps, use `tile_m` 1.2 on 0.6 m trims), pipe (rings + bolts), banner.
  Old names alias: industrial_wall→industrial_metal, platform_side→machinery_panel, floor_plate→scifi_floor,
  grate→grating, pipe_metal→pipe, red_panel→banner. Legacy stylised kinds (town square) still work and get
  albedo-derived normals/roughness.
- Dark coated metal uses low metalness (0.35, bare worn edges higher): fully metallic dark albedo renders black.
- `python3 pipeline/material_swatches.py out.png [level.json]` → contact sheet (base | normal | ORM | emissive).
- `python3 pipeline/glb_stats.py level.glb` → size, tris, nodes, draw calls (unbatched / per-material min),
  images, texture memory (uncompressed RGBA8+mips vs ~1 B/px GPU-compressed). Estimates, not device benchmarks.

## Sky & distant environment (Stage 2) — optional `environment` section in level.json
Levels without it behave exactly as before. With it, `build_level.py` also writes (or run only
`python3 pipeline/environment.py levels/<name>` — rebuilds sky/background/metadata in ~1 s, level.glb untouched):
- `sky/panorama.jpg` — 2:1 equirect, procedural & seamless (`pipeline/sky.py`, every pixel from its view direction;
  perspective cloud layers, horizon smog band, sun/moon glow, stars, alien planet, factory glows on the horizon).
  Cached: only re-rendered when sky inputs change. External panorama: `"sky": {"image": "my_pano.jpg"}`.
  Presets: industrial_smog, sunset, sunrise, night, overcast, alien, clear_day (override any field:
  zenith/upper/horizon/below colours, clouds{coverage,scale,dark,lit,layers,wisps}, smog{strength,color,height_deg},
  sun{azimuth_deg,elevation_deg,color,size_deg,glow}, stars, planet, light{sun_energy,sun_color,ambient_energy,exposure}).
- `background.glb` — distant scenery (`pipeline/backdrop.py`), one node `BG_<id>` per layer under `Background`, no collision.
  Layer types (each deterministic from its `id`+`seed`, editable independently):
  `ground` (terrain skirt under the arena to the horizon, rim drops below ground), `mountain_ring` (closed 360° ridge:
  radius, depth, height[min,max], frequency, sharpness), `spires` (radius[min,max], count, height, azimuth_deg range),
  `skyline` (radius, azimuth_deg[from,to], count, height, glow, lit), `factory` (azimuth_deg, distance, scale, seed,
  glow [r,g,b] → also adds a horizon glow to the sky). Common: `fade` 0..1 (atmospheric perspective baked into the colour),
  `color`, `material_type`, `tile_m`, `res`. Azimuth: 0 = north (-z), 90 = east (+x).
- `environment.json` — engine-neutral settings: sky file/projection, sun (direction, colour, energy, Godot rotation),
  ambient (sky), fog (colour = sky horizon colour so geometry blends into the sky; start/end for linear fog, Godot
  exponential density ≈ 3/end, height fog), tonemap, glow, adjustments, camera far, background layer list + stats.
- `environment.tres` — Godot 4 Environment (Sky → PanoramaSkyMaterial, ambient/reflections from sky, filmic tonemap,
  glow, fog, adjustments). Assumes the level folder is at `res://levels/<name>/`. Generated, NOT tested in Godot here;
  the browser preview approximates it (no bloom/post-processing, linear fog). If the sky looks rotated against the
  sun in Godot, adjust the Environment's sky rotation in 90° steps.
- `"atmosphere"`: fog_start, fog_end, fog_color (default: sky horizon), sky_affect, height_fog{height,density},
  tonemap, exposure, contrast, saturation, brightness, glow{enabled,intensity,bloom,hdr_threshold}; `"lighting"` overrides
  the preset's light; `"horizon_distance"` (m).
- `"quality"`: performance | balanced (default) | quality →
  sky 1024/2048/4096 px, ring segments 48/96/160, background density ×0.6/1/1.4, factory detail 0/1/2,
  background texture 64/128/256 px, camera far 600/800/1000.
- Check: `python3 pipeline/check_background.py levels/<name>` → rays from spawn + every walkable area at third-person
  and elevated camera heights, 5° steps, below the horizon must all hit geometry (no void); horizon silhouette coverage;
  open edges above ground per background mesh. Writes `checks/background_check.json`.
- Viewer: panorama sky as background + image-based lighting, fog in the horizon colour, background layer, and a
  third-person camera (default; orbits 5 m from the player, pulls in at visible walls) / 1st person / orbit.

## Hand-authored layouts (concept sheets with a top-down plan)
When a concept sheet has a TOP DOWN LAYOUT/side view, don't run it through MiDaS: write a small layout script in
`pipeline/layouts/<level>.py` that emits level.json directly (same schema), then `build_level.py`. Example:
`pipeline/layouts/toxic_arena.py` → `levels/toxic_arena` (square arena shooter: HazardFluid, Central_Platform/Tower,
Platform_<dir>_01 groups (_Base/_Floor/_Trim/_Light/_Cover), Bridge_*, Ramp_*, Stairs_*, Walkway_*, OuterWall_*,
Pipe_* + _Fall, PipeRun_*, Banner_*, Background_Block_*). Materials may set `"emissive": [r,g,b]` (glow);
cylinders may set `"sections"` (8 = octagon). level.json `hazards[]` lists kill volumes (viewer respawns on contact).
Materials: see Materials section (Toxic Arena uses industrial_metal, trim_light, grating, machinery_panel, scifi_floor, pipe, toxic, glow, banner).

## level.json schema (edit this to change the level)
- `objects[]`: `name`, `type`, `parent` (optional; position is then relative to parent), `position` = centre of the
  object's BASE [x,y,z] m, `rotation` = degrees [x,y,z], `size` = [width x, height y, depth z], `material`.
  Move a building → change its group `position`; resize → `_Body.size` (+ move `_Roof.position[1]` to new height).
- `materials{}`: name → `type` (texture pattern), `color` [r,g,b 0–1], `tile_m`. Adding a new name is fine.
- `spawn` {position, yaw_deg}, `bounds`, `walkable[]` rects {min[x,z], max[x,z], y}, `sky_color`, `build_stats`.
- Units: metres, y-up, -z = forward from spawn. Player eye 1.7 m.

## Shareable preview
`python3 pipeline/make_preview.py levels/<name> "Title" out.html` → one self-contained page (level + background glb, sky, environment, every PBR map as data: URIs;
sandboxed pages block the blob: URLs GLTFLoader uses for .glb textures, which renders everything black).

## Mobile notes
Toxic Arena after Stage 2: playable level unchanged — 1,948 tris, 347 KB glb, 10 materials / 34 images, 137 draw calls unbatched (10 min if
batched by material), est. texture memory 3.9 MB GPU-compressed (15.6 MB uncompressed); plus background.glb 413 KB,
6.8k tris, 9 draw calls, ~0.35 MB textures; sky 56 KB jpeg (~2.7 MB GPU-compressed at 2048x1024). Town square: 2.5k tris, 483 KB. Engines: mark static & batch
(draw calls ≈ materials). Colliders: use Body/Wall/Platform/Ground boxes; Boundary_* are invisible (alpha 0).

## Lyra 2.0 (kept, not current priority)
`pipeline/lyra_stage.sh` / `gpu_run.sh`: image → Lyra video → 3DGS `reconstructed_scene.ply` (needs H100/A100 ≥43 GB,
untested). `make_level.sh` uses it when `LYRA_DIR` is set and `nvidia-smi` exists; the .ply feeds image_to_scene.py
the same way (output `levels/<name>-lyra/`). `points_to_level.py` main() = old blocky voxel export (legacy).

## Known limits
Depth scale is a guess; building detail is a fixed recipe (door/windows/trim), not read from the image; small props
< 1 m² are lost; arches/bridges not specially detected; anything not connected to the walkable area is dropped; material guess is colour-only.
