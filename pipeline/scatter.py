"""Stage 9: natural prop library + deterministic instanced scatter (vegetation, rocks, debris) on the world terrain.

level.json["terrain"]["scatter"] = [ {id, kinds: ["conifer", {"kind": "boulder", "weight": 0.3, "scale": [0.8, 1.6]}],
     area: "playable" | "extent" | [x0, z0, x1, z1] | [[x, z], ...polygon], density (instances per 100 m2), spacing (m),
     cluster 0..1 (clumping), slope_max (deg), height [lo, hi], layers ["grass", ...] (terrain material layers allowed),
     avoid ["road", "path", "river", "bank", "pad", "plaza", "cliff", "objects", "spawns"], style, seed, view_distance} ]

Every kind is a few low-poly VARIANTS (closed meshes, base at y=0) shared by all instances: the dev level.glb holds
them merged per chunk + material (few draw calls), terrain.json["instances"] keeps every transform and props.glb the
variant meshes, so Godot can use MultiMeshInstance3D instead (optional). Distant vegetation is never individual
geometry: scatter stops at its view distance (mobile visibility range) and the terrain layers / middle-zone carry on.
Styles change proportions + palette: realistic, stylised_scifi, fantasy, cartoon, post_apocalyptic.
"""
import math, os
import numpy as np
import trimesh
from trimesh.transformations import rotation_matrix

STYLES = {  # role colours per art style (materials "sc_<role>")
    "realistic": dict(trunk=[0.3, 0.22, 0.15], foliage=[0.2, 0.32, 0.15], foliage_b=[0.32, 0.4, 0.18], rock=[0.45, 0.43, 0.4], crystal=[0.4, 0.8, 1.0],
                      debris=[0.3, 0.28, 0.26], cactus=[0.3, 0.42, 0.25], flower=[0.85, 0.75, 0.3]),
    "stylised_scifi": dict(trunk=[0.25, 0.22, 0.3], foliage=[0.2, 0.45, 0.42], foliage_b=[0.35, 0.3, 0.55], rock=[0.36, 0.36, 0.4], crystal=[0.3, 0.95, 1.0],
                           debris=[0.32, 0.33, 0.36], cactus=[0.25, 0.5, 0.45], flower=[1.0, 0.4, 0.8]),
    "fantasy": dict(trunk=[0.35, 0.24, 0.16], foliage=[0.25, 0.5, 0.22], foliage_b=[0.45, 0.55, 0.2], rock=[0.48, 0.46, 0.52], crystal=[0.75, 0.45, 1.0],
                    debris=[0.4, 0.35, 0.3], cactus=[0.35, 0.5, 0.25], flower=[0.95, 0.5, 0.6]),
    "cartoon": dict(trunk=[0.45, 0.28, 0.15], foliage=[0.3, 0.65, 0.2], foliage_b=[0.55, 0.75, 0.25], rock=[0.6, 0.56, 0.52], crystal=[0.4, 0.8, 1.0],
                    debris=[0.5, 0.42, 0.35], cactus=[0.35, 0.65, 0.3], flower=[1.0, 0.85, 0.2]),
    "post_apocalyptic": dict(trunk=[0.25, 0.22, 0.2], foliage=[0.33, 0.33, 0.2], foliage_b=[0.4, 0.36, 0.22], rock=[0.4, 0.37, 0.33], crystal=[0.5, 1.0, 0.3],
                             debris=[0.35, 0.25, 0.18], cactus=[0.32, 0.36, 0.22], flower=[0.6, 0.55, 0.3]),
}
ROLE_KIND = dict(trunk=("wood", 2.0), foliage=("grass", 2.0), foliage_b=("moss", 2.0), rock=("rock", 4.0), crystal=("glow", 1.0), debris=("damaged_metal", 2.0),
                 cactus=("moss", 1.5), flower=("grass", 1.0))


