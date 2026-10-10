# Checks: test_urban - NOT PASSED

errors 2 · warnings 32 · info 1

| metric | dev | mobile |
|---|---|---|
| file KB | 1665 | 1910 |
| triangles | 24576 | 27096 |
| draw calls (measured) | 729 | 183 |
| visible draw calls (estimate) | - | 64.8 |
| GPU texture MB (estimate) | 5.79 | 5.79 |

Navigation: reachable 24160.0 of 40371.0 m² standable; components 422.
Camera: 312 cameras, void rays 0, back faces 0.
Geometry: {'ERROR': 1, 'WARNING': 0, 'INTENTIONAL': 19} (checks/geometry.md)

## Issues (highest impact first)
- **error** terrain pokes 0.14 m through Bridge_West_Lane_Road_Canal_Deck [auto-repairable]
- **error** Skywalk: not reachable from the spawn (walk/drop/jump with the gameplay config)
- **warning** ~65 visible draw calls (estimate, > 60)
- **warning** Block_6_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Cross_Street_Sidewalk_R15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_01: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_02: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_03: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_04: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_05: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_06: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_07: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_08: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_10: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_11: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_12: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_13: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_14: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Post_15: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_01b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_02b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_03b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_04b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_05b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_06b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_07b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_08b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_09b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_10b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_11b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_12b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_13b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Fence_Park_Rail_14b: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **warning** Tower_C_Foundation: walkable width ~1.0 m (< 3.0 m) - tight for strafing / the camera
- **info** 409 m² reachable floor has < 3.2 m headroom (cramped camera): TR_1_0_concrete, TR_1_0_grass, TR_1_0_mud, TR_1_0_road, TR_1_1_mud, TR_1_1_road, West_Lane_Sidewalk_L30, West_Lane_Sidewalk_L32

Estimates are not device benchmarks; renders are the browser preview, not Godot.
