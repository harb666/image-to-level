# Image → editable level pipeline (read this first; don't re-scan the repo or Lyra)

Concept image (e.g. AI-generated) → **editable scene description** (`level.json`) → textured low-poly `level.glb`.
Not a photo scan: the depth estimate is only spatial guidance for placing clean, named primitives.

## Commands
```
./make_level.sh inputs/<image>.png [name]        # full run -> levels/<name>/   (~10 s, CPU)
python3 pipeline/build_level.py levels/<name>    # rebuild glb after editing level.json (~1 s)
python3 pipeline/edit_level.py levels/<name> <command> ...   # targeted, undoable edit by object name + minimal rebuild
```
iPhone workflow + plain-English edit recipes: **IPHONE.md**.
**Stage 7 (recommended route for concept art):** Claude reads the image(s) -> `levels/<name>/scene_spec.json` -> 
`python3 pipeline/generate.py levels/<name>/scene_spec.json` (build + bounded refine + renders + previews + package).
Runbook: **GENERATE.md** · spec format: **SCENE_SPEC.md** · Godot import: **GODOT_IMPORT.md** · tests: `python3 tests/run_all.py`.
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

## Geometry & camera completeness (Stage 3)
- **New object types** (`pipeline/shapes.py`, all closed meshes, base at y=0, `size` = [w, h, d]):
  `railing` (posts + 2 rails along x), `ibeam` (girder along x), `rock` (+`seed`), `cliff` (jagged rock wall along x,
  +`seed`), `arch` (gate/tunnel along z; `opening`, `opening_h` fractions; passable), `pipe_elbow` (90° bend, w = pipe
  diameter, h = bend radius), `vent` (louvred box), `tank` (domed cylinder), `machinery` (+`seed` cluster).
  `box` + `"bevel": m` = chamfered edges. `bevel` can be set on a MATERIAL (applies to every box using it) or per object.
  Per object `"double_sided": true` (material variant with glTF doubleSided). Terrain heightfields get a vertical
  `skirt` (default 6 m; `"skirt": 0` disables) so their edges/undersides are never exposed.
- **Prefabs** (`pipeline/prefabs.py`) expand into named, editable children:
  `catwalk(name, start, end, width, rails, supports)`, `railing_along(name, start, end)`, `pipe_run(name, points, radius)`,
  `rock_cluster(name, center, radius, count, seed)`, `gate(name, position, yaw, width, height, depth)`, `machinery_bank(...)`.
  CLI: `python3 pipeline/prefabs.py levels/<name> add catwalk '{"name":"Catwalk_02","start":[x,y,z],"end":[x,y,z]}'`
  (adds missing `pf_*` default materials), then build + validate. `... list` shows prefabs.
- **Validator** `python3 pipeline/validate_level.py levels/<name> [--fix]` (~45 s for Toxic Arena):
  player samples over every walkable area (skips points inside solids or < 0.4 m from walls), third-person camera at
  5 m (8 yaws × 3 heights) with a 0.25 m spring arm (5 rays, stops 0.3 m before geometry, half-distance when very close —
  same rule as the viewer), ~88-ray frustum per camera. Reports `void_rays` (below-horizon rays hitting nothing, incl.
  background.glb), `back_face` (back of a single-sided surface visible; wall-mounted panels are exempt; hits confirmed
  with perturbed rays, front face wins ties), `open_mesh` (visible holes), `camera_inside`. Writes `checks/validation.json`.
  `--fix` (safe only, never inside walkable space): `double_sided` on objects whose back shows; void → adds/extends
  environment `AutoFix_Ground` skirt + `AutoFix_Horizon` mountain ring; rebuilds and re-validates. Fixed objects get an
  `"autofix"` reason. Intentional openings: `"validation": {"ignore_objects": [...], "allow_void": true}`.
- Test fixture: `pipeline/layouts/test_primitives.py` → `levels/test_primitives` (every primitive/prefab; ships in its
  auto-fixed state; regenerate it to see the two deliberate faults).

