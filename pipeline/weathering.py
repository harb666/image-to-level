"""Weathering decals (Stage 13): green slime leaking from SOME structures, chosen at random but reproducibly.

  spec "leaks": {"chance": 0.4, "material": "accent", "seed": 0, "kinds": ["tower", "building"], "max_drips": 3}

Per chosen structure: runs of slime down one or two faces (from under the cap / under a strap band / from a side
conduit), sometimes a puddle where a run reaches the floor. Decals are flat cut panels (shapes.cut_panel "drip" /
"blob") a few cm in front of the face: visual only (collision false, ignored by navigation and colliders), static
for the mobile merge. With an atlas material (alien_cartoon "accent": banner + "drip" / "puddle" cells) they add
no material and no draw call. They keep clear of the banners so emblems stay readable.
"""
import hashlib, math
import numpy as np

DEFAULTS = dict(chance=0.4, material="slime", seed=0, kinds=["tower", "building"], max_drips=3)


def _rng(*key):
    return np.random.default_rng(int(hashlib.sha1("|".join(map(str, key)).encode()).hexdigest()[:8], 16))


def _rot(x, z, yaw):
    a = math.radians(yaw); return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def leaks(ctx, spec):
    cfg = dict(DEFAULTS, **(spec.get("leaks") or {}))
    if not spec.get("leaks") or cfg["chance"] <= 0: return 0
    by = {o["name"]: o for o in ctx.objects}; mat = cfg["material"]; n_dec = 0
    for s in spec.get("structures", []):
        if s.get("kind") not in cfg["kinds"] or s["id"] not in by or by[s["id"]]["type"] != "group": continue
        rng = _rng(cfg["seed"], s["id"])
        if rng.random() >= cfg["chance"]: continue
        ctx.element = (s["id"], s.get("source", "visible")); g = s["id"]; w, h, d = s.get("size", [4, 8, 4]); dec = s.get("decor") or []
        tower = s["kind"] == "tower"
        floor = max(0.6, min(1.2, h * 0.06)) if (tower and "hazard" in dec and h > 4) else 0.05  # plinth top (drips end above it)
        bw = min(2.6, w * 0.4) if (tower and "banners" in dec) else 0.0
        faces = [(0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d)]
        if not tower: faces = faces[1:]  # buildings: windows + door on the front, slime on sides / back
        pick = rng.choice(len(faces), size=min(len(faces), 1 + int(rng.random() < 0.45)), replace=False)
        k_tot = 0
        for fi in pick:
            px, pz, fy, fw = faces[fi]; lim = fw / 2 - 0.45
            spans = [(-lim, -bw / 2 - 0.12), (bw / 2 + 0.12, lim)] if bw else [(-lim, lim)]
            spans = [sp for sp in spans if sp[1] - sp[0] > 0.35]
            if not spans: continue
            tops = [h] + ([h * f for f in (0.42, 0.7)] if tower and "bands" in dec and h > 6 else [])
            for j in range(int(rng.integers(1, cfg["max_drips"] + 1))):
                if k_tot >= cfg["max_drips"] + 1: break
                a, b = spans[int(rng.integers(len(spans)))]; dw = float(min(b - a, rng.uniform(0.6, 1.3)))
                cx = float(rng.uniform(a + dw / 2, b - dw / 2)); top = float(tops[int(rng.integers(len(tops)))])
                L = float(min(top - floor - 0.05, rng.uniform(0.25, 0.65) * h))
                if L < 0.8: continue
                ox, oz = _rot(cx, 0.05, fy); k_tot += 1; n_dec += 1
                ctx.add(f"{g}_Leak_{k_tot:02d}", "panel", [px + ox, top - L, pz + oz], [round(dw, 2), round(L, 2), 0], mat, g, [0, fy, 0],
                        cut="drip", seed=int(rng.integers(1 << 30)), uv_region="drip", collision=False, outline=False, mobile={"static": True})
                if top - L <= floor + 0.6 and rng.random() < 0.7:  # reached the floor: a puddle spreading in front of the face
                    _puddle(ctx, g, mat, rng, px, pz, fy, cx, (0.25 if floor > 0.1 else 0.0) + 0.05, f"{g}_Puddle_{k_tot:02d}"); n_dec += 1
        if tower and "pipes" in dec and h > 6 and rng.random() < 0.5:  # a side conduit leaking from its top joint
            k = 1 if rng.random() < 0.5 else 3; px, pz, fy, fw = faces[k]; sd = -1 if rng.random() < 0.5 else 1
            L = float(rng.uniform(0.3, 0.8) * h * 0.92); top = h * 0.92 - 0.2; ox, oz = _rot(sd * fw * 0.18, 0.35, fy); k_tot += 1; n_dec += 1
            ctx.add(f"{g}_Leak_{k_tot:02d}", "panel", [px + ox, max(floor, top - L), pz + oz], [0.26, round(min(L, top - floor), 2), 0], mat, g, [0, fy, 0],
                    cut="drip", seed=int(rng.integers(1 << 30)), uv_region="drip", collision=False, outline=False, mobile={"static": True})
            if top - L <= floor + 0.6: _puddle(ctx, g, mat, rng, px, pz, fy, sd * fw * 0.18, 0.5, f"{g}_Puddle_{k_tot:02d}"); n_dec += 1
    ctx.element = None
    if n_dec: ctx.notes.append(f"leaks: {n_dec} slime decals (visual only) on structures picked with chance {cfg['chance']}")
    return n_dec


