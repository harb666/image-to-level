# Checks: toxic_arena - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 390 | 419 |
| triangles | 3676 | 3364 |
| draw calls (measured) | 137 | 50 |
| visible draw calls (estimate) | - | 38.8 |
| GPU texture MB (estimate) | 3.9 | None |

Navigation: reachable 2224.8 of 3542.3 m² standable; components 50.
Camera: 1080 cameras, void rays 0, back faces 0.

## Issues (highest impact first)
- **info** 36 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
