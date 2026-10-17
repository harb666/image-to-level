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
| `elevator_arrival` | Stage 15: round elevator car that comes DOWN into the level and rests at the centre of its platform (`on`, `offset` [0, 0]); `radius` (default 5.0), `car_height` (4.8), `comes_from` (previous level id), `travel_s` (6 s), `shaft` (m of shaft above the roof). Open between four posts, spawn with `"at": "<id>"`. See Stage 15. |
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

## Stage 13 additions (banners, organic falls, leaks)
- Banner materials can be an atlas: `"atlas": {"banner": [u0, v0, u1, v1], "drip": [...], "puddle": [...]}` (UV
  rectangles, v up). `"panel_cut": "pennant"` cuts every panel of the material into a swallowtail banner whose middle
  band shows the emblem at a fixed aspect (`emblem_aspect`, `emblem_band`), so the emblem never stretches on long or
  short banners. `"emblem": "<path from the repo root>"` uses an image (alpha, or everything that differs from the
  border colour); without it a procedural emblem is drawn. `emblem_color`, `cloth_glow`, `slime` tune the colours.
  Towers with strap bands centre the emblem between the bands (`emblem_at` on the banner panel).
- Panels take `"cut": "pennant" | "drip" | "blob"` (shapes.cut_panel) and `"uv_region": "<atlas cell>"`.
- Terrain waterfalls (`waterfall` on a world with terrain) are curved sheets (`stream` with a `grid`): every column
  finds its own lip, the top lies on the plateau with a ragged rounded edge, bends over the edge, and every row stays
  >= 0.85 m in front of the rock reaching down to the next row (no cliff pokes through). The sheet has its own UVs
  (v along the flow). `"organic": false` or an explicit `"y"` keeps the old straight sheet.
- `"leaks": {"chance", "material", "seed", "kinds", "max_drips"}` (alien_cartoon: chance 0.4, material accent):
  slime runs down one or two faces of randomly picked structures (reproducible), sometimes pooling at the base; they
  avoid banners, are visual only (collision false, navigation and colliders unchanged) and, on an atlas material,
  add no material or draw call (`pipeline/weathering.py`).
- `elevator_shaft` `"bottom": "void"` (default) | `"glow"`: void = the lower 70 % of the shaft is wrapped in a dark
  sleeve (panel cut `"sleeve"`) whose wall fades from the wall colour into pure black, with a black bottom and the lower
  light ring / strips removed, so the shaft reads bottomless. The black comes from the banner atlas cell `"void"`
  (`void_top`, `void_black`; ambient occlusion 0 there, so no sky light or reflection) - no extra draw call; levels
  without that atlas use a plain black `void` role. The preview's toon shading now drops direct specular, like the
  Godot toon style (`specular_mode disabled`).
- Printed crates: when the accent atlas has `"crate_front"`, `"crate_side"` and `"crate_top"` cells (alien_cartoon),
  every crate (`crates` structures and platform cover crates) is a plain box: grey hull, dark corner brackets with
  glowing pink triangles, edge rails with light strips; a maroon plate with a black glyph on one pair of faces (picked
  per crate, so stacks don't repeat), a plain plate with dash marks on the other pair, a glowing square lid
  (`box` `"faces": {"front", "side", "top", "front_axis"}`, shapes.box_faces, materials.crate_face;
  `crate_body`, `crate_plate`, `crate_glow`). It does not reuse the banner emblem. Same size / position, so colliders and cover are unchanged; one
  shared material (fewer mobile draw calls than before). `"outline": true` on an object forces an outline even if
  its material is in `skip_materials`.
- `elevator_shaft` `"dressing": "minimal"` (default) | `"full"`: minimal = plain hull lip, two insignia plates placed
  off-symmetry, one continuous outer light ring, four inner light strips of uneven length (no striped lip, no ring of
  light panels, no radial strips, no segmented inner light ring); full = the earlier, busier rim.
- Outline `"max_footprint"` (m): objects wider than this (decks, platform bodies, underframes) get no outline shell -
  on big flat pieces a world-space hull reads as a heavy black slab along the edges up close. alien_cartoon: 12 m,
  width 0.03-0.08 m (rel 0.008). The ink colour is sRGB and converted to linear for the glTF factor.

## Stage 14: nothing floats
- `Terrain.mesh_height(X, Z)`: height of the RENDERED terrain (LOD0 triangles, same diagonal rule as the chunks).
  The analytic `height()` is sharper at mesa rims and cliff edges (up to a cell further out), so props and waterfalls
  placed with it could hang off the visible edge. Scatter placement and terrain waterfalls now use mesh_height.
- Scatter `"edge_clear"` (m, default 1.6): an instance is placed only if the ground on a ring of that radius round its
  base stays within 0.8 m of the base (never on a ledge).
- Alien satellite props are whole: lights sit on bar ends / antenna tips / saucer rims, cross-bars pass through the
  stem, dishes sit in the saucer (tests/test_stage14.py measures the gap of every part).
- Terrain waterfalls narrow themselves when a column finds no edge near the lip height (small islands), keep the
  plateau part on the island, and are closed slabs (visible thickness from the side).
- Terrain waterfalls CLING to the cliff: columns ~2 m apart, a row every ~2.5 m of drop, each row 0.3 m (+ half the
  slab) in front of the rendered rock at its own height and the next row's (so it steps out above a ledge, never
  through it), the first ~4 m following the water's arc off the lip. No gap behind the sheet to see through. Lips are
  found on LOD0 (what you see up close); the rock to clear is the outermost of terrain LOD 0-2 (coarse chunks shown at
  distance can bulge past LOD0). All columns run down to one common bottom (no stepped, mid-air ends).
- Connection junction plates use the floor material of the platform they meet and sit 3 cm under its surface: hidden
  where they overlap the deck, read as the deck continuing where they fill the corner gap (no visible square).


## Stage 15: indoor arenas, elevator arrivals, multi-part levels
- `arena.ceiling` `{"opening": m, "thickness": 1.0, "beam_step": 12, "beam_depth": 1.1, "lamps": true, "material": "wall"}`:
  a roof slab on the wall caps (y = walls.height + 0.5) with an optional round opening at the arena centre (a real hole,
  concave collider), girders under it (they never cross the opening) and glow lamp panels in the bays. A roofed level has
  no background layers (art-style presets add none either), no sky drift or cloud effects, and the sun casts no shadows
  (`environment.json` `indoor`, `sun.shadows.enabled` false, manifest `directional_light.shadow_enabled` false) - the
  roof would otherwise shade the whole hall in Godot. Ceiling parts are tagged `"cutaway": true`: the preview hides them
  while the camera is above the roof (orbit / top-down views look in; third person inside sees the roof).
- `elevator_arrival` (`pipeline/modules/transit.py`): car = floor disc (0.25 m step) with a hazard-stripe edge, a light
  ring and an emblem; four posts on the diagonals (walk-off openings ~4-6 m wide); top ring, cross beams, hoist hub and
  cable. Under a ceiling opening it adds a lit shaft above the roof (liner, pilasters, light strips, winch, cap); the car
  starts 0.3 m above the roof slab (`start_offset_y`) hidden inside that shaft.
- level.json `"entrances"`: `{id, type: "elevator_arrival", comes_from, car, mobile_group, rest_position,
  start_offset_y, duration_s, spawn, radius, shaft_top_y}` (also in mobile `collision.json`).
- `"mobile": {"group": G}` on an object: the mobile export merges it per material into its own nodes `G__<material>`
  (manifest `kind: "group"`, `group: G`), never into the static cells. Used for the car (movable) and the ceiling.
- spawns `{"at": "<elevator_arrival id>"}`: stand on the car floor, facing south unless `yaw` is given.
- `"campaign": {"level", "part", "parts", "previous", "next"}` is copied to level.json: where the level sits in a
  multi-part level. Level 1 = `skyforge_arena` (part 1, its elevator exit targets `slime_arena`) -> `slime_arena` (part 2).

## Stage 16: factory hall dressing, windows onto the factory, smaller files
- Wall openings (rect arenas) are placed in their side's own coordinates (several per side work). `"sill": y` keeps
  the wall below the sill (a window, out of reach when the sill is > 3 m above the walkway) and adds frame bars
  (mullions ~5 m apart, transom, ledge; `"frame": false` to skip); `"height"` is the window top (lintel above).
