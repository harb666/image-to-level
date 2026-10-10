"""Stage 3: third-person camera completeness validator (+ safe auto-fix).

  python3 pipeline/validate_level.py levels/<name>          # report -> checks/validation.json
  python3 pipeline/validate_level.py levels/<name> --fix    # apply safe fixes to level.json, rebuild, re-validate

Simulates the game/viewer camera: player positions sampled over every walkable area (+ spawn), camera orbiting the
player's head at 5 m (8 directions x 3 heights), pulled in by a 0.25 m spring arm (stops 0.3 m before geometry). From each camera a
~100°x70° frustum of rays is cast. Issues:
  void          a ray pointing below the horizon hits nothing (level + background): the world visibly ends
  back_face     a ray hits the BACK of a single-sided surface: a missing face / open back is visible
  open_mesh     a visible (non-panel) object has open boundary edges above its base: holes/unfinished edges
  camera_inside the pulled-in camera ended inside an object (clipping) - reported, not counted as missing faces
Fixes (never inside walkable space): back_face -> object "double_sided": true; void -> add/extend environment
ground skirt + horizon mountain ring (Stage 2 background); terrain heightfields always get skirts in the builder.
Respect intentional openings with level.json "validation": {"ignore_objects": [names], "allow_void": false}.
"""
import json, os, subprocess, sys, numpy as np, trimesh

HERE = os.path.dirname(os.path.abspath(__file__))


NONPLAYABLE = ("TRM_", "SCN_", "TW_")  # Stage 9: middle zone, non-colliding scatter (grass, pebbles), water sheets (rivers are wadeable: the bed carries)


def load_tris(path, skip_invisible=True, skip_nonplayable=True):
    """World-space triangles + owning node name per triangle (+ per-object meshes for edge checks)."""
    s = trimesh.load(path, force="scene"); T, names, objs = [], [], {}
    for node in s.graph.nodes_geometry:
        M, g = s.graph[node]; m = s.geometry[g]
        mat = getattr(getattr(m.visual, "material", None), "name", "") or ""
        if skip_invisible and (node.startswith("Boundary") or mat == "Collider_invisible"): continue
        if skip_nonplayable and node.startswith(NONPLAYABLE): continue
        if node.endswith("__ol"): continue  # cartoon outline shells (build_level.outline_hull): not surfaces
        tri = trimesh.transform_points(m.triangles.reshape(-1, 3), M).reshape(-1, 3, 3)
        T.append(tri); names += [node] * len(tri); objs[node] = (m, M, mat)
    return (np.concatenate(T) if T else np.zeros((0, 3, 3))), np.array(names), objs


def closed_mask(names, objs):
    """Per-triangle body id (-1 = open) after welding: only CLOSED bodies (every edge shared by exactly 2 faces) can
    contain a point. Per body, not per object, so merged meshes (Stage 5) with some open parts are handled."""
    from scipy.sparse.csgraph import connected_components
    from scipy.sparse import coo_matrix
    out, nxt = [], 0
    for nm in dict.fromkeys(names):
        m, M, _ = objs[nm]; mm = m.copy(); mm.merge_vertices(merge_tex=True, merge_norm=True)
        nf = len(mm.faces); body = np.full(len(m.faces), -1)
        if nf:
            adj = mm.face_adjacency
            _, lab = connected_components(coo_matrix((np.ones(len(adj)), (adj[:, 0], adj[:, 1])), shape=(nf, nf)), directed=False)
            e = np.sort(mm.faces[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1); fl = np.repeat(lab, 3)
            key = np.c_[e, fl]; _, inv, cnt = np.unique(key, axis=0, return_inverse=True, return_counts=True)
            ok = np.ones(lab.max() + 1, bool); ok[fl[cnt[inv.ravel()] != 2]] = False
            if len(mm.faces) == len(m.faces):  # face order preserved by merge_vertices
                body = np.where(ok[lab], lab + nxt, -1); nxt += lab.max() + 1
        out.append(body)
    return np.concatenate(out) if out else np.zeros(0, int)


def cast(O, D, T, far=1e4):
    """Rays (n,3) from origins O (n,3) vs triangles T (m,3,3): nearest t, triangle index (-1 = miss), signed facing."""
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]; nrm = np.cross(e1, e2)
    bt = np.full(len(D), np.inf); bi = np.full(len(D), -1)
    for i in range(0, len(D), 96):
        o, d = O[i:i + 96], D[i:i + 96]
        p = np.cross(d[:, None, :], e2[None]); det = np.einsum("nmk,mk->nm", p, e1)
        ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        s = o[:, None, :] - v0[None]; u = np.einsum("nmk,nmk->nm", s, p) * inv
        q = np.cross(s, e1[None]); v = np.einsum("nk,nmk->nm", d, q) * inv; t = np.einsum("mk,nmk->nm", e2, q) * inv
        t = np.where(ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-4) & (t < far), t, np.inf)
        t = t + (np.einsum("nk,mk->nm", d, nrm) > 0) * 1e-5  # tie on a shared edge: the front face wins
        j = t.argmin(1); bt[i:i + 96] = t[np.arange(len(j)), j]; bi[i:i + 96] = np.where(np.isfinite(bt[i:i + 96]), j, -1)
    facing = np.where(bi >= 0, np.einsum("nk,nk->n", nrm[np.maximum(bi, 0)], D), 0)  # >0 = hit the back side
    return bt, bi, facing


