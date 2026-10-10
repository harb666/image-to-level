"""Stage 7: scene spec -> level.json (deterministic; the CPU half of image -> level).

  python3 pipeline/spec_to_level.py levels/<name>/scene_spec.json [--force] [--dry-run]

Reads Claude's scene_spec.json (see SCENE_SPEC.md), validates it (scene_spec.py), assembles named objects with the
architecture modules (architecture.py), assigns role materials from the theme palette (+ per-role overrides and shared
variants), adds environment (Stage 2 sky/background), effects (Stage 4, "auto" rules), spawns, walkable areas, bounds,
and writes levels/<name>/level.json + gen_state.json. Then build with build_level.py (or run generate.py for the whole
pipeline).

Re-generation keeps manual edits: gen_state.json stores a hash of everything the generator produced last time. On the
next run, an object/material/effect/environment entry that was EDITED since (hash differs) is kept as edited, one that
was DELETED stays deleted, MANUALLY ADDED ones are kept, untouched generated ones are replaced by the new generation.
An existing level.json without gen_state.json (hand-made level) is never overwritten unless --force.
Every regeneration snapshots the previous level.json into .history/ (edit_level.py undo restores it).
"""
import copy, hashlib, json, math, os, sys
import architecture as A
from scene_spec import validate
from gameplay import load_gameplay

H = lambda v: hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()[:16]
UNITS = "metres, y-up; position = centre of object's base, in parent space; rotation = degrees XYZ"


def generate(spec, G):
    ctx = A.Ctx(spec, G); ar = spec["arena"]; fy = ar["floor"]["y"]; centre = tuple(ar.get("center", [0, 0]))
    A.arena(ctx, ar, fy)
    for t in spec.get("terrain", []):
        ctx.element = (t["id"], t.get("source", "visible")); A.terrain(ctx, t, fy)
    base_y = 0.0 if ar["floor"]["kind"] == "hazard" else fy
    plats = {}
    for p in spec.get("platforms", []):
        ctx.element = (p["id"], p.get("source", "visible")); A.platform(ctx, p, base_y, centre); plats[p["id"]] = p
    for c in spec.get("connections", []):
        ctx.element = (c["id"], c.get("source", "visible")); A.connection(ctx, c, plats[c["from"]], plats[c["to"]], fy)
    blocks = {}
    for s in spec.get("structures", []):
        ctx.element = (s["id"], s.get("source", "visible")); x, y, z, yaw = A._place(ctx, s, plats, fy, centre)
        A.STRUCTURES[s["kind"]](ctx, s, x, y, z, yaw)
        if s.get("on"):
            blocks.setdefault(s["on"], []).append((x, z, max(s.get("size", [2, 2, 2])[0], s.get("size", [2, 2, 2])[-1]) / 2 + 0.8))
            ctx.platform_blocks = getattr(ctx, "platform_blocks", []) + [blocks[s["on"]][-1]]  # cover keeps clear of it
    for p in spec.get("pipes", []):
        ctx.element = (p["id"], p.get("source", "visible")); A.pipe(ctx, p, fy, ar)
    A.party_walls(ctx)
    A.place_covers(ctx)  # after connections: cover never stands in a landing (Stage 8)
    for h in spec.get("hazards", []):
        ctx.element = (h["id"], h.get("source", "visible")); x0, z0, x1, z1 = h["area"]
        ctx.hazards.append(ctx.add(h["id"], "box", [(x0 + x1) / 2, 0, (z0 + z1) / 2], [abs(x1 - x0), h["y"], abs(z1 - z0)], h.get("material", "hazard")))
    ctx.element = None
    # materials: only roles in use (+ spec overrides; variants follow their base override)
    over = spec.get("materials", {}).get("roles", {}); theme = spec.get("theme", "industrial"); mats = {}
    for r in sorted(ctx.roles):
        m = A.role_material(theme, r); base = r[:-3] if r.endswith("_v2") else r
        if base in over:
            m = dict(m, **over[base])
            if r != base and "color" in over[base]: m["color"] = [round(min(1, c * f), 3) for c, f in zip(over[base]["color"], (0.92, 0.95, 0.9))]
        mats[r] = m
    spawn, spawns = _spawns(spec, plats, blocks, centre, ctx, G)
    env, glow = _environment(spec, ctx)
    b = _bounds(spec, ctx)
    from sky import PRESETS
    L = dict(version=1, units=UNITS, source=f"scene_spec.json - {spec.get('title', spec['name'])}",
             generator=dict(tool="pipeline/spec_to_level.py", spec_sha=H(spec), theme=theme, detail=spec.get("detail", "medium")),
             interpretation=spec.get("interpretation", {}), sky_color=PRESETS[env["sky"]["preset"]]["horizon"],
             spawn=spawn, spawns=spawns, hazards=ctx.hazards, effects=_effects(spec, ctx, plats, env, glow), environment=env,
             bounds=b, walkable=ctx.walkable, materials=mats, objects=ctx.objects, mobile=dict(profile=spec.get("profile", "balanced")),
             validation=dict(ignore_objects=[]), generator_notes=ctx.notes, relations=ctx.relations)
    if spec.get("gameplay"): L["gameplay"] = spec["gameplay"]
    return L


