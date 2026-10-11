"""Stage 9 natural modules: rock_arch, cave, overhang, cliff_face, rock_spire, ruins, crystal_cluster, boulder_field.
Custom closed meshes (shapes.py) instead of heightfield tricks for what a heightfield cannot do (vertical walls, holes,
overhangs). All use the 'rock' role (theme palette) unless "material" is given; collision is the real mesh where a
convex hull would fill an opening (arch, cave, overhang)."""
import math
import numpy as np
import architecture as A
from modules import structure


def _seed(s):
    return A._h(s["id"]) % 9973


@structure("rock_arch", pad=False, needs_size=True, natural=True)
def rock_arch(ctx, s, x, y, z, yaw):
    """Natural stone arch spanning size[0] along local x, top at size[1] (walk under it)."""
    w, h, d = s["size"]; ctx.add(s["id"], "rock_arch", [x, y - 0.3, z], [w, h, d], s.get("material", "rock"), rot=[0, yaw, 0], seed=_seed(s), collision_mesh=True)


def _cave_terrain(s, TR0):
    x, z = s["position"][0], s["position"][-1]; w, h, d = s["size"]; y = TR0.height_at(x, z) if len(s["position"]) == 2 else s["position"][1]
    return [dict(id=s["id"] + "_Floor", type="pad", center=[x, z], size=[w * 0.9, d * 0.9], yaw=s.get("yaw", 0), y=round(y, 2), margin=4.0, surface="pad")]


@structure("cave", pad=False, needs_size=True, natural=True, terrain=_cave_terrain)
def cave(ctx, s, x, y, z, yaw):
    """Rock outcrop with a walk-in cave on its front (+z after yaw); the ground under it is flattened to the cave floor."""
    w, h, d = s["size"]; y0 = ctx.TR.height_at(x, z) if getattr(ctx, "TR", None) is not None else y
    ctx.add(s["id"], "cave", [x, y0, z], [w, h, d], s.get("material", "rock"), rot=[0, yaw, 0], seed=_seed(s), opening=s.get("opening", 0.5), collision_mesh=True)
    ctx.walkable.append(dict(name=s["id"], min=[x - 1, z - 1], max=[x + 1, z + 1], y=y0))


@structure("overhang", pad=False, needs_size=True, natural=True)
def overhang(ctx, s, x, y, z, yaw):
    """Rock shelf whose lip juts over a recess (cover from above); front = +z after yaw."""
    w, h, d = s["size"]; ctx.add(s["id"], "overhang", [x, y - 0.2, z], [w, h, d], s.get("material", "rock"), rot=[0, yaw, 0], seed=_seed(s), collision_mesh=True)


@structure("cliff_face", pad=False, natural=True)
def cliff_face(ctx, s, x, y, z, yaw):
    """Vertical rock wall along 'from' -> 'to' (segments of ~10 m), face towards the lower side, base below the lower ground."""
    (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); n = max(1, int(round(L / s.get("segment", 10.0))))
    ux, uz = (bx - ax) / L, (bz - az) / L; nx, nz = uz, -ux; TR = getattr(ctx, "TR", None); d = s.get("depth", 4.0)
    for i in range(n):
        cx, cz = ax + ux * L * (i + 0.5) / n, az + uz * L * (i + 0.5) / n
        if TR is not None:
            hp, hm = TR.height_at(cx + nx * 6, cz + nz * 6), TR.height_at(cx - nx * 6, cz - nz * 6); sg = 1 if hp < hm else -1
            lo, hi = min(hp, hm), max(hp, hm)
        else: sg, lo, hi = 1, y, y + s.get("height", 8)
        fx, fz = nx * sg, nz * sg  # face direction (towards the low side)
        hh = (s.get("height") or (hi - lo)) + 1.5
        ctx.add(f"{s['id']}_{i + 1:02d}", "cliff", [cx - fx * 0.6, lo - 1.0, cz - fz * 0.6], [L / n + 1.2, hh + 1.0, d], s.get("material", "rock"),
                rot=[0, A.yaw_to(fx, fz), 0], seed=_seed(s) + i)


