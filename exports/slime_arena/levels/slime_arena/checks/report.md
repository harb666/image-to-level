# Checks: slime_arena - PASSED

errors 0 · warnings 3 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6052 | 3628 |
| triangles | 91298 | 106714 |
| draw calls (measured) | 4506 | 121 |
| visible draw calls (estimate) | - | 68.6 |
| GPU texture MB (estimate) | 22.89 | 7.27 |

Navigation: reachable 9586.0 of 49113.0 m² standable; components 447.
Camera: 1080 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 121 (> 80)
- **warning** ~69 visible draw calls (estimate, > 60)
- **warning** 113350 triangles (> budget 40000)
- **info** dev GLB 6052 KB (> 6000)
- **info** 44 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
