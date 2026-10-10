"""Stage 5: mobile-optimised export (level.json stays the editable master; level.glb stays the dev export).

  python3 pipeline/export_mobile.py levels/<name> [--profile performance|balanced|quality]

Writes levels/<name>/mobile/:
  level_mobile.glb     static meshes MERGED by material inside spatial cells (draw calls down, frustum culling still
                       works); small props merged into separate cells with a view distance; objects that effects animate
                       per node, hazards and the spawn marker stay separate nodes with their original names. Faces hidden
                       under opaque hazard liquid are removed. Textures capped per profile. Node extras = source objects.
  background_mobile.glb  background with textures capped per profile
  collision.json       authoritative lightweight colliders from level.json shapes (box/cylinder/convex/heightmap),
                       stairs as ramps, arches keep their opening, panels/decals excluded, hazards as areas
  collision.glb        same colliders as meshes named "<name>-convcolonly" / "-colonly" (Godot import creates static bodies)
  mobile_manifest.json merge map (node -> source objects), per-node shadows + visibility ranges, Godot import settings,
                       dev-vs-mobile metrics incl. estimated visible draw calls from sampled third-person cameras
  apply_mobile.gd      Godot starter (UNTESTED): visibility ranges, shadow flags, hazard Area3Ds from the manifest
"""
import json, math, os, shutil, sys, numpy as np, trimesh
from trimesh.transformations import quaternion_from_matrix
from glb_tools import dedupe_images, downscale_images, set_node_extras, restore_images
from glb_stats import stats

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES = {
    "performance": dict(cell=64, tex_max=256, bg_tex_max=64, prop_range=45, small=2.0),
    "balanced": dict(cell=48, tex_max=512, bg_tex_max=128, prop_range=70, small=2.0),
    "quality": dict(cell=32, tex_max=1024, bg_tex_max=256, prop_range=110, small=2.0),
}
NO_COLLISION = {"panel", "group"}
CONVEX_FROM_MESH = {"rock", "cliff", "tank", "machinery", "spire", "roof", "pipe_elbow", "vent", "ramp"}


def world_matrices(L):
    from build_level import node_matrix
    W, by = {}, {o["name"]: o for o in L["objects"]}
    def get(n):
        if n not in W:
            o = by[n]; W[n] = (get(o["parent"]) if o.get("parent") in by else np.eye(4)) @ node_matrix(o)
        return W[n]
    for n in by: get(n)
    return W, by


def quat_xyzw(M):
    w, x, y, z = quaternion_from_matrix(M); return [round(float(v), 5) for v in (x, y, z, w)]