- `pipeline/modules/factory.py` kinds:
  | kind | keys | |
  |---|---|---|
  | `vat` | `position` [x, z], `size` [D, H, D] (8, 20, 8), `sections` (10), `banner` | slime vat standing in the slime: plinth, red-lit bands, glowing glass (the hazard material, solid collider, not a hazard area), dark body with a banner facing the hall, cap |
  | `claw` | `position`, `length` (9), `y` (top; default the ceiling) | crane claw on two chain strands: hoist block with a red light, three prongs. Visual only |
  | `gallery` | `from`, `to`, `y`, `width` (3) | upper balcony along a wall: grate deck, railing + red light strip on the hall side, struts. Visual only (out of reach) |
  | `blast_door` | `position` [x, y, z], `facing`, `size` [W, H, D] | sealed door against a wall (frame, two striped leaves, lit seam, warning light): a future exit |
  All parts carry `mobile.static` (merged into the static cells: no extra draw calls) and reuse existing material roles.
- Background layer `factory_interior` (indoor levels; the only type kept under `arena.ceiling`): tank towers with
  glowing slime sections, tiered decks, gantries with hanging claws, pillars, pipes, roof and outer walls around the
  square `inner` (m) hole for the hall, out to `outer`; `floor_y` (slime sea), `roof_y`, counts `towers`, `decks`,
  `gantries`, `pillars`, `pipes`, `roof_lamps`, `factory_id` + `seed`. `part`: `hull` | `glass` | `lights` | `shell`
  (one material each = one draw call each; give the shell layer `"cutaway": true` so the preview hides it from above).
  Long pieces always run along the ring, never into the hall.
- File size (mobile export, automatic): `glb_tools.slim` writes 16-bit index buffers where possible, drops normal /
  occlusion / metallic-roughness maps from toon materials (flat toon shading never shows them; base colour + emissive
  stay), removes unused images and repacks the binary chunk. Tap-to-identify boxes for merged nodes moved out of the
  GLB into `mobile/pick.json` (preview only). Indoor levels render a 512 px sky (only ambient light uses it). Background
  meshes share corner vertices (faces stay flat). A level without background no longer keeps a stale
  `background_mobile.glb`. `package.py --game` leaves out `level.glb`, `background.glb` and `mobile/pick.json`.

## Stage 17: the Toxic Works (annexes, zone kit, exit door, size settings)
- `"annexes": [{id, center, size, floor?, walls {height, thickness, skip: ["south"], openings}, ceiling, walkway?}]`:
  extra rect enclosures built like the arena (slime floor, walls with windows / doorways, roof with girders + lamps),
  names prefixed `<id>_`. `walls.skip` leaves out the side shared with the arena: put the annex's inner edge on the
  arena wall's OUTER face and cut the doorway into the arena wall (`openings` with a `height`); the two roof slabs then
  meet edge to edge. Platforms inside an annex are fine (the "outside the arena" warning knows annexes).
- Zone kit (`pipeline/modules/factory.py`): `conveyor` (from/to/y/width/parcels: 0.75 m bed = low cover, rollers, lit
  edges, crates riding on it), `robot_arm` (position [x, y, z], pose [shoulder, elbow] deg or from the id, scale,
  pedestal m down to the slime), `lattice` (maintenance-shaft frame: posts, rings every 4 m, braces, lit ladder, service
  cage), `conduit` (from/to/y/width/height/step: arch ribs with light bars and a spine pipe over a walkway),
  `blast_door` `"open": true` (+ `"target"`: a `level_exit` trigger in the doorway and a dark corridor panel).
- `style.bevel_min` (m): boxes whose middle dimension is below it get no bevel (a bevelled box is ~44 triangles, a
  plain one 12; under toon ink lines the bevel of a thin part never reads). `style.outline.min_thickness` (m): no ink
  shell on thin bars (chains, mullions, braces, rails). Mobile cells sit on a grid centred on the level.
- `factory_interior` background: `extent` [x0, z0, x1, z1] (filled area) and `clear` (list of rects kept empty = every
  playable room incl. walls); long pieces run along whichever axis stays out of the rooms.

## Stage 18: immersive, non-repeating dressing
- `ceiling.style: "varied"` (+ `seed`, `pods` density factor): no grid. Main beams across the short span at irregular
  spacing (8-21 m), mixed I-beams and deep trusses (chords + alternating webs), split round the shaft; stepped
  ceiling sections hanging 1.6-4.2 m (some with red light strips); 2-3 ducts at different heights on hangers; 1-2
  ventilation fan rings; clusters of caged green lamp pods of mixed size and drop (bottom >= 4.5 m over any walkable
  surface below); sagging cable runs; scattered red light pairs. Built after the platforms (dress_ceilings). All
  visual: no colliders, cutaway, mobile group "Ceiling". `ceiling.material` sets the slab (e.g. "frame": dark).
- `walls.dressing: "varied"` (+ `dress_y`: the height where machines / doors / tanks sit): each inner face is cut into
  random 5-13 m slots, each gets a module never equal to its neighbour: `Pipes` (bundle + brackets), `Machine`
  (housing on a bracket + light), `Fan` (big wall fan), `Emblem` (painted banner), `Vent` (frame + slats), `Tank`
  (glowing slime window, solid), `Door` (sealed, lit frame + sign, at most one per wall), `Plain` (light strip); plus raised
  plates in other tones and stray red lights. Object names carry the kind: `<wall>_M03Fan_Hub`.
- Window openings `"fill": "slime"`: a giant slime-tank window (glowing, solid) instead of a view out.
- `column` (position, radius, height = ceiling): reactor column, slime-glass sections at irregular heights between
  banded drums with red lights, flared capital into the roof. `rock_face` (from/to along a wall, height, depth):
  jagged cliff slabs, the raw rock the factory was cut into.
- `style.bevel_min` raised to 2.5 m for this level: only big boxes keep their bevel (cheaper dressing).

## Stage 19: spinning fans, wall textures from the fan reference, inner-face fix
- Shape `fan_rotor` (size [diameter, depth, diameter]; `blades`, `sweep` deg, `pitch_root` / `pitch_tip`, `hub`,
  `solidity`): swept, twisted blades broad at the tip, stepped hub with a domed cap; shared vertices = smooth shading.
  `fan_unit()` builds the whole fan (housing ring + 4 clamps, glow disc, open grille of bars, rotor). Wall fans (wall
  module `Fan`, at most one per wall) and the varied ceiling's fan rings use it.
- Objects with `"spin": rpm` (sign = direction) get the effect `{"type": "spin", "targets": [...]}` (category
  `transform_animation`, per-target `speeds`): Godot `apply_effects.gd` calls `rotate_object_local(Vector3.UP, ...)`, the
  preview rotates the meshes. Rotors carry `mobile.merge: false` (own node: it must move) and no outline shell.
- Material kinds `wall_works` (irregular riveted plates from a recursive split, corner rivets, louvred vents, X-braced
  insets, pairs of green light dashes - emissive, conduit pairs, grime streaks) and `wall_slimed` (same plates + glowing
  slime drips and stains). alien_cartoon roles `wall_works` (tile 16 m) / `wall_slimed` (13 m); varied walls pick their
  body texture per segment and use them for raised plates, so stretches of wall differ in texture as well as in modules.
- FIX: `wall_segment` turned its decorated side (local +z) to the OUTSIDE of the arena; it now faces the inner point.
  Pilasters, banners and Stage 18 wall modules all sit on the inner face (modules also keep clear of the corners).
- Mobile cells start at the level's min corner (fewest cells: this level 1 x 2 at 160 m).

## Stage 20: see-through tubes with rising slime blobs, less green on the walls
- Material `"alpha": a` -> glTF alphaMode BLEND, double-sided (alien_cartoon role `glass`: faint green tint, alpha 0.22).
  Vat glass and column glass sections use it (`material` overrides) and carry `"tube": true`, solid colliders, double-sided.
