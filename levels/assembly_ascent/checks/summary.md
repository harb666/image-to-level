# assembly_ascent: generation summary

Spec: levels/assembly_ascent/scene_spec.json · 2279 objects · 38 materials · 28 effects
Checks: PASSED ({'error': 0, 'warning': 7, 'info': 1}) · refine passes: 0
Mobile (balanced): 2238 KB · 58902 tris · 123 draw calls · ~68.3 visible (estimate) · ~9.5 MB GPU textures (estimate)
Navigation: 3983.0 m² reachable of 18675.0 m² standable
Package: dist/assembly_ascent/package (38 files, 9.48 MB) valid=True
Previews: dist/assembly_ascent/preview.html, preview_mobile.html · renders: levels/assembly_ascent/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- warning: OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- warning: mobile draw calls 123 (> 80)
- warning: ~68 visible draw calls (estimate, > 60)
- warning: enemy_arena: hazard 0.5 m away (< 3.0 m)
- warning: Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- warning: 61084 triangles (> budget 40000)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: glass dome r 20 m (rise 10 m) at (14, -34), 12 ribs, warm light shafts
- ceiling: roof slab at y 34.5 m, varied dressing
- Yard_Bridge: 0.35 m junction plate where it meets Robot_Ring's angled edge
- Yard_Bridge: 0.45 m junction plate where it meets Start_Deck's angled edge
- Exit_Stairs: 0.70 m junction plate where it meets Exit_Deck's angled edge
- Exit_Stairs: 0.75 m junction plate where it meets Upper_Deck's angled edge
- Exit_Stairs: stairs run 5.7 m > gap 4.0 m - extends 1.7 m onto Upper_Deck
- Entry_Door: entrance hallway 10 m out of the black (from slime_arena)
- Saw_West: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 26.5]
- Saw_East: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 20.5]
- Pillars: 7 striped pillars on truss legs
- Belt_A: conveyor ramp 16.5 m at 21 deg, belt -2.4 m/s, spike pit at the foot
- Belt_B: conveyor ramp 16.5 m at 21 deg, belt -3.4 m/s, spike pit at the foot
- Exit_Door: exit hallway 12 m fading to black -> level2_part1
- Spinner: spinner, 4 arms driven by a ceiling press (peak 64.43 rpm, still 3.8 s per 9.5 s), 4 hovering pads
- Overlook: corner overlook 5.1 x 15.0 m at 15.5 m, gantry 14.8 m to lift Spinner_Pad_1_Lift
- Arena: battle arena rising out of the liquid (goofy) - 25 square tiles, 20.8 m across at 15.5 m
- Jet_Screen: jetpack grin screen bobbing at [-2.0, 22.0, -18.0]; flies to [28.39, 21.632, 28.89] when a player reaches Arena_Deck - big red button opens ['Yard_Laser']
- crates: 5 printed crates (accent atlas)
- fixtures: 63 parts cleared out of fans / vents (wall units removed: OuterWall_East_M06Fan, OuterWall_East_M07Vent, OuterWall_North_M02Fan, OuterWall_West_M02Fan)
- ducts: Ceil_Duct_1 trimmed to 2 piece(s) clear of 2 standing part(s), 0 crane runway(s), ends at beams 0.0 m; Ceil_Duct_2 trimmed to 1 piece(s) clear of 0 standing part(s), 1 crane runway(s), ends at beams 0.0 m
- corrosion: 6 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 8 lights at the liquid line removed, 12 light strips raised clear of it
- corrosion: 587 wall faces at the liquid line get a corroded band (one mesh, one material)

## Timing
- spec -> level.json: 2.0 s
- build (glb, sky, background, effects, mobile): 35.1 s
- checks (fast): 39.5 s
- previews: 1.1 s
- export package: 0.5 s
- total: 78.1 s