def inside_solid(P, T, obj):
    """Point inside any closed object? Per-object crossing parity (odd = inside) along 3 directions, majority vote.
    Parity per object (not first hit) so overlapping solids (rock clusters, stacked boxes) and coplanar caps are handled."""
    ids = np.unique(obj, return_inverse=True)[1]; nobj = ids.max() + 1; v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    votes = np.zeros((len(P), nobj), int)
    for d in ([0.0137, 1.0, 0.0071], [1.0, 0.0093, 0.0061], [0.0083, 0.0057, -1.0]):  # slightly skewed: no exact edge hits
        d = np.array(d) / np.linalg.norm(d); cnt = np.zeros((len(P), nobj), int)
        p = np.cross(d, e2); det = np.einsum("mk,mk->m", e1, p); ok = np.abs(det) > 1e-9; inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
        for i in range(0, len(P), 128):
            s = P[i:i + 128, None, :] - v0[None]; u = np.einsum("nmk,mk->nm", s, p) * inv
            q = np.cross(s, e1[None]); v = (q @ d) * inv; t = np.einsum("mk,nmk->nm", e2, q) * inv
            hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-6)
            for k in range(nobj): cnt[i:i + 128, k] = hit[:, ids == k].sum(1)
        votes += cnt % 2
    return (votes >= 2).any(1)


def inside_solid_bodies(P, T, body, pad=0.01):
    """inside_solid with a per-body AABB prefilter (Stage 9 worlds: tens of thousands of terrain points vs many
    small closed props) - same answer, each point only tested against the bodies whose box contains it."""
    P = np.asarray(P, float); out = np.zeros(len(P), bool); ids = np.unique(body[body >= 0])
    for b in ids:
        tb = T[body == b]; lo, hi = tb.reshape(-1, 3).min(0) - pad, tb.reshape(-1, 3).max(0) + pad
        m = np.all((P >= lo) & (P <= hi), 1) & ~out
        if m.any(): out[np.flatnonzero(m)] = inside_solid(P[m], tb, np.zeros(len(tb), int))
    return out


def orbit_dirs(yaw, pitch):
    """Viewer convention: back vector of Euler(pitch, yaw, 'YXZ') applied to +z."""
    return np.array([np.sin(yaw) * np.cos(pitch), -np.sin(pitch), np.cos(yaw) * np.cos(pitch)])


def frustum(fwd, hfov=100, vfov=70, nh=11, nv=8):
    yaw0 = np.arctan2(fwd[0], fwd[2]); el0 = np.arcsin(np.clip(fwd[1], -1, 1)); out = []
    for dv in np.radians(np.linspace(-vfov / 2, vfov / 2, nv)):
        for dh in np.radians(np.linspace(-hfov / 2, hfov / 2, nh)):
            e, a = el0 + dv, yaw0 + dh; out.append([np.sin(a) * np.cos(e), np.sin(e), np.cos(a) * np.cos(e)])
    return np.array(out)


