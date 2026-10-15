# slime_arena: generation summary

Spec: levels/slime_arena/scene_spec.json · 4414 objects · 31 materials · 24 effects
Checks: PASSED ({'error': 0, 'warning': 3, 'info': 2}) · refine passes: 0
Mobile (balanced): 3966 KB · 116936 tris · 131 draw calls · ~72.1 visible (estimate) · ~7.52 MB GPU textures (estimate)
Navigation: 9568.0 m² reachable of 49184.0 m² standable
Package: dist/slime_arena/package (38 files, 15.52 MB) valid=True
Previews: dist/slime_arena/preview.html, preview_mobile.html · renders: levels/slime_arena/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: mobile draw calls 131 (> 80)
- warning: ~72 visible draw calls (estimate, > 60)
- warning: 124170 triangles (> budget 40000)
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
- Gate_Works: open blast door (12 x 6 m)
- Conv_West: working assembly line - 4 parcels 7.35 m apart at 0.8 m/s, 2 station(s)
- Conv_East: working assembly line - 4 parcels 7.35 m apart at 0.8 m/s, 2 station(s)
- Valve_A_Vent: left out - it would hang over the edge of Pipe_Junction_A
- Exit_Door: open exit door -> level1_part3
- outlets: removed wall dressing in front of pours: Works_Wall_West_02_M02Monitor, Works_Wall_West_02_M03Machine
- Central: 3 cover crate(s) dropped - no free spot clear of landings
- Tunnel_West: HazardFluid_2 reaches on to -56.0 through the bore
- crates: 35 printed crates (accent atlas)
- fixtures: 31 parts cleared out of fans / vents (wall units removed: OuterWall_West_02_M02Vent, Works_Wall_West_02_M05Fan)
- ducts: Ceil_Duct_3 trimmed to 1 piece(s) clear of 1 standing part(s); Works_Ceil_Duct_1 trimmed to 1 piece(s) clear of 3 standing part(s); Works_Ceil_Duct_2 trimmed to 2 piece(s) clear of 7 standing part(s)
- portals: 3 thin fixtures covered by a doorway portal removed (Gallery_North_Strut_02, Gallery_North_Strut_03, Gallery_North_Strut_04)
- corrosion: 34 lit bodies get a plain skirt at the liquid line (no lights in the slime)
- corrosion: 48 lights at the liquid line removed, 28 light strips raised clear of it
- corrosion: 2246 wall faces at the liquid line get a corroded band (one mesh, one material)

## Timing
- spec -> level.json: 6.6 s
- build (glb, sky, background, effects, mobile): 117.3 s
- checks (fast): 100.1 s
- previews: 0.7 s
- export package: 0.8 s
- total: 225.6 s
