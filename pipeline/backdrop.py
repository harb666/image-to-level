"""Distant environment geometry (no collision, low-poly, closed silhouettes). Used by environment.py.

Every generator is deterministic from its layer `id` + `seed`, so editing one layer in level.json never changes the
others. Level azimuth convention: 0° = north (-z), 90° = east (+x). Layer types:
  ground        polar terrain skirt from under the arena out to the horizon (rises towards the mountains)
  mountain_ring closed 360° ridge: inner slope, ridge, outer slope, base below ground (no open backs)
  spires        scattered rock spires (tapered, jittered prisms, closed caps)
  skyline       band of industrial blocks + chimneys along an azimuth range
  factory       one modular factory complex (hall, towers, chimneys, pipe bridge) at azimuth/distance
  ring_structure  sci-fi megastructure ring on pylons at azimuth/distance (Stage 9)
"""
import numpy as np, trimesh
from sky import fbm3

QUALITY = {  # Balanced is the default everywhere
    "performance": dict(sky_width=1024, sky_q=80, ring_segments=48, ground_rings=8, density=0.6, factory_detail=0, tex_res=64, far=600),
    "balanced": dict(sky_width=2048, sky_q=84, ring_segments=96, ground_rings=12, density=1.0, factory_detail=1, tex_res=128, far=800),
    "quality": dict(sky_width=4096, sky_q=88, ring_segments=160, ground_rings=16, density=1.4, factory_detail=2, tex_res=256, far=1000),
}


def _seed(layer):
    return (sum(map(ord, layer["id"])) * 131 + int(layer.get("seed", 0)) * 7919) % 100003


def polar(az_deg, dist):
    a = np.radians(az_deg); return np.array([dist * np.sin(a), 0.0, -dist * np.cos(a)])


def _grid_mesh(P, closed_u=True):
    """P: (rows, cols, 3) vertex grid; quads between neighbours; columns wrap if closed_u."""
    R, C = P.shape[:2]; idx = np.arange(R * C).reshape(R, C); f = []
    for r in range(R - 1):
        for c in range(C if closed_u else C - 1):
            a, b, cc, d = idx[r, c], idx[r, (c + 1) % C], idx[r + 1, (c + 1) % C], idx[r + 1, c]
            f += [[a, b, cc], [a, cc, d]]
    return trimesh.Trimesh(P.reshape(-1, 3), np.array(f), process=False)


def _orient(m, inward_point=None):
    """Make faces point away from the volume (or towards inward_point for open shells seen from inside)."""
    m.merge_vertices()
    if m.is_watertight: m.fix_normals(); return m
    if inward_point is not None:
        c = m.triangles_center; to = np.asarray(inward_point) - c
        if (np.einsum("ij,ij->i", m.face_normals, to) < 0).mean() > 0.5: m.invert()
    return m


def ground(L, q):
    """Terrain skirt: flat (base_y) out to `flat_radius`, then rolling rise to `rise` m at the outer radius."""
    s = _seed(L); r0, r1 = L.get("radius", [0, 450]); flat = L.get("flat_radius", 60); rise = L.get("rise", 12)
    seg = q["ring_segments"]; rings = q["ground_rings"]
    rs = np.r_[0.0, flat * 0.5, flat, flat + (r1 - flat) * (np.linspace(0, 1, rings) ** 1.6)[1:]]
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False); A, Rr = np.meshgrid(a, rs)
    t = np.clip((Rr - flat) / (r1 - flat), 0, 1)
    n = fbm3(np.sin(A) * Rr / 60, np.cos(A) * Rr / 60, s * 0.37, s, 4)
    y = L.get("base_y", -0.6) + rise * t ** 1.4 + L.get("roughness", 4) * (n - 0.5) * np.clip(t * 3, 0, 1)
    y = np.vstack([y, np.full((1, seg), L.get("base_y", -0.6) - 12)])  # skirt: outer rim drops below ground (no open edge)
    Rr = np.vstack([Rr, Rr[-1:] + 2]); A = np.vstack([A, A[-1:]])
    P = np.stack([Rr * np.sin(A), y, -Rr * np.cos(A)], -1)
    m = _grid_mesh(P); m.update_faces(m.nondegenerate_faces()); return _orient(m, inward_point=[0, 1e4, 0])


