# toxic_arena_gen: generation summary

Spec: levels/toxic_arena_gen/scene_spec.json · 278 objects · 14 materials · 13 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 1}) · refine passes: 1
Mobile (balanced): 723 KB · 8720 tris · 58 draw calls · ~44.1 visible (estimate) · ~6.33 MB GPU textures (estimate)
Navigation: 1746.8 m² reachable of 3109.8 m² standable
Package: dist/toxic_arena_gen/package (30 files, 2.61 MB) valid=True
Previews: dist/toxic_arena_gen/preview.html, preview_mobile.html · renders: levels/toxic_arena_gen/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Ramp_NE: 2.15 m junction plate where it meets Platform_NE's corner
- Ramp_NW: 2.15 m junction plate where it meets Platform_NW's corner
- Ramp_SE: 2.15 m junction plate where it meets Platform_SE's corner
- Ramp_SW: 2.15 m junction plate where it meets Platform_SW's corner

## Timing
- spec -> level.json: 0.1 s
- build (glb, sky, background, effects, mobile): 11.7 s
- refine (checks -> safe fixes): 331.3 s
- previews: 0.5 s
- export package: 0.2 s
- total: 343.7 s