def _ico(r, sub=1, seed=1, jitter=0.18, flat=0.0):
    m = trimesh.creation.icosphere(subdivisions=sub, radius=1.0); rng = np.random.default_rng(seed)
    v = m.vertices * rng.uniform(1 - jitter, 1 + jitter, (len(m.vertices), 1)) * r
    if flat: v[:, 1] = np.where(v[:, 1] < 0, v[:, 1] * (1 - flat), v[:, 1])
    return trimesh.Trimesh(v, m.faces, process=True)


def _cone(r, h, n=7, y=0.0):
    m = trimesh.creation.cone(radius=r, height=h, sections=n); m.apply_transform(rotation_matrix(-np.pi / 2, [1, 0, 0])); m.apply_translation([0, y, 0]); return m


def _cyl(r, h, n=6, y=0.0, r_top=None):
    if r_top is None:
        m = trimesh.creation.cylinder(radius=r, height=h, sections=n)
    else:
        a = np.linspace(0, 2 * np.pi, n, endpoint=False); bot = np.c_[r * np.cos(a), np.full(n, -h / 2), r * np.sin(a)]; top = np.c_[r_top * np.cos(a), np.full(n, h / 2), r_top * np.sin(a)]
        m = trimesh.convex.convex_hull(np.vstack([bot, top]))
        m.apply_transform(rotation_matrix(np.pi / 2, [1, 0, 0]))
    m.apply_transform(rotation_matrix(-np.pi / 2, [1, 0, 0])); m.apply_translation([0, y + h / 2, 0]); return m


def _place(m, T):
    m = m.copy(); m.apply_transform(T); return m


def conifer(rng, st):
    h = rng.uniform(7, 11) * (0.85 if st == "cartoon" else 1); tiers = 2 if st == "cartoon" else 3; trunk = _cyl(0.22 * h / 9, h * 0.35, 6, -0.3)
    fol = [_cone(h * (0.22 - 0.045 * k) * (1.25 if st == "cartoon" else 1), h * 0.42, 7 if st != "cartoon" else 8, h * (0.22 + 0.21 * k)) for k in range(tiers)]
    return dict(trunk=trunk, foliage=trimesh.util.concatenate(fol)), dict(collider=("cylinder", 0.22 * h / 9 + 0.05, h * 0.5))


def broadleaf(rng, st):
    h = rng.uniform(5.5, 8.5); r = h * rng.uniform(0.32, 0.4) * (1.2 if st in ("fantasy", "cartoon") else 1); trunk = _cyl(0.2 * h / 7, h * 0.55, 6, -0.3, 0.12 * h / 7)
    crown = [_ico(r, 1, int(rng.integers(1e6)), 0.2, 0.3)]; crown[0].apply_translation([0, h * 0.62, 0])
    if st != "cartoon":
        for k in range(2):
            c = _ico(r * 0.6, 1, int(rng.integers(1e6)), 0.2); a = rng.uniform(0, 2 * np.pi); c.apply_translation([math.cos(a) * r * 0.55, h * 0.55 + rng.uniform(-0.5, 0.8), math.sin(a) * r * 0.55]); crown.append(c)
    return dict(trunk=trunk, foliage=trimesh.util.concatenate(crown)), dict(collider=("cylinder", 0.2 * h / 7 + 0.05, h * 0.5))


def dead_tree(rng, st):
    h = rng.uniform(4.5, 7.5); parts = [_cyl(0.18, h, 5, -0.3, 0.06)]
    for k in range(3):
        b = _cyl(0.08, h * 0.35, 4, 0, 0.03); b.apply_transform(rotation_matrix(math.radians(rng.uniform(35, 60)), [math.cos(k * 2.1), 0, math.sin(k * 2.1)]))
        b.apply_translation([0, h * (0.45 + 0.15 * k), 0]); parts.append(b)
    return dict(trunk=trimesh.util.concatenate(parts)), dict(collider=("cylinder", 0.22, h * 0.6))


