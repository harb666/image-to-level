"""Stage 9 connector modules: bridge, walkway (elevated catwalk), tunnel. All take 'from' / 'to' [x, z] world points.

Rules (same as Stage 8): decks are connectors (anchors at both ends, checked against the walkable surface they land
on), every elevated span is supported (piers / columns to the real ground under them, abutments into the banks),
nothing floats, decks sit 10 cm above the road they continue (a step, never a gap)."""
import math
import numpy as np
import architecture as A
from modules import structure


def _span(s):
    (ax, az), (bx, bz) = s["from"], s["to"]; return math.hypot(bx - ax, bz - az)


def _ground(ctx, x, z, y):
    return A.ground_height(ctx, x, z, y) if getattr(ctx, "TR", None) is not None else y - 6


@structure("bridge", pad=False)
def bridge(ctx, s, x, y, z, yaw):
    """Bridge deck from 'from' to 'to' (top at 'y'), rails/parapets, piers down to the ground or river bed, abutments."""
    n = s["id"]; L = _span(s); w = s.get("width", 5.0); st = s.get("style") or ("stone" if ctx.theme["wall_style"] == "stone" else "steel")
    ya, yb = s.get("y_from", y), s.get("y_to", y); y = (ya + yb) / 2; pitch = -math.degrees(math.atan2(yb - ya, L))  # follows the road grade
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); th = 0.5 if st == "stone" else 0.45
    sp = ctx.add(n + "_Span", "group", [0, 0, 0], parent=g, rot=[round(pitch, 3), 0, 0])  # deck, rails, girders tilt with the road grade
    deck = ctx.add(n + "_Deck", "box", [0, -th, 0], [w, th, L], "stone" if st == "stone" else "deck", sp, connector=True, axis="z")
    for sd, side in ((-1, "L"), (1, "R")):
        if st == "stone": ctx.add(f"{n}_Parapet_{side}", "box", [sd * (w / 2 - 0.2), 0, 0], [0.4, 0.95, L - 0.4], "stone", sp)
        elif s.get("rails", True): ctx.add(f"{n}_Rail_{side}", "railing", [sd * (w / 2 - 0.05), 0, 0], [L - 0.6, 1.05, 0.06], "rail", sp, [0, 90, 0])
        if st != "stone":
            gd = ctx.add(f"{n}_Girder_{side}", "ibeam", [sd * (w / 2 - 0.45), -th - 0.7, 0], [L - 0.2, 0.7, 0.35], "frame", sp, [0, 90, 0]); ctx.rel("supported_by", deck, gd)
    bot = -th - (0.7 if st != "stone" else 0.0); dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    dy = lambda zz: (yb - ya) * zz / L  # deck height offset at local z
    k = max(1, int(L // s.get("pier_spacing", 9.0)))
    for i in range(1, k):  # piers at interior points, down into the ground / river bed
        zz = -L / 2 + L * i / k; gy = _ground(ctx, x + dx * zz, z + dz * zz, y) - 0.6
        hgt = y + dy(zz) + bot - gy
        if hgt < 0.3: continue
        if st == "stone": p = ctx.add(f"{n}_Pier_{i:02d}", "box", [0, gy - y, zz], [w * 0.7, hgt, 1.4], "stone", g, connector=False); ctx.rel("supported_by", deck, p)
        else:
            p = ctx.add(f"{n}_Pier_{i:02d}", "box", [0, dy(zz) + bot - 0.79, zz], [w - 0.4, 0.8, 1.0], "structure_b", g, connector=False) if hgt > 3 else None  # cross-head under the girders
            for sd, side in ((-1, "L"), (1, "R")):
                c = ctx.add(f"{n}_Column_{i:02d}{side}", "cylinder", [sd * (w / 2 - 0.45), gy - y, zz], [0.6, hgt - (0.79 if p else 0.0), 0.6], "frame", g, sections=8)
                ctx.rel("supported_by", p or f"{n}_Girder_{side}", c)
            if p: ctx.rel("supported_by", f"{n}_Girder_L", p)
    for e, zz in (("A", -L / 2 + 0.9), ("B", L / 2 - 0.9)):  # abutments into the banks
        gy = _ground(ctx, x + dx * zz, z + dz * zz, y) - 1.0; hgt = y + dy(zz) + bot - gy
        if hgt > 0.3:
            a = ctx.add(f"{n}_Abutment_{e}", "box", [0, gy - y, zz], [w + 0.4, hgt, 1.8], "structure_b" if st != "stone" else "stone", g, connector=False)
            ctx.rel("supported_by", f"{n}_Girder_L" if st != "stone" else deck, a)
    ctx.landings += [(x - dx * L / 2, z - dz * L / 2, w / 2), (x + dx * L / 2, z + dz * L / 2, w / 2)]
    ctx.walkable.append(dict(name=n, min=[x - 1, z - 1], max=[x + 1, z + 1], y=y))


@structure("walkway", pad=False)
def walkway(ctx, s, x, y, z, yaw):
    """Elevated grated catwalk at height 'y' between two points (rails both sides, slim columns to the ground)."""
    s = dict(s, style="steel", rails=True, width=s.get("width", 3.0), pier_spacing=s.get("pier_spacing", 7.0)); bridge(ctx, s, x, y, z, yaw)


def _tunnel_terrain(s, TR0):
    (ax, az), (bx, bz) = s["from"], s["to"]; y = s.get("y", min(TR0.height_at(ax, az), TR0.height_at(bx, bz)))
    return [dict(id=s["id"] + "_Trench", type="trench", points=[s["from"], s["to"]], width=s.get("width", 8.0) + 1.2, y=y - 0.05, transition=6.0)]


@structure("tunnel", pad=False, terrain=_tunnel_terrain)
def tunnel(ctx, s, x, y, z, yaw):
    """Tunnel from 'from' to 'to' at floor height 'y': the terrain is trenched, a concrete tube (floor, walls, roof) runs
    through it, portal frames at both ends, and a berm restores the original hill over the roof (walkable, closed)."""
    n = s["id"]; L = _span(s); w = s.get("width", 8.0); h = s.get("height", 5.0); t = 0.6
    if s.get("y") is None:
        TRp = getattr(ctx, "TR_pre", None) or ctx.TR; (ax, az), (bx, bz) = s["from"], s["to"]; y = min(TRp.height_at(ax, az), TRp.height_at(bx, bz))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Floor", "box", [0, -0.4, 0], [w + 2 * t - 0.02, 0.4, L - 0.02], "ground", g, connector=True, axis="z")
    for sd, side in ((-1, "L"), (1, "R")):
        ctx.add(f"{n}_Wall_{side}", "box", [sd * (w / 2 + t / 2), -0.39, 0], [t, h + 0.39, L], "structure", g)
        ctx.add(f"{n}_Light_{side}", "panel", [sd * (w / 2 - 0.01), h * 0.75, 0], [L * 0.9, 0.18, 0], "glow", g, [0, -90 * sd, 0])
    ctx.add(n + "_Roof", "box", [0, h, 0], [w + 2 * t, t, L], "structure", g)
    for e, zz in (("A", -L / 2), ("B", L / 2)):
        ctx.add(f"{n}_Portal_{e}", "box", [0, h - 0.2, zz], [w + 2 * t + 1.2, 1.4, 0.8], "trim", g)
        for sd, side in ((-1, "L"), (1, "R")):
            ctx.add(f"{n}_Portal_{e}{side}", "box", [sd * (w / 2 + t + 0.3), -0.43, zz], [1.2, h + 0.22, 0.8], "trim", g)
    TRp = getattr(ctx, "TR_pre", None)
    if TRp is not None:  # berm: original terrain heights over the roof, across the whole trench width
        hw = w / 2 + t + 0.6 + 6.0; nl, nw = max(3, int(L / 2) + 1), 9; zs = np.linspace(-L / 2 + 0.4, L / 2 - 0.4, nl); xs = np.linspace(-hw, hw, nw)
        a = math.radians(yaw); top = np.zeros((nl, nw))
        for i, zz in enumerate(zs):
            wx = x + np.cos(a) * xs + np.sin(a) * zz; wz = z - np.sin(a) * xs + np.cos(a) * zz
            top[i] = np.maximum(TRp.height(wx, wz) - y + 0.05, h + t + 0.3)
        ctx.add(n + "_Berm", "berm", [0, h + t - 0.05, 0], [2 * hw, float(top.max() - h - t), L - 0.8], "rock", g,
                heights=np.round(top - (h + t - 0.05), 3).tolist(), xs=np.round(xs, 3).tolist(), zs=np.round(zs, 3).tolist(), collision_mesh=True)
    ctx.walkable.append(dict(name=n, min=[x - 1, z - 1], max=[x + 1, z + 1], y=y))
