# Checks: slime_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 5828 | 3462 |
| triangles | 87784 | 102917 |
| draw calls (measured) | 4292 | 77 |
| visible draw calls (estimate) | - | 55.2 |
| GPU texture MB (estimate) | 22.95 | 7.28 |

Navigation: reachable 9224.0 of 48811.0 m² standable; components 438.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** 108974 triangles (> budget 40000)
- **info** 76 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
