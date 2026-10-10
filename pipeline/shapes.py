"""Stage 3 primitive library: closed, low-poly, game-ready meshes (local space, base at y=0, centred on x/z).
All return trimesh.Trimesh; every solid is closed (no open backs). Sizes are o["size"] = [w (x), h (y), d (z)].

  box + "bevel": m      chamfered box (edges catch light, silhouette less "primitive")
  railing               posts every ~1.5 m + top & mid rail along x (w = length, h = height, d = thickness)
  ibeam                 I-section girder along x
  rock                  seeded jittered boulder filling the size box ("seed")
  cliff                 jagged rock wall along x, thick base, closed
  arch                  gateway/tunnel along z: two piers + lintel, opening = "opening" fraction of w (passable)
  pipe_elbow            90° bend of radius w/2 tube (h = bend radius), capped ends
  vent                  box with horizontal louvre slats on the +z face
  tank                  vertical cylinder with domed top
  machinery             seeded cluster of boxes/cylinders filling the size box ("seed")
  hip_roof              four-sided roof (hips at "pitch", default 45°); "overhang" m beyond the size box   (Stage 7)
  round_arch            gateway along z with a semicircular opening ("opening" fraction of w); passable    (Stage 7)
  battlement            ring of merlons round a w x d top (h = merlon height, "thickness")                  (Stage 7)
  wedge                 buttress / sloped block: full height at -z, 0 at +z                                  (Stage 7)
  stream                liquid leaving an outlet: origin = outlet centre, local +z = outlet direction; gravity arc
                        down to y = -size[1] (drop incl. submersion); "section" circle | rect | sheet, size[0] = outlet
                        width (diameter), size[2] = section depth; "speed" m/s, "pitch" deg (-90 = vertical drain),
                        "inset" m started inside the opening (covers the mouth). Closed, few triangles.      (Stage 8)
  channel               open U trough along local z (rectangular drain / spillway lip): floor + two side walls (Stage 8)
  berm                  earth cover over a tunnel: top from "heights" grid ("xs", "zs"), flat base (Stage 9)
  rock_arch             natural stone arch along x (span w, top h, depth d), flared buried legs (Stage 9)
  cave                  rock mass with a walk-in cave on its +z face, flat floor at y=0, closed back (Stage 9)
  overhang              rock shelf with a lip jutting forward (+z) over a recess (Stage 9)
  frustum               tapered block, full footprint on top, "bottom_scale" at the base; rect or n-gon (Stage 9)
"""
import math
import numpy as np, trimesh
from trimesh.transformations import rotation_matrix


def bevel_box(w, h, d, b):
    """Chamfered box: convex hull of each corner pushed in by b along its three axes (44 triangles)."""
    b = max(0.0, min(b, 0.4 * min(w, h, d)))
    if b <= 1e-4:
        m = trimesh.creation.box([w, h, d]); m.apply_translation([0, h / 2, 0]); return m
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                cx, cy, cz = sx * w / 2, sy * h / 2, sz * d / 2
                pts += [[cx - sx * b, cy, cz], [cx, cy - sy * b, cz], [cx, cy, cz - sz * b]]
    m = trimesh.convex.convex_hull(np.array(pts)); m.apply_translation([0, h / 2, 0]); return m


def _box(w, h, d, x=0, y=0, z=0, b=0):
    m = bevel_box(w, h, d, b); m.apply_translation([x, y, z]); return m


def _cyl(r, h, x=0, y=0, z=0, sections=10, axis="y"):
    c = trimesh.creation.cylinder(radius=r, height=h, sections=sections)
    if axis == "y": c.apply_transform(rotation_matrix(-np.pi / 2, [1, 0, 0])); c.apply_translation([x, y + h / 2, z])
    elif axis == "x": c.apply_transform(rotation_matrix(np.pi / 2, [0, 1, 0])); c.apply_translation([x, y, z])
    return c


def railing(w, h, d, o):
    n = max(2, int(round(w / o.get("post_spacing", 1.5))) + 1); t = max(d, 0.05)
    parts = [_box(t, h, t, -w / 2 + i * w / (n - 1) * (1 - 1e-3) + t / 2 * (1 if i == 0 else -1 if i == n - 1 else 0)) for i in range(n)]
    parts += [_box(w, t * 1.2, t * 1.4, y=h - t * 1.2), _box(w, t * 0.8, t, y=h * 0.5)]
    return trimesh.util.concatenate(parts)


