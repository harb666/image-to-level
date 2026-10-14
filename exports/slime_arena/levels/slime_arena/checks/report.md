# Checks: slime_arena - PASSED

errors 0 · warnings 2 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6140 | 3646 |
| triangles | 91846 | 107941 |
| draw calls (measured) | 4633 | 93 |
| visible draw calls (estimate) | - | 59.6 |
| GPU texture MB (estimate) | 22.95 | 7.28 |

Navigation: reachable 9256.0 of 48773.0 m² standable; components 436.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 93 (> 80)
- **warning** 114024 triangles (> budget 40000)
- **info** dev GLB 6140 KB (> 6000)
- **info** 54 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
