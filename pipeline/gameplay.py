"""Stage 7: gameplay config + navigation / reachability analysis for third-person arena levels.

  python3 pipeline/gameplay.py levels/<name>      -> checks/navigation.json + checks/navigation.png

Player/camera numbers come from config/gameplay.json (PLACEHOLDERS until Construct Error's real values are copied in),
overridden by levels/<name>/gameplay.json and level.json "gameplay". Nothing here hard-codes movement measurements.

Method (Recast-like, CPU/numpy): every triangle of level.glb is sampled every cell/2 m and binned into an x/z grid
(cell = nav.cell). Per cell the samples form vertical SPANS; a span is standable when its top surface faces up (slope
<= max_slope_deg), is not a hazard and has >= player height of free space above it. Neighbouring standable spans connect
when the height difference <= step_height (ramps and stairs therefore connect, walls/crates do not). Spans closer than
the player radius to a wall or edge are eroded. Connected spans = walk COMPONENTS (a platform, a deck, a ramp+deck...).
Components link by:
  drop  stepping off an edge onto a lower component (fall <= safe_drop)
  jump  up to jump_height higher / safe_drop lower within jump_distance horizontally, with no obstacle rising above the
        higher end along the way (overhead structures don't block)
Reports: reachability of every component and every intended walkable area (level.json "walkable") from the spawn,
one-way traps (reachable but no way back), spawn safety (standable, clearance, headroom, hazard distance), narrow
connectors (< design.min_bridge_width) and low ceilings (< design.min_headroom: cramped third-person camera).
Limits: jump arcs are approximated (straight-line obstacle test, no air control); moving platforms/doors unknown."""
import json, math, os, sys, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)


