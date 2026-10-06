"""Depth points (.npz from image_to_points.py, or Lyra .ply) -> editable scene description (level.json).

Depth is only spatial guidance: analyse() (points_to_level.py) gives 2.5D grids; here they become a small set of
clean named primitives (terrain, buildings with roofs, walls, platforms, paths, props) with material types.
build_level.py turns level.json into level.glb. Edit level.json, re-run build_level.py: no re-analysis needed.
"""
import argparse, colorsys, json, os, numpy as np
from scipy import ndimage
from points_to_level import analyse

K3 = np.ones((3, 3), bool)


def rects(mask, min_cells, max_n=40, cover=0.9):
    """Greedy cover of a mask by largest axis-aligned rectangles -> [(j0, i0, j1, i1)]."""
    m = mask.copy(); total = m.sum(); out = []
    while m.sum() > (1 - cover) * total and len(out) < max_n:
        h = np.zeros(m.shape[1], int); best = (0, None)
        for j in range(m.shape[0]):  # largest rectangle in histogram, row by row
            h = np.where(m[j], h + 1, 0); st = []
            for i in range(len(h) + 1):
                cur = h[i] if i < len(h) else 0
                while st and h[st[-1]] >= cur:
                    hh = h[st.pop()]; i0 = st[-1] + 1 if st else 0
                    if hh * (i - i0) > best[0]: best = (hh * (i - i0), (j - hh + 1, i0, j + 1, i))
                st.append(i)
        if best[0] < min_cells: break
        j0, i0, j1, i1 = best[1]; m[j0:j1, i0:i1] = False; out.append(best[1])
    return out


