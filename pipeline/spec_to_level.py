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
import world as WM
from scene_spec import validate
from gameplay import load_gameplay

H = lambda v: hashlib.sha1(json.dumps(v, sort_keys=True).encode()).hexdigest()[:16]
UNITS = "metres, y-up; position = centre of object's base, in parent space; rotation = degrees XYZ"


def mode_of(spec):
    return "hybrid" if spec.get("world") and spec.get("arena") else "open" if spec.get("world") else "structured"


def generate(spec, G, level_dir=None):
    spec = copy.deepcopy(spec); ctx = A.Ctx(spec, G); ctx.level_dir = level_dir; ctx.TR = None
    ar, W = spec.get("arena"), spec.get("world"); auto = []
    fy = ar["floor"]["y"] if ar else float(W.get("base_y", 0.0))
    centre = tuple(ar.get("center", [0, 0])) if ar else tuple(W.get("center") or [(a + b) / 2 for a, b in zip(WM.extent_of(W)[:2], WM.extent_of(W)[2:])])
    if W: _, auto = WM.build_world(ctx, spec, W, fy, centre)  # Stage 9: terrain definition, pads, foundations, boundary, auto bridges
    if ar: A.arena(ctx, ar, fy)
    for t in spec.get("terrain", []):
        ctx.element = (t["id"], t.get("source", "visible")); A.terrain(ctx, t, fy)
    base_y = 0.0 if ar and ar["floor"]["kind"] == "hazard" else fy
    plats = {}
    for p in spec.get("platforms", []):
        ctx.element = (p["id"], p.get("source", "visible")); pb = base_y
        if ctx.TR is not None and not (ar and _in_arena(ar, p["center"])):  # on open terrain: supports reach below the lowest ground under it
            pb = A.ground_height(ctx, p["center"][0], p["center"][1], fy, max(p["size"]) / 2) - 0.6
        A.platform(ctx, p, pb, centre); plats[p["id"]] = p
    for c in spec.get("connections", []):
        ctx.element = (c["id"], c.get("source", "visible")); A.connection(ctx, c, plats[c["from"]], plats[c["to"]], fy)
    blocks = {}
    for s in spec.get("structures", []) + auto:
        ctx.element = (s["id"], s.get("source", "visible"))
        if s.get("from") and s.get("to") and not s.get("position") and not s.get("on"):  # line modules: wall, bridge, street, walkway, tunnel
            (ax, az), (bx, bz) = s["from"], s["to"]; x, z = (ax + bx) / 2, (az + bz) / 2; yaw = A.yaw_to(bx - ax, bz - az) if (ax, az) != (bx, bz) else 0.0
            y = s.get("y", A.ground_height(ctx, x, z, fy) if ctx.TR is not None else fy) if s["kind"] != "wall" else s.get("y", fy)
            if s["kind"] in ("bridge", "walkway") and "y" not in s and ctx.TR is not None:  # decks land on the banks at both ends, never on the bed
                import numpy as np
                t_ = np.linspace(0, 1, 41); L_ = math.hypot(bx - ax, bz - az) or 1; nx_, nz_ = -(bz - az) / L_, (bx - ax) / L_; hw_ = s.get("width", 5.0) / 2
                H_ = np.max([ctx.TR.height(ax + (bx - ax) * t_ + nx_ * o_, az + (bz - az) * t_ + nz_ * o_) for o_ in (-hw_, 0.0, hw_)], axis=0)  # across the deck width
                ya, yb = s.get("y_from", float(H_[:3].max()) + 0.1), s.get("y_to", float(H_[-3:].max()) + 0.1)
                lift = max(0.0, float((H_ + 0.12 - (ya + (yb - ya) * t_)).max()))  # the whole deck clears the ground under it
                s = dict(s, y_from=round(ya + lift, 2), y_to=round(yb + lift, 2)); y = (s["y_from"] + s["y_to"]) / 2
        else: x, y, z, yaw = A._place(ctx, s, plats, fy, centre)
        A.STRUCTURES[s["kind"]](ctx, s, x, y, z, yaw)
        if s.get("on"):
            blocks.setdefault(s["on"], []).append((x, z, max(s.get("size", [2, 2, 2])[0], s.get("size", [2, 2, 2])[-1]) / 2 + 0.8))
            ctx.platform_blocks = getattr(ctx, "platform_blocks", []) + [blocks[s["on"]][-1]]  # cover keeps clear of it
    for p in spec.get("pipes", []):
        ctx.element = (p["id"], p.get("source", "visible")); A.pipe(ctx, p, fy, ar or {"center": list(centre), "size": [0, 0]})
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
    regions = None
    if W and not spec.get("spawns"):  # Stage 9: player / enemy spawn regions on open terrain
        blocked = [(o["position"][0], o["position"][2], max(o["size"][0], o["size"][2]) / 2) for o in ctx.objects
                   if not o.get("parent") and o.get("size") and o["type"] not in ("boundary", "group")]
        blocked += [(s["position"][0], s["position"][-1], max(s.get("size", [3, 3, 3])[0], s.get("size", [3, 3, 3])[-1]) / 2 + 1.0)
                    for s in spec.get("structures", []) + auto if s.get("position") and not s.get("on")]
        blocked += [((s["from"][0] + s["to"][0]) / 2, (s["from"][1] + s["to"][1]) / 2, math.hypot(s["to"][0] - s["from"][0], s["to"][1] - s["from"][1]) / 2)
                    for s in spec.get("structures", []) + auto if s.get("from") and s.get("to") and s["kind"] in ("bridge", "walkway", "tunnel")]
        blocked += [(p["center"][0], p["center"][1], max(p["size"]) / 2) for p in spec.get("platforms", [])]
        if ar: blocked.append((ar.get("center", [0, 0])[0], ar.get("center", [0, 0])[1], max(ar["size"]) / 2 + 3))
        regions = WM.spawn_regions(ctx, spec, W, G, blocked)
        pl = next((r for r in regions if r["team"] == "player" and r["points"]), None)
        if pl is None: raise SystemExit("world: no safe player spawn point found in any player spawn region")
        spawn = dict(position=pl["points"][0], yaw_deg=pl["yaw_deg"]); spawns = [dict(id=f"{r['id']}_{k + 1}", position=p, yaw_deg=r["yaw_deg"], team=r["team"])
                                                                                 for r in regions for k, p in enumerate(r["points"]) if p is not pl["points"][0]]
        ctx.walkable += [dict(name=r["id"], min=[r["points"][0][0] - 1.5, r["points"][0][2] - 1.5], max=[r["points"][0][0] + 1.5, r["points"][0][2] + 1.5],
                              y=r["points"][0][1]) for r in regions if r["points"]]
    else: spawn, spawns = _spawns(spec, plats, blocks, centre, ctx, G)
    if ctx.TR is not None and W.get("terrain_playable", True): ctx.walkable += WM.walk_samples(ctx)
    env, glow = _environment(spec, ctx)
    b = _bounds(spec, ctx) if ctx.TR is None else WM.world_bounds(ctx, max([p["top"] for p in spec.get("platforms", [])] + [0]))
    from sky import PRESETS
    L = dict(version=1, units=UNITS, source=f"scene_spec.json - {spec.get('title', spec['name'])}",
             generator=dict(tool="pipeline/spec_to_level.py", spec_sha=H(spec), theme=theme, detail=spec.get("detail", "medium")),
             interpretation=spec.get("interpretation", {}), sky_color=PRESETS[env["sky"]["preset"]]["horizon"],
             spawn=spawn, spawns=spawns, hazards=ctx.hazards, effects=_effects(spec, ctx, plats, env, glow), environment=env,
             bounds=b, walkable=ctx.walkable, materials=mats, objects=ctx.objects, mobile=dict(profile=spec.get("profile", "balanced"), **spec.get("mobile", {})), **({"style": spec["style"]} if spec.get("style") else {}),
             validation=dict(ignore_objects=[]), generator_notes=ctx.notes, relations=ctx.relations)
    if spec.get("gameplay"): L["gameplay"] = spec["gameplay"]
    if W: L["gameplay"] = dict({"nav": {"cell": 1.0}}, **L.get("gameplay", {}))  # open worlds: 1 m nav cells (large areas)
    L["generator"]["mode"] = mode_of(spec)
    if ctx.TR is not None:
        L["terrain"] = ctx.terrain_def; L["spawn_regions"] = regions or []
        L["materials"].update({k: v for k, v in ctx.TR.materials().items() if k not in L["materials"]})
        for k in list(L["materials"]):  # spec material overrides for terrain layers ("ter_grass": {...})
            if k in spec.get("materials", {}).get("roles", {}) and k.startswith("ter_"): L["materials"][k] = dict(L["materials"][k], **spec["materials"]["roles"][k])
    return L