def validate(level_dir, step=6.0, verbose=True, mobile=False):
    L = json.load(open(os.path.join(level_dir, "level.json"))); V = L.get("validation", {})
    from gameplay import load_gameplay  # Stage 7: camera/player numbers from config/gameplay.json (defaults = the Stage 3 values)
    G = load_gameplay(level_dir, L); Pl, Cm = G["player"], G["camera"]; arm, pr, mg = Cm["arm_length"], Cm["probe_radius"], Cm["margin"]
    ignore = set(V.get("ignore_objects", []))
    T, names, objs = load_tris(os.path.join(level_dir, "mobile", "level_mobile.glb") if mobile else os.path.join(level_dir, "level.glb"))
    bgp = os.path.join(level_dir, "mobile", "background_mobile.glb") if mobile else os.path.join(level_dir, "background.glb")
    BT = load_tris(bgp)[0] if os.path.exists(bgp) else np.zeros((0, 3, 3))
    spec = {o["name"]: o for o in L["objects"]}
    # player positions over walkable areas
    pts = [L["spawn"]["position"]]
    for w in L.get("walkable", []):
        xs = np.arange(w["min"][0] + 1.37, w["max"][0] - 0.99, step) if w["max"][0] - w["min"][0] > 2 else [(w["min"][0] + w["max"][0]) / 2]
        zs = np.arange(w["min"][1] + 1.23, w["max"][1] - 0.99, step) if w["max"][1] - w["min"][1] > 2 else [(w["min"][1] + w["max"][1]) / 2]
        pts += [[x, w["y"], z] for x in xs for z in zs]
    mx = int(Cm.get("validation_max_players", 48))
    if len(pts) > mx: pts = [pts[0]] + [pts[i] for i in np.linspace(1, len(pts) - 1, mx - 1).round().astype(int)]  # spawn + evenly spread samples
    heads = np.array(pts, float) + [0, Pl["eye_height"] + Cm["pivot_above_eye"], 0]
    body = closed_mask(names, objs); cm = body >= 0; TC, NC = T[cm], body[cm]
    ins = inside_solid(np.array(pts, float) + [0, 0.5, 0], TC, NC)
    # player capsule (r 0.35 m) can't stand closer than ~0.4 m to geometry: drop such samples
    ring = np.array([[np.cos(a), 0, np.sin(a)] for a in np.radians(np.arange(0, 360, 45))])
    near = np.zeros(len(heads), bool)
    for d in ring: near |= cast(heads, np.tile(d, (len(heads), 1)), T, Pl["radius"] + 0.05)[1] >= 0
    blocked_players = int((ins | near).sum()); heads = heads[~(ins | near)]  # inside a solid / hugging a wall
    if isinstance(L.get("terrain"), dict):  # Stage 9 worlds: local camera check (gaps to the horizon: terrain_check.background)
        return _validate_local(level_dir, L, G, V, spec, ignore, heads, blocked_players, T, names, objs, TC, NC, mobile, verbose)
    cams = []
    for h in heads:
        for yaw in np.radians(np.arange(0, 360, 45)):
            for pitch in np.radians(Cm["pitch_deg"]):
                cams.append((h, orbit_dirs(yaw, pitch)))
    O = np.array([c[0] for c in cams]); B = np.array([c[1] for c in cams])
    # camera collision as a 0.25 m sphere-ish spring arm (5 parallel rays, like Godot SpringArm3D with a shape)
    perp = np.cross(B, [0.0, 1.0, 0.0]); perp[np.linalg.norm(perp, axis=1) < 1e-6] = [1.0, 0, 0]; perp /= np.linalg.norm(perp, axis=1, keepdims=True)
    up2 = np.cross(perp, B); t = cast(O, B, T, arm)[0]
    for off in (perp, -perp, up2, -up2):
        t = np.minimum(t, cast(O + off * pr, B, T, arm)[0])
    dist = np.where(np.isfinite(t), np.where(t > 2 * mg, t - mg, t * 0.5), arm); C = O + B * dist[:, None]  # same rule as the viewer: never past a surface
    inside = inside_solid(C, TC, NC)  # camera ended inside a solid: a clipping issue, not a missing face
    issues = dict(void=0, back_face={}, camera_inside=int(inside.sum())); void_examples = []; visible = set(); nrays = 0
    for k, (c, fwd) in enumerate(zip(C, -B)):
        if inside[k]: continue
        D = frustum(fwd); Oc = np.repeat(c[None], len(D), 0); nrays += len(D)
        tt, ii, fc = cast(Oc, D, T)
        hit = ii >= 0; back = hit & (fc > 0)
        for nm in names[ii[hit & ~back]]: visible.add(nm)
        if back.any():  # confirm with 2 slightly perturbed rays each: rays grazing an edge/corner are numerical noise
            jb = np.flatnonzero(back); conf = np.ones(len(jb), bool)
            for off in ([0.004, 0.003, -0.002], [-0.003, -0.002, 0.004]):
                Dp = D[jb] + off; Dp /= np.linalg.norm(Dp, axis=1, keepdims=True)
                _, i2, f2 = cast(Oc[jb], Dp, T); conf &= (i2 >= 0) & (f2 > 0) & (names[np.maximum(i2, 0)] == names[ii[jb]])
            jc = jb[conf]
            if len(jc):
                ispanel = np.array([spec.get(n, {}).get("type") == "panel" for n in names[ii[jc]]])
                if ispanel.any():  # look 0.25 m past the panel: a wall right behind it means the back can't show a hole
                    jp = jc[ispanel]; P2 = Oc[jp] + D[jp] * (tt[jp] + 1e-3)[:, None]
                    t3, i3, _ = cast(P2, D[jp], T, 0.25); mounted = (i3 >= 0) & (names[np.maximum(i3, 0)] != names[ii[jp]])
                    jc = np.r_[jc[~ispanel], jp[~mounted]]
            for nm in names[ii[jc]]:
                if nm in ignore or spec.get(nm, {}).get("double_sided") or objs[nm][2].endswith("__2s"): continue  # __2s = doubleSided material
                issues["back_face"][nm] = issues["back_face"].get(nm, 0) + 1
        miss = (~hit) & (D[:, 1] < -0.01)
        if miss.any() and len(BT):
            bt_, bi_, _ = cast(Oc[miss], D[miss], BT, 2000); idx = np.flatnonzero(miss)[bi_ < 0]
        else: idx = np.flatnonzero(miss)
        if len(idx) and not V.get("allow_void"):
            issues["void"] += len(idx)
            if len(void_examples) < 12: void_examples.append(dict(camera=np.round(c, 1).tolist(), dir=np.round(D[idx[0]], 2).tolist()))
    open_mesh = {}
    for nm in visible:
        if nm in ignore or nm not in objs: continue
        typ = spec.get(nm, spec.get(nm.rsplit("_Top", 1)[0], {})).get("type")
        if typ in ("panel", None) or spec.get(nm, {}).get("double_sided"): continue
        m = objs[nm][0].copy(); m.merge_vertices(merge_tex=True, merge_norm=True)
        u, cnt = np.unique(m.edges_sorted, axis=0, return_counts=True); b = u[cnt == 1]
        if len(b):
            ymin = m.vertices[:, 1].min(); above = int((m.vertices[b].min(1)[:, 1] > ymin + 0.05).sum())
            if above and typ != "terrain": open_mesh[nm] = above
    R = dict(players=len(heads), players_skipped_inside_or_against_walls=blocked_players, cameras=len(cams), rays=nrays, void_rays=issues["void"], void_examples=void_examples,
             back_face=dict(sorted(issues["back_face"].items(), key=lambda x: -x[1])), open_mesh=open_mesh,
             camera_inside=issues["camera_inside"], visible_objects=len(visible),
             passed=issues["void"] == 0 and not issues["back_face"] and not open_mesh)
    os.makedirs(os.path.join(level_dir, "checks"), exist_ok=True)
    json.dump(R, open(os.path.join(level_dir, "checks", "validation_mobile.json" if mobile else "validation.json"), "w"), indent=1)
    if verbose: print(json.dumps({k: v for k, v in R.items() if k != "void_examples"}))
    return R