def rail_posts(points, spacing=1.6):
    """Post base points along a railing polyline (local coords, each ON its supporting surface): every vertex
    (corners, slope changes) plus evenly spaced posts between them (<= spacing apart, measured in plan)."""
    P = np.asarray(points, float); out = [P[0]]
    for a, b in zip(P[:-1], P[1:]):
        n = max(1, int(math.ceil(math.hypot(b[0] - a[0], b[2] - a[2]) / spacing - 1e-6)))
        out += [a + (b - a) * k / n for k in range(1, n + 1)]
    return np.array(out)


def _beam(a, b, t, h):
    """Box of cross-section t (wide) x h (tall) from point a to point b, kept upright (no roll) on slopes."""
    a, b = np.asarray(a, float), np.asarray(b, float); v = b - a; L = np.linalg.norm(v)
    if L < 1e-6: return None
    m = trimesh.creation.box([t, h, L]); f = v / L; s = np.cross([0, 1, 0], f)
    s = s / np.linalg.norm(s) if np.linalg.norm(s) > 1e-6 else np.array([1.0, 0, 0]); u = np.cross(f, s)
    T = np.eye(4); T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = s, u, f, (a + b) / 2; m.apply_transform(T); return m


def rail_run(w, h, d, o):
    """Engineered safety railing along a polyline that follows the walking surface (flat, sloped, cornered).
    o["points"]: base points in the object's local frame, each ON the supporting surface. Posts stay vertical and
    are sunk 2 cm into the floor; top rail, mid rail and kick plate follow the slope continuously and meet at the
    corner posts (extended by half a post: closed joints). size = [length, height, post thickness]."""
    P = np.asarray(o.get("points") or [[-w / 2, 0, 0], [w / 2, 0, 0]], float); t = max(d, 0.05); posts = rail_posts(P, o.get("post_spacing", 1.6)); parts = []
    for p in posts: parts.append(_box(t, h + 0.02, t, p[0], p[1] - 0.02, p[2]))
    for a, b in zip(P[:-1], P[1:]):
        f = (b - a) / max(np.linalg.norm(b - a), 1e-6) * t / 2  # half-post overlap at each end: no gaps at corners
        for dy, th, tw in ((h - 0.045, 0.09, t * 1.3), (h * 0.5, 0.06, t * 0.8)):
            parts.append(_beam(a - f + [0, dy, 0], b + f + [0, dy, 0], tw, th))
        if o.get("kick", True): parts.append(_beam(a + [0, 0.11, 0], b + [0, 0.11, 0], t * 0.45, 0.14))
    return trimesh.util.concatenate([p for p in parts if p is not None])


def ibeam(w, h, d, o):
    f = max(h * 0.12, 0.04); web = max(d * 0.18, 0.03)
    return trimesh.util.concatenate([_box(w, f, d), _box(w, f, d, y=h - f), _box(w, h - 2 * f, web, y=f)])


def rock(w, h, d, o):
    rng = np.random.default_rng(int(o.get("seed", 1)))
    m = trimesh.creation.icosphere(subdivisions=1, radius=1.0)
    v = m.vertices * rng.uniform(0.72, 1.12, (len(m.vertices), 1))
    v[:, 1] = np.where(v[:, 1] < -0.3, -0.3 + (v[:, 1] + 0.3) * 0.2, v[:, 1])  # flatter buried base (order kept: no folds)
    v = (v - v.min(0)) / np.ptp(v, 0) * [w, h * 1.08, d] - [w / 2, h * 0.08, d / 2]
    return trimesh.convex.convex_hull(v) if o.get("convex", False) else trimesh.Trimesh(v, m.faces, process=True)


