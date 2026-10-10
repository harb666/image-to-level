"""Stage 7: Construct Error / Godot 4 export package + package validation.

  python3 pipeline/package.py levels/<name> [--zip]     -> dist/<name>/package/levels/<name>/ (+ dist/<name>/<name>.zip)
                                                          and levels/<name>/level_manifest.json
  python3 pipeline/package.py --check dist/<name>/package   validate an existing package

The package mirrors the Godot project layout: copy its "levels/<name>/" folder to res://levels/<name>/ (the paths
inside environment.tres and the scripts assume that). Contents:
  level.json (editable master)  level.glb (dev, one node per object)  mobile/ (level_mobile.glb, background_mobile.glb,
  collision.json/.glb, effects_mobile.json, mobile_manifest.json, apply_mobile.gd)  background.glb + sky/panorama.jpg
  environment.json + environment.tres  effects.json + fx/ (sprites + godot shaders/scripts)  gameplay/spawns.json,
  gameplay/hazards.json, gameplay/navigation.json  level_manifest.json (every file + sha1 + purpose, metrics,
  validation)  IMPORT_GODOT.md  checks/report.md
Validation: every manifest file exists with the recorded sha1; JSON parses; GLBs are glTF 2.0 with valid buffers;
environment.tres references resolve inside the package; effect targets and hazards name real nodes; spawns lie inside the
level bounds. Standard formats only (glTF 2.0 .glb, JPEG/PNG, JSON, Godot .tres/.gd/.gdshader text resources).
"""
import hashlib, json, os, re, shutil, sys, time, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
PURPOSE = {"level.json": "editable master (source of truth for edits)", "level.glb": "dev export: one node per named object",
           "background.glb": "distant scenery (no collision)", "sky/panorama.jpg": "2:1 equirect sky -> PanoramaSkyMaterial",
           "environment.json": "engine-neutral lighting / fog / sky metadata", "environment.tres": "Godot 4 Environment resource (UNTESTED in Godot here)",
           "effects.json": "runtime effects metadata (Godot recreates them)", "mobile/level_mobile.glb": "mobile export: merged by cell+material (use in game)",
           "mobile/background_mobile.glb": "mobile background", "mobile/collision.json": "primitive colliders + hazard areas",
           "mobile/collision.glb": "collision meshes (-colonly / -convcolonly import suffixes)", "mobile/effects_mobile.json": "effects with merged-node targets",
           "mobile/mobile_manifest.json": "per-node visibility/shadows + Godot import settings + metrics", "mobile/apply_mobile.gd": "Godot starter: visibility ranges, shadows, hazard Area3Ds",
           "gameplay/spawns.json": "player spawns (position, yaw)", "gameplay/hazards.json": "hazard volumes (kill / damage areas)",
           "gameplay/navigation.json": "reachability summary from the gameplay config (not a navmesh)", "IMPORT_GODOT.md": "how to import into Construct Error",
           "checks/report.md": "validation report", "scene_spec.json": "Claude's interpretation of the reference images (regenerate input)",
           "terrain.json": "Stage 9 terrain metadata: chunks + hashes, LOD ranges, features, layers, water, scatter instances (derived)",
           "props/props.glb": "Stage 9 scatter variant meshes (unit transforms) for optional MultiMesh instancing",
           "mobile/apply_scatter_multimesh.gd": "OPTIONAL Godot script: MultiMesh scatter from terrain.json (UNTESTED in Godot here)"}


def sha1(p): return hashlib.sha1(open(p, "rb").read()).hexdigest()


