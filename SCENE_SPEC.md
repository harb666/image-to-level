# Scene spec (`levels/<name>/scene_spec.json`)

The scene spec is the explicit, reproducible hand-off from Claude's reading of the reference image(s) to the
deterministic CPU builder. Claude writes it; `pipeline/spec_to_level.py` turns it into `level.json`.

- Validate it: `python3 pipeline/scene_spec.py <spec>`
- Run the whole pipeline: `python3 pipeline/generate.py <spec>`

**Coordinates:** metres, y up, x = east, z = south (north = −z). The arena centre is usually `[0, 0]`. In a top-down
plan the image top is north.

**Provenance:** every element can carry `"source": "visible" | "inferred"`. The generated objects keep it, together
with `"gen": <element id>`.

**Ids:** element ids become the stable object names (`Platform_North` → `Platform_North_Base`, `_Floor`, ...). Use
letters, digits and `_` only.

## Top level

| key | required | meaning |
|---|---|---|
| `spec_version` | yes | `1` |
| `name` | yes | the level folder name |
| `title` | no | used in previews |
| `theme` | no | `industrial`, `toxic_industrial`, `scifi`, `medieval_town` or `ruins`. Sets the material palette, platform and wall style, sky, ambient particles and background. |
| `detail` | no | `low`, `medium` or `high`. Controls ribs, glow strips, vents, wall pipes, timber framing and pinnacles. |
| `profile` | no | `performance`, `balanced` (the default) or `quality`. Used for the mobile export and the sky/background quality. |
| `references[]` | no | `{file, kind, panels[{id, bbox_px, view: top_down / elevation / perspective / detail / text, use[], notes}], notes}` |
| `interpretation` | no | `{summary, scale_basis, visible[], inferred[], assumptions[], questions[]}`. Records what was seen and what was guessed. |
| `arena` | yes | See [Arena](#arena). |
| `platforms[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `connections[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `structures[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `pipes[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `hazards[]` | no | Extra hazard volumes: `{id, area: [x0, z0, x1, z1], y, material}`. |
| `materials` | no | `{variation: true, roles: {<role>: {type, color, tile_m, ...}}}`. Overrides the theme palette per role. |
| `atmosphere` | no | `{sky: <preset>, sky_overrides{}, fog_start, fog_end, height_fog{}, glow_color, ambient: spores / dust / embers / snow / none}` |
| `background` | no | Compact form: `{mountains: both / far / near / none, mountain_height: [lo, hi], factories: n, skyline, spires}`. Explicit form: `{layers: [...]}` using the Stage 2 layer format. |
| `effects` | no | `"auto"` (the default), `"none"`, a list of Stage 4 effects, or `{auto, extra: [...], disable: [ids]}` |
| `spawns[]` | no | `{id, on: <platform>}` or `{id, position: [x, y, z]}`, plus an optional `yaw`. The first entry is the main spawn. |
| `gameplay` | no | Overrides `config/gameplay.json` for this level. |
| `refine` | no | `{max_passes: 3}` |

## Arena

```json
"arena": {"shape": "rect|octagon|circle", "size": [72, 72], "center": [0, 0],
          "floor": {"kind": "hazard|ground|deck", "y": 1.0, "name": "HazardFluid"},
          "walls": {"height": 14, "thickness": 4, "style": "auto|industrial|stone|none",
                    "openings": [{"side": "north", "at": 0, "width": 8, "height": 7}]},
          "walkway": {"width": 4, "y": 7},
          "boundary": "walls|invisible"}
```

- **Floor `hazard`** (liquid) makes a kill volume. Platforms then rise from y = 0.
- **Floor `ground` or `deck`** gives walkable floor at `y`.
- **Walls** follow the arena outline (4, 8 or 20 segments). Openings are supported on `rect` arenas.
- **Walkway** is a deck ring along the inner side of the walls (`rect` arenas only).
- **`boundary: "invisible"`** adds invisible collider walls at the arena edge. Use it for outdoor levels enclosed by
  buildings.

## Platforms, connections, structures, pipes

```json
{"id": "Central", "shape": "octagon", "center": [0, 0], "size": [22, 22], "top": 8, "style": "industrial_pillar|stone_plinth|plain",
 "cover": 4, "lights": true, "source": "visible"}
{"id": "Bridge_North", "from": "Central", "to": "Platform_North", "kind": "auto|bridge|catwalk|ramp|stairs|jump", "width": 4.5, "rails": false}
{"id": "Central_Tower", "kind": "tower", "on": "Central", "offset": [0, 0], "size": [7, 13, 7], "decor": ["banners", "glow_strips", "vents"]}
{"id": "House_W1", "kind": "house", "position": [-18.5, 19], "facing": "east", "size": [11, 12, 9], "style": "timber", "floors": 3, "roof": "gable"}
{"id": "Pipe_NE", "wall": "ne", "y": 10, "radius": 1.5, "length": 11, "pour": true, "outlet": "circle|drain|spillway|vertical|broken", "width": 2}
{"id": "Pipe_Run_1", "kind": "run", "points": [[-30, 3, -35], [30, 3, -35]], "radius": 0.6}
```

### Connection kinds

`kind: "auto"` chooses for you:

- **bridge** when the height difference ≤ the player's `step_height`
- **ramp** when the slope ≤ min(`max_slope_deg`, 35°)
- **stairs** otherwise. Stairs may extend onto the lower platform, and the generator reports when they do.

How each kind is built:

- An elevated ramp is built as a sloped bridge: a tilted deck, beams and a support.
- A **jump** creates no geometry. The navigation check verifies the jump against the gameplay config.

### Structure kinds

All sizes are `[w, h, d]`. For buildings, `w` is the frontage. `facing` takes `center`, `north`, `south`, `east` or
`west`, or you can give `yaw` in degrees. The front of a building is its local +z side.

| kind | what it builds |
|---|---|
| `tower` | Industrial tower: bevelled body, cap, setback top, corner ribs. `decor` options: banners, glow_strips, vents. |
| `building` | Industrial hall: parapet, roof machinery or a `roof` (gable/hip), lit window strip, door. |
| `house` | Town house. `style`: timber, stone or plaster. `floors`, jettied timber framing, `roof`: gable, hip or flat; chimney, windows, door. |
| `stone_tower` | String courses, buttresses, windows. `roof`: crenellated (battlements + pinnacles), spire or hip. |
| `fountain` | Basin, water surface, column, bowl. The water gets a surface effect. |
| `gate` / `arch` | Round (`round: true`) or square arch. `opening` is the width fraction. Passable. |
| `wall` | Free-standing wall: `from` [x, z], `to` [x, z], `height`, `thickness`, `style`, `inner` [x, z]. |
| `machinery`, `tank`, `pillar`, `lamp`, `crates` (cover), `rocks`, `tree`, `banner` | Props and decor. |

To support a shape that isn't listed (for example a dome or a crane), add a module to `pipeline/architecture.py`.
Register it in `STRUCTURES`, keep the mesh closed, name its parts, and document it here. Don't swap in an unrelated
shape.

### Terrain (Stage 8)

```json
"terrain": [{"id": "Island", "area": [-30, 6, -12, 20], "height": [0, 4], "cell": 2.0, "seed": 3, "material": "rock", "top_material": "foliage"}]
```

Builds a heightfield that rises from the floor. Its border is tucked under the floor or liquid, so no seam shows.
Structures placed by `position` on terrain are grounded: thin things (rocks, trees, lamps, pillars) at the centre
height, buildings at the lowest point under their footprint.

### Liquid outlets (Stage 8)

Every pipe pours a `stream` that leaves its real opening. The opening is the anchor `outlet`. The stream's
cross-section matches the opening, it follows a gravity arc, and it ends submerged in the arena's hazard pool. The
generator records `emits_from` and `flows_into` relations.

| `outlet` | What you get |
|---|---|
| `circle` | Round pipe. |
| `drain` | Rectangular channel with a liquid strip and a rectangular stream. |
| `spillway` | Wide channel pouring a thin sheet. |
| `vertical` | Pipe pointing down, with a straight column. |
| `broken` | Weak gush, tilted downward. |

### Relations

The generator writes `level.json["relations"]` for connections, supports, outlets and jumps. Add your own with
`edit_level.py relate`. Declare deliberate gaps with `intentional_gap`, or with a connection of `kind: "jump"`.
These are validated as INTENTIONAL and the repair system never fills them.

## Material roles

Objects use roles, and each role resolves to a material through the theme palette. Roles shared by many objects are
shared materials, so they cost few draw calls.

`deck`, `structure`, `structure_b`, `wall`, `trim`, `grate`, `frame`, `rail`, `pipe`, `hazard`, `glow`, `accent`,
`machine`, `ground`, `rock`, `foliage`, `water`, `window`, `door`, `stone`, `plaster`, `timber`, `roof`, `roof_slate`,
`backdrop`.

With `variation: true` (the default), `wall`, `structure`, `deck` and `plaster` get one shared `_v2` variant with a
slightly different tint and wear, assigned per element. This breaks repetition without adding a unique texture per
object. Override any role with Stage 1 material keys in `materials.roles`:

```json
{"plaster": {"type": "plaster", "color": [0.9, 0.83, 0.66]}}
```

## What the generator adds without being asked

- `walkable[]` areas, one per platform, bridge and floor. The navigation and camera checks use them.
- Bounds.
- Spawn placement. On a platform, it picks the spot with the most room, away from structures and cover.
- The environment: sky preset and background layers scaled to the arena size.
- Auto effects:
  - hazard surface, bubbles and mist
  - flow, splash and steam on pours
  - glow pulse
  - trim pulse and flicker on emissive industrial materials
  - sparks at towers
  - ambient particles
  - factory smoke
  - sky drift
- Generator notes, for example a stair run that extends onto a platform.

## Regenerating keeps manual edits

`gen_state.json` stores hashes of what was generated last time. When you run the generator again:

- Edited objects, materials, effects and environment entries stay as edited.
- Deleted ones stay deleted.
- Manually added ones are kept.
- Untouched generated ones are replaced.

Each regeneration is undoable with `edit_level.py undo`. A hand-made `level.json` that has no `gen_state.json` is
never overwritten unless you pass `--force`.