def palm(rng, st):
    h = rng.uniform(6, 9); seg = []; x = 0.0; lean = rng.uniform(0.04, 0.1)
    for k in range(5):
        s = _cyl(0.2 - 0.02 * k, h / 5 + 0.05, 6, h / 5 * k - (0.3 if k == 0 else 0)); s.apply_translation([x, 0, 0]); seg.append(s); x += lean * h / 5 * (k + 1) * 0.5
    leaves = []
    for k in range(7):
        a = 2 * np.pi * k / 7; L = rng.uniform(2.6, 3.4)
        blade = trimesh.convex.convex_hull([[0, 0, -0.3], [0, 0, 0.3], [L, -0.9, -0.08], [L, -0.9, 0.08], [L * 0.5, 0.25, 0], [L * 0.5, 0.12, 0]])
        blade.apply_transform(rotation_matrix(a, [0, 1, 0])); blade.apply_translation([x, h, 0]); leaves.append(blade)
    return dict(trunk=trimesh.util.concatenate(seg), foliage=trimesh.util.concatenate(leaves)), dict(collider=("cylinder", 0.25, h * 0.6))


def bush(rng, st):
    r = rng.uniform(0.7, 1.2); b = _ico(r, 1, int(rng.integers(1e6)), 0.22, 0.5); b.apply_translation([0, r * 0.45, 0])
    return dict(foliage_b=b), dict()


def grass_tuft(rng, st):
    blades = []
    for k in range(5):
        a = 2 * np.pi * k / 5 + rng.uniform(-0.3, 0.3); d = rng.uniform(0.05, 0.25); hh = rng.uniform(0.35, 0.6)
        p = trimesh.convex.convex_hull([[-0.05, 0, -0.03], [0.05, 0, -0.03], [0, 0, 0.05], [math.cos(a) * 0.15, hh, math.sin(a) * 0.15]])
        p.apply_translation([math.cos(a) * d, -0.05, math.sin(a) * d]); blades.append(p)
    return dict(foliage=trimesh.util.concatenate(blades)), dict()


def rock_small(rng, st):
    r = rng.uniform(0.35, 0.7); m = _ico(r, 1, int(rng.integers(1e6)), 0.25, 0.6); m.apply_scale([1, rng.uniform(0.5, 0.8), 1]); m.apply_translation([0, r * 0.25, 0])
    return dict(rock=m), dict()


def boulder(rng, st):
    r = rng.uniform(1.1, 2.0); m = _ico(r, 1, int(rng.integers(1e6)), 0.22, 0.5); m.apply_scale([1, rng.uniform(0.6, 0.9), rng.uniform(0.8, 1.1)]); m.apply_translation([0, r * 0.35, 0])
    return dict(rock=m), dict(collider=("convex",))


def cactus(rng, st):
    h = rng.uniform(2.2, 3.6); parts = [_cyl(0.28, h, 8, -0.2)]
    for side in (-1, 1):
        if rng.random() < 0.75:
            yb = h * rng.uniform(0.35, 0.55); arm = _cyl(0.18, 0.6, 6); arm.apply_transform(rotation_matrix(np.pi / 2, [0, 0, 1])); arm.apply_translation([side * 0.55, yb, 0])
            up = _cyl(0.18, h * 0.35, 6, yb - 0.1); up.apply_translation([side * 0.85, 0, 0]); parts += [arm, up]
    return dict(cactus=trimesh.util.concatenate(parts)), dict(collider=("cylinder", 0.35, h))


def crystal(rng, st):
    parts = []
    for k in range(int(rng.integers(3, 6))):
        h = rng.uniform(0.8, 2.4); r = rng.uniform(0.15, 0.32); a = np.linspace(0, 2 * np.pi, 6, endpoint=False)
        pts = np.r_[np.c_[r * np.cos(a), np.zeros(6), r * np.sin(a)], np.c_[r * np.cos(a), np.full(6, h * 0.8), r * np.sin(a)], [[0, h, 0]]]
        c = trimesh.convex.convex_hull(pts); c.apply_transform(rotation_matrix(rng.uniform(-0.45, 0.45), [rng.uniform(-1, 1), 0, rng.uniform(-1, 1)]))
        c.apply_translation([rng.uniform(-0.4, 0.4), -0.15, rng.uniform(-0.4, 0.4)]); parts.append(c)
    return dict(crystal=trimesh.util.concatenate(parts)), dict(collider=("convex",))


