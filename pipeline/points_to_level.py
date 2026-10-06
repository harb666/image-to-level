"""Points -> low-poly game level (.glb + level.json + top-down preview).

Input: .npz from image_to_points.py, or a Lyra Gaussian .ply (reconstructed_scene.ply).
Method (2.5D, block-out style): fit ground plane -> scale so camera = player eye height ->
bin points into a grid -> per cell: walkable floor tile, solid column (wall/building) or
overhang slab (roof/eaves) -> merge runs of cells -> vertex-coloured boxes.
"""
import argparse, json, os, numpy as np, trimesh
from PIL import Image

EYE = 1.7  # metres; player eye height used to set world scale


def load_points(path):
    if path.endswith(".npz"):
        d = np.load(path)
        return d["xyz"], d["rgb"], d["sky_rgb"]
    # Lyra 3DGS .ply: OpenCV camera frame (y down, z forward) -> flip y
    from plyfile import PlyData  # only needed for Lyra output
    v = PlyData.read(path)["vertex"]
    xyz = np.stack([v["x"], -v["y"], v["z"]], 1)
    rgb = np.clip(0.5 + 0.28209479 * np.stack([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]], 1), 0, 1)
    keep = 1 / (1 + np.exp(-np.asarray(v["opacity"]))) > 0.3
    return xyz[keep], rgb[keep], np.array([0.6, 0.75, 0.9])


def fit_ground(xyz, iters=400, tol=0.08, rng=np.random.default_rng(0)):
    """RANSAC plane on the lower half of nearby points. Returns unit normal n (pointing to camera) and d (n.x+d=0)."""
    dist = np.linalg.norm(xyz, axis=1)
    cand = xyz[(xyz[:, 1] < np.median(xyz[:, 1])) & (dist < np.percentile(dist, 70))]
    best, bn, bd = -1, None, None
    for _ in range(iters):
        p = cand[rng.choice(len(cand), 3, replace=False)]
        n = np.cross(p[1] - p[0], p[2] - p[0]); l = np.linalg.norm(n)
        if l < 1e-9 or abs(n[1]) / l < 0.7:  # roughly horizontal planes only
            continue
        n /= l; d = -n @ p[0]
        if d < 0: n, d = -n, -d  # camera (origin) on positive side
        score = (np.abs(cand @ n + d) < tol * max(d, 1e-3)).sum()
        if score > best: best, bn, bd = score, n, d
    return bn, bd


def rot_to_up(n):
    up = np.array([0, 1.0, 0]); v = np.cross(n, up); c = n @ up
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def box(x0, x1, y0, y1, z0, z1, rgb):
    m = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0])
    m.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])
    m.visual.vertex_colors = np.tile(np.r_[np.uint8(np.clip(rgb, 0, 1) * 255), 255], (len(m.vertices), 1))
    return m


