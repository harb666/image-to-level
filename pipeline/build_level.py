"""level.json -> level.glb (+ topdown.png). Usage: python3 pipeline/build_level.py levels/<name>
Each object becomes its own named glTF node (children under their parent group); meshes share one material
per material type with a small procedural tileable texture (UVs are world-scaled, so textures never stretch)."""
import io, json, os, sys, numpy as np, trimesh
from PIL import Image, ImageDraw
from trimesh.transformations import euler_matrix, translation_matrix

TEX = 256  # px; mobile-friendly (jpeg-compressed in the glb)


def _noise(rng, cells, octaves=3):
    out = np.zeros((TEX, TEX))
    for o in range(octaves):
        c = cells * 2 ** o; a = rng.random((c, c))
        big = np.asarray(Image.fromarray(np.tile(a, (3, 3)).astype(np.float32)).resize((TEX * 3, TEX * 3), Image.BICUBIC))
        out += big[TEX:2 * TEX, TEX:2 * TEX] / 2 ** o  # centre of a 3x3 tiling -> seamless
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _cells(rng, n):
    """Tileable Voronoi: (id of nearest point, edge closeness 0..1)."""
    pts = rng.random((n, 2)) * TEX; y, x = np.mgrid[:TEX, :TEX]
    d = np.stack([np.hypot(np.minimum(abs(x - px), TEX - abs(x - px)), np.minimum(abs(y - py), TEX - abs(y - py))) for px, py in pts])
    s = np.sort(d, 0); return d.argmin(0), np.clip((s[1] - s[0]) / 4, 0, 1)


def _bevel(e, w=0.35):
    """Edge closeness 0..1 -> raised-tile shading (dark grout, lit top-left bevel)."""
    return np.clip(e / w, 0, 1) ** 0.6


