# test_valley: generation summary

Spec: levels/test_valley/scene_spec.json · 92 objects · 18 materials · 1 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 1}) · refine passes: 1
Mobile (balanced): 6343 KB · 83890 tris · 238 draw calls · ~53.4 visible (estimate) · ~3.58 MB GPU textures (estimate)
Navigation: 27649.0 m² reachable of 37826.0 m² standable
Package: dist/test_valley/package (34 files, 15.53 MB) valid=True
Previews: dist/test_valley/preview.html, preview_mobile.html · renders: levels/test_valley/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_Trail_River: bridge added where road Trail crosses river River

## Timing
- spec -> level.json: 1.3 s
- build (glb, sky, background, effects, mobile): 13.7 s
- refine (checks -> safe fixes): 183.8 s
- previews: 0.9 s
- export package: 1.0 s
- total: 200.7 s