def cliff(w, h, d, o):
    """Rock wall along x: jagged top profile and front face, flat buried base/back, closed."""
    rng = np.random.default_rng(int(o.get("seed", 2))); n = max(4, int(w / o.get("step", 3.0)))
    xs = np.linspace(-w / 2, w / 2, n + 1); top = h * rng.uniform(0.7, 1.0, n + 1); top[[0, -1]] *= 0.85
    fz = d / 2 * rng.uniform(0.75, 1.0, n + 1); mz = d * rng.uniform(0.05, 0.25, n + 1)  # front & mid-front depth
    rows = [np.c_[xs, np.full(n + 1, -1.0), fz],                      # front base (buried)
            np.c_[xs, top * rng.uniform(0.4, 0.6, n + 1), fz * 0.9],  # front ledge
            np.c_[xs, top, mz],                                        # ridge
            np.c_[xs, top * 0.95, np.full(n + 1, -d / 2)],             # back top
            np.c_[xs, np.full(n + 1, -1.0), np.full(n + 1, -d / 2)]]   # back base
    P = np.array(rows); R = len(rows); idx = np.arange(R * (n + 1)).reshape(R, n + 1); f = []
    for r in range(R):  # ring closes back to the front base (bottom face)
        r2 = (r + 1) % R
        for c in range(n):
            a, b_, cc, dd = idx[r, c], idx[r, c + 1], idx[r2, c + 1], idx[r2, c]; f += [[a, cc, b_], [a, dd, cc]]
    ends = [idx[:, 0], idx[:, -1]]
    for k, e in enumerate(ends):  # cap both ends with fans
        for i in range(1, R - 1): f.append([e[0], e[i], e[i + 1]] if k else [e[0], e[i + 1], e[i]])
    m = trimesh.Trimesh(P.reshape(-1, 3), np.array(f), process=True); m.fix_normals(); return m


def arch(w, h, d, o):
    """Gate/tunnel along z. Opening width = opening*w, height = opening_h*h; piers + lintel (+ optional floor)."""
    ow = w * o.get("opening", 0.6); oh = h * o.get("opening_h", 0.75); pw = (w - ow) / 2
    parts = [_box(pw, h, d, -(ow + pw) / 2, b=o.get("bevel", 0)), _box(pw, h, d, (ow + pw) / 2, b=o.get("bevel", 0)),
             _box(ow + 0.02, h - oh, d, y=oh, b=o.get("bevel", 0))]
    return trimesh.util.concatenate(parts)


def pipe_elbow(w, h, d, o):
    """Quarter torus: tube radius w/2, bend radius h; starts along +z at origin, turns to +x. Capped."""
    r, R, seg, sides = w / 2, max(h, w), int(o.get("segments", 6)), int(o.get("sections", 10))
    ang = np.linspace(0, np.pi / 2, seg + 1); phi = np.linspace(0, 2 * np.pi, sides, endpoint=False); V = []
    for a in ang:
        cx, cz = R - R * np.cos(a), R * np.sin(a); tx, tz = np.sin(a), np.cos(a)  # centre & tangent
        nx, nz = tz, -tx
        for p in phi: V.append([cx + r * np.cos(p) * nx, r * np.sin(p) + r, cz + r * np.cos(p) * nz])
    V = np.array(V); f = []
    for i in range(seg):
        for j in range(sides):
            a, b_, c, dd = i * sides + j, i * sides + (j + 1) % sides, (i + 1) * sides + (j + 1) % sides, (i + 1) * sides + j
            f += [[a, b_, c], [a, c, dd]]
    c0 = len(V); c1 = c0 + 1; V = np.vstack([V, V[:sides].mean(0), V[-sides:].mean(0)])
    for j in range(sides):
        f += [[c0, (j + 1) % sides, j], [c1, seg * sides + j, seg * sides + (j + 1) % sides]]
    m = trimesh.Trimesh(V, np.array(f), process=True); m.fix_normals(); return m


def vent(w, h, d, o):
    n = max(3, int(h / 0.18)); parts = [_box(w, h, d * 0.7, z=-d * 0.15)]
    frame = 0.08 * min(w, h)
    parts += [_box(w, frame, d, y=0), _box(w, frame, d, y=h - frame), _box(frame, h, d, -w / 2 + frame / 2), _box(frame, h, d, w / 2 - frame / 2)]
    for i in range(n):
        y = frame + (h - 2 * frame) * (i + 0.5) / n
        s = _box(w - 2 * frame, 0.035, d * 0.35); s.apply_transform(rotation_matrix(np.radians(-30), [1, 0, 0])); s.apply_translation([0, y, d * 0.2])
        parts.append(s)
    return trimesh.util.concatenate(parts)


def tank(w, h, d, o):
    r = min(w, d) / 2; body = _cyl(r, h - r * 0.5, sections=int(o.get("sections", 12)))
    dome = trimesh.creation.icosphere(subdivisions=1, radius=r); dome.vertices[:, 1] = np.maximum(dome.vertices[:, 1], 0) * 0.5
    dome.apply_translation([0, h - r * 0.5, 0])
    ring = _cyl(r * 1.05, 0.15 * r, y=h * 0.3, sections=int(o.get("sections", 12)))
    return trimesh.util.concatenate([body, trimesh.convex.convex_hull(dome.vertices), ring])