def alien_plant(rng, st):
    h = rng.uniform(1.5, 3.0); stalk = _cyl(0.08, h, 5, -0.2, 0.05); bulb = _ico(0.35, 1, int(rng.integers(1e6)), 0.15); bulb.apply_translation([0, h, 0])
    return dict(foliage_b=stalk, crystal=bulb), dict()


def debris(rng, st):
    parts = []
    for k in range(int(rng.integers(2, 4))):
        b = trimesh.creation.box([rng.uniform(0.6, 1.8), rng.uniform(0.15, 0.5), rng.uniform(0.4, 1.2)])
        b.apply_transform(rotation_matrix(rng.uniform(-0.4, 0.4), [1, 0, 0]) @ rotation_matrix(rng.uniform(0, np.pi), [0, 1, 0])); b.apply_translation([rng.uniform(-0.7, 0.7), 0.05, rng.uniform(-0.7, 0.7)])
        parts.append(b)
    return dict(debris=trimesh.util.concatenate(parts)), dict()


def stump(rng, st):
    return dict(trunk=_cyl(rng.uniform(0.3, 0.45), rng.uniform(0.4, 0.8), 7, -0.15)), dict(collider=("cylinder", 0.4, 0.7))


def log(rng, st):
    L = rng.uniform(3, 5); m = _cyl(0.3, L, 7); m.apply_transform(rotation_matrix(np.pi / 2, [0, 0, 1])); m.apply_translation([L / 2, 0.15, 0])
    return dict(trunk=m), dict(collider=("convex",))


def flowers(rng, st):
    parts = []
    for k in range(6):
        a = rng.uniform(0, 2 * np.pi); d = rng.uniform(0, 0.35); s = _ico(0.07, 0, int(rng.integers(1e6)), 0.1); s.apply_translation([math.cos(a) * d, rng.uniform(0.2, 0.35), math.sin(a) * d]); parts.append(s)
    return dict(flower=trimesh.util.concatenate(parts)), dict()


PROPS = dict(conifer=conifer, broadleaf=broadleaf, dead_tree=dead_tree, palm=palm, bush=bush, grass_tuft=grass_tuft, rock_small=rock_small,
             boulder=boulder, cactus=cactus, crystal=crystal, alien_plant=alien_plant, debris=debris, stump=stump, log=log, flowers=flowers)
SINK = dict(conifer=0.2, broadleaf=0.2, dead_tree=0.2, palm=0.2, bush=0.25, grass_tuft=0.05, rock_small=0.15, boulder=0.45, cactus=0.15, crystal=0.12,
            alien_plant=0.15, debris=0.1, stump=0.1, log=0.12, flowers=0.0)
DEFAULT_VIEW = dict(grass_tuft=35, flowers=30, rock_small=60, debris=60, bush=80, crystal=90, alien_plant=80)  # m; trees / boulders: 160


def variants(kind, style, n=3, seed=0):
    out = []
    for v in range(n):
        rng = np.random.default_rng((sum(map(ord, kind + style)) * 7919 + v * 104729 + seed) % (2 ** 32))  # stable across runs
        parts, meta = PROPS[kind](rng, style)
        for m in parts.values(): m.fix_normals()
        out.append((parts, meta))
    return out


def materials(style, used_roles):
    pal = STYLES.get(style, STYLES["realistic"]); out = {}
    for r in sorted(used_roles):
        k, tile = ROLE_KIND[r]; out[f"sc_{r}"] = dict(type=k, color=pal[r], tile_m=tile, res=128, **({"emissive": [c * 0.8 for c in pal[r]]} if r == "crystal" else {}))
    return out


def roles_of(kind, style):
    return set(variants(kind, style, 1)[0][0])


