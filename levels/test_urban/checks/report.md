# Checks: test_urban - PASSED

errors 0 · warnings 1 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 1746 | 1964 |
| triangles | 24896 | 27416 |
| draw calls (measured) | 723 | 185 |
| visible draw calls (estimate) | - | 65.4 |
| GPU texture MB (estimate) | 6.04 | 6.04 |

Navigation: reachable 24279.0 of 40410.0 m² standable; components 462.
Camera: 312 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 19} (checks/geometry.md)

## Issues (highest impact first)
- **warning** ~65 visible draw calls (estimate, > 60)
- **info** 377 m² reachable floor has < 3.2 m headroom (cramped camera): TR_1_0_concrete, TR_1_0_grass, TR_1_0_mud, TR_1_0_road, TR_1_1_mud, TR_1_1_road, West_Lane_Sidewalk_L30, West_Lane_Sidewalk_L32

Estimates are not device benchmarks; renders are the browser preview, not Godot.