- Effect `tube_blobs` (particles): glowing blobs of slime rising through the tubes every few seconds; one emitter per
  structure (a column's sections are one shaft), one merged particle system per tube-height group, lifetime from the
  height so blobs fade before the top.
- `wall_slimed`: fewer leak sources (`leak_threshold`, default 0.8), thinner drips, fainter stains; used on fewer wall
  stretches / plates. `wall_works`: fewer plates with green light dashes.

## Stage 21: ceilings from the user's ceiling reference
- Material kind `ceiling_works`: dark olive riveted plates in an irregular layout, rivet rows along seams, vent grilles
  of different sizes, X-braced panels, slot vents, conduit bundles with brackets, patchy moss grime. `"seed"` (any PBR
  kind) changes the layout: alien_cartoon roles `ceiling` (seed 1, 20 m tile) and `ceiling_b` (seed 2, 18 m) give each
  room its own roof. Varied-ceiling stepped sections use the room's `ceiling.material`.
- Varied ceilings add: hazard-striped beam ends, warm pill lights (`lamp` role) under beams at irregular spacing,
  conduit bundles (3-4 pipes) resting on hung trays, green capsule tubes in banded holders along the long walls,
  square recesses round the ceiling fans. Every part is offset so no two faces share a plane (no flicker).

## Stage 22: wall monitors
- Material kind `screen_ui` (fully emissive): purple control screen - radar circle with a green wireframe robot
  schematic (original design), dials and buttons, alien glyph column with a red horned emblem, grinning icon, dots.
  Drawn for 4:3 panels; alien_cartoon roles `screen` (seed 1) / `screen_b` (seed 2).
- Wall module `Monitor` replaces `Tank`: frame, screen panel, angular red corner caps, red top lights, side box with a
  light, feed cable up the wall (max 3.5 m).

## Stage 23: monitors that read as TVs
- Shape `tv_body` (size [w, h, depth]; `border`, `chin`, `radius`, `front`, `recess`): moulded bezel with rounded
  corners, recessed screen opening above a control chin, back plate, tapered CRT-style back housing; planar front UVs.
- Material kind `tv_casing` (laid out for those UVs): dark moulded plastic, lit edge bevel, shadow lip round the screen,
  corner screws, top vent slits, chin with speaker grille, badge plate, two knobs, power LED (emissive).
- `screen_ui` now has screen glass: scanlines, vignette, glare streak, pixel grid, rounded dark corners.
- Wall `Monitor` = tv_body + recessed screen panel + mount arms + red corner caps + cable; screens get a subtle
  `flicker` effect (CRT feel).

## Stage 24: alien viewscreens instead of green slime windows
- Material kind `bigscreen` (fully emissive, `"aspect"` default 1.7): `"mode": "broadcast"` = propaganda viewscreen
  (horned one-eyed emblem with rays, glyph headline and ticker, planet crosshair panel, status bars, warning triangles);
  `"mode": "specimen"` = green containment tank with bubbles, caustics and a one-eyed tentacled specimen on feed tubes,
  glare, glyph label, hazard edge. Both are original designs, scanlines and vignette on top.
- Material kind `screen_atlas`: `"left"` / `"right"` sub-materials rendered side by side in one texture (atlas cells
  `"a"` / `"b"`), so two looks cost one draw call. alien_cartoon roles: `screen` = two `screen_ui` layouts (wall
  monitors pick a half with `uv_region`), `bigscreen` = broadcast | specimen.
- Wall openings take `"fill": "screen"` or `"specimen"` (with `"frame": false`): a solid backing box fills the hole
  (collision), the `bigscreen` panel faces the room, red caps at the top corners and a light bar along the sill.
  Both screen roles get a subtle `flicker` effect.

## Stage 25: robot viewscreens, smallest mobile / game files
- `bigscreen` is about robots now: `broadcast` = a riveted robot head (antenna bolts, visor with two glaring red eyes,
  jaw grille) in a ringed target, a cog in a crosshair, a ticker of marching robot heads; `specimen` = a half-built
  robot (open chest with a power core, dangling arms, one eye booting) hung from feed cables in a green assembly tank.
  The sill light bar sits on the front face of the window ledge (it was buried in the ledge before).
- Mobile export: faces covered by one solid, opaque, always-visible box (not cutaway, not moving, not small props) are
  culled (`mobile.cull_hidden`, default true); textures re-encoded as WebP (`EXT_texture_webp`, profile `webp` quality,
  0 = keep JPEG / PNG); untextured outline meshes lose their UVs and are welded; mesh extras and node merge lists
  (`source_objects`) leave the GLB (manifest / pick.json keep them); identical buffer views / accessors are stored once.
- `package.py --game`: minified JSON rounded to 1e-4, editor-only lists omitted (counted under `"omitted"`), no
  `scene_spec.json`. Fixed: `environment.tres` was written empty in every package (opened for writing before reading).

## Stage 26: TV static on the screens
- Effect `tv_static` (category `material_shader`) on the `screen` and `bigscreen` roles: animated snow over the
  picture (cells change `fps` times a second, line jitter), a dark bar rolling down, and every `signal_every` seconds
  the picture breaks through for `signal_len` seconds. Godot: `fx/godot/tv_static.gdshader` set by `apply_effects.gd`
  as a material_override (one ShaderMaterial per screen material; no extra draw calls); the preview runs the same maths.
- Spec `"screens": {"static": 0.85, "signal_every": 6, "signal_len": 1.4}` - `static` is the share of snow over the
  picture (1 = snow only); `0` switches it off and brings back the old CRT `flicker`.

## Stage 27: open lift
- `elevator_arrival` takes `"frame": false`: the car is only its floor disc (hazard-stripe edge, light ring, emblem) -
  no posts, top ring, cross beams, hoist hub or cable. Slime Arena uses it. The shaft above the roof stays.

## Stage 28: corrosion where the liquid meets the walls
- Spec `"corrosion": {"height": 1.2}` (opt-in; also `sink`, `offset`, `tile`): every solid crossing a hazard pool's
  surface is cut there; its near-vertical faces that face open liquid (not pressed against a neighbour) get a strip
  2.1 cm in front, from 15 cm under the surface up to `height` m above it (never above the solid's top).
- All strips are ONE object `Corrosion_Band` (type `band`, mobile group `Corrosion`): one mesh, one material, one draw
  call; no collision, ignored by navigation and the open-body check.
- Material kind `corrosion` (128 px, cut-out: glTF alphaMode MASK, so no transparency sorting): rust-black pits with
  glowing green crust rims, stained metal, drips reaching up, a ragged top edge; denser towards the liquid.
- Fixed: the band texture was upside down (trimesh UVs are bottom-up and flipped on glTF export) - the dense
  corrosion now sits at the liquid line.
- No lights in the slime: bodies whose texture has lit panels (`unlit`, default `["structure"]`) get a plain
  `skirt_material` sleeve 1 cm proud from under the surface to `skirt` m (2.2) above it; base light strips and lamp
  panels (`..._Glow_<n>L/R`, `..._Light_<n>`) that start within `light_clear` m (1.6) of the surface are removed when
  short, or start that high when tall.

## Stage 29: wall textures merge into each other
- Varied walls keep their mix of textures (per segment, and raised plates in other tones), but a plate is now a worn
  panel 1.2 cm off the wall with a ragged, eaten-away outline (`panel` with `"cut": "ragged"`), so its texture
  dissolves into the wall's along an irregular edge instead of stopping at a straight line. `walls.plate_blend: false`
  brings back the old raised box plates. No new materials or textures.
- Objects with `"uv_space": "world"` (varied wall bodies, plates) get planar UVs from world metres instead of their
  own centre, so the same texture's pattern lines up across neighbouring parts; such meshes are never instanced.
- Side-door leaf 2 cm above its frame's bottom (no shared bottom face).

## Stage 30: outlets with a real opening, nothing hung in front of a pour
- `drain` / `spillway` pipes that leave a wall get a mouth (pipe `"mouth": false` turns it off): jambs, sill and lintel
  in that wall's own texture jutting 1.4 m from its face (placed on the face even when the channel starts inside the
  wall), a dark tunnel back (accent atlas `void` cell), a `structure_b` trim and a hazard stripe on the lintel. Visual
  only, no new materials.
- Wall modules (TVs, machines, fans, vents, emblems, side doors) within 3 m of an outlet's fall and below its top + 4 m
  are removed (`generator_notes` lists them).

## Stage 31: nothing hangs from bare ceiling
- `claw`: an overhead crane - an I-beam runway (hazard band on the web) runs wall to wall of its room along world x
  (`rail_yaw` turns it), 4.9 m under the roof (`rail_drop`), hung on rods every ~11 m; claws on the same line share it.
  A trolley rides the rail and the hoist chains hang from it. `"rail": false` (or a fixed `"y"`) = the old direct chain.
- Overhead pipe runs (`pipes` with `"kind": "run"`) under a roof hang on rods with clamps every ~8 m (`"hangers": false`
  turns it off); `vertical` outlet pipes get a feed pipe up into the roof with a roof plate.
- Stage 32: varied-ceiling cage lamps hang in rows from lamp rails (I-beams 3 m under the roof on rods, kept clear of
  crane runways and the lift shaft), never straight from the ceiling panels. `ceiling.pods` scales the count per room
  (Slime Arena: 1.6 in the hall, 0.35 in the Works wing).

## Stage 33: robot arms from the user's reference, glass lamp pods
- `robot_arm`: tapered octagonal base and turret, shoulder / elbow axles with glowing red discs, tapered angular links
  with red light strips on both sides, a spike on the back of the elbow, two sagging hoses, a tapered six-sided wrist
  housing with a red diamond light and side strips, and a three-finger claw (`claw_fingers`: upper segment angled out,
  tapered tip curling in, red inlays). Ceiling `claw`s get the same head (hoist housing + collar + fingers).
- Cage lamp pods: see-through `glass` shell with a glowing core from base to cap.
- Fixes: lights on tapered parts (claw housing, wrist, turret) lie on the faces (`face_light`), link strips are as
  thick as the taper, fingers have a knuckle joint and their inlays sit on the finger faces - no floating pieces.
  Lamp pods use a clear `glass_clear` shell with nothing inside.

## Stage 34: pipes the liquid can pass through, arms clear of everything, corrosion everywhere
- `column`: drums, neck and capital are rings (`hole` 0.8 r, `hole_res` 16) - the glass pipe's bore runs on through
  them up into the roof. Cylinders / frustums take `hole_res` (default 24) for the hole's resolution.
- `robot_arm`: picks the pose closest to `pose` whose links, wrist, claw fingers and hoses keep 0.25 m clear of every
  object already placed (`generator_notes` lists changed poses); pedestals sink 1.2 m below their stated base.
- Corrosion is ON by default (`"corrosion": false` turns it off) and reaches everything in the liquid or standing on
  its surface.
- Column plinths are rings too (the pipe reaches down into the slime). Lamp pods: the glass shell's ends sit 5 cm
  inside base and cap (no flickering lids), the cage is three corner posts outside the glass (no bars through it).

## Stage 35: shaft like the previous level, real wall vents
- `elevator_arrival` roof shaft: the same look as `elevator_shaft` "minimal" (Skyforge): plain structure_b lip, thin glow
  outer ring, two insignia plates (not symmetric) on the roof's underside, short light strips of uneven length near the
  mouth.
- Wall `Vent` module: a framed opening (four frame bars), dark duct behind it (accent atlas `void`), angled louvres
  every ~0.4 m and a status light - no flat panel of wall texture. Same placement as before.

## Stage 36: crates apart, wall fittings for pipes
- Cover crates on a platform keep 0.4 m apart (no crate inside another).
- Pipes leaving a wall (`pipes` on an arena wall, and `run` ends on a wall face) get a fitting: square mounting plate
  with four bolts, a hazard stripe and a red light, plus a flange collar; corner pipes get a thick boot and the collar.
  `"fitting": false` on a pipe turns it off.

## Stage 37: clean fans and vents, real bridge piers, no red caps on screens
- Ceiling fans are placed clear of girders / steps / anything under the roof. A clean-up pass (`clear_fixtures`) removes
  thin fixtures (hangers, cables, clamps, brackets, struts) cutting into a fan or wall vent, and removes a wall Fan /
  Vent module that anything bigger (crane rail, pipe run, gallery) runs through (`generator_notes` lists them).
- Bridge supports (`pier`): flared footing sunk into the floor / liquid, hull-plated column with ribs on both broad
  faces, flared head under the deck, red light near the top - instead of a plain block.
- Wall TVs and window screens lost their red angled corner caps.
- Stage 38: a crane runway whose end would meet a window screen, TV, fan, vent, machine, emblem, gallery or outlet mouth
  on the wall is cut back: to 5 m past the last claw on its line (or 2 m clear of the obstacle), with an end-stop
  block. Runways with nothing in the way still run wall to wall.

## Stage 39: yellow ceiling-fan light
- Ceiling fans glow yellow (role `glow_yellow`, emissive) and cast a soft yellow light: effect `point_light`
  (category `light`): one light per fan, 1.2 m under it, `color`, `energy` (1.0), `range` (16 m; 12 on
  performance). Godot: `OmniLight3D` without shadows (apply_effects.gd); preview: a three.js PointLight. Wall fans stay
  green.

## Stage 40: bottomless lift shaft, dark band round it
- The roof shaft over an `elevator_arrival` fades into pure black above its lit mouth (upside-down accent `void`
  sleeve, wider than the car so it passes inside it); pilasters stop where it begins; no winch.
- A plain dark textured band (`frame`) covers the roof between the shaft mouth and the glow ring (Stage 42 replaced the
  lip and insignia plates with a collar).

## Stage 41: gloomy wall fans, machinery stays on its deck
- Wall fans glow dark and dim (role `glow_dim`: deep purple, weak emission) instead of green; ceiling fans stay yellow.
- `machinery` banks placed `on` a platform leave out any part (vent / unit / tank) that would hang over the deck edge
  (`generator_notes` says which).

## Stage 42: segmented collar round the roof shaft (user reference)
- `elevator_arrival`'s roof shaft drops the hull lip and the two insignia plates; a collar (`structure_b`, shaft radius
  to +2.6 m) rings the mouth instead: 16 seams, four clamp plates (N/E/S/W) with a red light slot and a grille, four dark
  struts on the diagonals, eight small red triangle lights in dark recesses, and four red slots on plates outside that
  cross the glow ring. Visual only (no collision), existing roles; the car's floor emblem stays.

