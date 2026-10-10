"""Stage 9 urban / futuristic / industrial modules: street, futuristic_tower, office_block, factory, container,
barrier_line, wreck, billboard, antenna, fence. Footprint modules (pad=True) get a terrain pad + foundation on open
ground; line modules ('from' / 'to') follow the terrain. Roles come from the theme palette (THEMES)."""
import math
import numpy as np
import architecture as A
from modules import structure


def _line(s):
    (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); return ax, az, bx, bz, L, (bx - ax) / L, (bz - az) / L


def _in_play(ctx, x, z, inset=4.0):
    B = getattr(ctx, "boundary", None)
    if not B: return True
    from terrain import inside_poly, poly_query
    return bool(inside_poly(B, np.array([x]), np.array([z]))[0]) and poly_query(B, np.array([x]), np.array([z]), closed=True)[0][0] > inset


def _street_terrain(s, TR0):
    w = s.get("width", 8.0) + 2 * s.get("sidewalk", 2.5)
    return [dict(id=s["id"] + "_Road", type="street", points=[s["from"], s["to"]], width=s.get("width", 8.0), shoulder=s.get("sidewalk", 2.5) + 2.5,
                 max_grade=0.08, smooth=20, deck_width=round(w + 0.6, 2), flat_width=round(w + 1.0, 2), extend=False)]


