# Upgrade plan (Construct Error environment generator)

Architecture stays: concept image → `level.json` (editable master) → `build_level.py` → `level.glb` (+ previews).
Each stage is tested on **Toxic Arena** (benchmark), metrics recorded with `pipeline/glb_stats.py`, PIPELINE.md updated,
committed, then paused for approval.

| Stage | Scope | Key outputs |
|---|---|---|
| 1 Materials & textures ✅ | `pipeline/materials.py` PBR library: base colour, normal, ORM (AO/roughness/metal), emissive mask; per-material resolution; legacy kinds keep working; viewer renders full PBR | richer surfaces at similar size |
| 2 Sky & distant scenery ✅ | panoramic sky (CPU-painted equirect, jpeg), horizon haze, lightweight backdrop cards/rings (mountains, factory skylines) in level.json `sky` / `backdrop` | world feels larger, no extra gameplay geometry |
| 3 Geometry & camera completeness ✅ | bevelled/modular primitives (railings, catwalk, machinery, rocks), `validate_level.py`: sample camera-reachable viewpoints (3rd-person orbit), raycast for exposed backs/void/gaps, auto-fill with perimeter/skirt geometry, report | no exposed edges from any reachable camera |
| 4 Effects metadata ✅ | `effects[]` in level.json (toxic flow, bubbles, steam, sparks, pulsing lights, fog) + viewer preview; export sidecar `effects.json` for Godot (GLB carries only static emissive) | Godot-recreatable VFX |
| 5 Mobile performance ✅ | dev vs mobile export: merge static meshes by material (names kept in node extras/level.json), LOD for big objects, collision proxies, texture atlas for small emissive/decals, KTX2 if a free encoder is available (else rely on Godot VRAM compression) | fewer draw calls, measured budgets |
| 6 iPhone editing & preview ✅ | third-person + free camera + top-down, tap-to-identify object (name/material), screenshot button, quality toggle, edit-by-name helper | full phone workflow |
| 7 Image → level generation & autonomous refinement ✅ | references.py (panels/plan/grid) → Claude writes scene_spec.json → generate.py: spec_to_level (architecture modules, role materials, auto environment/effects/spawns, edit-preserving regeneration) → build → refine loop (checks.py + navigation + camera, safe fixes, bounded) → headless renders → previews → Godot package | one command from interpretation to validated, packaged level |
| 9 Universal terrain & environment generation ✅ | structured / open / hybrid modes; deterministic feature terrain (terrain.py) in crack-free chunks with LODs, biome material layers, rivers/roads/pads/water; natural + urban + connector modules in a pluggable registry; instanced scatter in 5 styles; near/middle/far continuity with an organic boundary + natural barrier; spawn regions; mobile LOD/collision export; world validation + safe repairs; viewer terrain inspection | any environment type from one spec, editable by feature id |
| 8 Intelligent geometry, connections & environment validation ✅ | anchors + relations scene graph, connection-aware construction rules (junction plates, flush ramps/stairs, no coplanar overlaps, cover clear of landings, party walls, grounded terrain props), liquid streams from real outlets (5 outlet types), geometry validator (ERROR/WARNING/INTENTIONAL), safe deterministic repair, inspection close-ups | physically coherent levels in any theme |

Not possible on free CPU infra: real device GPU benchmarks (numbers are estimates), neural texture/sky generation at
quality (procedural fallback instead).

## Status
- Stage 1 ✅ PBR material library (materials.py), glb image dedupe, glb_stats, swatches. Toxic Arena 347 KB / 1,948 tris.
- Stage 2 ✅ sky.py (7 presets, seamless, cached, external import), backdrop.py (ground skirt, mountain rings, spires,
  skyline, factories), environment.py (background.glb, environment.json, environment.tres, quality presets),
  check_background.py, viewer sky/fog/3rd-person camera. Toxic Arena demo: background 413 KB, 6.8k tris, 9 draw calls;
  sky 56 KB. Void rays 0 / 10,080; open edges 0. Not yet verified in Godot (browser preview only).
