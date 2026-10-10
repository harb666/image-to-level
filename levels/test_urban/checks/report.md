# Checks: test_urban - NOT PASSED

errors 1 · warnings 6 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 1747 | 1965 |
| triangles | 24896 | 27416 |
| draw calls (measured) | 723 | 185 |
| visible draw calls (estimate) | - | 65.5 |
| GPU texture MB (estimate) | 6.04 | 6.04 |

Navigation: reachable 24279.0 of 40341.0 m² standable; components 440.
Camera: 312 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 1, 'WARNING': 0, 'INTENTIONAL': 19} (checks/geometry.md)

## Issues (highest impact first)
- **error** terrain pokes 0.11 m through Bridge_West_Lane_Road_Canal_Deck [auto-repairable]
- **warning** ~66 visible draw calls (estimate, > 60)
- **warning** Block_6_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Cross_Street_Sidewalk_R15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Skywalk_Stairs_From: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Skywalk_Stairs_To: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Tower_C_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **info** 377 m² reachable floor has < 3.2 m headroom (cramped camera): TR_1_0_concrete, TR_1_0_grass, TR_1_0_mud, TR_1_0_road, TR_1_1_mud, TR_1_1_road, West_Lane_Sidewalk_L30, West_Lane_Sidewalk_L32

Estimates are not device benchmarks; renders are the browser preview, not Godot.
