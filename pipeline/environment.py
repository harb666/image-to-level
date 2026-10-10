"""Stage 2: sky + distant environment + Godot environment metadata from level.json["environment"].

  python3 pipeline/environment.py levels/<name>     # rebuild ONLY sky/background/metadata (level.glb untouched)
  (build_level.py also calls it automatically when level.json has an "environment" section)

Writes into levels/<name>/:
  sky/panorama.jpg        2:1 equirect sky (procedural, or resized external image)  -> Godot PanoramaSkyMaterial
  background.glb          distant scenery, one node per layer id under "Background" (no collision, not walkable)
  environment.json        engine-neutral lighting/fog/sky/background settings (authoritative metadata)
  environment.tres        Godot 4 Environment resource generated from environment.json (UNTESTED in Godot here)
Levels without "environment" are unaffected (backwards compatible).
"""
import hashlib, json, os, sys, numpy as np, trimesh
from PIL import Image
from trimesh.transformations import euler_matrix, translation_matrix
import sky as skymod
from backdrop import QUALITY, GENERATORS, DEFAULTS, polar
from materials import make_material
from glb_tools import dedupe_images
from glb_stats import stats

DEFAULT_ATMOS = dict(fog_start=70, fog_end=None, sky_affect=0.55, height_fog=dict(height=2.0, density=0.12),
                     exposure=1.0, tonemap="filmic", contrast=1.05, saturation=1.05, brightness=1.0,
                     glow=dict(enabled=True, intensity=0.7, bloom=0.08, hdr_threshold=0.9))


def _lerp(a, b, t):
    return [round(float(x + (y - x) * t), 3) for x, y in zip(a, b)]