@structure("street", pad=False, terrain=_street_terrain)
def street(ctx, s, x, y, z, yaw):
    """Urban street: asphalt roadway (terrain layer), raised kerbed sidewalks following the grade, street lamps."""
    ax, az, bx, bz, L, ux, uz = _line(s); rw = s.get("width", 8.0); sw = s.get("sidewalk", 2.5); n = s["id"]; TR = ctx.TR
    seg = 4.0; k = max(1, int(round(L / seg))); nx, nz = uz, -ux
    others = [o for o in ctx.spec.get("structures", []) if o["kind"] == "street" and o["id"] != s["id"]]
    def crossing(px, pz):  # inside another street's roadway + kerb: intersection, no sidewalk / lamp there
        from terrain import poly_query
        return any(poly_query([o["from"], o["to"]], np.array([px]), np.array([pz]))[0][0] < o.get("width", 8.0) / 2 + o.get("sidewalk", 2.5) + 0.6 for o in others)
    for side, sg in (("L", -1), ("R", 1)):
        off = sg * (rw / 2 + sw / 2)
        for i in range(k):
            t0, t1 = L * i / k, L * (i + 1) / k; cx, cz = ax + ux * (t0 + t1) / 2 + nx * off, az + uz * (t0 + t1) / 2 + nz * off
            if crossing(cx, cz) or crossing(ax + ux * t0 + nx * off, az + uz * t0 + nz * off) or crossing(ax + ux * t1 + nx * off, az + uz * t1 + nz * off): continue
            if not _in_play(ctx, cx, cz): continue  # beyond the playable boundary the street only continues as terrain
            if TR is not None and TR._river_mask(np.array([cx, ax + ux * t0 + nx * off, ax + ux * t1 + nx * off]), np.array([cz, az + uz * t0 + nz * off, az + uz * t1 + nz * off])).any(): continue  # the bridge carries it
            y0 = TR.height_at(ax + ux * t0 + nx * off, az + uz * t0 + nz * off) if TR else y; y1 = TR.height_at(ax + ux * t1 + nx * off, az + uz * t1 + nz * off) if TR else y
            pitch = -math.degrees(math.atan2(y1 - y0, t1 - t0)); yc = (y0 + y1) / 2
            ctx.add(f"{n}_Sidewalk_{side}{i + 1:02d}", "box", [cx, yc - 0.45, cz], [sw, 0.6, (t1 - t0) + 0.02], "deck", rot=[pitch, A.yaw_to(ux, uz), 0], vkey=n + "sw")
    if s.get("lamps", True):
        for i in range(int(L // 18) + 1):
            t = min(L - 2, 2 + i * 18); sg = -1 if i % 2 else 1; off = sg * (rw / 2 + sw - 0.5); px, pz = ax + ux * t + nx * off, az + uz * t + nz * off
            if crossing(px, pz) or (TR is not None and TR._river_mask(np.array([px]), np.array([pz]))[0] > 0) or not _in_play(ctx, px, pz): continue
            py = (TR.height_at(px, pz) if TR else y) + 0.1; g = ctx.add(f"{n}_Lamp_{i + 1:02d}", "group", [px, py, pz], rot=[0, A.yaw_to(-nx * sg, -nz * sg), 0])
            ctx.add(f"{n}_Lamp_{i + 1:02d}_Post", "cylinder", [0, -0.3, 0], [0.22, 6.3, 0.22], "frame", g, sections=6)
            ctx.add(f"{n}_Lamp_{i + 1:02d}_Arm", "box", [0, 5.8, 0.7], [0.15, 0.15, 1.5], "frame", g)
            ctx.add(f"{n}_Lamp_{i + 1:02d}_Light", "box", [0, 5.55, 1.3], [0.5, 0.25, 0.7], "glow", g)


@structure("futuristic_tower", pad=True, needs_size=True)
def futuristic_tower(ctx, s, x, y, z, yaw):
    """Sci-fi high-rise: stepped setbacks (2-4 tiers), lit window bands on every face, crown light ring, antenna,
    entrance canopy at the front (+z)."""
    n = s["id"]; w, h, d = s["size"]; tiers = max(2, min(4, int(s.get("floors", 3)))); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); yy = 0.0
    for t in range(tiers):
        f = 1 - 0.18 * t; th = h * (0.45 if t == 0 else 0.55 / (tiers - 1)); tw, td = w * f, d * f
        ctx.add(f"{n}_Tier_{t + 1}", "box", [0, yy, 0], [tw, th, td], "wall", g, vkey=n)
        for k, (px, pz, fy, fw) in enumerate(((0, td / 2, 0, tw), (tw / 2, 0, 90, td), (0, -td / 2, 180, tw), (-tw / 2, 0, 270, td))):
            nx_, nz_ = (px and math.copysign(0.03, px)), (pz and math.copysign(0.03, pz)); bands = max(1, int(th // 4.5))
            for b in range(bands):
                ctx.add(f"{n}_T{t + 1}_Win_{k + 1}{b + 1:02d}", "panel", [px + nx_, yy + 1.6 + b * 4.5, pz + nz_], [fw * 0.84, 1.1, 0], "glow" if s.get("lit", True) else "window", g, [0, fy, 0])
        ctx.add(f"{n}_T{t + 1}_Ledge", "box", [0, yy + th, 0], [tw + 0.6, 0.4, td + 0.6], "trim", g); yy += th + 0.4
    ctx.add(n + "_Crown", "cylinder", [0, yy, 0], [w * 0.35, 1.2, w * 0.35], "accent", g, sections=12)
    ctx.add(n + "_Antenna", "cylinder", [0, yy + 1.2, 0], [0.3, h * 0.18, 0.3], "frame", g, sections=6)
    ctx.add(n + "_Canopy", "box", [0, 3.6, d / 2 + 1.5], [min(8, w * 0.6), 0.4, 3.0], "trim", g)
    ctx.add(n + "_Door", "panel", [0, 0, d / 2 + 0.03], [min(4, w * 0.3), 3.2, 0], "glow", g)
    ctx.platform_blocks = getattr(ctx, "platform_blocks", []) + [(x, z, max(w, d) / 2 + 0.6)]


@structure("office_block", pad=True, needs_size=True)
def office_block(ctx, s, x, y, z, yaw):
    """Mid-rise block: body, window grid per floor on all faces, roof units, ground-floor entrance + canopy."""
    n = s["id"]; w, h, d = s["size"]; fl = max(1, int(s.get("floors", h // 3.5))); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Body", "box", [0, 0, 0], [w, h, d], "wall", g, vkey=n)
    ctx.add(n + "_Roof", "box", [0, h, 0], [w + 0.3, 0.5, d + 0.3], "trim", g)
    for k, (px, pz, fy, fw) in enumerate(((0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d))):
        nx_, nz_ = (px and math.copysign(0.03, px)), (pz and math.copysign(0.03, pz))
        for f in range(1, fl):
            ctx.add(f"{n}_Win_{k + 1}{f:02d}", "panel", [px + nx_, f * h / fl + 0.8, pz + nz_], [fw * 0.8, 1.4, 0], "window", g, [0, fy, 0])
    ctx.add(n + "_Door", "panel", [0, 0, d / 2 + 0.03], [min(3.5, w * 0.3), 3.0, 0], "structure_b", g)
    ctx.add(n + "_Canopy", "box", [0, 3.3, d / 2 + 1.0], [min(6, w * 0.45), 0.3, 2.0], "trim", g)
    if ctx.detail >= 1: ctx.add(n + "_RoofUnit", "machinery", [w * 0.2, h + 0.5, 0], [min(4, w * 0.35), 2.0, min(3, d * 0.35)], "machine", g, seed=A._h(n) % 97)


@structure("factory", pad=True, needs_size=True)
def factory(ctx, s, x, y, z, yaw):
    """Factory hall: sawtooth roof, tall chimney(s), side tanks, loading door + pipe bridge to a side unit."""
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Hall", "box", [0, 0, 0], [w, h, d], "wall", g, vkey=n)
    teeth = max(2, int(w // 6)); tw = w / teeth
    for i in range(teeth):
        ctx.add(f"{n}_Roof_{i + 1:02d}", "wedge", [-w / 2 + tw * (i + 0.5), h, 0], [tw, 2.2, d], "structure_b", g, [0, -90, 0])
    for i in range(int(s.get("count", 1))):
        ctx.add(f"{n}_Chimney_{i + 1}", "cylinder", [w / 2 - 2.5 - 4 * i, h - 0.5, -d / 2 + 2.5], [2.2, h * 1.4, 2.2], "pipe", g, sections=10)
    ctx.add(n + "_Door", "panel", [0, 0, d / 2 + 0.03], [min(6, w * 0.4), min(5, h * 0.6), 0], "structure_b", g)
    ctx.add(n + "_Windows", "panel", [0, h * 0.7, d / 2 + 0.03], [w * 0.85, 1.2, 0], "glow" if s.get("lit", True) else "window", g)
    ctx.add(n + "_Tank", "tank", [-w / 2 - 2.2, 0, d / 4], [3.2, h * 0.8, 3.2], "pipe", g)
    ctx.add(n + "_PipeA", "cylinder", [-w / 2 - 0.9, h * 0.75, d / 4], [0.6, 2.0, 0.6], "pipe", g, [0, 0, 90], sections=8)
    ctx.platform_blocks = getattr(ctx, "platform_blocks", []) + [(x, z, max(w, d) / 2 + 3.0)]


@structure("container", pad=False)
def container(ctx, s, x, y, z, yaw):
    """Shipping containers as cover: 'count' boxes, stacked two high from the third one."""
    n = s["id"]; g = ctx.add(n, "group", [x, y - 0.1, z], rot=[0, yaw, 0]); rng = np.random.default_rng(A._h(n))
    for i in range(int(s.get("count", 2))):
        lay = [(0, 0, 0), (0, 0, 2.9), (0, 2.6, 0.2), (0, 0, -2.9)][i % 4]
        ctx.add(f"{n}_{i + 1:02d}", "box", [lay[0], lay[1], lay[2]], [6.0, 2.6, 2.44], "accent" if i % 2 else "structure_b", g, [0, float(rng.uniform(-4, 4)), 0])


@structure("barrier_line", pad=False)
def barrier_line(ctx, s, x, y, z, yaw):
    """Jersey barriers every 3.2 m from 'from' to 'to' (cover line, 1.1 m), each grounded."""
    ax, az, bx, bz, L, ux, uz = _line(s); k = max(1, int(L // 3.2)); n = s["id"]
    for i in range(k):
        t = (i + 0.5) * L / k; px, pz = ax + ux * t, az + uz * t; gy = A.ground_height(ctx, px, pz, y, 1.2)
        ctx.add(f"{n}_{i + 1:02d}", "wedge", [px, gy - 0.15, pz], [3.0, 1.25, 0.6], "structure", rot=[0, A.yaw_to(ux, uz) + 90, 0])


@structure("wreck", pad=False)
def wreck(ctx, s, x, y, z, yaw):
    """Burnt-out vehicle (cover): chassis, cabin, wheels."""
    n = s["id"]; g = ctx.add(n, "group", [x, y - 0.15, z], rot=[0, yaw, 5])
    ctx.add(n + "_Body", "box", [0, 0.4, 0], [2.0, 0.9, 4.4], "structure_b", g, bevel=0.15)
    ctx.add(n + "_Cabin", "box", [0, 1.3, -0.3], [1.8, 0.8, 2.2], "structure_b", g)
    for i, (wx, wz) in enumerate(((-1, -1.4), (1, -1.4), (-1, 1.4), (1, 1.4))):
        ctx.add(f"{n}_Wheel_{i + 1}", "cylinder", [wx * 0.95, 0.42, wz], [0.8, 0.35, 0.8], "frame", g, [0, 0, 90], sections=8)


@structure("billboard", pad=False)
def billboard(ctx, s, x, y, z, yaw):
    """Two posts + lit sign panel (front +z)."""
    w, h, d = s.get("size", [8, 9, 0.5]); n = s["id"]; g = ctx.add(n, "group", [x, y - 0.3, z], rot=[0, yaw, 0])
    for sd in (-1, 1): ctx.add(f"{n}_Post{'LR'[sd > 0]}", "box", [sd * w * 0.3, 0, 0], [0.5, h * 0.97, 0.5], "frame", g)
    ctx.add(n + "_Board", "box", [0, h * 0.6, 0], [w, h * 0.4, 0.3], "structure_b", g)
    ctx.add(n + "_Sign", "panel", [0, h * 0.62, 0.17], [w * 0.92, h * 0.36, 0], "accent", g)


@structure("antenna", pad=True)
def antenna(ctx, s, x, y, z, yaw):
    """Comms mast with dish + warning light."""
    w, h, d = s.get("size", [3, 18, 3]); n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Base", "box", [0, 0, 0], [w, 1.0, d], "structure", g)
    ctx.add(n + "_Mast", "cylinder", [0, 1.0, 0], [0.5, h, 0.5], "frame", g, sections=6)
    ctx.add(n + "_Dish", "cylinder", [0.8, h * 0.7, 0], [2.4, 0.4, 2.4], "structure_b", g, [0, 0, 70], sections=12)
    ctx.add(n + "_Light", "box", [0, h + 1.0, 0], [0.4, 0.4, 0.4], "glow", g)


@structure("fence", pad=False)
def fence(ctx, s, x, y, z, yaw):
    """Posts + two rails from 'from' to 'to', posts grounded on the terrain (thin: not cover)."""
    ax, az, bx, bz, L, ux, uz = _line(s); n = s["id"]; k = max(1, int(L // 3.0))
    for i in range(k + 1):
        t = i * L / k; px, pz = ax + ux * t, az + uz * t; gy = A.ground_height(ctx, px, pz, y)
        ctx.add(f"{n}_Post_{i + 1:02d}", "box", [px, gy - 0.4, pz], [0.15, 1.6, 0.15], "rail")
    for i in range(k):
        t = (i + 0.5) * L / k; px, pz = ax + ux * t, az + uz * t; g0 = A.ground_height(ctx, ax + ux * i * L / k, az + uz * i * L / k, y); g1 = A.ground_height(ctx, ax + ux * (i + 1) * L / k, az + uz * (i + 1) * L / k, y)
        pitch = -math.degrees(math.atan2(g1 - g0, L / k))
        for r, hh in enumerate((0.45, 1.0)):
            ctx.add(f"{n}_Rail_{i + 1:02d}{'ab'[r]}", "box", [px, (g0 + g1) / 2 + hh, pz], [0.06, 0.08, L / k], "rail", rot=[pitch, A.yaw_to(ux, uz), 0])


@structure("floor_marking", pad=False)
def floor_marking(ctx, s, x, y, z, yaw):
    """Concentric floor rings (helipad / target / arena centre): thin discs 2 cm apart in height, alternating
    'accent' / 'glow' / deck roles, outer radius size[0] / 2, 'count' rings."""
    R = s.get("size", [10, 0, 10])[0] / 2; k = int(s.get("count", 4)); n = s["id"]
    for i in range(k):
        r = R * (1 - i / k); mat = ("accent", "deck", "glow", "deck")[i % 4] if i < k - 1 else "glow"
        ctx.add(f"{n}_Ring_{i + 1}", "cylinder", [x, y - 0.02 + 0.02 * (i + 1), z], [2 * r, 0.04, 2 * r], mat, sections=24)
