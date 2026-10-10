# skyforge_arena: generation summary

Spec: levels/skyforge_arena/scene_spec.json · 641 objects · 23 materials · 13 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 0}) · refine passes: 1
Mobile (balanced): 5807 KB · 99292 tris · 150 draw calls · ~56.6 visible (estimate) · ~6.9 MB GPU textures (estimate)
Navigation: 4246.8 m² reachable of 29297.5 m² standable
Package: dist/skyforge_arena/package (36 files, 13.87 MB) valid=True
Previews: dist/skyforge_arena/preview.html, preview_mobile.html · renders: levels/skyforge_arena/checks/views/contact_sheet.jpg

## Needs Claude's judgement
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
- spec -> level.json: 0.3 s
- build (glb, sky, background, effects, mobile): 40.7 s
- refine (checks -> safe fixes): 462.9 s
- previews: 0.9 s
- export package: 0.9 s
- total: 505.7 s
