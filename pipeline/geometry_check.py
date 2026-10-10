"""Stage 8: physical-coherence validation of a built level (any theme) -> checks/geometry.json + geometry.md

  python3 pipeline/geometry_check.py levels/<name>

Uses the real world-space triangles of level.glb + connection anchors / relations (anchors.py), not centre distances.
Every finding is classified:  ERROR (definite construction failure) | WARNING (review) | INTENTIONAL (declared on
purpose: relation "intentional": true, "intentional_gap", object "intentional": [...], validation.ignore_objects).
Checks
  connection     each connector end (bridge / walkway deck / ramp / stairs) meets a walkable surface: gap, partial
                 support (overhang), elevation mismatch, wrong target, railing blocking the entrance
  stairs_ramps   step rise <= player step_height, tread, slope <= max_slope, width >= player
  support        every structure touches / rests on / is attached to something (floating, small hovers)
  overlap        coplanar overlapping faces of different materials (z-fighting flicker)
  mesh           NaN / degenerate triangles / open boundaries on solid types
  outlet         liquid emitted from a pipe/channel: position + direction + cross-section match the opening,
                 no rectangular block under a circular pipe, does not start inside other solids
  flow           streams reach the receiving pool (submerged, inside it), don't pass through walls,
                 liquid surfaces don't cover walkable floors
  openings       arches / gates keep their opening clear
  terrain        cracks between terrain pieces (rocks / cliffs grounded via "support")
  collision      collision.json present + newer than level.json, every hazard has a hazard area
  spawn          spawn safety (from gameplay.py)
Each finding may carry a deterministic "repair" (geometry_repair.py applies the unambiguous ones).
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


class Geo:
    """World-space triangles per object + walkable-surface queries."""

    def __init__(self, d, L, G):
        from validate_level import load_tris, closed_mask
        self.L, self.G = L, G
        T, names, objs = load_tris(os.path.join(d, "level.glb"), skip_invisible=False)
        self.T = T; self.node = names; self.obj = np.array([n[:-4] if n.endswith("_Top") else n for n in names])
        self.mat = np.array([objs[n][2] for n in names])
        nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nl = np.linalg.norm(nrm, axis=1); self.area = nl / 2
        self.n = nrm / np.maximum(nl, 1e-12)[:, None]; self.lo = T.min(1); self.hi = T.max(1)
        by = {o["name"]: o for o in L["objects"]}; self.by = by
        hz = set(L.get("hazards", [])); hzm = {by[h].get("material") for h in hz if h in by}
        self.liquid_objs = hz | {o["name"] for o in L["objects"] if o.get("material") in hzm or o["type"] == "stream"}
        self.liquid = np.array([o in self.liquid_objs for o in self.obj]); bnd = np.array([by.get(o, {}).get("type") == "boundary" for o in self.obj])
        self.walk = (self.n[:, 1] >= math.cos(math.radians(G["player"]["max_slope_deg"]))) & ~self.liquid & ~bnd
        self.body = closed_mask(names, objs)
        wi = np.flatnonzero(self.walk)
        if len(wi):
            from validate_level import inside_solid
            cm = self.body >= 0; P = T[wi].mean(1) + [0, 0.03, 0]; bur = np.zeros(len(wi), bool)
            for k in range(0, len(wi), 512): bur[k:k + 512] = inside_solid(P[k:k + 512], T[cm], self.body[cm])
            self.walk[wi[bur]] = False
        ter = np.array([by.get(o, {}).get("type") == "terrain" for o in self.obj])  # terrain skirts reach below the world floor
        self.ground_y = float(T[~ter][:, :, 1].min()) if (~ter).any() else (float(T[:, :, 1].min()) if len(T) else 0.0)
        # base level: lowest LARGE up-facing surface (ground, deck or liquid) - nothing below it is ever seen by the camera
        up = (self.n[:, 1] > 0.9) & ~ter & ~bnd
        if up.any():
            hy = np.round(T[up, :, 1].mean(1), 2); u = np.unique(hy); big = [v for v in u if self.area[up][hy == v].sum() >= 25]
            self.base_level = float(min(big)) if big else self.ground_y
        else: self.base_level = self.ground_y
        self.boundary = bnd
        self.bgT = np.zeros((0, 3, 3))  # background ground layers support objects standing outside the playable floor
        bgp = os.path.join(d, "background.glb")
        if os.path.exists(bgp) and L.get("environment"):
            try:
                bt, bn, _ = load_tris(bgp, skip_invisible=False); gid = {"BG_" + l["id"] for l in L["environment"].get("background", []) if l.get("type") == "ground"}
                self.bgT = bt[np.isin(bn, list(gid))]
            except Exception: pass
        # xz grid hash of walkable triangles
        self.cs = 2.0; self.grid = {}
        for i in np.flatnonzero(self.walk):
            for gx in range(int(self.lo[i, 0] // self.cs), int(self.hi[i, 0] // self.cs) + 1):
                for gz in range(int(self.lo[i, 2] // self.cs), int(self.hi[i, 2] // self.cs) + 1):
                    self.grid.setdefault((gx, gz), []).append(i)

    def family(self, name):
        """name + all descendants (groups)."""
        kids = {name}; ch = True
        while ch:
            ch = False
            for o in self.L["objects"]:
                if o.get("parent") in kids and o["name"] not in kids: kids.add(o["name"]); ch = True
        return kids

    def surface(self, p, dy_max, exclude=(), tris=None):
        """Walkable surface under/over point p within |dy| <= dy_max: (dy, object) closest, or None."""
        cand = tris if tris is not None else self.grid.get((int(p[0] // self.cs), int(p[2] // self.cs)), [])
        best = None
        for i in cand:
            if self.obj[i] in exclude: continue
            a, b, c = self.T[i]; v0, v1, v2 = b - a, c - a, p - a
            den = v0[0] * v1[2] - v1[0] * v0[2]
            if abs(den) < 1e-12: continue
            u = (v2[0] * v1[2] - v1[0] * v2[2]) / den; v = (v0[0] * v2[2] - v2[0] * v0[2]) / den
            if u < -1e-6 or v < -1e-6 or u + v > 1 + 1e-6: continue
            y = a[1] + u * v0[1] + v * v1[1]; dy = y - p[1]
            if abs(dy) <= dy_max and (best is None or abs(dy) < abs(best[0])): best = (dy, self.obj[i])
        return best

    def near(self, lo, hi, exclude=()):
        m = np.all(self.hi >= lo, 1) & np.all(self.lo <= hi, 1)
        if exclude: m &= ~np.isin(self.obj, list(exclude))
        return np.flatnonzero(m)

    def inside(self, P, idx):
        """Points inside any CLOSED body among triangles idx."""
        from validate_level import inside_solid
        bodies = np.unique(self.body[np.asarray(idx, int)]) if len(idx) else []
        bodies = [b for b in bodies if b >= 0]  # parity needs the WHOLE closed body, not just the nearby triangles
        idx = np.flatnonzero(np.isin(self.body, bodies))
        if not len(idx) or not len(P): return np.zeros(len(P), bool)
        return inside_solid(np.asarray(P, float), self.T[idx], self.body[idx])

    def cast(self, O, D, idx, far):
        from validate_level import cast
        if not len(idx): return np.full(len(O), np.inf), np.full(len(O), -1)
        t, i, _ = cast(np.asarray(O, float), np.asarray(D, float), self.T[idx], far); return t, np.where(i >= 0, np.asarray(idx)[np.maximum(i, 0)], -1)


def _intentional(L, names, what):
    ign = set(L.get("validation", {}).get("ignore_objects", []))
    by = {o["name"]: o for o in L["objects"]}
    for n in names:
        if n in ign or what in (by.get(n, {}).get("intentional") or []): return True
    for r in L.get("relations", []):
        if (r.get("a") in names or r.get("b") in names) and (r.get("intentional") or r["type"] == "intentional_gap"): return True
    return False


def F(check, cls, objects, msg, pos=None, measured=None, repair=None, ambiguous=False):
    return dict(check=check, cls=cls, objects=list(objects), message=msg, pos=None if pos is None else [round(float(v), 2) for v in pos],
                measured=measured or {}, repair=repair, ambiguous=ambiguous)


def check_connections(g, L, rel, W, out):
    from anchors import world_anchor, local_anchors
    P_ = g.G["player"]; step = P_["step_height"]
    for r in rel:
        if r["type"] != "walkable_connection": continue
        o = g.by.get(r["a"])
        if not o: continue
        a = world_anchor(W, o, r.get("a_anchor"))
        if a is None: continue
        fam = g.family(o["name"]); u = a["dir"].copy(); u[1] = 0; nu = np.linalg.norm(u)
        if nu < 1e-6: continue
        u /= nu; v = np.array([-u[2], 0, u[0]]); Wd = a["width"]; E = a["pos"]
        S = np.linspace(-Wd / 2 + min(0.3, Wd / 4), Wd / 2 - min(0.3, Wd / 4), 5)
        hits = [g.surface(E + v * s + u * 0.15 + [0, 0.0, 0], step, fam) for s in S]
        f = sum(h is not None for h in hits) / len(hits); tag = f"{o['name']}.{r.get('a_anchor')}"
        intent = _intentional(L, [o["name"]], "gap")
        targets = {h[1] for h in hits if h}
        if r.get("b") and targets and not any(t in g.family(r["b"]) for t in targets):
            out.append(F("connection", "WARNING", [o["name"], r["b"]], f"{tag} meets {sorted(str(t) for t in targets)} instead of {r['b']}", E))
        buried = g.surface(E + [0, 0.205, 0], 0.2, fam)  # a floor ABOVE the end (within 0.4 m): the end is tucked under it
        if buried and f > 0: continue  # end tucked UNDER a floor plate (dip-under junction): hidden, no lip
        if f >= 0.8:
            dys = [abs(h[0]) for h in hits if h]
            if max(dys) > 0.05: out.append(F("connection", "WARNING", [o["name"]], f"{tag}: {max(dys):.2f} m lip where it meets {sorted(str(t) for t in targets)}", E, dict(lip=max(dys))))
            continue
        if f > 0:  # partly over the edge: how far must the end move along the connector to be fully supported?
            ext = None
            for x in np.arange(0.1, 3.01, 0.1):
                E3 = E + u * x
                if sum(g.surface(E3 + v * s - u * 0.05, step, fam) is not None for s in S) >= 5: ext = round(float(x) + 0.05, 2); break
            out.append(F("connection", "ERROR" if f < 0.6 else "WARNING", [o["name"]], f"{tag}: only {f:.0%} of the {Wd:.1f} m end rests on a floor (overhangs an edge)", E,
                         dict(supported_fraction=f), dict(action="extend", obj=o["name"], anchor=r.get("a_anchor"), distance=ext) if ext else None, ambiguous=ext is None))
            continue
        gap = None
        for x in np.arange(0.25, 4.01, 0.05):
            h = g.surface(E + u * x, step, fam)
            if h: gap = (round(float(x), 2), h); break
        if gap and not intent:
            out.append(F("connection", "ERROR", [o["name"], gap[1][1]], f"{tag} stops {gap[0] - 0.15:.2f} m short of {gap[1][1]}", E, dict(gap=gap[0] - 0.15),
                         dict(action="extend", obj=o["name"], anchor=r.get("a_anchor"), distance=round(gap[0] - 0.13, 2), target=gap[1][1])))
            continue
        mism = g.surface(E + u * 0.3, 1.6, fam)
        if mism and not intent:
            out.append(F("connection", "ERROR", [o["name"], mism[1]], f"{tag}: elevation mismatch {mism[0]:+.2f} m with {mism[1]}", E, dict(dy=mism[0]),
                         dict(action="elevate", obj=o["name"], anchor=r.get("a_anchor"), dy=round(float(mism[0]), 3)) if o["type"] in ("ramp", "stairs") else None,
                         ambiguous=o["type"] not in ("ramp", "stairs")))
            continue
        out.append(F("connection", "INTENTIONAL" if intent else "ERROR", [o["name"]], f"{tag} leads nowhere (no floor within 4 m at step height)" + (" - declared intentional" if intent else ""), E, ambiguous=True))
    # declared gaps (jump challenges): reported as INTENTIONAL, measured, and checked against the jump ability
    for r in rel:
        if r["type"] != "intentional_gap" or r.get("a") not in g.by or r.get("b") not in g.by: continue
        A = np.flatnonzero(np.isin(g.obj, list(g.family(r["a"]))) & g.walk); B = np.flatnonzero(np.isin(g.obj, list(g.family(r["b"]))) & g.walk)
        if not len(A) or not len(B): continue
        def main_floor(I):  # the height carrying most walkable area (not a crate top)
            hy = np.round(g.T[I, :, 1].mean(1) / 0.05) * 0.05; u = np.unique(hy); ar = [g.area[I][hy == v].sum() for v in u]; y0 = u[int(np.argmax(ar))]
            P = g.T[I[np.abs(hy - y0) < 0.03]].reshape(-1, 3); return P, float(y0)
        pa, ya = main_floor(A); pb, yb = main_floor(B)
        from scipy.spatial import cKDTree
        dist, j = cKDTree(pb[:, [0, 2]]).query(pa[:, [0, 2]]); k = int(np.argmin(dist)); gap = float(dist[k]); dy = float(yb - ya)
        ok = gap <= P_["jump_distance"] and dy <= P_["jump_height"]
        out.append(F("connection", "INTENTIONAL" if ok else "WARNING", [r["a"], r["b"]],
                     f"deliberate gap {r['a']} -> {r['b']}: {gap:.2f} m, dy {dy:+.2f} m - " + ("jumpable with the gameplay config, left open" if ok else f"NOT jumpable (jump {P_['jump_distance']} m / {P_['jump_height']} m) - left open, review"),
                     (pa[k] + pb[j[k]]) / 2, dict(gap=gap, dy=dy, jumpable=ok)))
    # something standing in a connector's landing zone (railings, crates, walls...) blocks the entrance
    if True:
        ridx = np.flatnonzero(~g.liquid & (g.area > 1e-4))
        for r in rel:
            if r["type"] != "walkable_connection" or r["a"] not in g.by: continue
            a = world_anchor(W, g.by[r["a"]], r.get("a_anchor"))
            if a is None: continue
            u = a["dir"].copy(); u[1] = 0; u /= (np.linalg.norm(u) or 1); v = np.array([-u[2], 0, u[0]]); c = a["pos"] + u * 0.3
            ext = np.abs(v) * a["width"] * 0.4 + np.abs(u) * 0.35
            lo_b, hi_b = c - ext + [0, 0.35, 0], c + ext + [0, 1.6, 0]
            hit = ridx[np.all(g.hi[ridx] >= lo_b, 1) & np.all(g.lo[ridx] <= hi_b, 1)]
            hit = sorted({g.obj[i] for i in hit} - g.family(r["a"]))
            if hit:
                kind = "railing " if g.by.get(hit[0], {}).get("type") == "railing" else ""
                out.append(F("connection", "ERROR" if kind else "WARNING", [r["a"]] + hit[:2], f"{kind}{hit[0]} stands in the landing of {r['a']}.{r.get('a_anchor')} (blocks the route)", a["pos"], ambiguous=True))


def check_stairs_ramps(g, L, out):
    P_ = g.G["player"]
    for o in L["objects"]:
        if o["type"] not in ("stairs", "ramp") or not o.get("size"): continue
        w, h, d = o["size"]; slope = math.degrees(math.atan2(h, d))
        if w < 2 * P_["radius"] + 0.3: out.append(F("stairs_ramps", "ERROR", [o["name"]], f"{o['name']}: {w:.2f} m wide - narrower than the player ({2 * P_['radius']:.2f} m + clearance)"))
        if o["type"] == "stairs":
            n = max(2, int(round(h / 0.25))); rise, tread = h / n, d / n
            if rise > P_["step_height"] + 1e-6: out.append(F("stairs_ramps", "ERROR", [o["name"]], f"{o['name']}: step rise {rise:.2f} m > step_height {P_['step_height']} m"))
            if tread < 0.22: out.append(F("stairs_ramps", "WARNING", [o["name"]], f"{o['name']}: tread {tread:.2f} m (< 0.22 m) - steep"))
            if slope > 45: out.append(F("stairs_ramps", "WARNING", [o["name"]], f"{o['name']}: {slope:.0f}° stair slope"))
        elif slope > P_["max_slope_deg"] + 0.5:
            out.append(F("stairs_ramps", "ERROR", [o["name"]], f"{o['name']}: ramp slope {slope:.0f}° > max_slope {P_['max_slope_deg']}° (not walkable)"))


def check_support(g, L, rel, out):
    from anchors import is_connector
    roots = [o for o in L["objects"] if not o.get("parent")]
    props = [o for o in L["objects"] if o.get("parent") and o["type"] in ("box", "cylinder", "rock", "tank", "machinery", "vent")
             and o.get("size") and max(o["size"]) <= 3.0 and not any(t in o["name"] for t in ("_Post_", "_Rail_", "_Mid_", "_Win_", "_Rib_"))]
    skip_t = {"boundary", "terrain", "stream"}
    for o in roots + props:  # whole structures, plus loose props inside groups (crates, tanks...) - siblings count as support
        n = o["name"]
        if o["type"] in skip_t or n in g.liquid_objs or is_connector(o): continue  # connectors: their ends are checked by "connection"
        fam = g.family(n); idx = np.flatnonzero(np.isin(g.obj, list(fam)))
        if not len(idx): continue
        lo, hi = g.T[idx].reshape(-1, 3).min(0), g.T[idx].reshape(-1, 3).max(0)
        if lo[1] <= max(g.ground_y, g.base_level) + 0.03: continue
        nb = g.near(lo - 0.08, hi + 0.08, fam)
        contact = bool(len(nb)) and touching(g, idx, nb)
        if not contact and len(nb):  # sunk into an OPEN surface (terrain): something crosses just above its bottom
            V = g.T[idx].reshape(-1, 3); B = V[V[:, 1] <= lo[1] + 0.05][:80]
            t, _ = g.cast(B - [0, 0.02, 0], np.tile([0, 1.0, 0], (len(B), 1)), nb, 2.0); contact = bool(np.isfinite(t).any())
        if not contact and len(g.bgT):  # standing on the distant ground (outside the playable floor)
            from validate_level import cast as _cast
            V = g.T[idx].reshape(-1, 3); B = V[V[:, 1] <= lo[1] + 0.05][:60]
            near_bg = g.bgT[np.all(g.bgT.max(1) >= lo - 1, 1) & np.all(g.bgT.min(1) <= hi + 1, 1)]
            if len(near_bg):
                t1 = _cast(B + [0, 0.5, 0], np.tile([0, -1.0, 0], (len(B), 1)), near_bg, 1.5)[0]
                t2 = _cast(B - [0, 0.5, 0], np.tile([0, 1.0, 0], (len(B), 1)), near_bg, 3.0)[0]
                contact = bool(np.isfinite(t1).any() or np.isfinite(t2).any())
        if contact: continue
        if _intentional(L, [n], "floating"): out.append(F("support", "INTENTIONAL", [n], f"{n} floats (declared intentional)", (lo + hi) / 2)); continue
        V = g.T[idx].reshape(-1, 3); bot = V[V[:, 1] <= lo[1] + 0.02]; bot = bot[np.linspace(0, len(bot) - 1, min(len(bot), 40)).astype(int)]
        below = g.near(np.r_[lo[0] - .1, g.ground_y - 1, lo[2] - .1], np.r_[hi[0] + .1, lo[1] + .1, hi[2] + .1], fam)
        t, ti = g.cast(bot + [0, 1e-3, 0], np.tile([0, -1.0, 0], (len(bot), 1)), below, 200)
        hov = float(t.min()) if np.isfinite(t).any() else None; onto = g.obj[ti[np.argmin(t)]] if hov is not None else None
        prop = o["type"] in ("rock", "tank", "machinery", "vent", "box", "cylinder", "group") and (hi - lo).max() < 6
        if o["type"] == "cylinder" and any(r["type"] == "emits_from" and r.get("b") == n for r in rel):  # a pipe: its inlet should sit in a wall / machine
            from anchors import world_anchor, world_matrices
            Wm = world_matrices(L)[0]; a = world_anchor(Wm, o, "inlet"); rr = a["width"] / 2; v = np.cross(a["dir"], [0, 1, 0]); v = v / (np.linalg.norm(v) or 1)
            pts = [a["pos"] + v * k * rr * 0.7 for k in (-1, 0, 1)]; nb2 = g.near(a["pos"] - 4, a["pos"] + 4, fam)
            t, ti = g.cast(pts, [a["dir"]] * 3, nb2, 3.5)
            if np.isfinite(t).all():
                out.append(F("support", "ERROR", [n, g.obj[ti[1]]], f"pipe {n} ends {t.max():.2f} m in front of {g.obj[ti[1]]} (inlet not attached)", a["pos"], dict(gap=float(t.max())),
                             dict(action="extend_inlet", obj=n, distance=round(float(t.max()) + 0.3, 3)))); continue
        if hov is not None and hov <= 0.35 and prop:
            out.append(F("support", "WARNING", [n, onto], f"{n} hovers {hov:.2f} m above {onto}", (lo + hi) / 2, dict(hover=hov), dict(action="drop", obj=n, distance=round(hov, 3))))
        else:
            out.append(F("support", "ERROR" if hov is None or hov > 0.35 else "WARNING", [n], f"{n} is not supported or attached" + (f" ({hov:.2f} m above {onto})" if hov is not None else " (nothing below)"),
                         (lo + hi) / 2, dict(hover=hov), ambiguous=True))
    for r in rel:  # explicit supported_by / attached_to relations must really touch
        if r["type"] not in ("supported_by", "attached_to") or r.get("a") not in g.by or r.get("b") not in g.by: continue
        A = np.flatnonzero(np.isin(g.obj, list(g.family(r["a"])))); B = np.flatnonzero(np.isin(g.obj, list(g.family(r["b"]))))
        if not len(A) or not len(B): continue
        if not touching(g, A, B):
            out.append(F("support", "ERROR", [r["a"], r["b"]], f"{r['a']} is declared {r['type']} {r['b']} but does not touch it", g.T[A].reshape(-1, 3).mean(0), ambiguous=True))


def touching(g, A, B, tol=0.08):
    """Do triangle sets A and B touch / interpenetrate? Dense surface samples of the smaller set cast both ways along
    their normals (flush and slightly embedded contacts) + vertices inside the other's closed bodies."""
    from gameplay import _sample
    if g.area[A].sum() > g.area[B].sum(): A, B = B, A
    P, I = _sample(g.T[A], 0.3); sel = np.linspace(0, len(P) - 1, min(len(P), 600)).astype(int); P, N = P[sel], g.n[A][I[sel]]
    t, _ = g.cast(np.r_[P - N * 0.02, P + N * 0.02], np.r_[N, -N], B, tol + 0.02)
    if np.isfinite(t).any(): return True
    return bool(g.inside(g.T[A].reshape(-1, 3)[::2], B).any()) or bool(g.inside(g.T[B].reshape(-1, 3)[::2], A).any())