@structure("rock_spire", pad=False, natural=True)
def rock_spire(ctx, s, x, y, z, yaw):
    """Hoodoo / sea stack: stacked weathered rock blocks narrowing upwards (+ a cap rock)."""
    w, h, d = s.get("size", [5, 14, 5]); n = s["id"]; g = ctx.add(n, "group", [x, y - 0.6, z], rot=[0, yaw, 0]); k = 4; yy = 0.0
    for i in range(k):
        f = 1 - 0.18 * i; hh = h / k * (1.15 if i == 0 else 1.0)
        ctx.add(f"{n}_{i + 1:02d}", "rock", [0, yy, 0], [w * f, hh, d * f], s.get("material", "rock"), g, seed=_seed(s) + i, convex=True); yy += hh * 0.86
    ctx.add(n + "_Cap", "rock", [0, yy, 0], [w * 0.9, h * 0.12, d * 0.9], s.get("material", "rock"), g, seed=_seed(s) + 9, convex=True)


@structure("ruins", pad=True, needs_size=True)
def ruins(ctx, s, x, y, z, yaw):
    """Broken masonry: jagged wall stubs round the footprint (gaps for routes), fallen blocks, broken columns."""
    w, h, d = s["size"]; n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); rng = np.random.default_rng(_seed(s)); mat = s.get("material", "stone")
    sides = [((-w / 2, -d / 2), (w / 2, -d / 2)), ((w / 2, -d / 2), (w / 2, d / 2)), ((w / 2, d / 2), (-w / 2, d / 2)), ((-w / 2, d / 2), (-w / 2, -d / 2))]
    k = 0
    for i, ((x0, z0), (x1, z1)) in enumerate(sides):
        L = math.hypot(x1 - x0, z1 - z0); ux, uz = (x1 - x0) / L, (z1 - z0) / L; t = 0.0
        while t < L - 1.5:
            seg = rng.uniform(2.5, 5.0); gap = rng.uniform(1.6, 3.5) if rng.random() < 0.45 else 0.0; seg = min(seg, L - t)
            if seg > 1.2:
                cx, cz = x0 + ux * (t + seg / 2), z0 + uz * (t + seg / 2); k += 1
                ctx.add(f"{n}_Wall_{k:02d}", "cliff", [cx, -0.3, cz], [seg, h * rng.uniform(0.35, 1.0), 0.9], mat, g, [0, math.degrees(math.atan2(ux, uz)) - 90, 0], seed=_seed(s) + k, step=1.2)
            t += seg + gap
    for j in range(int(s.get("count", 4))):
        bx, bz = rng.uniform(-w / 2.5, w / 2.5), rng.uniform(-d / 2.5, d / 2.5)
        if rng.random() < 0.5: ctx.add(f"{n}_Column_{j + 1:02d}", "cylinder", [bx, -0.2, bz], [0.9, rng.uniform(1.0, h * 0.8), 0.9], mat, g, sections=8)
        else: ctx.add(f"{n}_Block_{j + 1:02d}", "box", [bx, -0.3, bz], [rng.uniform(1.0, 1.8), rng.uniform(0.8, 1.3), rng.uniform(0.9, 1.4)], mat, g, [0, rng.uniform(0, 90), 0])


@structure("crystal_cluster", pad=False, natural=True)
def crystal_cluster(ctx, s, x, y, z, yaw):
    """Large glowing crystal formation (alien / fantasy); seeded hex prisms."""
    w, h, d = s.get("size", [4, 5, 4]); ctx.add(s["id"], "crystals", [x, y - 0.3, z], [w, h, d], s.get("material", "glow"), rot=[0, yaw, 0], seed=_seed(s))


