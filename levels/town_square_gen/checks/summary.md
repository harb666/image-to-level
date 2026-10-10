# town_square_gen: generation summary

Spec: levels/town_square_gen/scene_spec.json · 871 objects · 17 materials · 4 effects
Checks: PASSED ({'error': 0, 'warning': 1, 'info': 0}) · refine passes: 1
Mobile (balanced): 929 KB · 8534 tris · 61 draw calls · ~35.8 visible (estimate) · ~4.4 MB GPU textures (estimate)
Navigation: 1105.5 m² reachable of 1571.5 m² standable
Package: dist/town_square_gen/package (30 files, 4.17 MB) valid=True
Previews: dist/town_square_gen/preview.html, preview_mobile.html · renders: levels/town_square_gen/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: House_B1_Rail_20 and House_NW_Floor_2 share coplanar faces (0.22 m², different materials): z-fighting flicker [auto-repairable]
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- party walls: 175 hidden side decorations removed between touching buildings

## Timing
- spec -> level.json: 0.1 s
- build (glb, sky, background, effects, mobile): 11.2 s
- refine (checks -> safe fixes): 229.7 s
- previews: 0.5 s
- export package: 0.3 s
- total: 241.8 s
