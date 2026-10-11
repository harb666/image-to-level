# Checks: slime_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3648 | 2335 |
| triangles | 51503 | 67408 |
| draw calls (measured) | 2652 | 72 |
| visible draw calls (estimate) | - | 49.0 |
| GPU texture MB (estimate) | 6.77 | 3.48 |

Navigation: reachable 9090.0 of 48829.0 m² standable; components 382.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** 69517 triangles (> budget 40000)
- **info** 88 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