def classify(rgb, floor):
    """Mean colour -> material type (rough, by hue/saturation/value)."""
    h, s, v = colorsys.rgb_to_hsv(*np.clip(rgb, 0, 1)); h *= 360
    if s > 0.2 and 70 < h < 170: return "grass"
    if s > 0.35 and (h < 25 or h > 330): return "painted_wood"
    if s > 0.2 and 25 <= h <= 55: return ("sand" if v > 0.6 else "soil") if floor else ("wood" if v < 0.55 else "plaster")
    if s < 0.2 and 180 < h < 260 and not floor: return "metal" if v < 0.7 else "plaster"
    if floor: return "cobblestone" if v < 0.75 else "concrete"
    return "plaster" if v > 0.62 else "stone_brick"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("points"); ap.add_argument("out_json")
    ap.add_argument("--cell", type=float, default=0.5)
    a = ap.parse_args()
    g = analyse(a.points, a.cell, align=True)
    walk, solid, over, top, bot, fcol, scol, fh = (g[k] for k in "walk solid over top bot fcol scol fh".split())
    cell, ox, oz = g["cell"], g["ox"], g["oz"]
    W = lambda j, i: (float(ox + i * cell), float(oz + j * cell))  # grid -> world xz

    mats, objs, count = {}, [], {}
    def mat(kind, rgb):
        if kind not in mats: mats[kind] = {"type": kind, "color": [], "tile_m": 2.0}
        mats[kind]["color"].append([float(x) for x in rgb]); return kind
    def name(kind):
        count[kind] = count.get(kind, 0) + 1; return f"{kind}_{count[kind]:02d}"
    def add(**o):
        o.setdefault("rotation", [0, 0, 0]); objs.append(o); return o

    # --- terrain: coarse heightfield; flat play area, hills rising outside it as a natural boundary
    play = walk | solid
    fl = g["floor"]
    floor_rgb = np.median(fcol[fl], 0) if fl.any() else np.array([.5, .5, .5])
    tmat = mat(classify(floor_rgb, True), floor_rgb)
    tc = 2.0; margin = 12.0
    bbj, bbi = np.argwhere(play).min(0), np.argwhere(play).max(0) + 1
    x0, z0 = W(bbj[0], bbj[1]); x1, z1 = W(bbi[0], bbi[1])
    x0, z0, x1, z1 = x0 - margin, z0 - margin, x1 + margin, z1 + margin
    nxt, nzt = int(np.ceil((x1 - x0) / tc)) + 1, int(np.ceil((z1 - z0) / tc)) + 1
    rng = np.random.default_rng(1); heights = []
    gx0, gz0, gx1, gz1 = x0 + margin, z0 + margin, x1 - margin, z1 - margin  # play-area rectangle
    for r in range(nzt):
        row = []
        for c in range(nxt):
            x, z = x0 + c * tc, z0 + r * tc
            d = np.hypot(max(gx0 - x, 0, x - gx1), max(gz0 - z, 0, z - gz1))  # distance outside the play rectangle
            row.append(round(-0.1 if d < 1 else min(0.8 * d, 9.0) + rng.uniform(0, 1.5), 2))
        heights.append(row)
    add(name="Terrain", type="terrain", material=mat("rock", [0.42, 0.4, 0.36]), position=[x0, 0, z0], cell=tc, heights=heights)

    # facades only show their front: extrude solid cells up to 6 m away from the walkable area into building mass
    away = ndimage.distance_transform_edt(~walk) * cell
    grow = solid.copy()
    for _ in range(int(6 / cell)):
        nb = ndimage.binary_dilation(grow, K3) & ~walk & ~grow
        nb &= ndimage.grey_dilation(np.where(grow, away, -1), footprint=K3) < away  # only step further from the floor
        if not nb.any(): break
        grow |= nb
    idx = ndimage.distance_transform_edt(~solid, return_distances=False, return_indices=True)
    top = np.where(grow & ~solid, top[idx[0], idx[1]], top); scol = np.where((grow & ~solid)[..., None], scol[idx[0], idx[1]], scol)
    solid = grow; play = walk | solid
    # --- ground: one flat editable slab over the play area (change its material/size freely)
    (gx0, gz0), (gx1, gz1) = W(bbj[0], bbj[1]), W(bbi[0], bbi[1])
    add(name="Ground", type="box", material=tmat, position=[(gx0 + gx1) / 2, -0.2, (gz0 + gz1) / 2], size=[gx1 - gx0 + 2, 0.2, gz1 - gz0 + 2])
    # --- structures: rectangle cover of solid cells -> buildings / walls / platforms / props
    lab, n = ndimage.label(solid, K3)
    for comp in range(1, n + 1):
        cm = lab == comp
        for (j0, i0, j1, i1) in rects(cm, max(2, int(1 / cell ** 2)), max_n=6):
            w, d = (i1 - i0) * cell, (j1 - j0) * cell
            h = float(np.median(top[j0:j1, i0:i1][cm[j0:j1, i0:i1]]))
            rgb = np.median(scol[j0:j1, i0:i1][cm[j0:j1, i0:i1]], 0)
            (xa, za), (xb, zb) = W(j0, i0), W(j1, i1)
            c = [round((xa + xb) / 2, 2), 0, round((za + zb) / 2, 2)]
            thin = min(w, d) <= 1.0
            if h > 3.0 and not thin:
                bn = name("Building"); kind = classify(rgb, False)
                add(name=bn, type="group", position=c)
                add(name=bn + "_Body", parent=bn, type="box", material=mat(kind, rgb), position=[0, 0, 0], size=[w, round(h, 1), d])
                add(name=bn + "_Roof", parent=bn, type="roof", material=mat("roof_tiles", [0.35, 0.22, 0.18]),
                    position=[0, round(h, 1), 0], size=[w + 0.6, round(min(w, d) * 0.4, 1), d + 0.6])
            elif thin or h <= 1.5 and min(w, d) < 2:
                add(name=name("Wall"), type="box", material=mat(classify(rgb, False), rgb), position=c, size=[w, round(max(h, 1.0), 1), d])
            elif h <= 1.6:
                add(name=name("Platform"), type="box", material=mat(classify(rgb, True), rgb), position=c, size=[w, round(h, 1), d])
            elif max(w, d) <= 3.5:
                add(name=name("Prop"), type="cylinder", material=mat(classify(rgb, False), rgb), position=c, size=[w, round(h, 1), d])
            else:
                add(name=name("Block"), type="box", material=mat(classify(rgb, False), rgb), position=c, size=[w, round(h, 1), d])
    # overhangs (roofs/canopies/bridges above walkable floor)
    for (j0, i0, j1, i1) in rects(over, max(4, int(2 / cell ** 2)), max_n=8):
        sub = over[j0:j1, i0:i1]; b = float(np.median(bot[j0:j1, i0:i1][sub])); rgb = np.median(scol[j0:j1, i0:i1][sub], 0)
        (xa, za), (xb, zb) = W(j0, i0), W(j1, i1)
        if min(xb - xa, zb - za) < 1.5: continue
        add(name=name("Overhang"), type="box", material=mat(classify(rgb, False), rgb),
            position=[round((xa + xb) / 2, 2), round(b, 1), round((za + zb) / 2, 2)], size=[xb - xa, 0.4, zb - za])
    # paths: floor areas whose material differs from the terrain material
    pm = walk & fl & ~solid
    kinds = np.array([[classify(fcol[j, i], True) if pm[j, i] else "" for i in range(pm.shape[1])] for j in range(pm.shape[0])])
    for kind in set(kinds[pm]) - {tmat}:
        m2 = ndimage.binary_opening(kinds == kind, K3, iterations=1)
        for (j0, i0, j1, i1) in rects(m2, int(8 / cell ** 2), max_n=6):
            if min(j1 - j0, i1 - i0) * cell < 1.5: continue
            rgb = np.median(fcol[j0:j1, i0:i1][m2[j0:j1, i0:i1]], 0)
            (xa, za), (xb, zb) = W(j0, i0), W(j1, i1)
            add(name=name("Path"), type="box", material=mat(kind, rgb), position=[round((xa + xb) / 2, 2), 0, round((za + zb) / 2, 2)], size=[xb - xa, 0.08, zb - za])
    # invisible boundary walls round the play area (terrain hills are the visible boundary)
    (bx0, bz0), (bx1, bz1) = W(bbj[0], bbj[1]), W(bbi[0], bbi[1])
    for nm, pos, size in [("N", [(bx0 + bx1) / 2, 0, bz0 - 0.5], [bx1 - bx0 + 2, 4, 1]), ("S", [(bx0 + bx1) / 2, 0, bz1 + 0.5], [bx1 - bx0 + 2, 4, 1]),
                          ("W", [bx0 - 0.5, 0, (bz0 + bz1) / 2], [1, 4, bz1 - bz0 + 2]), ("E", [bx1 + 0.5, 0, (bz0 + bz1) / 2], [1, 4, bz1 - bz0 + 2])]:
        add(name="Boundary_" + nm, type="boundary", position=[round(v, 2) for v in pos], size=[round(v, 2) for v in size])

    for m in mats.values(): m["color"] = [round(float(v), 3) for v in np.median(m["color"], 0)]
    for o in objs:
        for k in ("position", "size"):
            if k in o: o[k] = [round(float(v), 2) for v in o[k]]
    walkable = [dict(min=list(W(j0, i0)), max=list(W(j1, i1)), y=0.0) for (j0, i0, j1, i1) in rects(walk & ~solid, int(4 / cell ** 2), max_n=12)]
    fd = g["fd"]
    scene = dict(version=1, units="metres, y-up; position = centre of object's base, in parent space; rotation = degrees XYZ",
                 source=os.path.basename(a.points), sky_color=[round(float(v), 3) for v in g["sky"]],
                 spawn=dict(position=g["spawn"], yaw_deg=round(float(np.degrees(np.arctan2(-fd[0], -fd[1]))), 1)),
                 bounds=dict(min=[round(bx0, 2), 0, round(bz0, 2)], max=[round(bx1, 2), round(float(top.max()), 2), round(bz1, 2)]),
                 walkable=walkable, materials=mats, objects=objs)
    json.dump(scene, open(a.out_json, "w"), indent=1)
    print(f"{len(objs)} objects, {len(mats)} materials -> {a.out_json}")


if __name__ == "__main__":
    main()