def _puddle(ctx, g, mat, rng, px, pz, fy, cx, out, name):
    """Flat slime puddle on the floor of the structure's group (y 0.04), centred `out` m + its half depth in front of the
    face, under the drip at lateral offset cx."""
    pw, pd = float(rng.uniform(1.0, 2.2)), float(rng.uniform(0.7, 1.4))
    ox, oz = _rot(cx, out + pd / 2, fy); cx_, cz_ = px + ox, pz + oz
    sx, sz = _rot(0, pd / 2, fy)  # blob centre: local (0, h/2) -> after rotation [-90, fy, 0] at Ry(fy)(0, 0, -h/2) = -(sx, sz)
    ctx.add(name, "panel", [cx_ + sx, 0.04, cz_ + sz], [round(pw, 2), round(pd, 2), 0], mat, g, [-90, fy, 0],
            cut="blob", seed=int(rng.integers(1 << 30)), uv_region="puddle", collision=False, outline=False, mobile={"static": True})


def crate_skin(ctx, spec):
    """Printed crates: when the accent material is an atlas with "crate_side" / "crate_top" cells (alien_cartoon), every
    crate (crates structures, platform cover crates) becomes a plain box: glyph print ("crate_front") on one pair of
    faces (picked per crate), plain plate ("crate_side") on the other pair, lid on top. Same size and position (same collider, same cover); accent material + mobile static merge, so
    no extra draw call; outlined like the rest of the cartoon world."""
    A = ((spec.get("materials", {}).get("roles", {}).get("accent") or {}).get("atlas") or {})
    if not ("crate_side" in A and "crate_top" in A): return 0
    groups = {s["id"] for s in spec.get("structures", []) if s.get("kind") == "crates"}; n = 0
    for o in ctx.objects:
        if o["type"] == "box" and (o.get("parent") in groups or "_Cover_" in o["name"]):
            fa = "zx"[_rng("crate", o["name"]).integers(2)]  # which pair of faces carries the glyph: varies crate to crate
            o.update(material=ctx.role("accent"), faces={"side": A["crate_side"], "top": A["crate_top"], "front": A.get("crate_front"), "front_axis": fa},
                     outline=True, mobile={"static": True}); n += 1
    if n: ctx.notes.append(f"crates: {n} printed crates (accent atlas)")
    return n


CORR = dict(height=1.2, sink=0.15, offset=0.021, material="corrosion", tile=4.0, skirt=2.2, skirt_material="structure_b", unlit=["structure"], light_clear=1.6)