def texture(kind):
    """Stylised tileable texture: RGB multiplier around 1.0 (times the material colour)."""
    rng = np.random.default_rng(sum(map(ord, kind))); y, x = np.mgrid[:TEX, :TEX] / TEX
    n = _noise(rng, 4); fine = _noise(rng, 32, 2); tint = np.ones((TEX, TEX, 3))
    if kind == "cobblestone":
        cid, e = _cells(rng, 34); shade = rng.uniform(0.75, 1.15, 34)[cid]
        t = shade * (0.35 + 0.65 * _bevel(e, 0.5)) * (0.85 + 0.25 * fine)
        tint *= rng.uniform(0.97, 1.03, (34, 3))[cid]
    elif kind in ("stone_brick", "concrete_block"):
        rows = 8; row = (y * rows).astype(int); off = (row % 2) * 0.125; col = ((x + off) * 4).astype(int) % 4
        ey = np.minimum((y * rows) % 1, 1 - (y * rows) % 1) * 4; ex = np.minimum(((x + off) * 4) % 1, 1 - ((x + off) * 4) % 1) * 8
        shade = rng.uniform(0.78, 1.1, (rows, 4))[row, col]; t = shade * (0.35 + 0.65 * _bevel(np.minimum(ex, ey), 0.4)) * (0.85 + 0.3 * fine)
        tint *= rng.uniform(0.97, 1.03, (rows, 4, 3))[row, col]
    elif kind in ("wood", "door_wood", "trim_wood", "painted_wood"):
        boards = 4 if kind != "trim_wood" else 2; board = (x * boards).astype(int)
        grain = np.sin((y * 3 + rng.random(boards)[board]) * 60 + 8 * _noise(rng, 6)) * 0.5 + 0.5
        t = (0.8 + 0.2 * grain * (0.4 if kind == "painted_wood" else 1)) * rng.uniform(0.85, 1.1, boards)[board]
        t *= 0.4 + 0.6 * _bevel(np.minimum((x * boards) % 1, 1 - (x * boards) % 1) * 10, 0.5)
        if kind == "door_wood":  # frame + handle
            fr = (x < 0.08) | (x > 0.92) | (y < 0.06); t[fr] *= 0.6; t[(abs(x - 0.8) < 0.03) & (abs(y - 0.55) < 0.03)] = 1.6
    elif kind == "window":  # dark glass, light frame, 2x2 mullions
        glass = 0.35 + 0.25 * (y < 0.5 - 0.4 * x)  # sky reflection streak
        frame = (np.minimum(x, 1 - x) < 0.09) | (np.minimum(y, 1 - y) < 0.07) | (abs(x - 0.5) < 0.03) | (abs(y - 0.5) < 0.03)
        t = np.where(frame, 1.15, glass); tint[~frame] = [0.6, 0.8, 1.2]
    elif kind in ("roof_tiles", "roof_slate"):
        rows = 10 if kind == "roof_tiles" else 14; r = (y * rows) % 1; cols = 8 if kind == "roof_tiles" else 6
        u = (x * cols + (y * rows).astype(int) % 2 * 0.5) % 1
        t = (0.55 + 0.55 * r) * (1 - 0.35 * (np.abs(u - 0.5) > 0.44)) * rng.uniform(0.85, 1.1, (rows, cols + 1))[(y * rows).astype(int), (x * cols + 0.5).astype(int)]
    elif kind == "metal":
        t = 0.85 + 0.1 * _noise(rng, 64, 1)[:, :1].repeat(TEX, 1) + 0.06 * n
        seam = np.minimum(y % 0.5, x % 0.5) < 0.012; t[seam] = 0.5
        riv = (np.hypot((x % 0.5) - 0.04, (y % 0.5) - 0.04) < 0.012) | (np.hypot((x % 0.5) - 0.46, (y % 0.5) - 0.04) < 0.012); t[riv] = 1.25
    elif kind == "grass":
        blades = _noise(rng, 64, 1); t = 0.65 + 0.35 * n + 0.25 * (blades > 0.7) - 0.15 * (blades < 0.25)
        tint[..., 0] *= 0.85 + 0.3 * _noise(rng, 3, 2); tint[..., 2] *= 0.8 + 0.2 * n
    elif kind == "rock":
        cid, e = _cells(rng, 9); t = rng.uniform(0.8, 1.1, 9)[cid] * (0.5 + 0.5 * _bevel(e, 0.9)) * (0.75 + 0.4 * _noise(rng, 6, 4))
        t[(np.abs(_noise(rng, 5, 2) - 0.5) < 0.015)] *= 0.6  # cracks
    elif kind == "water":
        t = 0.85 + 0.3 * np.sin((x + 0.3 * n) * 25) ** 8; tint *= [0.9, 1.0, 1.1]
    elif kind == "floor_plate":  # worn tan deck plates: 2x2 plates, bevelled seams, octagon inlay, scuffs, edge wear
        px, py = (x * 2) % 1, (y * 2) % 1; e = np.minimum(np.minimum(px, 1 - px), np.minimum(py, 1 - py)) * 14
        t = (0.42 + 0.58 * _bevel(e, 0.35)) * (0.86 + 0.16 * fine + 0.1 * n) * rng.uniform(0.9, 1.06, (2, 2))[(y * 2).astype(int), (x * 2).astype(int)]
        oc = np.maximum(np.abs(px - 0.5), np.abs(py - 0.5)) + 0.45 * np.minimum(np.abs(px - 0.5), np.abs(py - 0.5))
        inl = np.abs(oc - 0.33) < 0.012; t[inl] *= 0.75; tint[inl] = [1.3, 1.1, 0.55]
        bolt = np.hypot(np.minimum(px, 1 - px) - 0.06, np.minimum(py, 1 - py) - 0.06) < 0.018; t[bolt] = 0.55
        t *= 1 - 0.25 * np.clip(_noise(rng, 5, 3) - 0.6, 0, 1) * 2.5  # dark scuffs / grime
        tint *= [1.04, 1.0, 0.94]
    elif kind == "industrial_wall":  # dark worn metal: vertical panels, seams, rivet rows, horizontal straps, grime
        cols = 4; cx = (x * cols) % 1; band = (y * 2) % 1
        e = np.minimum(cx, 1 - cx) * 18; pnl = rng.uniform(0.85, 1.12, cols)[(x * cols).astype(int)]
        t = (0.5 + 0.5 * _bevel(e, 0.4)) * pnl * (0.85 + 0.15 * fine + 0.12 * n)
        strap = np.abs(band - 0.5) < 0.05; t[strap] *= 1.25; t[np.abs(band - 0.5) - 0.05 < 0.01] *= 0.7
        riv = (np.abs(band - 0.5) < 0.05) & (np.hypot(((x * cols * 3) % 1) - 0.5, (band - 0.5) * 6) < 0.12); t[riv] = 1.35
        t *= 1 - 0.35 * np.clip(_noise(rng, 6, 3) - 0.55, 0, 1) * 2.2 * (0.6 + 0.4 * y)  # grime, heavier lower
        lamp = (np.abs(cx - 0.5) < 0.05) & (np.abs(band - 0.2) < 0.012); t[lamp] = 1.6; tint[lamp] = [1.6, 1.0, 0.3]  # tiny amber lights
    elif kind == "platform_side":  # chunky block sides: big recessed panels, thick frames, vertical drip grime
        cx, cy = (x * 2) % 1, (y * 2) % 1; e = np.minimum(np.minimum(cx, 1 - cx), np.minimum(cy, 1 - cy))
        frame = e < 0.09; inset = (e > 0.13)
        t = np.where(frame, 1.12, np.where(inset, 0.82, 0.55)) * (0.85 + 0.18 * fine + 0.1 * n)
        t *= 1 - 0.3 * np.clip(_noise(rng, 12, 1)[:1, :].repeat(TEX, 0) - 0.55, 0, 1) * 2.2 * y  # vertical streaks
        tint *= [0.95, 1.02, 0.97]
    elif kind == "grate":  # metal walkway grating: bars over dark gaps, side rails
        bar = (y * 16) % 1 < 0.55; rail = np.minimum(x, 1 - x) < 0.06
        t = np.where(bar | rail, 0.95 + 0.1 * fine, 0.3); t *= 0.9 + 0.15 * n
    elif kind == "pipe_metal":  # dark pipe: segment rings/flanges + bolts, lengthwise sheen, grime
        v = (y * 2) % 1; ring = np.abs(v - 0.5) < 0.06
        sheen = 0.8 + 0.25 * np.sin(x * np.pi * 2) ** 2
        t = sheen * (0.82 + 0.12 * n + 0.08 * fine); t[ring] = 1.25 * sheen[ring]; t[np.abs(np.abs(v - 0.5) - 0.07) < 0.01] *= 0.55
        bolt = ring & (((x * 12) % 1) < 0.2) & (np.abs(v - 0.5) < 0.03); t[bolt] = 1.5
        t *= 1 - 0.3 * np.clip(_noise(rng, 4, 3) - 0.6, 0, 1) * 2.5
    elif kind == "toxic":  # bright neon fluid: swirls + light foam caustics
        sw = np.sin((x + 0.35 * _noise(rng, 3, 2)) * 18) * np.sin((y + 0.35 * _noise(rng, 3, 2)) * 14)
        cid, e = _cells(rng, 30); foam = np.clip(1 - e * 3, 0, 1) ** 3
        t = 0.8 + 0.2 * sw ** 2 + 0.12 * n + 0.35 * foam; tint[..., 0] += 0.4 * foam; tint[..., 2] += 0.3 * foam
    elif kind == "glow":  # emissive tube: hot core, soft falloff to the edges
        t = 0.55 + 0.9 * np.exp(-((x - 0.5) / 0.22) ** 2) + 0.05 * n; tint[..., 0] += 0.3 * np.exp(-((x - 0.5) / 0.12) ** 2)
    elif kind == "red_panel":  # banner: dark frame, red cloth with pennant V-cut, ring+cross emblem, stitched border
        frame = (np.minimum(x, 1 - x) < 0.07) | (y < 0.05)
        vcut = y > 0.86 + 0.14 * np.abs(x - 0.5) * 2  # dark notch at the bottom
        r = np.hypot(x - 0.5, (y - 0.42) * 1.2); emb = (np.abs(r - 0.17) < 0.022) | ((r < 0.25) & ((np.abs(x - 0.5) < 0.012) | (np.abs(y - 0.42) < 0.012)))
        cloth = 0.85 + 0.12 * np.sin(x * 40 + 4 * n) * 0.3 + 0.1 * fine - 0.25 * y
        t = np.where(frame | vcut, 0.18, cloth); t[emb & ~frame] = 1.45; tint[emb & ~frame] = [1.0, 0.75, 0.4]
        t[(np.abs(np.minimum(x, 1 - x) - 0.1) < 0.008) & ~vcut & (y > 0.05)] = 1.2
    elif kind == "plaster":
        t = 0.93 + 0.1 * fine - 0.12 * np.clip(_noise(rng, 3, 2) - 0.6, 0, 1) * 3 * (1 - y)  # stains near the bottom
    elif kind in ("sand", "soil"):
        t = 0.82 + 0.25 * _noise(rng, 6, 3) + 0.12 * (fine > 0.75)
    else:  # concrete
        t = 0.88 + 0.15 * fine + 0.05 * n; t[(x % 0.5 < 0.006) | (y % 0.5 < 0.006)] *= 0.75
    return np.clip(t[..., None] * tint, 0, 1.4)


