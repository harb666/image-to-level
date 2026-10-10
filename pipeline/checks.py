"""Stage 7: one machine-readable report of everything that can be wrong with a built level.

  python3 pipeline/checks.py levels/<name> [--fast]     -> checks/report.json + checks/report.md

Sections (each issue: kind, severity error|warning|info, message, object, pos [x,y,z] when known):
  schema       unique names, parents exist / no cycles, known types, finite positive sizes, finite transforms,
               materials exist + known kinds, hazards/effects/spawn references resolve, duplicate overlapping objects
  assets       level.glb / mobile export / collision / environment / sky / background / effects files exist and parse
  complexity   triangles per object + total, nodes, materials (budgets in config/gameplay.json "budgets")
  performance  dev + mobile file size, draw calls (measured counts) and visible draw calls / texture memory (ESTIMATES)
  navigation   gameplay.py: reachability, spawn safety, narrow connectors, headroom
  camera       validate_level.py: void below the horizon, visible back faces, open meshes (skipped with --fast)
  render       checks/render.json from render_views.py if present (page errors = asset loading problems)
Severity "error" = must fix before export; "warning" = review; "info" = FYI. The list is sorted by impact so the
refinement loop (refine.py) and Claude look at the top of it first.
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import shapes as _shapes
TYPES = {"group", "box", "cylinder", "panel", "spire", "roof", "ramp", "stairs", "terrain", "boundary"} | set(_shapes.SHAPES)  # every builder type
SEV = {"error": 0, "warning": 1, "info": 2}


def world_positions(L):
    from trimesh.transformations import euler_matrix, translation_matrix
    by = {o["name"]: o for o in L["objects"]}; M = {}

    def mat(n, depth=0):
        if n in M: return M[n]
        o = by[n]; T = translation_matrix(o.get("position", [0, 0, 0])) @ euler_matrix(*np.radians(o.get("rotation", [0, 0, 0])), "sxyz")
        p = o.get("parent")
        M[n] = (mat(p, depth + 1) @ T) if p in by and depth < 50 else T; return M[n]
    out = {}
    for n in by:
        try: out[n] = [round(float(v), 2) for v in mat(n)[:3, 3]]
        except RecursionError: out[n] = None
    return out


def schema(L, I):
    from materials import PBR, ALIASES, legacy_texture
    import inspect, re
    kinds = set(PBR) | set(ALIASES) | set(re.findall(r'"([a-z_]+)"', inspect.getsource(legacy_texture)))
    names = [o.get("name") for o in L.get("objects", [])]; by = {}; wp = world_positions(L)
    for i, o in enumerate(L.get("objects", [])):
        n = o.get("name")
        if not n: I.append(dict(kind="schema", severity="error", message=f"objects[{i}] has no name")); continue
        if n in by: I.append(dict(kind="duplicate_name", severity="error", object=n, message=f"{n}: name used twice (names are the stable ids)"))
        by[n] = o
        if o.get("type") not in TYPES: I.append(dict(kind="unknown_type", severity="error", object=n, message=f"{n}: unknown type '{o.get('type')}'"))
        for k in ("position", "rotation"):
            v = o.get(k, [0, 0, 0])
            if not (isinstance(v, list) and len(v) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)):
                I.append(dict(kind="invalid_transform", severity="error", object=n, message=f"{n}: {k} must be 3 finite numbers, got {v}"))
            elif k == "position" and max(abs(x) for x in v) > 5000: I.append(dict(kind="invalid_transform", severity="error", object=n, message=f"{n}: position {v} is absurdly far"))
        if o.get("type") not in ("group", "terrain"):
            sz = o.get("size")
            if not (isinstance(sz, list) and len(sz) == 3 and all(isinstance(x, (int, float)) and math.isfinite(x) and x >= 0 for x in sz)):
                I.append(dict(kind="invalid_size", severity="error", object=n, message=f"{n}: size must be 3 finite numbers >= 0, got {sz}"))
            elif o["type"] != "panel" and min(sz) <= 1e-4 and o["type"] not in ("railing",):
                I.append(dict(kind="degenerate", severity="warning", object=n, pos=wp.get(n), message=f"{n}: zero thickness {sz} (invisible / z-fighting)"))
            if o.get("type") not in ("boundary",):
                m = o.get("material")
                if m not in L.get("materials", {}): I.append(dict(kind="missing_material", severity="error", object=n, message=f"{n}: material '{m}' not defined"))
    for n, o in by.items():
        p, seen = o.get("parent"), set()
        if p and p not in by: I.append(dict(kind="missing_parent", severity="error", object=n, message=f"{n}: parent '{p}' does not exist"))
        while p and p in by:
            if p in seen or p == n: I.append(dict(kind="parent_cycle", severity="error", object=n, message=f"{n}: parent cycle")); break
            seen.add(p); p = by[p].get("parent")
    for k, m in L.get("materials", {}).items():
        if not isinstance(m, dict) or m.get("type") not in kinds: I.append(dict(kind="broken_material", severity="error", object=k, message=f"material {k}: unknown type '{(m or {}).get('type')}'"))
        elif not (isinstance(m.get("color"), list) and len(m["color"]) == 3): I.append(dict(kind="broken_material", severity="error", object=k, message=f"material {k}: color must be [r,g,b] 0..1"))
    for h in L.get("hazards", []):
        if h not in by: I.append(dict(kind="missing_reference", severity="error", object=h, message=f"hazards: '{h}' does not exist"))
    import fnmatch
    for e in L.get("effects", []):
        for k in ("target", "area_from"):
            if e.get(k) and e[k] not in by: I.append(dict(kind="missing_reference", severity="error", object=e["id"], message=f"effect {e['id']}: {k} '{e[k]}' does not exist"))
        for k in ("targets_glob", "at_targets_glob"):
            gl = e.get(k)
            if gl and not any(fnmatch.fnmatch(n, g) for n in by for g in ([gl] if isinstance(gl, str) else gl)):
                I.append(dict(kind="missing_reference", severity="warning", object=e["id"], message=f"effect {e['id']}: {k} matches no object"))
        if e.get("target_material") and e["target_material"] not in L.get("materials", {}): I.append(dict(kind="missing_reference", severity="warning", object=e["id"], message=f"effect {e['id']}: material '{e['target_material']}' not defined"))
    from anchors import validate_relations  # Stage 8 scene graph: types, objects and anchors must exist
    for e in validate_relations(L): I.append(dict(kind="relation", severity="error", message=e))
    if not L.get("spawn") or len(L["spawn"].get("position", [])) != 3: I.append(dict(kind="missing_spawn", severity="error", message="level.json has no valid spawn"))
    seen = {}
    for n, o in by.items():  # exact duplicates (same type/size/material at the same world spot): z-fighting + wasted triangles
        if o.get("type") == "group" or wp.get(n) is None: continue
        key = (o["type"], json.dumps(o.get("size")), o.get("material"), tuple(wp[n]), json.dumps(o.get("rotation")))
        if key in seen: I.append(dict(kind="duplicate_object", severity="warning", object=n, pos=wp[n], message=f"{n}: exact duplicate of {seen[key]} (z-fighting)"))
        else: seen[key] = n
    return wp


def assets(d, L, I):
    from glb_tools import _read
    need = [("level.glb", True), ("mobile/level_mobile.glb", L.get("mobile", {}).get("export", True)), ("mobile/collision.json", L.get("mobile", {}).get("export", True)),
            ("environment.json", bool(L.get("environment"))), ("background.glb", bool(L.get("environment", {}).get("background"))),
            ("effects.json", bool(L.get("effects")))]
    info = {}
    for f, req in need:
        p = os.path.join(d, f)
        if not req: continue
        if not os.path.exists(p): I.append(dict(kind="missing_asset", severity="error", object=f, message=f"{f} missing - rebuild (build_level.py)")); continue
        info[f] = round(os.path.getsize(p) / 1024)
        try:
            if f.endswith(".glb"):
                g, b = _read(p); assert g.get("asset", {}).get("version") == "2.0"
                for im in g.get("images", []): assert im["bufferView"] < len(g["bufferViews"])
            else: json.load(open(p))
        except Exception as e: I.append(dict(kind="broken_asset", severity="error", object=f, message=f"{f} does not parse: {e}"))
    if L.get("environment") and os.path.exists(os.path.join(d, "environment.json")):
        E = json.load(open(os.path.join(d, "environment.json"))); sk = E.get("sky", {}).get("image")
        if sk and not os.path.exists(os.path.join(d, sk)): I.append(dict(kind="missing_asset", severity="error", object=sk, message=f"sky image {sk} missing"))
    if os.path.exists(os.path.join(d, "effects.json")):
        F = json.load(open(os.path.join(d, "effects.json")))
        for k, v in F.get("textures", {}).items():
            if not os.path.exists(os.path.join(d, v)): I.append(dict(kind="missing_asset", severity="error", object=v, message=f"effect texture {v} missing"))
    return info


def complexity(d, L, G, I, wp):
    import trimesh
    B = G["budgets"]; s = trimesh.load(os.path.join(d, "level.glb"), force="scene"); per = {}
    for node in s.graph.nodes_geometry:
        g = s.graph[node][1]; per[node] = per.get(node, 0) + len(s.geometry[g].faces)
    for n, t in sorted(per.items(), key=lambda x: -x[1]):
        if n.startswith(("TR_", "TRM_", "TW_", "SC_", "SCN_")): continue  # Stage 9 terrain chunks / merged scatter cells: judged per chunk (geometry density)
        if t > B["max_object_triangles"]:
            I.append(dict(kind="heavy_object", severity="warning", object=n, pos=wp.get(n), message=f"{n}: {t} triangles (> {B['max_object_triangles']} per object)"))
    tot = sum(per.values())
    if tot > B["triangles"] and not isinstance(L.get("terrain"), dict): I.append(dict(kind="triangle_budget", severity="warning", message=f"{tot} triangles (> budget {B['triangles']})"))
    return dict(triangles=tot, nodes=len(per), materials=len(L.get("materials", {})), heaviest=sorted(per.items(), key=lambda x: -x[1])[:5])


def performance(d, L, G, I):
    B = G["budgets"]; bs = L.get("build_stats", {}); P = dict(dev=dict(glb_kb=bs.get("glb_kb"), triangles=bs.get("triangles"), draw_calls=bs.get("draw_calls_unbatched"),
                                                                       tex_mem_gpu_mb_est=bs.get("tex_mem_gpu_compressed_mb")))
    mp = os.path.join(d, "mobile", "mobile_manifest.json")
    if os.path.exists(mp):
        M = json.load(open(mp))["metrics"]; m = M["mobile"]; P["mobile"] = dict(profile=M.get("profile"), glb_kb=m["level"]["glb_kb"], triangles=m["level"]["triangles"],
                                                                             draw_calls=m["level"]["draw_calls_unbatched"], visible_draw_calls_est=m["visible"]["visible_draw_calls_mean"],
                                                                             visible_draw_calls_max_est=m["visible"].get("visible_draw_calls_max"), tex_mem_gpu_mb_est=m["level"].get("tex_mem_gpu_compressed_mb"),
                                                                             materials=m["level"].get("materials"), nodes=m["level"].get("nodes"), colliders=m.get("collision"),
                                                                             background_kb=m.get("background", {}).get("glb_kb") if isinstance(m.get("background"), dict) else None)
        world = isinstance(L.get("terrain"), dict)
        if world:  # Stage 9: LODs + view distances -> budgets on what the camera sees (estimates), plus the file size
            WB = dict(B, **{k: v for k, v in G.get("world_budgets", {}).items() if k != "note"}); B = WB
            P["mobile"]["visible_triangles_est"] = m["visible"].get("visible_triangles_mean"); P["mobile"]["visible_triangles_max_est"] = m["visible"].get("visible_triangles_max")
            if m["visible"].get("visible_triangles_max", 0) > B["visible_triangles"]:
                I.append(dict(kind="mobile_visible_triangles", severity="warning", message=f"up to ~{m['visible']['visible_triangles_max']} visible triangles (estimate, > {B['visible_triangles']})"))
        if m["level"]["glb_kb"] > B["mobile_glb_kb"]: I.append(dict(kind="mobile_size", severity="warning", message=f"mobile GLB {m['level']['glb_kb']} KB (> {B['mobile_glb_kb']})"))
        if m["level"]["draw_calls_unbatched"] > B["mobile_draw_calls"] and not world: I.append(dict(kind="mobile_draw_calls", severity="warning", message=f"mobile draw calls {m['level']['draw_calls_unbatched']} (> {B['mobile_draw_calls']})"))
        if m["visible"]["visible_draw_calls_mean"] > B["mobile_visible_draw_calls"]: I.append(dict(kind="mobile_visible_draw_calls", severity="warning", message=f"~{m['visible']['visible_draw_calls_mean']:.0f} visible draw calls (estimate, > {B['mobile_visible_draw_calls']})"))
        tm = m["level"].get("tex_mem_gpu_compressed_mb") or 0
        if tm > B["texture_mem_compressed_mb"]: I.append(dict(kind="texture_memory", severity="warning", message=f"~{tm} MB GPU texture memory (estimate, > {B['texture_mem_compressed_mb']})"))
    if (bs.get("glb_kb") or 0) > B["glb_kb"]: I.append(dict(kind="dev_size", severity="info", message=f"dev GLB {bs['glb_kb']} KB (> {B['glb_kb']})"))
    fx = os.path.join(d, "effects.json")
    if os.path.exists(fx):
        tot = json.load(open(fx)).get("totals", {}).get(L.get("mobile", {}).get("profile", "balanced"), {})
        P["effects"] = tot
        if tot.get("max_particles", 0) > B["particles"]: I.append(dict(kind="particle_budget", severity="warning", message=f"{tot['max_particles']} particles (> {B['particles']})"))
    P["note"] = "sizes/counts measured from files; visible draw calls and GPU memory are ESTIMATES (no device benchmark)"
    return P


def run(d, fast=False, verbose=True):
    from gameplay import load_gameplay, analyse
    L = json.load(open(os.path.join(d, "level.json"))); G = load_gameplay(d, L); I = []; R = dict(level=os.path.basename(os.path.normpath(d)))
    wp = schema(L, I); R["assets_kb"] = assets(d, L, I)
    if not any(i["kind"] in ("missing_asset", "broken_asset") and i["object"] == "level.glb" for i in I):
        R["complexity"] = complexity(d, L, G, I, wp); R["performance"] = performance(d, L, G, I)
        N = analyse(d, G, verbose=False); I += N["issues"]
        import geometry_check  # Stage 8: physical coherence (connections, supports, outlets, liquids, overlaps, openings, collision)
        GR = geometry_check.run(d, verbose=False); R["geometry"] = dict(counts=GR["counts"], relations=GR["relations"], repairable=GR["repairable"], passed=GR["passed"])
        for f in GR["findings"]:
            if f["cls"] == "INTENTIONAL" or f["check"] == "spawn": continue
            I.append(dict(kind="geo_" + f["check"], severity="error" if f["cls"] == "ERROR" else "warning", object=(f["objects"] or [None])[0], pos=f["pos"],
                          message=f["message"] + (" [auto-repairable]" if f["repair"] and not f["ambiguous"] else "")))
        R["navigation"] = {k: N[k] for k in ("standable_area_m2", "reachable_area_m2", "components", "spawns", "intended_areas", "narrow_connectors", "passed")}
        if not fast:
            from validate_level import validate
            V = validate(d, verbose=False); R["camera"] = {k: V[k] for k in ("cameras", "rays", "void_rays", "back_face", "open_mesh", "camera_inside", "passed")}
            for n, c in list(V["back_face"].items())[:15]:
                I.append(dict(kind="back_face", severity="error", object=n, pos=wp.get(n.rsplit("_Top", 1)[0]), message=f"{n}: back face visible from {c} camera rays (missing/one-sided geometry)"))
            for n, c in list(V["open_mesh"].items())[:15]:
                I.append(dict(kind="open_mesh", severity="error", object=n, pos=wp.get(n), message=f"{n}: {c} open edges visible (unfinished mesh)"))
            if V["void_rays"]:
                ex = V["void_examples"][0]["camera"] if V.get("void_examples") else None
                I.append(dict(kind="void", severity="error", pos=ex, message=f"{V['void_rays']} camera rays below the horizon see empty space (world edge visible)"))
            if V["camera_inside"]: I.append(dict(kind="camera_clipping", severity="info", message=f"{V['camera_inside']} of {V['cameras']} camera positions end inside geometry (spring arm against walls)"))
        elif os.path.exists(os.path.join(d, "checks", "validation.json")):
            R["camera"] = dict(json.load(open(os.path.join(d, "checks", "validation.json"))), stale_note="from the last full run (--fast skipped it)")
    rp = os.path.join(d, "checks", "render.json")
    if os.path.exists(rp):
        Rr = json.load(open(rp)); R["render"] = Rr
        for e in Rr.get("errors", []): I.append(dict(kind="render_error", severity="error", message=f"preview page error: {e}"))
    I.sort(key=lambda i: (SEV[i["severity"]], i["kind"]))
    R["issues"] = I; R["counts"] = {s: sum(i["severity"] == s for i in I) for s in SEV}; R["passed"] = R["counts"]["error"] == 0
    R["gameplay_config"] = G.get("status", "")
    os.makedirs(os.path.join(d, "checks"), exist_ok=True); json.dump(R, open(os.path.join(d, "checks", "report.json"), "w"), indent=1)
    open(os.path.join(d, "checks", "report.md"), "w").write(markdown(R))
    if verbose: print(json.dumps(dict(passed=R["passed"], counts=R["counts"], top=[i["message"] for i in I[:10]])))
    return R


def markdown(R):
    P = R.get("performance", {}); m = P.get("mobile", {}); dv = P.get("dev", {}); n = R.get("navigation", {}); c = R.get("camera", {})
    out = [f"# Checks: {R['level']} - {'PASSED' if R['passed'] else 'NOT PASSED'}", "",
           f"errors {R['counts']['error']} · warnings {R['counts']['warning']} · info {R['counts']['info']}", "",
           "| metric | dev | mobile |", "|---|---|---|",
           f"| file KB | {dv.get('glb_kb')} | {m.get('glb_kb')} |", f"| triangles | {dv.get('triangles')} | {m.get('triangles')} |",
           f"| draw calls (measured) | {dv.get('draw_calls')} | {m.get('draw_calls')} |", f"| visible draw calls (estimate) | - | {m.get('visible_draw_calls_est')} |",
           f"| GPU texture MB (estimate) | {dv.get('tex_mem_gpu_mb_est')} | {m.get('tex_mem_gpu_mb_est')} |", "",
           f"Navigation: reachable {n.get('reachable_area_m2')} of {n.get('standable_area_m2')} m² standable; components {n.get('components')}.",
           f"Camera: {c.get('cameras', '-')} cameras, void rays {c.get('void_rays', '-')}, back faces {len(c.get('back_face', {})) if c else '-'}.",
           f"Geometry: {R.get('geometry', {}).get('counts')} (checks/geometry.md)", "", "## Issues (highest impact first)"]
    out += [f"- **{i['severity']}** {i['message']}" for i in R["issues"][:40]] or ["- none"]
    out += ["", "Estimates are not device benchmarks; renders are the browser preview, not Godot."]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    R = run(sys.argv[1], fast="--fast" in sys.argv); sys.exit(0 if R["passed"] else 1)
