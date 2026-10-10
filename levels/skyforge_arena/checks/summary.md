# skyforge_arena: generation summary

Spec: levels/skyforge_arena/scene_spec.json · 695 objects · 28 materials · 14 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 0}) · refine passes: 1
Mobile (balanced): 5068 KB · 94683 tris · 138 draw calls · ~59.4 visible (estimate) · ~7.15 MB GPU textures (estimate)
Navigation: 4138.0 m² reachable of 29489.0 m² standable
Package: dist/skyforge_arena/package (37 files, 12.67 MB) valid=True
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
- Elevator: elevator shaft r 5.5 m, 10.3 m deep through Hub; exit trigger -> next_level
- North_Hall: 2 cover crate(s) dropped - no free spot clear of landings
- leaks: 20 slime decals (visual only) on structures picked with chance 0.4

## Timing
- spec -> level.json: 0.6 s
- build (glb, sky, background, effects, mobile): 33.5 s
- refine (checks -> safe fixes): 525.2 s
- previews: 0.8 s
- export package: 0.8 s
- total: 560.9 s
