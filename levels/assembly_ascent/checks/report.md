# Checks: assembly_ascent - PASSED

errors 0 · warnings 3 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 2733 | 1418 |
| triangles | 32581 | 37478 |
| draw calls (measured) | 1699 | 65 |
| visible draw calls (estimate) | - | 46.0 |
| GPU texture MB (estimate) | 17.88 | 7.06 |

Navigation: reachable 3249.0 of 19185.0 m² standable; components 98.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 2, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