def place(TR, L, sc, blockers):
    """Deterministic instance transforms [(kind, variant, x, y, z, yaw_deg, scale)] for one scatter rule."""
    from terrain import inside_poly, Perlin, _sid
    seed = _sid(TR.seed, "scatter", sc["id"], sc.get("seed", 0)); rng = np.random.default_rng(seed)
    area = sc.get("area", "playable"); bpts = (L["terrain"].get("boundary") or {}).get("points")
    if area == "playable" and bpts: P = np.asarray(bpts, float); poly = P
    elif area in ("extent", "playable"): poly = np.array([[TR.x0, TR.z0], [TR.x1, TR.z0], [TR.x1, TR.z1], [TR.x0, TR.z1]], float)
    elif len(area) == 4 and not isinstance(area[0], list): x0, z0, x1, z1 = area; poly = np.array([[x0, z0], [x1, z0], [x1, z1], [x0, z1]], float)
    else: poly = np.asarray(area, float)
    dens = sc.get("density", 1.0); sp = sc.get("spacing", max(0.8, 10.0 / math.sqrt(max(dens, 1e-3))))
    lo, hi = poly.min(0), poly.max(0); gx = np.arange(lo[0], hi[0], sp); gz = np.arange(lo[1], hi[1], sp)
    X, Z = np.meshgrid(gx, gz); X = X.ravel() + rng.uniform(-0.45, 0.45, X.size) * sp; Z = Z.ravel() + rng.uniform(-0.45, 0.45, Z.size) * sp
    keep = inside_poly(poly, X, Z) & (X > TR.x0 + 1) & (X < TR.x1 - 1) & (Z > TR.z0 + 1) & (Z < TR.z1 - 1)
    p_acc = min(1.0, dens * sp * sp / 100.0)
    cl = sc.get("cluster", 0.5)
    if cl > 0:
        nz = Perlin(seed); c = nz.fbm(X / 28.0, Z / 28.0, 3) * 0.5 + 0.5; p = p_acc * np.clip((c - cl * 0.5) / max(1e-3, 1 - cl * 0.5), 0, 1) * (1 + cl)
    else: p = np.full(X.size, p_acc)
    keep &= rng.random(X.size) < p
    X, Z = X[keep], Z[keep]
    if not len(X): return []
    H, M = TR._eval(X, Z); e = 0.75
    sl = np.degrees(np.arctan(np.hypot(TR.height(X + e, Z) - TR.height(X - e, Z), TR.height(X, Z + e) - TR.height(X, Z - e)) / (2 * e)))
    ok = sl <= sc.get("slope_max", 30)
    if sc.get("height"): ok &= (H >= sc["height"][0]) & (H <= sc["height"][1])
    W = TR.water_y(X, Z); ok &= ~(H < W + 0.3)
    avoid = sc.get("avoid", ["road", "path", "river", "bank", "pad", "plaza", "cliff", "objects", "spawns"])
    for k in avoid:
        if k in M: ok &= M[k] < 0.5
    if sc.get("layers"):
        n = np.stack([-(TR.height(X + e, Z) - TR.height(X - e, Z)) / (2 * e), np.ones_like(X), -(TR.height(X, Z + e) - TR.height(X, Z - e)) / (2 * e)], 1)
        n /= np.linalg.norm(n, axis=1, keepdims=True); lay = TR.classify(np.c_[X, H, Z], n, M, W)
        ok &= np.isin(np.array([TR.rules[k]["material"] for k in lay]), sc["layers"])
    if "objects" in avoid or "spawns" in avoid:
        for bx0, bz0, bx1, bz1 in blockers: ok &= ~((X > bx0) & (X < bx1) & (Z > bz0) & (Z < bz1))
    X, Z, H = X[ok], Z[ok], H[ok]
    kinds = [k if isinstance(k, dict) else {"kind": k} for k in sc["kinds"]]; w = np.array([k.get("weight", 1.0) for k in kinds]); w /= w.sum()
    pick = rng.choice(len(kinds), size=len(X), p=w); out = []
    for x, z, h, ki in zip(X, Z, H, pick):
        k = kinds[ki]; s0, s1 = k.get("scale", sc.get("scale", [0.8, 1.25])); s = float(rng.uniform(s0, s1)); var = int(rng.integers(0, k.get("variants", 3)))
        out.append((k["kind"], var, round(float(x), 3), round(float(h) - SINK[k["kind"]] * s, 3), round(float(z), 3), round(float(rng.uniform(0, 360)), 1), round(s, 3)))
    return out