- Stage 3 ✅ shapes.py (bevel box, railing, ibeam, rock, cliff, arch, pipe_elbow, vent, tank, machinery), prefabs.py
  (catwalk, railing_along, pipe_run, rock_cluster, gate, machinery_bank + CLI), terrain skirts, double_sided objects,
  validate_level.py (third-person spring-arm camera simulation, void/back-face/open-mesh, --fix). Viewer camera uses the
  same spring arm. Toxic Arena: visual bevels only (3,676 tris, 390 KB, draw calls unchanged 137/10), validation passed
  (1,080 cameras, 95k rays, 0 issues). Fixture: void + one-sided sign detected and auto-fixed.
- Stage 4 ✅ effects.py (12 effect types, placement by node/glob/material/area/chimneys, per-quality params + cost
  estimates, merged emitters), effects.json, fx sprites, Godot kit (3 shaders + apply_effects.gd, untested in Godot),
  viewer FX preview + quality button. Toxic Arena: 13 effects; balanced ≈ 911 particles, 10 extra draw calls (est.),
  5,184 m² mist overdraw; performance ≈ 293 particles, no mist. level.glb unchanged (390 KB / 3,676 tris).
- Stage 5 ✅ export_mobile.py: cell+material merging (props separate with visibility ranges), FX targets merged per effect,
  hidden-face removal under hazard liquid, texture caps per profile, lossless JPEG restore, node extras/merge map,
  collision.json/.glb (primitive colliders, stairs→ramps, hazard areas), mobile_manifest.json + apply_mobile.gd, metrics
  incl. estimated visible draw calls. Toxic Arena balanced: draw calls 137 → 50, est. visible ~69 → ~39, 92 colliders;
  validated (0 issues) and visually identical in preview (mean pixel diff 0.05/255). Town square 117 → 29 draw calls.
- Stage 6 ✅ edit_level.py (targeted, undoable edits by stable name; minimal rebuild scopes), viewer: 3rd/1st person,
  orbit, free cam, top-down, tap-to-identify (incl. merged mobile nodes) + material inspector + "Copy for Claude",
  screenshot overlay, quality + stats; IPHONE.md recipes. Tested on a scratch copy of Toxic Arena (committed arena
  unchanged): wider central platform, alien sky, taller mountains, metal-grate north wall, new rusted material,
  duplicated pipe + toxic fall (joined flow/splash/steam effects), north-wall pipe run, rename, remove; validation
  passed (0 issues); undo chain restored the original level.json exactly. Rebuild ~5–7 s per edit (a new sky preset
  ~25 s once, was ~60 s: sky render 2–3× faster, identical output). Mobile GLB +17 KB for tap-to-identify bounds.

### Stage 7 milestones (implemented in order)
1. Gameplay config (`config/gameplay.json`, placeholders) + navigation/reachability analysis (`gameplay.py`).
2. Scene spec schema (`scene_spec.py`, SCENE_SPEC.md) + architecture modules (`architecture.py`) + new shapes (hip roof,
   round arch, battlements, wedge) + assembler with edit-preserving regeneration (`spec_to_level.py`).
3. Reference helpers (`references.py`: panel split, plan regions in metres, measuring grid).
4. Aggregate checks (`checks.py`), headless renders (`render_views.py`), viewer jump / inspection camera / issues overlay.
5. Bounded refine loop (`refine.py`), structured edits (`edit_level.py connect/apply` + schema check), Godot package
   (`package.py`, GODOT_IMPORT.md), one command (`generate.py`), Claude runbook (GENERATE.md).
6. Tests (`tests/`, 28 cases, all passing; `QUICK=1` skips slow ones) + real-image runs + docs.

## Stage 7 status
- Stages 1–6 re-verified: all four existing levels rebuild with byte-identical level.glb; camera validator unchanged on
  Toxic Arena (1,080 cameras, 0 issues); regression tests for materials, sky, background, shapes, build, mobile, edits,
  preview.
