# Checks: assembly_ascent - PASSED

errors 0 · warnings 3 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 2589 | 1307 |
| triangles | 29404 | 33935 |
| draw calls (measured) | 1569 | 59 |
| visible draw calls (estimate) | - | 43.2 |
| GPU texture MB (estimate) | 17.87 | 7.06 |

Navigation: reachable 2460.0 of 18414.0 m² standable; components 51.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 2, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
