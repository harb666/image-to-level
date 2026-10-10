# test_hybrid: generation summary

Spec: levels/test_hybrid/scene_spec.json · 247 objects · 30 materials · 6 effects
Checks: NOT PASSED ({'error': 76, 'warning': 26, 'info': 1}) · refine passes: 4
Mobile (balanced): 5032 KB · 69302 tris · 270 draw calls · ~71.7 visible (estimate) · ~9.83 MB GPU textures (estimate)
Navigation: 27686.0 m² reachable of 41266.0 m² standable
Package: dist/test_hybrid/package (34 files, 12.82 MB) valid=True
Previews: dist/test_hybrid/preview.html, preview_mobile.html · renders: levels/test_hybrid/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- error: Link_Ground_Gantry_A.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_B.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Tower_Top.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_A_2.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_B_2.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Tower_Top_2.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_A_2.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Gantry_B_2.low leads nowhere (no floor within 4 m at step height)
- error: Link_Ground_Tower_Top_2.low leads nowhere (no floor within 4 m at step height)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A_2.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B_2.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A_2.high (blocks the route)
- error: railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B_2.high (blocks the route)
- error: relations[59] (supported_by): object 'Link_Ground_Gantry_A_3' does not exist
- error: relations[59] (supported_by): object 'Link_Ground_Gantry_A_Support_3' does not exist
- error: relations[60] (supported_by): object 'Link_Ground_Gantry_A_Junction_Hi_3' does not exist
- error: relations[61] (walkable_connection): object 'Link_Ground_Gantry_A_3' does not exist
- error: relations[61] (walkable_connection): object 'Link_Ground_Gantry_A_Junction_Hi_3' does not exist
- error: relations[62] (supported_by): object 'Link_Ground_Gantry_A_Junction_Lo_3' does not exist
- error: relations[63] (walkable_connection): object 'Link_Ground_Gantry_A_3' does not exist
- error: relations[63] (walkable_connection): object 'Link_Ground_Gantry_A_Junction_Lo_3' does not exist
- error: relations[64] (supported_by): object 'Link_Ground_Gantry_B_3' does not exist
- error: relations[64] (supported_by): object 'Link_Ground_Gantry_B_Support_3' does not exist
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_South_Road_River: bridge added where road South_Road crosses river River
- Tower_Stairs: 0.30 m junction plate where it meets Gantry_A's angled edge
- Yard_Catwalk: 0.50 m junction plate where it meets Silo_Deck's angled edge
- Yard_Catwalk: 0.55 m junction plate where it meets Gantry_B's angled edge
- Dock_Stairs: 1.45 m junction plate where it meets Gantry_A's corner
- Dock_Stairs: 1.50 m junction plate where it meets Loading_Dock's corner
- party walls: 2 hidden side decorations removed between touching buildings

## Timing
- spec -> level.json: 1.8 s
- build (glb, sky, background, effects, mobile): 24.6 s
- refine (checks -> safe fixes): 1086.2 s
- previews: 0.9 s
- export package: 1.1 s
- total: 1114.6 s