@structure("boulder_field", pad=False, natural=True)
def boulder_field(ctx, s, x, y, z, yaw):
    """Cluster of large boulders (cover) over a radius, each grounded on the terrain."""
    rng = np.random.default_rng(_seed(s)); R = s.get("radius", 8.0); n = s["id"]
    for i in range(int(s.get("count", 6))):
        a, r = rng.uniform(0, 2 * np.pi), R * math.sqrt(rng.uniform(0.05, 1)); bx, bz = x + r * math.cos(a), z + r * math.sin(a); sz = rng.uniform(1.4, 3.2)
        gy = A.ground_height(ctx, bx, bz, y, sz * 0.3)
        ctx.add(f"{n}_{i + 1:02d}", "rock", [bx, gy - sz * 0.25, bz], [sz * rng.uniform(1, 1.4), sz, sz * rng.uniform(0.9, 1.3)], s.get("material", "rock"), rot=[0, rng.uniform(0, 360), 0], seed=_seed(s) + i)


class _Rendered:
    """Terrain seen as RENDERED (mesh_height: LOD0 triangles) - waterfalls must hug the visible rock, not the sharper
    analytic surface (mesa rims sit up to a cell further out there, which left the top of a fall in mid-air)."""
    def __init__(self, TR):
        self.TR = TR; mh = getattr(TR, "mesh_height", None); n = 2  # LOD 0..2 (terrain.lod_settings: levels = 3)
        # the outermost of every terrain LOD that can be on screen: the coarse chunks' cliffs may bulge past LOD0
        self.h = (lambda X, Z: np.max([mh(X, Z, k) for k in range(n + 1)], axis=0)) if mh else TR.height
        self.h0 = mh or TR.height  # LOD0 alone: the edge you see up close (lips, the plateau the flow lies on)
    def height0(self, X, Z): return self.h0(np.asarray(X, float), np.asarray(Z, float))
    def height(self, X, Z): return self.h(np.asarray(X, float), np.asarray(Z, float))
    def height_at(self, x, z): return float(self.height(np.array([x]), np.array([z]))[0])
    def water_y(self, X, Z): return self.TR.water_y(X, Z)


