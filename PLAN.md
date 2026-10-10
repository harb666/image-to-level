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
| 5 Mobile performance | dev vs mobile export: merge static meshes by material (names kept in node extras/level.json), LOD for big objects, collision proxies, texture atlas for small emissive/decals, KTX2 if a free encoder is available (else rely on Godot VRAM compression) | fewer draw calls, measured budgets |
| 6 iPhone editing & preview | third-person + free camera + top-down, tap-to-identify object (name/material), screenshot button, quality toggle, edit-by-name helper | full phone workflow |

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
