"""Stage 7: bounded generate -> validate -> fix loop (no endless regeneration).

  python3 pipeline/refine.py levels/<name> [--max-passes N] [--no-render]

Each pass: build -> checks.py (schema, assets, complexity, performance, navigation, camera) -> pick the highest-impact
problems -> apply only SAFE, TARGETED automatic fixes -> rebuild. Stops when there are no errors, when no automatic fix
applies, or after max passes (default: scene_spec "refine.max_passes", else 3). Then renders the review views.
Automatic fixes (each is an ordinary level.json edit, undoable with edit_level.py undo):
  back_face / void          validate_level.fix: double-sided flag / background ground skirt (never touches walkable space)
  spawn_* (unsafe spawn)    move the spawn to the roomiest safe standable point of the main area (navigation candidates)
  unreachable_platform      connect it to the nearest reachable walkable area (edit_level.connect: bridge/ramp/stairs)
  duplicate_object          remove the exact duplicate
  missing / broken asset    rebuild
  geometry (Stage 8)        geometry_repair.py: extend short/overhanging connectors, fix ramp/stair elevations, liquid
                            from the real pipe opening, streams into pools, pipes back into walls, z-fight nudges
Everything else (art direction, narrow bridges, budgets, visual accuracy against the reference) is listed under
"needs_claude" in checks/refine_log.json: those need judgement and the rendered views, not a blind rule.
"""
import json, math, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))


