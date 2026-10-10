# skyforge_arena: generation summary

Spec: levels/skyforge_arena/scene_spec.json · 432 objects · 22 materials · 9 effects
Checks: PASSED ({'error': 0, 'warning': 1, 'info': 1}) · refine passes: 1
Mobile (balanced): 4429 KB · 69506 tris · 252 draw calls · ~67.6 visible (estimate) · ~6.81 MB GPU textures (estimate)
Navigation: 4262.0 m² reachable of 29400.3 m² standable
Package: dist/skyforge_arena/package (34 files, 10.5 MB) valid=True
Previews: dist/skyforge_arena/preview.html, preview_mobile.html · renders: levels/skyforge_arena/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: ~68 visible draw calls (estimate, > 60)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Steps_Turret: stairs run 4.3 m > gap 2.6 m - extends 1.6 m onto North_Hall
- Ramp_Hub_NW: 0.40 m junction plate where it meets Hub's angled edge
- Ramp_Hub_NW: 4.35 m junction plate where it meets NW_Bastion's corner
- Link_North_NW: 0.35 m junction plate where it meets North_Hall's angled edge
- Link_North_NW: 0.40 m junction plate where it meets NW_Bastion's angled edge
- Ramp_Hub_SW: 0.40 m junction plate where it meets Hub's angled edge
- Ramp_Hub_SW: 0.40 m junction plate where it meets SW_Octagon's angled edge
- Ramp_Hub_SE: 0.35 m junction plate where it meets Hub's angled edge
- Ramp_Hub_SE: 0.35 m junction plate where it meets SE_Octagon's angled edge
- North_Hall: 2 cover crate(s) dropped - no free spot clear of landings

## Timing
- spec -> level.json: 0.2 s
- build (glb, sky, background, effects, mobile): 19.1 s
- refine (checks -> safe fixes): 353.6 s
- previews: 0.8 s
- export package: 0.7 s
- total: 374.4 s