def mountain_ring(L, q):
    """Closed ridge all the way round (inner slope, ridge, outer slope, buried base): no visible backs or gaps."""
    s = _seed(L); r = L.get("radius", 400); d = L.get("depth", 60); hmin, hmax = L.get("height", [60, 140]); base = L.get("base_y", -10)
    seg = q["ring_segments"]; rng = np.random.default_rng(s)
    a = np.linspace(0, 2 * np.pi, seg, endpoint=False)
    n = fbm3(np.cos(a) * L.get("frequency", 2.2), np.sin(a) * L.get("frequency", 2.2), s * 0.11, s, 5)
    n = (n - n.min()) / (np.ptp(n) + 1e-6)
    h = hmin + (hmax - hmin) * n ** L.get("sharpness", 1.6) * rng.uniform(0.85, 1.15, seg)
    jag = rng.uniform(-0.12, 0.12, (5, seg)) * d
    prof = [(r - d, base), (r - 0.45 * d, 0.55), (r, 1.0), (r + 0.45 * d, 0.6), (r + d, base)]
    rows = []
    for k, (rr, yy) in enumerate(prof):
        y = np.full(seg, yy) if yy == base else h * yy * rng.uniform(0.9, 1.08, seg)
        R = rr + jag[k]; rows.append(np.stack([R * np.sin(a), y, -R * np.cos(a)], -1))
    m = _grid_mesh(np.array(rows)); return _orient(m, inward_point=[0, 0, 0])


def _spire(rng, h, rb, sides=7):
    fr = [0.0, 0.3, 0.55, 0.8, 1.0]; prof = [1.0, 0.78, 0.55, 0.32, 0.07]
    lean = rng.uniform(-0.12, 0.12, 2) * h; P = []
    for f, p in zip(fr, prof):
        a = np.linspace(0, 2 * np.pi, sides, endpoint=False) + rng.uniform(0, 0.4)
        rad = rb * p * rng.uniform(0.75, 1.2, sides)
        P.append(np.stack([rad * np.cos(a) + lean[0] * f * f, np.full(sides, f * h - 3), rad * np.sin(a) + lean[1] * f * f], -1))
    P = np.array(P); m = _grid_mesh(P); top = len(m.vertices)
    v = np.vstack([m.vertices, [[lean[0], h + 1.5, lean[1]]]]); last = np.arange((len(fr) - 1) * sides, len(fr) * sides)
    f = np.vstack([m.faces, [[last[i], last[(i + 1) % sides], top] for i in range(sides)]])
    return trimesh.Trimesh(v, f[:, ::-1], process=False)  # grid winds inward (open base: _orient cannot tell) -> flip outward


def spires(L, q):
    s = _seed(L); rng = np.random.default_rng(s); r0, r1 = L.get("radius", [120, 220]); h0, h1 = L.get("height", [25, 70])
    n = max(1, int(round(L.get("count", 12) * q["density"]))); az = L.get("azimuth_deg", [0, 360]); parts = []
    for i in range(n):
        h = rng.uniform(h0, h1); m = _spire(rng, h, h * rng.uniform(0.12, 0.2))
        m = _orient(m); m.apply_translation(polar(rng.uniform(*az), rng.uniform(r0, r1))); parts.append(m)
    return trimesh.util.concatenate(parts)


def _box(w, h, d, x=0, y=0, z=0):
    b = trimesh.creation.box([w, h, d]); b.apply_translation([x, y + h / 2, z]); return b


def _cyl(r, h, x=0, y=0, z=0, sections=8):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])); c.apply_translation([x, y + h / 2, z]); return c


