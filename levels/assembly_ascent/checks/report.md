# Checks: assembly_ascent - PASSED

errors 0 · warnings 11 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6201 | 3704 |
| triangles | 94920 | 105936 |
| draw calls (measured) | 3415 | 183 |
| visible draw calls (estimate) | - | 94.3 |
| GPU texture MB (estimate) | 29.9 | 14.09 |

Navigation: reachable 5454.0 of 20630.0 m² standable; components 235.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 183 (> 80)
- **warning** ~94 visible draw calls (estimate, > 60)
- **warning** Showcase_Pit_1_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_1_Pillar_R: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Pillar_L: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 109972 triangles (> budget 40000)
- **info** dev GLB 6201 KB (> 6000)
- **info** 9 m² reachable floor has < 3.2 m headroom (cramped camera): Pod_Tube_1_Glass_03, Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
