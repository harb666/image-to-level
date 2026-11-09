# Checks: assembly_ascent - PASSED

errors 0 · warnings 5 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3158 | 1690 |
| triangles | 39945 | 45959 |
| draw calls (measured) | 1931 | 88 |
| visible draw calls (estimate) | - | 54.0 |
| GPU texture MB (estimate) | 22.46 | 7.81 |

Navigation: reachable 3248.0 of 19155.0 m² standable; components 90.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 2, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 88 (> 80)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 47841 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
