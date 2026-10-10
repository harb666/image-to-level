# Generating a level from concept images: Claude's runbook (Stage 7)

```
SEND IMAGE → ANALYSE → PLAN → GENERATE → TEXTURE → VALIDATE → PREVIEW → REFINE → EXPORT
   user       Claude + references.py   scene_spec.json   ── generate.py (deterministic CPU) ──   Claude reviews renders
```

The user works only from an iPhone. Never ask them to write JSON, run Python or open folders. Claude does every step
below and replies with a preview link plus a short report.

## 0. Receive

1. Put each image in `levels/<name>/references/`. If it arrived as a chat attachment, save it there.
2. Pick `<name>` in snake_case. Don't reuse a name unless the user asked to regenerate that level.

## 1. Analyse (Claude's judgement; the tools only measure)

| Reference type | Do this | Use it for |
|---|---|---|
| Concept sheet, collage or multi-panel | `python3 pipeline/references.py split <img> levels/<name>/references/panels`, then look at `panels_overview.jpg` and each crop. Label every panel's `view`. | each panel for its purpose |
| Top-down plan | `references.py plan <crop> <out> --size W D --bbox ...` gives measured regions in metres (`plan_regions.png` / `.json`). Decide which colour cluster is a platform, the hazard, a wall or a bridge. | layout, connectivity, sizes |
| Side elevation | `references.py grid <crop> <out>`, then read height ratios: floor → decks → towers → pipes. | heights |
| Perspective (single image) | `references.py grid`. Read proportions from doors (~2.2–2.5 m), storeys (~3–3.5 m) and stairs. Expect depth to be the least certain dimension, and say so. | appearance, materials, rough layout |
| Detail / texture close-up | Look at it. | materials, decor, effects |

- Don't treat a multi-panel sheet as one photo.
- Don't run depth estimation (`make_level.sh`) on diagrams, plans or collages. It's only a rough fallback for a single
  real photo.
- Ask the user a question **only** when the gap blocks generation entirely, for example no indication of which way is
  up in a plan. Otherwise make a gameplay-safe assumption and record it in `interpretation.assumptions`.

## 2. Plan: write `levels/<name>/scene_spec.json`

Follow `SCENE_SPEC.md`.