def build(level_dir, out_root=None, make_zip=False, verbose=True):
    L = json.load(open(os.path.join(level_dir, "level.json"))); name = os.path.basename(os.path.normpath(level_dir))
    out_root = out_root or os.path.join(ROOT, "dist", name, "package"); dst = os.path.join(out_root, "levels", name)
    shutil.rmtree(out_root, ignore_errors=True); os.makedirs(dst)
    files = ["level.json", "level.glb", "background.glb", "environment.json", "environment.tres", "effects.json", "scene_spec.json", "terrain.json", "props/props.glb"]
    files += [os.path.join("sky", f) for f in ("panorama.jpg",) if os.path.exists(os.path.join(level_dir, "sky", f))]
    files += [os.path.join("mobile", f) for f in sorted(os.listdir(os.path.join(level_dir, "mobile")))] if os.path.isdir(os.path.join(level_dir, "mobile")) else []
    if os.path.isdir(os.path.join(level_dir, "fx")):
        for r, _, fs in os.walk(os.path.join(level_dir, "fx")): files += [os.path.relpath(os.path.join(r, f), level_dir) for f in sorted(fs)]
    files += [f for f in ("checks/report.md",) if os.path.exists(os.path.join(level_dir, f))]
    for f in files:
        s = os.path.join(level_dir, f)
        if os.path.exists(s): os.makedirs(os.path.dirname(os.path.join(dst, f)), exist_ok=True); shutil.copy2(s, os.path.join(dst, f))
    tres = os.path.join(dst, "environment.tres")  # res:// paths must match the package folder name
    if os.path.exists(tres): open(tres, "w").write(re.sub(r"res://levels/[^/]+/", f"res://levels/{name}/", open(tres).read()))
    gp = os.path.join(dst, "gameplay"); os.makedirs(gp)
    spawns = [dict(id="spawn", **L["spawn"])] + L.get("spawns", [])
    json.dump(dict(note="Positions in metres (Godot: y up, -z forward). yaw_deg rotates the player about +y. Stage 9: 'team' player / enemy; "
                        "spawn_regions = the regions the points were chosen in (safe, flat, dry, clear).", spawns=spawns,
                   spawn_regions=L.get("spawn_regions", [])), open(os.path.join(gp, "spawns.json"), "w"), indent=1)
    col = json.load(open(os.path.join(level_dir, "mobile", "collision.json"))) if os.path.exists(os.path.join(level_dir, "mobile", "collision.json")) else {}
    json.dump(dict(note="Hazard volumes: box areas in world space (Area3D). The game decides damage / kill / respawn.", hazards=col.get("hazards", []), names=L.get("hazards", [])),
              open(os.path.join(gp, "hazards.json"), "w"), indent=1)
    nav_p = os.path.join(level_dir, "checks", "navigation.json")
    if os.path.exists(nav_p):
        N = json.load(open(nav_p)); json.dump({k: N[k] for k in ("gameplay_status", "standable_area_m2", "reachable_area_m2", "spawns", "intended_areas", "links", "passed") if k in N},
                                             open(os.path.join(gp, "navigation.json"), "w"), indent=1)
    open(os.path.join(dst, "IMPORT_GODOT.md"), "w").write(open(os.path.join(ROOT, "GODOT_IMPORT.md")).read().replace("<name>", name))
    rep = json.load(open(os.path.join(level_dir, "checks", "report.json"))) if os.path.exists(os.path.join(level_dir, "checks", "report.json")) else {}
    entries = []
    for r, _, fs in os.walk(dst):
        for f in sorted(fs):
            p = os.path.join(r, f); rel = os.path.relpath(p, dst).replace(os.sep, "/")
            if rel == "level_manifest.json": continue
            entries.append(dict(path=rel, bytes=os.path.getsize(p), sha1=sha1(p), purpose=PURPOSE.get(rel, "effect sprite / Godot effect kit" if rel.startswith("fx/") else "")))
    M = dict(format="image-to-level package v1", level=name, title=L.get("source", name), generated=time.strftime("%Y-%m-%d %H:%M:%S"),
             godot_root=f"res://levels/{name}/", use_in_game="mobile/level_mobile.glb (+ mobile/background_mobile.glb, mobile/collision.glb)",
             profile=L.get("mobile", {}).get("profile", "balanced"), spawns=spawns, hazards=L.get("hazards", []),
             generator=L.get("generator"), metrics=rep.get("performance"), validation=dict(passed=rep.get("passed"), counts=rep.get("counts")),
             gameplay_config_status=rep.get("gameplay_config"), files=entries,
             notes=["GLB carries static geometry/materials only; effects, environment and hazards are recreated in Godot from the JSON/tres + scripts.",
                    "Scripts and .tres are UNTESTED in Godot from this environment.", "Performance numbers are estimates, not device benchmarks."])
    json.dump(M, open(os.path.join(dst, "level_manifest.json"), "w"), indent=1)
    json.dump({k: v for k, v in M.items() if k != "files"} | {"files": len(entries)}, open(os.path.join(level_dir, "level_manifest.json"), "w"), indent=1)
    errs = check(out_root, verbose=False)
    z = None
    if make_zip:
        z = os.path.join(os.path.dirname(out_root), f"{name}.zip") if os.path.basename(out_root) == "package" else out_root + ".zip"
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            for r, _, fs in os.walk(out_root):
                for f in fs: zf.write(os.path.join(r, f), os.path.relpath(os.path.join(r, f), out_root))
    res = dict(package=out_root, files=len(entries), mb=round(sum(e["bytes"] for e in entries) / 1e6, 2), zip=z, valid=not errs, errors=errs)
    if verbose: print(json.dumps(res))
    return res


