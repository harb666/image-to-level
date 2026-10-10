# test_hybrid: generation summary

Spec: levels/test_hybrid/scene_spec.json · 242 objects · 30 materials · 6 effects
Checks: NOT PASSED ({'error': 8, 'warning': 7, 'info': 1}) · refine passes: 4
Mobile (balanced): 5020 KB · 68250 tris · 279 draw calls · ~73.6 visible (estimate) · ~9.83 MB GPU textures (estimate)
Navigation: 29121.0 m² reachable of 41261.0 m² standable
Package: dist/test_hybrid/package (34 files, 12.75 MB) valid=True
Previews: dist/test_hybrid/preview.html, preview_mobile.html · renders: levels/test_hybrid/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- error: Link_Ground_Gantry_A.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_B.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Tower_Top.low leads nowhere (no floor within 4 m at step height)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B.high (blocks the route)
- error: Link_Ground_Gantry_A is declared supported_by Link_Ground_Gantry_A_Support but does not touch it
- error: Link_Ground_Gantry_B is declared supported_by Link_Ground_Gantry_B_Support but does not touch it
- error: Ridge_Post: not reachable from the spawn (walk/drop/jump with the gameplay config)
- warning: Link_Ground_Tower stands in the landing of Link_Ground_Gantry_B.low (blocks the route)
- warning: Link_Ground_Gantry_A stands in the landing of Link_Ground_Tower_Top.low (blocks the route)
- warning: ~74 visible draw calls (estimate, > 60)
- warning: Gantry_A_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Gantry_B_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Gantry_Bridge_Deck: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Tower_Top_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_South_Road_River: bridge added where road South_Road crosses river River
- Tower_Stairs: 0.30 m junction plate where it meets Gantry_A's angled edge
- Yard_Catwalk: 0.50 m junction plate where it meets Silo_Deck's angled edge
- Yard_Catwalk: 0.55 m junction plate where it meets Gantry_B's angled edge
- party walls: 2 hidden side decorations removed between touching buildings

## Timing
- spec -> level.json: 1.7 s
- build (glb, sky, background, effects, mobile): 23.3 s
- refine (checks -> safe fixes): 940.1 s
- previews: 0.9 s
- export package: 0.9 s
- total: 967.0 s
