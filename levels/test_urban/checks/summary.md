# test_urban: generation summary

Spec: levels/test_urban/scene_spec.json · 740 objects · 26 materials · 4 effects
Checks: NOT PASSED ({'error': 1, 'warning': 6, 'info': 1}) · refine passes: 4
Mobile (balanced): 1965 KB · 27416 tris · 185 draw calls · ~65.5 visible (estimate) · ~6.04 MB GPU textures (estimate)
Navigation: 24279.0 m² reachable of 40341.0 m² standable
Package: dist/test_urban/package (34 files, 5.68 MB) valid=True
Previews: dist/test_urban/preview.html, preview_mobile.html · renders: levels/test_urban/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- error: terrain pokes 0.11 m through Bridge_West_Lane_Road_Canal_Deck [auto-repairable]
- warning: ~66 visible draw calls (estimate, > 60)
- warning: Block_6_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Cross_Street_Sidewalk_R15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Skywalk_Stairs_From: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Skywalk_Stairs_To: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Tower_C_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_Avenue_Road_Canal: bridge added where road Avenue_Road crosses river Canal
- Bridge_West_Lane_Road_Canal: bridge added where road West_Lane_Road crosses river Canal

## Timing
- spec -> level.json: 6.1 s
- build (glb, sky, background, effects, mobile): 15.2 s
- refine (checks -> safe fixes): 512.3 s
- previews: 0.6 s
- export package: 0.4 s
- total: 534.6 s
