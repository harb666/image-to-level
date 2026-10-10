"""Stage 7: the SCENE SPEC - the explicit, reproducible hand-off from Claude's reading of the concept image(s) to the
deterministic CPU builder.  Format reference: SCENE_SPEC.md.   python3 pipeline/scene_spec.py <scene_spec.json>  (validate)

Claude writes levels/<name>/scene_spec.json (what it sees: layout, heights, structures, materials, atmosphere; every
element tagged "source": "visible" | "inferred"); spec_to_level.py turns it into level.json. Validation here is strict
about structure (types, required keys, references between elements, plausible numbers) and returns readable errors with
JSON paths; unknown keys are warnings (typos) so the format can grow.
Coordinates: metres, y up, x = east, z = SOUTH (north = -z), arena centre usually [0, 0].
"""
import json, sys

NUM, INT, STR, BOOL, LIST, DICT = (int, float), int, str, bool, list, dict
V2, V3 = ("vec", 2), ("vec", 3)

ELEMENT = {"source": (STR, False, ("visible", "inferred"))}
SCHEMA = {
    "spec_version": (INT, True), "name": (STR, True), "title": (STR, False), "theme": (STR, False), "detail": (STR, False, ("low", "medium", "high")),
    "seed": (INT, False), "profile": (STR, False, ("performance", "balanced", "quality")),
    "references": (LIST, False, {"file": (STR, True), "kind": (STR, False, ("concept_sheet", "perspective", "top_down", "elevation", "detail", "photo")),
                                 "panels": (LIST, False, {"id": (STR, True), "bbox_px": (("vec", 4), False), "view": (STR, True, ("top_down", "elevation", "perspective", "detail", "text")),
                                                          "use": (LIST, False), "notes": (STR, False)}), "notes": (STR, False)}),
    "interpretation": (DICT, False, {"summary": (STR, False), "visible": (LIST, False), "inferred": (LIST, False), "assumptions": (LIST, False),
                                     "scale_basis": (STR, False), "questions": (LIST, False)}),
    "arena": (DICT, True, {"shape": (STR, False, ("rect", "octagon", "circle")), "size": (V2, True), "center": (V2, False), "source": (STR, False),
                           "floor": (DICT, True, {"kind": (STR, True, ("hazard", "ground", "deck")), "y": (NUM, True), "material": (STR, False), "name": (STR, False), "source": (STR, False)}),
                           "walls": (DICT, False, {"height": (NUM, True), "thickness": (NUM, False), "style": (STR, False, ("auto", "industrial", "stone", "none")), "source": (STR, False),
                                                   "openings": (LIST, False, {"side": (STR, True, ("north", "south", "east", "west")), "at": (NUM, False), "width": (NUM, True), "height": (NUM, False)})}),
                           "walkway": (DICT, False, {"width": (NUM, False), "y": (NUM, True), "style": (STR, False), "source": (STR, False)}),
                           "boundary": (STR, False, ("walls", "invisible"))}),
    "platforms": (LIST, False, dict(ELEMENT, id=(STR, True), shape=(STR, False, ("rect", "octagon", "circle")), center=(V2, True), size=(V2, True),
                                    top=(NUM, True), style=(STR, False, ("industrial_pillar", "stone_plinth", "plain")), cover=(INT, False), lights=(BOOL, False),
                                    material=(STR, False), unreachable_ok=(BOOL, False), notes=(STR, False))),
    "connections": (LIST, False, dict(ELEMENT, id=(STR, True), **{"from": (STR, True)}, to=(STR, True), kind=(STR, False, ("auto", "bridge", "catwalk", "ramp", "stairs", "jump")),
                                      width=(NUM, False), rails=(BOOL, False), notes=(STR, False))),
    "structures": (LIST, False, dict(ELEMENT, id=(STR, True), kind=(STR, True, None), on=(STR, False), offset=(V2, False), position=(LIST, False), yaw=(NUM, False),
                                     facing=(STR, False, ("center", "north", "south", "east", "west")), size=(V3, False), style=(STR, False), roof=(STR, False),
                                     floors=(INT, False), decor=(LIST, False), round=(BOOL, False), opening=(NUM, False), count=(INT, False), radius=(NUM, False),
                                     lit=(BOOL, False), chimney=(BOOL, False), roof_height=(NUM, False), material=(STR, False), height=(NUM, False), thickness=(NUM, False),
                                     to=(V2, False), inner=(V2, False), notes=(STR, False), **{"from": (V2, False)})),
    "pipes": (LIST, False, dict(ELEMENT, id=(STR, True), kind=(STR, False, ("outlet", "run")), wall=(STR, False, ("north", "south", "east", "west", "ne", "nw", "se", "sw")),
                                at=(NUM, False), position=(LIST, False), yaw=(NUM, False), y=(NUM, False), radius=(NUM, False), length=(NUM, False), pour=(BOOL, False),
                                pour_material=(STR, False), points=(LIST, False), notes=(STR, False), width=(NUM, False),
                                outlet=(STR, False, ("circle", "drain", "spillway", "vertical", "broken")))),
    "terrain": (LIST, False, dict(ELEMENT, id=(STR, True), area=(("vec", 4), True), height=(V2, False), cell=(NUM, False), seed=(INT, False),
                                  material=(STR, False), top_material=(STR, False), walkable=(BOOL, False), notes=(STR, False))),
    "hazards": (LIST, False, dict(ELEMENT, id=(STR, True), area=(("vec", 4), True), y=(NUM, True), material=(STR, False))),
    "materials": (DICT, False, {"variation": (BOOL, False), "roles": (DICT, False)}),
    "atmosphere": (DICT, False, {"sky": (STR, False), "sky_overrides": (DICT, False), "fog_start": (NUM, False), "fog_end": (NUM, False), "height_fog": (DICT, False),
                                 "glow_color": (("vec", 3), False), "ambient": (STR, False, ("spores", "dust", "embers", "snow", "none")), "source": (STR, False)}),
    "background": (DICT, False, {"mountains": (STR, False, ("both", "far", "near", "none")), "mountain_height": (V2, False), "factories": (INT, False),
                                 "skyline": (BOOL, False), "spires": (BOOL, False), "town": (BOOL, False), "ground_type": (STR, False),
                                 "ground_color": (("vec", 3), False), "layers": (LIST, False), "source": (STR, False)}),
    "effects": ((STR, LIST, DICT), False),
    "spawns": (LIST, False, {"id": (STR, False), "on": (STR, False), "position": (V3, False), "yaw": (NUM, False)}),
    "gameplay": (DICT, False), "refine": (DICT, False, {"max_passes": (INT, False)}), "notes": (STR, False),
}


