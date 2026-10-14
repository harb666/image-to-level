# slime_arena: generation summary

Spec: levels/slime_arena/scene_spec.json · 4242 objects · 29 materials · 20 effects
Checks: PASSED ({'error': 0, 'warning': 2, 'info': 2}) · refine passes: 0
Mobile (balanced): 3641 KB · 107785 tris · 93 draw calls · ~59.6 visible (estimate) · ~7.28 MB GPU textures (estimate)
Navigation: 9256.0 m² reachable of 48773.0 m² standable
Package: dist/slime_arena/package (37 files, 14.36 MB) valid=True
Previews: dist/slime_arena/preview.html, preview_mobile.html · renders: levels/slime_arena/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: mobile draw calls 93 (> 80)
- warning: 113864 triangles (> budget 40000)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: roof slab at y 26.5 m, varied dressing
- Works_ceiling: roof slab at y 26.5 m, varied dressing
- Ramp_NE: 2.15 m junction plate where it meets Platform_NE's corner
- Ramp_NW: 2.15 m junction plate where it meets Platform_NW's corner
- Ramp_SE: 2.15 m junction plate where it meets Platform_SE's corner
- Ramp_SW: 2.15 m junction plate where it meets Platform_SW's corner
- RampOut_NE: 0.35 m junction plate where it meets Round_NE's angled edge
- RampOut_NE: 2.15 m junction plate where it meets Platform_NE's corner
- RampOut_NW: 0.40 m junction plate where it meets Round_NW's angled edge
- RampOut_NW: 2.15 m junction plate where it meets Platform_NW's corner
- RampOut_SE: 0.35 m junction plate where it meets Round_SE's angled edge
- RampOut_SE: 2.15 m junction plate where it meets Platform_SE's corner
- RampOut_SW: 0.40 m junction plate where it meets Round_SW's angled edge
- RampOut_SW: 2.15 m junction plate where it meets Platform_SW's corner
- W_Cat_Pipes: 0.85 m junction plate where it meets Pipe_Junction_A's angled edge
- W_Cat_Pipes: 4.20 m junction plate where it meets Assembly_Line's corner
- W_Cat_Junction: 0.30 m junction plate where it meets Pipe_Junction_B's angled edge
- W_Cat_Junction: 1.50 m junction plate where it meets Pipe_Junction_A's corner
- W_Ramp_Core: 0.30 m junction plate where it meets Core_Ring's angled edge
- W_Ramp_Core: 1.70 m junction plate where it meets Purification_Deck's corner
- W_Stairs_Maint: 0.95 m junction plate where it meets Maint_Low's angled edge
- W_Stairs_Shaft: 1.60 m junction plate where it meets Maint_High's corner
- W_Stairs_Shaft: 1.65 m junction plate where it meets Maint_Low's corner
- W_Ramp_Conduit: 0.40 m junction plate where it meets Processing_Deck's angled edge
- W_Ramp_Conduit: 0.45 m junction plate where it meets Conduit_Walk's angled edge
- Elevator: elevator car r 5.2 m arrives on Central from skyforge_arena, travel 19.8 m
- Gate_Works: open blast door (12 x 8 m)
- Arm_2: pose 50/95 -> 32/71 (clear of the objects around it)
- Arm_4: pose 40/60 -> 16/28 (clear of the objects around it)
- Valve_A_Vent: left out - it would hang over the edge of Pipe_Junction_A
- Exit_Door: open exit door -> level1_part3
- outlets: removed wall dressing in front of pours: Works_Wall_West_02_M02Monitor, Works_Wall_West_02_M03Machine
- Central: 3 cover crate(s) dropped - no free spot clear of landings
- crates: 35 printed crates (accent atlas)
- fixtures: 31 parts cleared out of fans / vents (wall units removed: OuterWall_West_02_M02Vent, Works_Wall_West_02_M05Fan)
- corrosion: 30 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 48 lights at the liquid line removed, 20 light strips raised clear of it
- corrosion: 1865 wall faces at the liquid line get a corroded band (one mesh, one material)

## Timing
- spec -> level.json: 5.1 s
- build (glb, sky, background, effects, mobile): 156.2 s
- checks (fast): 100.8 s
- previews: 0.7 s
- export package: 0.7 s
- total: 263.5 s