def deep_merge(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_gameplay(level_dir=None, L=None):
    G = json.load(open(os.path.join(ROOT, "config", "gameplay.json")))
    if level_dir:
        p = os.path.join(level_dir, "gameplay.json")
        if os.path.exists(p): G = deep_merge(G, json.load(open(p)))
        if L is None and os.path.exists(os.path.join(level_dir, "level.json")): L = json.load(open(os.path.join(level_dir, "level.json")))
    if L and L.get("gameplay"): G = deep_merge(G, L["gameplay"])
    return G


def hazard_objects(L):
    """Hazard names + every object sharing a hazard's material (e.g. toxic falls) - same rule as the mobile export."""
    hz = set(L.get("hazards", [])); mats = {o.get("material") for o in L["objects"] if o["name"] in hz}
    return hz | {o["name"] for o in L["objects"] if o.get("material") in mats and o.get("material")}


def _sample(T, spacing):
    """Points on every triangle (<= spacing apart; grid spanned from the vertex opposite the longest edge, so long thin
    triangles cost ~area/spacing^2 points) + triangle index."""
    el = np.stack([np.linalg.norm(T[:, 2] - T[:, 1], axis=1), np.linalg.norm(T[:, 0] - T[:, 2], axis=1), np.linalg.norm(T[:, 1] - T[:, 0], axis=1)], 1)
    a = el.argmax(1); T = np.stack([T[np.arange(len(T)), a], T[np.arange(len(T)), (a + 1) % 3], T[np.arange(len(T)), (a + 2) % 3]], 1)
    l1 = np.linalg.norm(T[:, 1] - T[:, 0], axis=1); l2 = np.linalg.norm(T[:, 2] - T[:, 0], axis=1)
    n1 = np.clip(np.ceil(l1 / spacing).astype(int), 1, 4000); n2 = np.clip(np.ceil(l2 / spacing).astype(int), 1, 4000)
    key = n1 * 4001 + n2; P, I = [], []
    for k in np.unique(key):
        idx = np.flatnonzero(key == k); a1, a2 = divmod(int(k), 4001)
        u, v = np.meshgrid(np.arange(a1 + 1) / a1, np.arange(a2 + 1) / a2); m = u + v <= 1 + 1e-9; u, v = u[m], v[m]; w = 1 - u - v
        tri = T[idx]
        pts = tri[:, None, 0] * w[None, :, None] + tri[:, None, 1] * u[None, :, None] + tri[:, None, 2] * v[None, :, None]
        P.append(pts.reshape(-1, 3)); I.append(np.repeat(idx, len(u)))
    return np.concatenate(P), np.concatenate(I)


def _bodies(level_dir):
    from validate_level import load_tris, closed_mask
    _, names, objs = load_tris(os.path.join(level_dir, "level.glb"), skip_invisible=False)
    return closed_mask(names, objs)


def analyse(level_dir, G=None, write=True, verbose=True):
    from validate_level import load_tris
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    L = json.load(open(os.path.join(level_dir, "level.json"))); G = G or load_gameplay(level_dir, L)
    P_, D_, cell = G["player"], G["design"], G["nav"]["cell"]
    T, names, _ = load_tris(os.path.join(level_dir, "level.glb"), skip_invisible=False)  # invisible boundaries block too
    base = np.array([n[:-4] if n.endswith("_Top") else n for n in names]); onames, oid = np.unique(base, return_inverse=True)
    hz = hazard_objects(L); is_hz_obj = np.array([n in hz for n in onames]); invisible = np.array([n.startswith("Boundary") for n in onames])
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nl = np.linalg.norm(nrm, axis=1); ny = np.where(nl > 0, nrm[:, 1] / np.maximum(nl, 1e-12), 0)
    walk_tri = (ny >= np.cos(np.radians(P_["max_slope_deg"]))) & ~invisible[oid]
    b0 = np.array(L["bounds"]["min"], float) - 6; b1 = np.array(L["bounds"]["max"], float) + 6
    nx, nz = int(np.ceil((b1[0] - b0[0]) / cell)), int(np.ceil((b1[2] - b0[2]) / cell))
    P, I = _sample(T, cell / 2)
    ix, iz = np.floor((P[:, 0] - b0[0]) / cell).astype(int), np.floor((P[:, 2] - b0[2]) / cell).astype(int)
    keep = (ix >= 0) & (ix < nx) & (iz >= 0) & (iz < nz); P, I, ix, iz = P[keep], I[keep], ix[keep], iz[keep]
    c = iz * nx + ix; order = np.lexsort((P[:, 1], c)); c, y, I = c[order], P[order, 1], I[order]
    # spans: same cell, vertical gaps below a step merge
    mg = max(0.15, min(P_["step_height"], 0.4))  # gaps smaller than a step can't hold a player: one walking surface (stair treads)
    new = np.r_[True, (c[1:] != c[:-1]) | (y[1:] - y[:-1] > mg)]; sid = np.cumsum(new) - 1; ns = sid[-1] + 1
    s_first = np.flatnonzero(new); s_last = np.r_[s_first[1:] - 1, len(y) - 1]
    s_cell, s_lo, s_top = c[s_first], y[s_first], y[s_last]
    # top surface of the span: highest sample; walkable if that triangle is (ties: any walkable sample within 2 cm of the top)
    top_walk = np.zeros(ns, bool); np.logical_or.at(top_walk, sid, walk_tri[I] & (y >= s_top[sid] - 0.02))
    top_obj = oid[I[s_last]]; wsel = walk_tri[I] & (y >= s_top[sid] - 0.02)
    top_obj[sid[wsel]] = oid[I[wsel]]
    s_hz = is_hz_obj[top_obj]
    same_next = np.r_[s_cell[1:] == s_cell[:-1], False]
    s_ceil = np.where(same_next, np.r_[s_lo[1:], np.inf], np.inf)
    clear = s_ceil - s_top
    # buried? a top surface just inside another CLOSED solid (e.g. fluid under a platform base, a base top inside its
    # floor plate) is neither floor nor hazard. Proper point-in-solid test, only where something lies above in the cell.
    from validate_level import closed_mask, inside_solid
    hazard_top = top_walk & s_hz & (clear >= 0.5)
    cand = np.flatnonzero((hazard_top | (top_walk & ~s_hz & (clear >= P_["height"]))) & same_next)
    if len(cand):
        body = _bodies(level_dir)
        cm = body >= 0
        if cm.any():
            pts = np.c_[b0[0] + (s_cell[cand] % nx + 0.5) * cell, s_top[cand] + 0.05, b0[2] + (s_cell[cand] // nx + 0.5) * cell]
            bur = np.zeros(len(cand), bool); bid = np.unique(body[cm]); tb = body
            blo = np.array([T[tb == b].reshape(-1, 3).min(0) for b in bid]); bhi = np.array([T[tb == b].reshape(-1, 3).max(0) for b in bid])
            order = np.lexsort((pts[:, 0], np.floor(pts[:, 2] / 8), np.floor(pts[:, 0] / 8)))  # spatial chunks: only nearby bodies
            for k in range(0, len(cand), 256):
                ii = order[k:k + 256]; lo_, hi_ = pts[ii].min(0), pts[ii].max(0)
                near = bid[np.all(bhi >= lo_ - 0.01, 1) & np.all(blo <= hi_ + 0.01, 1)]
                if not len(near): continue
                sel = np.isin(tb, near); bur[ii] = inside_solid(pts[ii], T[sel], tb[sel])
            hazard_top[cand[bur]] = False; top_walk[cand[bur]] = False
    stand = top_walk & ~s_hz & (clear >= P_["height"])
    cell_start = np.searchsorted(s_cell, np.arange(nx * nz)); cell_end = np.searchsorted(s_cell, np.arange(nx * nz), side="right")
    nodes = np.flatnonzero(stand); nid = -np.ones(ns, int); nid[nodes] = np.arange(len(nodes)); N = len(nodes)
    # walking height of a cell = mean height of its walkable top samples (stairs treads shorter than a cell average out
    # to the stair slope instead of jumping by two risers); clearance still uses the true top
    wtop = walk_tri[I] & (y >= s_top[sid] - 0.55); ssum = np.zeros(ns); scnt = np.zeros(ns)
    np.add.at(ssum, sid[wtop], y[wtop]); np.add.at(scnt, sid[wtop], 1); s_walk = np.where(scnt > 0, ssum / np.maximum(scnt, 1), s_top)
    ncell, ntop, nceil = s_cell[nodes], s_walk[nodes], s_ceil[nodes]
    nxz = np.c_[b0[0] + (ncell % nx + 0.5) * cell, b0[2] + (ncell // nx + 0.5) * cell]
    # walk connections (4-neighbourhood)
    ea, eb = [], []; deg = np.zeros(N, int)
    for dx, dz in ((1, 0), (0, 1)):
        for i in range(N):
            cx, cz = ncell[i] % nx + dx, ncell[i] // nx + dz
            if cx >= nx or cz >= nz: continue
            c2 = cz * nx + cx
            for s in range(cell_start[c2], cell_end[c2]):
                j = nid[s]
                if j < 0: continue
                if abs(ntop[i] - ntop[j]) <= P_["step_height"] and min(nceil[i], nceil[j]) - max(ntop[i], ntop[j]) >= P_["height"]:
                    ea.append(i); eb.append(j); deg[i] += 1; deg[j] += 1
    ea, eb = np.array(ea, int), np.array(eb, int)
    adj = [[] for _ in range(N)]
    for a, b in zip(ea, eb): adj[a].append(b); adj[b].append(a)

    def border_dist(mask):
        d = np.full(N, 10 ** 6); fr = [i for i in range(N) if mask[i] and deg[i] < 4]
        for i in fr: d[i] = 0
        k = 0
        while fr:
            nxt = []
            for i in fr:
                for j in adj[i]:
                    if mask[j] and d[j] > d[i] + 1: d[j] = d[i] + 1; nxt.append(j)
            fr = nxt; k += 1
        return d
    dist = border_dist(np.ones(N, bool))
    ok = (dist + 0.5) * cell >= P_["radius"]  # eroded by the player radius
    m = ok[ea] & ok[eb]
    ncomp, comp = connected_components(coo_matrix((np.ones(m.sum()), (ea[m], eb[m])), shape=(N, N)), directed=False)
    comp = np.where(ok, comp, -1)
    # links between components
    sel = np.flatnonzero(ok); tree = cKDTree(nxz[sel]); links = {}
    bord = sel[dist[sel] <= 2 + int(np.ceil(P_["radius"] / cell))]
    if len(bord):
        btree = cKDTree(nxz[bord]); pairs = btree.sparse_distance_matrix(tree, P_["jump_distance"] + cell, output_type="coo_matrix")
        a, b, hd = bord[pairs.row], sel[pairs.col], pairs.data
        dy = ntop[b] - ntop[a]; good = (comp[a] != comp[b]) & (dy <= P_["jump_height"]) & (-dy <= P_["safe_drop"])
        a, b, hd, dy = a[good], b[good], hd[good], dy[good]
        o = np.lexsort((hd, comp[b], comp[a])); a, b, hd, dy = a[o], b[o], hd[o], dy[o]
        key = comp[a] * (ncomp + 1) + comp[b]; starts = np.flatnonzero(np.r_[True, key[1:] != key[:-1]])
        for si, st in enumerate(starts):
            en = starts[si + 1] if si + 1 < len(starts) else len(a)
            for k in range(st, min(en, st + 24)):
                if not _blocked(nxz[a[k]], nxz[b[k]], max(ntop[a[k]], ntop[b[k]]), s_cell, s_lo, s_top, cell_start, cell_end, b0, cell, nx, nz, P_):
                    kind = "drop" if dy[k] < -P_["step_height"] and hd[k] <= 1.5 + P_["radius"] else "jump"
                    links[(int(comp[a[k]]), int(comp[b[k]]))] = dict(kind=kind, frm=[round(float(nxz[a[k]][0]), 1), round(float(ntop[a[k]]), 2), round(float(nxz[a[k]][1]), 1)],
                                                                   to=[round(float(nxz[b[k]][0]), 1), round(float(ntop[b[k]]), 2), round(float(nxz[b[k]][1]), 1)],
                                                                   horizontal=round(float(hd[k]), 2), dy=round(float(dy[k]), 2))
                    break
    # spawn(s)
    spawns = [dict(L["spawn"], id="spawn")] + [dict(s, id=s.get("id", f"spawn_{i + 2}")) for i, s in enumerate(L.get("spawns", []))]
    hz_nodes = np.flatnonzero(hazard_top); hz_xz = np.c_[b0[0] + (s_cell[hz_nodes] % nx + 0.5) * cell, b0[2] + (s_cell[hz_nodes] // nx + 0.5) * cell]
    hz_tree = cKDTree(hz_xz) if len(hz_nodes) else None

    def nearest(p, maxd=1.0):
        cand = np.flatnonzero((np.hypot(*(nxz - [p[0], p[2]]).T) <= maxd) & (np.abs(ntop - p[1]) <= 0.6))
        return int(cand[np.argmin(np.hypot(*(nxz[cand] - [p[0], p[2]]).T))]) if len(cand) else None
    sp_node = nearest(L["spawn"]["position"]); home = int(comp[sp_node]) if sp_node is not None and comp[sp_node] >= 0 else None
    fwd, back = _reach(ncomp, links, home)
    comps = []
    for k in range(ncomp):
        idx = np.flatnonzero(comp == k)
        if not len(idx): continue
        objs, cnt = np.unique(top_obj[nodes[idx]], return_counts=True); top = [str(onames[o]) for o in objs[np.argsort(-cnt)][:4]]
        comps.append(dict(id=k, area_m2=round(len(idx) * cell * cell, 1), y=round(float(np.median(ntop[idx])), 2),
                          bbox=[round(float(v), 1) for v in (*nxz[idx].min(0), *nxz[idx].max(0))], objects=top,
                          reachable=home is not None and k in fwd, can_return=home is not None and k in back,
                          reached_by=fwd.get(k), centre=[round(float(nxz[idx, 0].mean()), 1), round(float(np.median(ntop[idx])), 2), round(float(nxz[idx, 1].mean()), 1)]))
    cinfo = {c_["id"]: c_ for c_ in comps}
    issues = []
    # intended walkable areas (level.json "walkable" rects, written by the generator per platform)
    areas = []
    for w in L.get("walkable", []):
        inside = (nxz[:, 0] >= w["min"][0]) & (nxz[:, 0] <= w["max"][0]) & (nxz[:, 1] >= w["min"][1]) & (nxz[:, 1] <= w["max"][1]) & (np.abs(ntop - w["y"]) <= 0.6)
        idx = np.flatnonzero(inside & ok); total = max(1, int(np.sum(inside)))
        reach = [i for i in idx if comp[i] in fwd] if home is not None else []
        name = w.get("name", f"walkable@{w['min']}"); ctr = [(w["min"][0] + w["max"][0]) / 2, w["y"], (w["min"][1] + w["max"][1]) / 2]
        a = dict(name=name, standable_m2=round(len(idx) * cell * cell, 1), reachable_fraction=round(len(reach) / max(1, len(idx)), 2) if len(idx) else 0.0,
                 one_way=bool(reach) and not all(comp[i] in back for i in reach))
        areas.append(a)
        if not len(idx): issues.append(dict(kind="no_standable_surface", severity="error", object=name, pos=ctr, message=f"{name}: no standable surface (blocked, too steep or no headroom)"))
        elif a["reachable_fraction"] < 0.5 and not w.get("unreachable_ok"):
            issues.append(dict(kind="unreachable_platform", severity="error", object=name, pos=ctr, message=f"{name}: not reachable from the spawn (walk/drop/jump with the gameplay config)"))
        elif a["one_way"] and not w.get("one_way_ok"):
            issues.append(dict(kind="one_way_trap", severity="warning", object=name, pos=ctr, message=f"{name}: reachable but no way back to the spawn area"))
    sp_rep = []
    for s in spawns:
        p = s["position"]; ni = nearest(p); r = dict(id=s["id"], position=p)
        if ni is None or comp[ni] < 0:
            r["standable"] = False; issues.append(dict(kind="spawn_not_standable", severity="error", object=s["id"], pos=p, message=f"{s['id']}: not on a standable surface"))
        else:
            r.update(standable=True, clearance_m=round(float((dist[ni] + 0.5) * cell), 2), headroom_m=round(float(min(nceil[ni] - ntop[ni], 99)), 2), component=int(comp[ni]))
            if hz_tree is not None:
                lower = s_top[hz_nodes] <= ntop[ni] + 0.1; d, _ = hz_tree.query([p[0], p[2]], k=min(64, len(hz_nodes)))
                d = np.atleast_1d(d); j = np.atleast_1d(_)[np.isfinite(d)]; d = d[np.isfinite(d)]
                dl = d[lower[j]] if len(j) else []
                r["hazard_distance_m"] = round(float(dl.min()), 2) if len(dl) else None
                if len(dl) and dl.min() < D_["spawn_hazard_distance"]:
                    issues.append(dict(kind="spawn_near_hazard", severity="warning", object=s["id"], pos=p, message=f"{s['id']}: hazard {dl.min():.1f} m away (< {D_['spawn_hazard_distance']} m)"))
            if r["clearance_m"] < D_["spawn_clearance"]:
                issues.append(dict(kind="spawn_cramped", severity="warning", object=s["id"], pos=p, message=f"{s['id']}: only {r['clearance_m']} m to a wall/edge (< {D_['spawn_clearance']} m)"))
            if r["headroom_m"] < D_["min_headroom"]:
                issues.append(dict(kind="spawn_low_ceiling", severity="warning", object=s["id"], pos=p, message=f"{s['id']}: headroom {r['headroom_m']} m"))
            if s["id"] != "spawn" and home is not None and (comp[ni] not in fwd or comp[ni] not in back):
                issues.append(dict(kind="spawn_disconnected", severity="error", object=s["id"], pos=p, message=f"{s['id']}: not connected both ways with the main spawn"))
        sp_rep.append(r)
    # spawn candidates (used by refine.py to relocate an unsafe spawn): roomy, away from hazards, in the main area
    cand = []; big = max(comps, key=lambda c_: c_["area_m2"])["id"] if comps else None
    pool = [k for k in fwd if k in back] if home is not None else ([big] if big is not None else [])
    idx = np.flatnonzero(ok & np.isin(comp, pool))
    if len(idx):
        clr = (dist[idx] + 0.5) * cell; hd = hz_tree.query(nxz[idx])[0] if hz_tree is not None else np.full(len(idx), 99.0)
        sc = np.minimum(clr / D_["spawn_clearance"], 1) + np.minimum(hd / D_["spawn_hazard_distance"], 1) + ((nceil[idx] - ntop[idx]) >= D_["min_headroom"]) + 0.01 * np.minimum(clr, 5)
        for i in idx[np.argsort(-sc)]:
            p_ = [round(float(nxz[i, 0]), 2), round(float(ntop[i]), 2), round(float(nxz[i, 1]), 2)]
            if all(math.hypot(p_[0] - c_[0], p_[2] - c_[2]) > 8 for c_ in cand): cand.append(p_)
            if len(cand) >= 6: break
    # narrow connectors: elongated walkable objects whose walkable width < min_bridge_width (camera + strafing room)
    narrow = []
    reach_nodes = np.array([comp[i] in fwd for i in range(N)]) if home is not None else ok
    for o in np.unique(top_obj[nodes]):
        idx = np.flatnonzero((top_obj[nodes] == o) & reach_nodes)
        if len(idx) * cell * cell < 2: continue
        ext = nxz[idx].max(0) - nxz[idx].min(0) + cell; width = (2 * dist[idx].max() + 1) * cell
        others = np.isin(comp, np.unique(comp[idx])) & (top_obj[nodes] != o)  # a connector shares its walk component with other objects
        if max(ext) >= 2 * min(ext) and width < D_["min_bridge_width"] and others.sum() * cell * cell >= D_["min_platform_area_m2"]:
            nm = str(onames[o]); ctr = [float(nxz[idx, 0].mean()), float(np.median(ntop[idx])), float(nxz[idx, 1].mean())]
            narrow.append(dict(object=nm, width_m=round(width, 2))); issues.append(dict(kind="narrow_connector", severity="warning", object=nm, pos=[round(v, 1) for v in ctr],
                                                                                    message=f"{nm}: walkable width ~{width:.1f} m (< {D_['min_bridge_width']} m) - tight for strafing / the camera"))
    low = np.flatnonzero(ok & (nceil - ntop < D_["min_headroom"]) & reach_nodes)
    if len(low):
        objs = sorted({str(onames[o]) for o in top_obj[nodes[low]]})[:8]
        issues.append(dict(kind="low_ceiling", severity="info", object=objs[0], pos=[round(float(nxz[low[0], 0]), 1), round(float(ntop[low[0]]), 2), round(float(nxz[low[0], 1]), 1)],
                           message=f"{len(low) * cell * cell:.0f} m² reachable floor has < {D_['min_headroom']} m headroom (cramped camera): {', '.join(objs)}"))
    reach_area = sum(c_["area_m2"] for c_ in comps if c_["reachable"]); tot_area = sum(c_["area_m2"] for c_ in comps)
    R = dict(gameplay_status=G.get("status", ""), cell=cell, standable_area_m2=round(tot_area, 1), reachable_area_m2=round(reach_area, 1),
             components=len(comps), links=[dict(frm_component=a, to_component=b, **v) for (a, b), v in links.items()],
             spawns=sp_rep, intended_areas=areas, narrow_connectors=narrow,
             unreached_components=[c_ for c_ in sorted(comps, key=lambda c_: -c_["area_m2"]) if not c_["reachable"] and c_["area_m2"] >= D_["min_platform_area_m2"]][:12],
             issues=issues, passed=not any(i["severity"] == "error" for i in issues), spawn_candidates=cand, component_list=comps)
    if write:
        os.makedirs(os.path.join(level_dir, "checks"), exist_ok=True)
        json.dump(R, open(os.path.join(level_dir, "checks", "navigation.json"), "w"), indent=1)
        _draw(os.path.join(level_dir, "checks", "navigation.png"), nx, nz, cell, b0, s_cell, s_top, hazard_top, nodes, comp, cinfo, links, spawns, L)
    if verbose:
        print(json.dumps(dict(standable_m2=R["standable_area_m2"], reachable_m2=R["reachable_area_m2"], components=R["components"], links=len(links),
                              issues=[i["message"] for i in issues][:12], passed=R["passed"])))
    return R


def _blocked(pa, pb, hmax, s_cell, s_lo, s_top, cs, ce, b0, cell, nx, nz, P_):
    """Straight jump/drop path a->b blocked by something rising above the higher end (ignores overhead structures)?"""
    n = max(2, int(np.hypot(*(pb - pa)) / (cell / 2)))
    apex = hmax + P_["jump_height"] + 0.3
    for t in np.linspace(0, 1, n)[1:-1]:
        x, z = pa + (pb - pa) * t; ix, iz = int((x - b0[0]) / cell), int((z - b0[2]) / cell)
        if not (0 <= ix < nx and 0 <= iz < nz): continue
        c = iz * nx + ix
        for s in range(cs[c], ce[c]):
            if s_lo[s] < apex and s_top[s] > hmax + 0.25: return True
    return False


def _reach(n, links, home):
    """Forward (from home) and backward (to home) reachability over component links; fwd[k] = how it was reached."""
    if home is None: return {}, set()
    out = {}
    for (a, b), v in links.items(): out.setdefault(a, []).append((b, v["kind"]))
    fwd = {home: "spawn"}; fr = [home]
    while fr:
        nxt = []
        for a in fr:
            for b, k in out.get(a, []):
                if b not in fwd: fwd[b] = k if fwd[a] == "spawn" else fwd[a] if fwd[a] == k else "jump" if "jump" in (k, fwd[a]) else k; nxt.append(b)
        fr = nxt
    inn = {}
    for (a, b) in links: inn.setdefault(b, []).append(a)
    back = {home}; fr = [home]
    while fr:
        nxt = []
        for b in fr:
            for a in inn.get(b, []):
                if a not in back: back.add(a); nxt.append(a)
        fr = nxt
    return fwd, back


def _draw(path, nx, nz, cell, b0, s_cell, s_top, hazard_top, nodes, comp, cinfo, links, spawns, L, px=3):
    from PIL import Image, ImageDraw
    img = np.zeros((nz, nx, 3), np.uint8) + np.array([28, 30, 34], np.uint8)
    top = np.full(nx * nz, -np.inf)
    allsp = np.arange(len(s_cell)); np.maximum.at(top, s_cell, s_top)
    yr = (top[np.isfinite(top)].min(), top[np.isfinite(top)].max()) if np.isfinite(top).any() else (0, 1)
    shade = lambda yy: 0.55 + 0.45 * (yy - yr[0]) / max(1e-6, yr[1] - yr[0])
    for s in allsp[(s_top >= top[s_cell] - 1e-6)]:  # top-most surface per cell: grey by height
        v = int(70 * shade(s_top[s])); img.flat[s_cell[s] * 3:s_cell[s] * 3 + 3] = [v, v, v + 6]
    for s in np.flatnonzero(hazard_top & (s_top >= top[s_cell] - 1e-6)): img.flat[s_cell[s] * 3:s_cell[s] * 3 + 3] = [70, 200, 40]
    for k, s in enumerate(nodes):
        if s_top[s] < top[s_cell[s]] - 2.0 and comp[k] >= 0: pass  # covered by something higher: still draw (dimmer) below
        ci = comp[k]
        if ci < 0: col = [90, 90, 110]
        elif cinfo[ci]["reachable"]:
            g = shade(s_top[s]); col = [int(60 * g), int(150 * g), int(230 * g)] if cinfo[ci]["can_return"] else [int(230 * g), int(150 * g), int(40 * g)]
        else: col = [220, 50, 50]
        if s_top[s] >= top[s_cell[s]] - 2.0: img.flat[s_cell[s] * 3:s_cell[s] * 3 + 3] = col
    im = Image.fromarray(img).resize((nx * px, nz * px), Image.NEAREST); dr = ImageDraw.Draw(im)
    w2p = lambda x, z: ((x - b0[0]) / cell * px, (z - b0[2]) / cell * px)
    for (a, b), v in links.items():
        if a in cinfo and cinfo[a]["reachable"]:
            dr.line([w2p(v["frm"][0], v["frm"][2]), w2p(v["to"][0], v["to"][2])], fill=(255, 230, 60) if v["kind"] == "jump" else (255, 140, 40), width=1)
    for s in spawns:
        x, z = w2p(s["position"][0], s["position"][2]); dr.ellipse([x - 5, z - 5, x + 5, z + 5], fill=(255, 255, 255), outline=(0, 0, 0))
    dr.rectangle([0, 0, im.width, 14], fill=(0, 0, 0))
    dr.text((4, 2), "blue=reachable  orange=reachable one-way  red=unreachable  green=hazard  lines: yellow jump / orange drop  N=up", fill=(255, 255, 255))
    im.save(path)


if __name__ == "__main__":
    R = analyse(sys.argv[1])
    sys.exit(0 if R["passed"] else 1)
