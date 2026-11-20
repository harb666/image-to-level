# Checks: scene_rave - PASSED

errors 0 · warnings 3 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 2212 | 1298 |
| triangles | 41232 | 45385 |
| draw calls (measured) | 1552 | 168 |
| visible draw calls (estimate) | - | 73.3 |
| GPU texture MB (estimate) | 12.64 | 6.64 |

Navigation: reachable 9528.0 of 12812.0 m² standable; components 133.
Camera: - cameras, void rays -, back faces -.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 30} (checks/geometry.md)

## Issues (highest impact first)
- **warning** mobile draw calls 168 (> 80)
- **warning** ~73 visible draw calls (estimate, > 60)
- **warning** 47754 triangles (> budget 40000)
- **info** 57 m² reachable floor has < 3.2 m headroom (cramped camera): DJ_Stage_Cap, Ground, Skull_E_Plinth, Skull_W_Plinth

Estimates are not device benchmarks; renders are the browser preview, not Godot.