## Stage 43: barrels shooting up the reactor columns
- Every `column` carries a train of slime-green barrels with dark hoops up its bore, exactly 7 m apart (`"barrels": false`
  turns it off). Effect `tube_travel` (category `translate_loop`) moves them all up by `(t * 9 m/s) mod 7 m`, so the train
  looks endless: the lowest barrel starts hidden in the plinth under the glass and the top one leaves inside the capital.
- At rest no barrel face is level with a column face (the train slides a few cm until clear). Visual only; one mobile
  group `Tube_Barrels` for all columns (2 draw calls, ~3.8k triangles).

## Stage 44: no flags on the slime vats
- The slime arena's vats set `"banner": false` (the flat flag on a ten-sided body sank into its corners); the vat module
  default is unchanged for other levels.

## Stage 45: sloped bridges and ramps stand on real piers
- The single support under an elevated `ramp` connection (sloped bridge) is now the Stage 37 `pier` (footing, ribbed
  hull column, flared head, red light) instead of a plain block; its head is tilted to the deck's pitch and sits 6 cm
  inside the deck. The pier stands min(1.2 m, 15 % of the run) toward the high end, clear of the low landing.

## Stage 46: finished-looking sloped bridges and ramps
- Elevated `ramp` connections get hull cladding (`structure_b`) along both deck edges, top 3 cm under the walking
  surface and deep enough to hide the girders (no V-notch where the slope meets a floor), with a red `glow` strip along
  it; hazard-stripe (`stripe`) plates mark the top of the ramp and a flat caution mat lies on the lower floor at its
  foot. All visual only (no collision); landings stay clear.

## Stage 47: free cam starts at the player (preview)
- Switching the browser preview to "free cam" puts the camera 6 m behind and 3 m above the player, looking the same
  way (it used to start wherever the previous orbit camera was - far out in a corner). Respawn re-places it too.

## Stage 48: bubbling vats, no corner pours
- The see-through tubes (vats, reactor columns) fill with rising bubbles instead of the glowing blobs: effect
  `tube_bubbles` (one mesh for the whole level, animated in the vertex shader - `fx/godot/tube_bubbles.gdshader` in Godot,
  the same maths in the preview). Bubbles stream mostly from seven nozzles, speed up, wobble and grow as they rise, fade
  in at the nozzles and pop under the hood; glassy rim + two highlights, drawn before the tinted glass. Count per tube =
  density x height x radius (12..140; ~1,000 in this level at balanced, 0.4x / 1.6x for performance / quality).
  The insides cost ~7k triangles for the 16 vats (mobile level 3.8 MB, ~117k triangles, measured).
- Vat insides: a machined diffuser drum at the bottom (perforated grate, red-lit ring, six tapered nozzles round a centre one)
  and a funnel hood hanging at the top (ribs, vent grate where the bubbles end). Glass objects may carry
  `bubble_range` [from, to] (m above the glass base).
- `Pipe_NE` and `Pipe_SW` (the last corner pours) are gone from the slime arena.

## Stage 49: rippling slime, launched pods in the columns
- `liquid_surface` ripples, procedural in the shader (no textures, no meshes, nothing allocated): rings run out from
  every pour's impact (strong) and from the plinths / pier footings standing in the liquid (gentle), plus random drop
  ripples popping across the surface (off at "performance"). Each ring is a bright crest + a darker trough so it reads
  on the bright slime, and it bends the texture a little. Points come from the level: effect key `ripples`
  ([x, z, amplitude, radius], at most 24 per surface).
- Reactor columns: no bubbles (glass `bubbles: false`); the barrel trains are replaced by ONE pod per column - the
  ceiling lamp-pod model (cap, clear shell, three cage bars, base) full of glowing slime - launched up the bore at
  28 m/s every 2.6-6.2 s, each column with its own period and phase (effect `tube_pods`, category `launch`). It waits
  hidden in the plinth and vanishes into the capital. Own mobile group per column (`<column>_Pod`): +3 draw calls each.