@structure("waterfall", pad=False, natural=True)
def waterfall(ctx, s, x, y, z, yaw):
    """Waterfall over a cliff edge: a falling water sheet from the lip at 'position' (top = highest ground within 3 m,
    or "y") down to the water surface / ground below, facing 'yaw' (or away from the cliff). "width" (m)."""
    w = s.get("width", s.get("size", [6, 1, 1])[0]); TR = getattr(ctx, "TR", None); n = s["id"]
    if TR is not None:
        TR = _Rendered(TR)
        if "yaw" not in s:  # face down the steepest descent
            e = 6.0; hx = TR.height_at(x + e, z) - TR.height_at(x - e, z); hz = TR.height_at(x, z + e) - TR.height_at(x, z - e); yaw = A.yaw_to(-hx, -hz)
        dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
        t = np.arange(-30, 30.5, 1.0); H = TR.height0(x + dx * t, z + dz * t); drop = H[:-4] - H[4:]  # find the lip: biggest 4 m drop along the facing line
        k = int(np.argmax(drop))
        if drop[k] > 3: x, z = x + dx * t[k], z + dz * t[k]
        g = np.linspace(-1.5, 1.5, 4); X, Z = np.meshgrid(x + g, z + g); top = float(TR.height0(X.ravel(), Z.ravel()).max())
        fx, fz = x + dx * 6, z + dz * 6
        wy = TR.water_y(np.array([fx]), np.array([fz]))[0]; bottom = max(float(TR.height_at(fx, fz)), float(wy) if np.isfinite(wy) else -1e9)
    else: top, bottom = s.get("y", y + 10), y
    top = s.get("y", top) - 0.15; drop = top - bottom + 0.8
    if drop < 2: ctx.notes.append(f"{n}: no drop at this position - waterfall skipped"); return
    G = _fall_grid(ctx, s, x, z, yaw, w, top, bottom) if TR is not None and s.get("organic", True) and "y" not in s else None
    if G is not None:  # Stage 13: curved sheet hugging the real lip, kept clear of the cliff below (nothing pokes through)
        o0 = 0.5 * (G[0, (G.shape[1] - 1) // 2] + G[0, G.shape[1] // 2]); Gl = G - o0  # origin: top of the middle column
        a = math.radians(yaw); ca_, sa_ = math.cos(a), math.sin(a)
        Gl = np.stack([Gl[..., 0] * ca_ - Gl[..., 2] * sa_, Gl[..., 1], Gl[..., 0] * sa_ + Gl[..., 2] * ca_], -1)  # world -> local (inverse Ry)
        w = min(w, float(np.linalg.norm(G[0, -1] - G[0, 0])) / 0.86)  # after any narrowing
        st = ctx.add(n, "stream", list(o0), [round(w, 2), round(float(o0[1] - G[-1, :, 1].min()), 2), 0.35], s.get("material", "water"), rot=[0, yaw, 0],
                     section="sheet", speed=s.get("speed", 1.6), pitch=-10, inset=0.6, grid=np.round(Gl, 3).tolist(), closed=True)  # slab: has thickness seen from the side
        ctx.pours.append(st); return
    st = ctx.add(n, "stream", [x, top, z], [round(w, 2), round(drop, 2), 0.35], s.get("material", "water"), rot=[0, yaw, 0],
                 section="sheet", speed=s.get("speed", 1.6), pitch=-10, inset=0.6)
    ctx.pours.append(st)


def _fall_grid(ctx, s, x, z, yaw, w, top, bottom, clear=0.3):
    """World-space centre surface (rows x cols x 3) of a terrain waterfall. Every column finds ITS OWN lip along the
    facing line (diagonal / ragged cliff edges), starts a few metres upstream lying on the ground (ragged, rounded top
    edge), bends over the lip and runs down the cliff: every ~2.5 m of drop each column sits `clear` m (plus half the
    slab) in front of the rendered rock at that height (sampled on the column and halfway to its neighbours) - it
    clings to the face, so there is no gap behind it to see through and no rock cuts through it. Width tapers in at the top and widens a little towards the bottom; edges wobble. If some column
    finds no edge near the lip height (small islands), the fall is narrowed until every column pours off real ground."""
    TR = _Rendered(ctx.TR); a = math.radians(yaw)
    F = np.array([math.sin(a), math.cos(a)]); S = np.array([math.cos(a), -math.sin(a)]); t = np.arange(-10, 40.01, 0.25)
    def prof(lat, h=None): P = np.array([x, z]) + S * lat + F * t[:, None]; return (h or TR.height0)(P[:, 0], P[:, 1])
    def lip(lat):  # this column's own edge: (t, y) or None when there is no edge near the fall's lip height
        Hc = prof(lat); i0 = np.searchsorted(t, -6); steep = np.flatnonzero((Hc[i0:-8] - Hc[i0 + 4:-4]) > 1.2)  # drop > 1.2 m over the next metre
        if not len(steep): return None
        il = i0 + int(steep[0]); return (t[il], Hc[il]) if top - 6 <= Hc[il] <= top + 3 else None
    w0 = w
    ncol = lambda w_: int(np.clip(round(w_ / 2.2), 2, 10)) + 1  # ~2 m apart: the sheet can follow the rock closely
    while w > 1.5 and any(lip(u * w * 0.86) is None for u in np.linspace(-0.5, 0.5, ncol(w))):
        w *= 0.85  # small islands: narrow the fall until every column pours off real ground (never from mid-air)
    if w < w0 - 0.01: ctx.notes.append(f"{s['id']}: waterfall narrowed {w0:.1f} -> {w:.1f} m to stay on the ground at its lip")
    rng = np.random.default_rng(_seed(s))
    C = ncol(w); R_up = 3; nf = int(np.clip(round((top - bottom) / 2.5), 6, 24))  # a row every ~2.5 m of drop
    us = np.linspace(-0.5, 0.5, C); spacing = w / (C - 1)
    def foot(lat):  # ground / water under the fall 6 m out from this column's lip
        L_ = lip(lat); tl_ = L_[0] if L_ is not None else 0.0; gx = np.array([x, z]) + S * lat + F * (tl_ + 6)
        wy = TR.water_y(np.array([gx[0]]), np.array([gx[1]]))[0]; return max(float(TR.height_at(*gx)), float(wy) if np.isfinite(wy) else -1e9, bottom - 2)
    ybot_all = min(foot(u * w * 0.86) for u in us) - 0.8  # one common bottom: every column runs down into rock / abyss (no stepped, mid-air ends)
    cols = []
    for j, u in enumerate(us):
        lat = u * w * 0.86; Hc = prof(lat); L_ = lip(lat)
        tl, yl = L_ if L_ is not None else (0.0, top)
        side = [lat + k * spacing / 2 for k in (-1, 1)] + ([lat * 1.25] if j in (0, C - 1) else [])  # between columns + beyond the edges
        Hn = np.max([prof(q, TR.height) for q in [lat] + side], axis=0)  # rock to clear: outermost of every LOD  # (the sheet widens below)
        def front(yq):  # furthest rock (t) at height >= yq, scanning out from the lip
            below = np.flatnonzero((t > tl) & (Hn < yq - 0.2)); return t[below[0]] - 0.25 if len(below) else -1e9  # none: at / under the ground the sheet ends
        ybot = ybot_all
        up = 2.0 + 1.6 * rng.random() - 1.4 * abs(u * 2) ** 2  # ragged, rounded top edge on the plateau
        pts = []
        gh = lambda tq: float(TR.height0(*(np.array([x, z]) + S * lat + F * tq)[:, None])[0])
        for k, f in enumerate(np.linspace(1, 0, R_up)):
            tk = tl - max(0.3, up) * f - 0.15
            while tk < tl - 0.3 and gh(tk) < yl - 0.6: tk += 0.25  # the plateau behind is narrow: start where there is ground
            pts.append([tk, gh(tk) + 0.3])
        pts[-1][1] = max(pts[-1][1], yl + 0.3)
        pts.append([tl + 0.55, yl + 0.3])  # rounded lip: bends over the edge (as thick as the flow on the plateau)
        prev = tl + 0.55; ys = yl - (yl - ybot) * np.linspace(0, 1, nf + 1)[1:] ** 1.1
        for k, yq in enumerate(ys):  # clings to the rock face: just in front of it (no gap to see through), never inside it
            tau = (-0.28 + math.sqrt(0.0784 + 19.62 * (yl - yq))) / 9.81  # first ~4 m: the water's own arc off the lip
            te = max(tl + 0.55, front(yl) + 0.35)  # where the rock really falls away (the steep test fires up to 1 m early)
            arc = te + 1.58 * tau if yl - yq < 4.0 else tl + 0.3
            f_ = max(front(yq), front(ys[min(k + 1, len(ys) - 1)]))  # also clear the next row's rock: steps out ABOVE a ledge, never through it
            tk = max(arc, prev if f_ < -1e8 else f_ + clear + 0.175); prev = tk; pts.append([tk, yq])
        cols.append((lat, np.array(pts)))
    R = len(cols[0][1]); G = np.zeros((R, C, 3))
    for j, (lat, P) in enumerate(cols):
        for i in range(R):
            fr = i / (R - 1); wob = (0.35 * (rng.random() - 0.5) if j in (0, C - 1) else 0.0)
            l2 = lat * (0.86 + 0.14 * min(1, fr * 3)) / 0.86 * (1 + 0.15 * fr) + wob  # taper in at the top, widen below
            xy = np.array([x, z]) + S * l2 + F * P[i, 0]; G[i, j] = [xy[0], P[i, 1], xy[1]]
    return G