def colliders(L, level_dir=None):
    """Lightweight collision primitives in world space from level.json (not from render meshes)."""
    import shapes
    from build_level import shape as render_shape
    W, by = world_matrices(L); hazards = set(L.get("hazards", [])); out, haz = [], []
    hazard_mats = {by[h].get("material") for h in hazards if h in by}  # e.g. toxic falls share the pool's material -> also hazards
    hazards |= {o["name"] for o in L["objects"] if o.get("material") in hazard_mats and o.get("collision") is not True}
    for o in L["objects"]:
        t = o["type"]; M = W[o["name"]]
        if t in NO_COLLISION or o.get("collision") is False: continue
        if t == "stream" and o["name"] not in hazards: continue  # Stage 8: liquid is never a solid collider
        if o["name"] in hazards:
            b = render_shape(o).bounds; c = np.array([[x, y, z, 1] for x in b[:, 0] for y in b[:, 1] for z in b[:, 2]]) @ M.T
            haz.append(dict(name=o["name"], shape="box_area", center=((c[:, :3].min(0) + c[:, :3].max(0)) / 2).round(3).tolist(),
                            size=(c[:, :3].max(0) - c[:, :3].min(0)).round(3).tolist(), rotation=[0, 0, 0, 1])); continue
        R = M.copy(); R[:3, 3] = 0
        def box(nm, w, h, d, local=(0, 0, 0)):
            c = M @ [local[0], local[1] + h / 2, local[2], 1]
            out.append(dict(name=nm, source=o["name"], shape="box", center=c[:3].round(3).tolist(), size=[round(w, 3), round(h, 3), round(d, 3)], rotation=quat_xyzw(R)))
        if t == "terrain":
            out.append(dict(name=o["name"], source=o["name"], shape="heightmap", origin=M[:3, 3].round(3).tolist(), cell=o["cell"], heights=o["heights"]))
            continue
        if o.get("collision_mesh"):  # concave on purpose (cave, arch, overhang, tunnel berm): a hull would fill the opening
            m = render_shape(o); v = (np.c_[m.vertices, np.ones(len(m.vertices))] @ M.T)[:, :3]
            out.append(dict(name=o["name"], source=o["name"], shape="mesh", vertices=v.round(3).tolist(), faces=m.faces.tolist())); continue
        w, h, d = o["size"]
        if t in ("box", "boundary", "railing", "ibeam"):
            box(o["name"], w, h, d)
        elif t == "cylinder":
            c = M @ [0, h / 2, 0, 1]
            out.append(dict(name=o["name"], source=o["name"], shape="cylinder", center=c[:3].round(3).tolist(), radius=round(min(w, d) / 2, 3), height=round(h, 3), rotation=quat_xyzw(R)))
        elif t == "arch":  # keep the opening passable: two piers + lintel
            ow = w * o.get("opening", 0.6); oh = h * o.get("opening_h", 0.75); pw = (w - ow) / 2
            box(o["name"] + "_PierL", pw, h, d, (-(ow + pw) / 2, 0, 0)); box(o["name"] + "_PierR", pw, h, d, ((ow + pw) / 2, 0, 0))
            box(o["name"] + "_Lintel", ow, h - oh, d, (0, oh, 0))
        elif t == "stairs":  # smooth ramp collider: friendlier for character controllers, far fewer shapes
            pts = np.array([[-w/2, 0, -d/2], [w/2, 0, -d/2], [-w/2, 0, d/2], [w/2, 0, d/2], [-w/2, h, d/2], [w/2, h, d/2]])
            out.append(dict(name=o["name"], source=o["name"], shape="convex", points=(np.c_[pts, np.ones(6)] @ M.T)[:, :3].round(3).tolist()))
        elif t in CONVEX_FROM_MESH or t in shapes.SHAPES:
            hull = render_shape(o).convex_hull; v = hull.vertices
            if len(v) > 32: v = trimesh.convex.convex_hull(v[np.linspace(0, len(v) - 1, 32).astype(int)]).vertices  # cap point count
            out.append(dict(name=o["name"], source=o["name"], shape="convex", points=(np.c_[v, np.ones(len(v))] @ M.T)[:, :3].round(3).tolist()))
    if isinstance(L.get("terrain"), dict):  # Stage 9: one HeightMapShape3D per terrain chunk + scatter trunks / boulders
        from terrain import Terrain
        TR = Terrain(L["terrain"], level_dir)
        for i, j in TR.chunk_ids(): out.append(dict(name=f"TR_{i}_{j}", source="terrain", **TR.collider(i, j)))
        tj = os.path.join(level_dir or ".", "terrain.json")
        if level_dir and os.path.exists(tj):
            from scatter import colliders as sc_col
            out += sc_col(L, json.load(open(tj)))
    return out, haz


