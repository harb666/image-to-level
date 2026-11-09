# Checks: assembly_ascent - PASSED

errors 0 · warnings 5 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3132 | 1672 |
| triangles | 39721 | 45735 |
| draw calls (measured) | 1915 | 88 |
| visible draw calls (estimate) | - | 54.0 |
| GPU texture MB (estimate) | 22.21 | 7.73 |

Navigation: reachable 3240.0 of 19147.0 m² standable; components 86.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 2, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 88 (> 80)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 47617 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
