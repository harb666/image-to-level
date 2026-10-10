# Checks: test_hybrid - NOT PASSED

errors 76 · warnings 26 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 4309 | 5032 |
| triangles | 56502 | 69302 |
| draw calls (measured) | 371 | 270 |
| visible draw calls (estimate) | - | 71.7 |
| GPU texture MB (estimate) | 9.33 | 9.83 |

Navigation: reachable 27686.0 of 41266.0 m² standable; components 1028.
Camera: 888 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 47, 'WARNING': 13, 'INTENTIONAL': 9} (checks/geometry.md)

## Issues (highest impact first)
- **error** Link_Ground_Gantry_A.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_B.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Tower_Top.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_A_2.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_B_2.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Tower_Top_2.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_A_2.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Gantry_B_2.low leads nowhere (no floor within 4 m at step height)
- **error** Link_Ground_Tower_Top_2.low leads nowhere (no floor within 4 m at step height)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A_2.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B_2.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A_2.high (blocks the route)
- **error** railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B_2.high (blocks the route)
- **error** relations[59] (supported_by): object 'Link_Ground_Gantry_A_3' does not exist
- **error** relations[59] (supported_by): object 'Link_Ground_Gantry_A_Support_3' does not exist
- **error** relations[60] (supported_by): object 'Link_Ground_Gantry_A_Junction_Hi_3' does not exist
- **error** relations[61] (walkable_connection): object 'Link_Ground_Gantry_A_3' does not exist
- **error** relations[61] (walkable_connection): object 'Link_Ground_Gantry_A_Junction_Hi_3' does not exist
- **error** relations[62] (supported_by): object 'Link_Ground_Gantry_A_Junction_Lo_3' does not exist
- **error** relations[63] (walkable_connection): object 'Link_Ground_Gantry_A_3' does not exist
- **error** relations[63] (walkable_connection): object 'Link_Ground_Gantry_A_Junction_Lo_3' does not exist
- **error** relations[64] (supported_by): object 'Link_Ground_Gantry_B_3' does not exist
- **error** relations[64] (supported_by): object 'Link_Ground_Gantry_B_Support_3' does not exist
- **error** relations[65] (supported_by): object 'Link_Ground_Gantry_B_Junction_Hi_3' does not exist
- **error** relations[66] (walkable_connection): object 'Link_Ground_Gantry_B_3' does not exist
- **error** relations[66] (walkable_connection): object 'Link_Ground_Gantry_B_Junction_Hi_3' does not exist
- **error** relations[67] (supported_by): object 'Link_Ground_Gantry_B_Junction_Lo_3' does not exist
- **error** relations[68] (walkable_connection): object 'Link_Ground_Gantry_B_3' does not exist
- **error** relations[68] (walkable_connection): object 'Link_Ground_Gantry_B_Junction_Lo_3' does not exist
- **error** relations[69] (supported_by): object 'Link_Ground_Tower_Top_3' does not exist
- **error** relations[69] (supported_by): object 'Link_Ground_Tower_Top_Support_3' does not exist
- **error** relations[70] (supported_by): object 'Link_Ground_Tower_Top_Junction_Hi_3' does not exist
- **error** relations[71] (walkable_connection): object 'Link_Ground_Tower_Top_3' does not exist
- **error** relations[71] (walkable_connection): object 'Link_Ground_Tower_Top_Junction_Hi_3' does not exist
- **error** relations[72] (supported_by): object 'Link_Ground_Tower_Top_Junction_Lo_3' does not exist
- **error** relations[73] (walkable_connection): object 'Link_Ground_Tower_Top_3' does not exist
- **error** relations[73] (walkable_connection): object 'Link_Ground_Tower_Top_Junction_Lo_3' does not exist
- **error** Link_Ground_Gantry_A is declared supported_by Link_Ground_Gantry_A_Support but does not touch it

Estimates are not device benchmarks; renders are the browser preview, not Godot.
