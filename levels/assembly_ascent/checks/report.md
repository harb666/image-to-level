# Checks: assembly_ascent - PASSED

errors 0 · warnings 5 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3220 | 1741 |
| triangles | 41217 | 47261 |
| draw calls (measured) | 2027 | 94 |
| visible draw calls (estimate) | - | 55.7 |
| GPU texture MB (estimate) | 22.46 | 7.81 |

Navigation: reachable 3531.0 of 19416.0 m² standable; components 102.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 2, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 94 (> 80)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 49233 triangles (> budget 40000)
- **info** 5 m² reachable floor has < 3.2 m headroom (cramped camera): OuterWall_East_M12Monitor_Body, Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