## Stage 50: ceiling ducts stop short of columns and vats
- After everything is placed, a ceiling duct (`<room>Ceil_Duct_<n>`) that would run through a structure standing up
  from below (column - capital included -, vat, tower, machinery) ends 0.6 m before it; the pieces either side stay as
  separate ducts (`..._Duct_<n>b`) when at least 6 m long, each re-hung with a hanger near both ends. Crane rails and
  other hanging things are not obstacles. `generator_notes` lists the trimmed ducts.

## Stage 51: wall fitting on position-placed pipes
- A round / broken outlet pipe placed with "position" whose base sits on an arena or annex wall face (within 0.3 m,
  pointing into the room) now gets the same Stage 36 wall fitting as wall-side pipes (plate, bolts, hazard stripe, red
  light, collar) instead of the plain mount block - e.g. `W_Broken` in the works wing.

## Stage 52: every screen its own, plus an easter egg
- Screens are numbered per role (`screen`, `bigscreen`) and carry the number as a whole-number u shift of their UVs
  (object key `uv_shift`; the texture repeats, so the picture is unchanged). `tv_static` reads it: each screen has its
  own signal timing and length, roll speed, a slight tint, and quick brightness flickers at its own moments.
- Role atlases may be a 2x2 `grid` ([[top-left, top-right], [bottom-left, bottom-right]] - material dicts or
  {"image": repo path}) with cells a-d in the same texture size: the slime arena's TVs cycle three layouts (screen_ui
  seeds 1-3) and its window screens alternate two broadcast and two specimen variants.
