# Checks: assembly_ascent - PASSED

errors 0 · warnings 6 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3260 | 1771 |
| triangles | 41521 | 47615 |
| draw calls (measured) | 2046 | 99 |
| visible draw calls (estimate) | - | 58.0 |
| GPU texture MB (estimate) | 22.71 | 8.06 |

Navigation: reachable 3881.0 of 19766.0 m² standable; components 103.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 99 (> 80)
- **warning** enemy_arena: hazard 0.3 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 49573 triangles (> budget 40000)
- **info** 15 m² reachable floor has < 3.2 m headroom (cramped camera): OuterWall_East_M12Monitor_Body, Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
