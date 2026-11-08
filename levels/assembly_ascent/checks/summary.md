# assembly_ascent: generation summary

Spec: levels/assembly_ascent/scene_spec.json · 1606 objects · 30 materials · 17 effects
Checks: PASSED ({'error': 0, 'warning': 3, 'info': 1}) · refine passes: 0
Mobile (balanced): 1430 KB · 37821 tris · 65 draw calls · ~46.0 visible (estimate) · ~7.06 MB GPU textures (estimate)
Navigation: 3249.0 m² reachable of 19185.0 m² standable
Package: dist/assembly_ascent/package (38 files, 6.65 MB) valid=True
Previews: dist/assembly_ascent/preview.html, preview_mobile.html · renders: levels/assembly_ascent/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- warning: OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- warning: Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: roof slab at y 34.5 m, varied dressing
- Yard_Bridge: 0.35 m junction plate where it meets Robot_Ring's angled edge
- Yard_Bridge: 0.45 m junction plate where it meets Start_Deck's angled edge
- Exit_Stairs: 0.70 m junction plate where it meets Exit_Deck's angled edge
- Exit_Stairs: 0.75 m junction plate where it meets Upper_Deck's angled edge
- Exit_Stairs: stairs run 5.7 m > gap 4.0 m - extends 1.7 m onto Upper_Deck
- Entry_Door: entrance hallway 10 m out of the black (from slime_arena)
- Saw_West: saw 4.4 m chopping +-52 deg every 3.2 s across [-31.95, 26.5]
- Saw_East: saw 4.4 m chopping +-52 deg every 3.2 s across [-31.95, 20.5]
- Pillars: 7 striped pillars on truss legs
- Belt_A: conveyor ramp 16.5 m at 21 deg, belt -2.4 m/s, spike pit at the foot
- Belt_B: conveyor ramp 16.5 m at 21 deg, belt -3.4 m/s, spike pit at the foot
- Exit_Door: exit hallway 12 m fading to black -> level2_part1
- Spinner: spinner, 4 arms at 6.0 rpm, 4 hovering pads
- crates: 5 printed crates (accent atlas)
- fixtures: 62 parts cleared out of fans / vents (wall units removed: OuterWall_East_M06Fan, OuterWall_East_M07Vent, OuterWall_North_M02Fan, OuterWall_West_M02Fan)
- ducts: Ceil_Duct_1 trimmed to 1 piece(s) clear of 1 standing part(s), 0 crane runway(s), ends at beams 0.0 m
- corrosion: 6 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 8 lights at the liquid line removed, 12 light strips raised clear of it
- corrosion: 563 wall faces at the liquid line get a corroded band (one mesh, one material)

## Timing
- spec -> level.json: 0.9 s
- build (glb, sky, background, effects, mobile): 18.1 s
- checks (fast): 21.7 s
- previews: 0.4 s
- export package: 0.2 s
- total: 41.3 s