def _spawns(spec, plats, blocks, centre, ctx, G):
    rq = G["design"]["spawn_clearance"] + G["player"]["radius"]; out = []
    want = spec.get("spawns") or [{"id": "spawn", "on": max(plats, key=lambda k: plats[k]["center"][1]) if plats else None}]
    for i, s in enumerate(want):
        if s.get("position"): x, y, z = s["position"]
        elif s.get("on"):
            p = plats[s["on"]]; (cx, cz), (w, d) = p["center"], p["size"]; y = p["top"]; best = None
            hx, hz = max(0.0, w / 2 - rq), max(0.0, d / 2 - rq)
            for gx in [cx + hx * k / 4 for k in range(-4, 5)]:
                for gz in [cz + hz * k / 4 for k in range(-4, 5)]:
                    obs = blocks.get(s["on"], []) + [(cx + ox, cz + oz, 1.4) for ox, oz in ((-w / 4, -d / 4), (w / 4, d / 4), (w / 4, -d / 4), (-w / 4, d / 4))[:int(p.get("cover", 0))]]
                    if p.get("shape") in ("octagon", "circle") and math.hypot(gx - cx, gz - cz) > min(w, d) / 2 * 0.85 - rq: continue
                    clear = min([math.hypot(gx - ox, gz - oz) - r for ox, oz, r in obs] or [99])
                    score = (clear >= rq, -math.hypot(gx - cx, gz - cz) if clear >= rq else clear)
                    if best is None or score > best[0]: best = (score, gx, gz)
            x, z = best[1], best[2]
        else:
            fy = spec["arena"]["floor"]["y"]; x, y, z = centre[0], fy, centre[1] + spec["arena"]["size"][1] * 0.35
        yaw = s.get("yaw", math.degrees(math.atan2(-(centre[0] - x), -(centre[1] - z))) if math.hypot(centre[0] - x, centre[1] - z) > 1 else 0.0)
        out.append(dict(id=s.get("id", "spawn" if i == 0 else f"spawn_{i + 1}"), position=[round(x, 2), round(y, 2), round(z, 2)], yaw_deg=round(yaw, 1)))
    first = dict(position=out[0]["position"], yaw_deg=out[0]["yaw_deg"])
    return first, out[1:]


