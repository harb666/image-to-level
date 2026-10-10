# Checks: test_hybrid - NOT PASSED

errors 8 · warnings 7 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4302 | 5020 |
| triangles | 55450 | 68250 |
| draw calls (measured) | 368 | 279 |
| visible draw calls (estimate) | - | 73.6 |
| GPU texture MB (estimate) | 9.33 | 9.83 |

Navigation: reachable 29121.0 of 41261.0 m² standable; components 1004.
Camera: 960 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 7, 'WARNING': 2, 'INTENTIONAL': 8} (checks/geometry.md)

## Issues (highest impact first)
- **error** Link_Ground_Gantry_A.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_B.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Tower_Top.low leads nowhere (no floor within 4 m at step height)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B.high (blocks the route)
- **error** Link_Ground_Gantry_A is declared supported_by Link_Ground_Gantry_A_Support but does not touch it
- **error** Link_Ground_Gantry_B is declared supported_by Link_Ground_Gantry_B_Support but does not touch it
- **error** Ridge_Post: not reachable from the spawn (walk/drop/jump with the gameplay config)
- **warning** Link_Ground_Tower stands in the landing of Link_Ground_Gantry_B.low (blocks the route)
- **warning** Link_Ground_Gantry_A stands in the landing of Link_Ground_Tower_Top.low (blocks the route)
- **warning** ~74 visible draw calls (estimate, > 60)
- **warning** Gantry_A_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Gantry_B_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Gantry_Bridge_Deck: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Tower_Top_Trim: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **info** 160 m² reachable floor has < 3.2 m headroom (cramped camera): TR_0_1_dirt, TR_1_0_dirt, TR_1_1_dirt, TR_1_2_dirt, TR_1_2_grass, TR_1_3_dirt, TR_2_1_dirt, TR_2_1_mud

Estimates are not device benchmarks; renders are the browser preview, not Godot.
