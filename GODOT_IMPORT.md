# Importing a generated level into Construct Error (Godot 4)

Claude does these steps for you when it has access to the Construct Error repository and you've asked it to. Nothing
here changes the Construct Error repo on its own. The Godot scripts and `.tres` files are **untested in Godot from
the generator environment**, so treat them as starting points and check the first import in the editor.

## 1. Copy the package

1. Run `python3 pipeline/package.py levels/<name> --zip` to produce `dist/<name>/package/levels/<name>/` and
   `dist/<name>/<name>.zip`.
2. Copy the `levels/<name>/` folder to `res://levels/<name>/` in the Godot project. Every path inside the package
   (`environment.tres`, the scripts) assumes that location.

## 2. Build the level scene

Use the mobile files for the game, and the dev files for editing and inspection.

| What | File | How |
|---|---|---|
| Level geometry | `mobile/level_mobile.glb` | Instance it. In the import settings, keep the default mesh compression and enable LOD generation (see `mobile/mobile_manifest.json` → `godot`). |
| Distant scenery | `mobile/background_mobile.glb` | Instance it. It has no collision and nothing is walkable. |
| Collision | `mobile/collision.glb` | Instance it. Its node suffixes `-colonly` / `-convcolonly` make Godot create StaticBody3D shapes on import. As an alternative, build the shapes yourself from `mobile/collision.json`. |
| Visibility, shadows and hazards | `mobile/apply_mobile.gd` | Add a Node3D at the origin with this script. Set `manifest_path` to `res://levels/<name>/mobile/mobile_manifest.json` and `level_root` to the level_mobile instance. |
| Effects | `fx/godot/apply_effects.gd` | Add a Node3D with this script. Set `effects_path` to `res://levels/<name>/mobile/effects_mobile.json` (its targets match the merged mobile nodes), `level_root`, `quality`, and `environment`. |
| Sky, fog and light | `environment.tres` | Assign it to a WorldEnvironment. Add a DirectionalLight3D using `environment.json` → `sun.godot_rotation_degrees`, colour and energy. |
| Fluids (Stage 8) | `effects.json` → `fluid_attachments` | One entry per liquid stream: outlet position / direction / diameter / section, impact point, receiving pool, initial speed. The GLB already contains a stream mesh leaving the real opening (animated by `liquid_flow`). Use these anchors if Construct Error renders richer fluids at runtime. |
| Terrain (Stage 9) | `mobile/level_mobile.glb` nodes `TR_<i>_<j>_<material>_L0/L1`, `TR_<i>_<j>_L2_far`, `TRM_<sector>` | Chunk LODs with complementary visibility ranges in `mobile_manifest.json` (begin/end); `apply_mobile.gd` sets them. Borders are full-resolution at every LOD, so any mix is crack-free. `*_far` / `TRM_*` use vertex colours (the importer enables vertex colour as albedo). Middle zone `TRM_*` has no collision. |
| Terrain collision | `mobile/collision.glb` `TR_<i>_<j>-colonly` | One heightmap mesh per chunk (or build HeightMapShape3D from `collision.json`: origin, cell, heights). Caves / arches / overhangs / tunnel berms are concave (`-colonly`) so their openings stay open. |
| Scatter (optional) | `terrain.json` → `instances`, `props/props.glb`, `mobile/apply_scatter_multimesh.gd` | The GLB already has scatter merged per cell (no code needed). For MultiMesh instancing use the script (UNTESTED in Godot here); it hides the merged `SC_*` nodes. |
| Spawns | `gameplay/spawns.json` | The `PlayerSpawn` node in the GLB is the first spawn. Extra team or respawn points are listed in the JSON (position, yaw_deg, Stage 9 `team` player / enemy, plus the `spawn_regions` they came from). |
| Hazards | `gameplay/hazards.json` | Box Area3Ds in world space. Construct Error decides whether they kill, damage or respawn. `apply_mobile.gd` creates them in the group `hazard`. |

## 3. Gameplay numbers

`config/gameplay.json` holds PLACEHOLDER player and camera values: radius, height, step, slope, jump, and the
spring-arm length and probe radius. The navigation and camera checks use them. Copy Construct Error's real
CharacterBody3D and SpringArm3D settings into that file, or into `levels/<name>/gameplay.json`, and re-run
`python3 pipeline/checks.py levels/<name>`. Reachability and jump results are only as right as those numbers.

## 4. What is not in the GLB

The GLB holds only static meshes and PBR materials. These are rebuilt at runtime from the JSON, `.tres` and scripts:

- animated liquid
- particles
- pulsing lights
- fog sheets
- sky drift
- hazards
- spawns

The browser preview approximates all of these with three.js. It is close to Godot but not identical.

## 5. Checklist after the first import

- [ ] The level appears at the right scale. The player capsule fits the doors and bridges.
- [ ] The collision shapes line up with the floors and walls. You can't walk through walls.
- [ ] The hazard areas trigger.
- [ ] The sky and fog look like the preview.
- [ ] The effects play, and none of them spawn inside opaque geometry.
- [ ] Run the profiler on a device. The manifest numbers are estimates.
- [ ] Worlds: walk to a chunk border and watch LODs switch (no cracks, no popping holes); check the boundary colliders
      sit just inside the barrier ridge; look out from the edge in every direction (no void below the horizon).