- Multi-view test (real image, `inputs/toxic_arena_concept.png`, 7 panels found automatically): `levels/toxic_arena_gen`
  — 282 objects, 14 materials, 13 effects; checks passed (0 errors; camera 1,488 cameras, 0 void/back faces; every
  intended area reachable); mobile 694 KB, 7.5k tris, 60 draw calls (est. ~45 visible, ~6.3 MB GPU textures);
  package valid (30 files, 2.6 MB); one command ≈ 3.5 min on CPU.
- Single-image test (real image, `inputs/town_square.png`): `levels/town_square_gen` — first render review found an
  empty plain outside the square + corner gaps + oversized cobbles → added a reusable `townscape` background generator,
  corner houses in the spec, smaller cobble tiling; regenerated: 1,046 objects, checks passed, mobile 1,041 KB, 10.5k
  tris, 61 draw calls (est. ~36 visible).
- Natural-language edit run (scratch copy): 7 example requests → targeted commands; checks caught a side effect
  (enlarged wall-pipe brackets blocked the north walkway, 35% reachable) → fixed with targeted edits (100%) and the
  generator now mounts pipe brackets on the wall.
- Not verified here: Godot import (scripts/.tres untested), device performance (estimates only), Construct Error's real
  gameplay numbers (config placeholders).

### Stage 8 milestones (implemented in order)
1. Stream + channel shapes (liquid leaving an opening along a gravity arc; rectangular drain trough).
2. Anchors + relations scene graph (`anchors.py`; explicit in generated levels, inferred for hand-made ones).
3. Geometry validator (`geometry_check.py`): 11 check families, ERROR / WARNING / INTENTIONAL.
4. Deterministic repair (`geometry_repair.py`), wired into refine.py and checks.py.
5. Inspection close-ups (junctions per connector kind, outlets, third-person at junctions).
6. Construction rules in the generator (junction plates, flush ramps/stairs, 1 cm under-floor overlaps, supports,
   cover clear of landings, party walls, outlet types, embedded pipes, terrain + grounding).
7. Synthetic fixture `levels/test_connections`, tests (`tests/test_stage8.py`), Toxic Arena regression repair, docs.

## Stage 8 status
- Toxic Arena (hand-made, regression): validator found 16 errors + 25 warnings (bridges meeting octagon CORNERS with
  80% of the deck end unsupported, all 4 stair flights 1.7 m short of the walkway, 8 rectangular liquid blocks under
  round pipes, ramp tops on corners, bridge/floor z-fighting, cover crates standing in ramp landings). 24 automatic
  repairs (extend 4 bridges + 4 stairs + 4 ramps, 8 streams from the real pipe openings, 4 z-fight nudges) + 5 cover
  crates moved off the landings by review -> 0 errors / 0 warnings; camera validation passed (void 0, back faces 0);
  every walkable area reachable; hazards unchanged (HazardFluid + 8 fall hazard areas); layout unchanged otherwise.
  Dev 390 -> 415 KB, 3,676 -> 5,180 tris; mobile 419 -> 460 KB, 3,364 -> 4,868 tris, 50 draw calls (unchanged),
  est. ~39 visible (unchanged), ~3.9 MB GPU textures (unchanged), 92 colliders, 9 hazard areas.
- Generated levels after the generator rules: toxic_arena_gen 0/0 (mobile 723 KB, 8.7k tris, 58 draws, est. ~44
  visible), town_square_gen 0/0 after 1 nudge (175 hidden party-wall decorations removed; mobile 929 KB, 8.5k tris,
  61 draws), test_connections 0 errors / 0 warnings / 1 INTENTIONAL (the deliberate 2.7 m jump, measured jumpable).
- Tests: full suite 46 tests passing (Stages 1-8). Stage 8: 5 detect+repair cases (short bridge, stairs missing the landing, stream offset from its pipe, rectangular block
  under a round pipe, hovering crate + undo), 7 generic rule cases (z-fight, blocked arch, railing in a landing, steep
  ramp, liquid over a floor, terrain crack, bad relations), construction rules on the synthetic yard, arena regression.
