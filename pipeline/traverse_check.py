"""Stage 79: walk every connector (ramp, stairs, bridge, catwalk) with the player capsule, up AND down, on the real
collision geometry (mobile/collision.glb - what the game collides with), and report where a player would get caught.

The grid navigation (gameplay.py, 1 m cells) says whether two floors are linked; this follows the actual surfaces in
0.1 m steps, like a CharacterBody3D with the gameplay.json player (radius, height, step_height, max_slope_deg):
  blocked   something in front of the capsule above step height (a lip, a riser too tall, a beam) - the player stops
  steep     the surface under the capsule is steeper than max_slope_deg for 0.2 m or more - the player slides back
  fall      the floor drops away under the capsule (a gap between the connector and a floor)
  head      not enough headroom (capsule height) over the surface
  scrape    the capsule's side touches something (rail, cladding, wall) - it snags / gets pushed
Lanes: the centre line (problems are errors) and one lane near each side edge (problems are warnings: the player can
hug the rail there). Endpoints: the connector's two ends along its long axis, plus 1 m onto each floor.
Output: checks/traverse.json; checks.py turns the findings into report issues."""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path: sys.path.insert(0, HERE)


def _cast(O, D, T):
    """Nearest hit (t, triangle index) of rays O + t D against triangles T (Moller-Trumbore, brute force)."""
    if not len(T): return np.full(len(O), np.inf), np.full(len(O), -1)
    v0, e1, e2 = T[:, 0], T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]
    p = np.cross(D[:, None, :], e2[None]); det = np.einsum("mk,nmk->nm", e1, p); ok = np.abs(det) > 1e-12
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0); s = O[:, None, :] - v0[None]
    u = np.einsum("nmk,nmk->nm", s, p) * inv; q = np.cross(s, e1[None]); v = np.einsum("nk,nmk->nm", D, q) * inv
    t = np.einsum("mk,nmk->nm", e2, q) * inv; hit = ok & (u >= 0) & (v >= 0) & (u + v <= 1) & (t > 1e-5)
    t = np.where(hit, t, np.inf); i = t.argmin(1); return t[np.arange(len(O)), i], np.where(np.isfinite(t.min(1)), i, -1)


