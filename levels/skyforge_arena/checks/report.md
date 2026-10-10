# Checks: skyforge_arena - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 3910 | 4429 |
| triangles | 60756 | 69506 |
| draw calls (measured) | 493 | 252 |
| visible draw calls (estimate) | - | 67.6 |
| GPU texture MB (estimate) | 6.81 | 6.81 |

Navigation: reachable 4262.0 of 29400.3 m² standable; components 89.
Camera: 984 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 2} (checks/geometry.md)

## Issues (highest impact first)
- **warning** ~68 visible draw calls (estimate, > 60)
- **info** 0 m² reachable floor has < 3.2 m headroom (cramped camera): Link_North_NW_Deck

Estimates are not device benchmarks; renders are the browser preview, not Godot.
