# Checks: test_valley - PASSED

errors 0 · warnings 0 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 5569 | 6343 |
| triangles | 71090 | 83890 |
| draw calls (measured) | 245 | 238 |
| visible draw calls (estimate) | - | 53.4 |
| GPU texture MB (estimate) | 3.42 | 3.58 |

Navigation: reachable 27649.0 of 37826.0 m² standable; components 1252.
Camera: 288 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 0, 'WARNING': 0, 'INTENTIONAL': 2} (checks/geometry.md)

## Issues (highest impact first)
- **info** 922 m² reachable floor has < 3.2 m headroom (cramped camera): Cave, SC_Rocks__64_1_1, SC_Rocks__64_3_1, TR_0_1_grass, TR_0_2_dirt, TR_0_2_grass, TR_0_2_gravel, TR_1_0_dirt

Estimates are not device benchmarks; renders are the browser preview, not Godot.