def collider_mesh(c):
    if c["shape"] == "box":
        m = trimesh.creation.box(c["size"]); x, y, z, w = c["rotation"]
        T = trimesh.transformations.quaternion_matrix([w, x, y, z]); T[:3, 3] = c["center"]; m.apply_transform(T); return m
    if c["shape"] == "cylinder":
        m = trimesh.creation.cylinder(radius=c["radius"], height=c["height"], sections=12)
        m.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 2, [1, 0, 0])); x, y, z, w = c["rotation"]
        T = trimesh.transformations.quaternion_matrix([w, x, y, z]); T[:3, 3] = c["center"]; m.apply_transform(T); return m
    if c["shape"] == "convex":
        return trimesh.convex.convex_hull(np.array(c["points"]))
    if c["shape"] == "mesh":
        return trimesh.Trimesh(np.array(c["vertices"]), np.array(c["faces"]), process=False)
    if c["shape"] == "heightmap":
        h = np.array(c["heights"], float); nz, nx = h.shape; zz, xx = np.mgrid[:nz, :nx] * c["cell"]
        v = np.c_[xx.ravel(), h.ravel(), zz.ravel()] + c["origin"]; i = np.arange(nz * nx).reshape(nz, nx)
        a, b, cc, d = i[:-1, :-1].ravel(), i[:-1, 1:].ravel(), i[1:, 1:].ravel(), i[1:, :-1].ravel()
        return trimesh.Trimesh(v, np.r_[np.c_[a, d, cc], np.c_[a, cc, b]])


# ---------------------------------------------------------------- visible draw-call estimate (frustum + distance culling)
def frustum_planes(pos, yaw, pitch, vfov=70, aspect=19.5 / 9, far=800):
    f = np.array([-math.sin(yaw) * math.cos(pitch), math.sin(pitch), -math.cos(yaw) * math.cos(pitch)])
    r = np.cross(f, [0, 1, 0]); r /= np.linalg.norm(r); u = np.cross(r, f)
    tv = math.tan(math.radians(vfov) / 2); th = tv * aspect; P = []
    for n in (np.cross(u, f + r * th), np.cross(f - r * th, u), np.cross(r, f - u * tv), np.cross(f + u * tv, r)):
        n = n / np.linalg.norm(n); P.append((n, -n @ pos))
    P.append((f, -f @ pos - 0.1)); P.append((-f, f @ pos + far)); return P


def visible(boxes, planes):
    lo, hi = boxes[:, 0], boxes[:, 1]; ok = np.ones(len(boxes), bool)
    for n, d in planes:
        p = np.where(n > 0, hi, lo); ok &= (p @ n + d) >= 0
    return ok


def node_list(glb, ranges=None):
    """[(node, aabb, triangles, (range_begin, range_end))]; ranges: node -> end or (begin, end)."""
    s = trimesh.load(glb, force="scene"); out = []
    for node in s.graph.nodes_geometry:
        M, g = s.graph[node]; m = s.geometry[g]; b = m.bounds
        c = np.array([[x, y, z, 1] for x in b[:, 0] for y in b[:, 1] for z in b[:, 2]]) @ M.T
        r = (ranges or {}).get(node, 0); r = r if isinstance(r, tuple) else (0, r)
        out.append((node, np.array([c[:, :3].min(0), c[:, :3].max(0)]), len(m.faces), r))
    return out


def estimate(L, nodes, far=800):
    pts = [L["spawn"]["position"]] + [[(w["min"][0] + w["max"][0]) / 2, w["y"], (w["min"][1] + w["max"][1]) / 2] for w in L.get("walkable", [])]
    B = np.array([n[1] for n in nodes]); T = np.array([n[2] for n in nodes]); R = np.array([n[3][1] for n in nodes], float); R0 = np.array([n[3][0] for n in nodes], float)
    C = (B[:, 0] + B[:, 1]) / 2; draws, tris = [], []
    for p in pts:
        head = np.array(p, float) + [0, 1.9, 0]
        for yaw in np.radians(np.arange(0, 360, 45)):
            cam = head + 5 * np.array([math.sin(yaw), 0.35, math.cos(yaw)]) / np.linalg.norm([1, 0.35])  # behind & above
            vis = visible(B, frustum_planes(cam, yaw, math.radians(-12), far=far))
            dist = np.linalg.norm(C - cam, axis=1); vis &= ((R <= 0) | (dist <= R)) & (dist >= R0)  # visibility_range_begin / end
            draws.append(int(vis.sum())); tris.append(int(T[vis].sum()))
    return dict(cameras=len(draws), visible_draw_calls_mean=round(float(np.mean(draws)), 1), visible_draw_calls_max=int(max(draws)),
                visible_triangles_mean=int(np.mean(tris)), visible_triangles_max=int(max(tris)))


