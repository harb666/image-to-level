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
| 7 Image → level generation & autonomous refinement ✅ | references.py (panels/plan/grid) → Claude writes scene_spec.json → generate.py: spec_to_level (architecture modules, role materials, auto environment/effects/spawns, edit-preserving regeneration) → build → refine loop (checks.py + navigation + camera, safe fixes, bounded) → headless renders → previews → Godot package | one command from interpretation to validated, packaged level |
| 6 iPhone editing & preview ✅ | third-person + free camera + top-down, tap-to-identify object (name/material), screenshot button, quality toggle, edit-by-name helper | full phone workflow |

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