def check_overlap(g, L, out):
    """Coplanar overlapping faces of different materials -> z-fighting."""
    keys = {}
    hidden = ((g.n[:, 1] < -0.9) & (g.T[:, :, 1].max(1) <= g.base_level + 0.01)) | (g.T[:, :, 1].max(1) <= g.ground_y + 0.01) | g.boundary  # under the base floor / invisible: never seen
    for i in np.flatnonzero((g.area > 1e-3) & ~hidden):
        nn = np.round(g.n[i], 2); dd = float(np.dot(g.n[i], g.T[i, 0]))
        keys.setdefault((tuple(nn), round(dd / 0.004)), []).append(i)
    pairs, samples = {}, {}
    for k, idx in keys.items():
        idx = idx + keys.get((k[0], k[1] + 1), [])
        objs = {g.obj[i] for i in idx}
        if len(objs) < 2: continue
        n = np.array(k[0]); ax = np.eye(3)[np.argmin(np.abs(n))]; e1 = np.cross(n, ax); e1 /= np.linalg.norm(e1); e2 = np.cross(n, e1)
        P2 = {i: np.c_[g.T[i] @ e1, g.T[i] @ e2] for i in idx}
        for a_ in range(len(idx)):
            for b_ in range(a_ + 1, len(idx)):
                i, j = idx[a_], idx[b_]
                if g.obj[i] == g.obj[j] or g.mat[i].split("__")[0] == g.mat[j].split("__")[0]: continue
                A, B = P2[i], P2[j]
                if (A.max(0) < B.min(0) + 0.02).any() or (B.max(0) < A.min(0) + 0.02).any(): continue
                ov = np.prod(np.minimum(A.max(0), B.max(0)) - np.maximum(A.min(0), B.min(0)))
                if ov > 1e-3 and (_in_tri(A.mean(0), B) or _in_tri(B.mean(0), A) or ov > 0.05):
                    key = tuple(sorted((g.obj[i], g.obj[j]))); pairs[key] = pairs.get(key, 0) + min(ov, g.area[i], g.area[j])
                    c2 = (np.maximum(A.min(0), B.min(0)) + np.minimum(A.max(0), B.max(0))) / 2  # centre of the overlap, in plane coords
                    p3 = n * np.dot(n, g.T[i, 0]) + e1 * c2[0] + e2 * c2[1]
                    samples.setdefault(key, []).append((p3, n))
    from anchors import is_connector
    for (a, b), area in pairs.items():
        if area < 0.02: continue
        S = samples[(a, b)][:12]; P = np.array([c + n_ * 0.03 for c, n_ in S])  # visible? the space in front of the faces must be open
        nb = g.near(P.min(0) - 0.1, P.max(0) + 0.1, g.family(a) | g.family(b))
        if len(nb) and g.inside(P, nb).all(): continue
        oa, ob = g.by.get(a, {}), g.by.get(b, {})
        mover = a if is_connector(oa) else b if is_connector(ob) else (a if (np.prod(oa.get("size", [1, 1, 1])) <= np.prod(ob.get("size", [1, 1, 1]))) else b)
        cls = "INTENTIONAL" if _intentional(L, [a, b], "overlap") else "WARNING"
        i = np.flatnonzero(g.obj == mover)
        out.append(F("overlap", cls, [a, b], f"{a} and {b} share coplanar faces ({area:.2f} m², different materials): z-fighting flicker",
                     g.T[i].reshape(-1, 3).mean(0) if len(i) else None, dict(area_m2=round(area, 3)), dict(action="nudge", obj=mover, other=a if mover == b else b, distance=0.01)))