def corrosion(ctx, spec):
    """Stage 28: corroded band where the toxic liquid meets walls / bases (spec "corrosion": {"height": 1.2}; on by
    default since Stage 34, "corrosion": false turns it off). Everything in or standing on the liquid gets it.
    Every solid crossing a liquid surface is cut at the surface; its near-vertical faces that face open liquid (not
    pressed against a neighbour) get a strip 2.1 cm in front (an odd gap: trims sit 3 / 5 cm proud), from just under the surface to "height" m above it (never
    above the solid's top). All strips are ONE object (type "band", material "corrosion": a small cut-out texture of
    pits and green crust) -> one mesh, one material, one draw call; visual only (no collision, ignored by navigation)."""
    if spec.get("corrosion") is False: return 0  # Stage 34: on by default wherever a hazard pool exists
    import trimesh
    from build_level import shape as _shape  # every type (plain boxes / cylinders too), same local frame as the GLB
    from anchors import world_matrices
    cfg = dict(CORR, **(spec.get("corrosion") if isinstance(spec.get("corrosion"), dict) else {}))
    by = {o["name"]: o for o in ctx.objects}
    pools = []
    for h in getattr(ctx, "hazards", []):
        o = by.get(h)
        if o and o["type"] == "box" and not o.get("parent") and not o.get("rotation", [0, 0, 0])[1]:
            (x, y, z), (w, hh, d) = o["position"], o["size"]; pools.append((y + hh, x - w / 2, z - d / 2, x + w / 2, z + d / 2))
    if not pools: return 0
    W, _ = world_matrices({"objects": ctx.objects})
    skip_t = {"group", "panel", "stream", "boundary", "terrain", "band", "railing", "rail_run"}
    skip_m = {"hazard", "glass", "glow", "stripe", "ink", "accent", "screen", "bigscreen", cfg["material"]}
    hz = set(getattr(ctx, "hazards", []))
    solids = []
    for o in ctx.objects:
        if o["type"] in skip_t or o["name"] in hz or not o.get("size") or o.get("material") in skip_m or o.get("cutaway"): continue
        if (o.get("mobile") or {}).get("group") or o.get("spin") or max(o["size"]) < 0.4: continue
        p = W[o["name"]][:3, 3]; r = max(o["size"]) * 1.8
        if not any(p[1] - r < Ly < p[1] + r and x0 - r < p[0] < x1 + r and z0 - r < p[2] < z1 + r for Ly, x0, z0, x1, z1 in pools): continue
        try: m = _shape(o)
        except Exception: continue
        if m is None or not len(m.faces): continue
        m = m.copy(); m.apply_transform(W[o["name"]]); solids.append((o["name"], m))
    paths, edges = [], 0; ctx.element = ("corrosion", "inferred")  # skirts / band are generated (not drawn from the image)
    _skirts(ctx, cfg, pools, solids, by, W); _clear_lights(ctx, cfg, pools, W)
    for Ly, x0, z0, x1, z1 in pools:
        cut = Ly + 0.05; inside = lambda q: x0 + 0.05 < q[0] < x1 - 0.05 and z0 + 0.05 < q[1] < z1 - 0.05
        live = [(n, m) for n, m in solids if m.bounds[0][1] < Ly + 0.04 and m.bounds[1][1] > Ly + 0.3]  # in it or standing on it
        occ = [(n, m.bounds, m.face_normals, np.einsum("ij,ij->i", m.face_normals, m.triangles[:, 0])) for n, m in live if m.is_watertight and m.is_convex]
        inside_solid = lambda P, b, fn, off: bool(np.all(b[0] <= P) and np.all(P <= b[1]) and np.all(fn @ P - off <= 0.01))  # convex solids only; within 1 cm of a face counts (no strip lying on another surface)
        for name, m in live:
            segs, fi = trimesh.intersections.mesh_plane(m, [0, 1, 0], [0, cut, 0], return_faces=True)
            fn = m.face_normals[fi]; keep = np.abs(fn[:, 1]) < 0.3
            top = min(Ly + cfg["height"], m.bounds[1][1] - 0.05)
            for (a, b), nrm in zip(segs[keep][:, :, [0, 2]], fn[keep][:, [0, 2]]):
                if np.hypot(*(b - a)) < 0.05: continue
                nn = nrm / (np.linalg.norm(nrm) or 1); mid = (a + b) / 2; q = mid + nn * 0.2
                if not inside(q): continue  # faces dry ground / outside the pool
                P = np.array([[q[0], Ly + 0.3, q[1]]])
                S_ = np.array([mid[0] + nn[0] * cfg["offset"], Ly + 0.3, mid[1] + nn[1] * cfg["offset"]])  # the strip itself
                if any(on != name and (inside_solid(P[0], b_, fn_, off_) or inside_solid(S_, b_, fn_, off_)) for on, b_, fn_, off_ in occ): continue  # pressed against / inside a neighbour
                if (-(b - a)[1]) * nn[0] + (b - a)[0] * nn[1] < 0: a, b = b, a  # strip winding faces out of the solid (left of a->b)
                o_ = nn * cfg["offset"]
                paths.append(dict(a=[round(float(a[0] + o_[0]), 5), round(float(a[1] + o_[1]), 5)], b=[round(float(b[0] + o_[0]), 5), round(float(b[1] + o_[1]), 5)],  # 0.01 mm: short strips stay parallel to their face
                                  y0=round(Ly - cfg["sink"], 3), y1=round(float(top), 3)))
                edges += 1
    if not paths: return 0
    ctx.element = ("corrosion", "inferred")
    ctx.add("Corrosion_Band", "band", [0, 0, 0], [1, 1, 1], ctx.role(cfg["material"]), None, collision=False, outline=False,
            segments=_chain(paths), band_top=round(float(max(p[0] for p in pools) + cfg["height"]), 3), tile=cfg["tile"],
            mobile={"group": "Corrosion"})
    ctx.notes.append(f"corrosion: {edges} wall faces at the liquid line get a corroded band (one mesh, one material)")
    return edges


