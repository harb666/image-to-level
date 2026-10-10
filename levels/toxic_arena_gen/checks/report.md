# Checks: toxic_arena_gen - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 567 | 723 |
| triangles | 9674 | 8720 |
| draw calls (measured) | 252 | 58 |
| visible draw calls (estimate) | - | 44.1 |
| GPU texture MB (estimate) | 6.33 | 6.33 |

Navigation: reachable 1869.6 of 3257.5 m² standable; components 36.
Camera: 1032 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **info** 41 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
