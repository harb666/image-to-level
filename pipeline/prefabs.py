"""Stage 3 prefabs: expand a high-level structure into named, editable level.json objects (group + children).

From a layout script:   objs += prefabs.catwalk("Catwalk_01", start=[0, 6, -10], end=[0, 6, 10])
From the command line:  python3 pipeline/prefabs.py levels/<name> add catwalk '{"name":"Catwalk_01","start":[0,6,-10],"end":[0,6,10]}'
                        python3 pipeline/prefabs.py levels/<name> list
After adding: python3 pipeline/build_level.py levels/<name>  (then validate_level.py).
Every child is a normal object (box/railing/ibeam/rock/arch/...) so it can be moved, resized, re-materialed or removed.
Missing default materials (pf_*) are added to the level automatically; remap them freely.
"""
import json, math, sys

DEFAULT_MATERIALS = {
    "pf_grating": {"type": "grating", "color": [0.3, 0.31, 0.3], "tile_m": 2.0},
    "pf_metal": {"type": "industrial_metal", "color": [0.24, 0.25, 0.25], "tile_m": 3.0, "bevel": 0.04},
    "pf_rail": {"type": "painted_metal", "color": [0.55, 0.45, 0.12], "tile_m": 2.0, "res": 256},
    "pf_pipe": {"type": "pipe", "color": [0.24, 0.27, 0.26], "tile_m": 2.5},
    "pf_rock": {"type": "rock", "color": [0.3, 0.29, 0.27], "tile_m": 6.0, "res": 256},
    "pf_machine": {"type": "machinery_panel", "color": [0.23, 0.24, 0.24], "tile_m": 2.0, "accent": [1.0, 0.12, 0.08], "emissive": [1, 1, 1]},
    "pf_concrete": {"type": "concrete", "color": [0.45, 0.44, 0.42], "tile_m": 4.0, "bevel": 0.08},
}


def _o(**k):
    k.setdefault("rotation", [0, 0, 0]); return k


def catwalk(name, start, end, width=2.2, rails=True, supports=True, ground_y=0.0, deck="pf_grating", frame="pf_metal", rail="pf_rail", spacing=8.0):
    """Straight walkway from start to end (deck top at their height): grated deck, I-beam edges, railings, support legs."""
    dx, dz = end[0] - start[0], end[2] - start[2]; L = math.hypot(dx, dz); yaw = math.degrees(math.atan2(-dz, dx))  # local +x along the walk
    y = start[1]; cx, cz = (start[0] + end[0]) / 2, (start[2] + end[2]) / 2
    o = [_o(name=name, type="group", position=[cx, 0, cz], rotation=[0, round(yaw, 2), 0]),
         _o(name=name + "_Deck", parent=name, type="box", material=deck, position=[0, y - 0.15, 0], size=[L, 0.15, width])]
    for s, side in ((1, "L"), (-1, "R")):
        o.append(_o(name=f"{name}_Beam_{side}", parent=name, type="ibeam", material=frame, position=[0, y - 0.55, s * (width / 2 - 0.12)], size=[L, 0.4, 0.24]))
        if rails: o.append(_o(name=f"{name}_Rail_{side}", parent=name, type="rail_run", material=rail, position=[0, 0, 0], size=[L, 1.05, 0.07],
                              points=[[round(-L / 2 + 0.2, 3), y, s * (width / 2 - 0.04)], [round(L / 2 - 0.2, 3), y, s * (width / 2 - 0.04)]], post_spacing=1.6))
    if supports and y - ground_y > 1.0:
        n = max(2, int(L / spacing) + 1)
        for i in range(n):
            x = -L / 2 + 0.3 + (L - 0.6) * i / (n - 1)
            o.append(_o(name=f"{name}_Support_{i + 1:02d}", parent=name, type="box", material=frame, position=[round(x, 2), ground_y, 0], size=[0.4, round(y - 0.55 - ground_y, 2), width * 0.6]))
    return o


def railing_along(name, start, end, height=1.05, material="pf_rail"):
    """Free-standing railing between two points (e.g. along a platform edge). Points are the post bases ON the floor;
    different heights give a sloped run (vertical posts, rails parallel to the slope)."""
    return railing_path(name, [start, end], height, material)


def railing_path(name, points, height=1.05, material="pf_rail", spacing=1.6):
    """Railing along a polyline of floor points [[x, y, z], ...] (corners and flat/slope transitions are vertices).
    A rail_run in world coordinates; geometry_check verifies every post stands on a surface (snap_rail repairs it)."""
    P = [[round(float(v), 3) for v in p] for p in points]
    L = sum(math.dist(a, b) for a, b in zip(P[:-1], P[1:]))
    return [_o(name=name, type="rail_run", material=material, position=[0, 0, 0], size=[round(max(L, 0.1), 2), height, 0.07], points=P, post_spacing=spacing)]