def _skirts(ctx, cfg, pools, solids, by, W):
    """Bodies whose texture has lit panels (cfg["unlit"], e.g. machinery_panel "structure") get a plain sleeve
    (cfg["skirt_material"]) 1 cm proud from under the liquid to cfg["skirt"] m above it: no indicator lights sitting
    in the slime. Same type and footprint as the body, no collision, no outline; the mobile export then culls the
    body faces it covers."""
    n = 0
    for name, m in solids:
        o = by[name]
        if o.get("material") not in cfg["unlit"] or o["type"] not in ("box", "cylinder") or o.get("hole"): continue
        rx, _, rz = o.get("rotation", [0, 0, 0])
        if rx or rz: continue
        b0, b1 = m.bounds[0][1], m.bounds[1][1]
        for Ly, x0, z0, x1, z1 in pools:
            if not (b0 < Ly - 0.02 and b1 > Ly + 0.3): continue
            c = m.bounds.mean(0)
            if not (x0 < c[0] < x1 and z0 < c[2] < z1): continue
            y0 = max(b0, Ly - cfg["sink"]); y1 = min(b1 - 0.3, Ly + cfg["skirt"])
            if y1 - y0 < 0.5: continue
            w, h, d = o["size"]; e = 0.02  # 1 cm proud: clear of the body (coplanar check) and 1.1 cm behind the corrosion band
            ctx.add(name + "_Skirt", o["type"], [o["position"][0], o["position"][1] + (y0 - b0), o["position"][2]], [w + e, y1 - y0, d + e],
                    ctx.role(cfg["skirt_material"]), o.get("parent"), list(o.get("rotation", [0, 0, 0])), collision=False, outline=False,
                    **({"sections": o["sections"]} if "sections" in o else {}), mobile={"static": True})
            n += 1; break
    if n: ctx.notes.append(f"corrosion: {n} lit bodies get a plain skirt at the liquid line (no lights in the slime)")
    return n


def _clear_lights(ctx, cfg, pools, W):
    """Light strips / lamp panels at the base of decks (names ..._Glow_<n>L/R, ..._Light_<n>) that start in or just above
    the liquid: short ones go, tall ones start cfg["light_clear"] m above the surface instead (no lamps in the slime)."""
    import re
    pat = re.compile(r"_(Glow_\d+[LR]|Light_\d+)$"); drop, moved = set(), 0
    for o in ctx.objects:
        if not pat.search(o["name"]) or not o.get("size") or o["type"] not in ("panel", "box"): continue
        p = W[o["name"]][:3, 3]; y0 = p[1]; h = o["size"][1]
        for Ly, x0, z0, x1, z1 in pools:
            if not (x0 - 1 < p[0] < x1 + 1 and z0 - 1 < p[2] < z1 + 1) or y0 > Ly + cfg["light_clear"] or y0 + h < Ly: continue
            cut = Ly + cfg["light_clear"] - y0
            if h - cut < 1.5: drop.add(o["name"])
            else: o["position"][1] = round(o["position"][1] + cut, 3); o["size"][1] = round(h - cut, 3); moved += 1
            break
    if drop:
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
    if drop or moved: ctx.notes.append(f"corrosion: {len(drop)} lights at the liquid line removed, {moved} light strips raised clear of it")
    return len(drop), moved


def _chain(segs, tol=0.0005):
    """Join edge segments that meet end to start (same y range) into polylines; drop the inner points of straight runs."""
    key = lambda p: (round(p[0] / tol), round(p[1] / tol)); start = {}
    for i, s in enumerate(segs): start.setdefault((key(s["a"]), s["y0"], s["y1"]), []).append(i)
    used, out = set(), []
    for i, s in enumerate(segs):
        if i in used: continue
        used.add(i); pts = [s["a"], s["b"]]; cur = s
        while True:
            nxt = [j for j in start.get((key(cur["b"]), cur["y0"], cur["y1"]), []) if j not in used]
            if not nxt: break
            j = nxt[0]; used.add(j); cur = segs[j]; pts.append(cur["b"])
        simp = [pts[0]]
        for k in range(1, len(pts) - 1):
            u = np.subtract(pts[k], simp[-1]); v = np.subtract(pts[k + 1], pts[k])
            if abs(u[0] * v[1] - u[1] * v[0]) > 1e-4 * (np.linalg.norm(u) * np.linalg.norm(v) + 1e-9): simp.append(pts[k])
        simp.append(pts[-1]); out.append(dict(pts=simp, y0=s["y0"], y1=s["y1"]))
    return out
