# Checks: slime_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4890 | 2675 |
| triangles | 67550 | 80283 |
| draw calls (measured) | 3374 | 74 |
| visible draw calls (estimate) | - | 50.6 |
| GPU texture MB (estimate) | 22.83 | 7.2 |

Navigation: reachable 9085.0 of 48682.0 m² standable; components 388.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** 85192 triangles (> budget 40000)
- **info** 98 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