def _in_tri(p, T):
    a, b, c = T; v0, v1, v2 = b - a, c - a, p - a; den = v0[0] * v1[1] - v1[0] * v0[1]
    if abs(den) < 1e-12: return False
    u = (v2[0] * v1[1] - v1[0] * v2[1]) / den; v = (v0[0] * v2[1] - v2[0] * v0[1]) / den
    return u >= 0 and v >= 0 and u + v <= 1


def check_mesh(g, L, out):
    by = g.by
    for nm in np.unique(g.node):
        idx = np.flatnonzero(g.node == nm); T = g.T[idx]; base = nm[:-4] if nm.endswith("_Top") else nm; o = by.get(base, {})
        if not np.isfinite(T).all(): out.append(F("mesh", "ERROR", [base], f"{nm}: NaN/inf vertices")); continue
        bad = int((g.area[idx] < 1e-9).sum())
        if bad: out.append(F("mesh", "WARNING", [base], f"{nm}: {bad} degenerate triangles"))
        if o.get("type") in ("panel", "terrain", None) or o.get("double_sided"): continue
        V = T.reshape(-1, 3); _, inv = np.unique(np.round(V, 4), axis=0, return_inverse=True); F_ = inv.reshape(-1, 3)
        e = np.sort(F_[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), 1); _, c = np.unique(e, axis=0, return_counts=True)
        if (c == 1).sum(): out.append(F("mesh", "WARNING", [base], f"{nm}: {(c == 1).sum()} open boundary edges (not a closed solid)", V.mean(0)))


