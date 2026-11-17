# assembly_ascent: generation summary

Spec: levels/assembly_ascent/scene_spec.json · 2846 objects · 61 materials · 48 effects
Checks: PASSED ({'error': 0, 'warning': 11, 'info': 1}) · refine passes: 0
Mobile (balanced): 3252 KB · 90644 tris · 174 draw calls · ~89.2 visible (estimate) · ~13.9 MB GPU textures (estimate)
Navigation: 5454.0 m² reachable of 20220.0 m² standable
Package: dist/assembly_ascent/package (39 files, 14.77 MB) valid=True
Previews: dist/assembly_ascent/preview.html, preview_mobile.html · renders: levels/assembly_ascent/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- warning: OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- warning: mobile draw calls 174 (> 80)
- warning: ~89 visible draw calls (estimate, > 60)
- warning: Showcase_Pit_1_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_1_Pillar_R: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_2_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_2_Pillar_L: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: enemy_arena: hazard 0.5 m away (< 3.0 m)
- warning: Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- warning: 94216 triangles (> budget 40000)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: lift shaft BossShaft r 10.0 m at (-30.0, -39.5), 10 m tall, car parked at the top
- ceiling: glass dome r 20 m (rise 10 m) at (14, -34), 12 ribs, warm light shafts
- ceiling: roof slab at y 34.5 m, varied dressing
- Yard_Bridge: 0.35 m junction plate where it meets Robot_Ring's angled edge
- Yard_Bridge: 0.45 m junction plate where it meets Start_Deck's angled edge
- Exit_Stairs: 0.70 m junction plate where it meets Exit_Deck's angled edge
- Exit_Stairs: 0.75 m junction plate where it meets Upper_Deck's angled edge
- Exit_Stairs: stairs run 5.7 m > gap 4.0 m - extends 1.7 m onto Upper_Deck
- Entry_Door: entrance hallway 10 m out of the black (from slime_arena)
- Showcase: specimen cyber_girl floating in the tank (18094 tris), bangs on the glass within 9 m
- Showcase: Construct Error showcase - dais r 8.6 m, stage tank, banner 16 m, 2 slime pits
- West_DuctFans: 2 massive duct fans (r 4.4 m) with ducts into the wall and 13 louvred vents
- Deck_Monitor_L: wall monitor 3.4 m
- Deck_Monitor_R: wall monitor 3.4 m
- East_SlimeTunnel: slime tunnel 10 x 9 m through the wall, 9 m deep, fading to black
- Saw_West: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 26.5]
- Saw_East: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 20.5]
- Pillars: 7 floating stepping platforms (bobbing, thruster flames)
- Belt_A: conveyor ramp 16.5 m at 21 deg, belt -2.4 m/s, spike pit at the foot
- Belt_B: conveyor ramp 16.5 m at 21 deg, belt -3.4 m/s, spike pit at the foot
- Exit_Door: exit hallway 12 m fading to black -> level2_part1
- Spinner: spinner, 4 arms driven by a ceiling press (peak 64.43 rpm, still 3.8 s per 9.5 s), 4 hovering pads
- Overlook: corner overlook 5.1 x 15.0 m at 15.5 m, gantry 14.8 m to lift Spinner_Pad_1_Lift
- Arena: battle arena rising out of the liquid (goofy) - 25 square tiles, 20.8 m across at 15.5 m
- Jet_Screen: jetpack grin screen bobbing at [-2.0, 22.0, -18.0]; flies to [28.39, 21.632, 28.89] when a player reaches Arena_Deck - big red button opens ['Yard_Laser']
- ceiling: 75 dressing parts cleared from over the lift shaft at (-30, -40)
- crates: 11 printed crates (accent atlas)
- fixtures: 56 parts cleared out of fans / vents (wall units removed: OuterWall_East_M06Fan, OuterWall_East_M07Vent, OuterWall_West_M02Fan)
- ducts: Ceil_Duct_1 trimmed to 1 piece(s) clear of 8 standing part(s), 0 crane runway(s), ends at beams 0.0 m; Ceil_Duct_2 trimmed to 1 piece(s) clear of 0 standing part(s), 1 crane runway(s), ends at beams 0.0 m
- corrosion: 8 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 12 lights at the liquid line removed, 16 light strips raised clear of it
- corrosion: 706 wall faces at the liquid line get a corroded band (one mesh, one material)

## Timing
- spec -> level.json: 2.0 s
- build (glb, sky, background, effects, mobile): 60.3 s
- checks (fast): 73.8 s
- previews: 1.2 s
- export package: 0.5 s
- total: 137.7 s
