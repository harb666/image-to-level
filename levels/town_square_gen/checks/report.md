# Checks: town_square_gen - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 749 | 929 |
| triangles | 8558 | 8534 |
| draw calls (measured) | 838 | 61 |
| visible draw calls (estimate) | - | 35.8 |
| GPU texture MB (estimate) | 4.4 | 4.4 |

Navigation: reachable 1407.0 of 1712.5 m² standable; components 24.
Camera: 696 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **info** 6 m² reachable floor has < 3.2 m headroom (cramped camera): Square_Ground

Estimates are not device benchmarks; renders are the browser preview, not Godot.