def factory(L, q):
    """Modular factory in local space (front faces the arena = +z after the node's yaw). Detail by quality, or per layer
    "detail" (0..3; overrides the quality's level)."""
    rng = np.random.default_rng(_seed(L)); k = L.get("scale", 1.0); det = int(L.get("detail", q["factory_detail"]))
    hw, hh, hd = rng.uniform(34, 48) * k, rng.uniform(14, 22) * k, rng.uniform(20, 28) * k
    parts = [_box(hw, hh + 4, hd, y=-4)]
    nt = 1 + det + (rng.random() > 0.5)
    for i in range(nt):
        tx = (i - (nt - 1) / 2) * hw / max(nt, 1); th = rng.uniform(28, 55) * k; tw = rng.uniform(7, 11) * k
        parts.append(_box(tw, th + 4, tw, tx, -4, -hd * 0.15))
        if det >= 1: parts.append(_box(tw * 0.6, th * 0.18, tw * 0.6, tx, th, -hd * 0.15))  # setback top
    nc = 2 + det; tops = []
    for i in range(nc):
        cx = rng.uniform(-hw / 2, hw / 2); cz = -hd * rng.uniform(0.3, 0.5); ch = rng.uniform(40, 72) * k; cr = rng.uniform(1.6, 2.8) * k
        parts += [_cyl(cr, ch + 4, cx, -4, cz), _cyl(cr * 1.35, 2.2 * k, cx, ch - 2 * k, cz)]
        tops.append([cx, ch + 0.3 * k, cz, cr])
    if det >= 1 and nt > 1:
        parts.append(_box(hw * 0.8, 2.2 * k, 2.2 * k, 0, hh * 1.5, -hd * 0.15))  # pipe bridge between towers
    m = trimesh.util.concatenate(parts); m.metadata["chimney_tops"] = tops  # local [x, y, z, radius] (Stage 4 smoke)
    return m


def skyline(L, q):
    """Industrial city band along an azimuth range (one merged mesh)."""
    rng = np.random.default_rng(_seed(L)); r = L.get("radius", 300); a0, a1 = L.get("azimuth_deg", [-60, 60])
    h0, h1 = L.get("height", [18, 60]); n = max(3, int(round(L.get("count", 24) * q["density"]))); parts = []
    for i in range(n):
        az = a0 + (a1 - a0) * (i + rng.uniform(0.1, 0.9)) / n; w, d, h = rng.uniform(8, 22), rng.uniform(8, 22), rng.uniform(h0, h1)
        m = _box(w, h + 5, d, y=-5)
        if L.get("setbacks"):  # stepped high-rise: 1-2 narrower tiers on top (silhouette reads at distance)
            y_, ww, dd = h, w, d
            for _ in range(int(rng.integers(0, 3))):
                ww, dd = ww * rng.uniform(0.55, 0.8), dd * rng.uniform(0.55, 0.8); th = h * rng.uniform(0.15, 0.35)
                m = trimesh.util.concatenate([m, _box(ww, th, dd, y=y_ - 0.5)]); y_ += th - 0.5
            if rng.random() < L.get("spikes", 0.0):  # alien spire top: a sharp faceted cone (strong silhouette)
                sp = trimesh.creation.cone(radius=min(ww, dd) * 0.5, height=h * rng.uniform(0.25, 0.6), sections=4)
                sp.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])); sp.apply_translation([0, y_ - 0.5, 0]); m = trimesh.util.concatenate([m, sp])
            elif rng.random() < L.get("masts", 0.0): m = trimesh.util.concatenate([m, _cyl(0.5, h * rng.uniform(0.15, 0.3), 0, y_ - 0.5, 0, 5)])
        elif rng.random() < 0.35: m = trimesh.util.concatenate([m, _cyl(rng.uniform(1, 2), h * 1.4 + 5, w * 0.25, -5, 0, 6)])
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-az), [0, 1, 0]))
        m.apply_translation(polar(az, r + rng.uniform(-25, 25))); parts.append(m)
    return trimesh.util.concatenate(parts)


