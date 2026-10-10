# iPhone workflow (Construct Error levels)

## 1. Look at the level
Open the level's preview link in Safari.
- **Mode** button cycles through these views:
  - **3rd person**: stick to move, drag to look; same spring-arm camera as the validator.
  - **1st person**.
  - **orbit**.
  - **free cam**: fly with the stick, drag to look, ▲▼ to go up and down.
  - **top-down**: one finger pans, pinch zooms.
- **Quality** low/med/high changes resolution and effect density. It's remembered on your phone.
- **FX** toggles the effects preview.
- **Stats** shows the browser renderer's draw calls, triangles and fps. These numbers are not Godot or device benchmarks.

## 2. Point at something
Tap any object. A sheet shows:
- its **name** (the stable id used for edits), type and parent
- position, size and rotation
- its material: swatch, type, tile size, glow, texture preview
- triangle count

In the mobile preview, merged meshes still show the original object name.

Tap **Copy for Claude**, then paste into the chat and finish the sentence:
> In Toxic Arena: object "OuterWall_North" (box, metal_dark, …). Please change: make it industrial metal with pipes

## 3. Show what you mean
Tap 📷 to take a screenshot. It opens full screen. Long-press it, choose **Save to Photos**, then attach it to the chat.

## 4. What Claude runs (one targeted edit, then a rebuild of only the affected parts)
| You say | Command (`python3 pipeline/edit_level.py levels/<name> …`) |
|---|---|
| Make the central platform wider | `resize Central_Platform 1.25 1 1.25` |
| Replace that rock wall with industrial metal | `material <tapped name> metal_dark` (or create one first: `mat rusted_plate type=damaged_metal color=[.45,.3,.2] tile_m=3`) |
| Add large pipes to the north wall | `prefab pipe_run '{"name":"NorthWall_Pipes_01","points":[[-30,10,-35.4],[30,10,-35.4]],"radius":0.9,"material":"pipe","junction":"metal_dark"}'` |
| Make the mountains taller | `env background.Mountains_Far.height=[110,240] background.Mountains_Near.height=[30,80]` |
| Add toxic green waterfalls | `duplicate Pipe_North_01 Pipe_North_02 -24 0 0` and `duplicate Pipe_North_01_Fall Pipe_North_02_Fall -24 0 0` (the new fall joins the flow, splash and steam effects) |
| Make the factory look more detailed | `env 'background.Factory_*.detail=3'` (more towers, chimneys, pipe bridges; `env` alone lists every background layer and the sky). Close-up detail: `prefab machinery_bank …` near a wall |
| Change the sky to a dark alien atmosphere | `env sky.preset=alien atmosphere.fog_end=500` (presets: industrial_smog, sunset, sunrise, night, overcast, alien, clear_day) |
| Less / no toxic mist | `fx Toxic_Mist opacity=0.15` (or `fx Toxic_Mist enabled=false`) |
| Move / remove / rename | `move <name> dx dy dz`, `remove <name>`, `rename <old> <new>` |
| Undo that | `undo` (history: `history`) |

Each edit changes only the named objects. Every other value in level.json stays unchanged.

How long the rebuild takes:
- environment-only edits: about 6 s
- effects-only edits: about 5 s
- geometry or material edits: about 6 s
- switching to a new sky preset: about 25 s, once

After a geometry edit, Claude runs the camera validator (`--validate`) and refreshes the preview link.

## 5. Take it to Godot
Copy `levels/<name>/mobile/` (`level_mobile.glb`, `background_mobile.glb`, `collision.*`, `effects_mobile.json`,
`apply_mobile.gd`) along with the environment and effects kit into the Godot project.

The Godot scripts are untested. The browser preview is close to Godot but not identical.