def pipe_run(name, points, radius=0.5, material="pf_pipe", junction="pf_metal"):
    """Pipe through a list of points (segments may be in any direction); flanges at both ends of every segment,
    junction blocks at corners. Points are pipe centre-lines."""
    o = [_o(name=name, type="group", position=[0, 0, 0])]
    for i, (a, b) in enumerate(zip(points[:-1], points[1:])):
        d = [b[k] - a[k] for k in range(3)]; L = math.sqrt(sum(x * x for x in d))
        yaw = math.degrees(math.atan2(d[0], d[2])); pitch = math.degrees(math.asin(max(-1, min(1, d[1] / L))))
        rot = [round(90 - pitch, 2), round(yaw, 2), 0]  # cylinder (+y) rotated onto the segment direction
        o.append(_o(name=f"{name}_Seg_{i + 1:02d}", parent=name, type="cylinder", sections=10, material=material, position=list(a), rotation=rot, size=[2 * radius, round(L, 2), 2 * radius]))
        for j, p in enumerate((a, b)):
            ft = 0.25  # flanges sit 1 cm inside the segment ends: no coplanar end discs (Stage 8)
            fp = [p[k] + (d[k] / L) * (0.01 if j == 0 else -ft - 0.01) for k in range(3)]
            o.append(_o(name=f"{name}_Flange_{i + 1:02d}{'ab'[j]}", parent=name, type="cylinder", sections=10, material=junction, position=[round(v, 3) for v in fp], rotation=rot, size=[2 * radius * 1.3, ft, 2 * radius * 1.3]))
    for i, p in enumerate(points[1:-1]):
        o.append(_o(name=f"{name}_Junction_{i + 1:02d}", parent=name, type="box", material=junction, position=[p[0], p[1] - radius * 1.4, p[2]], size=[radius * 2.8] * 3))
    return o


def rock_cluster(name, center, radius=6.0, count=5, size=(2.0, 5.0), seed=1, material="pf_rock"):
    import random; r = random.Random(seed); o = [_o(name=name, type="group", position=list(center))]
    for i in range(count):
        a, d = r.uniform(0, 2 * math.pi), r.uniform(0, radius); s = r.uniform(*size)
        o.append(_o(name=f"{name}_Rock_{i + 1:02d}", parent=name, type="rock", material=material, seed=seed * 100 + i,
                    position=[round(d * math.sin(a), 2), 0, round(-d * math.cos(a), 2)], rotation=[0, round(r.uniform(0, 360), 1), 0],
                    size=[round(s * r.uniform(0.8, 1.3), 2), round(s * r.uniform(0.6, 1.0), 2), round(s * r.uniform(0.8, 1.3), 2)]))
    return o


def gate(name, position, yaw=0, width=8.0, height=7.0, depth=3.0, material="pf_metal", light="pf_machine"):
    """Gateway/tunnel mouth along local z: arch (passable opening) + warning light panels either side."""
    ow = width * 0.6
    return [_o(name=name, type="group", position=list(position), rotation=[0, yaw, 0]),
            _o(name=name + "_Arch", parent=name, type="arch", material=material, position=[0, 0, 0], size=[width, height, depth], opening=0.6, opening_h=0.75, bevel=0.08),
            _o(name=name + "_Lights", parent=name, type="vent", material=light, position=[0, height * 0.75 + 0.2, depth / 2 + 0.05], size=[ow * 0.6, 0.6, 0.3])]


def machinery_bank(name, position, yaw=0, seed=1, material="pf_machine", tank_material="pf_metal"):
    return [_o(name=name, type="group", position=list(position), rotation=[0, yaw, 0]),
            _o(name=name + "_Unit", parent=name, type="machinery", material=material, seed=seed, position=[0, 0, 0], size=[4, 3, 2.5]),
            _o(name=name + "_Tank", parent=name, type="tank", material=tank_material, position=[3.6, 0, 0], size=[2.4, 4, 2.4]),
            _o(name=name + "_Vent", parent=name, type="vent", material=material, position=[-3.2, 0, 0], size=[1.8, 1.6, 0.6])]


PREFABS = dict(catwalk=catwalk, railing_along=railing_along, railing_path=railing_path, pipe_run=pipe_run, rock_cluster=rock_cluster, gate=gate, machinery_bank=machinery_bank)


def add_to_level(level_dir, prefab, kwargs):
    import os
    p = os.path.join(level_dir, "level.json"); L = json.load(open(p))
    names = {o["name"] for o in L["objects"]}
    new = PREFABS[prefab](**kwargs); clash = [o["name"] for o in new if o["name"] in names]
    if clash: raise SystemExit(f"name(s) already exist: {clash[:5]} - choose another name")
    for o in new:
        for k in ("material", "top_material"):
            if o.get(k) in DEFAULT_MATERIALS and o[k] not in L["materials"]: L["materials"][o[k]] = DEFAULT_MATERIALS[o[k]]
    L["objects"] += new; json.dump(L, open(p, "w"), indent=1)
    print(f"added {len(new)} objects ({new[0]['name']}...) to {p}")


if __name__ == "__main__":
    if sys.argv[2] == "list":
        for k, f in PREFABS.items(): print(k, f.__doc__.strip().splitlines()[0] if f.__doc__ else "")
    else:
        add_to_level(sys.argv[1], sys.argv[3], json.loads(sys.argv[4]))