def _environment(spec, ctx):
    at, bg, th = spec.get("atmosphere", {}), spec.get("background", {}), ctx.theme
    ar = spec["arena"]; R = math.hypot(*ar["size"]) / 2; f = max(1.0, R / 51.0)
    glow = at.get("glow_color") or A.role_material(spec.get("theme", "industrial"), "glow").get("emissive", [0.5, 1.0, 0.3])
    sky = dict(preset=at.get("sky", th["sky"]), **at.get("sky_overrides", {}))
    atm = {k: at[k] for k in ("fog_start", "fog_end", "height_fog") if k in at}; atm.setdefault("fog_start", round(60 * f))
    if "layers" in bg: layers = bg["layers"]
    else:
        d = dict(th["background"], **{k: v for k, v in bg.items() if k != "source"}); mh = d.get("mountain_height", [70, 160])
        layers = [dict(id="Ground", type="ground", radius=[0, round(470 * f)], flat_radius=round(R + 12), rise=16, roughness=5,
                       **({"material_type": d["ground_type"], "color": d.get("ground_color", [0.3, 0.3, 0.25])} if d.get("ground_type") else {}))]
        if d.get("town"):  # distant houses (walls + matching roofs) so the town continues beyond the playable square
            tr = [round(R + 6), round(R * 2.5 + 70)]
            layers += [dict(id="Town_Walls", type="townscape", part="walls", radius=tr, height=[8, 15], count=34, seed=11, fade=0.15),
                       dict(id="Town_Roofs", type="townscape", part="roofs", radius=tr, height=[8, 15], count=34, seed=11, fade=0.15,
                            material_type="roof_tiles", color=[0.52, 0.29, 0.22], tile_m=3.0)]
        if d["mountains"] in ("both", "far"): layers.append(dict(id="Mountains_Far", type="mountain_ring", radius=round(430 * f), depth=70, height=mh, fade=0.55, seed=3))
        if d["mountains"] in ("both", "near"): layers.append(dict(id="Mountains_Near", type="mountain_ring", radius=round(290 * f), depth=45, height=[round(mh[0] * 0.26), round(mh[1] * 0.35)], fade=0.3, seed=8, frequency=3.5, sharpness=2.2))
        if d.get("spires"): layers.append(dict(id="Spires", type="spires", radius=[round(R * 1.9), round(210 * f)], count=16, height=[22, 65], fade=0.15, seed=5))
        if d.get("skyline"): layers.append(dict(id="Skyline_North", type="skyline", radius=round(250 * f), azimuth_deg=[-55, 40], count=26, height=[18, 60], fade=0.35, glow=glow, lit=0.12))
        for i, az in enumerate([48, 105, 215, 290, 160, 340][:d.get("factories", 0)]):
            layers.append(dict(id=f"Factory_{i + 1:02d}", type="factory", azimuth_deg=az, distance=round((165 + 12 * i) * f), scale=round(0.9 + 0.1 * (i % 3), 2), seed=i + 1, glow=glow, fade=0.15))
    env = dict(quality=spec.get("profile", "balanced"), horizon_distance=round(460 * f), sky=sky, atmosphere=atm, background=layers)
    return env, glow


def _effects(spec, ctx, plats, env, glow):
    E = spec.get("effects", "auto")
    if E == "none": return []
    if isinstance(E, list): return E
    cfg = E if isinstance(E, dict) else {"auto": True}; out = []
    toxic = A.role_material(spec.get("theme", "industrial"), "hazard")["type"] == "toxic"
    if cfg.get("auto", True):
        ar = spec["arena"]; (cx, cz), (w, d) = ar.get("center", [0, 0]), ar["size"]; fy = ar["floor"]["y"]
        for i, hz in enumerate(ctx.hazards):
            sfx = "" if i == 0 else f"_{i + 1}"
            out += [dict(id="Hazard_Surface" + sfx, type="liquid_surface", target=hz, scroll=[0.03, 0.015], swirl=0.03, pulse_speed=0.2, pulse_amount=0.18)]
            if toxic: out += [dict(id="Hazard_Bubbles" + sfx, type="bubbles", area_from=hz, rate=45), dict(id="Hazard_Mist" + sfx, type="fog_sheet", area_from=hz, height=0.5, opacity=0.3, color=glow)]
        if ctx.pours:
            out += [dict(id="Pour_Flow", type="liquid_flow", targets_glob=list(ctx.pours), speed=3.0),
                    dict(id="Pour_Splash", type="splash", at_targets_glob=list(ctx.pours), anchor="bottom"),
                    dict(id="Pour_Steam", type="steam", at_targets_glob=list(ctx.pours), anchor="bottom")]
        for f in getattr(ctx, "fountains", []): out.append(dict(id=f + "_Ripple", type="liquid_surface", target=f, scroll=[0.02, 0.01], swirl=0.02, pulse_speed=0.1, pulse_amount=0.05))
        if "glow" in ctx.roles: out.append(dict(id="Glow_Pulse", type="pulse_light", target_material="glow", speed=0.9, amount=0.4))
        if "trim" in ctx.roles and A.role_material(spec.get("theme", "industrial"), "trim").get("emissive"): out.append(dict(id="Trim_Pulse", type="pulse_light", target_material="trim", speed=0.35, amount=0.35))
        if "structure" in ctx.roles and A.role_material(spec.get("theme", "industrial"), "structure").get("emissive"): out.append(dict(id="Machinery_Flicker", type="flicker", target_material="structure", rate=6, amount=0.2))
        towers = [s for s in spec.get("structures", []) if s["kind"] in ("tower", "machinery", "building")]
        if towers and spec.get("theme", "industrial") in ("industrial", "toxic_industrial", "scifi"):
            pts = []
            for s in towers[:3]:
                o = next(o for o in ctx.objects if o["name"] == s["id"]); w_ = s.get("size", [4, 4, 4])
                pts.append([round(o["position"][0] + w_[0] / 2 + 0.2, 2), round(o["position"][1] + 0.4, 2), round(o["position"][2] + w_[-1] / 2 + 0.2, 2)])
            out.append(dict(id="Sparks", type="sparks", positions=pts))
        amb = spec.get("atmosphere", {}).get("ambient", ctx.theme["ambient"])
        if amb != "none":
            col = {"spores": glow, "dust": [0.9, 0.85, 0.7], "embers": [1.0, 0.5, 0.15], "snow": [0.95, 0.97, 1.0]}[amb]
            out.append(dict(id="Ambient_" + amb.capitalize(), type="ambient_particles", area=[cx - w / 2, fy, cz - d / 2, cx + w / 2, fy + 15, cz + d / 2],
                            count=220 if amb != "dust" else 160, color=col, **({"blend": "alpha", "alpha": 0.35} if amb == "dust" else {})))
        if any(l.get("type") == "factory" for l in env["background"]): out.append(dict(id="Factory_Smoke", type="smoke", at_background="factory_chimneys"))
        out.append(dict(id="Sky_Drift", type="sky_drift", speed_deg_s=0.25))
    out = [e for e in out if e["id"] not in set(cfg.get("disable", []))] + list(cfg.get("extra", []))
    return out


