# slime_arena: generation summary

Spec: levels/slime_arena/scene_spec.json · 323 objects · 15 materials · 10 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 1}) · refine passes: 0
Mobile (balanced): 854 KB · 13502 tris · 67 draw calls · ~42.5 visible (estimate) · ~6.9 MB GPU textures (estimate)
Navigation: 1962.6 m² reachable of 8389.6 m² standable
Package: dist/slime_arena/package (33 files, 2.61 MB) valid=True
Previews: dist/slime_arena/preview.html, preview_mobile.html · renders: levels/slime_arena/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- ceiling: roof slab at y 22.5 m with a 5.6 m opening for the shaft, 8 girders
- Ramp_NE: 2.15 m junction plate where it meets Platform_NE's corner
- Ramp_NW: 2.15 m junction plate where it meets Platform_NW's corner
- Ramp_SE: 2.15 m junction plate where it meets Platform_SE's corner
- Ramp_SW: 2.15 m junction plate where it meets Platform_SW's corner
- Elevator: elevator car r 5.2 m arrives on Central from skyforge_arena, travel 15.8 m
- Central: 3 cover crate(s) dropped - no free spot clear of landings
- crates: 13 printed crates (accent atlas)

## Timing
- spec -> level.json: 0.0 s
- build (glb, sky, background, effects, mobile): 12.1 s
- checks (fast): 9.4 s
- previews: 0.3 s
- export package: 0.2 s
- total: 22.0 s
