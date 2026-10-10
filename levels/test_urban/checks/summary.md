# test_urban: generation summary

Spec: levels/test_urban/scene_spec.json · 740 objects · 26 materials · 4 effects
Checks: PASSED ({'error': 0, 'warning': 1, 'info': 1}) · refine passes: 2
Mobile (balanced): 1964 KB · 27416 tris · 185 draw calls · ~65.4 visible (estimate) · ~6.04 MB GPU textures (estimate)
Navigation: 24279.0 m² reachable of 40410.0 m² standable
Package: dist/test_urban/package (34 files, 5.78 MB) valid=True
Previews: dist/test_urban/preview.html, preview_mobile.html · renders: levels/test_urban/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: ~65 visible draw calls (estimate, > 60)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_Avenue_Road_Canal: bridge added where road Avenue_Road crosses river Canal
- Bridge_West_Lane_Road_Canal: bridge added where road West_Lane_Road crosses river Canal

## Timing
- spec -> level.json: 7.4 s
- build (glb, sky, background, effects, mobile): 15.4 s
- refine (checks -> safe fixes): 306.9 s
- previews: 0.6 s
- export package: 0.4 s
- total: 330.7 s