def _validate_local(level_dir, L, G, V, spec, ignore, heads, blocked_players, T, names, objs, TC, NC, mobile, verbose, R_local=40.0):
    """Same spring-arm cameras + back-face / open-mesh rules, but each player only against triangles within R_local m
    (a world has tens of thousands of triangles). Rays that see nothing within R_local are not void here: distant
    completeness is checked from the horizon by terrain_check.check_background."""
    Pl, Cm = G["player"], G["camera"]; arm, pr, mg = Cm["arm_length"], Cm["probe_radius"], Cm["margin"]
    lo, hi = T.min(1), T.max(1); clo, chi = TC.min(1), TC.max(1)
    issues = dict(back_face={}, camera_inside=0); visible = set(); ncams = nrays = 0
    for h in heads:
        sel = np.all((hi >= h - R_local) & (lo <= h + R_local), 1); Tl, nl = T[sel], names[sel]
        cs = np.all((chi >= h - arm - 1) & (clo <= h + arm + 1), 1)
        B = np.array([orbit_dirs(yaw, pitch) for yaw in np.radians(np.arange(0, 360, 45)) for pitch in np.radians(Cm["pitch_deg"])]); O = np.repeat(h[None], len(B), 0)
        perp = np.cross(B, [0.0, 1.0, 0.0]); perp[np.linalg.norm(perp, axis=1) < 1e-6] = [1.0, 0, 0]; perp /= np.linalg.norm(perp, axis=1, keepdims=True)
        up2 = np.cross(perp, B); t = cast(O, B, Tl, arm)[0]
        for off in (perp, -perp, up2, -up2): t = np.minimum(t, cast(O + off * pr, B, Tl, arm)[0])
        dist = np.where(np.isfinite(t), np.where(t > 2 * mg, t - mg, t * 0.5), arm); C = O + B * dist[:, None]
        inside = inside_solid(C, TC[cs], NC[cs]) if cs.any() else np.zeros(len(C), bool); issues["camera_inside"] += int(inside.sum()); ncams += len(C)
        for k, (c, fwd) in enumerate(zip(C, -B)):
            if inside[k]: continue
            D = frustum(fwd); Oc = np.repeat(c[None], len(D), 0); nrays += len(D)
            tt, ii, fc = cast(Oc, D, Tl, R_local); hit = ii >= 0; back = hit & (fc > 0)
            for nm in nl[ii[hit & ~back]]: visible.add(nm)
            if back.any():
                jb = np.flatnonzero(back); conf = np.ones(len(jb), bool)
                for off in ([0.004, 0.003, -0.002], [-0.003, -0.002, 0.004]):
                    Dp = D[jb] + off; Dp /= np.linalg.norm(Dp, axis=1, keepdims=True)
                    _, i2, f2 = cast(Oc[jb], Dp, Tl, R_local); conf &= (i2 >= 0) & (f2 > 0) & (nl[np.maximum(i2, 0)] == nl[ii[jb]])
                for nm in nl[ii[jb[conf]]]:
                    if nm in ignore or spec.get(nm, {}).get("double_sided") or spec.get(nm, {}).get("type") == "panel" or objs[nm][2].endswith("__2s"): continue
                    issues["back_face"][nm] = issues["back_face"].get(nm, 0) + 1
    open_mesh = {}
    for nm in visible:
        if nm in ignore or nm not in objs or nm.startswith(("TR_", "TRM_", "TW_", "SC")): continue
        typ = spec.get(nm, spec.get(nm.rsplit("_Top", 1)[0], {})).get("type")
        if typ in ("panel", None) or spec.get(nm, {}).get("double_sided"): continue
        m = objs[nm][0].copy(); m.merge_vertices(merge_tex=True, merge_norm=True)
        u, cnt = np.unique(m.edges_sorted, axis=0, return_counts=True); b = u[cnt == 1]
        if len(b):
            ymin = m.vertices[:, 1].min(); above = int((m.vertices[b].min(1)[:, 1] > ymin + 0.05).sum())
            if above and typ != "terrain": open_mesh[nm] = above
    R = dict(players=len(heads), players_skipped_inside_or_against_walls=blocked_players, cameras=ncams, rays=nrays, void_rays=0, void_examples=[],
             back_face=dict(sorted(issues["back_face"].items(), key=lambda x: -x[1])), open_mesh=open_mesh, camera_inside=issues["camera_inside"],
             visible_objects=len(visible), mode=f"local ({R_local:.0f} m) - world gaps: checks/geometry.json background", passed=not issues["back_face"] and not open_mesh)
    os.makedirs(os.path.join(level_dir, "checks"), exist_ok=True)
    json.dump(R, open(os.path.join(level_dir, "checks", "validation_mobile.json" if mobile else "validation.json"), "w"), indent=1)
    if verbose: print(json.dumps({k: v for k, v in R.items() if k != "void_examples"}))
    return R


