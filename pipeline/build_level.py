"""level.json -> level.glb (+ topdown.png). Usage: python3 pipeline/build_level.py levels/<name>
Each object becomes its own named glTF node (children under their parent group); meshes share one material
per material type with a small procedural tileable texture (UVs are world-scaled, so textures never stretch)."""
import io, json, os, sys, numpy as np, trimesh
from PIL import Image, ImageDraw
from trimesh.transformations import euler_matrix, translation_matrix

TEX = 128  # px; mobile-friendly


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


def texture(kind):
    rng = np.random.default_rng(abs(hash(kind)) % 2 ** 32); y, x = np.mgrid[:TEX, :TEX] / TEX; n = _noise(rng, 4)
    if kind == "cobblestone":
        cid, e = _cells(rng, 28); shade = rng.uniform(0.75, 1.1, 28)[cid]; t = shade * (0.55 + 0.45 * e) * (0.9 + 0.2 * n)
    elif kind in ("stone_brick", "concrete_block"):
        row = (y * 8).astype(int); off = (row % 2) * 0.125; col = ((x + off) * 4).astype(int)
        mort = (np.minimum((y * 8) % 1, 1 - (y * 8) % 1) < 0.07) | (np.minimum(((x + off) * 4) % 1, 1 - ((x + off) * 4) % 1) < 0.035)
        t = rng.uniform(0.8, 1.05, (8, 5))[row, col % 5] * (0.9 + 0.2 * n); t[mort] = 0.55
    elif kind in ("wood", "painted_wood"):
        board = (x * 4).astype(int); t = 0.85 + 0.1 * np.sin(y * 40 + n * 6 + board * 2) * (0.5 if kind == "painted_wood" else 1)
        t *= rng.uniform(0.85, 1.05, 4)[board]; t[(x * 4) % 1 < 0.04] = 0.5
    elif kind == "roof_tiles":
        r = (y * 8) % 1; t = 0.7 + 0.35 * r - 0.25 * (np.abs(((x * 8 + (y * 8).astype(int) % 2 * 0.5) % 1) - 0.5) > 0.45)
    elif kind == "metal":
        t = 0.85 + 0.08 * _noise(rng, 32, 1)[:, :1].repeat(TEX, 1) + 0.05 * n; t[(np.minimum(y % 0.5, x % 0.5) < 0.01)] = 0.55
    elif kind == "grass":
        t = 0.7 + 0.45 * _noise(rng, 16, 2) * (0.6 + 0.4 * n)
    elif kind == "rock":
        t = 0.6 + 0.5 * _noise(rng, 3, 4)
    else:  # plaster, sand, soil, concrete
        t = 0.88 + 0.18 * _noise(rng, 8, 3)
    return np.clip(t, 0, 1.3)


def material(name, m):
    if name == "_invisible":
        return trimesh.visual.material.PBRMaterial(name="Collider_invisible", baseColorFactor=[1, 0, 0, 0], alphaMode="BLEND")
    t = texture(m["type"])[..., None] * np.array(m["color"])[None, None] * 1.1
    img = Image.fromarray((np.clip(t, 0, 1) * 255).astype(np.uint8))
    rough = 0.45 if m["type"] == "metal" else 0.9
    return trimesh.visual.material.PBRMaterial(name=name, baseColorTexture=img, metallicFactor=0.6 if m["type"] == "metal" else 0.0,
                                               roughnessFactor=rough)


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
        m = trimesh.creation.cylinder(radius=min(w, d) / 2, height=h, sections=12)
        m.apply_transform(euler_matrix(-np.pi / 2, 0, 0)); m.apply_translation([0, h / 2, 0]); return m
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
    mats = {k: material(k, m) for k, m in L["materials"].items()}; mats["_invisible"] = material("_invisible", None)
    scene = trimesh.Scene(); base = scene.graph.base_frame; tris = 0
    world = {}  # name -> world matrix (for topdown)
    for o in L["objects"]:
        parent = o.get("parent") or base; T = node_matrix(o)
        world[o["name"]] = (world.get(parent, np.eye(4)) if parent != base else np.eye(4)) @ T
        if o["type"] == "group":
            scene.graph.update(frame_from=parent, frame_to=o["name"], matrix=T); continue
        mk = "_invisible" if o["type"] == "boundary" else o["material"]
        tile = L["materials"].get(mk, {}).get("tile_m", 2.0)
        m, uv = uv_world(shape(o), tile)
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[mk])
        if o["type"] != "boundary": tris += len(m.faces)
        scene.add_geometry(m, node_name=o["name"], geom_name=o["name"], parent_node_name=parent, transform=T)
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
    tc = L["materials"][next(o for o in L["objects"] if o["type"] == "terrain")["material"]]["color"]
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
