"""Stage 9: open-world / hybrid generation for spec_to_level.py (spec["world"] -> level.json["terrain"] + world objects).

Modes (Claude picks one per concept image; see SCENE_SPEC.md):
  structured  Stage 7 arena only (spec has "arena", no "world")         - closed arenas, interiors, compounds
  open        spec has "world" and no "arena"                           - valleys, deserts, cities, coasts...
  hybrid      both: an arena/compound sits on a terrain pad inside a world (terrain + industrial platforms + bridges)
Nothing here assumes a square boundary, symmetry or a central platform.

What the CPU does automatically (deterministic):
  terrain definition from the world spec (relief preset, biome layers, features with stable ids + seeds)
  organic playable boundary (or Claude's polygon) + a natural barrier feature just outside it + invisible colliders
  terrain pads + foundations under every padded structure placed on the ground (buildings never float or sink)
  bridges where a road crosses a river (deck at road level, supports down to the bed, abutments into the banks)
  spawn regions (player / enemy) -> safe, flat, dry, unobstructed points inside the boundary
  walkable sample points for camera / draw-call estimates
"""
import math
import numpy as np
from terrain import Terrain, inside_poly, poly_query, resample, Perlin, _sid
from modules import pads as module_pads

RELIEF = {"flat": dict(amplitude=0.5, scale=90, ridged=0.05, warp=0.3), "gentle": dict(amplitude=1.6, scale=80, ridged=0.15),
          "hilly": dict(amplitude=3.5, scale=70, ridged=0.3), "rugged": dict(amplitude=5.5, scale=60, ridged=0.5, warp=0.8),
          "mountainous": dict(amplitude=8.0, scale=90, ridged=0.6, warp=0.9)}
THEME_BIOME = {"industrial": "industrial", "toxic_industrial": "industrial", "scifi": "industrial", "medieval_town": "temperate", "ruins": "wasteland",
               "desert": "desert", "alpine": "alpine", "fantasy_forest": "fantasy", "alien": "alien", "post_apocalyptic": "wasteland",
               "cartoon": "cartoon", "futuristic_city": "urban", "urban": "urban"}


def A_THEMES():
    import architecture as A
    return A.THEMES


def extent_of(W):
    if W.get("extent"): return [float(v) for v in W["extent"]]
    (cx, cz), (w, d) = W.get("center", [0, 0]), W.get("size", [200, 200]); return [cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2]


def boundary_points(W, ext, seed):
    B = W.get("boundary", {})
    if B.get("points"): return [[float(x), float(z)] for x, z in B["points"]]
    x0, z0, x1, z1 = ext; m = B.get("margin", 22.0); cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    rx, rz = (x1 - x0) / 2 - m, (z1 - z0) / 2 - m; n = B.get("vertices", 30); nz = Perlin(_sid(seed, "boundary"))
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) + 0.07
    shape = B.get("shape", "organic"); sq = 4.0 if shape == "organic" else 2.0  # superellipse: uses the corners, still rounded
    r = 1.0 / (np.abs(np.cos(a)) ** sq + np.abs(np.sin(a)) ** sq) ** (1 / sq)
    if shape == "organic": r = r * (1 + 0.09 * nz.fbm(np.cos(a) * 1.5, np.sin(a) * 1.5, 3))
    r = np.minimum(r, 1.0)
    return [[round(float(cx + rx * r[k] * math.cos(a[k])), 2), round(float(cz + rz * r[k] * math.sin(a[k])), 2)] for k in range(n)]


