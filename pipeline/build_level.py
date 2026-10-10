"""level.json -> level.glb (+ topdown.png). Usage: python3 pipeline/build_level.py levels/<name>
Each object becomes its own named glTF node (children under their parent group); meshes share one material
per material type with procedural tileable PBR maps from materials.py (UVs are world-scaled, so textures never stretch)."""
import io, json, os, sys, numpy as np, trimesh
from PIL import Image, ImageDraw
from trimesh.transformations import euler_matrix, translation_matrix
from materials import make_material
from glb_tools import dedupe_images
import shapes



def material(name, m):
    return make_material(name, m)[0]


def shape(o, bevel=0.0):
    t = o["type"]
    if t == "terrain":
        h = np.array(o["heights"], float); c = o["cell"]; nz, nx = h.shape
        zz, xx = np.mgrid[:nz, :nx] * c
        v = np.c_[xx.ravel(), h.ravel(), zz.ravel()]; i = np.arange(nz * nx).reshape(nz, nx)
        a, b, cc, d = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, 1:].ravel(), i[1:, :-1].ravel()
        f = np.r_[np.c_[a, d, cc], np.c_[a, cc, b]]
        sk = o.get("skirt", 6.0)  # Stage 3: vertical skirt round the edge so the camera never sees under/behind the heightfield
        if sk:
            ring = np.r_[i[0, :], i[1:, -1], i[-1, -2::-1], i[-2:0:-1, 0]]; bot = len(v) + np.arange(len(ring))
            low = v[ring].copy(); low[:, 1] = h.min() - sk; v = np.vstack([v, low])
            n2 = np.roll(np.arange(len(ring)), -1)
            f = np.vstack([f, np.c_[ring, bot, bot[n2]], np.c_[ring, bot[n2], ring[n2]]])
        m = trimesh.Trimesh(v, f, process=False)
        if sk:  # orient skirt faces outward (away from the terrain centre)
            cen = v[:nz * nx].mean(0); sk_f = np.arange(len(f) - 2 * len(ring), len(f))
            out = np.einsum("ij,ij->i", m.face_normals[sk_f], m.triangles_center[sk_f] - cen) < 0
            f[sk_f[out]] = f[sk_f[out]][:, ::-1]; m = trimesh.Trimesh(v, f, process=False)
        return m
    m = shapes.make(o, bevel)  # Stage 3 primitives (bevelled boxes, railings, rocks, cliffs, arches, ...)
    if m is not None: return m
    w, h, d = o["size"]
    if t in ("box", "boundary"):
        m = trimesh.creation.box([w, h, d]); m.apply_translation([0, h / 2, 0]); return m
    if t == "cylinder":
        m = trimesh.creation.cylinder(radius=min(w, d) / 2, height=h, sections=o.get("sections", 12))
        m.apply_transform(euler_matrix(-np.pi / 2, 0, 0)); m.apply_translation([0, h / 2, 0]); return m
    if t == "panel" and o.get("cut"):  # pennant banner / drip / puddle outline (shapes.cut_panel, own UVs)
        return shapes.cut_panel(w, h, o["cut"], o.get("seed", 0), o.get("_layout"))
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


def _outlined(o, OL):
    sz = o.get("size") or [0, 0, 0]
    return (o["type"] not in OL.get("skip_types", []) and o.get("material") not in OL.get("skip_materials", []) and o.get("outline", True)
            and max(sz) >= OL.get("min_size", 0.25) and min(sz) > 0.0)


def _ol_width(o, OL):
    w0, w1 = OL.get("width", [0.05, 0.16]); return float(np.clip(OL.get("rel", 0.012) * max(o["size"]), w0, w1))


def outline_hull(m, w):
    """Inverted hull: the mesh welded, pushed out along its smoothed vertex normals by w, winding flipped. With normal
    back-face culling only its far inner side renders -> a dark silhouette / crease line around the object.
    Name suffix "__ol": every check, navigation and collider export ignores it (not a surface)."""
    h = m.copy(); h.merge_vertices(merge_tex=True, merge_norm=True)
    if len(h.faces) == 0: return None
    vn = h.vertex_normals; h.vertices = h.vertices + vn * w; h.invert(); return h