def machinery(w, h, d, o):
    rng = np.random.default_rng(int(o.get("seed", 3))); parts = [_box(w, h * 0.45, d, b=0.05 * min(w, d))]
    for i in range(int(rng.integers(2, 4))):
        bw, bd = w * rng.uniform(0.25, 0.45), d * rng.uniform(0.3, 0.6); bh = h * rng.uniform(0.3, 0.55)
        parts.append(_box(bw, bh, bd, rng.uniform(-1, 1) * (w - bw) / 2, h * 0.45, rng.uniform(-1, 1) * (d - bd) / 2, b=0.04 * bw))
    r = min(w, d) * 0.12; parts.append(_cyl(r, h * 0.55, rng.uniform(-0.3, 0.3) * w, h * 0.45, rng.uniform(-0.3, 0.3) * d))
    return trimesh.util.concatenate(parts)


def hip_roof(w, h, d, o):
    """Hip roof over w x d (+ overhang): ridge along the longer side, 4 sloped faces. Closed (flat underside)."""
    ov = o.get("overhang", 0.0); w2, d2 = w / 2 + ov, d / 2 + ov
    if w >= d: r = max(0.0, w2 - d2 * o.get("hip", 1.0)); ridge = [[-r, h, 0], [r, h, 0]]
    else: r = max(0.0, d2 - w2 * o.get("hip", 1.0)); ridge = [[0, h, -r], [0, h, r]]
    return trimesh.convex.convex_hull(np.array([[-w2, 0, -d2], [w2, 0, -d2], [w2, 0, d2], [-w2, 0, d2]] + ridge))


def round_arch(w, h, d, o):
    """Gate along z with a round-topped opening: two piers + an arch ring of convex segments (each closed)."""
    ow = w * o.get("opening", 0.55); r = ow / 2; spring = max(0.0, min(h * o.get("opening_h", 0.75) - r, h - r - 0.3))
    pw = (w - ow) / 2; parts = [_box(pw, h, d, -(ow + pw) / 2), _box(pw, h, d, (ow + pw) / 2)]
    n = int(o.get("segments", 8)); top = h

    def outer(a):  # ray from the arch centre at angle a hits the rectangle [-ow/2, ow/2] x [spring, top]
        dx, dy = np.cos(a), np.sin(a); ts = []
        if abs(dx) > 1e-9: ts.append((np.sign(dx) * ow / 2) / dx)
        if dy > 1e-9: ts.append((top - spring) / dy)
        t = min(t for t in ts if t > 0); return [dx * t, spring + dy * t]
    corners = [[ow / 2, top], [-ow / 2, top]]
    for i in range(n):
        a0, a1 = np.pi * i / n, np.pi * (i + 1) / n
        pts = [[r * np.cos(a0), spring + r * np.sin(a0)], [r * np.cos(a1), spring + r * np.sin(a1)], outer(a0), outer(a1)]
        pts += [c for c in corners if np.arctan2(c[1] - spring, c[0]) > a0 + 1e-6 and np.arctan2(c[1] - spring, c[0]) < a1 - 1e-6]
        P = np.array([[x, y, z] for x, y in pts for z in (-d / 2, d / 2)])
        parts.append(trimesh.convex.convex_hull(P))
    return trimesh.util.concatenate(parts)


def battlement(w, h, d, o):
    """Merlons round the top edge of a w x d footprint (outer faces flush with the footprint)."""
    t = o.get("thickness", 0.5); mw = o.get("merlon", 0.8); parts = []
    for L, along_x, off in ((w, True, d / 2 - t / 2), (w, True, -d / 2 + t / 2), (d - 2 * t, False, w / 2 - t / 2), (d - 2 * t, False, -w / 2 + t / 2)):
        n = max(2, int(round(L / (2 * mw))))
        for i in range(n):
            c = -L / 2 + (i + 0.5) * L / n
            parts.append(_box(mw, h, t, c, 0, off) if along_x else _box(t, h, mw, off, 0, c))
    return trimesh.util.concatenate(parts)


def wedge(w, h, d, o):
    return trimesh.convex.convex_hull(np.array([[-w / 2, 0, -d / 2], [w / 2, 0, -d / 2], [-w / 2, 0, d / 2], [w / 2, 0, d / 2], [-w / 2, h, -d / 2], [w / 2, h, -d / 2]]))


