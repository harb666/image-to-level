# Checks: assembly_ascent - PASSED

errors 0 · warnings 11 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4679 | 2759 |
| triangles | 69860 | 76622 |
| draw calls (measured) | 2839 | 144 |
| visible draw calls (estimate) | - | 78.9 |
| GPU texture MB (estimate) | 27.28 | 11.63 |

Navigation: reachable 5429.0 of 19868.0 m² standable; components 124.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 144 (> 80)
- **warning** ~79 visible draw calls (estimate, > 60)
- **warning** Showcase_Pit_1_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_1_Pillar_R: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Pillar_L: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 79764 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