def build(level_dir):
    L = json.load(open(os.path.join(level_dir, "level.json")))
    TERR = isinstance(L.get("terrain"), dict)  # Stage 9 world terrain (terrain.py): definition in level.json, meshes derived
    if TERR:
        from terrain import Terrain, BIOMES
        for k, v in Terrain(L["terrain"], level_dir).materials().items(): L["materials"].setdefault(k, v)
        L["materials"].setdefault(L["terrain"].get("water_material", "water"), {"type": "water", "color": [0.25, 0.42, 0.48], "tile_m": 6.0})
    mats = {k: material(k, m) for k, m in L["materials"].items()}
    L.setdefault("draw_hint", "one material per surface type; mark static + batch in engine"); mats["_invisible"] = material("_invisible", None)
    OL = (L.get("style") or {}).get("outline")
    if OL: mats["_ink"] = trimesh.visual.material.PBRMaterial(name="ink", baseColorFactor=[*[int(c * 255) for c in OL.get("color", [0.03, 0.01, 0.05])], 255], metallicFactor=0.0, roughnessFactor=1.0)
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
        if o.get("double_sided") and mk != "_invisible":  # visible from behind (panels, thin shells): doubleSided variant
            if mk + "__2s" not in mats:
                mats[mk + "__2s"] = material(mk + "__2s", L["materials"][mk]); mats[mk + "__2s"].doubleSided = True
            mk = mk + "__2s"
        bevel = L["materials"].get(o.get("material"), {}).get("bevel", 0.0)
        key = json.dumps([{k: v for k, v in o.items() if k not in ("name", "position", "rotation", "parent")}, mk, bevel], sort_keys=True)
        if key in geoms:  # identical part (window/door/...) -> reuse the same mesh (glTF instancing)
            scene.graph.update(frame_from=parent, frame_to=o["name"], matrix=T, geometry=geoms[key])
            tris += len(scene.geometry[geoms[key]].faces); continue
        mspec = L["materials"].get(o.get("material"), {})
        if o["type"] == "panel" and not o.get("cut") and mspec.get("panel_cut"):  # e.g. banners: every panel of the material is cut
            o = dict(o, cut=mspec["panel_cut"], _layout=(mspec.get("emblem_aspect", 1.3), tuple(mspec.get("emblem_band", (0.2, 0.8))), o.get("emblem_at")))
        g0 = shape(o, bevel)
        if "uv" in g0.metadata: m, uv = g0, g0.metadata["uv"]  # shapes with their own UVs (grid sheets, cut panels)
        else:
            m, uv = uv_world(g0, tile)
            if o["type"] == "panel": uv = (m.vertices[:, :2] - [-o["size"][0] / 2, 0]) / o["size"][:2]  # whole texture once
        reg = (mspec.get("atlas") or {}).get(o.get("uv_region") or ("banner" if o["type"] == "panel" else None))
        if reg: uv = np.asarray(reg[:2]) + np.asarray(uv) * (np.asarray(reg[2:]) - np.asarray(reg[:2]))  # atlas sub-rectangle
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[mk])
        if o["type"] != "boundary": tris += len(m.faces)
        gname = o["name"] if o["type"] not in ("panel", "cylinder") else f"{o['type']}_{mk}_{len(geoms)}"
        geoms[key] = gname
        scene.add_geometry(m, node_name=o["name"], geom_name=gname, parent_node_name=parent, transform=T)
        if OL and _outlined(o, OL):  # cartoon ink outline: inverted hull baked into the GLB (works in any engine, no shader)
            if key + "__ol" not in geoms:
                hull = outline_hull(shape(o, bevel), _ol_width(o, OL))
                if hull is not None: hull.visual = trimesh.visual.TextureVisuals(material=mats["_ink"]); geoms[key + "__ol"] = gname + "__ol"; scene.add_geometry(hull, geom_name=gname + "__ol", node_name=o["name"] + "__ol", parent_node_name=parent, transform=T)
            else: scene.graph.update(frame_from=parent, frame_to=o["name"] + "__ol", matrix=T, geometry=geoms[key + "__ol"])
    tinfo = None
    if TERR:
        import terrain as TM
        ttris, TR, tinfo = TM.build_into(scene, L, mats, level_dir, material); tris += ttris
        from scatter import build_scatter  # Stage 9 instanced vegetation / rocks (shared meshes, merged per chunk)
        tris += build_scatter(scene, L, TR, mats, material, level_dir, world, tinfo)
    sp = L["spawn"]
    scene.graph.update(frame_from=base, frame_to="PlayerSpawn",
                       matrix=translation_matrix(sp["position"]) @ euler_matrix(0, np.radians(sp["yaw_deg"]), 0))
    glb = os.path.join(level_dir, "level.glb"); scene.export(glb); dedupe_images(glb)
    if TERR:
        from glb_tools import far_material
        far_material(glb)
    from glb_stats import stats
    st = stats(glb)
    L["build_stats"] = dict(triangles=tris, objects=len(L["objects"]), materials=len(L["materials"]), glb_kb=st["glb_kb"],
                            nodes=st["nodes"], draw_calls_unbatched=st["draw_calls_unbatched"], draw_calls_batched_min=st["draw_calls_batched_min"],
                            images=st["images"], tex_mem_gpu_compressed_mb=st["tex_mem_gpu_compressed_mb"],
                            tex_mem_uncompressed_mb=st["tex_mem_uncompressed_mb"], note="GPU numbers are estimates (pipeline/glb_stats.py)")
    if tinfo is not None:
        L["build_stats"]["terrain_triangles_lod0"] = sum(c["triangles_lod0"] for c in tinfo["chunks"])
        TM.write_info(level_dir, L, TR, tinfo)
    elif os.path.exists(os.path.join(level_dir, "terrain.json")): os.remove(os.path.join(level_dir, "terrain.json"))
    json.dump(L, open(os.path.join(level_dir, "level.json"), "w"), indent=1)
    topdown(L, world, os.path.join(level_dir, "topdown.png"), TR if TERR else None)
    print(json.dumps(L["build_stats"]))
    if L.get("environment"):  # Stage 2: sky + distant scenery + Godot environment metadata
        from environment import build_environment
        build_environment(level_dir, L)
    else:  # no environment section: remove stale outputs from an earlier build
        for f in ("background.glb", "environment.json", "environment.tres"):
            if os.path.exists(os.path.join(level_dir, f)): os.remove(os.path.join(level_dir, f))
        import shutil; shutil.rmtree(os.path.join(level_dir, "sky"), ignore_errors=True)
    from effects import build_effects  # Stage 4: effects.json + fx/ (removes stale outputs when the level has no effects)
    build_effects(level_dir, L)
    if L.get("mobile", {}).get("export", True):  # Stage 5: keep mobile/ in sync with every build ("mobile": {"export": false} to skip)
        from export_mobile import export
        export(level_dir)


def topdown(L, world, path, TR=None, px=10):
    b0, b1 = np.array(L["bounds"]["min"]) - 4, np.array(L["bounds"]["max"]) + 4
    if TR is not None:  # whole detailed terrain, coloured by material layer + hill shading
        b0, b1 = np.array([TR.x0, 0, TR.z0]), np.array([TR.x1, 0, TR.z1]); px = max(2, min(10, int(2400 / max(b1[0] - b0[0], b1[2] - b0[2]))))
    W, H = int((b1[0] - b0[0]) * px), int((b1[2] - b0[2]) * px)
    img = Image.new("RGB", (W, H), (40, 44, 40)); dr = ImageDraw.Draw(img)
    ter = next((o for o in L["objects"] if o["type"] == "terrain"), None)
    tc = L["materials"][ter["material"]]["color"] if ter else [0.1, 0.1, 0.1]
    xy = lambda x, z: ((x - b0[0]) * px, (z - b0[2]) * px)
    if TR is not None:
        img = Image.fromarray(TR.map_image(L)).resize((W, H), Image.BILINEAR); dr = ImageDraw.Draw(img)
    else:
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
