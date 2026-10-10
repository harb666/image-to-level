"""Stage 4: environmental effects metadata (+ Godot 4 runtime kit, + browser preview data).

  python3 pipeline/effects.py levels/<name>      # rebuild ONLY effects (seconds); build_level.py also calls it

level.json "effects": [ {id, type, ...placement, ...params} ]  (optional; levels without it are unaffected)
Placement (pick one): "target": node | "targets_glob": "Pipe_*_Fall" or a list of globs (shader/material effects on those nodes)
  "target_material": name (every node using it) | "area_from": node (its top surface/box) | "area": [x0,y0,z0,x1,y1,z1]
  "at_targets_glob" (glob or list) + "anchor": bottom|top|center (one emitter per matching node) | "positions": [[x,y,z],...]
  "at_background": "factory_chimneys" (chimney tops from environment.json)
Every type has defaults (TYPES below); any default can be overridden per effect; "enabled": false disables it.

IMPORTANT - what transfers where:
  GLB (level.glb)  : only static appearance - textures/emissive at "frame 0". NO animation, particles or fog.
  effects.json     : engine-neutral description of every effect: world-space emitters/targets, per-quality params,
                     "merge_emitters": continuous multi-point effects should be ONE particle system (emission points),
                     estimated cost. This is what Construct Error should recreate at runtime.
  fx/godot/        : untested-in-Godot starter kit: .gdshader files + apply_effects.gd (builds CPUParticles3D /
                     ShaderMaterial overrides / emission pulses on the imported scene by node name).
  Browser viewer   : approximates the same effects with three.js for previewing on iPhone (not identical to Godot).
"""
import fnmatch, json, math, os, shutil, sys, numpy as np, trimesh
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
QUALITY = {"performance": 0.4, "balanced": 1.0, "quality": 1.6}  # particle count / rate multiplier