## Environmental effects (Stage 4) — optional `effects` list in level.json
GLB = static appearance only (textures/emissive "frame 0"); NO animation, particles or fog survive in a GLB.
`build_level.py` (or `python3 pipeline/effects.py levels/<name>`, seconds) writes:
- `effects.json` — engine-neutral, authoritative: per effect id/type/category, resolved world-space `targets` (node
  names) / `emitters` (points with radius) / `area`, `material_tile_m` for UV-scroll speeds, per-quality
  (performance/balanced/quality) `enabled` + params + cost estimate (particles alive, emitters, extra draw calls,
  transparent overdraw m²), `merge_emitters` (continuous multi-point effects = ONE particle system), totals.
- `fx/*.png` — 4 tiny white-alpha sprites (puff, mote, spark, bubble), tinted at runtime.
- `fx/godot/` — Godot 4 starter kit (UNTESTED in Godot here): `liquid_surface.gdshader`, `liquid_flow.gdshader`,
  `fog_sheet.gdshader`, `apply_effects.gd` (CPUParticles3D, ShaderMaterial overrides, emission pulses, sky drift), README.
Effect types (defaults in `pipeline/effects.py` TYPES; override any param per effect, `"enabled": false` to disable):
  surface shaders `liquid_surface` (scroll, swirl, pulse), `liquid_flow` (speed m/s, wobble);
  material animation `pulse_light` (speed Hz, amount, phase), `flicker` (rate, amount);
  particles `bubbles`, `splash` (kill_below_spawn), `steam`, `smoke`, `sparks` (burst + interval), `ambient_particles` (count);
  `fog_sheet` (low mist plane; volumetric fog isn't available in Godot Mobile/Compatibility); `sky_drift` (Godot only).
Placement: `target`, `targets_glob`, `target_material`, `area_from` (node's top surface), `area`, `at_targets_glob` +
`anchor` bottom/top/center (spawns on a disc around the node), `positions`, `at_background: "factory_chimneys"`
(chimney tops from environment.json). Viewer: "FX" button cycles off/performance/balanced/quality (approximation).

## Mobile export (Stage 5) — `levels/<name>/mobile/` (rebuilt by every build; or `python3 pipeline/export_mobile.py levels/<name> [--profile performance|balanced|quality]`)
level.json stays the editable master; `level.glb` stays the dev export (one node per object). Mobile export:
- `level_mobile.glb`: static meshes merged by material inside spatial cells (cell 64/48/32 m for performance/balanced/
  quality: big enough to cut draw calls, small enough for frustum culling); small props (< 2 m) merged into separate
  `_props` cells with a visibility range (45/70/110 m); vertices welded (flat shading kept). Kept separate: hazards,
  per-node effect targets (each shader effect's targets merged into ONE `FX_<effect id>` node), objects with
  `"mobile": {"merge": false}`. Faces entirely under opaque hazard liquid removed (`"mobile": {"cull_below_y": y}` to
  override). Original JPEG bytes restored after the round-trip; textures capped at 256/512/1024 px. Node `extras` list
  the source objects (also in the manifest) so edits still target level.json names.
- `background_mobile.glb` (textures capped 64/128/256), `effects_mobile.json` (targets renamed to merged nodes).
- `collision.json`: world-space colliders from level.json SHAPES (not render meshes): boxes (box/railing/ibeam/boundary),
  cylinders, convex hulls (rock/cliff/tank/machinery/...; ≤ 32 points), stairs → ramp, arch → 2 piers + lintel (opening
  stays passable), terrain → heightmap; panels excluded; `"collision": false` per object. Hazards (+ any object using a
  hazard's material, e.g. toxic falls) → `hazards` areas. `collision.glb`: same as `*-convcolonly` / `*-colonly` nodes.
- `mobile_manifest.json`: per node kind/material/triangles/source objects/visibility_range_end/cast_shadow, Godot settings
  (ETC2/ASTC VRAM compression, LOD generation, mobile shadow settings), metrics. `apply_mobile.gd`: Godot starter (UNTESTED).
- Metrics: dev vs mobile file stats + ESTIMATED visible draw calls/triangles from 80 sampled third-person cameras
  (frustum + distance culling, iPhone 19.5:9, background included). No device benchmarks here.
- `validate_level.py levels/<name> --mobile` checks the mobile build; `make_preview.py ... --mobile` previews it.
- KTX2/Basis not used (Godot re-compresses on import; the sandboxed preview can't fetch a transcoder).

## iPhone editing & preview (Stage 6)
**Editing** — `pipeline/edit_level.py levels/<name> <command>` (full list: run it without arguments). level.json stays the
master; objects are addressed by their stable `name` (or a glob); only the touched fields change; every edit snapshots
the previous level.json to `levels/<name>/.history/` (last 30, git-ignored) → `undo`, `history`. Commands: list, info,
set (dotted keys `size.0=12`), move, resize (groups scale children's offsets + sizes), material, mat (create/edit a
material; type checked), remove (with children; effects targeting it disabled, hazards cleaned), duplicate (deep copy;
the clone joins its source's glob effects, e.g. a duplicated toxic fall flows + splashes), rename (children, parents,
effects, hazards, validation updated), add (JSON object), prefab (Stage 3 prefabs), env (sky/atmosphere/quality;
background layers by id: `background.Mountains_Far.height=[110,240]`), fx / fx-add / fx-remove, undo, history.
Minimal rebuild: env edits → environment + effects + mobile (~6 s; a NEW sky preset renders the panorama once: ~25 s for that edit, was ~60 s
at 2048 px, then cached); fx edits → effects + mobile (~5 s); geometry/material → full build (~6 s for Toxic Arena, incl.
mobile export). `--no-build` to batch several edits, `--validate` to run the camera validator after. Effect globs
(`targets_glob`, `at_targets_glob`) may be a list.
**Viewer** (`index.html` / previews; three.js, NOT Godot): view modes 3rd person (spring arm) / 1st person / orbit /
free cam (stick + drag look + ▲▼) / top-down (one-finger pan, pinch zoom); tap an object → bottom sheet with name, type,
parent, position/size/rotation, material (swatch, type, tile, glow, texture thumbnail), triangles, "merged into" for
mobile-merged nodes (resolved to the source object via node extras `source_bounds`), highlight box, **Copy for Claude**
(one-line reference to paste into chat); 📷 screenshot (shown full screen: long-press → Save to Photos); quality
low/med/high (pixel ratio + FX density, remembered); stats (draw calls/tris/fps of the BROWSER renderer).

## Image -> level generation & autonomous refinement (Stage 7)
Split of responsibilities: **Claude** interprets the references (with measuring helpers) and writes a structured
`scene_spec.json` (layout, heights, structures, materials, atmosphere, each element tagged visible/inferred); the
**CPU pipeline** turns it into a validated, previewed, packaged level deterministically. No vision model, no paid API.
- `references.py` split (concept sheets -> panels via XY-cut on gutters), plan (top-down colour regions -> metres),
  grid (measurement overlays). Measures only; Claude decides meanings.
- `scene_spec.py` schema + cross-reference validation (readable errors with JSON paths; unknown keys = warnings).
- `architecture.py` reusable modules: arena (hazard/ground/deck floor, walls with openings, walkway ring, invisible
  boundary), platforms (industrial_pillar / stone_plinth / plain; rect/octagon/circle), connections (bridge, catwalk,
  ramp, sloped elevated bridge, stairs + support, jump), structures (industrial tower/building, town house with timber
  framing + jetties + gable/hip roof, stone tower with battlements/pinnacles/spire, fountain, round/square gate, wall,
  machinery, tank, pillar, lamp, crates, rocks, tree, banner), pipe outlets with pours + pipe runs. Material ROLES ->
  theme palettes (industrial, toxic_industrial, scifi, medieval_town, ruins) + per-role overrides + shared `_v2`
  variants. New Stage 3 shapes: hip_roof, round_arch, battlement, wedge.
- `spec_to_level.py` assembly + environment/background scaled to the arena + auto effects + spawns + walkable areas;
  regeneration MERGES with manual edits via `gen_state.json` hashes (edited/deleted/added kept; undoable).
- `gameplay.py` + `config/gameplay.json` (PLACEHOLDER player/camera numbers, budgets): Recast-like span heightfield
  from level.glb -> walk components (step/slope/headroom/radius erosion) + drop/jump links -> reachability from the spawn,
  one-way traps, unreachable intended areas, spawn safety, narrow connectors, low ceilings; `checks/navigation.png`.
  The camera validator, viewer and renders read the same config.
- `checks.py` one report (schema/transforms/materials/references, assets parse, triangles per object, measured
  sizes/draw calls + ESTIMATED visible draw calls/GPU memory vs budgets, navigation, camera completeness, render errors)
  -> `checks/report.json/.md`, issues sorted by impact with world positions (viewer overlay).
- `render_views.py` real headless renders (Chromium + SwiftShader, three.js from pipeline/render/node_modules):
  bird's-eye, overviews, third-person spawn, 4 compass views at player height, main platforms, 4 background-facing,
  tallest structure -> `checks/views/contact_sheet.jpg`. Fails loudly if no browser - never fabricated.
- `refine.py` bounded loop (max passes): checks -> safe automatic fixes (double-sided/ground skirt, spawn relocation to
  navigation candidates, connect unreachable platforms, remove duplicates, rebuild) -> rebuild; remaining issues go to
  `needs_claude`. Claude then reviews renders and applies targeted edits.
- `edit_level.py` + `connect` (bridge/ramp/stairs between areas) + `apply` (schema-checked batch ops); every edit is
  schema-validated before saving.
- `package.py` Construct Error / Godot 4 package mirroring `res://levels/<name>/` (level.json, glbs, mobile, collision,
  sky/background/environment.tres, effects + Godot kit, gameplay/spawns.json + hazards.json + navigation.json,
  level_manifest.json with sha1s, IMPORT_GODOT.md) + `--check` validation; `dist/<name>/<name>.zip`.
- Viewer: jump button, gameplay-config camera/player, scripted inspection camera, issues overlay (markers + list + "Copy
  for Claude"). `make_preview.py` embeds GAMEPLAY + ISSUES.
- Tests: `tests/` (unittest; Stages 1-6 regression + Stage 7; `QUICK=1` skips slow ones).
Real-image runs: `levels/toxic_arena_gen` (multi-panel concept sheet: plan + elevation + perspective + details) and
`levels/town_square_gen` (single perspective image). Both specs, renders and reports are committed.

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
`python3 pipeline/make_preview.py levels/<name> "Title" out.html` → one self-contained page (level + background glb, sky, environment, effects + sprites, every PBR map as data: URIs;
sandboxed pages block the blob: URLs GLTFLoader uses for .glb textures, which renders everything black).

## Mobile notes
Toxic Arena MOBILE (balanced): 429 KB (incl. 17 KB tap-to-identify extras), 3,364 tris, 51 nodes, 50 draw calls (est. ~39 visible per frame incl. background,
vs ~69 dev), 92 colliders + 9 hazard areas (52 KB), +10 effect draw calls / ~911 particles.
Toxic Arena dev export: 3,676 tris, 390 KB glb, 10 materials / 34 images, 137 draw calls unbatched (10 min if
batched by material), est. texture memory 3.9 MB GPU-compressed (15.6 MB uncompressed); plus background.glb 413 KB,
6.8k tris, 9 draw calls, ~0.35 MB textures; sky 56 KB jpeg (~2.7 MB GPU-compressed at 2048x1024). Town square: 2.5k tris, 483 KB. Engines: mark static & batch
(draw calls ≈ materials). Colliders: use Body/Wall/Platform/Ground boxes; Boundary_* are invisible (alpha 0).

## Lyra 2.0 (kept, not current priority)
`pipeline/lyra_stage.sh` / `gpu_run.sh`: image → Lyra video → 3DGS `reconstructed_scene.ply` (needs H100/A100 ≥43 GB,
untested). `make_level.sh` uses it when `LYRA_DIR` is set and `nvidia-smi` exists; the .ply feeds image_to_scene.py
the same way (output `levels/<name>-lyra/`). `points_to_level.py` main() = old blocky voxel export (legacy).

## Known limits
Stage 7: the scene spec is Claude's interpretation - single perspective images leave depth uncertain; arbitrary
architecture is approximated with the module library (extend architecture.py for new forms); jump arcs are approximated;
renders are the three.js preview (SwiftShader), not Godot; Godot scripts/.tres untested here; gameplay numbers are
placeholders until Construct Error's are supplied.
Depth scale is a guess; building detail is a fixed recipe (door/windows/trim), not read from the image; small props
< 1 m² are lost; arches/bridges not specially detected; anything not connected to the walkable area is dropped; material guess is colour-only.