def _terrain_mobile(L, level_dir, src, nodes, scene, manifest_nodes, ranges, extras, glow):
    """Stage 9: terrain chunks as LOD0/1/2 nodes with complementary visibility ranges (borders full-res: crack-free at
    any LOD mix), middle ring + water as plain nodes, scatter nodes with their view distance (vegetation stops there)."""
    from terrain import Terrain, textured, lod_settings, shifted
    from materials import make_material
    TR = Terrain(L["terrain"], level_dir); r0, r1 = lod_settings(L["terrain"])["ranges"]; mobj = {}
    for node, M, g in nodes: mobj[src.geometry[g].visual.material.name] = src.geometry[g].visual.material
    tj = os.path.join(level_dir, "terrain.json"); inst = json.load(open(tj)).get("instances", {}) if os.path.exists(tj) else {}
    margin = 4.0
    for i, j in TR.chunk_ids():
        b = TR.chunk_bounds(i, j); G = TR.grid(); C = TR.C
        c = np.array([(b[0] + b[2]) / 2, float(G["H"][i * C:(i + 1) * C + 1, j * C:(j + 1) * C + 1].mean()), (b[1] + b[3]) / 2])
        for lod, (rb, re) in enumerate(((0, r0 + margin), (r0, r1 + margin), (r1, 0))):
            for mname, m in sorted(TR.chunk_mesh(i, j, lod, broad=lod > 0, far=lod == 2, L=L).items()):
                if mname not in mobj and mname != "ter_far": mobj[mname] = make_material(mname, L["materials"][mname])[0]
                m = shifted(m, -c); textured(m, mobj.get(mname)); node = f"TR_{i}_{j}_{mname[4:]}_L{lod}"
                if mname == "ter_far": node = f"TR_{i}_{j}_L2_far"
                scene.add_geometry(m, node_name=node, geom_name=node, transform=trimesh.transformations.translation_matrix(c)); ranges[node] = (rb, re)
                info = dict(node=node, kind=f"terrain_lod{lod}", material=mname, triangles=int(len(m.faces)), visibility_range_begin=rb, visibility_range_end=re,
                            cast_shadow=lod == 0, source_objects=[f"terrain chunk TR_{i}_{j}"])
                manifest_nodes.append(info); extras[node] = dict(kind=info["kind"], chunk=f"TR_{i}_{j}", lod=lod, visibility_range_begin=rb, visibility_range_end=re,
                                                               visibility_range_margin=margin, cast_shadow=lod == 0)
    for node, M, g in nodes:
        if node.startswith("TR_"): continue
        m = src.geometry[g]; mat = m.visual.material.name; rng = 0; kind = {"TRM": "terrain_middle", "TW": "water"}.get(node.split("_")[0], "scatter")
        if kind == "scatter":
            sid = node.split("_", 1)[1].split("__")[0]; rng = inst.get(sid, {}).get("nodes", {}).get(node, 160)
        scene.add_geometry(m, node_name=node, geom_name=node, transform=M); ranges[node] = (0, rng)
        manifest_nodes.append(dict(node=node, kind=kind, material=mat, triangles=int(len(m.faces)), visibility_range_end=rng,
                                   cast_shadow=kind == "scatter" and node.startswith("SC_"), source_objects=[node],
                                   reason={"terrain_middle": "middle zone (no collision, not playable)", "water": "water surface", "scatter": "instanced scatter (merged per cell)"}[kind]))
        extras[node] = dict(kind=kind, visibility_range_end=rng, cast_shadow=manifest_nodes[-1]["cast_shadow"])


