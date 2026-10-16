# Checks: slime_arena - PASSED

errors 0 · warnings 3 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6503 | 3967 |
| triangles | 99818 | 117800 |
| draw calls (measured) | 4913 | 140 |
| visible draw calls (estimate) | - | 75.0 |
| GPU texture MB (estimate) | 23.14 | 7.52 |

Navigation: reachable 9596.0 of 49443.0 m² standable; components 486.
Camera: 984 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 140 (> 80)
- **warning** ~75 visible draw calls (estimate, > 60)
- **warning** 125080 triangles (> budget 40000)
- **info** dev GLB 6503 KB (> 6000)
- **info** 44 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