**Stage 9 - choose the generation mode first** (Claude's judgement, recorded in `interpretation.assumptions`):
- *structured* (`arena` only): enclosed arenas, interiors, walled compounds.
- *open* (`world` only): landscapes and cities. Read the image for: relief (`flat` … `mountainous`), the biome / ground
  materials, named landforms (each hill, ridge, river, road, cliff, lake as a `features[]` entry with an `id`), where
  the playable area ends and what conceals it (ridge, cliffs, water, buildings), vegetation and rock density
  (`scatter[]`), and where players / enemies start (`spawn_regions[]`).
- *hybrid* (`arena` + `world`): a structured compound inside a landscape.
Don't force a square boundary, symmetry or a centre platform: use `boundary.points` when the image shows the shape.
For layout taken from an image, a grayscale `heightmap` or a `mask` feature can carry it (paint/derive the image,
put it in the level folder). Footprint buildings get pads and foundations automatically; roads crossing rivers get
bridges; rivers/roads leaving the area continue to the horizon.

1. **Scale.** Pick a scale basis and write it down in `interpretation.scale_basis`. Platforms of at least 8–12 m give
   third-person combat room. Bridges must be at least `design.min_bridge_width`.
2. **Gameplay spaces.**
   - Connect every major area intentionally: bridges, ramps and stairs. For a deliberate `jump`, check the gap and
     height against the gameplay config.
   - Add cover with `cover`, `crates` or structures.
   - Keep the spawn safe: room around it and away from hazards.
3. **Separate seen from guessed.** Tag every element `source: visible` or `source: inferred`, and fill in
   `interpretation.visible` and `interpretation.inferred`.
4. **Close the world.** Close the sides the image doesn't show (walls, houses, boundary) so the third-person camera
   never sees a void. Record these as inferred.
5. **Stay faithful.** Keep the reference's composition, proportions, colours (via `materials.roles` overrides) and
   architecture. If a needed shape doesn't exist, extend `pipeline/architecture.py`. Don't silently substitute a box.
6. **Validate:** `python3 pipeline/scene_spec.py levels/<name>/scene_spec.json`.

## 3. Generate, texture, validate, preview, export: one command

```
python3 pipeline/generate.py levels/<name>/scene_spec.json      # ~3-4 min on CPU
```

This runs spec → `level.json` → build (glb, PBR textures, sky, background, effects, mobile export), then a bounded
refine loop (`checks.py`, safe automatic fixes, rebuild; at most `refine.max_passes`). After that it renders headless
views, writes the final report, the previews (`dist/<name>/preview.html` and `preview_mobile.html`) and the package
(`dist/<name>/<name>.zip`), and finally `levels/<name>/checks/summary.md`.

## 3a. Worlds (Stage 9, automatic inside the same command)

The build adds the terrain chunks (+ LODs in the mobile export), the middle-zone ring, water, scatter and
`terrain.json`; the checks add the world family (`terrain_check.py`: holes / LOD seams, roads + bridges, foundations,
ground through floors, boundary concealment, water edges, unreachable areas, density, background gaps from boundary /
hilltop / spawn cameras). Safe repairs edit only `level.json["terrain"]` features outside the playable area or under a
floor ("lower"-only), or extend a foundation. The renders add boundary views looking OUT in each compass direction, the
highest playable point and a zones overview. Look at those: a valid world can still look wrong.

## 3b. Geometry (Stage 8, automatic inside refine)
`checks/geometry.md` lists construction findings (ERROR / WARNING / INTENTIONAL); the safe ones are already repaired
(`checks/repairs.json`, undoable). Look at `checks/inspect/contact_sheet.jpg` (junction / outlet / third-person
close-ups) - a passing geometric test is not proof that it looks right. Ambiguous findings (a connector leading nowhere,
cover in a landing, a big hover) are your call: fix with targeted edits or declare them intentional
(`edit_level.py relate intentional_gap A B`).

## 4. Refine (Claude, bounded)

1. **Look** at `levels/<name>/checks/views/contact_sheet.jpg`, plus individual views and `checks/navigation.png`
   (blue = reachable, orange = one-way, red = unreachable).
2. **Compare** with the reference. Only claim visual similarity after actually looking.
3. **Read** `checks/report.md`, starting with the highest-impact issues.
4. **Fix** the top 1–3 problems with targeted edits. Use `edit_level.py` commands or `apply` ops; don't regenerate
   for small changes. If the spec itself was wrong, edit the spec and re-run `generate.py`, which keeps manual edits.
5. **Re-run:** `python3 pipeline/generate.py ... --max-passes 1`, or `refine.py` followed by `render_views.py`.
6. **Stop** after at most 3 Claude rounds, or sooner when only cosmetic issues remain. Report what's left; never loop
   endlessly.

## 5. Publish and report

1. Publish `dist/<name>/preview.html` as an artifact. It is self-contained, sandbox-safe and carries the issues overlay.
2. Commit `levels/<name>/` and push. `dist/` is not committed; regenerate it any time with `package.py`.
3. Keep the report short:
   - what was built
   - what came from the image and what was inferred
   - check results
   - **measured** numbers: file size, triangles, nodes, materials, draw calls
   - **estimated** numbers: visible draw calls, GPU texture memory
   - the remaining issues and limits
4. Never say the browser preview equals Godot.

## Turning natural-language edits into commands

Use the stable names. The user can tap an object → **Copy for Claude**.

| User says | Command (`python3 pipeline/edit_level.py levels/<name> ...`) |
|---|---|
| Make the north platform twice as wide | `resize Platform_North 2 1 1`. A group scales its children's sizes and offsets. Then check that its bridge still meets it (`connect` again if not). |
| Add a bridge between these two platforms | `connect Platform_NE Platform_East bridge 4` (or `auto`) |
| Make the pipes much larger | `resize 'Pipe_*' 1.5 1 1.5`. Check with `list 'Pipe_*'` first. |
| Add green glowing liquid flowing from the factory | `apply '[{"op":"add","object":{...fall box, material "hazard"...}},{"op":"fx","id":"Pour_Flow","values":{"targets_glob":[...]}}]'`, or duplicate an existing `*_Fall`. Clones join the source's effects. |
| Make the distant mountains taller | `env background.Mountains_Far.height=[120,260]` |
| Change the sky to a stormy alien atmosphere | `env sky.preset=alien sky.clouds.coverage=0.85 atmosphere.fog_start=40` |
| Add more industrial detail without increasing file size too much | Raise `detail` in the spec and regenerate (edits kept), or add `prefab machinery_bank` / `pipe_run`. These reuse shared materials, so draw calls hardly change. Check the mobile numbers afterwards. |
| Fix the exposed geometry behind the central tower | Run `checks.py`. A `back_face` or `open_mesh` issue names the object: `set <obj> double_sided=true`, or close it with an added box. The refine loop also applies the safe fix automatically. |
| Undo that | `undo` (`history` lists the steps) |

Every edit is schema-checked before it is saved. Invalid edits are refused with the reason. Rebuilds cover only what
changed. Run `checks.py --fast` afterwards, `checks.py` (full) after geometry edits near playable space, and
`render_views.py` when the change is visual.

## Honesty rules

- Never fabricate renders. `render_views.py` either produces real headless renders or fails loudly.
- Never call a real image-to-level test successful unless a real reference image was processed.
- Visual accuracy is "verified" only after Claude looked at the renders. Say what differs.
- Device performance is unknown until it's measured on an iPhone or in Godot. Manifest numbers are estimates.
- `config/gameplay.json` holds placeholders until Construct Error's real values are copied in.
