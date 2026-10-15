# Checks: slime_arena - PASSED

errors 0 · warnings 3 · info 2

| metric | dev | mobile |
|---|---|---|
| file KB | 6382 | 3899 |
| triangles | 97774 | 114422 |
| draw calls (measured) | 4801 | 125 |
| visible draw calls (estimate) | - | 70.0 |
| GPU texture MB (estimate) | 23.14 | 7.52 |

Navigation: reachable 9620.0 of 49147.0 m² standable; components 448.
Camera: 1080 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 125 (> 80)
- **warning** ~70 visible draw calls (estimate, > 60)
- **warning** 121602 triangles (> budget 40000)
- **info** dev GLB 6382 KB (> 6000)
- **info** 44 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