def fix(level_dir, R):
    """Safe fixes only: material/shading flags and background below/around the level - nothing in walkable space."""
    p = os.path.join(level_dir, "level.json"); L = json.load(open(p)); spec = {o["name"]: o for o in L["objects"]}; log = []
    for nm in R["back_face"]:
        o = spec.get(nm) or spec.get(nm.rsplit("_Top", 1)[0])
        if o and not o.get("double_sided"):
            o["double_sided"] = True; o["autofix"] = "back face visible from the third-person camera"; log.append(f"{o['name']}: double_sided")
    if R["void_rays"]:
        b0, b1 = np.array(L["bounds"]["min"]), np.array(L["bounds"]["max"])
        rad = float(np.hypot(*(b1 - b0)[[0, 2]]) / 2); cx, cz = (b0 + b1)[[0, 2]] / 2
        env = L.setdefault("environment", {})
        if not env.get("background"):
            bright = np.mean(L.get("sky_color", [0.5, 0.5, 0.5])) > 0.45
            env.update(quality=env.get("quality", "balanced"), horizon_distance=max(300, rad * 6), sky=env.get("sky", {"preset": "clear_day" if bright else "overcast"}))
            env["background"] = [
                dict(id="AutoFix_Ground", type="ground", radius=[0, max(300, rad * 6)], flat_radius=rad + 10, rise=10, roughness=3, autofix="void below horizon"),
                dict(id="AutoFix_Horizon", type="mountain_ring", radius=max(280, rad * 5.5), depth=50, height=[25, 70], fade=0.5, autofix="close the horizon")]
            log.append("environment: added ground skirt + horizon ring")
        else:
            g = next((l for l in env["background"] if l["type"] == "ground"), None)
            if g is None:
                env["background"].insert(0, dict(id="AutoFix_Ground", type="ground", radius=[0, env.get("horizon_distance", 450)], flat_radius=rad + 10, rise=10, autofix="void below horizon"))
                log.append("environment: added ground skirt")
            else:
                g["flat_radius"] = max(g.get("flat_radius", 60), rad + 10); g["radius"] = [0, max(g["radius"][1], env.get("horizon_distance", 450))]
                log.append(f"environment: widened {g['id']}")
        if "center" not in env: env["center_note"] = f"background is centred on the world origin; level centre is ({cx:.0f}, {cz:.0f})"
    json.dump(L, open(p, "w"), indent=1)
    return log


if __name__ == "__main__":
    d = sys.argv[1]; R = validate(d, mobile="--mobile" in sys.argv)  # --mobile: check mobile/level_mobile.glb instead
    if "--fix" in sys.argv and not R["passed"]:
        log = fix(d, R); print("fixes:", log)
        subprocess.run([sys.executable, os.path.join(HERE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL)
        R2 = validate(d); print("after fix: passed =", R2["passed"])