- Legacy levels still build unchanged; the validator reports real findings there (test yard demo props float, MiDaS
  pagoda overhangs float, town_square spawn) - left for review, not auto-changed.

### Stage 9 milestones (implemented in order)
1. Terrain core (`terrain.py`): feature heightfield (22 feature types, per-feature seeds + influence boxes), global grid
   chunks, LOD1/2 with full-res stitched borders, layer materials (biome presets, new PBR kinds), water surfaces.
2. World mode in the spec (`world.py`, `scene_spec.py`, `spec_to_level.py`): open / hybrid, organic boundary + barrier,
   pads + foundations, automatic road/river bridges, line modules, terrain-aware platforms, edit-preserving merge.
3. Modules: registry (`pipeline/modules/`), natural (arch, cave, overhang, cliff face, spire, ruins, crystals, boulders),
   connectors (bridge, walkway, tunnel), urban/futuristic (street, towers, blocks, factory, cover props); 7 new themes;
   instanced scatter (`scatter.py`, 15 kinds x 5 styles, atlas material per rule, props.glb + instances).
4. Middle zone ring + far layers coupling, river/road continuation, fog for worlds.
5. Mobile export: terrain LOD nodes with visibility ranges, vertex-colour far LOD, per-chunk heightmap + concave +
   scatter colliders, world budgets, Godot scripts (visibility begin/end, optional MultiMesh scatter).
6. Validation (`terrain_check.py`) + repairs + exact overlap areas / buried-face rules, viewer (ranges, terrain info,
   boundary/spawn overlay), render views at the boundary / hilltop, terrain edit commands.
7. Three synthetic engineering worlds (A valley, B city, C hybrid), tests (`tests/test_stage9.py`), docs.


## Stage 9 status
Measured on the three synthetic engineering worlds (no concept image; previews are three.js, not Godot; draw calls /
visible triangles / GPU memory are ESTIMATES from sampled third-person cameras, file sizes and counts are measured).

| | A test_valley (open) | B test_urban (open) | C test_hybrid (hybrid) |
|---|---|---|---|
| theme / biome / prop style | alpine / rocky / realistic | futuristic_city / urban / stylised_scifi | post_apocalyptic / wasteland / post_apocalyptic |
| terrain features / objects / scatter instances | 14 / 92 / 603 | 20 / 740 / 20 | 15 / 235 / 180 |
| near chunks (LOD0 tris) + middle ring tris | 16 (32,768) + 3,108 | 4 (6,272) + 1,736 | 16 (32,768) + 3,108 |
| dev GLB | 5.6 MB, 71k tris, 18 materials | 1.7 MB, 25k tris, 26 materials | 4.2 MB, 54k tris, 30 materials |
| mobile GLB (all LODs stored) | 6.3 MB, 84k tris | 2.0 MB, 27k tris | 5.0 MB, 67k tris |
| visible per camera (est.) | ~53 draws (max 80), ~22k tris (max 31k) | ~65 draws (max 134), ~12k tris | ~72 draws (max 124), ~19k tris |
| GPU textures (est.) | 3.6 MB | 6.0 MB | 9.8 MB |
| colliders | 251 (16 heightmaps, concave cave/arch/overhang) | 506 | 261 |
| geometry + world checks | 0 errors, 0 warnings, 2 intentional | 0 / 0 / 19 intentional (roofs, river/street exits) | 0 / 1 warning / 8 intentional |
| camera validation | 288 cameras, 0 back faces | 312, 0 | 960, 0 |
| reachable / standable | 27,649 / 37,826 m² | 24,279 / 40,410 m² | 29,198 / 41,270 m² |

- Open warnings: B and C exceed the 60 visible-draw-call target (estimate); C: a stair support beam stands in the
  landing of another stair flight (layout of the synthetic spec, left for review).
