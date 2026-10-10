# Checks: toxic_arena - PASSED

errors 0 · warnings 2 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 415 | 460 |
| triangles | 5180 | 4868 |
| draw calls (measured) | 137 | 50 |
| visible draw calls (estimate) | - | 38.8 |
| GPU texture MB (estimate) | 3.9 | 3.9 |

Navigation: reachable 2388.3 of 3716.0 m² standable; components 40.
Camera: 1032 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 0} (checks/geometry.md)

## Issues (highest impact first)
- **warning** PipeRun_East_01: walkable width ~1.5 m (< 3.0 m) - tight for strafing / the camera
- **warning** PipeRun_South_01: walkable width ~1.5 m (< 3.0 m) - tight for strafing / the camera
- **info** 70 m² reachable floor has < 3.2 m headroom (cramped camera): Walkway_East_Floor, Walkway_North_Floor, Walkway_South_Floor, Walkway_West_Floor

Estimates are not device benchmarks; renders are the browser preview, not Godot.