def material(name, m):
    if name == "_invisible":
        return trimesh.visual.material.PBRMaterial(name="Collider_invisible", baseColorFactor=[1, 0, 0, 0], alphaMode="BLEND")
    t = texture(m["type"]) * np.array(m["color"])[None, None] * 1.1
    buf = io.BytesIO(); Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8)).save(buf, "JPEG", quality=82)
    img = Image.open(io.BytesIO(buf.getvalue()))  # JPEG-backed -> embedded as jpeg (smaller glb)
    metal = m["type"] in ("metal", "pipe_metal")
    if m.get("emissive"):  # glowing (toxic fluid, lights): same texture drives emission
        return trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=img, emissiveTexture=img,
                                                   emissiveFactor=m["emissive"], metallicFactor=0.0, roughnessFactor=0.3)
    return trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=img, metallicFactor=0.6 if metal else 0.0,
                                               roughnessFactor=0.45 if metal or m["type"] in ("window", "water") else 0.9)


def shape(o):
    t = o["type"]
    if t == "terrain":
        h = np.array(o["heights"], float); c = o["cell"]; nz, nx = h.shape
        zz, xx = np.mgrid[:nz, :nx] * c
        v = np.c_[xx.ravel(), h.ravel(), zz.ravel()]; i = np.arange(nz * nx).reshape(nz, nx)
        a, b, cc, d = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, 1:].ravel(), i[1:, :-1].ravel()
        return trimesh.Trimesh(v, np.r_[np.c_[a, d, cc], np.c_[a, cc, b]])
    w, h, d = o["size"]
    if t in ("box", "boundary"):
        m = trimesh.creation.box([w, h, d]); m.apply_translation([0, h / 2, 0]); return m
    if t == "cylinder":
        m = trimesh.creation.cylinder(radius=min(w, d) / 2, height=h, sections=o.get("sections", 12))
        m.apply_transform(euler_matrix(-np.pi / 2, 0, 0)); m.apply_translation([0, h / 2, 0]); return m
    if t == "panel":  # flat quad facing +z (windows, doors, signs); base at y=0
        return trimesh.Trimesh([[-w/2, 0, 0], [w/2, 0, 0], [w/2, h, 0], [-w/2, h, 0]], [[0, 1, 2], [0, 2, 3]])
    if t == "spire":  # 4-sided pyramid
        return trimesh.convex.convex_hull([[-w/2, 0, -d/2], [w/2, 0, -d/2], [w/2, 0, d/2], [-w/2, 0, d/2], [0, h, 0]])
    if t == "roof":  # gable along the longer side
        if w >= d: pts = [[-w/2, 0, -d/2], [w/2, 0, -d/2], [w/2, 0, d/2], [-w/2, 0, d/2], [-w/2, h, 0], [w/2, h, 0]]
        else: pts = [[-w/2, 0, -d/2], [w/2, 0, -d/2], [w/2, 0, d/2], [-w/2, 0, d/2], [0, h, -d/2], [0, h, d/2]]
        return trimesh.convex.convex_hull(pts)
    if t == "ramp":  # rises towards +z
        return trimesh.convex.convex_hull([[-w/2, 0, -d/2], [w/2, 0, -d/2], [-w/2, 0, d/2], [w/2, 0, d/2], [-w/2, h, d/2], [w/2, h, d/2]])
    if t == "stairs":  # climbs towards +z
        n = max(2, int(round(h / 0.25))); parts = []
        for k in range(n):
            b = trimesh.creation.box([w, h * (k + 1) / n, d / n]); b.apply_translation([0, h * (k + 1) / n / 2, -d / 2 + d / n * (k + .5)]); parts.append(b)
        return trimesh.util.concatenate(parts)
    raise ValueError(f"unknown type {t} ({o['name']})")