def townscape(L, q):
    """Stage 7: rings of distant town houses (walls OR gable roofs: "part" = walls | roofs, same seed -> they line up)
    so a town square continues into a town instead of an empty plain. radius [r0, r1], height [lo, hi], count per ring."""
    rng = np.random.default_rng(int(L.get("seed", 1)) * 7919 + 17)  # seed only (not the id): walls + roofs layers line up
    r0, r1 = L.get("radius", [60, 160]); h0, h1 = L.get("height", [8, 16]); part = L.get("part", "walls")
    a0, a1 = L.get("azimuth_deg", [0, 360]); parts = []; ring = 0; r = r0
    while r < r1:
        n = max(6, int(round(L.get("count", 40) * q["density"] * r / r0 * (a1 - a0) / 360)))
        for i in range(n):
            az = a0 + (a1 - a0) * (i + rng.uniform(0.15, 0.85)) / n; w, d = rng.uniform(8, 14), rng.uniform(8, 12); h = rng.uniform(h0, h1) * (1 + 0.15 * ring)
            rh = min(w, d) * rng.uniform(0.45, 0.7); rr = r + rng.uniform(-3, 3)
            if part == "walls": m = _box(w, h + 5, d, y=-5)
            else: m = trimesh.convex.convex_hull(np.array([[-w / 2 - .3, h, -d / 2 - .3], [w / 2 + .3, h, -d / 2 - .3], [w / 2 + .3, h, d / 2 + .3], [-w / 2 - .3, h, d / 2 + .3], [-w / 2 - .3, h + rh, 0], [w / 2 + .3, h + rh, 0]]))
            m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-az), [0, 1, 0])); m.apply_translation(polar(az, rr)); parts.append(m)
        r += 14 + 4 * ring; ring += 1
    return trimesh.util.concatenate(parts)


def ring_structure(L, q):
    """Distant sci-fi megastructure: a tilted ring (closed torus) held by tapered pylons from the ground, at
    azimuth/distance. Keys: radius, tube, elevation (ring centre height), tilt_deg, pylons, seed. Local mesh (placed by
    environment.py like a factory), closed parts only."""
    rng = np.random.default_rng(_seed(L)); R = L.get("radius", 60.0); r = L.get("tube", 3.0); yc = L.get("elevation", 90.0)
    tilt = np.radians(L.get("tilt_deg", 12)); nu, nv = max(24, int(48 * q["density"])), 8
    u, v = np.meshgrid(np.linspace(0, 2 * np.pi, nu, endpoint=False), np.linspace(0, 2 * np.pi, nv, endpoint=False), indexing="ij")
    x = (R + r * np.cos(v)) * np.cos(u); y = r * np.sin(v); z = (R + r * np.cos(v)) * np.sin(u)
    P = np.stack([x, y, z], -1).reshape(-1, 3); ct, st = np.cos(tilt), np.sin(tilt)
    P = np.c_[P[:, 0], P[:, 1] * ct - P[:, 2] * st, P[:, 1] * st + P[:, 2] * ct] + [0, yc, 0]
    idx = np.arange(nu * nv).reshape(nu, nv); F = []
    for a in range(nu):
        for b in range(nv):
            p0, p1, p2, p3 = idx[a, b], idx[(a + 1) % nu, b], idx[(a + 1) % nu, (b + 1) % nv], idx[a, (b + 1) % nv]; F += [[p0, p1, p2], [p0, p2, p3]]
    ring = trimesh.Trimesh(P, F, process=True); ring.fix_normals(); parts = [ring]
    for k in range(int(L.get("pylons", 3))):  # pylons from below the horizon up to the ring
        a = 2 * np.pi * (k + 0.5) / L.get("pylons", 3) + rng.uniform(-0.2, 0.2); px, pz = R * 0.9 * np.cos(a), R * 0.9 * np.sin(a)
        top = yc + (-pz * st) * 1.0 - r; m = _spire(rng, top + 12, max(4.0, R * 0.08)); m.apply_translation([px, -12, pz * ct]); parts.append(m)
    hub = trimesh.creation.icosphere(subdivisions=1, radius=r * 2.2); hub.apply_translation([0, yc, 0]); parts.append(hub)
    return trimesh.util.concatenate(parts)


