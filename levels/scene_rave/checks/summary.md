# scene_rave: generation summary

Spec: levels/scene_rave/scene_spec.json · 1409 objects · 34 materials · 67 effects
Checks: PASSED ({'error': 0, 'warning': 3, 'info': 1}) · refine passes: 0
Mobile (balanced): 1298 KB · 45385 tris · 168 draw calls · ~73.3 visible (estimate) · ~6.64 MB GPU textures (estimate)
Navigation: 9528.0 m² reachable of 12812.0 m² standable
Package: dist/scene_rave/package (38 files, 5.68 MB) valid=True
Previews: dist/scene_rave/preview.html, preview_mobile.html · renders: levels/scene_rave/checks/views/contact_sheet.jpg

## Needs Claude's judgement
- warning: mobile draw calls 168 (> 80)
- warning: ~73 visible draw calls (estimate, > 60)
- warning: 47754 triangles (> budget 40000)
- visual comparison of the renders with the reference image(s) (not automatic)

## Generator notes
- Zebra_Ramp: 0.35 m junction plate where it meets Zebra_Deck's angled edge
- Zebra_Ramp: 0.40 m junction plate where it meets Dance_Floor's angled edge
- Leopard_Ramp: 0.35 m junction plate where it meets Leopard_Deck's angled edge
- Leopard_Ramp: 0.40 m junction plate where it meets Dance_Floor's angled edge
- Halo_Ramp_W: 4.00 m junction plate where it meets Halo_Deck's corner
- Halo_Ramp_W: 0.85 m junction plate where it meets Heart_Loft's angled edge
- Halo_Ramp_E: 4.00 m junction plate where it meets Halo_Deck's corner
- Halo_Ramp_E: 0.85 m junction plate where it meets Star_Loft's angled edge
- DJ: DJ stage - booth, turntables, speaker stacks, truss with spotlights + 2 sweeping laser fans, spinning spiral disc, 4 neon signs
- Float_Floor: 10 floating giant icons
- Float_High: 12 floating giant icons
- Butterflies: 6 holographic butterflies circling, flapping
- Butterflies_High: 4 holographic butterflies circling, flapping
- Kandi_Halo: kandi railing, 7 posts, 180 beads
- Kandi_Zebra: kandi railing, 3 posts, 60 beads
- Kandi_Leopard: kandi railing, 3 posts, 60 beads
- Kandi_Stage: kandi railing, 4 posts, 96 beads
- Kandi_Stage_E: kandi railing, 4 posts, 96 beads
- Rainbows: 4 rainbow light ribbons

## Timing
- spec -> level.json: 0.2 s
- build (glb, sky, background, effects, mobile): 10.5 s
- checks (fast): 18.1 s
- previews: 0.4 s
- export package: 0.2 s
- total: 29.4 s