def _build(d):
    subprocess.run([sys.executable, os.path.join(HERE, "build_level.py"), d], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def auto_fix(d, R):
    import edit_level as E
    from validate_level import fix as vfix
    log0 = []
    if any(i["kind"].startswith("geo_") and "[auto-repairable]" in i["message"] for i in R["issues"]):  # Stage 8 geometry repairs first
        import geometry_repair
        rep = geometry_repair.repair(d, max_passes=3, verbose=False); log0 = [f"geometry: {x['object']}: {x['result']}" for x in rep["repairs"] if x.get("object")]
    lp = os.path.join(d, "level.json"); L = json.load(open(lp)); before = json.loads(json.dumps(L)); log = list(log0)
    kinds = {i["kind"] for i in R["issues"] if i["severity"] == "error"} | {i["kind"] for i in R["issues"] if i["kind"].startswith("spawn_")}
    cam = R.get("camera") or {}
    if ("back_face" in kinds or "void" in kinds) and cam:
        vr = dict(back_face=cam.get("back_face", {}), void_rays=cam.get("void_rays", 0))
        log += [f"camera: {x}" for x in vfix(d, vr)]; L = json.load(open(lp))
    if any(k.startswith("spawn_") for k in kinds):
        from gameplay import analyse
        N = analyse(d, verbose=False, write=False); bad = {i["object"] for i in N["issues"] if i["kind"].startswith("spawn_") and i["severity"] in ("error", "warning")}
        cands = N.get("spawn_candidates", [])
        if "spawn" in bad and cands:
            old = L["spawn"]["position"]; c = min(cands[:3], key=lambda p: math.hypot(p[0] - old[0], p[2] - old[2]))  # safe AND close to the intended spot
            L["spawn"]["position"] = c; log.append(f"spawn moved {old} -> {c} (clearance/hazard distance)")
        for s in L.get("spawns", []):
            if s.get("id") in bad and cands:
                used = [L["spawn"]["position"]] + [x["position"] for x in L["spawns"] if x is not s]
                c = max(cands, key=lambda p: min(math.hypot(p[0] - u[0], p[2] - u[2]) for u in used)); log.append(f"{s['id']} moved {s['position']} -> {c}"); s["position"] = c
    json.dump(L, open(lp, "w"), indent=1)
    unreach = [i["object"] for i in R["issues"] if i["kind"] == "unreachable_platform"]
    if unreach:
        nav = json.load(open(os.path.join(d, "checks", "navigation.json")))
        ok = [a["name"] for a in nav["intended_areas"] if a["reachable_fraction"] >= 0.5]
        for name in unreach[:3]:
            try:
                pa = E._area(L, name); best = min(ok, key=lambda n: _gap(pa, E._area(L, n))) if ok else None
                if best:
                    added = E.connect(L, best, name); log.append(f"connected {best} -> {name}: {added[:4]}"); ok.append(name)
            except SystemExit as e: log.append(f"could not connect {name}: {e}")
        if E._schema_errors(L): L = json.load(open(lp)); log.append("connection refused by schema check")
        json.dump(L, open(lp, "w"), indent=1)
    dups = [i["object"] for i in R["issues"] if i["kind"] == "duplicate_object"]
    if dups:
        L = json.load(open(lp)); L["objects"] = [o for o in L["objects"] if o["name"] not in set(dups)]; json.dump(L, open(lp, "w"), indent=1); log.append(f"removed duplicates {dups[:6]}")
    if any(i["kind"] in ("missing_asset", "broken_asset") for i in R["issues"]): log.append("rebuild (missing/broken asset)")
    if len(log) > len(log0): E.snapshot(d, before, "refine: " + "; ".join(log[len(log0):])[:200])
    return log


def _gap(a, b):
    dx = abs(a["center"][0] - b["center"][0]) - (a["size"][0] + b["size"][0]) / 2; dz = abs(a["center"][1] - b["center"][1]) - (a["size"][1] + b["size"][1]) / 2
    return math.hypot(max(dx, 0), max(dz, 0)) + abs(a["top"] - b["top"]) * 2


def refine(d, max_passes=None, render=True, verbose=True):
    import checks
    spec_p = os.path.join(d, "scene_spec.json")
    if max_passes is None: max_passes = json.load(open(spec_p)).get("refine", {}).get("max_passes", 3) if os.path.exists(spec_p) else 3
    passes, t0 = [], time.time()
    if not os.path.exists(os.path.join(d, "level.glb")): _build(d)
    for k in range(1, max_passes + 1):
        R = checks.run(d, verbose=False); top = [i["message"] for i in R["issues"] if i["severity"] == "error"][:8]
        p = dict(n=k, errors=R["counts"]["error"], warnings=R["counts"]["warning"], top_errors=top)
        if verbose: print(f"pass {k}: {R['counts']}  " + (" | ".join(top[:3]) if top else "no errors"))
        fixable = any(i["kind"].startswith("geo_") and "[auto-repairable]" in i["message"] for i in R["issues"])
        if R["counts"]["error"] == 0 and not fixable and not any(i["kind"].startswith("spawn_") for i in R["issues"]): passes.append(p); break
        fixes = auto_fix(d, R); p["fixes"] = fixes; passes.append(p)
        if not fixes: p["stopped"] = "no automatic fix applies - remaining issues need Claude"; break
        if verbose: print("  fixes:", fixes)
        _build(d)
        if k == max_passes: R = checks.run(d, verbose=False); passes.append(dict(n="final", errors=R["counts"]["error"], warnings=R["counts"]["warning"]))
    if render:
        try:
            from render_views import render as rv
            rv(d)
            from render_views import inspect as rinspect  # Stage 8: close-ups of junctions, outlets, liquid impacts, third-person at junctions
            rinspect(d); R = checks.run(d, fast=True, verbose=False)  # fold page errors from the renders into the report
        except SystemExit as e: passes.append(dict(render_unavailable=str(e)))
    needs = [dict(severity=i["severity"], message=i["message"], object=i.get("object")) for i in R["issues"] if i["severity"] in ("error", "warning")][:30]
    log = dict(passes=passes, max_passes=max_passes, seconds=round(time.time() - t0, 1), passed=R["passed"], counts=R["counts"], needs_claude=needs,
               visual_review="checks/views/contact_sheet.jpg + checks/inspect/contact_sheet.jpg must be LOOKED AT by Claude and compared with the reference before calling the level done" if render else "renders skipped")
    json.dump(log, open(os.path.join(d, "checks", "refine_log.json"), "w"), indent=1)
    if verbose: print(json.dumps(dict(passed=log["passed"], counts=log["counts"], passes=len(passes), seconds=log["seconds"])))
    return log


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    mp = int(sys.argv[sys.argv.index("--max-passes") + 1]) if "--max-passes" in sys.argv else None
    if mp is not None: a = [x for x in a if x != str(mp)]
    refine(a[0], mp, render="--no-render" not in sys.argv)
