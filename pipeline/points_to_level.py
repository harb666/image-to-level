"""Points -> low-poly game level (.glb + level.json + top-down preview).

Input: .npz from image_to_points.py, or a Lyra Gaussian .ply (reconstructed_scene.ply).
Method (2.5D, block-out style): fit ground plane -> scale so camera = player eye height ->
bin points into a grid -> per cell: walkable floor tile, solid column (wall/building) or
overhang slab (roof/eaves) -> merge runs of cells -> vertex-coloured boxes.
"""
import argparse, json, os, warnings, numpy as np, trimesh
warnings.filterwarnings("ignore", "All-NaN")
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
    """Greedy merge: runs along x of equal quantised height+colour, then identical runs stacked along z -> boxes."""
    nz, nx = mask.shape
    key = lambda j, i: (round(h0[j, i] / hq), round(h1[j, i] / hq), tuple(np.round(col[j, i], 2)))
    open_, out = {}, []
    def emit(r, j0, j1):
        i, k, (b0, b1, c) = r
        out.append(box(ox + i * cell, ox + k * cell, b0 * hq, max(b1 * hq, b0 * hq + hq),
                       oz + j0 * cell, oz + j1 * cell, np.array(c)))
    for j in range(nz + 1):
        runs = set()
        i = 0
        while j < nz and i < nx:
            if not mask[j, i]: i += 1; continue
            kk, k = key(j, i), i + 1
            while k < nx and mask[j, k] and key(j, k) == kk: k += 1
            runs.add((i, k, kk)); i = k
        for r in list(open_):
            if r not in runs: emit(r, open_.pop(r), j)
        for r in runs:
            open_.setdefault(r, j)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("points"); ap.add_argument("outdir")
    ap.add_argument("--cell", type=float, default=0.5, help="grid cell size in metres")
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
    from scipy import ndimage
    from scipy.cluster.vq import kmeans2
    k3 = np.ones((3, 3), bool)
    # structures: drop specks (<1 m^2), median-smooth tops so walls/roofs are flat
    def denoise(m, min_cells):
        lab, n = ndimage.label(m, k3); sz = ndimage.sum(m, lab, range(1, n + 1))
        return np.isin(lab, 1 + np.flatnonzero(sz >= min_cells))
    mc = max(2, int(round(1 / cell ** 2)))
    solid, over = denoise(solid, mc), denoise(over & ~solid, mc)
    for m in (solid, over):
        t = ndimage.generic_filter(np.where(m, top, np.nan), np.nanmedian, 3, mode="constant", cval=np.nan)
        top = np.where(m, np.nan_to_num(t, nan=top.max()), top)
    bot = np.where(over, ndimage.generic_filter(np.where(over, bot, np.nan), np.nanmedian, 3, mode="constant", cval=np.nan), bot)
    # walkable floor: close occlusion holes, keep the connected area nearest the camera (rejects clouds/backdrop)
    walk = ndimage.binary_closing(floor | solid, k3, iterations=2) | floor
    walk = ndimage.binary_opening(walk, k3) | (floor & walk)
    lab, n = ndimage.label(walk & ~solid)
    cj, ci = -oz / cell, -ox / cell
    w = np.argwhere(lab > 0)
    main = lab == lab[tuple(w[np.argmin(np.hypot(w[:, 0] - cj, w[:, 1] - ci))])]
    near = ndimage.binary_dilation(main, k3, iterations=2)
    walk = main | (walk & near & solid)
    solid &= near; over &= ndimage.binary_dilation(walk, k3)
    lab, n = ndimage.label(solid, k3)  # keep whole buildings that touch the play area
    solid = np.isin(lab, np.unique(lab[solid & near]))
    idx = ndimage.distance_transform_edt(~floor, return_distances=False, return_indices=True)
    fcol = np.where(floor[..., None], fcol, fcol[idx[0], idx[1]])
    fcol = np.where(walk[..., None], ndimage.median_filter(fcol, size=(3, 3, 1)), fcol)
    # palette: 8 colours -> cleaner merges, fewer boxes, easy to re-material later
    used = np.r_[fcol[walk], scol[solid | over]]
    pal, _ = kmeans2(used.astype(float), 8, seed=0, minit="++")
    q = lambda c: pal[np.argmin(((c[..., None, :] - pal) ** 2).sum(-1), -1)]
    fcol, scol = q(fcol), q(scol)
    # boundary: invisible 3 m walls on open edges of the play area
    edge = ndimage.binary_dilation(walk | solid, k3) & ~(walk | solid)

    parts = {
        "Floor": merge_runs(walk, np.full_like(top, -0.5), np.zeros_like(top), fcol, cell, ox, oz),
        "Structures": merge_runs(solid, np.zeros_like(top), top, scol, cell, ox, oz),
        "Overhangs": merge_runs(over, bot, top, scol, cell, ox, oz),
        "Boundary_collider": merge_runs(edge, np.zeros_like(top), np.full_like(top, 3.0), np.zeros_like(fcol), cell, ox, oz),
    }
    scene = trimesh.Scene()
    tris = 0
    for name, boxes in parts.items():
        if not boxes: continue
        m = trimesh.util.concatenate(boxes); m.merge_vertices(); tris += len(m.faces) if name != "Boundary_collider" else 0
        scene.add_geometry(m, node_name=name, geom_name=name)
    # spawn: open walkable cell (>=1 m from walls/edges) nearest the original camera, facing the play area
    clear = ndimage.distance_transform_edt(walk & ~over) * cell
    w = np.argwhere(clear >= min(1.0, clear.max()))
    jj, ii = w[np.argmin(np.hypot(w[:, 0] - cj, w[:, 1] - ci))]
    spawn = [float(ox + (ii + .5) * cell), 0.0, float(oz + (jj + .5) * cell)]
    cz, cx = np.argwhere(walk).mean(0)
    fd = np.array([cx - ii, cz - jj], float); fd /= max(np.linalg.norm(fd), 1e-6)
    sp = trimesh.creation.cone(0.3, 0.6); sp.apply_translation([spawn[0], 0.05, spawn[2]])
    scene.add_geometry(sp, node_name="Spawn_marker", geom_name="Spawn_marker")
    scene.export(os.path.join(a.outdir, "level.glb"))

    bb = np.argwhere(walk | solid)
    meta = dict(units="metres, y-up, player faces spawn_facing", spawn=spawn, eye_height=EYE,
                spawn_facing=[float(fd[0]), 0, float(fd[1])], cell_size=cell, sky_rgb=[float(x) for x in sky],
                bounds_min=[float(ox + bb[:, 1].min() * cell), 0, float(oz + bb[:, 0].min() * cell)],
                bounds_max=[float(ox + (bb[:, 1].max() + 1) * cell), float(top[solid | over].max()), float(oz + (bb[:, 0].max() + 1) * cell)],
                triangles=int(tris), palette=[[round(float(v), 3) for v in c] for c in pal], boxes={k: len(v) for k, v in parts.items()})
    json.dump(meta, open(os.path.join(a.outdir, "level.json"), "w"), indent=1)

    # top-down preview: colour = floor/structure colour, brightness = height
    img = np.where(walk[..., None], fcol, 0.08)
    hs = np.clip(top / max(top.max(), 1), 0, 1)[..., None]
    img = np.where((solid | over)[..., None], scol * (0.5 + 0.5 * hs), img)
    img = np.where(edge[..., None], [0.9, 0.2, 0.2], img)  # red = invisible boundary
    j0, i0 = np.maximum(bb.min(0) - 2, 0); j1, i1 = bb.max(0) + 3
    img = (np.clip(img[j0:j1, i0:i1], 0, 1) * 255).astype(np.uint8)  # forward (-z) at top
    Image.fromarray(img).resize((img.shape[1] * 8, img.shape[0] * 8), Image.NEAREST).save(os.path.join(a.outdir, "topdown.png"))
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
