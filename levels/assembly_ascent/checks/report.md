# Checks: assembly_ascent - PASSED

errors 0 · warnings 7 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3522 | 2091 |
| triangles | 48676 | 55340 |
| draw calls (measured) | 2320 | 121 |
| visible draw calls (estimate) | - | 67.1 |
| GPU texture MB (estimate) | 23.73 | 9.08 |

Navigation: reachable 3983.0 of 19851.0 m² standable; components 93.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 121 (> 80)
- **warning** ~67 visible draw calls (estimate, > 60)
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 57468 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
