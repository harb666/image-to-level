"""Distant environment geometry (no collision, low-poly, closed silhouettes). Used by environment.py.

Every generator is deterministic from its layer `id` + `seed`, so editing one layer in level.json never changes the
others. Level azimuth convention: 0° = north (-z), 90° = east (+x). Layer types:
  ground        polar terrain skirt from under the arena out to the horizon (rises towards the mountains)
  mountain_ring closed 360° ridge: inner slope, ridge, outer slope, base below ground (no open backs)
  spires        scattered rock spires (tapered, jittered prisms, closed caps)
  skyline       band of industrial blocks + chimneys along an azimuth range
  factory       one modular factory complex (hall, towers, chimneys, pipe bridge) at azimuth/distance
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
    return trimesh.Trimesh(v, f, process=False)


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
    """Modular factory in local space (front faces the arena = +z after the node's yaw). Detail by quality."""
    rng = np.random.default_rng(_seed(L)); k = L.get("scale", 1.0); det = q["factory_detail"]
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
        if rng.random() < 0.35: m = trimesh.util.concatenate([m, _cyl(rng.uniform(1, 2), h * 1.4 + 5, w * 0.25, -5, 0, 6)])
        m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(-az), [0, 1, 0]))
        m.apply_translation(polar(az, r + rng.uniform(-25, 25))); parts.append(m)
    return trimesh.util.concatenate(parts)


GENERATORS = dict(ground=ground, mountain_ring=mountain_ring, spires=spires, skyline=skyline, factory=factory)
DEFAULTS = {  # material kind, colour, tile size per layer type (overridable per layer: material_type/color/tile_m)
    "ground": ("dirt", [0.16, 0.17, 0.14], 14.0), "mountain_ring": ("rock", [0.2, 0.21, 0.19], 40.0),
    "spires": ("rock", [0.17, 0.18, 0.16], 14.0), "skyline": ("factory_facade", [0.16, 0.17, 0.17], 12.0),
    "factory": ("factory_facade", [0.17, 0.18, 0.18], 10.0),
}