- Generator / validator issues found and fixed on the way (each a general rule, not a per-map fix): road profiles dipping
  into river channels, perched river water above a bank, valleys breaching the boundary barrier, bridge decks below
  the road, steel bridge supports not touching, coplanar kerbs / pilasters / tunnel walls, z-fight false positives from
  bounding-box overlap (now exact triangle overlap), refine bridging from an enclosing floor, repair ridges reaching
  into the playable area, coarse-grid narrow-walkway false positives.
- Regression: all 7 earlier levels (Toxic Arena, toxic_arena_gen, town_square_gen, test_connections, town_square,
  test_primitives, pagoda_balcony) rebuild byte-identical (dev + mobile GLB); Stage 8 geometry results unchanged.


## Stage 10 status (Sky Citadel = skyforge_arena high-fidelity refinement)
Reference: an AI-enhanced collage of real Sky Citadel screenshots (`levels/skyforge_arena/references/enhanced/`).
Layout preserved: walkable areas, spawns, connections, every floor / deck / ramp / stairs object identical; all 11
intended areas still 100% reachable (per-area standable within +/-1 m2 grid noise; total reachable -15 m2 = the
corrected railings standing at the deck edges instead of being sunk into the sloped links).

| | before | after |
|---|---|---|
| dev GLB (measured) | 3.9 MB, 61.0k tris, 22 materials | 5.3 MB, 88.7k tris, 20 materials |
| mobile GLB (measured, all LODs stored) | 4.4 MB, 69.5k tris, 252 draw calls | 5.8 MB, 99.3k tris, 150 draw calls |
| visible per camera (estimate) | ~68 draws (max 104), ~17k tris | ~57 draws (max 79), ~29k tris (max 45k) |
| GPU textures (estimate) | 6.8 MB + 0.27 MB bg + 2.7 MB sky | 6.9 MB + 0.27 MB bg + 2.7 MB sky |
| effects extra draws (balanced, estimate) | 6 | 11 (2+1 cloud layers, 3 instanced puff sets) |
| checks | 0 errors, 1 warning (draw calls) | 0 errors, 0 warnings |

New reusable systems: rail_run railings + post validation + snap_rail repair; cloud_layer / cloud_puffs + preview
height fog; hull_plating / chevron materials, glossy deck option; tower decor kit; sky_pylon underside; bridge
cross-beams; skyline setbacks / masts; per-level mobile overrides; navigation mirrors game colliders.
Fixed on the way: inverted background spires, centroid-only burial test, duplicate check ignoring shape fields.


## Stage 11 status (Skyforge Arena -> alien_cartoon, Invader-Zim-inspired)
Layout preserved exactly: walkable areas, spawns, gameplay config, every object's geometry (only materials changed),
all 394 structural colliders identical, every intended area 100% reachable, reachable area unchanged (4246.8 m2).
Scenery-only change: island trees (196 scatter colliders) -> alien satellites (120), islands are not playable.
New reusable systems: styles.py presets, toon material flag, outline shells (GLB), cel-banded preview lighting,
Godot apply_style.gd, alien satellite props + hover satellites + spiky skyline, striped planet / stylised cloud options.

## Stage 12 status (Skyforge: falls, fly-by fade, elevator shaft)
Liquid flow direction is measured per mesh (`flow_uv`) and used by the preview and Godot shader (previously the preview
scrolled falls upward). Fly-by ships grow in / shrink away instead of popping. Generic `hole` on box / cylinder /
frustum, `elevator_shaft` structure with a `level_exit` trigger exported to collision.json + Godot Area3D signal.
Not modelled: the closed hatch of concept 1 (the shaft is always open); Construct Error must handle `level_exit_entered`.

## Stage 13 status (Skyforge: emblem banners, organic falls, slime leaks)
Banners are swallowtail pennants with the emblem from levels/skyforge_arena/references/banner_emblem_ref.png (atlas
material: banner + slime decal cells, one draw call). Terrain waterfalls follow each column's own lip and keep clear of
the cliff. Slime leaks on ~40 % of the structures, visual only. Gameplay and colliders unchanged (scenery aside).