- Role key `egg`: {"cell", "screen", "every", "len"} - that one screen now and then shows the atlas cell (here TV #2:
  `references/tv_easter_egg.jpg`, the user's GIR picture, ~4 s every 40 s, breaking through the static).

## Stage 53: no hanging pods in the slime arena
- Both slime-arena ceilings set `"pods": 0`: the glass lamp pods (and the lamp rails that only carried them) are gone.
  The pod model lives on in the reactor columns (Stage 49).

## Stage 54: bare lamp rails
- Ceiling `"lamp_rails": n` places n lamp rails (I-beams on roof hangers) even when `"pods": 0`; with pods it sets the
  rail count instead of pods / 6. The slime arena keeps its rails on their own for now: 4 in the hall, 1 in the works.

## Stage 55: no maintenance scaffolding
- `Maint_Lattice` (the 24 m lattice tower of posts, rings, cross braces, ladder and lift cage in the maintenance zone)
  is removed from the slime arena spec; it was decoration only (no route used it). The `lattice` module stays.

## Stage 56: the factory dug into glowing rock (user reference)
- `rock_face` with `"industrial": true`: pointed spires in front of the slabs (`spires`, 4), slime trickling from pipe
  spouts set into the rock (`spouts` - real pours: streams, splashes, steam and pool ripples; no mount block), metal
  ledges on brackets with red light slits (`ledges`, 3), and glass tube tanks standing in the pool with bubbling slime,
  a red band, a cap and an elbow pipe back into the rock (`tanks`, 2).
- Rock material `veins`: [r, g, b] paints a few long wandering cracks that glow (emissive, kept crisp through the toon
  pass, the rock lit green round them); `vein_width`, `vein_share`. Slime arena role `rock_veined` (256 px).
- Pipes accept `"mount": false` (no mount block when the base is buried).

## Stage 57: catwalk instead of the rock face, warm capsule lights
- Stage 56's industrial rock face is reverted and the slime arena's `Rock_West` rocks are gone (the `rock_face`
  `industrial` / `veins` options stay in the code, unused). In their place: two small pillar landings
  (`West_Landing_N` / `_S`, 4 x 6 m, top 10) and catwalk connections with guardrails - one from the Purification Deck,
  one along the west wall - so the walk is reachable (kept > 5 m from the wall TV so its top is not a jump target).
- Connections (and `walkway` structures) accept `lamp_posts`: n and `lamp_side`: +1 / -1 - warm lamps on posts along
  one edge (hood + `glow_yellow` bulb), each with a soft yellow point light (effect Fan_Lights).
- Ceiling `capsule_role`: the material of the capsule tubes under the roof - the slime arena uses `glow_yellow` (like
  the ceiling fans) instead of green.
- Corrosion band: thin posts (footprint <= 1.5 m) get their strips 4.5 cm out instead of 2.1 cm (their short faces'
  strips twist when chained and came within 5 mm of the post).
- The corrosion band is double-sided from the start (the validated build's camera check saw its back past the catwalk
  legs and had to repair it).

## Stage 58: conduit spine sinks into the slime
- `conduit` `"spine_out": "to" | "from"` (+ `spine_ext`, default 6 m; `spine_drop_y`, default 0.2): the spine pipe over
  the tunnel ribs runs on past that end, out over the slime, meets a corner block and drops straight down into the
  liquid (its bottom under the surface - it vanishes; the corrosion band marks the slime line). The slime arena's
  `Conduit` uses "to" (the north end; the south end has the ramp).

## Stage 59: armoured portal + laser gate into the Works (user reference)
- `blast_door` with `"open": true, "portal": true`: a portal round the doorway drawn from the user's reference -
  pointed armour pillars (back plate, front plate, slanted red light panels, side fin with a light slit, red strip on the
  jamb), a header with angled corners, two recessed panels and an inverted red trapezoid light, a red lamp hanging under
  it, hazard-striped plates low on the wall. Built from the new convex `prism` type (`poly`: [[x, y], ...] extruded
  along z). Proportions scale with the door height; the slime arena's gate is now 12 x 6 m so the portal fits under
  the north gallery (its three struts there are removed: `clear_portals`), and `Pipe_North` is gone (it ran through
  the right pillar; moved it would pour into a vat).
- `"laser_gate": {"id", "beams", "opens_on"}`: seven red laser beams + emitter strips across the doorway (role `laser`,
  flickering; own mobile group). Visual only in the level - navigation sees the doorway open - and level.json `gates`
  (copied to mobile/collision.json) tells the game: a blocker box stands there while closed, `opens_on` names the
  encounter. Top-level spec `encounters` ([{id, waves, enemies_per_wave, spawns, opens, trigger}]) pass straight to
  level.json / collision.json: the slime arena's `Hall_Waves` = 3 waves (4 / 6 / 8 enemies) from the hall's enemy spawns,
  starting with the level; clearing it opens `Gate_Works_Laser`.
- Godot: `apply_mobile.gd` builds the blockers (StaticBody3D, group `laser_gate`) and offers `open_gate(id)` (beams
  stutter out, blocker removed, signal `gate_opened(id)`). Construct Error runs the waves and calls it. The preview has a
  "Gate" button to see it open or closed (the preview never blocks the player).

## Stage 60: conveyor rollers on the pool side
- `conveyor` `"roller_side": +1 | -1` - which local side (x) the end rollers stick out of the bed (default -1, as
  before). The slime arena's `Conv_West` uses +1, so both assembly-line conveyors show their rollers towards the slime.

## Stage 61: working assembly lines
- `conveyor` `"working": {"speed", "spacing", "machine", "stations": [{"arm", "task": "add" | "inspect", "at"}]}`: an
  intake machine over the start of the belt (housing, dark mouth with rubber curtain strips, hazard-striped frame,
  yellow lamp, hopper of glowing slime) and an output machine over its end (red lamp, vent stack with a red ring).
  Identical parcels (11 per line here) ride the belt; effect `assembly_line` slides them by (t * speed) mod spacing, so a
  new parcel pushes out of the intake curtains as the last one disappears into the output (both inside the housings).
- `robot_arm` `"reach": [x, y, z]` turns the arm to that point and solves its pose (two-link IK, elbow up) so the claw
  tips rest there; `"task"` makes the upper arm its own moving group (3 materials). An "add" arm holds a glowing
  canister between its finger tips; an "inspect" arm carries a translucent yellow scan beam (role `scan`).
- Per station, every parcel carries the station's part - a canister set into its lid (add) or yellow approval lights on
  both sides (inspect) - revealed by a world clip plane at the arm: the part appears exactly as its parcel passes under
  the arm, which dips at that moment (angle solved so the canister lands on the lid / the beam reaches it), its held
  canister vanishes at the drop and returns before the next parcel; the scan beam shows only while the arm is down.
- Godot: `apply_effects.gd` (category `assembly`) moves the `<group>__*` nodes and puts
  `fx/godot/assembly_reveal.gdshader` on the parts; the preview does the same with three.js clipping planes. Cost: ~22
  extra draw calls for both lines (moving groups), ~2.7k triangles.

## Stage 62: scarce parcels, parts placed rather than conjured
- The slime arena's lines use `"spacing": 7.0` (4 parcels per line, ~7.35 m apart, one every 7.35 s).
- Parts no longer sweep into view through a clip plane: each part's UVs carry its parcel's number (u shifted by 10 per
  parcel) and the shader shows the whole part at the instant its parcel's centre reaches the arm - the same instant the
  arm's held canister disappears at the bottom of its dip (and the scan beam lands). Reveal data: `s0`, `spacing`,
  `s_arm`, `id_step`; the slide offset is fed in every frame. Dips are slower (1.8 s add, 2.2 s inspect).

## Stage 63: wider walkway, canister bins, real scanners, rust that updates
- The assembly-line conveyors moved out to x = +-4.7 (7.4 m of walkway between them instead of 5.4); the machines are
  narrower so they stay on the deck.
- `robot_arm` "task": "add" + `bin_yaw` (deg): a small bin stands beside the arm, the same reach away, turned bin_yaw about
  its base - ring body on a post down into the slime, glowing rim, hazard band, black floor deep inside (reads
  bottomless) and canisters waiting in it. After each drop the arm turns to the bin, reaches in (canister back in the
  claw at the bottom of that dip) and turns back before the next parcel (effect keys `bin_yaw_deg`, `bin_angle_deg`,
  `turn`, `bin_window`).
- "inspect" arms: a yellow lens under the wrist, the scan beam, and a laser frame round the parcel that sweeps up and
  down twice while it scans (`ring`, `ring_travel`, `sweeps`; scan window 2.6 s).
- Repairs no longer freeze generated objects: `refine.adopt_repairs` records the repaired state in gen_state.json, so the
  next generation rebuilds them (and the repairs run again). The corrosion band had been frozen since an old camera
  repair - so the moved arm pedestals had no rust; 27 such objects were reset. Two generator-level overlaps the repairs
  had been hiding are fixed at the source: ramp / stair junction blocks are 6 cm wider than their deck, wall-pipe
  brackets stand 6 cm proud of the pipes.

## Stage 64: no black slabs on the west crane arms
- Cause: the mobile export stores identical index lists once (trimesh), and the mirrored east / west arms' outline
  shells (`Arm_N_Upper__ink`) have the same triangle list. `glb_tools.slim` welds untextured (ink) primitives; welding
  the east arm rewrote the shared list in place, so the west arm kept its own vertices with the east arm's new
  indices: scrambled triangles, some facing out = dark slabs over the moving arms (preview and Godot alike).
- Fix: `slim` gives a primitive its own accessor + buffer view before rewriting data another primitive still uses;
  originals nobody reads any more are dropped. Measured: all 121 nodes of level_mobile.glb have the same oriented
  triangles before and after `slim`, and each arm's outline matches its level.glb shells exactly.

## Stage 65: every joint of the working arms moves
- Each working arm is skinned to its own skeleton (level.json `skeletons`): turret yaw, shoulder, elbow, wrist pitch,
  claw twist and three fingers. Parts carry `mobile.joint` (rigid) or a joint pair + `blend` line (the hose cables
  bend with the arm). The mobile export welds skinned groups per part only and writes JOINTS_0 / WEIGHTS_0 + the
  skin (`glb_tools.add_skins`); same draw calls as before (121), the turret now turns with the arm.
- The effect's station `rig`: bone names, rest-world axes, IK offsets [shoulder, elbow] that lower the claw straight
  down to the parcel (`dip`) and into the bin (`bin`), and an idle seed. Runtime (apply_effects.gd = viewer.html):
  wrist = -(shoulder + elbow) so the claw always hangs; adders twist the claw a third of a turn as they set a canister
  in, open the fingers to let go and close them on the next canister; scanners twist the head to and fro over the
  parcel and flex their fingers; every arm sways a little at turret, shoulder, elbow and wrist between jobs (damped to
  nothing while placing / picking). Measured in the test: at the dip the held canister moves < 2 cm sideways.

## Stage 66: the arms move like real machines
- No more idle sway or cosine "bobbing": each arm runs a motion program (`pipeline/arm_motion.py`, one cycle per
  parcel) of servo moves with a smootherstep profile (zero speed and acceleration at both ends of every move:
  jerk-limited, nothing bounces), holds that stand dead still, and every joint angle solved by inverse kinematics
  (turret yaw faces the wrist, two-link shoulder / elbow, wrist levels the claw).
- Adders: wait upstream over the belt -> accelerate to belt speed over the incoming parcel (conveyor tracking) ->
  straight down onto it -> set the canister in with a third of a turn of the claw, fingers open -> straight up ->
  brake -> coordinated swing to the bin -> straight down in, fingers close on the next canister -> straight up ->
  swing back upstream and wait. Scanners: ride along with the parcel, the head sweeping 35 deg each way while the
  beam and the laser frame (riding with the parcel too) scan it, then return upstream.
- Belts run at 0.8 m/s so a full adder cycle (7.75 s) fits between parcels; a note warns if a program does not fit.
- The same maths in Python (reference + tests), apply_effects.gd and viewer.html. Measured in tests: the preview's
  joint angles equal the reference to 1e-9; through the exported skeleton the canister sits within 1 cm of the
  moving parcel while it is set in; no joint jumps or velocity jumps at 240 Hz sampling; waiting = no motion at all.

## Stage 67: rigid links - no more stretching
- Cause of the "compressing / uncompressing": the arm parts were all built with one shared `mobile` dict, so the joint
  written last went to every part. In Stage 65/66 that was the hose cable's blend (shoulder -> wrist), so the whole
  upper arm was skinned as a blend between shoulder and wrist and stretched like a piston as the arm moved. Each part
  now gets its own copy: links, discs, wrist, claw and fingers each sit rigidly on their own joint (weight 1).
- The hose cables are gone from the working arms (a cable spanning a moving joint has to stretch); static arms keep them.
- The arms stand 1.2 m further back (x +-8.6) and are larger (adders 1.2, scanners 1.3) so the moves come from big,
  readable shoulder / elbow / turret rotations at a comfortable reach: measured max 92 % of full stretch over the cycle
  (`arm_motion.reach`; spec_to_level notes any arm over 93 %).

## Stage 68: wall fans over the Works gate, running belts
- New structure `wall_fans` (`modules/factory.py`): big fans set into a wall face (group on the face, local +z out of
  it, "yaw"), "fans": [[x, y, radius], ...], a louvred vent under each (`architecture.louvred_vent`, now shared with the
  wall dressing's vent module). Each rotor is its own node and spins (effect `spin`). slime_arena: `Lintel_Fans`, two
  1.7 m fans in the hall-side face of the wall block above Gate_Works (+2 draw calls for the rotors).
- Working conveyors give their belt its own material `belt` (falls back to the grate look); the assembly line effect
  carries `belt: {material, scroll}` and the runtimes move that material's UV offset by scroll * t (Godot
  `uv1_offset`, preview `map.offset` on its own texture object) - the surface runs with the parcels instead of the
  parcels gliding over a still belt. scroll = -axis * speed / tile on world (x, z) UVs; measured in the preview: belt
  pattern and parcel move the same way by the same amount (5 vs 6 px in 0.06 s, top-down; the parcel top is nearer).

## Stage 69: arched slime tunnels through the north wall
- Spec `tunnels`: [{id, x, z: [z_from, z_to], width, crown, floor, liquid}] -> `architecture.bore_tunnels` (after the
  modules, before slime decals / corrosion). Every unrotated box crossing the bore is split at x +- (width / 2 + 1.2);
  boxes reaching from the floor over the crown are refilled with a `round_arch` (opening `width`, round top at
  `crown`, flagged `waterway`: the openings check accepts liquid in it) + a plain box above; boxes in the opening's
  height band are only split; boxes above the crown are untouched. A pool gap inside the bore is closed by stretching
  the nearer pool box (slime_arena: HazardFluid_2 now reaches z -56 - the two pools join through the bores).
- Dressing (visual only): each mouth - 9 voussoirs with a raised keystone (lit inlay), a glowing yellow halo round the
  stones, jambs, impost blocks, pilasters with capitals and lanterns; ribs with a lamp under each crown through the
  bore; the corrosion pass dresses the inner waterline like every other wall.
- slime_arena: Tunnel_West (x -28, under window Op1) and Tunnel_East (x 28, under Op3), 6.6 m wide, crown 4.95 m,
  9 m long (wall + hall walkway base). The walkway's floor / trim / walkable area are unchanged (measured: same
  walkable entry, same reachable area 9620 m2); the arena-side dressing stays under its trim (top 5.85 m).