def _bounds(spec, ctx):
    ar = spec["arena"]; (cx, cz), (w, d) = ar.get("center", [0, 0]), ar["size"]; t = ar.get("walls", {}).get("thickness", 0) + 1
    xs, zs = [cx - w / 2 - t, cx + w / 2 + t], [cz - d / 2 - t, cz + d / 2 + t]; top = ar.get("walls", {}).get("height", 10)
    for o in ctx.objects:
        if o.get("parent") is None and o["type"] != "boundary":
            xs.append(o["position"][0]); zs.append(o["position"][2])
    for p in spec.get("platforms", []): top = max(top, p["top"])
    for s in spec.get("structures", []): top = max(top, s.get("size", [0, 0, 0])[1] + 10)
    return dict(min=[round(min(xs), 2), 0, round(min(zs), 2)], max=[round(max(xs), 2), round(top + 2, 2), round(max(zs), 2)])


# ------------------------------------------------------------------ merge with an existing (possibly edited) level
def _merge(new, cur, state, key, rep, label):
    out = {}
    for n, it in new.items():
        if n in cur:
            if n in state and H(cur[n]) != state[n]: out[n] = cur[n]; rep["kept_edited"].append(f"{label}:{n}")
            elif n not in state: out[n] = cur[n]; rep["kept_manual"].append(f"{label}:{n}")
            else: out[n] = it
        elif n in state: rep["kept_deleted"].append(f"{label}:{n}")
        else: out[n] = it
    for n, it in cur.items():
        if n in out: continue
        if n not in state: out[n] = it; rep["kept_manual"].append(f"{label}:{n}")
        elif H(it) != state[n]: out[n] = it; rep["kept_edited"].append(f"{label}:{n} (no longer generated)")
    return out


TOP_KEYS = ("spawn", "spawns", "bounds", "sky_color", "validation", "gameplay", "mobile", "interpretation")


