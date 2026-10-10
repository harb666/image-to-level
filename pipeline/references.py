"""Stage 7: helpers that let Claude READ reference images precisely before writing scene_spec.json.
They measure; they don't interpret. Claude still decides what each panel / region means.

  python3 pipeline/references.py split <image> <out_dir>
      Concept sheets: recursive XY-cut along uniform gutters -> panels.json (bbox per panel) + one crop per panel
      + panels_overview.jpg (numbered boxes). Claude labels each panel's view (top_down / elevation / perspective /
      detail) in scene_spec.json "references". A plain single image comes back as one panel.
  python3 pipeline/references.py plan <top_down_crop> <out_dir> --size W D [--bbox x0 y0 x1 y1] [--k 6]
      Top-down layouts: colour clusters -> connected regions -> metres (image top = north = -z, arena centre = 0,0).
      Writes plan_regions.json (centre, size, area, colour, rectangularity per region) + plan_regions.png (labelled).
  python3 pipeline/references.py grid <image> <out.jpg> [--cells 10] [--metres W D] [--bbox x0 y0 x1 y1]
      Overlays a labelled grid (pixels, or metres when --metres is given) for reading positions / heights off
      perspective, elevation or plan images.
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw


def _gutters(a, axis, min_run, tol):
    """Indices of rows (axis=0) / columns (axis=1) that look like uniform separators."""
    g = a.mean(-1); std = g.std(axis=1 - axis)
    grad = np.abs(np.diff(g, axis=1 - axis)).mean(axis=1 - axis)
    flat = (std < tol) & (grad < tol * 0.6)
    runs, start = [], None
    for i, f in enumerate(np.r_[flat, False]):
        if f and start is None: start = i
        if not f and start is not None:
            if i - start >= min_run: runs.append((start, i))
            start = None
    return runs


def _xycut(a, x0, y0, depth, out, min_size, tol):
    h, w = a.shape[:2]
    for axis in (0, 1):
        runs = [r for r in _gutters(a, axis, max(3, int(0.004 * (h if axis == 0 else w))), tol)]
        n = h if axis == 0 else w
        cuts = [(s, e) for s, e in runs if s > min_size and e < n - min_size]
        if cuts and depth < 6:
            edges = [0] + [v for s, e in cuts for v in (s, e)] + [n]
            for i in range(0, len(edges), 2):
                s, e = edges[i], edges[i + 1]
                if e - s < min_size: continue
                sub = a[s:e] if axis == 0 else a[:, s:e]
                _xycut(sub, x0 + (0 if axis == 0 else s), y0 + (s if axis == 0 else 0), depth + 1, out, min_size, tol)
            return
    # trim uniform borders of the leaf
    out.append([x0, y0, x0 + w, y0 + h])


def split(path, out_dir, tol=6.0):
    im = Image.open(path).convert("RGB"); a = np.asarray(im, float); os.makedirs(out_dir, exist_ok=True)
    boxes = []; _xycut(a, 0, 0, 0, boxes, int(0.08 * min(im.size)), tol)
    boxes = [b for b in boxes if (b[2] - b[0]) * (b[3] - b[1]) > 0.01 * im.size[0] * im.size[1]] or [[0, 0, *im.size]]
    stem = os.path.splitext(os.path.basename(path))[0]; panels = []
    ov = im.copy(); dr = ImageDraw.Draw(ov)
    for k, b in enumerate(boxes):
        f = os.path.join(out_dir, f"{stem}_p{k + 1:02d}.png"); im.crop(b).save(f)
        panels.append(dict(id=f"p{k + 1:02d}", bbox_px=b, file=os.path.relpath(f, out_dir), size_px=[b[2] - b[0], b[3] - b[1]], view="?", use=[]))
        dr.rectangle(b, outline=(255, 60, 60), width=4); dr.rectangle([b[0], b[1], b[0] + 46, b[1] + 22], fill=(255, 60, 60)); dr.text((b[0] + 6, b[1] + 5), f"p{k + 1:02d}", fill=(255, 255, 255))
    ov.thumbnail((1400, 1400)); ov.save(os.path.join(out_dir, "panels_overview.jpg"), quality=85)
    R = dict(image=os.path.relpath(path, out_dir), size_px=list(im.size), panels=panels,
             note="Label each panel's view (top_down / elevation / perspective / detail / text) in scene_spec.json references[].panels")
    json.dump(R, open(os.path.join(out_dir, "panels.json"), "w"), indent=1)
    print(f"{len(panels)} panel(s): " + ", ".join(f"{p['id']} {p['bbox_px']}" for p in panels)); return R


def _kmeans(X, k, iters=20, seed=0):
    rng = np.random.default_rng(seed); C = X[rng.choice(len(X), k, replace=False)]
    for _ in range(iters):
        lab = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
        C = np.array([X[lab == i].mean(0) if (lab == i).any() else C[i] for i in range(k)])
    return C, lab


def plan(path, out_dir, size, bbox=None, k=6, min_area_m2=4.0):
    from scipy import ndimage
    im = Image.open(path).convert("RGB")
    if bbox: im = im.crop(bbox)
    W, D = size; s = 300 / max(im.size); sm = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    a = np.asarray(sm, float); X = a.reshape(-1, 3); C, lab = _kmeans(X[::3], k)
    lab = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1).reshape(a.shape[:2])
    mx, mz = W / a.shape[1], D / a.shape[0]; regions = []
    for ci in range(k):
        L_, n = ndimage.label(ndimage.binary_opening(lab == ci, iterations=1))
        for ri, sl in enumerate(ndimage.find_objects(L_)):
            if sl is None: continue
            msk = L_[sl] == ri + 1; area = msk.sum() * mx * mz
            if area < min_area_m2: continue
            z0, z1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
            regions.append(dict(cluster=ci, colour=[int(v) for v in C[ci]], area_m2=round(float(area), 1),
                                center=[round((x0 + x1) / 2 * mx - W / 2, 1), round((z0 + z1) / 2 * mz - D / 2, 1)],
                                size=[round((x1 - x0) * mx, 1), round((z1 - z0) * mz, 1)], rectangularity=round(float(msk.mean()), 2),
                                bbox_px=[int(x0 / s), int(z0 / s), int(x1 / s), int(z1 / s)]))
    regions.sort(key=lambda r: -r["area_m2"])
    for i, r in enumerate(regions): r["id"] = f"r{i + 1:02d}"
    os.makedirs(out_dir, exist_ok=True); ov = im.copy().resize((im.width * 800 // max(im.size), im.height * 800 // max(im.size))); dr = ImageDraw.Draw(ov); f = ov.width / im.width
    for r in regions[:60]:
        b = [v * f for v in r["bbox_px"]]; dr.rectangle(b, outline=tuple(255 - c for c in r["colour"]), width=2)
        dr.text((b[0] + 3, b[1] + 2), f"{r['id']} {r['size'][0]:.0f}x{r['size'][1]:.0f}", fill=(255, 255, 255))
    ov.save(os.path.join(out_dir, "plan_regions.png"))
    R = dict(image=os.path.relpath(path, out_dir), arena_size_m=[W, D], crop=bbox, clusters=[[int(v) for v in c] for c in C], regions=regions,
             note="metres, arena centre = (0,0), image top = north (-z). Clusters are colours, not meanings: Claude decides which are platforms / hazard / walls.")
    json.dump(R, open(os.path.join(out_dir, "plan_regions.json"), "w"), indent=1)
    print(f"{len(regions)} regions >= {min_area_m2} m2 in {k} colour clusters -> {out_dir}/plan_regions.json"); return R


def grid(path, out, cells=10, metres=None, bbox=None):
    im = Image.open(path).convert("RGB"); dr = ImageDraw.Draw(im); x0, y0, x1, y1 = bbox or (0, 0, im.width, im.height)
    for i in range(cells + 1):
        x = x0 + (x1 - x0) * i / cells; y = y0 + (y1 - y0) * i / cells
        dr.line([(x, y0), (x, y1)], fill=(255, 255, 0), width=1); dr.line([(x0, y), (x1, y)], fill=(255, 255, 0), width=1)
        lx = f"{-metres[0] / 2 + metres[0] * i / cells:.0f}" if metres else f"{int(x)}"; ly = f"{-metres[1] / 2 + metres[1] * i / cells:.0f}" if metres else f"{int(y)}"
        dr.text((x + 2, y0 + 2), lx, fill=(255, 255, 0)); dr.text((x0 + 2, y + 2), ly, fill=(0, 255, 255))
    im.save(out, quality=88); print(out)


if __name__ == "__main__":
    cmd, args = sys.argv[1], sys.argv[2:]
    opt = lambda k, n=1: [float(v) for v in args[args.index(k) + 1:args.index(k) + 1 + n]] if k in args else None
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and not (i and args[i - 1].startswith("--")) and not (i > 1 and args[i - 2] in ("--size", "--metres")) and not any(i > j and i <= j + 4 and args[j] == "--bbox" for j in range(len(args)))]
    if cmd == "split": split(pos[0], pos[1])
    elif cmd == "plan":
        b = opt("--bbox", 4); plan(pos[0], pos[1], opt("--size", 2), [int(v) for v in b] if b else None, int(opt("--k")[0]) if opt("--k") else 6)
    elif cmd == "grid":
        b = opt("--bbox", 4); grid(pos[0], pos[1], int(opt("--cells")[0]) if opt("--cells") else 10, opt("--metres", 2), [int(v) for v in b] if b else None)
    else: raise SystemExit(__doc__)