def _walk(pts, y0, T, N, P):
    """Capsule walk along xz points (0.1 m apart) starting with feet at y0. Returns the first problem per kind."""
    r, sh, H, smax = P["radius"], P["step_height"], P["height"], P["max_slope_deg"]
    y = y0; out = {}; steep_run = 0; ring = [(0, 0)] + [(0.25 * math.cos(a), 0.25 * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    for k in range(1, len(pts)):
        a, b = pts[k - 1], pts[k]; d = np.array([b[0] - a[0], 0.0, b[1] - a[1]]); d /= np.linalg.norm(d) or 1.0
        side = np.array([-d[2], 0.0, d[0]])
        Ob = np.array([[a[0], y + h, a[1]] for h in (sh + 0.05, 0.9, H - 0.15)])
        tb, _ = _cast(Ob, np.repeat(d[None], 3, 0), T)
        if (tb < r + 0.1).any(): out.setdefault("blocked", [round(float(a[0]), 2), round(y + float((sh + 0.05, 0.9, H - 0.15)[int(np.argmin(tb))]), 2), round(float(a[1]), 2)])
        Og = np.array([[b[0] + ox, y + sh + 0.05, b[1] + oz] for ox, oz in ring]); tg, ig = _cast(Og, np.repeat([[0.0, -1.0, 0.0]], len(ring), 0), T)
        hg = np.where(np.isfinite(tg), y + sh + 0.05 - tg, -np.inf)
        g = float(hg.max())
        if not np.isfinite(g) or g < y - (sh + 0.35):
            out.setdefault("fall", [round(float(b[0]), 2), round(y, 2), round(float(b[1]), 2)])
            Od = np.array([[b[0], y + sh, b[1]]]); td, _ = _cast(Od, np.array([[0.0, -1.0, 0.0]]), T)
            if not np.isfinite(td[0]): break
            g = y + sh - float(td[0])
        if ig[0] >= 0 and hg[0] > g - sh:  # slope under the capsule centre (on a slope the probes ahead are higher: not the max)
            n = N[ig[0]]; ang = math.degrees(math.acos(min(1.0, abs(float(n[1])))))
            steep_run = steep_run + 1 if ang > smax + 0.5 else 0  # 2 steps (0.2 m) in a row: a slope, not a sliver of an edge
            if steep_run >= 2: out.setdefault("steep", [round(float(b[0]), 2), round(g, 2), round(float(b[1]), 2), round(ang, 1)])
        else: steep_run = 0
        tu, _ = _cast(np.array([[b[0], g + 0.05, b[1]]]), np.array([[0.0, 1.0, 0.0]]), T)
        if tu[0] < H - 0.05: out.setdefault("head", [round(float(b[0]), 2), round(g, 2), round(float(b[1]), 2)])
        Os = np.array([[b[0], g + h, b[1]] for h in (sh + 0.1, 1.2) for _ in (0, 1)]); Ds = np.array([side, -side, side, -side])
        ts, _ = _cast(Os, Ds, T)
        if (ts < r - 0.02).any(): out.setdefault("scrape", [round(float(b[0]), 2), round(g + 0.6, 2), round(float(b[1]), 2)])
        y = g
    return out, y


def run(d, verbose=True, write=True):
    from validate_level import load_tris
    from anchors import world_matrices
    from gameplay import load_gameplay
    L = json.load(open(os.path.join(d, "level.json"))); P = load_gameplay(d, L)["player"]
    cp = os.path.join(d, "mobile", "collision.glb")
    if not os.path.exists(cp): return dict(passed=True, skipped="no mobile/collision.glb", findings=[])
    T, names, _ = load_tris(cp, skip_invisible=False, skip_nonplayable=False)
    soft = set(L.get("hazards", [])) | {e.get("id") for e in L.get("exits", [])}
    keep = np.array([not (n in soft or n.startswith("Hazard") or n.endswith("_Trigger")) for n in names]); T = T[keep]
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
    W, _ = world_matrices(L); res, findings = [], []
    for o in L["objects"]:
        if not o.get("connector") or not o.get("size"): continue
        M = np.asarray(W[o["name"]]); w, h, dd = o["size"]; top = h if o["type"] == "box" else 0.0
        e0, e1 = (M @ [0, top, -dd / 2 - 1.0, 1])[:3], (M @ [0, h, dd / 2 + 1.0, 1])[:3]
        ax = np.array([e1[0] - e0[0], e1[2] - e0[2]]); Lx = float(np.linalg.norm(ax)); ax /= Lx or 1.0; sd = np.array([-ax[1], ax[0]])
        lo, hi = np.minimum(e0, e1) - [w + 2, 3, w + 2], np.maximum(e0, e1) + [w + 2, P["height"] + 3, w + 2]
        Tm = (T.max(1) >= lo).all(1) & (T.min(1) <= hi).all(1); Tl, Nl = T[Tm], nrm[Tm]
        n = max(2, int(Lx / 0.1) + 1); rec = dict(name=o["name"], type=o["type"], length=round(Lx, 2), lanes={})
        for lane, off in (("centre", 0.0), ("left", -(w / 2 - P["radius"] - 0.15)), ("right", w / 2 - P["radius"] - 0.15)):
            base = [np.array([e0[0], e0[2]]) + sd * off + ax * Lx * k / (n - 1) for k in range(n)]
            for way, pts in (("up" if e1[1] >= e0[1] else "down", base), ("down" if e1[1] >= e0[1] else "up", base[::-1])):
                ys = e0[1] if pts is base else e1[1]
                t0, _ = _cast(np.array([[pts[0][0], ys + 2.0, pts[0][1]]]), np.array([[0.0, -1.0, 0.0]]), Tl)
                if not np.isfinite(t0[0]): rec["lanes"][f"{lane}_{way}"] = {"start": "no floor"}; continue
                prob, _ = _walk(pts, ys + 2.0 - float(t0[0]), Tl, Nl, P); rec["lanes"][f"{lane}_{way}"] = prob
                for kind, pos in prob.items():
                    findings.append(dict(object=o["name"], lane=lane, way=way, kind=kind, pos=pos[:3], severity="error" if lane == "centre" and kind != "scrape" else "warning",
                                         message=f"{o['name']}: walking {way} the {lane} lane the player is {dict(blocked='stopped by an edge / lip', steep='on a slope steeper than the max', fall='dropping through a gap', head='hitting its head', scrape='scraping the side')[kind]}"
                                                 + (f" ({pos[3]} deg)" if kind == "steep" else "")))
        res.append(rec)
    R = dict(player={k: P[k] for k in ("radius", "height", "step_height", "max_slope_deg")}, connectors=len(res), findings=findings,
             passed=not any(f["severity"] == "error" for f in findings), results=res,
             note="capsule walk on mobile/collision.glb in 0.1 m steps, both directions; PLACEHOLDER player values from gameplay.json")
    if write:
        os.makedirs(os.path.join(d, "checks"), exist_ok=True); json.dump(R, open(os.path.join(d, "checks", "traverse.json"), "w"), indent=1)
    if verbose: print(json.dumps(dict(connectors=len(res), passed=R["passed"], findings=[f["message"] for f in findings][:30]), indent=1))
    return R


if __name__ == "__main__":
    run(sys.argv[1])