def check_liquids(g, L, rel, W, out):
    from anchors import world_anchor
    hz = [h for h in L.get("hazards", []) if h in g.by]
    for r in rel:
        if r["type"] == "emits_from" and r.get("a") in g.by and r.get("b") in g.by:
            s, p = g.by[r["a"]], g.by[r["b"]]; O = world_anchor(W, p, r.get("b_anchor") or "outlet")
            if O is None: out.append(F("outlet", "ERROR", [r["a"], r["b"]], f"{r['b']} has no outlet anchor", ambiguous=True)); continue
            intent = _intentional(L, [s["name"]], "outlet")
            if s["type"] != "stream":  # legacy liquid block
                cls = "INTENTIONAL" if intent or s.get("section") == "rect_ok" else "ERROR"
                out.append(F("outlet", cls, [s["name"], p["name"]], f"{s['name']} is a rectangular {s['type']} under the {O.get('section', 'round')} outlet of {p['name']} (liquid does not leave the opening)",
                             O["pos"], dict(outlet_diameter=O["width"]), dict(action="stream_from_outlet", obj=s["name"], source=p["name"], anchor=r.get("b_anchor") or "outlet")))
                continue
            S = world_anchor(W, s, "source"); off = float(np.linalg.norm(S["pos"] - O["pos"])); ang = math.degrees(math.acos(np.clip(np.dot(S["dir"], O["dir"]) / (np.linalg.norm(S["dir"]) * np.linalg.norm(O["dir"]) or 1), -1, 1)))
            ratio = s["size"][0] / max(O["width"], 1e-6); secm = (s.get("section", "circle") == "circle") == (O.get("section", "circle") == "circle")
            # a vertical outlet pointing up can't pour; a horizontal outlet emits along its axis; downward-tilted fine
            probs = []
            if off > 0.15 * O["width"] + 0.05: probs.append(f"source {off:.2f} m from the opening")
            if ang > 25 and not (O["dir"][1] < -0.9 and S["dir"][1] < -0.9): probs.append(f"direction off by {ang:.0f}°")
            if not 0.5 <= ratio <= 1.05: probs.append(f"cross-section {s['size'][0]:.2f} m vs opening {O['width']:.2f} m")
            if not secm and not intent: probs.append(f"{s.get('section', 'circle')} stream from a {O.get('section', 'circle')} opening")
            if probs:
                out.append(F("outlet", "INTENTIONAL" if intent else "ERROR", [s["name"], p["name"]], f"{s['name']} vs {p['name']} outlet: " + "; ".join(probs), O["pos"],
                             dict(offset=round(off, 3), angle=round(ang, 1), ratio=round(ratio, 2)), dict(action="stream_from_outlet", obj=s["name"], source=p["name"], anchor=r.get("b_anchor") or "outlet")))
            q = S["pos"] + S["dir"] * 0.35
            near = g.near(q - 0.05, q + 0.05, g.family(s["name"]) | g.family(p["name"]))
            if len(near) and g.inside([q], near).any(): out.append(F("outlet", "ERROR", [s["name"]], f"{s['name']} emerges inside solid {g.obj[near[0]]}", q, ambiguous=True))
        if r["type"] == "flows_into" and r.get("a") in g.by and r.get("b") in g.by:
            s, pool = g.by[r["a"]], r["b"]
            pidx = np.flatnonzero((g.obj == pool) & (g.n[:, 1] > 0.9))
            if s["type"] == "stream":
                K = world_anchor(W, s, "sink")["pos"]; S = world_anchor(W, s, "source")["pos"]
            else:
                idx = np.flatnonzero(g.obj == s["name"]); V = g.T[idx].reshape(-1, 3); K = np.r_[V[:, 0].mean(), V[:, 1].min(), V[:, 2].mean()]; S = None
            top = g.surface(np.r_[K[0], K[1], K[2]], 50, (), tris=pidx) if len(pidx) else None
            if top is None:
                land = g.surface(K, 50)
                out.append(F("flow", "ERROR", [s["name"], pool], f"{s['name']} lands outside {pool}" + (f" (on {land[1]})" if land else ""), K, ambiguous=True)); continue
            y_top = K[1] + top[0]
            if K[1] > y_top + 0.02: out.append(F("flow", "ERROR", [s["name"], pool], f"{s['name']} stops {K[1] - y_top:.2f} m above {pool}", K, dict(gap=K[1] - y_top),
                                                 dict(action="lengthen_stream", obj=s["name"], distance=round(K[1] - y_top + 0.3, 3)) if s["type"] == "stream" else None))
            elif K[1] > y_top - 0.08: out.append(F("flow", "WARNING", [s["name"], pool], f"{s['name']} ends at the {pool} surface without entering it (visible seam)", K,
                                                   repair=dict(action="lengthen_stream", obj=s["name"], distance=0.3) if s["type"] == "stream" else None))
            land = g.surface(np.r_[K[0], y_top + 0.01, K[2]], 0.6, {pool, s["name"]})
            if land and land[0] > -0.6 and land[0] >= 0: out.append(F("flow", "ERROR", [s["name"], land[1]], f"{s['name']} lands on walkable {land[1]}, not in {pool}", K, ambiguous=True))
            if s["type"] == "stream":  # path through walls?
                from shapes import stream_path
                M = W[s["name"]]; pts = [(M @ [*P, 1])[:3] for P, _, f in stream_path(s["size"][1], s) if 0.15 < f < 0.85]
                excl = g.family(s["name"]) | {pool} | {r2["b"] for r2 in rel if r2["type"] == "emits_from" and r2["a"] == s["name"]}
                nb = g.near(np.min(pts, 0) - 0.1, np.max(pts, 0) + 0.1, excl) if pts else []
                if len(nb):
                    ins = g.inside(pts, nb)
                    if ins.any(): out.append(F("flow", "ERROR", [s["name"]], f"{s['name']} passes through solid geometry", pts[int(np.argmax(ins))], ambiguous=True))
    # liquid surfaces covering intended walkable floors
    for h in hz:
        idx = np.flatnonzero((g.obj == h) & (g.n[:, 1] > 0.9))
        if not len(idx): continue
        y_top = float(g.T[idx, :, 1].max()); lo, hi = g.T[idx].reshape(-1, 3).min(0), g.T[idx].reshape(-1, 3).max(0)
        for w in L.get("walkable", []):
            if w["y"] < y_top - 0.01 and w["max"][0] > lo[0] and w["min"][0] < hi[0] and w["max"][1] > lo[2] and w["min"][1] < hi[2]:
                c = [(w["min"][0] + w["max"][0]) / 2, w["y"], (w["min"][1] + w["max"][1]) / 2]
                if g.surface(np.r_[c[0], y_top, c[2]], 0.005, (), tris=idx):
                    out.append(F("flow", "ERROR", [h, w.get("name", "?")], f"liquid {h} covers walkable {w.get('name', c)} ({y_top - w['y']:.2f} m deep)", c, ambiguous=True))