## Stage 70: omit list, big domed tank in the Works pool
- Spec `omit`: names / fnmatch patterns of generated objects to leave out (children go too; a note lists patterns
  that matched nothing). slime_arena drops the red light strip of Works_Wall_East_03's plain stretch and the small red
  lamp beside its banner.
- `Tank_Slime_East`: the domed barrel tank (same model as Tank_North / Tank_South), 7 m across and 11 m tall,
  standing in the Works pool in front of that wall (corroded at the waterline like everything else in the slime).

## Stage 71: twin domed tanks with ductwork to the ceiling
- `tank` structures take `duct`: {"to": ceiling underside y, "radius", "flange_every"} -> group `<id>_Ductwork`: a
  collar seated in the dome, a round duct (pipe material, like the ceiling ducts) from the crown 30 cm into the
  ceiling, flange rings every 2.6 m (`_Duct_Rib_<k>`), a boot 2 cm into the slab and four hangers.
- slime_arena: `Tank_Slime_East_2` (7 x 11 m) beside `Tank_Slime_East` in the Works pool; both ducted up to the
  Works ceiling slab (26.5 m).

## Stage 72: the crusher - jump across, don't get flattened
- New structure `crusher` (`modules/factory.py`): a hydraulic column out of the pool (flared foot, ribs, brace) to a
  square pad (`top`, `pad` m, hazard-striped rim, side lamps; walkable), a ram housing hung from the ceiling
  (`ceiling` = underside y; mount plate, ribs, red warning lamps in group `<id>_Warn`) and the ram (press head with
  striped sides + rod, mobile group `<id>_Ram`, rest gap `travel` m over the pad).
- Effect `crusher` (same timing in apply_effects.gd and viewer.html): per `period` s - rest, `warn` s of blinking
  lamps, a 0.22 s accelerating slam, 0.45 s pressed, a 1.2 s eased climb back. Kill zone = the pad's footprint up to
  2 m above it (level.json / collision.json `crushers[].kill`); it is deadly while the head is lower than 1.8 m over
  the pad (Godot: an Area3D in the `hazard_group`, its shape enabled only then; preview: respawn + "Crushed!").
- slime_arena: the W_Cat_Pipes catwalk is gone; `Crusher_A` stands between Assembly_Line (7 m) and Pipe_Junction_A
  (9 m): pad top 7.8 m (the deck's trim lip is 6.67 m: a 1.13 m jump up, then 1.2 m up to the junction - the nav
  check finds both jumps both ways), every 4.5 s, 1.9 s of safe time per cycle before the warning.

## Stage 73: purifiers spaced out, green down to the deck
- `vat` takes `base` (plinth height, default 3 m); a lower plinth hands its height to the glass (same overall height).
- slime_arena: Purifier_1 / Purifier_2 moved apart (centres 7.3 m, plinths 2.8 m clear) and given a 0.8 m collar - the
  green glass with its bubbles now starts 1.7 m over the deck instead of a 3 m dark plinth.

## Stage 74: background tank towers reach their bases, none overlap
- `backdrop.factory_interior` towers: the dark base stands from the slime sea to 6 m over it, but the first glowing
  section started at y 6 - an 8 m gap (the tubes floated over their bases). A glowing section + band now fill it, so
  the green runs down onto the base. Towers that would overlap an earlier one are pushed straight away from it (or to
  its other side if that spot is not free). Both changes draw no extra random numbers: the rest of the backdrop
  (decks, gantries, pillars, pipes, lamps) keeps its layout. slime_arena: the overlapping pair east of the Works
  (bases 1.8 m into each other) now stands 3.5 m apart.

## Stage 75: room to move on Pipe_Junction_A
- The crusher records a landing on every deck within a jump of its pad (cover crates keep out of it).
- Pipe_Junction_A: Valve_A (machine unit + tank) pushed into the corner along the north edge; the platform's cover crate
  replaced by one `crates` crate tucked into the far (south-east) corner; the deck is open from the crusher landing to
  the catwalk to Pipe_Junction_B (nothing within 1 m of that line), the crate is there to jump on.

## Stage 76: the pipe leaves through the window; no dome on the junction
- W_Run_North no longer stops at a plate in window Op1 of the Works' west wall: it runs out through the opening
  (y 16: between the sill at 13.5 and the transom at 19; z -112: between the opening edge and the first mullion),
  turns down outside the building and ends in the background slime sea (y -9), below the window line - out of view.
  Pipe runs no longer hang rods outside the arena / annex footprints (no roof there).
- Valve_A_Tank (the domed barrel on Pipe_Junction_A) is omitted (spec `omit`).

