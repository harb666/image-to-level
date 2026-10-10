"""Stage 8: safe, deterministic, reversible geometry repairs driven by geometry_check findings.

  python3 pipeline/geometry_repair.py levels/<name> [--dry-run] [--max-passes 2]

Only findings with a concrete "repair" and not marked ambiguous are applied; INTENTIONAL findings are never touched.
Every repair changes ONLY the object named in the finding (never unrelated objects), is recorded with the object's
before/after JSON in checks/repairs.json, and the whole level is snapshotted first (edit_level.py undo reverts it).
Actions
  extend             lengthen a connector (bridge deck / walkway / ramp / stairs) at the failing end along its own
                     axis: closes a gap, or pushes an overhanging end onto the floor; the other end stays put
  elevate            ramp / stairs end at the wrong height: change its rise (low end on the floor stays put)
  stream_from_outlet replace a liquid block (or a misaligned stream) by a "stream" that leaves the pipe's real opening
                     (position, direction, diameter, round section) and ends submerged in the receiving pool;
                     keeps the name, material and hazard role
  lengthen_stream    stream stops above / at the pool surface: lengthen its drop so it enters the pool
  extend_inlet       pipe hanging in front of a wall: lengthen it backwards into the wall (outlet stays put)
  nudge              z-fighting coplanar faces: move the connector / smaller object 1 cm behind the other surface
  drop               small prop hovering a few cm: lower it onto what is below
  extend_foundation  (Stage 9) ground below a foundation: lower the foundation's bottom, top unchanged
  terrain_lower      (Stage 9) terrain poking through a floor: add a "lower"-only pad under it (never raises ground)
  terrain_add        (Stage 9) boundary at open ground: add a low ridge OUTSIDE the playable boundary
  middle_extend      (Stage 9) gap in the distant scenery: widen + raise the middle zone (never playable)
Ambiguous cases (a connector leading nowhere, big hovers, blocked openings, crates in a landing) are left for Claude.
After repairs the level is rebuilt and re-checked (bounded passes).
"""
import copy, json, math, os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def _parent_rot(L, W, o):
    p = o.get("parent"); return W[p][:3, :3] if p else np.eye(3)


def _world_to_parent(L, W, o, v):
    return np.linalg.inv(_parent_rot(L, W, o)) @ np.asarray(v, float)


def _move(L, W, o, world_delta):
    d = _world_to_parent(L, W, o, world_delta); o["position"] = [round(float(a + b), 4) for a, b in zip(o.get("position", [0, 0, 0]), d)]


def act_extend(L, W, o, f):
    from anchors import local_anchors
    rp = f["repair"]; dist = float(rp["distance"]); a = local_anchors(o)[rp["anchor"]]; w, h, d = o["size"]
    ax = np.array(a["dir"], float); ax[1] = 0; ax /= np.linalg.norm(ax)  # local axis pointing out of that end
    k = 2 if abs(ax[2]) > abs(ax[0]) else 0
    if o["type"] in ("ramp", "stairs"): k = 2
    sz = list(o["size"]); sz[k] = round(sz[k] + dist, 4); o["size"] = sz
    R = W[o["name"]][:3, :3]; _move(L, W, o, R @ (ax * dist / 2))
    return f"lengthened {dist:.2f} m at {rp['anchor']}"


def act_elevate(L, W, o, f):
    dy = float(f["repair"]["dy"]); sz = list(o["size"])
    if f["repair"]["anchor"] == "high": sz[1] = round(max(0.05, sz[1] + dy), 4); o["size"] = sz; return f"rise {dy:+.2f} m"
    _move(L, W, o, [0, dy, 0]); sz[1] = round(max(0.05, sz[1] - dy), 4); o["size"] = sz; return f"low end {dy:+.2f} m"


def stream_for(L, W, src, anchor="outlet", pool=None, keep=None):
    """A stream object leaving the real opening of src (pipe / channel), dropping into the pool (top y)."""
    from anchors import world_anchor
    a = world_anchor(W, src, anchor); O, D = a["pos"], a["dir"]; dia = a["width"]
    horiz = math.hypot(D[0], D[2]); pitch = math.degrees(math.atan2(D[1], horiz)); yaw = math.degrees(math.atan2(D[0], D[2])) if horiz > 1e-6 else 0.0
    pool_y = 0.0
    if pool:
        po = next(o for o in L["objects"] if o["name"] == pool); pool_y = float((W[pool] @ [0, po["size"][1], 0, 1])[1])
    drop = max(0.5, O[1] - pool_y + 0.3)
    sec = a.get("section", "circle"); s = dict(keep or {})
    s.update(type="stream", position=[round(float(v), 3) for v in O], rotation=[0, round(yaw, 2), 0],
             size=[round(dia * 0.86, 3), round(drop, 3), round(dia * 0.86 if sec == "circle" else min(dia * 0.35, 0.5), 3)],
             section=sec, speed=0.0 if pitch < -60 else round(1.2 + 0.25 * dia, 2), pitch=round(min(0.0, pitch), 2) if pitch > -60 else -90, inset=round(min(0.3, dia * 0.2), 3))
    s.pop("parent", None)
    return s


