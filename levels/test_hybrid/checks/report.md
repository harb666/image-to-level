# Checks: test_hybrid - PASSED

errors 0 · warnings 2 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4229 | 4972 |
| triangles | 54342 | 67142 |
| draw calls (measured) | 347 | 270 |
| visible draw calls (estimate) | - | 71.5 |
| GPU texture MB (estimate) | 9.33 | 9.83 |

Navigation: reachable 29198.0 of 41270.0 m² standable; components 1023.
Camera: 960 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 1, 'INTENTIONAL': 8} (checks/geometry.md)

## Issues (highest impact first)
- **warning** Tower_Stairs_Beam_R stands in the landing of Dock_Stairs.high (blocks the route)
- **warning** ~72 visible draw calls (estimate, > 60)
- **info** 161 m² reachable floor has < 3.2 m headroom (cramped camera): Ground, TR_0_1_dirt, TR_1_0_dirt, TR_1_1_dirt, TR_2_1_dirt, TR_2_1_mud, TR_2_1_road, TR_2_2_dirt

Estimates are not device benchmarks; renders are the browser preview, not Godot.