def check_openings(g, L, W, out):
    for o in L["objects"]:
        if o["type"] not in ("arch", "round_arch") or not o.get("size"): continue
        w, h, d = o["size"]; M = W[o["name"]]; oh = h * o.get("opening_h", 0.75 if o["type"] == "arch" else 0.75)
        fam = g.family(o.get("parent") or o["name"]) | {o["name"]}
        for yy in (1.0, min(1.8, oh * 0.6)):
            O = (M @ [0, yy, -d / 2 - 0.6, 1])[:3]; E = (M @ [0, yy, d / 2 + 0.6, 1])[:3]; D = (E - O) / np.linalg.norm(E - O)
            nb = g.near(np.minimum(O, E) - 0.1, np.maximum(O, E) + 0.1, {o["name"]})
            t, ti = g.cast([O], [D], nb, float(np.linalg.norm(E - O)))
            if np.isfinite(t[0]) and g.obj[ti[0]] not in fam:
                out.append(F("openings", "ERROR", [o["name"], g.obj[ti[0]]], f"{o['name']} opening blocked by {g.obj[ti[0]]} at {yy:.1f} m", O + D * t[0], ambiguous=True)); break


def check_terrain(g, L, W, out):
    ter = [o for o in L["objects"] if o["type"] == "terrain"]
    for i, a in enumerate(ter):
        for b in ter[i + 1:]:
            def edge(o):
                h = np.array(o["heights"], float); c = o["cell"]; M = W[o["name"]]; nz, nx = h.shape
                ring = [(r, cc) for r in range(nz) for cc in range(nx) if r in (0, nz - 1) or cc in (0, nx - 1)]
                return np.array([(M @ [cc * c, h[r, cc], r * c, 1])[:3] for r, cc in ring])
            A, B = edge(a), edge(b)
            from scipy.spatial import cKDTree
            d, j = cKDTree(B[:, [0, 2]]).query(A[:, [0, 2]])
            m = d < 0.3
            if m.any():
                dy = np.abs(A[m, 1] - B[j[m], 1])
                if dy.max() > 0.05: out.append(F("terrain", "WARNING", [a["name"], b["name"]], f"crack between {a['name']} and {b['name']}: edges differ by up to {dy.max():.2f} m", A[m][int(np.argmax(dy))], ambiguous=True))


