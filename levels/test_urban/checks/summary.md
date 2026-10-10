# test_urban: generation summary

Spec: levels/test_urban/scene_spec.json · 746 objects · 25 materials · 4 effects
Checks: NOT PASSED ({'error': 2, 'warning': 32, 'info': 1}) · refine passes: 4
Mobile (balanced): 1910 KB · 27096 tris · 183 draw calls · ~64.8 visible (estimate) · ~5.79 MB GPU textures (estimate)
Navigation: 24160.0 m² reachable of 40371.0 m² standable
Package: dist/test_urban/package (34 files, 5.53 MB) valid=True
Previews: dist/test_urban/preview.html, preview_mobile.html · renders: levels/test_urban/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- error: terrain pokes 0.14 m through Bridge_West_Lane_Road_Canal_Deck [auto-repairable]
- error: Skywalk: not reachable from the spawn (walk/drop/jump with the gameplay config)
- warning: ~65 visible draw calls (estimate, > 60)
- warning: Block_6_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Cross_Street_Sidewalk_R15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_01: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_02: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_03: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_04: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_05: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_06: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_07: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_08: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_10: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_11: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_12: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_13: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_14: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Post_15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_01b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_02b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_03b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_04b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_05b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- warning: Fence_Park_Rail_06b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Bridge_Avenue_Road_Canal: bridge added where road Avenue_Road crosses river Canal
- Bridge_West_Lane_Road_Canal: bridge added where road West_Lane_Road crosses river Canal

## Timing
- spec -> level.json: 5.8 s
- build (glb, sky, background, effects, mobile): 15.0 s
- refine (checks -> safe fixes): 574.5 s
- previews: 0.5 s
- export package: 0.4 s
- total: 596.2 s
