# Checks: slime_arena - PASSED

errors 0 · warnings 3 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6560 | 4000 |
| triangles | 100920 | 119205 |
| draw calls (measured) | 4943 | 140 |
| visible draw calls (estimate) | - | 75.2 |
| GPU texture MB (estimate) | 23.14 | 7.52 |

Navigation: reachable 9635.0 of 49516.0 m² standable; components 480.
Camera: 984 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 140 (> 80)
- **warning** ~75 visible draw calls (estimate, > 60)
- **warning** 126526 triangles (> budget 40000)
- **info** dev GLB 6560 KB (> 6000)
- **info** 44 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