def hover_satellites(L, q):
    """Alien satellites hovering in the distance (silhouettes, one merged mesh): angular saucer bodies, a dangling
    spike or mast, asymmetric fins. radius [r0, r1], elevation [y0, y1], size [s0, s1] (saucer diameter), count."""
    rng = np.random.default_rng(_seed(L)); r0, r1 = L.get("radius", [200, 500]); y0, y1 = L.get("elevation", [50, 140]); s0, s1 = L.get("size", [10, 26])
    n = max(2, int(round(L.get("count", 12) * q["density"]))); parts = []
    for i in range(n):
        d = rng.uniform(s0, s1); r = d / 2; k = int(rng.choice([5, 6, 7, 8])); a = np.linspace(0, 2 * np.pi, k, endpoint=False)
        rim = np.c_[r * np.cos(a), np.zeros(k), r * np.sin(a)]
        body = trimesh.convex.convex_hull(np.vstack([rim, [[0, r * rng.uniform(0.35, 0.7), 0], [0, -r * rng.uniform(0.25, 0.5), 0]]]))
        sp = trimesh.creation.cone(radius=r * 0.18, height=r * rng.uniform(1.0, 2.2), sections=4); sp.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        sp.apply_translation([0, -r * 0.3, 0]); bits = [body, sp]
        if rng.random() < 0.6:
            mast = _cyl(r * 0.05, r * rng.uniform(0.6, 1.4), rng.uniform(-r, r) * 0.3, r * 0.4, 0, 4); bits.append(mast)
        for f in range(int(rng.integers(1, 3))):  # fins / wings at odd angles
            fin = _box(r * rng.uniform(0.6, 1.2), r * 0.08, r * 0.35); fin.apply_transform(trimesh.transformations.rotation_matrix(rng.uniform(-0.6, 0.6), [0, 0, 1]))
            fin.apply_translation([r * rng.choice([-0.8, 0.8]), 0, 0]); bits.append(fin)
        m = trimesh.util.concatenate(bits); m.apply_transform(trimesh.transformations.rotation_matrix(rng.uniform(-0.25, 0.25), [1, 0, 0]) @ trimesh.transformations.rotation_matrix(rng.uniform(0, 2 * np.pi), [0, 1, 0]))
        m.apply_translation(polar(rng.uniform(0, 360), rng.uniform(r0, r1)) + np.array([0, rng.uniform(y0, y1), 0])); parts.append(m)
    return trimesh.util.concatenate(parts)


def _hull_x(sections):
    """Convex hull through cross-sections [(x, half_width, half_height_top, half_height_bottom)] along x."""
    pts = []
    for x, w, ht, hb in sections:
        pts += [[x, ht, -w * 0.55], [x, ht, w * 0.55], [x, ht * 0.25, -w], [x, ht * 0.25, w], [x, -hb, -w * 0.6], [x, -hb, w * 0.6]]
    return trimesh.convex.convex_hull(np.array(pts))