def _atlas_uv(m, rect):
    """Unwelded triangles with a box projection normalised to the part's bounds, squeezed into its atlas cell."""
    v = m.vertices[m.faces].reshape(-1, 3); f = np.arange(len(v)).reshape(-1, 3); fn = m.face_normals; ax = np.abs(fn).argmax(1).repeat(3)
    lo, hi = m.bounds; sz = np.maximum(hi - lo, 1e-6); t = (v - lo) / sz
    uv = np.where(ax[:, None] == 0, t[:, [2, 1]], np.where(ax[:, None] == 1, t[:, [0, 2]], t[:, [0, 1]]))
    u0, v0, u1, v1 = rect; return v, f, np.c_[u0 + uv[:, 0] * (u1 - u0), v0 + uv[:, 1] * (v1 - v0)]


def blockers_of(L, world, extra=()):
    """XZ boxes scatter keeps clear of: every non-terrain object footprint (+0.8 m) and spawn points (4 m)."""
    from build_level import shape
    B = []
    for o in L["objects"]:
        if o["type"] in ("group", "boundary") or o["name"] not in world: continue
        try: b = shape(o).bounds
        except Exception: continue
        c = np.array([[x, y, z, 1] for x in b[:, 0] for y in b[:, 1] for z in b[:, 2]]) @ world[o["name"]].T
        B.append((c[:, 0].min() - 0.8, c[:, 2].min() - 0.8, c[:, 0].max() + 0.8, c[:, 2].max() + 0.8))
    for p in [L["spawn"]["position"]] + [s["position"] for s in L.get("spawns", [])] + [q for r in L.get("spawn_regions", []) for q in r.get("points", [])]:
        B.append((p[0] - 4, p[2] - 4, p[0] + 4, p[2] + 4))
    return B + list(extra)


