# test_hybrid: generation summary

Spec: levels/test_hybrid/scene_spec.json · 235 objects · 30 materials · 6 effects
Checks: PASSED ({'error': 0, 'warning': 2, 'info': 1}) · refine passes: 2
Mobile (balanced): 4972 KB · 67142 tris · 270 draw calls · ~71.5 visible (estimate) · ~9.83 MB GPU textures (estimate)
Navigation: 29198.0 m² reachable of 41270.0 m² standable
Package: dist/test_hybrid/package (34 files, 12.63 MB) valid=True
Previews: dist/test_hybrid/preview.html, preview_mobile.html · renders: levels/test_hybrid/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: Tower_Stairs_Beam_R stands in the landing of Dock_Stairs.high (blocks the route)
- warning: ~72 visible draw calls (estimate, > 60)
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
- spec -> level.json: 1.7 s
- build (glb, sky, background, effects, mobile): 23.7 s
- refine (checks -> safe fixes): 628.2 s
- previews: 0.9 s
- export package: 1.2 s
- total: 655.6 s
