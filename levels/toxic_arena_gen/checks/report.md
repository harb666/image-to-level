# Checks: toxic_arena_gen - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 548 | 694 |
| triangles | 8474 | 7520 |
| draw calls (measured) | 256 | 60 |
| visible draw calls (estimate) | - | 45.2 |
| GPU texture MB (estimate) | 6.33 | 6.33 |

Navigation: reachable 1732.6 of 3106.6 m² standable; components 47.
Camera: 960 cameras, void rays 0, back faces 0.

## Issues (highest impact first)
- **info** 11 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
