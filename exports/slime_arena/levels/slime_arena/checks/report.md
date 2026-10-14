# Checks: slime_arena - PASSED

errors 0 · warnings 2 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 5938 | 3482 |
| triangles | 87288 | 102891 |
| draw calls (measured) | 4234 | 92 |
| visible draw calls (estimate) | - | 58.7 |
| GPU texture MB (estimate) | 23.22 | 7.43 |

Navigation: reachable 9256.0 of 48811.0 m² standable; components 446.
Camera: 1056 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 92 (> 80)
- **warning** 109046 triangles (> budget 40000)
- **info** 54 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
