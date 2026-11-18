# Checks: assembly_ascent - PASSED

errors 0 · warnings 11 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6583 | 3906 |
| triangles | 100096 | 110788 |
| draw calls (measured) | 3668 | 192 |
| visible draw calls (estimate) | - | 98.7 |
| GPU texture MB (estimate) | 33.9 | 15.09 |

Navigation: reachable 5448.0 of 20650.0 m² standable; components 238.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 192 (> 80)
- **warning** ~99 visible draw calls (estimate, > 60)
- **warning** Showcase_Pit_1_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_1_Pillar_R: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Lintel: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Showcase_Pit_2_Pillar_L: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 115184 triangles (> budget 40000)
- **info** dev GLB 6583 KB (> 6000)
- **info** 9 m² reachable floor has < 3.2 m headroom (cramped camera): Pod_Tube_1_Glass_03, Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