TYPES = {  # category, defaults, Godot runtime recipe, what the GLB carries
    "liquid_surface": dict(category="surface_shader", godot="ShaderMaterial liquid_surface.gdshader on target meshes (albedo from the GLB texture)",
                           glb="static base colour + emissive texture", defaults=dict(scroll=[0.03, 0.015], swirl=0.025, pulse_speed=0.25, pulse_amount=0.15, glow_energy=1.0),
                           quality={"performance": dict(swirl=0.0)}),
    "liquid_flow": dict(category="surface_shader", godot="ShaderMaterial liquid_flow.gdshader (UV scroll along the fall/pipe)",
                        glb="static texture", defaults=dict(speed=1.5, glow_energy=1.2, wobble=0.02)),
    "pulse_light": dict(category="material_animation", godot="script: emission_energy_multiplier = base * (1 + amount*sin(2*pi*speed*t + phase))",
                        glb="emissive at base strength", defaults=dict(speed=0.5, amount=0.3, phase=0.0)),
    "flicker": dict(category="material_animation", godot="script: emission_energy_multiplier random flicker (rate Hz)",
                    glb="emissive at base strength", defaults=dict(rate=8.0, amount=0.25)),
    "bubbles": dict(category="particles", godot="CPUParticles3D, box emitter on the surface, alpha billboard", glb="nothing",
                    defaults=dict(rate=40.0, lifetime=1.4, speed=[0.3, 0.7], gravity=0.0, size=[0.15, 0.45], alpha=1.0, color=[0.92, 1.0, 0.7], texture="bubble", blend="alpha", spread=10)),
    "splash": dict(category="particles", godot="CPUParticles3D, point emitter, gravity", glb="nothing",
                   defaults=dict(rate=30.0, lifetime=0.8, speed=[2.0, 4.0], gravity=-9.8, kill_below_spawn=True, size=[0.35, 0.1], alpha=1.0, color=[0.9, 1.0, 0.6], texture="mote", blend="add", spread=40)),
    "steam": dict(category="particles", godot="CPUParticles3D, small sphere emitter, slow rise, growing soft puffs", glb="nothing",
                  defaults=dict(rate=5.0, lifetime=3.5, speed=[0.8, 1.5], gravity=0.15, size=[1.2, 5.0], alpha=0.5, color=[0.8, 0.92, 0.74], texture="puff", blend="alpha", spread=15, radius=0.8)),
    "smoke": dict(category="particles", godot="CPUParticles3D at chimney tops, few large puffs (distant: low cost)", glb="nothing",
                  defaults=dict(rate=1.2, lifetime=12.0, speed=[2.0, 3.5], gravity=0.05, size=[6.0, 26.0], alpha=0.45, color=[0.16, 0.18, 0.15], texture="puff", blend="alpha", spread=12, radius=2.0, wind=[1.2, 0, 0.4])),
    "sparks": dict(category="particles", godot="CPUParticles3D per point (independent bursts), explosiveness 1, one_shot re-triggered every interval, additive", glb="nothing",
                   defaults=dict(burst=18, interval=[1.5, 4.0], lifetime=0.6, speed=[3.0, 6.0], gravity=-9.8, size=[0.1, 0.03], alpha=1.0, color=[1.0, 0.65, 0.2], texture="spark", blend="add", spread=70)),
    "ambient_particles": dict(category="particles", godot="CPUParticles3D, box emitter over the play volume, slow drift (spores/ash/dust)", glb="nothing",
                              defaults=dict(count=250, lifetime=8.0, speed=[0.05, 0.25], gravity=0.0, size=[0.12, 0.25], alpha=0.7, color=[0.85, 1.0, 0.55], texture="mote", blend="add", spread=180),
                              quality={"performance": dict(count_mult=0.3)}),
    "fog_sheet": dict(category="transparent_mesh", godot="large plane MeshInstance3D + fog_sheet.gdshader (scrolling noise, depth-faded). "
                      "Godot FogVolume/volumetric fog is NOT available in the Mobile/Compatibility renderers, hence a sheet", glb="nothing",
                      defaults=dict(height=0.6, opacity=0.35, scroll=[0.02, 0.01], color=[0.55, 0.9, 0.3], layers=1),
                      quality={"performance": dict(enabled=False), "quality": dict(layers=2)}),
    "cloud_layer": dict(category="cloud_layer", godot="disc MeshInstance3D + cloud_layer.gdshader (fbm noise coverage, radial edge fade, sun-side "
                        "glow, soft intersections via depth). One transparent draw call per layer; no volumetrics", glb="nothing",
                        defaults=dict(y=20.0, radius=600.0, inner=0.55, opacity=0.6, coverage=0.45, scale=0.012, scroll=[0.004, 0.0015],
                                      color=[1.0, 0.86, 0.76], shade=[0.62, 0.5, 0.56], glow=[1.0, 0.62, 0.35], layers=1, spacing=6.0),
                        quality={"performance": dict(layers_mult=0.5), "quality": dict(layers_mult=1.5)}),
    "cloud_puffs": dict(category="billboards", godot="ONE MultiMeshInstance3D of quads, StandardMaterial3D billboard (keep scale), alpha, "
                        "unshaded, proximity fade; per-instance colour = sun-lit tint baked here. One draw call", glb="nothing",
                        defaults=dict(count=12, size=[8.0, 16.0], opacity=0.85, color=[1.0, 0.88, 0.8], shade=[0.6, 0.48, 0.55],
                                      glow=[1.0, 0.6, 0.32], drift=0.6, texture="cloud", squash=0.55),
                        quality={"performance": dict(count_mult=0.5), "quality": dict(count_mult=1.3)}),
    "sky_drift": dict(category="environment", godot="script: Environment.sky_rotation.y += speed (rad/s) - slow cloud drift", glb="nothing",
                      defaults=dict(speed_deg_s=0.25)),
}
PARTICLE_TEXTURES = ("puff", "mote", "spark", "bubble", "cloud")



def globmatch(name, g):
    """g: one glob or a list of globs (edit_level.py duplicate appends clone names to a list)."""
    return any(fnmatch.fnmatch(name, x) for x in ([g] if isinstance(g, str) else g))