def check_collision(d, L, out):
    p = os.path.join(d, "mobile", "collision.json")
    if L.get("mobile", {}).get("export", True) is False: return
    if not os.path.exists(p): out.append(F("collision", "ERROR", [], "mobile/collision.json missing - rebuild")); return
    if os.path.getmtime(p) + 1 < os.path.getmtime(os.path.join(d, "level.json")) - 5:
        out.append(F("collision", "WARNING", [], "collision.json is older than level.json - rebuild before export"))
    C = json.load(open(p)); hz = {h["name"] for h in C.get("hazards", [])}
    for h in L.get("hazards", []):
        if h not in hz: out.append(F("collision", "ERROR", [h], f"hazard {h} has no hazard area in collision.json"))
    if not C.get("colliders"): out.append(F("collision", "ERROR", [], "no colliders"))


def run(d, verbose=True, write=True):
    from gameplay import load_gameplay, analyse
    from anchors import world_matrices, infer_relations, validate_relations
    L = json.load(open(os.path.join(d, "level.json"))); G = load_gameplay(d, L); out = []
    for e in validate_relations(L): out.append(F("relations", "ERROR", [], e))
    rel = infer_relations(L); W, _ = world_matrices(L); g = Geo(d, L, G)
    check_connections(g, L, rel, W, out); check_stairs_ramps(g, L, out); check_support(g, L, rel, out); check_overlap(g, L, out)
    check_mesh(g, L, out); check_liquids(g, L, rel, W, out); check_openings(g, L, W, out); check_terrain(g, L, W, out); check_collision(d, L, out)
    try:
        N = analyse(d, G, write=False, verbose=False)
        for i in N["issues"]:
            if i["kind"].startswith("spawn_"): out.append(F("spawn", "ERROR" if i["severity"] == "error" else "WARNING", [i.get("object", "spawn")], i["message"], i.get("pos")))
    except Exception as e: out.append(F("spawn", "WARNING", [], f"navigation unavailable: {e}"))
    order = {"ERROR": 0, "WARNING": 1, "INTENTIONAL": 2}; out.sort(key=lambda f: (order[f["cls"]], f["check"]))
    for k, f in enumerate(out): f["id"] = f"{f['check']}:{k:03d}"
    R = dict(level=os.path.basename(os.path.normpath(d)), counts={c: sum(f["cls"] == c for f in out) for c in order},
             relations=dict(explicit=len(L.get("relations", [])), inferred=len(rel) - len(L.get("relations", []))),
             repairable=sum(1 for f in out if f["repair"] and not f["ambiguous"] and f["cls"] != "INTENTIONAL"), findings=out)
    R["passed"] = R["counts"]["ERROR"] == 0
    if write:
        os.makedirs(os.path.join(d, "checks"), exist_ok=True); json.dump(R, open(os.path.join(d, "checks", "geometry.json"), "w"), indent=1)
        md = [f"# Geometry: {R['level']} - {'PASSED' if R['passed'] else 'NOT PASSED'}", "", f"{R['counts']} · relations {R['relations']} · auto-repairable {R['repairable']}", ""]
        md += [f"- **{f['cls']}** [{f['check']}] {f['message']}" + (" (repair: " + f["repair"]["action"] + ")" if f["repair"] and not f["ambiguous"] else "") for f in out]
        open(os.path.join(d, "checks", "geometry.md"), "w").write("\n".join(md) + "\n")
    if verbose: print(json.dumps(dict(passed=R["passed"], counts=R["counts"], repairable=R["repairable"], top=[f"{f['cls']}: {f['message']}" for f in out[:14]]), indent=1))
    return R


if __name__ == "__main__":
    R = run(sys.argv[1]); sys.exit(0 if R["passed"] else 1)