def act_stream(L, W, o, f, rel):
    src = next(x for x in L["objects"] if x["name"] == f["repair"]["source"])
    pool = next((r["b"] for r in rel if r["type"] == "flows_into" and r["a"] == o["name"]), (L.get("hazards") or [None])[0])
    keep = {k: v for k, v in o.items() if k in ("name", "material", "gen", "source", "collision")}
    new = stream_for(L, W, src, f["repair"].get("anchor", "outlet"), pool, keep); o.clear(); o.update(new)
    L.setdefault("relations", [])
    for r in (dict(type="emits_from", a=o["name"], b=src["name"], b_anchor=f["repair"].get("anchor", "outlet")), dict(type="flows_into", a=o["name"], b=pool)):
        if r["b"] and not any(x["type"] == r["type"] and x["a"] == r["a"] for x in L["relations"]): L["relations"].append(r)
    return f"stream from {src['name']}.{f['repair'].get('anchor', 'outlet')} (Ø {o['size'][0]:.2f} m, drop {o['size'][1]:.2f} m) into {pool}"


def act_lengthen_stream(L, W, o, f):
    sz = list(o["size"]); sz[1] = round(sz[1] + float(f["repair"]["distance"]), 3); o["size"] = sz; return f"drop +{f['repair']['distance']:.2f} m"


def act_extend_inlet(L, W, o, f):
    dist = float(f["repair"]["distance"]); sz = list(o["size"]); sz[1] = round(sz[1] + dist, 3); o["size"] = sz
    R = W[o["name"]][:3, :3]; _move(L, W, o, R @ np.array([0, -dist, 0])); return f"pipe lengthened {dist:.2f} m into the wall"


def act_nudge(L, W, o, f, g_normals):
    n = g_normals.get(tuple(sorted(f["objects"][:2])), np.array([0, 1.0, 0])); dist = float(f["repair"]["distance"])
    _move(L, W, o, -n * dist); return f"moved {dist * 1000:.0f} mm behind {f['repair']['other']}"


def act_drop(L, W, o, f):
    _move(L, W, o, [0, -float(f["repair"]["distance"]), 0]); return f"lowered {f['repair']['distance']:.2f} m onto its support"


def act_extend_foundation(L, W, o, f):
    """Foundation bottom above the ground somewhere: lower its bottom (top stays) to below the lowest ground."""
    top = o["position"][1] + o["size"][1]; to = min(f["repair"]["to_y"], o["position"][1])
    o["position"][1] = round(to, 3); o["size"][1] = round(top - to, 3); return f"bottom lowered to {to:.2f} (top unchanged)"


def _terrain_add(L, f):
    feat = dict(f["repair"]["feature"]); fs = L["terrain"].setdefault("features", [])
    if any(x["id"] == feat["id"] for x in fs): return "already present"
    fs.append(feat); return f"terrain feature {feat['id']} ({feat['type']}{', ' + feat['mode'] if feat.get('mode') else ''}) added"


def _middle_extend(L, f):
    z = L["terrain"].setdefault("zones", {}).setdefault("middle", {}); r = z.get("radius", 380); z["radius"] = round(r * 1.15)
    z["rise"] = z.get("rise", 32.0) + 8.0; return f"middle zone radius {r} -> {z['radius']} m, rise {z['rise']} m"


TERRAIN_ACTIONS = dict(terrain_lower=_terrain_add, terrain_add=_terrain_add, middle_extend=_middle_extend)