def _in_arena(ar, p):
    (cx, cz), (w, d) = ar.get("center", [0, 0]), ar["size"]; return abs(p[0] - cx) <= w / 2 and abs(p[1] - cz) <= d / 2


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
            fy = spec["arena"]["floor"]["y"]; x, y, z = centre[0], fy, centre[1] + spec["arena"]["size"][1] * 0.35  # (world levels use spawn regions)
        yaw = s.get("yaw", math.degrees(math.atan2(-(centre[0] - x), -(centre[1] - z))) if math.hypot(centre[0] - x, centre[1] - z) > 1 else 0.0)
        out.append(dict(id=s.get("id", "spawn" if i == 0 else f"spawn_{i + 1}"), position=[round(x, 2), round(y, 2), round(z, 2)], yaw_deg=round(yaw, 1),
                        **({"team": s["team"]} if s.get("team") else {})))
    first = dict(position=out[0]["position"], yaw_deg=out[0]["yaw_deg"])
    return first, out[1:]


def _environment(spec, ctx):
    at, bg, th = spec.get("atmosphere", {}), spec.get("background", {}), ctx.theme
    if ctx.TR is not None:  # world: the detailed terrain + its middle ring replace the flat ground skirt
        e = ctx.TR; R = math.hypot(e.x1 - e.x0, e.z1 - e.z0) / 2; f = max(1.0, R / 120.0)
    else: ar = spec["arena"]; R = math.hypot(*ar["size"]) / 2; f = max(1.0, R / 51.0)
    glow = at.get("glow_color") or A.role_material(spec.get("theme", "industrial"), "glow").get("emissive", [0.5, 1.0, 0.3])
    sky = dict(preset=at.get("sky", th["sky"]), **at.get("sky_overrides", {}))
    atm = {k: at[k] for k in ("fog_start", "fog_end", "height_fog", "fog_color") if k in at}
    LK = ("sun_energy", "sun_color", "ambient_energy", "exposure"); lit = at.get("lighting", {})  # light -> env.lighting, grading -> atmosphere
    atm.update({k: v for k, v in lit.items() if k not in LK}); atm.setdefault("fog_start", round(60 * f) if ctx.TR is None else round(R * 0.9))
    if "layers" in bg: layers = bg["layers"]
    else:
        d = dict(th["background"], **{k: v for k, v in bg.items() if k != "source"}); mh = d.get("mountain_height", [70, 160])
        layers = [] if ctx.TR is not None else [dict(id="Ground", type="ground", radius=[0, round(470 * f)], flat_radius=round(R + 12), rise=16, roughness=5,
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
    if any(k in lit for k in LK): env["lighting"] = {k: lit[k] for k in LK if k in lit}
    if ctx.TR is not None and "radius" not in ctx.terrain_def["zones"]["middle"]:  # middle zone runs into the far mountains (no gap)
        mr = [l for l in layers if l.get("type") == "mountain_ring"]
        if mr:
            m = min(mr, key=lambda l: l["radius"]); ctx.terrain_def["zones"]["middle"]["radius"] = round(m["radius"] - 0.3 * m.get("depth", 60))
        else: ctx.terrain_def["zones"]["middle"]["radius"] = round(min(env["horizon_distance"] * 0.85, max(R * 2.6, 380)))
    return env, glow


def _effects(spec, ctx, plats, env, glow):
    E = spec.get("effects", "auto")
    if E == "none": return []
    if isinstance(E, list): return E
    cfg = E if isinstance(E, dict) else {"auto": True}; out = []
    toxic = A.role_material(spec.get("theme", "industrial"), "hazard")["type"] == "toxic"
    if cfg.get("auto", True):
        if spec.get("arena"): ar = spec["arena"]; (cx, cz), (w, d) = ar.get("center", [0, 0]), ar["size"]; fy = ar["floor"]["y"]
        else:
            P = ctx.boundary; xs, zs = [p[0] for p in P], [p[1] for p in P]; cx, cz, w, d = (min(xs) + max(xs)) / 2, (min(zs) + max(zs)) / 2, max(xs) - min(xs), max(zs) - min(zs)
            fy = float(ctx.TR.height_at(cx, cz))
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
        out += _clouds(spec, ctx, plats)
    out = [e for e in out if e["id"] not in set(cfg.get("disable", []))] + list(cfg.get("extra", []))
    return out


def _clouds(spec, ctx, plats):
    """atmosphere.clouds -> layered cloud effects (cloud_layer discs + cloud_puffs rings) that bury the lower parts of
    columns, islands and distant cliffs in cloud while staying BELOW the playable decks (combat sightlines stay clear).
    Keys: layers [{y, radius, opacity, coverage, scale, layers}], collars {glob, y}|false, islands true|false,
    distant true|false, horizon [radius, ...], color / shade / glow, below (m under the lowest deck kept clear)."""
    C = spec.get("atmosphere", {}).get("clouds")
    if not C: return []
    tint = {k: C[k] for k in ("color", "shade", "glow") if k in C}; out = []
    decks = [p["top"] for p in (plats.values() if isinstance(plats, dict) else plats)] or [0.0]; clear = min(decks) - C.get("below", 6.0)  # nothing above this height
    for i, l in enumerate(C.get("layers", [])):
        out.append(dict(id=f"Cloud_Layer_{i + 1}", type="cloud_layer", center=l.get("center", [0, 0]), **tint,
                        **{k: (min(v, clear) if k == "y" else v) for k, v in l.items() if k != "center"}))
    col = C.get("collars", {"glob": ["*_Column"]})
    if col:
        y = col.get("y", [clear - 14, clear]); y = [y[0], min(y[1], clear)]
        out.append(dict(id="Cloud_Collars", type="cloud_puffs", around_targets_glob=col.get("glob", ["*_Column"]), y=y, size=col.get("size", [7.0, 13.0]), **tint))
    TD = getattr(ctx, "terrain_def", None) or {}; feats = TD.get("features", []) if ctx.TR is not None else []
    base = TD.get("base_y", 0.0)
    def top(f): return base + f.get("height", 10)
    near = [f for f in feats if f.get("radius") and f.get("center") and f.get("type") in ("mesa", "plateau", "hill", "mountain") and math.hypot(*f["center"]) < 120]
    far = [f for f in feats if f.get("radius") and f.get("center") and f.get("type") in ("mesa", "plateau", "hill", "mountain", "cliff", "ridge") and math.hypot(*f["center"]) >= 120]
    if C.get("islands", True) and near:
        out.append(dict(id="Cloud_Islands", type="cloud_puffs", size=C.get("island_size", [14.0, 24.0]), **tint,
                        around_points=[[f["center"][0], f["center"][1], f["radius"] * 1.05, min(top(f) - 16, clear - 4), min(top(f) - 7, clear)] for f in near]))
    if C.get("distant", True):
        pts = [[f["center"][0], f["center"][1], f["radius"] * 1.1, top(f) * 0.25, top(f) * 0.6] for f in far]
        pts += [[0, 0, r, min(0.0, clear - 20), clear - 8, max(16, int(r / 14))] for r in C.get("horizon", [])]
        if pts: out.append(dict(id="Cloud_Distant", type="cloud_puffs", size=C.get("distant_size", [50.0, 110.0]), opacity=0.85, **tint, around_points=pts))
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


TOP_KEYS = ("spawn", "spawns", "bounds", "sky_color", "validation", "gameplay", "mobile", "interpretation", "spawn_regions", "style")


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
    if isinstance(Lnew.get("terrain"), dict):  # Stage 9: terrain settings + features merged by id (edited features survive regeneration)
        tn, tc = Lnew["terrain"], Lcur.get("terrain") if isinstance(Lcur.get("terrain"), dict) else {}; st = state.get("terrain", {})
        T = _merge({k: v for k, v in tn.items() if k != "features"}, {k: v for k, v in tc.items() if k != "features"}, st.get("keys", {}), None, rep, "terrain")
        T["features"] = list(_merge({f["id"]: f for f in tn["features"]}, {f["id"]: f for f in tc.get("features", [])}, st.get("features", {}), None, rep, "terrain_feature").values())
        L["terrain"] = T
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
                background={l["id"]: H(l) for l in L["environment"].get("background", [])}, top={k: H(L[k]) for k in TOP_KEYS if k in L},
                **({"terrain": dict(keys={k: H(v) for k, v in L["terrain"].items() if k != "features"}, features={f["id"]: H(f) for f in L["terrain"]["features"]})}
                   if isinstance(L.get("terrain"), dict) else {}))


def run(spec_path, level_dir=None, force=False, dry=False, verbose=True):
    import styles
    spec = styles.apply(json.load(open(spec_path))); E, W = validate(spec)  # art_style preset deep-merged UNDER the spec
    for w in W: verbose and print("warning:", w)
    if E: raise SystemExit("scene spec invalid:\n  " + "\n  ".join(E))
    level_dir = level_dir or os.path.dirname(os.path.abspath(spec_path)); lp = os.path.join(level_dir, "level.json"); sp = os.path.join(level_dir, "gen_state.json")
    G = load_gameplay(level_dir, {"gameplay": spec.get("gameplay")} if spec.get("gameplay") else None)
    if spec.get("world") and os.path.exists(lp) and os.path.exists(sp):  # Stage 9: kept terrain features (repairs / manual) shape the generation too
        Lc, st = json.load(open(lp)), json.load(open(sp)); gen_ids = set(st.get("terrain", {}).get("features", {}))
        own = {f["id"] for f in spec["world"].get("features", [])}
        extra = [f for f in (Lc.get("terrain") or {}).get("features", []) if f["id"] not in own and (f.get("gen") == "repair" or f["id"] not in gen_ids)]
        if extra: spec = copy.deepcopy(spec); spec["world"]["features"] = list(spec["world"].get("features", [])) + extra
    Lnew = generate(spec, G, level_dir); rep = dict(kept_edited=[], kept_manual=[], kept_deleted=[])
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