def uv_world(m, tile):
    """Unweld and give every face planar UVs along its dominant axis, in world metres / tile."""
    m = m.copy(); m.unmerge_vertices()
    ax = np.abs(m.face_normals).argmax(1).repeat(3); v = m.vertices
    uv = np.where(ax[:, None] == 0, v[:, [2, 1]], np.where(ax[:, None] == 1, v[:, [0, 2]], v[:, [0, 1]])) / tile
    return m, uv


def node_matrix(o):
    r = np.radians(o.get("rotation", [0, 0, 0]))
    return translation_matrix(o.get("position", [0, 0, 0])) @ euler_matrix(*r, "sxyz")


def build(level_dir):
    L = json.load(open(os.path.join(level_dir, "level.json")))
    mats = {k: material(k, m) for k, m in L["materials"].items()}
    L.setdefault("draw_hint", "one material per surface type; mark static + batch in engine"); mats["_invisible"] = material("_invisible", None)
    scene = trimesh.Scene(); base = scene.graph.base_frame; tris = 0
    world = {}  # name -> world matrix (for topdown)
    geoms = {}  # (type, size, material) -> shared geometry name
    for o in L["objects"]:
        parent = o.get("parent") or base; T = node_matrix(o)
        world[o["name"]] = (world.get(parent, np.eye(4)) if parent != base else np.eye(4)) @ T
        if o["type"] == "group":
            scene.graph.update(frame_from=parent, frame_to=o["name"], matrix=T); continue
        mk = "_invisible" if o["type"] == "boundary" else o["material"]
        tile = L["materials"].get(mk, {}).get("tile_m", 2.0)
        if o["type"] == "terrain":  # smooth-shaded; split into rock (steep) + top material (flat)
            m = shape(o); uv = m.vertices[:, [0, 2]] / 4.0
            flat = m.face_normals[:, 1] > 0.85
            for suffix, sel, mm in (("", ~flat, mk), ("_Top", flat, o.get("top_material", mk))):
                if not sel.any(): continue
                sub = trimesh.Trimesh(m.vertices, m.faces[sel], process=False)
                if suffix: sub.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[mm]); sub.remove_unreferenced_vertices()
                else: sub, suv = uv_world(sub, 4.0); sub.visual = trimesh.visual.TextureVisuals(uv=suv, material=mats[mm])  # cliffs: no stretching
                tris += len(sub.faces)
                scene.add_geometry(sub, node_name=o["name"] + suffix, geom_name=o["name"] + suffix, parent_node_name=parent, transform=T)
            continue
        key = (o["type"], tuple(o["size"]), mk, o.get("sections"))
        if key in geoms:  # identical part (window/door/...) -> reuse the same mesh (glTF instancing)
            scene.graph.update(frame_from=parent, frame_to=o["name"], matrix=T, geometry=geoms[key])
            tris += len(scene.geometry[geoms[key]].faces); continue
        m, uv = uv_world(shape(o), tile)
        if o["type"] == "panel": uv = (m.vertices[:, :2] - [-o["size"][0] / 2, 0]) / o["size"][:2]  # whole texture once
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[mk])
        if o["type"] != "boundary": tris += len(m.faces)
        gname = o["name"] if o["type"] not in ("panel", "cylinder") else f"{o['type']}_{mk}_{len(geoms)}"
        geoms[key] = gname
        scene.add_geometry(m, node_name=o["name"], geom_name=gname, parent_node_name=parent, transform=T)
    sp = L["spawn"]
    scene.graph.update(frame_from=base, frame_to="PlayerSpawn",
                       matrix=translation_matrix(sp["position"]) @ euler_matrix(0, np.radians(sp["yaw_deg"]), 0))
    scene.export(os.path.join(level_dir, "level.glb"))
    L["build_stats"] = dict(triangles=tris, objects=len(L["objects"]), materials=len(L["materials"]),
                            glb_kb=round(os.path.getsize(os.path.join(level_dir, "level.glb")) / 1024))
    json.dump(L, open(os.path.join(level_dir, "level.json"), "w"), indent=1)
    topdown(L, world, os.path.join(level_dir, "topdown.png"))
    print(json.dumps(L["build_stats"]))


