# Checks: slime_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 5478 | 3025 |
| triangles | 76902 | 89004 |
| draw calls (measured) | 3782 | 76 |
| visible draw calls (estimate) | - | 52.4 |
| GPU texture MB (estimate) | 22.91 | 7.24 |

Navigation: reachable 9100.0 of 48663.0 m² standable; components 387.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** 94484 triangles (> budget 40000)
- **info** 88 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
