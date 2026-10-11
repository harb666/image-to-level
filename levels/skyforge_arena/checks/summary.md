# skyforge_arena: generation summary

Spec: levels/skyforge_arena/scene_spec.json · 675 objects · 28 materials · 14 effects
Checks: PASSED ({'error': 0, 'warning': 0, 'info': 0}) · refine passes: 1
Mobile (balanced): 5009 KB · 92633 tris · 134 draw calls · ~57.6 visible (estimate) · ~7.15 MB GPU textures (estimate)
Navigation: 4138.3 m² reachable of 29489.2 m² standable
Package: dist/skyforge_arena/package (37 files, 12.58 MB) valid=True
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
- crates: 26 printed crates (accent atlas)

## Timing
- spec -> level.json: 0.6 s
- build (glb, sky, background, effects, mobile): 22.5 s
- refine (checks -> safe fixes): 376.1 s
- previews: 0.6 s
- export package: 0.8 s
- total: 400.5 s