def terrain_def(spec, W, ext, bpts, theme):
    seed = int(W.get("seed", spec.get("seed", 1))); B = W.get("boundary", {})
    noise = dict(RELIEF[W.get("relief", "gentle")], **W.get("noise", {}))
    feats = [dict(f) for f in W.get("features", [])]
    x0, z0, x1, z1 = ext
    for f in feats:  # rivers / roads that reach the edge of the playable area continue out to the horizon (middle zone)
        if f["type"] in ("river", "road", "street") and f.get("extend", True):
            P = [list(map(float, p)) for p in f["points"]]
            for end, prev in ((0, 1), (-1, -2)):
                e, q = np.array(P[end]), np.array(P[prev]); near_edge = min(e[0] - x0, x1 - e[0], e[1] - z0, z1 - e[1]) < 30 or not inside_poly(bpts, e[:1], e[1:])[0]
                if near_edge:  # gently meandering continuation (seeded by the feature id)
                    u = (e - q) / (np.linalg.norm(e - q) or 1); v = np.array([-u[1], u[0]]); nz = Perlin(_sid(seed, f["id"], end)); L_ = f.get("extend_m", 420.0)
                    more = [(e + u * t + v * 18 * nz.fbm(t / 140.0, 0.5, 2) * min(1, t / 80)).round(2).tolist() for t in np.arange(60, L_ + 1, 60)]
                    P = more[::-1] + P if end == 0 else P + more
            if len(P) != len(f["points"]): f["points"] = P; f["extended"] = True
    if B.get("barrier", "ridge") != "none":
        feats.append(dict(id="Boundary_Barrier", type="barrier", points=bpts, offset=B.get("offset", 16.0), width=B.get("width", 45.0),
                          height=B.get("height", 16.0), falloff=0.3, gen="world.boundary", source="inferred"))
    T = dict(seed=seed, extent=ext, cell=W.get("cell", 2.0), chunk=W.get("chunk", 32), base_y=W.get("base_y", 0.0),
             biome=W.get("biome") or A_THEMES().get(theme, {}).get("biome") or THEME_BIOME.get(theme, "temperate"), noise=noise, features=feats,
             style=W.get("style") or A_THEMES().get(theme, {}).get("style", "realistic"),
             boundary=dict(points=bpts, barrier=B.get("barrier", "ridge")),
             zones=dict(middle=dict(W.get("middle", {})), far=dict(note="Stage 2 background layers (environment.background)")),
             lod=dict(ranges=W.get("lod_ranges", [60, 120])))
    for k in ("water", "layers", "materials", "scatter", "water_material", "style"):
        if k in W: T[k] = W[k]
    return T


def footprint(s):
    sz = s.get("size", [4, 4, 4]); return sz[0], sz[-1]


