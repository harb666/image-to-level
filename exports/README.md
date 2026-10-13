# Game-ready level exports

Each folder here is a validated Godot 4 package produced by `python3 pipeline/package.py levels/<name> --out exports/<name> [--game]`
(the same content as `dist/<name>/package`, which is not committed). To use one in Construct Error:

1. Copy `exports/<name>/levels/<name>/` into the game project as `res://levels/<name>/` (scripts and `.tres` assume that path).
2. Follow `res://levels/<name>/IMPORT_GODOT.md` (level / background / collision GLBs, `apply_mobile.gd`, `apply_effects.gd`,
   `apply_style.gd`, `environment.tres`, spawns and hazards, the `level_exit_entered` signal for level exits).

Pulling only this folder from another checkout:

    git clone --depth 1 --filter=blob:none --sparse https://github.com/harb666/image-to-level.git
    cd image-to-level && git sparse-checkout set exports/skyforge_arena exports/slime_arena

| Level | Notes |
|---|---|
| `slime_arena` | Level 1, part 2: Toxic Works. Elevator arrives in the slime hall (start); open gate north into the Works wing: assembly line, pipeworks, purification hall, core chamber, maintenance shafts, processing towers, waste conduits, exit door (`level_exit` -> `level1_part3`, placeholder). Game package (`--game`): no desktop GLBs. Olive plated ceilings (girders, lights, conduits, capsule tubes), plate + slime wall textures, spinning fans (effect `spin`), see-through tubes with rising slime blobs, wall TVs and robot viewscreens - propaganda broadcast + robot assembly tank - in the old slime windows, all showing animated TV static (effect `tv_static`), reactor columns, rock face. Game export 3.8 MB (WebP textures, minified JSON, editor-only data left out); mobile level 2.7 MB, ~81k triangles, 77 draw calls (~52 visible, estimate). |
| `skyforge_arena` | Level 1, part 1. alien_cartoon style (toon + outline shells), elevator shaft in the Hub = `level_exit` trigger (target `slime_arena`), mobile export ~134 draw calls / ~88k triangles (estimates in `mobile/mobile_manifest.json`). |

The Godot scripts are UNTESTED in Godot from the generator environment - check the first import in the editor.
Regenerate an export after changing a level (`generate.py`, then the package command above).
