# Checks: slime_arena - PASSED

errors 0 · warnings 3 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6457 | 3966 |
| triangles | 99466 | 116936 |
| draw calls (measured) | 4845 | 131 |
| visible draw calls (estimate) | - | 72.1 |
| GPU texture MB (estimate) | 23.14 | 7.52 |

Navigation: reachable 9566.0 of 49182.0 m² standable; components 471.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 131 (> 80)
- **warning** ~72 visible draw calls (estimate, > 60)
- **warning** 124170 triangles (> budget 40000)
- **info** dev GLB 6457 KB (> 6000)
- **info** 44 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