def stream_path(h, o, n=None):
    """Centre-line of a stream (outlet at the origin, local +z forward): list of (point, tangent, fraction 0..1)."""
    sp = float(o.get("speed", 2.5)); p = np.radians(float(o.get("pitch", 0.0))); g = 9.81; vz, vy = sp * np.cos(p), sp * np.sin(p)
    if abs(vz) < 1e-3:  # vertical: straight column
        t_end = 1.0; pos = lambda t: np.array([0.0, -h * t, 0.0]); tan = lambda t: np.array([0.0, -1.0, 0.0])
    else:
        t_end = (vy + np.sqrt(vy * vy + 2 * g * h)) / g  # y(t) = vy t - g t^2 / 2 = -h
        pos = lambda t: np.array([0.0, vy * t - 0.5 * g * t * t, vz * t]); tan = lambda t: (lambda v: v / np.linalg.norm(v))(np.array([0.0, vy - g * t, vz]))
    n = n or (3 if abs(vz) < 1e-3 else int(o.get("segments", 8)))
    ts = t_end * (np.linspace(0, 1, n + 1) ** 1.3); out = []
    inset = float(o.get("inset", 0.2)); d0 = tan(0.0)
    out.append((-d0 * inset, d0, 0.0))
    for t in ts: out.append((pos(t), tan(t), t / t_end))
    return out