def build_world(ctx, spec, W, fy, centre):
    """Creates level.json['terrain'] (ctx.terrain_def) + ctx.TR; adds pads, bridges, boundary colliders, spawn regions."""
    import architecture as A
    ext = extent_of(W); seed = int(W.get("seed", spec.get("seed", 1))); bpts = boundary_points(W, ext, seed)
    T = terrain_def(spec, W, ext, bpts, spec.get("theme", "industrial")); feats = T["features"]
    ar = spec.get("arena")
    if ar:  # hybrid: the arena / compound sits on a flattened pad at its floor height
        (cx, cz), (w, d) = ar.get("center", [0, 0]), ar["size"]; t = ar.get("walls", {}).get("thickness", 2) + 2
        feats.append(dict(id="Pad_Arena", type="pad", center=[cx, cz], size=[w + 2 * t, d + 2 * t], y=fy - 0.05, margin=8, surface="plaza", gen="arena"))
    TR0 = Terrain(T, ctx.level_dir); ctx.TR_pre = TR0
    from modules import INFO as MI
    for s in spec.get("structures", []):  # module terrain hooks (tunnel trenches, ...)
        hook = MI.get(s["kind"], {}).get("terrain")
        if hook: feats.extend(dict(f, gen=s["id"]) for f in hook(s, TR0))
    if any(MI.get(s["kind"], {}).get("terrain") for s in spec.get("structures", [])): TR0 = Terrain(T, ctx.level_dir)
    for s in spec.get("structures", []):  # pads + foundations for ground-placed structures
        if s.get("on") or not s.get("position") or not module_pads(s["kind"]): continue
        x, z = s["position"][0], s["position"][-1]; w, d = footprint(s); yaw = A.structure_yaw(s, x, z, centre)
        if len(s["position"]) == 3: y = float(s["position"][1])
        else:
            a = np.radians(yaw); ox, oz = np.meshgrid(np.linspace(-w / 2, w / 2, 4), np.linspace(-d / 2, d / 2, 4))
            px = x + ox * np.cos(a) + oz * np.sin(a); pz = z - ox * np.sin(a) + oz * np.cos(a)
            y = float(np.median(TR0.height(px.ravel(), pz.ravel())))
        y = round(y, 2); m = s.get("pad_margin", 1.2)
        feats.append(dict(id="Pad_" + s["id"], type="pad", center=[x, z], size=[w + 2 * m, d + 2 * m], yaw=yaw, y=y, margin=s.get("pad_blend", 5.0),
                          surface="pad", gen=s["id"]))
        s["_pad_y"] = y; s["_found"] = 0.2
    TR = Terrain(T, ctx.level_dir); ctx.TR = TR; ctx.terrain_def = T; ctx.boundary = bpts
    for s in spec.get("structures", []):  # foundations (visible 20 cm plinth, 1.4 m into the ground)
        if s.get("_pad_y") is None: continue
        ctx.element = (s["id"], s.get("source", "visible")); w, d = footprint(s); yaw = A.structure_yaw(s, s["position"][0], s["position"][-1], centre)
        ctx.add(s["id"] + "_Foundation", "box", [s["position"][0], s["_pad_y"] - 1.4, s["position"][-1]], [w + 0.5, 1.61, d + 0.5], "foundation", rot=[0, yaw, 0])
    auto = auto_bridges(TR, T)
    for b in auto: ctx.notes.append(f"{b['id']}: bridge added where road {b['_road']} crosses river {b['_river']}")
    ctx.element = ("world.boundary", "inferred")
    for i, (p0, p1) in enumerate(zip(bpts, bpts[1:] + bpts[:1])):  # invisible safety colliders along the playable polygon
        L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); yaw = A.yaw_to((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L) - 90
        h = TR.height(np.array([p0[0], p1[0]]), np.array([p0[1], p1[1]]))
        ctx.add(f"Boundary_{i + 1:02d}", "boundary", [(p0[0] + p1[0]) / 2, float(h.min()) - 4, (p0[1] + p1[1]) / 2], [L + 0.6, float(h.max() - h.min()) + 34, 0.5], rot=[0, yaw, 0])
    ctx.element = None
    return TR, auto


def auto_bridges(TR, T):
    """Bridge structures for every road x river crossing (the terrain leaves the river open under the road)."""
    out = []
    roads = [f for f in TR.features if f["type"] in ("road", "street", "path")]; rivers = [f for f in TR.features if f["type"] == "river"]
    for r in roads:
        P, s = resample(r["points"], 1.0); prof = TR._prof[r["id"]]
        for v in rivers:
            d, _, _, _ = poly_query(v["points"], P[:, 0], P[:, 1]); k = int(np.argmin(d))
            if d[k] > 1.5: continue
            pv = TR._prof[v["id"]]; _, sv, _, _ = poly_query(v["points"], P[k:k + 1, 0], P[k:k + 1, 1])
            wat = float(np.interp(sv[0], pv["s"], pv["water"])); bed = float(np.interp(sv[0], pv["s"], pv["bed"]))
            hw = v.get("width", 8) * 0.35 + (wat - bed) / v.get("bank_slope", 0.5) + 1.0  # river mask half width the road leaves open
            dirv = P[min(k + 2, len(P) - 1)] - P[max(k - 2, 0)]; dirv /= np.linalg.norm(dirv)
            ang = abs(math.degrees(math.acos(min(1.0, abs(float(np.dot(dirv, _river_dir(v["points"], P[k]))))))))
            half = (hw + 3.0) / max(0.35, math.sin(math.radians(max(ang, 20))))  # skewed crossings need a longer deck
            ya = float(np.interp(s[k] - half, prof["s"], prof["y"])) + 0.1; yb = float(np.interp(s[k] + half, prof["s"], prof["y"])) + 0.1
            a, b = P[k] - dirv * half, P[k] + dirv * half
            t_ = np.linspace(0, 1, 41); nrm = np.array([-dirv[1], dirv[0]]); hw_ = r.get("deck_width", r.get("width", 6) + 1.0) / 2
            Hs = np.max([TR.height(a[0] + (b[0] - a[0]) * t_ + nrm[0] * o_, a[1] + (b[1] - a[1]) * t_ + nrm[1] * o_) for o_ in (-hw_, 0.0, hw_)], axis=0)
            lift = max(0.0, float((Hs + 0.12 - (ya + (yb - ya) * t_)).max())); ya += lift; yb += lift  # the deck clears the road profile everywhere
            out.append(dict(id=f"Bridge_{r['id']}_{v['id']}", kind="bridge", **{"from": [round(float(a[0]), 2), round(float(a[1]), 2)]},
                            to=[round(float(b[0]), 2), round(float(b[1]), 2)], y=round((ya + yb) / 2, 2), y_from=round(ya, 2), y_to=round(yb, 2),
                            width=r.get("deck_width", r.get("width", 6) + 1.0), source="inferred", _road=r["id"], _river=v["id"]))
    return out


def _river_dir(pts, p):
    P = np.asarray(pts, float); best, bd = None, 1e9
    for a, b in zip(P[:-1], P[1:]):
        ab = b - a; u = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-9), 0, 1); dd = np.linalg.norm(a + u * ab - p)
        if dd < bd: bd, best = dd, ab / np.linalg.norm(ab)
    return best