def _sprites(out_dir):
    """Tiny white-on-alpha particle sprites (tinted at runtime). 64/32 px PNGs."""
    os.makedirs(out_dir, exist_ok=True); rng = np.random.default_rng(4)
    def save(name, a, S):
        img = np.zeros((S, S, 4), np.uint8); img[..., :3] = 255; img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
        Image.fromarray(img, "RGBA").save(os.path.join(out_dir, name + ".png"), optimize=True)
    S = 64; y, x = (np.mgrid[:S, :S] + 0.5) / S - 0.5; r = np.hypot(x, y)
    n = np.asarray(Image.fromarray((rng.random((8, 8)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), float) / 255
    save("puff", np.clip(1 - r / 0.5, 0, 1) ** 1.6 * (0.6 + 0.4 * n), S)
    S = 32; y, x = (np.mgrid[:S, :S] + 0.5) / S - 0.5; r = np.hypot(x, y)
    save("mote", np.clip(1 - r / 0.5, 0, 1) ** 2.2, S)
    save("spark", np.clip(1 - r / 0.5, 0, 1) ** 3 + np.exp(-(r / 0.08) ** 2), S)
    save("bubble", np.exp(-((r - 0.36) / 0.05) ** 2) * 0.9 + 0.15 * np.clip(1 - r / 0.4, 0, 1) + np.exp(-(np.hypot(x + 0.15, y + 0.15) / 0.06) ** 2), S)
    # cloud: cumulus blob (overlapping soft lobes + fbm erosion); RGB = self-shadowing (lit top -> darker base), tinted at runtime
    S = 128; y, x = (np.mgrid[:S, :S] + 0.5) / S - 0.5; a = np.zeros((S, S))
    for cx_, cy_, r_ in ((0, 0.08, 0.3), (-0.2, 0.12, 0.2), (0.2, 0.1, 0.22), (-0.08, -0.08, 0.22), (0.12, -0.05, 0.2), (0.3, 0.18, 0.12), (-0.3, 0.2, 0.12)):
        a = np.maximum(a, np.clip(1 - np.hypot(x - cx_, (y - cy_) * 1.15) / r_, 0, 1))
    fb = sum(np.asarray(Image.fromarray((rng.random((k, k)) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC), float) / 255 / 2 ** i for i, k in enumerate((6, 12, 24)))
    a = np.clip(a ** 0.8 * 1.35 - (1 - fb / 1.75) * 0.45, 0, 1) * np.clip((0.5 - np.abs(y + 0.02)) * 3, 0, 1)
    lit = np.clip(0.55 + (0.25 - y) * 0.75 + (fb / 1.75 - 0.5) * 0.35, 0.35, 1.0)
    img = np.zeros((S, S, 4), np.uint8); img[..., 0] = img[..., 1] = img[..., 2] = (lit * 255).astype(np.uint8); img[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    Image.fromarray(img, "RGBA").save(os.path.join(out_dir, "cloud.png"), optimize=True)


def _node_boxes(glb):
    """World AABB per node of the level glb."""
    s = trimesh.load(glb, force="scene"); out = {}
    for node in s.graph.nodes_geometry:
        M, g = s.graph[node]; b = s.geometry[g].bounds
        c = np.array([[x, y, z, 1] for x in b[:, 0] for y in b[:, 1] for z in b[:, 2]]) @ M.T
        out[node] = np.array([c[:, :3].min(0), c[:, :3].max(0)])
    return out, s


def _mat_nodes(scene, mat):
    res = []
    for node in scene.graph.nodes_geometry:
        g = scene.geometry[scene.graph[node][1]]; m = getattr(getattr(g.visual, "material", None), "name", "")
        if m == mat or m == mat + "__2s": res.append(node)
    return res


def _puff_rings(e, boxes, D):
    """Cloud puff positions (deterministic): rings AROUND things so they hide their lower parts in cloud.
    around_targets_glob + y: [y0, y1] (absolute band, clamped to each node's height) -> ring at the node's footprint
    around_points: [[x, z, radius, y0, y1, n], ...] (terrain islands, distant cliffs, horizon banks)."""
    import zlib
    rng = np.random.default_rng(zlib.crc32(e["id"].encode())); s0, s1 = e.get("size", D["size"]); out = []
    def ring(cx, cz, rad, y0, y1, n, of=None):
        y0, y1 = min(y0, y1), max(y0, y1); a0 = rng.uniform(0, 2 * np.pi)
        for k in range(n):
            a = a0 + 2 * np.pi * k / n + rng.uniform(-0.25, 0.25) * 2 * np.pi / n; rr = rad * rng.uniform(0.85, 1.25)
            size = rng.uniform(s0, s1) * (1 + rad / 60) ** 0.5
            out.append(dict(pos=[round(float(cx + np.cos(a) * rr), 2), round(float(rng.uniform(y0, y1)), 2), round(float(cz + np.sin(a) * rr), 2)],
                            size=round(float(size), 2), rot=round(float(rng.uniform(-0.25, 0.25)), 3), **({"of": of} if of else {})))
    if e.get("around_targets_glob"):
        y0, y1 = e.get("y", [None, None])
        for n in sorted(n for n in boxes if globmatch(n, e["around_targets_glob"])):
            b = boxes[n]; c = (b[0] + b[1]) / 2; rad = float(np.hypot(*(b[1] - b[0])[[0, 2]]) / 2) + s0 * 0.25
            lo, hi = max(b[0][1], y0 if y0 is not None else b[0][1]), min(b[1][1], y1 if y1 is not None else b[1][1])
            if hi <= lo: continue
            ring(c[0], c[2], rad, lo, hi, int(e.get("per_target", max(3, min(8, round(rad * 2 * np.pi / (s0 * 0.9)))))), n)
    for pt in e.get("around_points", []):
        x, z, rad, y0, y1 = pt[:5]; n = int(pt[5]) if len(pt) > 5 else max(4, int(round(rad * 2 * np.pi / (s0 * 0.8))))
        ring(x, z, rad, y0, y1, n)
    return out


def resolve(level_dir, L=None):
    L = L or json.load(open(os.path.join(level_dir, "level.json"))); spec = L.get("effects")
    if not spec: return None
    boxes, scene = _node_boxes(os.path.join(level_dir, "level.glb"))
    envp = os.path.join(level_dir, "environment.json"); env = json.load(open(envp)) if os.path.exists(envp) else None
    out, totals = [], {q: dict(max_particles=0, emitters=0, extra_draw_calls=0, transparent_area_m2=0) for q in QUALITY}
    from anchors import world_matrices, world_anchor
    W, by = world_matrices(L)
    for e in spec:
        t = TYPES[e["type"]]; prm = dict(t["defaults"]); prm.update({k: v for k, v in e.items() if k in t["defaults"]})
        R = dict(id=e["id"], type=e["type"], category=t["category"], glb_contains=t["glb"], godot_runtime=t["godot"])
        # placement
        tg = [e["target"]] if e.get("target") else []
        if e.get("targets_glob"): tg = sorted(n for n in boxes if globmatch(n, e["targets_glob"]))
        if e.get("target_material"): tg = _mat_nodes(scene, e["target_material"]); R["target_material"] = e["target_material"]
        if tg: R["targets"] = tg
        if tg and t["category"] == "surface_shader":  # UV speed needs the material's tile size (UVs are metres / tile_m)
            mat = next((o.get("material") for o in L["objects"] if o["name"] == tg[0]), None)
            R["material_tile_m"] = L["materials"].get(mat, {}).get("tile_m", 2.0)
        em = []
        if e.get("at_targets_glob"):
            for n in sorted(n for n in boxes if globmatch(n, e["at_targets_glob"])):
                b = boxes[n]; c = (b[0] + b[1]) / 2; a = e.get("anchor", "center")
                if a == "bottom" and by.get(n, {}).get("type") == "stream":  # Stage 8: emit at the real impact point of the stream
                    k = world_anchor(W, by[n], "sink"); sub = 0.3; w_ = by[n]["size"][0]
                    em.append(dict(pos=[round(float(k["pos"][0]), 2), round(float(k["pos"][1] + sub), 2), round(float(k["pos"][2]), 2)], radius=round(w_ / 2 + e.get("margin", 0.6), 2), of=n)); continue
                rad = round(float(np.hypot(*(b[1] - b[0])[[0, 2]]) / 2 + e.get("margin", 0.6)), 2)  # spawn AROUND the node, not inside it
                em.append(dict(pos=[round(float(c[0]), 2), round(float(b[0][1] if a == "bottom" else b[1][1] if a == "top" else c[1]), 2), round(float(c[2]), 2)], radius=rad, of=n))
        for p in e.get("positions", []): em.append(dict(pos=p))
        if e["type"] == "cloud_puffs": em += _puff_rings(e, boxes, t["defaults"])
        if e.get("at_background") == "factory_chimneys" and env:
            for l in env["background"]["layers"]:
                for c in l.get("chimney_tops", []): em.append(dict(pos=c[:3], radius=c[3], of=l["node"]))
        area = None
        if e.get("area_from"):
            b = boxes[e["area_from"]]; area = [*b[0].round(2).tolist(), *b[1].round(2).tolist()]; area[1] = area[4]  # top surface
        if e.get("area"): area = e["area"]
        if area: R["area"] = [round(float(v), 2) for v in area]
        if em: R["emitters"] = em
        # per-quality parameters, enabling and cost estimate
        R["quality"] = {}
        for q, mult in QUALITY.items():
            p = dict(prm); p.update(t.get("quality", {}).get(q, {})); on = e.get("enabled", True) and p.pop("enabled", True)
            cost = dict(max_particles=0, emitters=0, extra_draw_calls=0)
            if t["category"] == "particles":
                k = mult * p.pop("count_mult", 1.0); n_em = max(1, len(em)) if (em or area) else 0
                if "count" in p: p["count"] = int(round(p["count"] * k)); alive = p["count"]
                elif "burst" in p: p["burst"] = max(4, int(round(p["burst"] * min(k, 1.2)))); alive = p["burst"]
                else: p["rate"] = round(p["rate"] * k, 2); alive = int(np.ceil(p["rate"] * p["lifetime"]))
                merged = "burst" not in p and n_em > 1  # continuous multi-point effects -> ONE emitter (emission points)
                cost = dict(max_particles=alive * n_em, emitters=n_em, extra_draw_calls=1 if merged else n_em)
                if merged: R["merge_emitters"] = True
            elif t["category"] == "cloud_layer":
                n_l = max(1, int(round(p.get("layers", 1) * p.pop("layers_mult", 1.0)))); p["layers"] = n_l
                cost = dict(max_particles=0, emitters=0, extra_draw_calls=n_l, transparent_area_m2=round(math.pi * p["radius"] ** 2 * n_l))
            elif t["category"] == "billboards":
                k = mult * p.pop("count_mult", 1.0); keep = em[::max(1, int(round(1 / k)))] if k < 1 else em
                if k > 1 and len(em): keep = em  # quality: all of them (rings already generated at full density)
                p["puffs"] = len(keep); R["emitters_by_quality"] = R.get("emitters_by_quality", {}); R["emitters_by_quality"][q] = [i for i, e_ in enumerate(em) if e_ in keep]
                cost = dict(max_particles=len(keep), emitters=1, extra_draw_calls=1 if keep else 0, transparent_area_m2=round(sum(e_["size"] ** 2 * 0.6 for e_ in keep)))
            elif t["category"] == "transparent_mesh" and area:
                cost = dict(max_particles=0, emitters=0, extra_draw_calls=p.get("layers", 1))
                cost["transparent_area_m2"] = round((area[3] - area[0]) * (area[5] - area[2]) * p.get("layers", 1))
            R["quality"][q] = dict(enabled=bool(on), params=p, cost_estimate=cost)
            if on:
                for k2 in totals[q]: totals[q][k2] += cost.get(k2, 0)
        out.append(R)
    att = []  # Stage 8: fluid attachment metadata (outlet -> stream -> pool) so the game can render enhanced fluids
    from anchors import infer_relations
    rel = infer_relations(L)
    for o in L["objects"]:
        if o["type"] != "stream": continue
        src = next((r for r in rel if r["type"] == "emits_from" and r["a"] == o["name"]), None); pool = next((r["b"] for r in rel if r["type"] == "flows_into" and r["a"] == o["name"]), None)
        S, K = world_anchor(W, o, "source"), world_anchor(W, o, "sink"); O = world_anchor(W, by[src["b"]], src.get("b_anchor") or "outlet") if src and src["b"] in by else None
        rnd = lambda v: [round(float(x), 3) for x in v]
        att.append(dict(stream=o["name"], source_object=src["b"] if src else None, outlet_pos=rnd(O["pos"]) if O else rnd(S["pos"]), outlet_dir=rnd(O["dir"]) if O else rnd(S["dir"]),
                        outlet_diameter=round(float(O["width"] if O else o["size"][0]), 3), section=o.get("section", "circle"), stream_width=o["size"][0],
                        initial_speed=o.get("speed", 2.5), impact_pos=rnd(K["pos"]), receiving=pool, hazard=o["name"] in set(L.get("hazards", [])) or o.get("material") in {by[h].get("material") for h in L.get("hazards", []) if h in by}))
    return dict(generated_by="image-to-level Stage 4 (pipeline/effects.py)", default_quality="balanced", fluid_attachments=att,
                note="GLB holds only static appearance. Recreate these at runtime (fx/godot/apply_effects.gd is an untested starter). "
                     "Costs are estimates: particles alive, emitters, extra draw calls, transparent overdraw area.",
                textures={k: f"fx/{k}.png" for k in PARTICLE_TEXTURES}, totals=totals, effects=out)


def build_effects(level_dir, L=None, log=print):
    L = L or json.load(open(os.path.join(level_dir, "level.json")))
    fxdir = os.path.join(level_dir, "fx")
    if not L.get("effects"):
        for f in ("effects.json",):
            if os.path.exists(os.path.join(level_dir, f)): os.remove(os.path.join(level_dir, f))
        shutil.rmtree(fxdir, ignore_errors=True); return None
    _sprites(fxdir); FX = resolve(level_dir, L)
    json.dump(FX, open(os.path.join(level_dir, "effects.json"), "w"), indent=1)
    gd = os.path.join(fxdir, "godot"); os.makedirs(gd, exist_ok=True)
    for f in os.listdir(os.path.join(HERE, "godot_fx")): shutil.copy(os.path.join(HERE, "godot_fx", f), gd)
    log(json.dumps(dict(effects=len(FX["effects"]), totals=FX["totals"]["balanced"])))
    return FX


if __name__ == "__main__":
    build_effects(sys.argv[1])
