"""Stage 8: connection anchors + relationships (the connection-aware scene graph).

ANCHORS are named points on an object, in its LOCAL coordinates (position, outward direction, kind, width/diameter),
transformed to world space through the parent chain exactly like the builder. Most are derived from the object type,
so existing levels get them for free; level.json objects may add/override them: "anchors": {"name": {"pos": [x,y,z],
"dir": [x,y,z], "kind": "...", "width": w}}.
  ramp / stairs     low (base edge, -z), high (top edge, +z)                         kind walk_end
  box / cylinder    edge_px / edge_nx / edge_pz / edge_nz at top height (+ top)        kind walk_edge
  long thin box     end_a / end_b along its long axis (bridge / walkway decks)         kind walk_end
  cylinder          outlet (+y end, diameter) / inlet (-y end)                         kind opening
  stream            source (outlet) / sink (end of the gravity path)                   kind liquid
  channel           outlet (+z end) / inlet (-z end)                                   kind opening
  any               base (bottom centre, -y)                                           kind support

RELATIONS (level.json "relations": [...], backwards compatible - levels without it get them INFERRED):
  {"type": "walkable_connection", "a": connector, "a_anchor": "high", "b": surface object, "b_anchor": "auto"}
  {"type": "emits_from", "a": stream, "b": pipe, "b_anchor": "outlet"}   {"type": "flows_into", "a": stream, "b": pool}
  {"type": "supported_by", "a": x, "b": y}   {"type": "attached_to", "a": x, "b": y}   {"type": "aligned_with", "a": x, "b": y}
  {"type": "connects_to", "a": x, "b": y}    {"type": "intentional_gap", "a": x, "b": y, "note": "jump challenge"}
Any relation may carry "intentional": true (a deliberate offset/gap/overlap the validator must not "fix").
"""
import fnmatch, math
import numpy as np
from trimesh.transformations import euler_matrix, translation_matrix

TYPES = ("walkable_connection", "connects_to", "supported_by", "attached_to", "emits_from", "flows_into", "aligned_with", "intentional_gap")
CONNECTOR_NAMES = ("*Bridge*", "*_Deck", "*Catwalk*", "*Link_*", "*Ramp*", "*Stairs*", "*Steps*")


def node_matrix(o):
    return translation_matrix(o.get("position", [0, 0, 0])) @ euler_matrix(*np.radians(o.get("rotation", [0, 0, 0])), "sxyz")


def world_matrices(L):
    by = {o["name"]: o for o in L["objects"]}; W = {}

    def m(n, depth=0):
        if n in W: return W[n]
        o = by[n]; p = o.get("parent"); T = node_matrix(o)
        W[n] = m(p, depth + 1) @ T if p in by and depth < 64 else T; return W[n]
    for n in by: m(n)
    return W, by


def is_connector(o):
    if o.get("connector") is not None: return bool(o["connector"])
    if o.get("type") in ("ramp", "stairs"): return True
    if o.get("type") != "box" or not o.get("size"): return False
    w, h, d = o["size"]
    return h <= 0.8 and max(w, d) >= 2.0 * min(w, d) and max(w, d) >= 2.5 and any(fnmatch.fnmatch(o["name"], p) for p in CONNECTOR_NAMES)