def merge_runs(mask, h0, h1, col, cell, ox, oz, hq=0.5):
    """Greedy merge along x of cells with equal quantised heights -> list of boxes."""
    out = []
    nz, nx = mask.shape
    for j in range(nz):
        i = 0
        while i < nx:
            if not mask[j, i]: i += 1; continue
            k = i + 1
            key = (round(h0[j, i] / hq), round(h1[j, i] / hq))
            while k < nx and mask[j, k] and (round(h0[j, k] / hq), round(h1[j, k] / hq)) == key \
                    and np.abs(col[j, k] - col[j, i]).max() < 0.15:
                k += 1
            c = col[j, i:k].mean(0)
            out.append(box(ox + i * cell, ox + k * cell, key[0] * hq, max(key[1] * hq, key[0] * hq + hq),
                           oz + j * cell, oz + (j + 1) * cell, c))
            i = k
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("points"); ap.add_argument("outdir")
    ap.add_argument("--cell", type=float, default=1.0, help="grid cell size in metres")
    ap.add_argument("--max-extent", type=float, default=80.0)
    ap.add_argument("--max-height", type=float, default=30.0)
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)

    xyz, rgb, sky = load_points(a.points)
    n, d = fit_ground(xyz)
    R = rot_to_up(n)
    s = EYE / d  # camera height above ground -> eye height
    p = (xyz @ R.T) * s; p[:, 1] += EYE  # ground at y=0, camera at (0, EYE, 0)
    p[:, 2] *= -1  # glTF: -z is forward
    keep = (p[:, 1] > -0.5) & (p[:, 1] < a.max_height)  # below-ground = void (e.g. clouds, drops)
    keep &= (np.abs(p[:, 0]) < a.max_extent) & (np.abs(p[:, 2]) < a.max_extent)
    p, c = p[keep], rgb[keep]

    cell = a.cell
    ox, oz = np.floor(p[:, 0].min()), np.floor(p[:, 2].min())
    ix = ((p[:, 0] - ox) / cell).astype(int); iz = ((p[:, 2] - oz) / cell).astype(int)
    nx, nz = ix.max() + 1, iz.max() + 1
    flat = iz * nx + ix
    order = np.argsort(flat); flat, pp, cc = flat[order], p[order], c[order]
    starts = np.r_[0, np.flatnonzero(np.diff(flat)) + 1, len(flat)]

    floor = np.zeros((nz, nx), bool); fcol = np.zeros((nz, nx, 3))
    solid = np.zeros((nz, nx), bool); over = np.zeros((nz, nx), bool)
    top = np.zeros((nz, nx)); bot = np.zeros((nz, nx)); scol = np.zeros((nz, nx, 3))
    for a0, a1 in zip(starts[:-1], starts[1:]):
        if a1 - a0 < 3: continue
        j, i = divmod(flat[a0], nx); y = pp[a0:a1, 1]; col = cc[a0:a1]
        g = y < 0.5
        if g.sum() >= 2: floor[j, i] = True; fcol[j, i] = col[g].mean(0)
        st = y > 0.6
        if st.sum() >= 3:
            ys = y[st]; t = np.percentile(ys, 95)
            if t < 0.9: continue
            top[j, i] = t; scol[j, i] = np.median(col[st], 0)
            if floor[j, i] and np.percentile(ys, 5) > 2.2:  # walkable underneath -> roof/eave slab
                over[j, i] = True; bot[j, i] = np.percentile(ys, 5)
            else:
                solid[j, i] = True
    # fill small holes in the walkable floor (occluded patches), give them neighbour colour
    from scipy import ndimage
    walk = ndimage.binary_closing(floor | solid, iterations=2) | floor
    idx = ndimage.distance_transform_edt(~floor, return_distances=False, return_indices=True)
    fcol = np.where(floor[..., None], fcol, fcol[idx[0], idx[1]])

    parts = {
        "Floor": merge_runs(walk, np.full_like(top, -0.5), np.zeros_like(top), fcol, cell, ox, oz),
        "Structures": merge_runs(solid, np.zeros_like(top), top, scol, cell, ox, oz),
        "Overhangs": merge_runs(over, bot, top, scol, cell, ox, oz),
    }
    scene = trimesh.Scene()
    tris = 0
    for name, boxes in parts.items():
        if not boxes: continue
        m = trimesh.util.concatenate(boxes); m.merge_vertices(); tris += len(m.faces)
        scene.add_geometry(m, node_name=name, geom_name=name)
    w = np.argwhere(walk)  # spawn = walkable cell nearest the original camera position
    jj, ii = w[np.argmin(np.hypot(w[:, 0] + oz / cell, w[:, 1] + ox / cell))]
    spawn = [float(ox + (ii + .5) * cell), 0.0, float(oz + (jj + .5) * cell)]
    sp = trimesh.creation.cone(0.3, 0.6); sp.apply_translation([spawn[0], 0.05, spawn[2]])
    scene.add_geometry(sp, node_name="Spawn_marker", geom_name="Spawn_marker")
    scene.export(os.path.join(a.outdir, "level.glb"))

    meta = dict(units="metres, y-up, player faces -Z at spawn", spawn=spawn, eye_height=EYE,
                spawn_facing=[0, 0, -1], cell_size=cell, sky_rgb=[float(x) for x in sky],
                bounds_min=[float(ox), 0, float(oz)], bounds_max=[float(ox + nx * cell), float(top.max()), float(oz + nz * cell)],
                triangles=int(tris), boxes={k: len(v) for k, v in parts.items()})
    json.dump(meta, open(os.path.join(a.outdir, "level.json"), "w"), indent=1)

    # top-down preview: colour = floor/structure colour, brightness = height
    img = np.where(walk[..., None], fcol, 0.08)
    hs = np.clip(top / max(top.max(), 1), 0, 1)[..., None]
    img = np.where((solid | over)[..., None], scol * (0.5 + 0.5 * hs), img)
    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)  # forward (-z) at top
    Image.fromarray(img).resize((nx * 8, nz * 8), Image.NEAREST).save(os.path.join(a.outdir, "topdown.png"))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