def _type_ok(v, t):
    if isinstance(t, tuple) and t and t[0] == "vec":
        return isinstance(v, list) and len(v) == t[1] and all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in v)
    if t is BOOL: return isinstance(v, bool)
    if t in (NUM, INT) or t == (int, float): return isinstance(v, t) and not isinstance(v, bool)
    if isinstance(t, tuple) and all(isinstance(x, type) for x in t): return isinstance(v, t)
    return isinstance(v, t)


def _tname(t):
    if isinstance(t, tuple) and t and t[0] == "vec": return f"[{t[1]} numbers]"
    if t == NUM: return "number"
    if isinstance(t, tuple): return " or ".join(x.__name__ for x in t)
    return t.__name__


def _check(obj, schema, path, E, W):
    for k, v in obj.items():
        if k.startswith("_"): continue
        if k not in schema: W.append(f"{path}.{k}: unknown key (ignored) - typo?"); continue
        spec = schema[k]; t = spec[0]
        if not _type_ok(v, t): E.append(f"{path}.{k}: expected {_tname(t)}, got {json.dumps(v)[:60]}"); continue
        if len(spec) > 2 and spec[2] is not None:
            sub = spec[2]
            if isinstance(sub, tuple) and isinstance(v, str) and v not in sub: E.append(f"{path}.{k}: '{v}' not one of {list(sub)}")
            elif isinstance(sub, dict):
                if isinstance(v, dict): _check(v, sub, f"{path}.{k}", E, W); _req(v, sub, f"{path}.{k}", E)
                elif isinstance(v, list):
                    for i, it in enumerate(v):
                        if not isinstance(it, dict): E.append(f"{path}.{k}[{i}]: expected an object"); continue
                        _check(it, sub, f"{path}.{k}[{i}]", E, W); _req(it, sub, f"{path}.{k}[{i}]", E)


def _req(obj, schema, path, E):
    for k, spec in schema.items():
        if spec[1] and k not in obj: E.append(f"{path}: missing required '{k}'")