def spawn_regions(ctx, spec, W, G, blocked):
    """Safe points per region: flat (<= 12 deg), dry, inside the boundary, clear of structures, spread apart."""
    TR = ctx.TR; out = []; rq = G["design"]["spawn_clearance"] + G["player"]["radius"]
    regs = W.get("spawn_regions") or [dict(id="Player_Start", team="player", center=_default_spawn(TR, ctx.boundary), radius=14, count=4)]
    for r in regs:
        cx, cz = r["center"]; R = r.get("radius", 12); n = r.get("count", 4); g = np.linspace(-R, R, 13); X, Z = np.meshgrid(cx + g, cz + g)
        X, Z = X.ravel(), Z.ravel(); ok = np.hypot(X - cx, Z - cz) <= R
        ok &= inside_poly(ctx.boundary, X, Z)
        e = 1.0; H = TR.height(X, Z); sl = np.degrees(np.arctan(np.hypot(TR.height(X + e, Z) - TR.height(X - e, Z), TR.height(X, Z + e) - TR.height(X, Z - e)) / (2 * e)))
        ok &= sl <= 12; ok &= ~np.isfinite(TR.water_y(X, Z)) | (H > TR.water_y(X, Z) + 0.3)
        for bx, bz, br in blocked: ok &= np.hypot(X - bx, Z - bz) > br + rq
        pts = []
        for k in np.argsort(np.hypot(X - cx, Z - cz)):
            if not ok[k]: continue
            if all(math.hypot(X[k] - p[0], Z[k] - p[2]) >= r.get("spacing", 4.0) for p in pts): pts.append([round(float(X[k]), 2), round(float(H[k]), 2), round(float(Z[k]), 2)])
            if len(pts) >= n: break
        face = r.get("facing") or _centroid(ctx.boundary)
        yaw = math.degrees(math.atan2(-(face[0] - cx), -(face[1] - cz)))
        out.append(dict(id=r["id"], team=r.get("team", "player"), center=[cx, cz], radius=R, points=pts, yaw_deg=round(yaw, 1),
                        note=None if len(pts) >= n else f"only {len(pts)} of {n} safe points found"))
    return out


def _centroid(pts):
    P = np.asarray(pts, float); return [float(P[:, 0].mean()), float(P[:, 1].mean())]


def _default_spawn(TR, bpts):
    c = _centroid(bpts); return c


def walk_samples(ctx, n=6):
    """Walkable sample areas on open terrain (camera / draw-call estimate positions)."""
    P = np.asarray(ctx.boundary, float); c = P.mean(0); out = []; TR = ctx.TR; e = 1.0
    for k in range(n):  # flattest dry point near 55 % of the way to the boundary in each direction
        a = 2 * math.pi * k / n; p0 = c + (P[np.argmax((P - c) @ [math.cos(a), math.sin(a)])] - c) * 0.55
        g = np.linspace(-12, 12, 7); X, Z = np.meshgrid(p0[0] + g, p0[1] + g); X, Z = X.ravel(), Z.ravel()
        sl = np.hypot(TR.height(X + e, Z) - TR.height(X - e, Z), TR.height(X, Z + e) - TR.height(X, Z - e)) / (2 * e)
        wet = TR.height(X, Z) < TR.water_y(X, Z) + 0.3; sc = sl + wet * 9 + np.hypot(X - p0[0], Z - p0[1]) * 0.004; i = int(np.argmin(sc)); p = (X[i], Z[i])
        y = TR.height_at(p[0], p[1]); out.append(dict(name=f"Terrain_{k + 1:02d}", min=[round(p[0] - 1.5, 2), round(p[1] - 1.5, 2)], max=[round(p[0] + 1.5, 2), round(p[1] + 1.5, 2)], y=round(y, 2), terrain=True, unreachable_ok=True))
    return out


def world_bounds(ctx, extra_top=0.0):
    P = np.asarray(ctx.boundary, float); G = ctx.TR.grid(); top = float(G["H"].max())
    return dict(min=[round(float(P[:, 0].min()) - 2, 2), round(float(G["H"].min()) - 1, 2), round(float(P[:, 1].min()) - 2, 2)],
                max=[round(float(P[:, 0].max()) + 2, 2), round(max(top, extra_top) + 12, 2), round(float(P[:, 1].max()) + 2, 2)])