def build_environment(level_dir, L=None, log=print):
    L = L or json.load(open(os.path.join(level_dir, "level.json")))
    env = L.get("environment")
    if not env: return None
    qname = env.get("quality", "balanced"); q = QUALITY[qname]
    layers = env.get("background", [])
    # ---- sky (cached: only re-rendered when its inputs change)
    glows = [dict(azimuth_deg=l.get("azimuth_deg", 0), color=l["glow"], strength=l.get("glow_strength", 0.35), width_deg=l.get("glow_width_deg", 10))
             for l in layers if l.get("type") == "factory" and l.get("glow")]
    sky_cfg = env.get("sky", {"preset": "industrial_smog"}); os.makedirs(os.path.join(level_dir, "sky"), exist_ok=True)
    pano = os.path.join(level_dir, "sky", "panorama.jpg"); keyf = pano + ".key.json"
    key = hashlib.sha1(json.dumps([sky_cfg, glows, q["sky_width"], q["sky_q"]], sort_keys=True).encode()).hexdigest()
    cached = os.path.exists(pano) and os.path.exists(keyf) and json.load(open(keyf)).get("key") == key
    if cached:
        info = json.load(open(keyf))["info"]
    else:
        if sky_cfg.get("image"):
            img, info = skymod.load_external(os.path.join(level_dir, sky_cfg["image"]), q["sky_width"]); info.update(light={}, sun=skymod.resolve(sky_cfg)["sun"])
        else:
            img, info = skymod.render(sky_cfg, q["sky_width"], glows)
        Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)).save(pano, quality=q["sky_q"], optimize=True, progressive=True)
        json.dump(dict(key=key, info=info), open(keyf, "w"))
    preset = skymod.resolve(sky_cfg); light = dict(preset.get("light", {}), **env.get("lighting", {}))
    atm = dict(DEFAULT_ATMOS, **env.get("atmosphere", {}))
    horizon = env.get("horizon_distance", 450)
    fog_color = atm.get("fog_color") or info["horizon_rgb"]
    fog_end = atm.get("fog_end") or horizon * 0.95
    # ---- background meshes
    scene = trimesh.Scene(); base = scene.graph.base_frame
    scene.graph.update(frame_from=base, frame_to="Background", matrix=np.eye(4))
    mats, meta_layers, tex_px = {}, [], 0
    for lay in layers:
        typ = lay["type"]; kind, col, tile = DEFAULTS[typ]
        fade = lay.get("fade", 0.0)  # atmospheric perspective baked into the colour (plus runtime fog)
        mname = "bg_" + lay["id"].lower()
        mdef = dict(type=lay.get("material_type", kind), color=_lerp(lay.get("color", col), fog_color, fade), tile_m=lay.get("tile_m", tile),
                    res=lay.get("res", q["tex_res"]))
        if lay.get("glow"): mdef.update(accent=lay["glow"], emissive=_lerp([0.7, 0.7, 0.7], [0.25, 0.25, 0.25], fade), lit=lay.get("lit", 0.15))
        mat, px = make_material(mname, mdef); mats[mname] = mdef; tex_px += sum(px)
        m = GENERATORS[typ](lay, q)
        T = np.eye(4)
        if typ in ("factory", "ring_structure"):  # local mesh, node placed by azimuth/distance, front turned to the arena
            T = translation_matrix(polar(lay.get("azimuth_deg", 0), lay.get("distance", 180))) @ euler_matrix(0, np.radians(-lay.get("azimuth_deg", 0)), 0)
        chim = [[round(float(c), 2) for c in (T @ [x, y, z, 1])[:3]] + [round(r, 2)] for x, y, z, r in m.metadata.get("chimney_tops", [])]
        # world-scaled planar UVs (same scheme as the playable level)
        from build_level import uv_world
        if typ == "ground":  # smooth & welded (6x fewer vertices than faceted), top-down UVs
            uv = m.vertices[:, [0, 2]] / mdef["tile_m"]
        else:  # faceted low-poly look
            m, uv = uv_world(m, mdef["tile_m"])
        m.visual = trimesh.visual.TextureVisuals(uv=uv, material=mat)
        node = "BG_" + lay["id"] if not lay["id"].startswith("BG_") else lay["id"]
        scene.add_geometry(m, node_name=node, geom_name=node, parent_node_name="Background", transform=T)
        meta_layers.append(dict(id=lay["id"], node=node, type=typ, triangles=int(len(m.faces)), material=mname,
                                collision=False, cast_shadows=False, visibility_range_end=round(q["far"] * 1.05)))
        if chim: meta_layers[-1]["chimney_tops"] = chim  # world [x, y, z, radius]: smoke emitters for Stage 4 effects
    bg = os.path.join(level_dir, "background.glb")
    if layers:
        scene.export(bg); dedupe_images(bg); bst = stats(bg)
    else:
        bst = None
        if os.path.exists(bg): os.remove(bg)
    # ---- metadata (engine-neutral) + Godot resource
    sun = preset["sun"]; az, el = sun["azimuth_deg"], sun["elevation_deg"]; sd = skymod._dir(az, el)
    E = dict(
        generated_by="image-to-level Stage 2 (pipeline/environment.py)", quality=qname,
        note="Browser preview approximates this; Godot settings are generated but not tested in Godot here.",
        files=dict(level="level.glb", background="background.glb" if layers else None, sky_panorama="sky/panorama.jpg", godot_environment="environment.tres"),
        sky=dict(type="panorama", image="sky/panorama.jpg", size=[q["sky_width"], q["sky_width"] // 2], projection="equirectangular",
                 preset=sky_cfg.get("preset", "industrial_smog"), external=bool(sky_cfg.get("image")),
                 azimuth_convention="image column u -> atan2(dir.z, dir.x) (three.js); level azimuth 0=north(-z) 90=east(+x). "
                                    "If the Godot sky looks rotated vs the sun, adjust Environment sky_rotation.y in 90° steps.",
                 horizon_rgb=info["horizon_rgb"], upper_rgb=info["upper_rgb"]),
        sun=dict(azimuth_deg=az, elevation_deg=el, direction_to_sun=[round(float(v), 4) for v in sd], color=light.get("sun_color", sun["color"]),
                 energy=light.get("sun_energy", 1.5), godot_rotation_degrees=[-el, round(180 - az, 2), 0],
                 shadows=dict(enabled=True, mode="PSSM 2 splits", max_distance=70, note="keep shadows to the playable area on mobile")),
        ambient=dict(source="sky", sky_color=info["upper_rgb"], ground_color=info.get("below_rgb", fog_color), energy=light.get("ambient_energy", 1.0)),
        fog=dict(enabled=True, color=fog_color, start=atm["fog_start"], end=round(fog_end), godot_density=round(3.0 / fog_end, 5),
                 sky_affect=atm["sky_affect"], height=atm["height_fog"]["height"], height_density=atm["height_fog"]["density"]),
        tonemap=dict(mode=atm["tonemap"], exposure=light.get("exposure", atm["exposure"])),
        glow=atm["glow"], adjustments=dict(brightness=atm["brightness"], contrast=atm["contrast"], saturation=atm["saturation"]),
        camera=dict(far=q["far"], horizon_distance=horizon),
        background=dict(layers=meta_layers, materials=list(mats), stats=bst,
                        tex_mem_gpu_compressed_mb=round(tex_px * 4 / 3 / 2 ** 20, 2)),
        sky_asset=dict(kb=round(os.path.getsize(pano) / 1024), tex_mem_gpu_compressed_mb=round(q["sky_width"] ** 2 / 2 * 4 / 3 / 2 ** 20, 2)),
    )
    json.dump(E, open(os.path.join(level_dir, "environment.json"), "w"), indent=1)
    write_tres(os.path.join(level_dir, "environment.tres"), E, level_dir)
    log(json.dumps(dict(environment=qname, sky_kb=E["sky_asset"]["kb"], sky_cached=cached,
                        background=(dict(kb=bst["glb_kb"], tris=bst["triangles"], draw_calls=bst["draw_calls_unbatched"], materials=bst["materials"]) if bst else None))))
    return E


def write_tres(path, E, level_dir):
    """Godot 4 text Environment resource (Sky -> PanoramaSkyMaterial). Path assumes the level folder is copied to res://levels/<name>/."""
    c = lambda v: "Color(%.3f, %.3f, %.3f, 1)" % tuple(v[:3])
    name = os.path.basename(os.path.normpath(level_dir)); f, t, g, a = E["fog"], E["tonemap"], E["glow"], E["adjustments"]
    tm = {"linear": 0, "reinhard": 1, "filmic": 2, "aces": 3}.get(t["mode"], 2)
    open(path, "w").write(f'''[gd_resource type="Environment" load_steps=4 format=3]

[ext_resource type="Texture2D" path="res://levels/{name}/{E["sky"]["image"]}" id="1_sky"]

[sub_resource type="PanoramaSkyMaterial" id="PanoramaSkyMaterial_1"]
panorama = ExtResource("1_sky")

[sub_resource type="Sky" id="Sky_1"]
sky_material = SubResource("PanoramaSkyMaterial_1")

[resource]
background_mode = 2
sky = SubResource("Sky_1")
ambient_light_source = 3
ambient_light_energy = {E["ambient"]["energy"]:.3f}
reflected_light_source = 2
tonemap_mode = {tm}
tonemap_exposure = {t["exposure"]:.3f}
glow_enabled = {"true" if g["enabled"] else "false"}
glow_intensity = {g["intensity"]:.3f}
glow_bloom = {g["bloom"]:.3f}
glow_hdr_threshold = {g["hdr_threshold"]:.3f}
fog_enabled = true
fog_light_color = {c(f["color"])}
fog_density = {f["godot_density"]:.5f}
fog_sky_affect = {f["sky_affect"]:.3f}
fog_height = {f["height"]:.3f}
fog_height_density = {f["height_density"]:.3f}
adjustment_enabled = true
adjustment_brightness = {a["brightness"]:.3f}
adjustment_contrast = {a["contrast"]:.3f}
adjustment_saturation = {a["saturation"]:.3f}
''')


if __name__ == "__main__":
    build_environment(sys.argv[1])