def validate(spec):
    """Returns (errors, warnings). Structural + cross-reference + plausibility checks."""
    from architecture import STRUCTURES, THEMES
    E, W = [], []
    if not isinstance(spec, dict): return ["spec must be a JSON object"], []
    _check(spec, SCHEMA, "spec", E, W); _req(spec, SCHEMA, "spec", E)
    if E: return E, W
    if spec.get("theme", "industrial") not in THEMES: E.append(f"spec.theme: '{spec['theme']}' not one of {list(THEMES)}")
    ids = {}
    for sec in ("platforms", "connections", "structures", "pipes", "hazards", "terrain"):
        for i, it in enumerate(spec.get(sec, [])):
            if it["id"] in ids: E.append(f"spec.{sec}[{i}].id: '{it['id']}' already used by {ids[it['id']]}")
            ids[it["id"]] = f"{sec}[{i}]"
            if not it["id"].replace("_", "").isalnum(): E.append(f"spec.{sec}[{i}].id: '{it['id']}' - use letters, digits and _ only (stable object names)")
    plats = {p["id"]: p for p in spec.get("platforms", [])}; A = spec["arena"]; hw, hd = A["size"][0] / 2, A["size"][1] / 2
    cx, cz = A.get("center", [0, 0])
    if min(A["size"]) <= 0: E.append("spec.arena.size: must be positive")
    for i, p in enumerate(spec.get("platforms", [])):
        if min(p["size"]) <= 0.5: E.append(f"spec.platforms[{i}].size: too small ({p['size']})")
        if p["top"] <= A["floor"]["y"] - 0.01 and A["floor"]["kind"] != "hazard": W.append(f"spec.platforms[{i}].top: at/below the arena floor")
        if abs(p["center"][0] - cx) > hw + 1 or abs(p["center"][1] - cz) > hd + 1: W.append(f"spec.platforms[{i}]: centre outside the arena")
        if p["top"] > 60: W.append(f"spec.platforms[{i}].top: {p['top']} m is very high - metres?")
    for i, c in enumerate(spec.get("connections", [])):
        for k in ("from", "to"):
            if c[k] not in plats: E.append(f"spec.connections[{i}].{k}: unknown platform '{c[k]}' (known: {sorted(plats)[:12]})")
        if c["from"] == c["to"]: E.append(f"spec.connections[{i}]: connects a platform to itself")
    for i, s in enumerate(spec.get("structures", [])):
        if s["kind"] not in STRUCTURES: E.append(f"spec.structures[{i}].kind: '{s['kind']}' not one of {sorted(STRUCTURES)} (extend architecture.py for new kinds)")
        if s.get("on") and s["on"] not in plats: E.append(f"spec.structures[{i}].on: unknown platform '{s['on']}'")
        if s["kind"] == "wall":
            if "from" not in s or "to" not in s: E.append(f"spec.structures[{i}]: kind 'wall' needs 'from' and 'to' [x, z]")
        elif not s.get("on") and not s.get("position"): E.append(f"spec.structures[{i}]: needs 'on' (platform id) or 'position' [x, z] / [x, y, z]")
        if s.get("position") is not None and not (isinstance(s["position"], list) and len(s["position"]) in (2, 3)): E.append(f"spec.structures[{i}].position: [x, z] or [x, y, z]")
        if s["kind"] in ("tower", "building", "house", "stone_tower", "gate", "arch") and "size" not in s: E.append(f"spec.structures[{i}]: kind '{s['kind']}' needs size [w, h, d]")
        if s.get("size") and min(s["size"]) <= 0: E.append(f"spec.structures[{i}].size: must be positive")
    for i, p in enumerate(spec.get("pipes", [])):
        if p.get("kind", "outlet") == "run":
            if not p.get("points") or len(p["points"]) < 2: E.append(f"spec.pipes[{i}]: kind 'run' needs >= 2 points [x, y, z]")
        elif not p.get("wall") and not p.get("position"): E.append(f"spec.pipes[{i}]: outlet needs 'wall' (+ 'at') or 'position' + 'yaw'")
    for i, s in enumerate(spec.get("spawns", [])):
        if s.get("on") and s["on"] not in plats: E.append(f"spec.spawns[{i}].on: unknown platform '{s['on']}'")
        if not s.get("on") and not s.get("position"): E.append(f"spec.spawns[{i}]: needs 'on' or 'position'")
    if isinstance(spec.get("effects"), str) and spec["effects"] not in ("auto", "none"): E.append("spec.effects: 'auto', 'none', a list of Stage 4 effects or {auto, extra, disable}")
    sky = spec.get("atmosphere", {}).get("sky")
    if sky:
        from sky import PRESETS
        if sky not in PRESETS: E.append(f"spec.atmosphere.sky: '{sky}' not one of {list(PRESETS)}")
    for k in ("visible", "inferred"):
        if not spec.get("interpretation", {}).get(k): W.append(f"spec.interpretation.{k}: empty - record what was seen vs inferred")
    return E, W


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1])); E, W = validate(spec)
    for w in W: print("warning:", w)
    for e in E: print("ERROR:", e)
    print("valid" if not E else f"{len(E)} error(s)"); sys.exit(1 if E else 0)
