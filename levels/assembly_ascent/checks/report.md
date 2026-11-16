# Checks: assembly_ascent - PASSED

errors 0 · warnings 7 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4032 | 2372 |
| triangles | 54416 | 61386 |
| draw calls (measured) | 2564 | 135 |
| visible draw calls (estimate) | - | 74.4 |
| GPU texture MB (estimate) | 26.4 | 10.76 |

Navigation: reachable 5427.0 of 20147.0 m² standable; components 122.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 135 (> 80)
- **warning** ~74 visible draw calls (estimate, > 60)
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 63828 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