def repair(d, dry=False, max_passes=2, verbose=True):
    import geometry_check as GC
    from anchors import world_matrices, infer_relations
    lp = os.path.join(d, "level.json"); log, before_all = [], json.load(open(lp)); done_ids = set()
    for k in range(max_passes):
        R = GC.run(d, verbose=False); L = json.load(open(lp)); W, by = world_matrices(L); rel = infer_relations(L)
        todo = [f for f in R["findings"] if f["repair"] and not f["ambiguous"] and f["cls"] in ("ERROR", "WARNING")]
        seen, applied = set(), []
        normals = {}
        for f in todo:  # one repair per object per pass (re-measured next pass)
            a = f["repair"]["action"]
            if a in TERRAIN_ACTIONS:  # Stage 9: edits of level.json["terrain"] (features / zones), never of objects
                key = (f["check"], a, json.dumps(f["repair"].get("feature", {}).get("id")))
                if key in done_ids or not isinstance(L.get("terrain"), dict): continue
                b = copy.deepcopy(L["terrain"]); msg = TERRAIN_ACTIONS[a](L, f); done_ids.add(key)
                applied.append(dict(pass_=k + 1, finding=f["message"], action=a, object="terrain", result=msg, before=None, after=None)); continue
            o = by.get(f["repair"]["obj"])
            if o is None or o["name"] in seen: continue
            key = (f["check"], o["name"], f["repair"]["action"], json.dumps(f["repair"].get("anchor")))
            if key in done_ids and f["repair"]["action"] != "extend": continue
            b = copy.deepcopy(o); a = f["repair"]["action"]
            try:
                if a == "extend": msg = act_extend(L, W, o, f)
                elif a == "elevate": msg = act_elevate(L, W, o, f)
                elif a == "stream_from_outlet": msg = act_stream(L, W, o, f, rel)
                elif a == "lengthen_stream": msg = act_lengthen_stream(L, W, o, f)
                elif a == "extend_inlet": msg = act_extend_inlet(L, W, o, f)
                elif a == "nudge":
                    if "normal" not in f: f["normal"] = _overlap_normal(d, L, f)
                    normals[tuple(sorted(f["objects"][:2]))] = np.array(f["normal"]); msg = act_nudge(L, W, o, f, normals)
                elif a == "drop": msg = act_drop(L, W, o, f)
                elif a == "extend_foundation": msg = act_extend_foundation(L, W, o, f)
                else: continue
            except Exception as e:
                log.append(dict(finding=f["message"], action=a, object=o["name"], result=f"skipped: {e}")); continue
            seen.add(o["name"]); done_ids.add(key); applied.append(dict(pass_=k + 1, finding=f["message"], action=a, object=o["name"], result=msg, before=b, after=copy.deepcopy(o)))
        if not applied: break
        from edit_level import _schema_errors, snapshot
        if _schema_errors(L): log.append(dict(result="repairs refused: level would be invalid", errors=[e["message"] for e in _schema_errors(L)][:5])); break
        if dry: log += applied; break
        if k == 0: snapshot(d, before_all, "geometry repair")
        json.dump(L, open(lp, "w"), indent=1); log += applied
        subprocess.run([sys.executable, os.path.join(HERE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    R = GC.run(d, verbose=False) if not dry else R
    rep = dict(repairs=[{k: v for k, v in x.items() if k not in ("before", "after")} for x in log], details=log, remaining=R["counts"],
               needs_review=[f["message"] for f in R["findings"] if f["cls"] == "ERROR" or (f["cls"] == "WARNING" and (f["ambiguous"] or not f["repair"]))][:30],
               note="Each repair touched only the named object; undo with: python3 pipeline/edit_level.py <level> undo")
    if not dry: json.dump(rep, open(os.path.join(d, "checks", "repairs.json"), "w"), indent=1, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x))
    if verbose:
        for x in log: print(f"  {x.get('object', '')}: {x.get('result')}")
        print(json.dumps(dict(applied=len(log), remaining=R["counts"], needs_review=rep["needs_review"][:10]), indent=1))
    return rep


def _overlap_normal(d, L, f):
    """Plane normal of the coplanar overlap (re-derived from the two objects' shared faces)."""
    import geometry_check as GC
    from gameplay import load_gameplay
    g = GC.Geo(d, L, load_gameplay(d, L)); a, b = f["objects"][:2]
    ia, ib = np.flatnonzero(g.obj == a), np.flatnonzero(g.obj == b)
    best = None
    for i in ia:
        for j in ib[:400]:
            if np.dot(g.n[i], g.n[j]) > 0.999 and abs(np.dot(g.n[i], g.T[i, 0] - g.T[j, 0])) < 0.006: best = g.n[i]; break
        if best is not None: break
    return (best if best is not None else np.array([0, 1.0, 0])).tolist()


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    mp = int(sys.argv[sys.argv.index("--max-passes") + 1]) if "--max-passes" in sys.argv else 2
    repair(a[0], dry="--dry-run" in sys.argv, max_passes=mp)