def merge(Lnew, Lcur, state):
    rep = dict(kept_edited=[], kept_manual=[], kept_deleted=[])
    objs = _merge({o["name"]: o for o in Lnew["objects"]}, {o["name"]: o for o in Lcur.get("objects", [])}, state.get("objects", {}), "name", rep, "object")
    order, seen = [], set()  # parents before children
    def visit(n, stack=()):
        if n in seen or n not in objs or n in stack: return
        p = objs[n].get("parent")
        if p: visit(p, stack + (n,))
        seen.add(n); order.append(objs[n])
    for n in objs: visit(n)
    L = dict(Lnew); L["objects"] = order
    L["materials"] = _merge(Lnew["materials"], Lcur.get("materials", {}), state.get("materials", {}), None, rep, "material")
    L["effects"] = list(_merge({e["id"]: e for e in Lnew["effects"]}, {e["id"]: e for e in Lcur.get("effects", [])}, state.get("effects", {}), None, rep, "effect").values())
    env_new, env_cur = Lnew["environment"], Lcur.get("environment", {})
    env = _merge({k: v for k, v in env_new.items() if k != "background"}, {k: v for k, v in env_cur.items() if k != "background"}, state.get("environment", {}), None, rep, "environment")
    env["background"] = list(_merge({l["id"]: l for l in env_new.get("background", [])}, {l["id"]: l for l in env_cur.get("background", [])}, state.get("background", {}), None, rep, "background").values())
    L["environment"] = env
    for k in TOP_KEYS:
        if k in Lcur and k in state.get("top", {}) and H(Lcur[k]) != state["top"][k]: L[k] = Lcur[k]; rep["kept_edited"].append(f"top:{k}")
    names = {o["name"] for o in L["objects"]}
    key = lambda r: (r["type"], r["a"], r.get("a_anchor"), r.get("b"))
    L["relations"] = [r for r in Lnew.get("relations", []) if r["a"] in names] + [r for r in Lcur.get("relations", []) if r.get("manual") and key(r) not in {key(x) for x in Lnew.get("relations", [])}]
    L["hazards"] = [h for h in dict.fromkeys(Lnew["hazards"] + Lcur.get("hazards", [])) if h in names]
    L["walkable"] = Lnew["walkable"] + [w for w in Lcur.get("walkable", []) if w.get("name") not in {x.get("name") for x in Lnew["walkable"]} and w.get("manual")]
    missing = sorted({o["parent"] for o in L["objects"] if o.get("parent") and o["parent"] not in names})
    if missing: rep["warnings"] = [f"children whose parent was deleted: {missing}"]
    return L, rep


def state_of(L):
    return dict(objects={o["name"]: H(o) for o in L["objects"]}, materials={k: H(v) for k, v in L["materials"].items()},
                effects={e["id"]: H(e) for e in L["effects"]}, environment={k: H(v) for k, v in L["environment"].items() if k != "background"},
                background={l["id"]: H(l) for l in L["environment"].get("background", [])}, top={k: H(L[k]) for k in TOP_KEYS if k in L})


def run(spec_path, level_dir=None, force=False, dry=False, verbose=True):
    spec = json.load(open(spec_path)); E, W = validate(spec)
    for w in W: verbose and print("warning:", w)
    if E: raise SystemExit("scene spec invalid:\n  " + "\n  ".join(E))
    level_dir = level_dir or os.path.dirname(os.path.abspath(spec_path)); lp = os.path.join(level_dir, "level.json"); sp = os.path.join(level_dir, "gen_state.json")
    G = load_gameplay(level_dir, {"gameplay": spec.get("gameplay")} if spec.get("gameplay") else None)
    Lnew = generate(spec, G); rep = dict(kept_edited=[], kept_manual=[], kept_deleted=[])
    if os.path.exists(lp):
        Lcur = json.load(open(lp))
        if not os.path.exists(sp) and not force: raise SystemExit(f"{lp} exists and was not made by spec_to_level.py (no gen_state.json): use --force to replace it")
        state = json.load(open(sp)) if os.path.exists(sp) else {}
        L, rep = merge(Lnew, Lcur, state) if state else (Lnew, rep)
        if not dry:
            from edit_level import snapshot
            snapshot(level_dir, Lcur, "regenerate from " + os.path.basename(spec_path))
    else: L = Lnew
    for k in ("build_stats",):
        if os.path.exists(lp) and k in json.load(open(lp)): pass
    summary = dict(objects=len(L["objects"]), materials=len(L["materials"]), effects=len(L["effects"]), background_layers=len(L["environment"]["background"]),
                   walkable_areas=len(L["walkable"]), notes=Lnew["generator_notes"], **{k: v for k, v in rep.items() if v})
    if dry:
        verbose and print(json.dumps(summary, indent=1)); return L, summary
    os.makedirs(level_dir, exist_ok=True)
    json.dump(L, open(lp, "w"), indent=1); json.dump(state_of(Lnew), open(sp, "w"), indent=0)
    verbose and print(json.dumps(summary, indent=1))
    return L, summary


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    run(a[0], a[1] if len(a) > 1 else None, force="--force" in sys.argv, dry="--dry-run" in sys.argv)