def build_scatter(scene, L, TR, mats, material_fn, level_dir, world, tinfo):
    """Adds merged scatter meshes (per scatter id, chunk, material) to the dev scene; instances + props.glb for Godot."""
    S = L["terrain"].get("scatter", []); tinfo["instances"] = {}
    pdir = os.path.join(level_dir, "props")
    if not S:
        if os.path.exists(os.path.join(pdir, "props.glb")): os.remove(os.path.join(pdir, "props.glb"))
        return 0
    blockers = blockers_of(L, world); tris = 0; lib = trimesh.Scene(); n_lib = 0
    from glb_tools import dedupe_images
    for sc in S:
        style = sc.get("style", L["terrain"].get("style", "realistic")); inst = place(TR, L, sc, blockers)
        kinds = sorted({i[0] for i in inst}); var = {k: variants(k, style, 3, sc.get("seed", 0)) for k in kinds}
        roles = sorted({r for k in kinds for v in var[k] for r in v[0]})
        for mname, mdef in materials(style, roles).items(): L["materials"].setdefault(mname, mdef)
        aname = f"sc_atlas_{sc['id'].lower()}"  # all roles of this scatter in ONE atlas material: one draw call per merged cell
        from materials import atlas_material
        amat, _, rects = atlas_material(aname, [L["materials"][f"sc_{r}"] for r in roles]); mats[aname] = amat; rect = {r: rects[k] for k, r in enumerate(roles)}
        coll = {k for k in kinds if var[k][0][1].get("collider")}
        vd = {k: sc.get("view_distance") or DEFAULT_VIEW.get(k, 160) for k in kinds}
        groups, node_vd = {}, {}
        for kind, v, x, y, z, yaw, s in inst:  # merged per cell; cell size follows the view distance (small things pop in small cells)
            cs = int(max(32, min(TR.C * TR.cell, vd[kind]))); ci, cj = int((z - TR.z0) // cs), int((x - TR.x0) // cs)
            T = trimesh.transformations.translation_matrix([x, y, z]) @ rotation_matrix(math.radians(yaw), [0, 1, 0]) @ np.diag([s, s, s, 1])
            for role, m in var[kind][v][0].items():
                key = (("SC" if kind in coll else "SCN"), cs, ci, cj); groups.setdefault(key, []).append(_atlas_uv(_place(m, T), rect[role]))
                node_vd[key] = max(node_vd.get(key, 0), vd[kind])
        nodes = {}
        for key, ms in sorted(groups.items()):
            pre, cs, ci, cj = key; v_ = np.vstack([m[0] for m in ms]); o = np.cumsum([0] + [len(m[0]) for m in ms])[:-1]
            f_ = np.vstack([m[1] + oo for m, oo in zip(ms, o)]); uv = np.vstack([m[2] for m in ms])
            mm = trimesh.Trimesh(v_, f_, process=False); mm.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[aname])
            node = f"{pre}_{sc['id']}__{cs}_{ci}_{cj}"; scene.add_geometry(mm, node_name=node, geom_name=node); tris += len(mm.faces); nodes[node] = node_vd[key]
        per = {}
        for kind, v, x, y, z, yaw, s in inst: per.setdefault(kind, []).append([x, y, z, yaw, s, v])
        tinfo["instances"][sc["id"]] = dict(style=style, count=len(inst), collision_kinds=sorted(coll), view_distance=vd, nodes=nodes,
                                            kinds={k: dict(count=len(p), variants=[f"{k}_{style}_{i}" for i in range(3)], tris_per_instance=[int(sum(len(m.faces) for m in var[k][i][0].values())) for i in range(3)],
                                                       collider=var[k][0][1].get("collider"), transforms_xyz_yaw_scale_variant=p) for k, p in per.items()})
        for k in kinds:  # variant library (unit transforms) for Godot MultiMesh
            for i, (parts, _) in enumerate(var[k]):
                for role, m in parts.items():
                    v_, f_, uv = _atlas_uv(m, rect[role]); mm = trimesh.Trimesh(v_, f_, process=False); mm.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[aname])
                    lib.add_geometry(mm, node_name=f"{k}_{style}_{i}_{role}", geom_name=f"{k}_{style}_{i}_{role}"); n_lib += 1
    if n_lib:
        os.makedirs(pdir, exist_ok=True); lib.export(os.path.join(pdir, "props.glb")); dedupe_images(os.path.join(pdir, "props.glb"))
    return tris


def colliders(L, tinfo):
    """Collision for colliding scatter kinds (trunk cylinders / convex hulls) from terrain.json instances."""
    out = []
    for sid, d in tinfo.get("instances", {}).items():
        for kind, k in d["kinds"].items():
            c = k.get("collider")
            if not c: continue
            var = variants(kind, d["style"], 3) if c[0] == "convex" else None
            for n, (x, y, z, yaw, s, v) in enumerate(k["transforms_xyz_yaw_scale_variant"]):
                nm = f"SC_{sid}_{kind}_{n:04d}"
                if c[0] == "cylinder":
                    out.append(dict(name=nm, source=f"scatter:{sid}", shape="cylinder", center=[x, round(y + c[2] * s / 2, 3), z], radius=round(c[1] * s, 3), height=round(c[2] * s, 3), rotation=[0, 0, 0, 1]))
                else:
                    pts = np.vstack([m.vertices for m in var[v][0].values()]); hull = trimesh.convex.convex_hull(pts).vertices
                    if len(hull) > 24: hull = hull[np.linspace(0, len(hull) - 1, 24).astype(int)]
                    T = trimesh.transformations.translation_matrix([x, y, z]) @ rotation_matrix(math.radians(yaw), [0, 1, 0]) @ np.diag([s, s, s, 1])
                    out.append(dict(name=nm, source=f"scatter:{sid}", shape="convex", points=(np.c_[hull, np.ones(len(hull))] @ T.T)[:, :3].round(3).tolist()))
    return out
