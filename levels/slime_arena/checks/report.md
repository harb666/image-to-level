# Checks: slime_arena - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 712 | 854 |
| triangles | 11302 | 13502 |
| draw calls (measured) | 388 | 67 |
| visible draw calls (estimate) | - | 42.5 |
| GPU texture MB (estimate) | 6.9 | 6.9 |

Navigation: reachable 1962.6 of 8389.6 m² standable; components 30.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **info** 41 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
