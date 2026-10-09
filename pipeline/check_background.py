"""Background / horizon completeness check: python3 pipeline/check_background.py levels/<name>
Camera positions: spawn + every walkable area centre, at third-person camera height (eye + 2 m) and an elevated
camera (eye + 8 m). From each, rays every 5° of azimuth at several elevations:
  - below the horizon (-30°..-0.5°): every ray must hit geometry within the camera far plane (else: visible void)
  - just above (+0.5°, +2°): fraction hitting background silhouettes (informational: horizon coverage)
Plus: open (boundary) edges above ground in background meshes = exposed backs/holes.
Writes checks/background_check.json. Pure numpy ray/triangle test (no extra dependencies)."""
import json, os, sys, numpy as np, trimesh


def tri_soup(path):
    s = trimesh.load(path, force="scene"); return s.to_geometry().triangles if len(s.geometry) else np.zeros((0, 3, 3))


def first_hit(O, D, T, far):
    """Möller–Trumbore, rays (n,3) from O (3,) vs triangles (m,3,3) -> nearest distance per ray (inf = miss)."""
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]; best = np.full(len(D), np.inf)
    for i in range(0, len(D), 64):
        dd = D[i:i + 64]; p = np.cross(dd[:, None, :], e2[None]); det = np.einsum("nmk,mk->nm", p, e1)
        ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0); s = O - v0
        u = np.einsum("mk,nmk->nm", s, p) * inv; qv = np.cross(s, e1); v = np.einsum("nk,mk->nm", dd, qv) * inv
        t = np.einsum("mk,mk->m", e2, qv)[None] * inv
        hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 0.05) & (t < far)
        best[i:i + 64] = np.where(hit, t, np.inf).min(1)
    return best


def main(level_dir):
    L = json.load(open(os.path.join(level_dir, "level.json")))
    E = json.load(open(os.path.join(level_dir, "environment.json"))) if os.path.exists(os.path.join(level_dir, "environment.json")) else None
    far = E["camera"]["far"] if E else 500
    lvl = tri_soup(os.path.join(level_dir, "level.glb"))
    bgp = os.path.join(level_dir, "background.glb"); bg = tri_soup(bgp) if os.path.exists(bgp) else np.zeros((0, 3, 3))
    allT = np.concatenate([lvl, bg])
    pts = [L["spawn"]["position"]] + [[(w["min"][0] + w["max"][0]) / 2, w["y"], (w["min"][1] + w["max"][1]) / 2] for w in L.get("walkable", [])]
    az = np.radians(np.arange(0, 360, 5)); below = np.radians([-30, -15, -8, -4, -2, -1, -0.5]); above = np.radians([0.5, 2])
    dirs = lambda els: np.array([[np.cos(e) * np.sin(a), np.sin(e), -np.cos(e) * np.cos(a)] for e in els for a in az])
    Db, Da = dirs(below), dirs(above)
    misses, cover, n_b = [], [], 0
    for p in pts:
        for dh, tag in ((1.7 + 2.0, "third_person"), (1.7 + 8.0, "elevated")):
            O = np.array(p, float) + [0, dh, 0]
            hb = first_hit(O, Db, allT, far); n_b += len(Db)
            for k in np.flatnonzero(~np.isfinite(hb)):
                misses.append(dict(camera=[round(float(x), 1) for x in O], view=tag, azimuth_deg=int(np.degrees(az[k % len(az)])),
                                   elevation_deg=round(float(np.degrees(below[k // len(az)])), 1)))
            if len(bg): cover.append(float(np.isfinite(first_hit(O, Da, bg, far)).mean()))
    open_edges = {}
    if len(bg):
        for name, g in trimesh.load(bgp, force="scene").geometry.items():
            g = g.copy(); g.merge_vertices(merge_tex=True, merge_norm=True)
            e = g.edges_sorted; u, c = np.unique(e, axis=0, return_counts=True); b = u[c == 1]
            open_edges[name] = int((g.vertices[b].min(1)[:, 1] > 0.0).sum()) if len(b) else 0  # boundary edges above ground
    R = dict(camera_positions=len(pts) * 2, rays_below_horizon=n_b, void_rays=len(misses), void_examples=misses[:20],
             horizon_silhouette_coverage=round(float(np.mean(cover)), 3) if cover else None, open_edges_above_ground=open_edges,
             passed=len(misses) == 0 and all(v == 0 for v in open_edges.values()))
    os.makedirs(os.path.join(level_dir, "checks"), exist_ok=True)
    json.dump(R, open(os.path.join(level_dir, "checks", "background_check.json"), "w"), indent=1)
    print(json.dumps({k: v for k, v in R.items() if k != "void_examples"}))
    return R


if __name__ == "__main__":
    main(sys.argv[1])
