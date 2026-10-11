# Checks: slime_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3742 | 2408 |
| triangles | 52071 | 66050 |
| draw calls (measured) | 2559 | 67 |
| visible draw calls (estimate) | - | 46.3 |
| GPU texture MB (estimate) | 9.44 | 4.81 |

Navigation: reachable 9087.0 of 48845.0 m² standable; components 387.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** 68069 triangles (> budget 40000)
- **info** 91 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