def check(pkg_root, verbose=True):
    from glb_tools import _read
    errs = []; lv = os.path.join(pkg_root, "levels"); names = os.listdir(lv) if os.path.isdir(lv) else []
    if len(names) != 1: return [f"expected one levels/<name>/ folder in {pkg_root}, found {names}"]
    name = names[0]; d = os.path.join(lv, name); mp = os.path.join(d, "level_manifest.json")
    if not os.path.exists(mp): return ["level_manifest.json missing"]
    M = json.load(open(mp))
    for e in M["files"]:
        p = os.path.join(d, e["path"])
        if not os.path.exists(p): errs.append(f"missing {e['path']}"); continue
        if sha1(p) != e["sha1"]: errs.append(f"checksum mismatch {e['path']}")
        try:
            if p.endswith(".json"): json.load(open(p))
            elif p.endswith(".glb"):
                g, b = _read(p); assert g["asset"]["version"] == "2.0"
                for bv in g.get("bufferViews", []): assert bv.get("byteOffset", 0) + bv["byteLength"] <= len(b)
        except Exception as ex: errs.append(f"{e['path']} does not parse: {ex}")
    for need in ("level.json", "level.glb", "mobile/level_mobile.glb", "mobile/collision.json", "gameplay/spawns.json", "IMPORT_GODOT.md"):
        if not os.path.exists(os.path.join(d, need)): errs.append(f"required file missing: {need}")
    tres = os.path.join(d, "environment.tres")
    if os.path.exists(tres):
        for ref in re.findall(r'path="(res://[^"]+)"', open(tres).read()):
            rel = ref.replace(f"res://levels/{name}/", "")
            if ref.startswith(f"res://levels/{name}/") and not os.path.exists(os.path.join(d, rel)): errs.append(f"environment.tres references missing {ref}")
            if not ref.startswith(f"res://levels/{name}/"): errs.append(f"environment.tres references outside the package: {ref}")
    if os.path.exists(os.path.join(d, "mobile", "level_mobile.glb")):
        g, _ = _read(os.path.join(d, "mobile", "level_mobile.glb")); nodes = {n.get("name") for n in g["nodes"]}
        fx = os.path.join(d, "mobile", "effects_mobile.json")
        if os.path.exists(fx):
            for e in json.load(open(fx)).get("effects", []):
                for t in e.get("targets", []):
                    if t not in nodes: errs.append(f"effect {e['id']} target {t} not a node of level_mobile.glb")
        col = json.load(open(os.path.join(d, "mobile", "collision.json")))
        if not col.get("colliders"): errs.append("collision.json has no colliders")
        if "PlayerSpawn" not in nodes: errs.append("level_mobile.glb has no PlayerSpawn node")
    L = json.load(open(os.path.join(d, "level.json"))); b0, b1 = L["bounds"]["min"], L["bounds"]["max"]
    for s in json.load(open(os.path.join(d, "gameplay", "spawns.json")))["spawns"]:
        p = s["position"]
        if not (b0[0] - 1 <= p[0] <= b1[0] + 1 and b0[2] - 1 <= p[2] <= b1[2] + 1): errs.append(f"spawn {s.get('id')} {p} outside the level bounds")
    if verbose: print(json.dumps(dict(package=pkg_root, valid=not errs, errors=errs)))
    return errs


if __name__ == "__main__":
    if sys.argv[1] == "--check": sys.exit(1 if check(sys.argv[2]) else 0)
    r = build(sys.argv[1], make_zip="--zip" in sys.argv); sys.exit(0 if r["valid"] else 1)
