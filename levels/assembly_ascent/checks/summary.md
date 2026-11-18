# assembly_ascent: generation summary

Spec: levels/assembly_ascent/scene_spec.json · 3541 objects · 65 materials · 56 effects
Checks: PASSED ({'error': 0, 'warning': 10, 'info': 2}) · refine passes: 0
Mobile (balanced): 3872 KB · 114650 tris · 212 draw calls · ~105.1 visible (estimate) · ~15.67 MB GPU textures (estimate)
Navigation: 5443.0 m² reachable of 20640.0 m² standable
Package: dist/assembly_ascent/package (39 files, 17.44 MB) valid=True
Previews: dist/assembly_ascent/preview.html, preview_mobile.html · renders: levels/assembly_ascent/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- warning: OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- warning: mobile draw calls 212 (> 80)
- warning: ~105 visible draw calls (estimate, > 60)
- warning: Showcase_Pit_1_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_1_Pillar_R: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_2_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Showcase_Pit_2_Pillar_L: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: enemy_arena: hazard 0.5 m away (< 3.0 m)
- warning: 119128 triangles (> budget 40000)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: lift shaft BossShaft r 10.0 m at (-30.0, -39.5), 10 m tall, car parked at the top - boss lift
- ceiling: glass dome r 20 m (rise 10 m) at (14, -34), 12 ribs, warm light shafts
- ceiling: roof slab at y 34.5 m, varied dressing
- Yard_Bridge: 0.35 m junction plate where it meets Robot_Ring's angled edge
- Yard_Bridge: 0.45 m junction plate where it meets Start_Deck's angled edge
- Exit_Stairs: 0.70 m junction plate where it meets Exit_Deck's angled edge
- Exit_Stairs: 0.75 m junction plate where it meets Upper_Deck's angled edge
- Exit_Stairs: ramp run 9.0 m > gap 4.0 m - extends 5.0 m onto Upper_Deck
- Entry_Door: entrance hallway 10 m out of the black (from slime_arena)
- Showcase: specimen cyber_girl floating in the tank (18094 tris), bangs on the glass within 9 m
- Showcase: Construct Error showcase - dais r 8.6 m, stage tank, scan monitor, 2 slime pits
- West_DuctFans: 2 massive duct fans (r 4.4 m) with ducts into the wall and 13 louvred vents
- Deck_Monitor_L: wall monitor 3.4 m
- Deck_Monitor_R: wall monitor 3.4 m
- East_SlimeTunnel: slime tunnel 10 x 9 m through the wall, 9 m deep, fading to black
- Saw_West: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 26.5]
- Saw_East: ceiling saw 4.4 m, jointed arm (shoulder 30 deg) across [-31.95, 20.5]
- Pillars: 7 floating stepping platforms (bobbing, thruster flames)
- Belt_A: conveyor ramp 16.5 m at 21 deg, belt -2.4 m/s, spike pit at the foot
- Belt_B: conveyor ramp 16.5 m at 21 deg, belt -3.4 m/s, spike pit at the foot
- Claw_Line: 5 claws with canisters riding the runway at z 12, hatches in both end walls
- Exit_Door: exit hallway 12 m fading to black -> level2_part1
- Spinner: spinner, 4 arms driven by a ceiling press (peak 64.43 rpm, still 3.8 s per 9.5 s), 4 hovering pads
- Overlook: corner overlook 5.1 x 15.0 m at 15.5 m, gantry 14.8 m to lift Spinner_Pad_1_Lift
- Arena: battle arena rising out of the liquid (goofy) - 25 square tiles, 20.8 m across at 15.5 m
- Jet_Screen: jetpack grin screen bobbing at [-2.0, 22.0, -18.0]; flies to [28.39, 21.632, 28.89] when a player reaches Arena_Deck - big red button opens ['Yard_Laser']
- Reactor: slime reactor in the pool - deck r 7.5 at 3.4, vat r 3.3 to 11.6, 3 catwalks, 2 falls
- Pod_Export: 3 pod pipes out through the roof, up 18.7 m and east to x 91.8 (39 pods)
- ceiling: 75 dressing parts cleared from over the lift shaft at (-30, -40)
- crates: 11 printed crates (accent atlas)
- fixtures: 56 parts cleared out of fans / vents (wall units removed: OuterWall_East_M06Fan, OuterWall_East_M07Vent, OuterWall_West_M02Fan)
- ducts: Ceil_Duct_1 trimmed to 2 piece(s) clear of 12 standing part(s), 0 crane runway(s), ends at beams 0.0 m; Ceil_Duct_2 trimmed to 2 piece(s) clear of 1 standing part(s), 1 crane runway(s), ends at beams 0.0 m
- corrosion: 8 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 12 lights at the liquid line removed, 16 light strips raised clear of it
- corrosion: 1112 wall faces at the liquid line get a corroded band (one mesh, one material)
- Jet_Screen: path planned - colliding samples per phase {'home': 0, 'fly': 0, 'wait': 0, 'press': 0, 'back': 0} (arrive [28.3, 21.632, 35.34], yaw 90.0)

## Timing
- spec -> level.json: 17.5 s
- build (glb, sky, background, effects, mobile): 67.6 s
- checks (fast): 89.0 s
- previews: 0.9 s
- export package: 0.8 s
- total: 175.8 s