def stream(w, h, d, o):
    sec = o.get("section", "circle"); sides = int(o.get("sides", 10)) if sec == "circle" else 4
    widen, thin = float(o.get("widen", 0.2)), float(o.get("thin", 0.35)); V, rings = [], []
    for P, T, f in stream_path(h, o):
        S = np.array([1.0, 0.0, 0.0]); N = np.cross(T, S); N /= np.linalg.norm(N) or 1
        a, b = (w / 2) * (1 + widen * f), (d / 2) * (1 - thin * f)
        if sec == "circle": ang = np.linspace(0, 2 * np.pi, sides, endpoint=False); pts = [P + S * a * np.cos(q) + N * b * np.sin(q) for q in ang]
        else: pts = [P + S * sx * a + N * sy * b for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        rings.append(len(V)); V += pts
    f = []; k = sides
    for i in range(len(rings) - 1):
        for j in range(k):
            a0, a1, b0, b1 = rings[i] + j, rings[i] + (j + 1) % k, rings[i + 1] + j, rings[i + 1] + (j + 1) % k
            f += [[a0, b0, b1], [a0, b1, a1]]
    c0 = len(V); V.append(np.mean(V[rings[0]:rings[0] + k], 0)); c1 = len(V); V.append(np.mean(V[rings[-1]:rings[-1] + k], 0))
    for j in range(k):
        f += [[c0, rings[0] + (j + 1) % k, rings[0] + j], [c1, rings[-1] + j, rings[-1] + (j + 1) % k]]
    m = trimesh.Trimesh(np.array(V), np.array(f), process=True); m.fix_normals(); return m


def channel(w, h, d, o):
    t = float(o.get("wall", 0.2))
    return trimesh.util.concatenate([_box(w, t, d), _box(t, h, d, -w / 2 + t / 2), _box(t, h, d, w / 2 - t / 2)])


def berm(w, h, d, o):
    """Earth/rock cover over a tunnel (Stage 9): top surface from o["heights"] (rows along z, cols along x at o["xs"],
    o["zs"]), flat base at y=0, closed sides."""
    H = np.asarray(o.get("heights", np.full((3, 3), h)), float); nl, nw = H.shape  # flat cover of height h by default
    xs = np.asarray(o.get("xs", np.linspace(-w / 2, w / 2, nw)), float); zs = np.asarray(o.get("zs", np.linspace(-d / 2, d / 2, nl)), float)
    X, Z = np.meshgrid(xs, zs); top = np.c_[X.ravel(), H.ravel(), Z.ravel()]; bot = top.copy(); bot[:, 1] = 0.0
    V = np.vstack([top, bot]); idx = np.arange(nl * nw).reshape(nl, nw); F = []
    for i in range(nl - 1):
        for j in range(nw - 1):
            a, b, c, d_ = idx[i, j], idx[i, j + 1], idx[i + 1, j + 1], idx[i + 1, j]
            F += [[a, d_, c], [a, c, b], [a + nl * nw, c + nl * nw, d_ + nl * nw], [a + nl * nw, b + nl * nw, c + nl * nw]]
    ring = list(idx[0, :]) + list(idx[1:, -1]) + list(idx[-1, -2::-1]) + list(idx[-2:0:-1, 0])
    for k in range(len(ring)):
        a, b = ring[k], ring[(k + 1) % len(ring)]; F += [[a, b + nl * nw, b], [a, a + nl * nw, b + nl * nw]]
    m = trimesh.Trimesh(V, F, process=True); m.fix_normals(); return m


def _ring_sweep(rings, cap_start=True, cap_end=True):
    """Closed tube through a list of (n,3) rings (same n); fan caps at both ends."""
    R = len(rings); n = len(rings[0]); V = np.vstack(rings); F = []
    for r in range(R - 1):
        for k in range(n):
            a, b, c, d_ = r * n + k, r * n + (k + 1) % n, (r + 1) * n + (k + 1) % n, (r + 1) * n + k; F += [[a, b, c], [a, c, d_]]
    V = list(V)
    for r, on in ((0, cap_start), (R - 1, cap_end)):
        if not on: continue
        ci = len(V); V.append(np.mean(rings[r], 0))
        for k in range(n): F.append([ci, r * n + (k + 1) % n, r * n + k])
    m = trimesh.Trimesh(np.array(V), F, process=True); m.fix_normals(); return m


def rock_arch(w, h, d, o):
    """Natural stone arch along x: span w, top at h, depth d; legs flare, buried 1 m; seeded noise."""
    rng = np.random.default_rng(int(o.get("seed", 3))); t = o.get("thickness", max(1.2, h * 0.2)); nr, ns = 16, 8; rings = []
    for i in range(nr):
        u = i / (nr - 1); ang = np.pi * (1 - u)  # left foot -> top -> right foot
        cx, cy = (w / 2 - t * 0.7) * np.cos(ang), (h - t / 2) * np.sin(ang) - (1.0 if i in (0, nr - 1) else 0.0)
        tan = np.array([-np.sin(ang) * (w / 2), np.cos(ang) * h, 0]); tan /= np.linalg.norm(tan); nrm = np.array([-tan[1], tan[0], 0])
        flare = 1 + 0.6 * (1 - np.sin(ang)) ** 2; jit = rng.uniform(0.85, 1.15, ns)
        a = np.linspace(0, 2 * np.pi, ns, endpoint=False)
        ring = np.array([[cx, cy, 0]]) + (np.cos(a) * t / 2 * flare * jit)[:, None] * nrm + (np.sin(a) * d / 2 * flare * jit)[:, None] * np.array([0, 0, 1])
        rings.append(ring)
    return _ring_sweep(rings)


def cave(w, h, d, o):
    """Rock mass with a cave opening on its +z face going back (-z) to a closed end: annular extrusion (outer rock
    shell + inner tunnel with a flat floor at y=0); width w, height h, depth d; "opening" = inner width fraction."""
    from terrain import stitch
    rng = np.random.default_rng(int(o.get("seed", 5))); op = o.get("opening", 0.5); n = 14; rows = 7; a = np.linspace(0, np.pi, n); O, I = [], []
    for i in range(rows):
        z = d / 2 - d * i / (rows - 1); f = 1 - 0.35 * i / (rows - 1); jo = rng.uniform(0.9, 1.1, n); ji = rng.uniform(0.93, 1.07, n)
        arc = np.c_[w / 2 * np.cos(a) * jo, h * np.sin(a) * jo * (0.85 + 0.15 * f), np.full(n, z)]          # +x foot -> top -> -x foot
        O.append(np.vstack([[[w / 2, -1.0, z]], arc[1:-1], [[-w / 2, -1.0, z]]]))                       # closes along the buried base
        I.append(np.c_[w / 2 * op * f * np.cos(a) * ji, 0.02 + h * 0.62 * f * np.sin(a) * ji, np.full(n, z)])  # closes along the floor
    no, ni = len(O[0]), len(I[0]); st = no + ni; V = [p for r in range(rows) for p in list(O[r]) + list(I[r])]; F = []
    oi = lambda r, k: r * st + k; ii = lambda r, k: r * st + no + k
    for r in range(rows - 1):
        for k in range(no):
            k2 = (k + 1) % no; F += [[oi(r, k), oi(r, k2), oi(r + 1, k2)], [oi(r, k), oi(r + 1, k2), oi(r + 1, k)]]
        for k in range(ni):
            k2 = (k + 1) % ni; F += [[ii(r, k), ii(r + 1, k2), ii(r, k2)], [ii(r, k), ii(r + 1, k), ii(r + 1, k2)]]
    F += stitch([oi(0, k) for k in range(no)], np.linspace(0, 1, no, endpoint=False), [ii(0, k) for k in range(ni)], np.linspace(0, 1, ni, endpoint=False))
    cb = len(V); V.append(O[-1].mean(0)); ci = len(V); V.append(I[-1].mean(0))  # closed back
    for k in range(no): F.append([cb, oi(rows - 1, (k + 1) % no), oi(rows - 1, k)])
    for k in range(ni): F.append([ci, ii(rows - 1, k), ii(rows - 1, (k + 1) % ni)])
    m = trimesh.Trimesh(np.array(V), F, process=True); m.fix_normals(); return m


def overhang(w, h, d, o):
    """Rock shelf along x whose top lip juts forward (+z) over its base: buried base, closed, seeded."""
    rng = np.random.default_rng(int(o.get("seed", 4))); n = max(4, int(w / 2.5)); xs = np.linspace(-w / 2, w / 2, n + 1); j = lambda a, b: rng.uniform(a, b, n + 1)
    lip = d / 2 * o.get("lip", 1.0)
    rows = [np.c_[xs, np.full(n + 1, -1.0), np.full(n + 1, d * 0.05) * j(0.8, 1.2)],      # front base (set back)
            np.c_[xs, h * 0.45 * j(0.85, 1.1), d * 0.1 * j(0.5, 1.5)],                     # recess
            np.c_[xs, h * 0.72 * j(0.9, 1.05), lip * j(0.8, 1.05)],                         # lip underside
            np.c_[xs, h * j(0.9, 1.0), lip * 0.8 * j(0.85, 1.0)],                           # lip top
            np.c_[xs, h * j(0.95, 1.05), np.full(n + 1, -d / 2)],                           # back top
            np.c_[xs, np.full(n + 1, -1.0), np.full(n + 1, -d / 2)]]                         # back base
    P = np.array(rows); R = len(rows); idx = np.arange(R * (n + 1)).reshape(R, n + 1); f = []
    for r in range(R):
        r2 = (r + 1) % R
        for c in range(n):
            a, b_, cc, dd = idx[r, c], idx[r, c + 1], idx[r2, c + 1], idx[r2, c]; f += [[a, cc, b_], [a, dd, cc]]
    for k, e in enumerate([idx[:, 0], idx[:, -1]]):
        for i in range(1, R - 1): f.append([e[0], e[i], e[i + 1]] if k else [e[0], e[i + 1], e[i]])
    m = trimesh.Trimesh(P.reshape(-1, 3), np.array(f), process=True); m.fix_normals(); return m


def crystals(w, h, d, o):
    """Cluster of hexagonal crystals with pointed tips inside w x h x d (seeded), bases buried 0.3 m."""
    rng = np.random.default_rng(int(o.get("seed", 6))); parts = []
    for k in range(int(o.get("count", 7))):
        hh = h * rng.uniform(0.35, 1.0); r = min(w, d) * rng.uniform(0.07, 0.15); a = np.linspace(0, 2 * np.pi, 6, endpoint=False)
        pts = np.r_[np.c_[r * np.cos(a), np.full(6, -0.3), r * np.sin(a)], np.c_[r * np.cos(a), np.full(6, hh * 0.8), r * np.sin(a)], [[0, hh, 0]]]
        c = trimesh.convex.convex_hull(pts); c.apply_transform(rotation_matrix(rng.uniform(-0.4, 0.4), [rng.uniform(-1, 1), 0, rng.uniform(-1, 1)]))
        c.apply_translation([rng.uniform(-w / 3, w / 3), 0, rng.uniform(-d / 3, d / 3)]); parts.append(c)
    return trimesh.util.concatenate(parts)


def tube(r_top, r_bot, r_in, h, n=24, phase=0.0, rz_top=None, rz_bot=None):
    """Closed hollow ring (annulus / hollow frustum) with a vertical round hole r_in through it, base at y=0. Outer
    radius r_top at y=h, r_bot at y=0 (rz_*: elliptical z radius). Outer wall faces out, hole wall faces the axis."""
    a = np.linspace(0, 2 * np.pi, n, endpoint=False) + phase; ca, sa = np.cos(a), np.sin(a)
    rz_top = r_top if rz_top is None else rz_top; rz_bot = r_bot if rz_bot is None else rz_bot
    V = np.vstack([np.c_[r_top * ca, np.full(n, h), rz_top * sa], np.c_[r_bot * ca, np.zeros(n), rz_bot * sa],
                   np.c_[r_in * ca, np.full(n, h), r_in * sa], np.c_[r_in * ca, np.zeros(n), r_in * sa]])
    OT, OB, IT, IB = 0, n, 2 * n, 3 * n; F = []
    for i in range(n):
        j = (i + 1) % n
        F += [[OT + i, OT + j, OB + j], [OT + i, OB + j, OB + i]]   # outer wall
        F += [[IT + i, IB + j, IT + j], [IT + i, IB + i, IB + j]]   # hole wall
        F += [[OT + i, IT + j, OT + j], [OT + i, IT + i, IT + j]]   # top ring
        F += [[OB + i, OB + j, IB + j], [OB + i, IB + j, IB + i]]   # bottom ring
    m = trimesh.Trimesh(V, np.array(F), process=True); m.fix_normals(); return m


def holed(w, h, d, hole, sections=0, phase=0.0, k=1.0):
    """Block with a round vertical hole of radius `hole` through its centre, base at y=0, outline unchanged: sections 0 =
    w x d rectangle, n = regular n-gon (circumradius w/2, d/2; first corner at `phase`); k = base scale (frustum). The
    outline is resampled to a multiple of n vertices (>= 24) so the hole stays round (tube())."""
    if sections: n, sx, sz = int(sections), w / 2, d / 2
    else: n, phase, sx, sz = 4, np.pi / 4, w / 2 * np.sqrt(2), d / 2 * np.sqrt(2)
    m = n * int(np.ceil(24 / n)); a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    f = np.cos(np.pi / n) / np.cos(np.mod(a, 2 * np.pi / n) - np.pi / n)  # polygon radius along each ray (1 at corners)
    if hole >= min(sx, sz) * np.cos(np.pi / n) - 0.05: raise ValueError(f"hole r {hole} does not fit inside a {w} x {d} outline")
    return tube(sx * f, sx * f * k, float(hole), h, m, phase, sz * f, sz * f * k)


def frustum(w, h, d, o):
    """Tapered block: full w x d footprint at the top (y=h), "bottom_scale" x at the base (y=0). "sections" 0 = rectangular,
    n = regular n-gon (flats facing the axes, like the rotated platform cylinders). Closed (Stage 9 sky-pylon underframes).
    "hole": r -> a round vertical hole of radius r through it (elevator shafts)."""
    k = o.get("bottom_scale", 0.5); n = int(o.get("sections", 0) or 0)
    if o.get("hole"): return holed(w, h, d, float(o["hole"]), n, np.pi / n if n else 0.0, k)
    if n: a = np.linspace(0, 2 * np.pi, n, endpoint=False) + np.pi / n; ring = np.c_[w / 2 * np.cos(a), d / 2 * np.sin(a)]
    else: ring = np.array([[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]])
    top = np.c_[ring[:, 0], np.full(len(ring), h), ring[:, 1]]; bot = np.c_[ring[:, 0] * k, np.zeros(len(ring)), ring[:, 1] * k]
    return trimesh.convex.convex_hull(np.vstack([top, bot]))


SHAPES = dict(railing=railing, rail_run=rail_run, ibeam=ibeam, rock=rock, cliff=cliff, arch=arch, pipe_elbow=pipe_elbow, vent=vent, tank=tank, machinery=machinery,
              hip_roof=hip_roof, round_arch=round_arch, battlement=battlement, wedge=wedge,
              stream=stream, channel=channel, berm=berm, rock_arch=rock_arch, cave=cave, overhang=overhang, crystals=crystals, frustum=frustum)


def make(o, bevel=0.0):
    """Builder entry for Stage 3 types; returns None if the type isn't handled here."""
    t = o["type"]; w, h, d = o["size"]
    if t in ("box", "cylinder") and o.get("hole"):  # hollow: a round hole straight through (elevator shafts)
        n = int(o.get("sections", 12)) if t == "cylinder" else 0; r = min(w, d)
        return holed(r if n else w, h, r if n else d, float(o["hole"]), n)
    if t == "box" and (o.get("bevel", bevel) or 0) > 0: return bevel_box(w, h, d, o.get("bevel", bevel))
    if t in SHAPES: return SHAPES[t](w, h, d, o)
    return None