def mothership(L, q):
    """Alien capital ship hovering in the distance (side-on silhouette): long angular hull with a pointed bow (+x),
    stepped under-decks and hanging gear, a raised spine deck, a tall tilted fin with an emblem plate, turret towers
    with antennae. part = "hull" (dark body) | "lights" (emissive strips, windows, emblem, beacons) - same seed, so the
    two layers line up (two materials, two draw calls). Local mesh, placed by azimuth/distance like a factory;
    length (m), elevation (m above the arena), heading_deg (turn about y), local +z faces the arena."""
    rng = np.random.default_rng(_seed(dict(L, id=L.get("ship_id", "mothership")))); Ln = L.get("length", 170.0); y0 = L.get("elevation", 240.0)
    W, H = Ln * 0.11, Ln * 0.045; part = L.get("part", "hull"); hull, lights = [], []
    hull.append(_hull_x([(-Ln * 0.5, W * 0.55, H * 0.8, H * 0.6), (-Ln * 0.3, W, H, H * 0.8), (Ln * 0.15, W * 0.85, H * 0.8, H * 0.7), (Ln * 0.5, W * 0.06, H * 0.1, H * 0.08)]))
    for k, (x0, x1, dy, sc) in enumerate(((-0.42, 0.18, -1.0, 0.75), (-0.33, 0.02, -1.7, 0.55), (-0.2, -0.05, -2.3, 0.35))):  # stepped under-decks
        b = _hull_x([(Ln * x0, W * sc, H * 0.4, H * 0.4), (Ln * x1, W * sc * 0.9, H * 0.4, H * 0.4), (Ln * x1 + Ln * 0.06, W * sc * 0.2, H * 0.1, H * 0.1)]); b.apply_translation([0, H * dy, 0]); hull.append(b)
    for k in range(int(rng.integers(4, 8))):  # hanging gear / antennas under the hull
        x = rng.uniform(-0.4, 0.2) * Ln; c = _cyl(rng.uniform(0.6, 1.4), H * rng.uniform(0.8, 1.8), x, -H * 2.2 - H * 1.6, rng.uniform(-W, W) * 0.4, 5); hull.append(c)
    hull.append(_box(Ln * 0.5, H * 0.45, W * 0.9, -Ln * 0.08, H * 0.75, 0))  # spine deck
    fx = -Ln * rng.uniform(0.12, 0.2); fh = Ln * 0.3; fl = Ln * 0.16; lean = Ln * 0.08  # tilted fin (leans back)
    fin = trimesh.convex.convex_hull(np.array([[fx - fl / 2, H, -1.2], [fx + fl / 2, H, -1.2], [fx - fl / 2, H, 1.2], [fx + fl / 2, H, 1.2],
                                               [fx - fl * 0.55 - lean, H + fh, -1.0], [fx + fl * 0.3 - lean, H + fh, -1.0], [fx - fl * 0.55 - lean, H + fh, 1.0], [fx + fl * 0.3 - lean, H + fh, 1.0]]))
    hull.append(fin); cap = _box(fl * 1.05, fh * 0.05, 3.4, fx - lean - fl * 0.12, H + fh, 0); hull.append(cap)
    for k in range(int(rng.integers(3, 5))):  # turret towers with antennae + beacons
        x = rng.uniform(-0.05, 0.3) * Ln if k else -Ln * 0.38; r = rng.uniform(2.0, 3.5); h1 = rng.uniform(4, 9)
        hull += [_cyl(r, h1, x, H, 0, 6), _cyl(r * 1.6, 1.0, x, H + h1, 0, 6), _cyl(0.3, rng.uniform(5, 10), x, H + h1 + 1.0, 0, 4)]
        lights.append(_box(1.0, 1.0, 1.0, x, H + h1 + 9.5, 0))
    lights.append(_box(1.4, 1.4, 1.4, fx - lean - fl * 0.1, H + fh + fh * 0.05, 0))
    for side in (-1, 1):  # light strips + window dashes along the hull, emblem plate on the fin
        for yy, x0, x1 in ((H * 0.1, -0.45, 0.3), (-H * 0.35, -0.4, 0.1)):
            for k in range(int(rng.integers(3, 6))):
                a = rng.uniform(x0, x1) * Ln; ln = rng.uniform(4, 14); lights.append(_box(ln, 0.7, 0.4, a, yy, side * W * 0.93))
        e = trimesh.convex.convex_hull(np.array([[fx - lean * 0.5 - fl * 0.18, H + fh * 0.7, 0], [fx - lean * 0.5 + fl * 0.18, H + fh * 0.7, 0], [fx - lean * 0.35, H + fh * 0.25, 0],
                                                 [fx - lean * 0.5 - fl * 0.18, H + fh * 0.7, side * 0.4], [fx - lean * 0.5 + fl * 0.18, H + fh * 0.7, side * 0.4], [fx - lean * 0.35, H + fh * 0.25, side * 0.4]]))
        e.apply_translation([0, 0, side * 1.2]); lights.append(e)
    m = trimesh.util.concatenate(hull if part == "hull" else lights)
    m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(L.get("heading_deg", 0)), [0, 1, 0]) @ trimesh.transformations.rotation_matrix(np.radians(L.get("roll_deg", -3)), [1, 0, 0]))
    m.apply_translation([0, y0, 0]); return m


GENERATORS = dict(ground=ground, mountain_ring=mountain_ring, spires=spires, skyline=skyline, factory=factory, townscape=townscape, ring_structure=ring_structure, hover_satellites=hover_satellites, mothership=mothership)
DEFAULTS = {  # material kind, colour, tile size per layer type (overridable per layer: material_type/color/tile_m)
    "ground": ("dirt", [0.16, 0.17, 0.14], 14.0), "mountain_ring": ("rock", [0.2, 0.21, 0.19], 40.0),
    "spires": ("rock", [0.17, 0.18, 0.16], 14.0), "skyline": ("factory_facade", [0.16, 0.17, 0.17], 12.0),
    "factory": ("factory_facade", [0.17, 0.18, 0.18], 10.0), "townscape": ("plaster", [0.72, 0.67, 0.58], 6.0),
    "ring_structure": ("machinery_panel", [0.3, 0.3, 0.32], 16.0),
    "hover_satellites": ("hull_plating", [0.12, 0.1, 0.16], 12.0),
    "mothership": ("hull_plating", [0.16, 0.1, 0.2], 14.0),
}
