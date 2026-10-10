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
| `theme` | no | `industrial`, `toxic_industrial`, `scifi`, `medieval_town`, `ruins`, and (Stage 9) `futuristic_city`, `desert`, `alpine`, `fantasy_forest`, `alien`, `post_apocalyptic`, `cartoon`. Sets the material palette, platform and wall style, sky, ambient particles, background, terrain biome and prop style. |
| `detail` | no | `low`, `medium` or `high`. Controls ribs, glow strips, vents, wall pipes, timber framing and pinnacles. |
| `profile` | no | `performance`, `balanced` (the default) or `quality`. Used for the mobile export and the sky/background quality. |
| `references[]` | no | `{file, kind, panels[{id, bbox_px, view: top_down / elevation / perspective / detail / text, use[], notes}], notes}` |
| `interpretation` | no | `{summary, scale_basis, visible[], inferred[], assumptions[], questions[]}`. Records what was seen and what was guessed. |
| `arena` | one of the two | See [Arena](#arena). Structured levels. |
| `world` | one of the two | Stage 9 open terrain. See [World](#world-stage-9). `arena` + `world` = hybrid. |
| `platforms[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `connections[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `structures[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `pipes[]` | no | See [Platforms](#platforms-connections-structures-pipes). |
| `hazards[]` | no | Extra hazard volumes: `{id, area: [x0, z0, x1, z1], y, material}`. |
| `materials` | no | `{variation: true, roles: {<role>: {type, color, tile_m, ...}}}`. Overrides the theme palette per role. |
| `atmosphere` | no | `{sky: <preset>, sky_overrides{}, fog_start, fog_end, height_fog{height, density}, fog_color, glow_color, ambient: spores / dust / embers / snow / none, clouds{}, lighting{}}` |
| `mobile` | no | per-level mobile export overrides: `{cell, tex_max, bg_tex_max, prop_range, small}` (e.g. `{"cell": 64}` = bigger merge cells, fewer draw calls) |
| `background` | no | Compact form: `{mountains: both / far / near / none, mountain_height: [lo, hi], factories: n, skyline, spires}`. Explicit form: `{layers: [...]}` using the Stage 2 layer format. |
| `effects` | no | `"auto"` (the default), `"none"`, a list of Stage 4 effects, or `{auto, extra: [...], disable: [ids]}` |
| `spawns[]` | no | `{id, on: <platform>}` or `{id, position: [x, y, z]}`, plus an optional `yaw` and `team` (player / enemy). The first entry is the main spawn. Open worlds normally use `world.spawn_regions` instead. |
| `gameplay` | no | Overrides `config/gameplay.json` for this level. |
| `refine` | no | `{max_passes: 3}` |

## Generation mode (Stage 9)

Claude picks the mode from the concept image; nothing assumes a square boundary, symmetry or a central platform.

| mode | spec | use for |
|---|---|---|
| structured | `arena` only | closed arenas, interiors, compounds with walls |
| open | `world` only | valleys, deserts, coasts, forests, cities, any landscape |
| hybrid | `arena` + `world` | a compound / arena on a terrain pad inside a landscape (platforms, bridges, roads around it) |

## World (Stage 9)

```json
"world": {"size": [256, 256], "center": [0, 0], "seed": 21, "relief": "hilly", "biome": "rocky", "style": "realistic",
          "cell": 2.0, "chunk": 32, "base_y": 0,
          "boundary": {"shape": "organic", "margin": 24, "barrier": "ridge", "height": 16},
          "features": [{"id": "River", "type": "river", "points": [[-118, -4], [0, 8], [118, 10]], "width": 9, "depth": 1.4}],
          "scatter": [{"id": "Pines", "kinds": ["conifer", {"kind": "dead_tree", "weight": 0.15}], "density": 1.1, "layers": ["grass"]}],
          "spawn_regions": [{"id": "Player_Start", "team": "player", "center": [-40, 42], "radius": 14, "count": 4},
                            {"id": "Enemy_East", "team": "enemy", "center": [60, 20], "radius": 16, "count": 5}],
          "water": {"level": -2.0}, "middle": {"radius": 450, "rise": 32}, "lod_ranges": [60, 120]}
```

| key | meaning |
|---|---|
| `size` / `extent` | Detailed (NEAR) terrain: `[w, d]` around `center`, or `[x0, z0, x1, z1]`. Playable area + room for the barrier. |
| `relief` | `flat`, `gentle`, `hilly`, `rugged`, `mountainous`: amplitude / scale / ridges of the base noise (domain-warped, non-repeating). `noise{}` overrides. |
| `biome` | Terrain material layers: `temperate`, `rocky`, `desert`, `alpine`, `urban`, `industrial`, `alien`, `wasteland`, `fantasy`, `cartoon` (default from the theme). |
| `style` | Prop look for scatter: `realistic`, `stylised_scifi`, `fantasy`, `cartoon`, `post_apocalyptic` (default from the theme). |
| `cell`, `chunk` | Grid spacing (m) and chunk size in cells (multiple of 4). 2 m / 32 = 64 m chunks; flat cities can use 4 m. |
| `boundary` | Playable polygon: `points` (Claude's) or `shape: organic / rounded` inside the extent minus `margin`. `barrier: ridge` adds a natural ridge just outside it (`height`, `offset`, `width`); `none` = no barrier (validated as intentional). Invisible colliders follow the polygon. |
| `features[]` | Named, individually editable terrain shapes (below). |
| `scatter[]` | Instanced props (below). |
| `spawn_regions[]` | `{id, team: player / enemy, center, radius, count, spacing, facing}` → safe points (flat ≤ 12°, dry, inside the boundary, clear of structures). |
| `water.level` | Sea level (with a `coast` feature). |
| `middle` | MIDDLE zone ring: `radius` (default: runs into the near mountain ring), `rise`, `enabled`. |
| `layers`, `materials` | Replace the biome's layer rules / material definitions (`ter_<material>` in level.json). |

### Terrain features

Every feature has an `id` (stable, edit it later), a `type`, and its own seed (from the terrain seed + id). Order of
application: shapes (hill … field) → carves (valley, canyon, river, lake, coast, trench) → barrier → flattening (pads,
then roads). Rivers and roads that reach the edge continue out to the horizon (gently meandering) unless `extend: false`.

| type | keys | effect |
|---|---|---|
| `hill`, `mountain` | `center`, `radius`, `height`, `stretch`, `yaw`, `irregular` | rounded hill / ridged peak, irregular outline |
| `ridge` | `points`, `width`, `height` | mountain chain along a line |
| `plateau`, `mesa` | `center`, `radius`, `height` or `y`, `edge` | flat top; mesa = stepped steep walls |
| `crater` | `center`, `radius`, `depth`, `rim` | bowl with a rim |
| `cliff` | `points`, `height`, `side`, `reach`, `transition` | raised shelf with a steep step (add `cliff_face` structures for vertical rock) |
| `dunes` | `center`, `radius`, `height`, `wavelength`, `direction` | wind ripples |
| `field` | `center`, `radius`, `strength`, `surface` | smooths to an open field (`surface: "park"` → grass in a paved city) |
| `valley`, `canyon` | `points`, `width`, `depth`, `floor` | soft valley / steep-walled canyon |
| `river` | `points`, `width`, `depth`, `bank`, `bank_slope`, `flow` | carved channel, water surface never above either bank, never flows uphill (`flow: false` for canals) |
| `lake` | `center`, `radius`, `depth`, `level` | bowl + water disc (level from the rim by default) |
| `coast` | `points`, `side`, `width`, `depth` | lowers the ground under `water.level` |
| `road`, `street`, `path` | `points`, `width`, `shoulder`, `max_grade`, `smooth` | flattened, grade-limited ribbon (road / path material layer); leaves rivers open → bridge |
| `pad` | `center`, `size` or `radius`, `y`, `yaw`, `margin`, `surface`, `mode: "lower"` | flat area (buildings get one automatically) |
| `trench` | `points`, `width`, `y` | flat cut (tunnels add one automatically) |
| `heightmap` | `image`, `area`, `height`, `mode: add / replace / max`, `feather` | heights from a grayscale image (layout from a concept image) |
| `mask` | `image`, `area`, `name` | named mask from an image, usable by layer rules / scatter `avoid` |

### Scatter

```json
{"id": "Rocks", "kinds": ["rock_small", {"kind": "boulder", "weight": 0.35, "scale": [0.8, 1.4]}], "area": "playable",
 "density": 1.6, "cluster": 0.4, "slope_max": 34, "layers": ["grass"], "avoid": ["road", "river", "pad", "objects", "spawns"]}
```

Kinds: `conifer`, `broadleaf`, `dead_tree`, `palm`, `bush`, `grass_tuft`, `rock_small`, `boulder`, `cactus`, `crystal`,
`alien_plant`, `debris`, `stump`, `log`, `flowers` (3 low-poly variants each, closed meshes). `area`: `"playable"`,
`"extent"`, `[x0, z0, x1, z1]` or a polygon. `density` = instances per 100 m²; `cluster` 0..1 clumps them. Trees and
boulders get colliders; grass, bushes and pebbles don't. Scatter stops at its view distance (grass 35 m, trees 160 m).

### Natural and urban structure kinds (Stage 9 modules, `pipeline/modules/`)

| kind | keys | what it builds |
|---|---|---|
| `rock_arch` | `position`, `size`, `yaw` | natural stone arch (walk under it; concave collision) |
| `cave` | `position`, `size`, `yaw`, `opening` | rock outcrop with a walk-in cave (ground flattened to its floor) |
| `overhang` | `position`, `size`, `yaw` | rock shelf jutting over a recess |
| `cliff_face` | `from`, `to`, `height`, `depth` | vertical rock wall segments facing the lower side |
| `rock_spire`, `boulder_field`, `crystal_cluster`, `ruins` | `position`, `size` / `radius`, `count` | hoodoo / boulders / glowing crystals / broken masonry |
| `bridge` | `from`, `to`, `width`, `style: steel / stone`, `y` or `y_from` / `y_to` | deck following the grade, rails/parapets, piers to the ground or bed, abutments |
| `walkway` | `from`, `to`, `y`, `width` | elevated grated catwalk with columns |
| `tunnel` | `from`, `to`, `width`, `height`, `y` | trench + concrete tube + portals + the original hill restored over the roof |
| `street` | `from`, `to`, `width`, `sidewalk`, `lamps` | flattened asphalt roadway, kerbed sidewalks following the grade (cut at intersections), street lamps |
| `futuristic_tower`, `office_block`, `factory` | `position`, `size`, `floors`, `count`, `lit` | setback sci-fi tower / window-grid block / sawtooth hall with chimneys |
| `container`, `barrier_line`, `wreck`, `billboard`, `antenna`, `fence` | `position` or `from`/`to` | cover and street furniture |

Footprint modules (towers, blocks, factories, houses, ruins, …) get a terrain pad + a 20 cm foundation plinth on open
ground. Add a kind by dropping a file into `pipeline/modules/` with `@structure("kind", pad=True)` - no generator edits.

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
| `elevator_shaft` | Stage 12: open shaft through the centre of its platform (`on`, `offset` [0, 0]), `radius` (default 5.5), `target` (next level id), `depth` (solid platforms, default 10). Cuts a real hole through every slab, lines the shaft (pilasters, light strips and rings, glowing floor), dresses the rim and adds a `level_exit` trigger. See below. |

To support a shape that isn't listed (for example a dome or a crane), add a file to `pipeline/modules/` that registers
it with `@structure("kind")` (Stage 9; or a function in `architecture.py` registered in `STRUCTURES`). Keep the mesh
closed, name its parts, and document it here. Don't swap in an unrelated shape.

### Terrain patches (Stage 8; open worlds use `world` instead)

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

Stage 9: `level.json["terrain"]` settings and every terrain feature (by `id`) follow the same rule, so an edited hill
or a moved river survives regeneration.

`gen_state.json` stores hashes of what was generated last time. When you run the generator again:

- Edited objects, materials, effects and environment entries stay as edited.
- Deleted ones stay deleted.
- Manually added ones are kept.
- Untouched generated ones are replaced.

Each regeneration is undoable with `edit_level.py undo`. A hand-made `level.json` that has no `gen_state.json` is
never overwritten unless you pass `--force`.


## Stage 10 additions (Sky Citadel refinement)

**Clouds** - `atmosphere.clouds` (auto effects, all below the playable decks so combat sightlines stay clear):
```json
"clouds": {"layers": [{"y": 12, "radius": 760, "opacity": 0.88, "coverage": 0.4, "scale": 0.008, "layers": 2, "spacing": 8}],
           "collars": {"glob": ["*_Column"], "y": [14, 30], "size": [10, 18]}, "islands": true, "distant": true,
           "horizon": [300, 470], "color": [1, 0.9, 0.84], "shade": [0.5, 0.42, 0.56], "glow": [1, 0.58, 0.3], "below": 6}
```
- `cloud_layer`: soft disc (fbm coverage, radial edge fade - never a visible plane edge), sun-side glow, depth-faded
  in Godot (`fx/godot/cloud_layer.gdshader`). One transparent draw per layer; performance preset halves the layers.
- `cloud_puffs`: billboard cumulus puffs in rings around columns (`collars`), terrain islands (`islands`), distant
  cliffs + horizon banks (`distant`, `horizon`). ONE draw call per effect (MultiMesh in Godot, instanced in the preview).
- `height_fog`: Godot `fog_height` / `fog_height_density`; the browser preview now applies the same formula.

**Lighting** - `atmosphere.lighting`: `sun_energy, sun_color, ambient_energy, exposure` (light) + `contrast,
saturation, brightness, tonemap, glow{}` (grading).

**Railings** - connectors with `"rails": true` build `rail_run` railings: vertical posts standing ON the deck surface
(sloped ramps, stairs: on tread centres), top rail / mid rail / kick plate parallel to the slope, closed corner joints.
Hand-placed: `edit_level.py prefab railing_path '{"name": "R", "points": [[x,y,z], ...]}'` (points on the floor).
`geometry_check` verifies every post (floating / sunk / over the void) and repairs with `snap_rail`.

**Tower decor kit** - `"decor": ["banners", "glow_strips", "vents", "bands", "pipes", "boxes", "hazard", "antenna"]`.
Ground-level kit parts are visual-only (`collision: false`, inside the player radius): colliders and navigation unchanged.
`sky_pylon` platforms get underside ribs + column collars (`"underside": false` to disable). Bridges get cross-beams.

**Materials** - new kinds `hull_plating` (worn tower plates: straps, vents, rain streaks, scuffed edges, roughness
breakup) and `chevron` (hazard stripes, role `stripe`); `scifi_floor` takes `gloss` and `metallic` (polished deck).

**Skyline** - background `skyline` layers take `setbacks: true` (stepped high-rises) and `masts: 0..1` (antennas).


## Art style presets (Stage 11)
`"art_style": "alien_cartoon"` applies a reusable preset (`pipeline/styles.py`). It is merged UNDER the spec: anything
the spec sets explicitly wins, so a level can tweak one colour without losing the rest. Levels without `art_style`
are unchanged (existing themes / styles keep working). `python3 pipeline/styles.py` lists presets.

`alien_cartoon` controls: material palette (purple-black inked structures, red rails / banners / lights, toxic green
fluid), toon shading, outline shells, magenta sky with angular posterised clouds, the striped pink planet (kept, drawn
over clouds), green height fog + green cloud abyss, green emissive waterfalls / sea, trees -> alien satellites
(`sat_dish`, `sat_pod`, `sat_spire`), distant hovering satellites (`hover_satellites` background layer), spiky
alien skyline, tower antennas.

Building blocks usable without the preset:
- material `"toon": true` (any kind): flat posterised colour, ink on height-map edges, matte, non-metallic
  (`toon_levels`, `toon_flatten`, `ink`, `ink_threshold`, `ink_color`).
- level.json `"style": {"toon": {"steps", "floor", "ambient"}, "outline": {"color", "width": [min, max], "rel",
  "min_size", "skip_materials", "skip_types"}}`: outline = inverted-hull shells baked into level.glb (`<name>__ol`,
  material `ink`) - real geometry, works in Godot / any engine without shaders; checks, navigation and colliders
  ignore them; mobile export merges them into a few coarse `M_ink_*` nodes. Per object `"outline": false` opts out.
- sky: `planet.stripes {strength, frequency, color}`, `planet.over_clouds`, `clouds.posterize`, `clouds.angular`,
  `clouds.stretch`.
- scatter kinds `sat_dish`, `sat_pod`, `sat_spire`; background types `hover_satellites`, skyline `spikes`.
- Godot: `fx/godot/apply_style.gd` sets StandardMaterial3D diffuse_mode TOON + specular off (Mobile renderer OK).
  The preview approximates toon with banded direct sunlight (three.js); not identical to Godot.

- background type `mothership` (part `hull` | `lights`, same `ship_id` so both layers line up): side-on alien capital
  ship hovering at `distance` / `azimuth_deg`, `length`, `elevation`, `heading_deg`. Background layers also take
  `fade_color` (haze towards the sky instead of the fog colour) and `emissive`.
- effect `flyby_ships`: small alien ships crossing the sky behind the background buildings now and then
  (`count, radius, height, azimuth_deg, arc_deg, speed, gap, size, color, glow`). Deterministic routes + ship meshes
  live in effects.json; the preview and `fx/godot/apply_effects.gd` (MultiMesh, untested in Godot) animate them with
  the same formula. Cost: one draw call per ship design, a few dozen triangles per ship.
- `flyby_ships` never pop in or out: each pass grows in from the distance and shrinks away again (size, distance and
  height follow a smoothstep envelope over the first / last 20 % of the pass; the formula is in `effects.flyby_paths`).

## Stage 12 additions (flow direction, elevator shaft, level exits)
- Liquids flow the right way: effects.json `liquid_flow` entries carry `flow_uv`, the measured downstream direction
  in the target mesh's glTF UV space (stream source -> sink, else straight down; projected through each triangle's
  position -> UV mapping). The preview and `liquid_flow.gdshader` (`flow_dir`) scroll along it, so any UV layout works.
- Material `"streaks": true` (toxic kind): long streaks along the fall instead of blotches (alien_cartoon role `fall`,
  used by `waterfall` structures without a material via the preset's `structures_material`).
- `"hole": r` on `box`, `cylinder` and `frustum` objects: a round vertical hole straight through, outline unchanged
  (`shapes.holed`, watertight). Give holed objects `"collision_mesh": true` so the collider stays concave.
- `elevator_shaft` (`pipeline/modules/transit.py`): sky_pylon platforms are cut down to where the underframe meets the
  column; solid platforms are cut `depth` m and their base is split (lower part stays solid). The shaft floor never
  goes below 0.3 m above the arena floor / hazard. Off-centre shafts are skipped with a note.
- level.json `"exits"`: `{id, type: "level_exit", target, shape: "cylinder", center, radius, height}` -> mobile
  `collision.json` `"triggers"` -> `apply_mobile.gd` builds an `Area3D` per trigger (group `level_exit`, meta
  `target`) and emits `level_exit_entered(target, body)`. Construct Error decides what loading the next level means;
  the preview only shows a toast and respawns.
- Per object `"mobile": {"static": true}`: small parts stay in the static merge cells instead of their own draw call.