def topdown(L, world, path, px=10):
    b0, b1 = np.array(L["bounds"]["min"]) - 4, np.array(L["bounds"]["max"]) + 4
    W, H = int((b1[0] - b0[0]) * px), int((b1[2] - b0[2]) * px)
    img = Image.new("RGB", (W, H), (40, 44, 40)); dr = ImageDraw.Draw(img)
    ter = next((o for o in L["objects"] if o["type"] == "terrain"), None)
    tc = L["materials"][ter["material"]]["color"] if ter else [0.1, 0.1, 0.1]
    xy = lambda x, z: ((x - b0[0]) * px, (z - b0[2]) * px)
    dr.rectangle([xy(L["bounds"]["min"][0], L["bounds"]["min"][2]), xy(L["bounds"]["max"][0], L["bounds"]["max"][2])], fill=tuple(int(c * 255) for c in tc))
    order = sorted([o for o in L["objects"] if o["type"] not in ("terrain", "group")], key=lambda o: world[o["name"]][1, 3] + o["size"][1])
    for o in order:
        w, _, d = o["size"]; M = world[o["name"]]
        corners = [M @ [sx * w / 2, 0, sz * d / 2, 1] for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        if o["type"] == "boundary":
            dr.polygon([xy(c[0], c[2]) for c in corners], outline=(230, 50, 50)); continue
        col = tuple(int(c * 255) for c in L["materials"][o["material"]]["color"])
        dr.polygon([xy(c[0], c[2]) for c in corners], fill=col, outline=(0, 0, 0))
    s = xy(L["spawn"]["position"][0], L["spawn"]["position"][2]); dr.ellipse([s[0] - 6, s[1] - 6, s[0] + 6, s[1] + 6], fill=(40, 120, 255))
    img.save(path)


if __name__ == "__main__":
    build(sys.argv[1])
