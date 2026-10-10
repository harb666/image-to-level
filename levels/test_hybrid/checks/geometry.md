# Geometry: test_hybrid - NOT PASSED

{'ERROR': 7, 'WARNING': 2, 'INTENTIONAL': 8} · relations {'explicit': 39, 'inferred': 0} · auto-repairable 0

- **ERROR** [connection] Link_Ground_Gantry_A.low leads nowhere (no floor within 4 m at step height)
- **ERROR** [connection] Link_Ground_Gantry_B.low leads nowhere (no floor within 4 m at step height)
- **ERROR** [connection] Link_Ground_Tower_Top.low leads nowhere (no floor within 4 m at step height)
- **ERROR** [connection] railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_A.high (blocks the route)
- **ERROR** [connection] railing Gantry_Bridge_Rail_L stands in the landing of Link_Ground_Gantry_B.high (blocks the route)
- **ERROR** [support] Link_Ground_Gantry_A is declared supported_by Link_Ground_Gantry_A_Support but does not touch it
- **ERROR** [support] Link_Ground_Gantry_B is declared supported_by Link_Ground_Gantry_B_Support but does not touch it
- **WARNING** [connection] Link_Ground_Tower stands in the landing of Link_Ground_Gantry_B.low (blocks the route)
- **WARNING** [connection] Link_Ground_Gantry_A stands in the landing of Link_Ground_Tower_Top.low (blocks the route)
- **INTENTIONAL** [boundary] playable boundary edge 1: Haul_Road leaves the area through a gap in the barrier (invisible collider there)
- **INTENTIONAL** [boundary] playable boundary edge 3: River leaves the area through a gap in the barrier (invisible collider there)
- **INTENTIONAL** [boundary] playable boundary edge 8: South_Road leaves the area through a gap in the barrier (invisible collider there)
- **INTENTIONAL** [unreachable] 163 m² standable area at [0.8, 29.3] not reachable from the spawn (on OuterWall (roof / top, no access): inaccessible by design)
- **INTENTIONAL** [unreachable] 840 m² standable area at [63.2, 26.1] not reachable from the spawn (on Haul (roof / top, no access): inaccessible by design)
- **INTENTIONAL** [unreachable] 171 m² standable area at [-87.2, 30.4] not reachable from the spawn (on Factory (roof / top, no access): inaccessible by design)
- **INTENTIONAL** [unreachable] 162 m² standable area at [-72.8, 29.6] not reachable from the spawn (on Factory (roof / top, no access): inaccessible by design)
- **INTENTIONAL** [unreachable] 168 m² standable area at [-79.8, 39.6] not reachable from the spawn (on Factory (roof / top, no access): inaccessible by design)
