# Game-ready level exports

Each folder here is a validated Godot 4 package produced by `python3 pipeline/package.py levels/<name> --out exports/<name>`
(the same content as `dist/<name>/package`, which is not committed). To use one in Construct Error:

1. Copy `exports/<name>/levels/<name>/` into the game project as `res://levels/<name>/` (scripts and `.tres` assume that path).
2. Follow `res://levels/<name>/IMPORT_GODOT.md` (level / background / collision GLBs, `apply_mobile.gd`, `apply_effects.gd`,
   `apply_style.gd`, `environment.tres`, spawns and hazards, the `level_exit_entered` signal for level exits).

Pulling only this folder from another checkout:

    git clone --depth 1 --filter=blob:none --sparse https://github.com/harb666/image-to-level.git
    cd image-to-level && git sparse-checkout set exports/skyforge_arena exports/slime_arena

| Level | Notes |
|---|---|
| `slime_arena` | Level 1, part 2 (indoor hall, roof). The round elevator from part 1 arrives through the roof onto the central deck: `entrances` + `apply_mobile.gd` `play_arrival("Elevator", player)`; player spawns on the car. Sun shadows off (indoor). Mobile ~67 draw calls / ~13.5k triangles (estimates). |
| `skyforge_arena` | Level 1, part 1. alien_cartoon style (toon + outline shells), elevator shaft in the Hub = `level_exit` trigger (target `slime_arena`), mobile export ~134 draw calls / ~88k triangles (estimates in `mobile/mobile_manifest.json`). |

The Godot scripts are UNTESTED in Godot from the generator environment - check the first import in the editor.
Regenerate an export after changing a level (`generate.py`, then the package command above).