# ---------------------------------------------------------------- export
def export(level_dir, profile=None):
    L = json.load(open(os.path.join(level_dir, "level.json"))); mob = L.get("mobile", {})
    profile = profile or mob.get("profile") or L.get("environment", {}).get("quality", "balanced"); P = PROFILES[profile]
    out_dir = os.path.join(level_dir, "mobile"); os.makedirs(out_dir, exist_ok=True)
    fxp = os.path.join(level_dir, "effects.json"); FX = json.load(open(fxp)) if os.path.exists(fxp) else {"effects": []}
    keep = set(L.get("hazards", [])) | {o["name"] for o in L["objects"] if o.get("mobile", {}).get("merge") is False}
    fx_merge = {}  # node -> merged FX node: an effect's shader targets become ONE node (one draw call, one material override)
    for e in FX["effects"]:
        if e["category"] == "surface_shader":
            tg = e.get("targets", []); keep |= set(tg)
            if len(tg) > 1 and not set(tg) & set(L.get("hazards", [])):
                for n in tg: fx_merge[n] = "FX_" + e["id"]
    by = {o["name"]: o for o in L["objects"]}
    cull_y = mob.get("cull_below_y")
    if cull_y is None and L.get("hazards"):
        cull_y = max(o["position"][1] + o["size"][1] for o in L["objects"] if o["name"] in L["hazards"] and o.get("size"))
    src = trimesh.load(os.path.join(level_dir, "level.glb"), force="scene")
    scene = trimesh.Scene(); groups, removed = {}, 0; separate = []; terrain_nodes = []
    for node in src.graph.nodes_geometry:
        M, g = src.graph[node]; m0 = src.geometry[g]; mat = getattr(getattr(m0.visual, "material", None), "name", "")
        if node.startswith("Boundary") or mat == "Collider_invisible": continue  # invisible walls live in collision only
        if node.startswith(("TR_", "TRM_", "TW_", "SC_", "SCN_")): terrain_nodes.append((node, M, g)); continue  # Stage 9: handled below
        if node in keep or by.get(node, {}).get("mobile", {}).get("merge") is False:
            separate.append((node, M, g)); continue
        m = m0.copy(); m.apply_transform(M)
        if cull_y is not None:  # faces entirely under opaque hazard liquid can never be seen
            hid = m.triangles[:, :, 1].max(1) < cull_y - 0.01
            if hid.any():
                removed += int(hid.sum()); m.update_faces(~hid); m.remove_unreferenced_vertices()
                if not len(m.faces): continue
        size = np.ptp(m.bounds, 0); c = m.bounds.mean(0); small = size.max() < P["small"]
        key = ("P" if small else "S", int(c[0] // P["cell"]), int(c[2] // P["cell"]), mat)
        groups.setdefault(key, []).append((node, m))
    manifest_nodes, ranges, extras = [], {}, {}
    glow = {k for k, v in L["materials"].items() if v.get("emissive")}
    for (kind, ix, iz, mat), items in sorted(groups.items()):
        name = f"M_{mat}_{ix}_{iz}" + ("_props" if kind == "P" else "")
        m = trimesh.util.concatenate([i[1] for i in items])
        m.merge_vertices(merge_tex=False, merge_norm=False)  # weld only identical position+UV (flat shading kept)
        scene.add_geometry(m, node_name=name, geom_name=name)
        rng = P["prop_range"] if kind == "P" else 0; ranges[name] = rng
        info = dict(node=name, kind="props" if kind == "P" else "static", material=mat, triangles=int(len(m.faces)),
                    visibility_range_end=rng, cast_shadow=not (mat.split("__")[0] in glow or kind == "P"), source_objects=[i[0] for i in items])
        manifest_nodes.append(info); extras[name] = {k: info[k] for k in ("kind", "source_objects", "visibility_range_end", "cast_shadow")}
        extras[name]["source_bounds"] = {n: [round(float(v), 2) for v in mm.bounds.ravel()] for n, mm in items}  # tap-to-identify in merged meshes
    fx_groups = {}
    for node, M, g in [x for x in separate if x[0] in fx_merge]:
        m = src.geometry[g].copy(); m.apply_transform(M); fx_groups.setdefault(fx_merge[node], []).append((node, m))
    for name, items in fx_groups.items():
        m = trimesh.util.concatenate([i[1] for i in items]); m.merge_vertices(merge_tex=False, merge_norm=False)
        scene.add_geometry(m, node_name=name, geom_name=name); mat = m.visual.material.name
        manifest_nodes.append(dict(node=name, kind="effect_target", material=mat, triangles=int(len(m.faces)), visibility_range_end=0,
                                   cast_shadow=mat.split("__")[0] not in glow, source_objects=[i[0] for i in items], reason="merged targets of one shader effect"))
        extras[name] = dict(kind="effect_target", source_objects=[i[0] for i in items],
                            source_bounds={n: [round(float(v), 2) for v in mm.bounds.ravel()] for n, mm in items})
    separate = [x for x in separate if x[0] not in fx_merge]
    for node, M, g in separate:
        scene.add_geometry(src.geometry[g], node_name=node, geom_name=g, transform=M)
        mat = src.geometry[g].visual.material.name
        manifest_nodes.append(dict(node=node, kind="separate", material=mat, triangles=int(len(src.geometry[g].faces)), visibility_range_end=0,
                                   cast_shadow=mat.split("__")[0] not in glow, source_objects=[node],
                                   reason="hazard" if node in L.get("hazards", []) else "animated by an effect / merge disabled"))
    if terrain_nodes: _terrain_mobile(L, level_dir, src, terrain_nodes, scene, manifest_nodes, ranges, extras, glow)
    sp = L["spawn"]; scene.graph.update(frame_from=scene.graph.base_frame, frame_to="PlayerSpawn",
                                        matrix=trimesh.transformations.translation_matrix(sp["position"]) @ trimesh.transformations.euler_matrix(0, math.radians(sp["yaw_deg"]), 0))
    lg = os.path.join(out_dir, "level_mobile.glb"); scene.export(lg); restore_images(lg, os.path.join(level_dir, "level.glb")); dedupe_images(lg)
    downscale_images(lg, P["tex_max"]); set_node_extras(lg, extras)
    if terrain_nodes:
        from glb_tools import far_material
        far_material(lg)
    if FX["effects"]:  # effects.json for the mobile scene: shader targets renamed to their merged FX node
        FXm = json.loads(json.dumps(FX)); src2node = {s_: mn["node"] for mn in manifest_nodes for s_ in mn.get("source_objects", [])}
        for e in FXm["effects"]:
            if e.get("targets"):  # FX-merged node, else the merged cell node that now contains the object
                e["targets"] = sorted({fx_merge.get(n) or src2node.get(n, n) for n in e["targets"]})
        FXm["note"] = "Mobile copy of ../effects.json: targets renamed to merged nodes of level_mobile.glb. " + FX.get("note", "")
        json.dump(FXm, open(os.path.join(out_dir, "effects_mobile.json"), "w"), indent=1)
    bg_src = os.path.join(level_dir, "background.glb"); bg = None
    if os.path.exists(bg_src):
        bg = os.path.join(out_dir, "background_mobile.glb"); shutil.copy(bg_src, bg); downscale_images(bg, P["bg_tex_max"])
    cols, haz = colliders(L, level_dir)
    json.dump(dict(note="World-space colliders generated from level.json shapes. Godot: BoxShape3D / CylinderShape3D / ConvexPolygonShape3D / "
                        "HeightMapShape3D (cell size = 'cell'). Hazards are areas (Area3D), not solid.", colliders=cols, hazards=haz),
              open(os.path.join(out_dir, "collision.json"), "w"), indent=1)
    cs = trimesh.Scene()
    for c in cols:
        m = collider_mesh(c); suffix = "-colonly" if c["shape"] == "heightmap" else "-convcolonly"
        cs.add_geometry(m, node_name=c["name"] + suffix, geom_name=c["name"] + suffix)
    cg = os.path.join(out_dir, "collision.glb"); cs.export(cg)
    shutil.copy(os.path.join(HERE, "godot_fx", "apply_mobile.gd"), out_dir)
    if isinstance(L.get("terrain"), dict): shutil.copy(os.path.join(HERE, "godot_fx", "apply_scatter_multimesh.gd"), out_dir)
    elif os.path.exists(os.path.join(out_dir, "apply_scatter_multimesh.gd")): os.remove(os.path.join(out_dir, "apply_scatter_multimesh.gd"))
    # ---- metrics: dev vs mobile (file + estimated visible draw calls from sampled third-person cameras)
    dev_glb = os.path.join(level_dir, "level.glb"); far = 800
    dev_nodes = [n for n in node_list(dev_glb) if not n[0].startswith("Boundary")]
    mob_nodes = node_list(lg, ranges); bg_nodes = node_list(bg_src) if bg else []
    fx_q = FX.get("totals", {}).get(profile, {})
    metrics = dict(profile=profile, note="File numbers are measured; draw calls / triangles visible and GPU memory are ESTIMATES (no device benchmark).",
                   dev=dict(level=stats(dev_glb), visible=estimate(L, dev_nodes + bg_nodes, far)),
                   mobile=dict(level=stats(lg), background=stats(bg) if bg else None, collision=dict(colliders=len(cols), hazards=len(haz), glb_kb=round(os.path.getsize(cg) / 1024)),
                               visible=estimate(L, mob_nodes + bg_nodes, far), hidden_faces_removed=removed, effects_extra_draw_calls=fx_q.get("extra_draw_calls", 0),
                               effects_max_particles=fx_q.get("max_particles", 0)))
    godot = dict(project_settings={"rendering/textures/vram_compression/import_etc2_astc": True, "rendering/renderer/rendering_method.mobile": "mobile",
                                   "rendering/lights_and_shadows/directional_shadow/size.mobile": 2048, "rendering/anti_aliasing/quality/msaa_3d": "2x"},
                 import_level_glb={"meshes/generate_lods": True, "meshes/light_baking": "Static Lightmaps (optional)", "textures": "VRAM Compressed (Godot compresses embedded images to ASTC/ETC2 on import)"},
                 import_collision_glb="nodes named *-convcolonly / *-colonly become StaticBody3D colliders; meshes are discarded",
                 directional_light={"shadow_enabled": True, "directional_shadow_mode": "PSSM 2 splits", "directional_shadow_max_distance": 60},
                 note="Settings are recommendations for Godot 4 mobile; not verified in Godot here. KTX2/Basis is not used: Godot re-compresses on import.")
    M = dict(generated_by="image-to-level Stage 5 (pipeline/export_mobile.py)", profile=profile, settings=P, files=dict(
        level="level_mobile.glb", background="background_mobile.glb" if bg else None, collision="collision.glb", collision_data="collision.json",
        effects="effects_mobile.json" if FX["effects"] else None, environment="../environment.json"), godot=godot, metrics=metrics, nodes=manifest_nodes)
    json.dump(M, open(os.path.join(out_dir, "mobile_manifest.json"), "w"), indent=1)
    d, mm = metrics["dev"], metrics["mobile"]
    print(json.dumps(dict(profile=profile, dev=dict(kb=d["level"]["glb_kb"], tris=d["level"]["triangles"], draws=d["level"]["draw_calls_unbatched"], vis=d["visible"]["visible_draw_calls_mean"]),
                          mobile=dict(kb=mm["level"]["glb_kb"], tris=mm["level"]["triangles"], draws=mm["level"]["draw_calls_unbatched"], vis=mm["visible"]["visible_draw_calls_mean"],
                                      tex_gpu_mb=mm["level"]["tex_mem_gpu_compressed_mb"], colliders=len(cols), hidden_faces_removed=removed))))
    return M


if __name__ == "__main__":
    prof = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else None
    export(sys.argv[1], prof)