## Stage 77: exit hallway, raised bigscreen
- Structure `exit_hall` {id, position (on the wall's room face, floor y), yaw (local +z into the room), wall (thickness, 4),
  length (14), width (6), height (7), target}: an arched doorway is CUT through the wall (`ctx.cuts` ->
  `architecture.cut_doorways`: y-turned boxes crossing it are split beside / under / over it, small dressing in it is
  removed) and framed by a round arch + the tunnel-mouth dressing (`architecture.arch_dressing`: voussoirs, lit
  keystone, glowing halo, jambs, imposts, pilasters, lanterns). Behind it a short floored hallway fades to pure black
  like the elevator shafts: "void"-region fade panels on the floor, walls and ceiling (wall colour at the door end ->
  black at the far end) and a black end wall; ribs with lamps in the lit part only. Walking into the dark end is the
  `level_exit` trigger. Panels take `cut: "rect"` (plain rectangle with its own UVs) where the material cuts panels.
- Objects may set `bevel: false` (no bevel whatever the material says).
- slime_arena: `Exit_Hall` replaces the old Exit_Door (-> level1_part3); the Works' east bigscreen opening sits 2 m
  higher (sill 16) so the screen clears the wall decals.

## Stage 78: conduit arches removed, its pipe into the ceiling
- slime_arena: the `Conduit` arches over Conduit_Walk are gone; their spine is now the pipe run `W_Conduit_Pipe` at the
  same height (y 15.6), hung from the ceiling, rising straight up into the roof slab at both ends (nothing drops into
  the slime). Doorway cuts take an optional `floor` y: floor decks reaching the wall are not split by the cut.

## Stage 79: walk check on every connector, shaft ramp, stale pieces dropped
- `pipeline/traverse_check.py` (run by checks.py, report kinds `traverse_*`, output `checks/traverse.json`): walks every
  connector (ramp, stairs, bridge, catwalk) with the player capsule in 0.1 m steps, up AND down, on
  `mobile/collision.glb`: blocked (edge / lip above step height), steep (> max_slope_deg for 0.2 m), fall (gap), head
  (headroom), scrape (side contact). Centre lane problems are errors, edge lanes (hugging the rail) warnings.
  Measured on slime_arena: all 25 connectors pass both ways (PLACEHOLDER player values from gameplay.json).
- slime_arena: `W_Stairs_Shaft` (between the maintenance towers) is a ramp (35 deg). Elevated ramps that start ON the
  lower floor put their girders under the open span only (none inside the floor / in its landing).
- Regeneration merge: a generated object the generator no longer makes, changed only by an automatic repair
  (`autofix`), is dropped instead of kept as a hand edit (stale banners left by older wall layouts - incl. the one
  beside the Works bigscreen - are gone).

## Stage 80: pads rising out of the slime, control terminal, gated exit
- Structure `rising_pads` {id, position, from / to ([x, z], the two floor edges), y (pad tops), count (10), pad_size (2.8),
  zigzag (1.2), steps (height offsets), liquid (surface y), trigger ([x, y, z]), trigger_radius, stagger, rise_s}:
  stepping-stone pads (hex column, octagonal deck cap, glowing rim, a slime surge disc at the surface). ALL pads are
  one skinned mesh per material (skeleton `L.skeletons[id]`: one bone per pad + one per surge disc) - the memory and
  draw calls of a single prop. They start under the liquid; a player entering the trigger sphere makes them surge up
  one after another (effect `emerge`, data `L.risers`: same timing in apply_effects.gd and viewer.html), each pad's
  collider is enabled once it is up. collision.glb / the checks see the raised pads.
- Structure `control_terminal` {id, position, yaw (front = local +z), activates [gate ids], radius}: console with a
  monitor (own screen id), button, beacon; `L.terminals` -> collision.json; apply_mobile.gd `activate_terminal(id)`
  opens its gates (signal `terminal_activated`). The preview uses it when the player walks up to it.
- `exit_hall` takes `laser_gate` {id, beams, opens_on} (beams across the arch, closed at start).
- Skin weights are stored as normalized bytes (4 B / vertex instead of 16; glTF-valid) - every skinned mesh.
- slime_arena: the long west catwalk is gone; `Pads_West` rise from the Works pool between West_Landing_N and
  West_Landing_S (gaps <= 2.6 m, steps <= 0.6 m), `Works_Terminal` at West_Landing_S opens `Exit_Hall_Laser`.

## Stage 81: easier pad route
- `rising_pads` spaces pads with EQUAL gaps (between pads and to both floors) instead of evenly spaced centres.
- slime_arena `Pads_West`: 11 pads, 3.4 m across, all at y 10, zig-zag 0.7 m: every hop is ~1.4 m edge to edge
  (floors -> first / last pad 1.2 m) - was up to ~2.7 m with 0.6 m height steps.

## Stage 82: turbine fan under the Works bigscreen
- Structure `turbine_fan` {id, position (wall face, floor y), yaw (local +z into the room), diameter (5.2), depth (1.4),
  length / spread (wind cone), push (m/s), lift (m/s^2 while airborne), ramp / blast / calm (s), phase, rpm, blades}:
  hazard-framed plate, deep housing with clamps and a solid plinth, red furnace glow, broad rotor (own node), guard bars;
  wall dressing in its footprint is cleared. `L.winds` / effect `wind` (apply_effects.gd `_wind`, viewer.html): the
  blast cycles (spin-up, blast, spin-down, calm); in the cone a CharacterBody3D is moved along the wind faster than it
  walks and lifted while airborne (a jump / double jump only carries it further out); streak particles while it blows.
- slime_arena `Turbine_East`: under the east bigscreen over Conduit_Walk (z -125.5), 18 m cone, 9 m/s, 3 s blasts and
  2.5 s calms - time the dash past it to the exit. (A preview-only fan another session had put in the main arena's
  south wall is replaced by this pipeline one.)
- Mobile: skinned untextured primitives (ink shells of arms / pads) drop their unused UVs.

## Stage 83: ducts stop short of crane runways
- `clear_ducts`: a crane runway beam crossing within 5 m of a ceiling duct's end shortens the duct to stop 1.2 m
  before it (mid-span crossings stay). slime_arena: Works_Ceil_Duct_2 no longer runs into CraneRail_06 (and the
  arena's Ceil_Duct_1 ends 1.2 m before CraneRail_02).

## Stage 84: duct ends finish at a beam
- `clear_ducts`: a ceiling duct end sticking out 0.3 - 3.5 m past the last ceiling beam it passes under is cut back to
  end at that beam (no short stub hanging in the air). slime_arena: Works_Ceil_Duct_1 (-1.7 m) and the arena's
  Ceil_Duct_1 / 2 / 3 ends (-2.7 / -1.7 / -2.4 m).

## Stage 85: turbine = mouth of an endless duct; blows until the pads are crossed
- `turbine_fan`: the wall ("wall" m) is cut behind it and lined with a `sleeve12` void panel (wall colour at the mouth
  -> pure black): the fan reads as the end of a huge endless duct. Plain dark steel frame + corner plates instead of
  the hazard stripes and back plate; no red furnace glow (two small red warning lamps stay).
- `stop_at` [x, y, z] (+ `stop_radius`, `spin_down`): full force until a player enters that sphere, then it spins down
  for good (apply_effects.gd also has `stop_wind(id)`). slime_arena: Turbine_East stops when a player reaches
  West_Landing_S (the rising pads crossed) - until then the walkway past the screen is blown clear.
- Panel cut `sleeve<n>`: n-sided sleeve; `fan_rotor` `detail: "low"`: coarser blades for big fast rotors (memory).

## Stage 86: exit doorway stands out
- `arch_dressing(look=...)`: stone / pilaster material, voussoir depth, halo width. The exit doorway uses machinery-panel
  stones, jambs and pilasters, a dark metal frame and a 0.24 m halo - in the wall's own hull plating the stones read as
  a see-through outline. Jambs keep 2 cm off the frame's faces (no flicker). Red guide strips along the hall walls
  replace the floor-edge strips; the doorway hazard mat and the turbine's red lamps are gone (mobile budget).

## Stage 87: round turbine, sculpted terminal
- `turbine_fan`: no wall cut, frame or corner plates - just the round housing (lined inside with the `sleeve12` void
  fade, black at the back: the end of an endless duct), clamps from the wall to the rim and a narrow pedestal.
- `control_terminal`: one sculpted body - side profile (pedestal tapering forward, sloped desk with a nose, a screen
  tower leaning in) as three convex machinery-panel prisms over the full width; screen set into the tower, glowing edge
  lines, lit hand plate in the desk slope, a light bar crown, an octagonal floor plate with a glowing rim.

## Stage 88: domed vat tops, invisible window barriers
- Shape `dome` (faceted spherical cap, `sections`, 3 rings). `vat` tops: a dark `frame` rim under a dome (no striped
  trim lid seen from above) - every vat, purifier and processing tower.
- Every plain arena window (`sill`, no `fill`) gets an invisible `boundary` collider filling the opening
  (`<wall>_Op<k>_Barrier`, in collision.json); the preview's player collides with level.json `boundary` objects.

## Stage 89: rising shotgun platform
- Structure `rising_platform` (`position`, `y` deck top, `diameter`, `liquid`, `trigger` [x, y, z], `trigger_radius`,
  `rise_s`, `pickup` {id, item, radius}, `drip_count`, `strands`): one round platform on the `emerge` rig (one bone + a
  surge ring) - 16-sided deck, a heavy lip with a glowing band, a rounded bowl underneath on a column, a pedestal with a
  lit top in the middle, slime drips (accent atlas `drip`) on the lip's flats and goo strands pouring into the pool.
  Its riser pad lists `drips` (rim points: falling drops once it is up) and `pickup`. level.json / collision.json
  `pickups`: [{id, item, center, radius, riser}].
- `Shotgun_Platform` (8.4 m) with `Shotgun_Pickup` (shotgun) over its pedestal - placed in Stage 90 (below). The preview drops goo and shows a yellow marker
  where the item goes (the marker is preview-only).
- Mobile budget: small wall / ceiling fan rotors use `detail: "low"` (lighter blades and hub).

## Stage 90: conveyor -> shotgun platform -> crusher -> Pipe_Junction_A
- `Shotgun_Platform` rises at the south end of Assembly_Line (deck 7.5 m, 1.8 m jump off the conveyor platform's
  edge) when the player walks to the end of it (trigger [0, 7, -102], r 6).
- `Crusher_A` moved to [-5.2, -121] (pad 8 m, 1.6 m from the platform), hanging from the roof slab (ceiling 26.5)
  clear of the W_Run_High pipe and the ceiling conduits; `Pipe_Junction_A` moved to [-13.6, -124.5] (1.8 m hop
  west of the pad, > 5 m from the platform: the crusher can't be skipped); its catwalk to Junction B follows.
- The pedestal's base plate is visual only (12 cm, no collider): not a narrow ledge for the nav check.

## Stage 91: the platform's goo drains away, red band set back
- `rising_platform`: the drips and strands hang on their own bones (`<id>_GD`, `<id>_GS`, children of the platform
  bone); riser pad `goo` {drips, strands, hold, fade}: `hold` s (4) after the platform is up the goo drains away over
  `fade` s (2.5, smoothstep) - drips shrink up off the lip while sliding 0.6 m down, strands fall into the pool (shrink
  to their bottom) and thin out; the falling drops stop (preview: they fade). Spec `goo_hold`, `goo_fade`.
- The glowing band runs round the deck edge above the lip (diameter D + 0.06, inside the lip's D + 0.36): it no longer
  sticks out in front of the slime.

## Stage 92: GIR in cryostasis (external models), plain materials
- Object type `model` (`file`: a parts GLB, `part`: its mesh name; height = size[1]) and structure `specimen`
  (`model`, `parts` {part: material role}, `height`, `position` = feet, `yaw`, `amp`, `period`, `sway`): a model
  floating in a tank; its parts are one mobile group `<id>_Float` the `bob` effect drifts (up / down + slow sway round
  its middle; apply_effects.gd and the preview). Visual only, `intentional: ["floating"]`; the shell checks skip `model`.
- `pipeline/model_asset.py`: source GLB -> static parts GLB (rest pose, feet at 0, unit height, parts grouped by source
  material, decimated per part). For a skinned source bake the pose first (the skin is ignored).
- `Gir_Specimen` in the middle of Core_Vat (3.6 m, red eyes): `levels/slime_arena/assets/gir_parts.glb` (~3.7k tris,
  credits in `assets/CREDITS.md`).
- Material roles with `"plain": true`: a flat colour (+ emissive), no textures - the mobile slim then drops their UVs
  and welds the vertices.
- Mobile budget: ceiling conduit trays every other one (same random draws); GLB accessor min / max written as the
  shortest decimal of the float32 value (lossless).