def local_anchors(o):
    t = o["type"]; A = {}
    if o.get("size"):
        w, h, d = o["size"]
        A["base"] = dict(pos=[0, 0, 0], dir=[0, -1, 0], kind="support", width=max(w, d))
        if t in ("ramp", "stairs"):
            A["low"] = dict(pos=[0, 0, -d / 2], dir=[0, 0, -1], kind="walk_end", width=w)
            A["high"] = dict(pos=[0, h, d / 2], dir=[0, 0, 1], kind="walk_end", width=w)
        elif t in ("box", "cylinder", "boundary"):
            for k, (p, di, wd) in {"edge_px": ([w / 2, h, 0], [1, 0, 0], d), "edge_nx": ([-w / 2, h, 0], [-1, 0, 0], d),
                                   "edge_pz": ([0, h, d / 2], [0, 0, 1], w), "edge_nz": ([0, h, -d / 2], [0, 0, -1], w)}.items():
                A[k] = dict(pos=p, dir=di, kind="walk_edge", width=wd)
            A["top"] = dict(pos=[0, h, 0], dir=[0, 1, 0], kind="surface", width=min(w, d))
            if t == "box" and is_connector(o):
                if o.get("axis", "z" if d >= w else "x") == "z": A["end_a"], A["end_b"] = dict(A["edge_nz"], kind="walk_end"), dict(A["edge_pz"], kind="walk_end")
                else: A["end_a"], A["end_b"] = dict(A["edge_nx"], kind="walk_end"), dict(A["edge_px"], kind="walk_end")
            if t == "cylinder":
                A["outlet"] = dict(pos=[0, h, 0], dir=[0, 1, 0], kind="opening", width=min(w, d), section="circle")
                A["inlet"] = dict(pos=[0, 0, 0], dir=[0, -1, 0], kind="opening", width=min(w, d), section="circle")
        elif t == "stream":
            from shapes import stream_path
            path = stream_path(h, o); P, T, _ = path[-1]
            A["source"] = dict(pos=[0, 0, 0], dir=path[1][1].tolist(), kind="liquid", width=w, section=o.get("section", "circle"))
            A["sink"] = dict(pos=P.tolist(), dir=T.tolist(), kind="liquid", width=w * (1 + float(o.get("widen", 0.2))), section=o.get("section", "circle"))
        elif t == "channel":
            A["outlet"] = dict(pos=[0, o.get("wall", 0.2), d / 2], dir=[0, 0, 1], kind="opening", width=w - 2 * o.get("wall", 0.2), section="rect")
            A["inlet"] = dict(pos=[0, o.get("wall", 0.2), -d / 2], dir=[0, 0, -1], kind="opening", width=w - 2 * o.get("wall", 0.2), section="rect")
        elif t == "panel":
            A["back"] = dict(pos=[0, h / 2, 0], dir=[0, 0, -1], kind="attach", width=w)
    for k, v in (o.get("anchors") or {}).items():
        A[k] = dict(dict(kind="custom", width=1.0, dir=[0, 0, 1]), **v)
    return A


def world_anchor(W, o, name):
    a = local_anchors(o).get(name)
    if a is None: return None
    M = W[o["name"]]; p = (M @ [*a["pos"], 1])[:3]; d = M[:3, :3] @ np.array(a["dir"], float); n = np.linalg.norm(d)
    return dict(a, name=name, obj=o["name"], pos=p, dir=d / n if n else d)


def world_anchors(L, W=None):
    W = W or world_matrices(L)[0]
    return {o["name"]: {k: world_anchor(W, o, k) for k in local_anchors(o)} for o in L["objects"]}


def validate_relations(L):
    """Structural check of explicit relations: known type, objects + anchors exist."""
    by = {o["name"]: o for o in L["objects"]}; errs = []
    for i, r in enumerate(L.get("relations", [])):
        if r.get("type") not in TYPES: errs.append(f"relations[{i}]: unknown type {r.get('type')} (known: {', '.join(TYPES)})"); continue
        for k in ("a", "b"):
            if r.get(k) is None and k == "b" and r["type"] in ("walkable_connection", "intentional_gap"): continue
            if r.get(k) not in by: errs.append(f"relations[{i}] ({r['type']}): object '{r.get(k)}' does not exist")
            elif r.get(k + "_anchor") not in (None, "auto") and r[k + "_anchor"] not in local_anchors(by[r[k]]):
                errs.append(f"relations[{i}]: '{r[k]}' has no anchor '{r[k + '_anchor']}' (has {sorted(local_anchors(by[r[k]]))})")
    return errs


def infer_relations(L):
    """Relations for levels that don't declare them (hand-made / older levels). Explicit ones always win."""
    by = {o["name"]: o for o in L["objects"]}; rel = list(L.get("relations", [])); have = {(r["type"], r["a"], r.get("a_anchor")) for r in rel}
    hz = set(L.get("hazards", [])); hz_mats = {by[h].get("material") for h in hz if h in by}
    explicit = bool(L.get("relations"))
    for o in L["objects"]:
        n = o["name"]
        if explicit and o.get("gen"): continue  # generated levels carry their own graph; infer only for manual additions
        if is_connector(o):
            ends = ("low", "high") if o["type"] in ("ramp", "stairs") else ("end_a", "end_b")
            for e in ends:
                if ("walkable_connection", n, e) not in have: rel.append(dict(type="walkable_connection", a=n, a_anchor=e, b=None, b_anchor="auto", inferred=True))
        liquid = o.get("material") in hz_mats and n not in hz
        if liquid and (o["type"] == "stream" or n.endswith("_Fall")):
            src = n[:-5] if n.endswith("_Fall") else None
            if src in by and by[src]["type"] == "cylinder" and ("emits_from", n, None) not in have and not any(r["type"] == "emits_from" and r["a"] == n for r in rel):
                rel.append(dict(type="emits_from", a=n, b=src, b_anchor="outlet", inferred=True))
            if not any(r["type"] == "flows_into" and r["a"] == n for r in rel):
                pool = next(iter(sorted(hz)), None)
                if pool: rel.append(dict(type="flows_into", a=n, b=pool, inferred=True))
    return rel
