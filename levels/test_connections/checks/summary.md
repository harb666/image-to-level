# test_connections: generation summary

Spec: levels/test_connections/scene_spec.json · 127 objects · 15 materials · 10 effects
Checks: PASSED ({'error': 0, 'warning': 1, 'info': 0}) · refine passes: 1
Mobile (balanced): 571 KB · 4176 tris · 47 draw calls · ~30.9 visible (estimate) · ~6.15 MB GPU textures (estimate)
Navigation: 373.8 m² reachable of 799.0 m² standable
Package: dist/test_connections/package (30 files, 1.77 MB) valid=True
Previews: dist/test_connections/preview.html, preview_mobile.html · renders: levels/test_connections/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: Island: reachable but no way back to the spawn area
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Gap_P2_P3: jump link P2_Bridged->P3_JumpTarget (gap 2.7 m, dy 0.0 m) - no geometry

## Timing
- spec -> level.json: 0.0 s
- build (glb, sky, background, effects, mobile): 8.8 s
- refine (checks -> safe fixes): 100.9 s
- previews: 0.3 s
- export package: 0.1 s
- total: 110.1 s
