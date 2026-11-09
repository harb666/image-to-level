# Checks: assembly_ascent - PASSED

errors 0 · warnings 6 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3360 | 1958 |
| triangles | 45777 | 52039 |
| draw calls (measured) | 2228 | 100 |
| visible draw calls (estimate) | - | 58.7 |
| GPU texture MB (estimate) | 22.71 | 8.06 |

Navigation: reachable 3974.0 of 19865.0 m² standable; components 106.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 3, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** OuterWall_East_M05Vent_FrameSide_2 and OuterWall_East_M05Vent_Red share coplanar faces (0.07 m², different materials): z-fighting flicker [auto-repairable]
- **warning** OuterWall_East_M05Vent and OuterWall_East_M05Vent_Red share coplanar faces (0.19 m², different materials): z-fighting flicker [auto-repairable]
- **warning** mobile draw calls 100 (> 80)
- **warning** enemy_arena: hazard 0.5 m away (< 3.0 m)
- **warning** Exit_Stairs: walking up the right lane the player is stopped by an edge / lip
- **warning** 54005 triangles (> budget 40000)
- **info** 3 m² reachable floor has < 3.2 m headroom (cramped camera): Robot_Ring_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
