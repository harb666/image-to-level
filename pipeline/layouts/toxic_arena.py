"""Hand-authored layout for inputs/toxic_arena_concept.png (read from its TOP DOWN LAYOUT + SIDE VIEW panels).
Writes levels/toxic_arena/level.json; then run: python3 pipeline/build_level.py levels/toxic_arena
Square arena, 72 m inside the walls. Hazard fluid top = 1 m; main deck = 6 m; diagonal platforms = 4 m.
North = -z. All objects are named and editable in level.json afterwards."""
import json, math, os, shutil

OUT = os.path.join(os.path.dirname(__file__), "..", "..", "levels", "toxic_arena")
A, DECK, LOW, FLUID = 36.0, 6.0, 4.0, 1.0
objs = []


def add(**o):
    o.setdefault("rotation", [0, 0, 0]); objs.append(o); return o


def platform(name, x, z, w, d, top, lights_to=None, cover=0):
    """Group: concrete _Base column rising from the fluid, worn _Floor plate, optional red _Light panels and _Cover crates."""
    add(name=name, type="group", position=[x, 0, z])
    add(name=name + "_Base", parent=name, type="box", material="concrete_dark", position=[0, 0, 0], size=[w, top - 0.3, d])
    add(name=name + "_Floor", parent=name, type="box", material="floor_plate", position=[0, top - 0.3, 0], size=[w + 0.3, 0.3, d + 0.3])
    add(name=name + "_Trim", parent=name, type="box", material="edge_trim", position=[0, top - 1.1, 0], size=[w + 0.5, 0.6, d + 0.5])
    if lights_to:  # light panels on the two faces looking at the centre
        sx, sz = lights_to
        add(name=name + "_Light_01", parent=name, type="panel", material="red_panel", position=[0, top - 3.2, sz * (d / 2 + 0.03)],
            rotation=[0, 0 if sz > 0 else 180, 0], size=[1.4, 1.8, 0])
        add(name=name + "_Light_02", parent=name, type="panel", material="red_panel", position=[sx * (w / 2 + 0.03), top - 3.2, 0],
            rotation=[0, 90 if sx > 0 else 270, 0], size=[1.4, 1.8, 0])
    for k in range(cover):  # waist-high cover crates for the shooter
        cx, cz = [(-w / 4, -d / 4), (w / 4, d / 4), (w / 4, -d / 4), (-w / 4, d / 4)][k]
        add(name=f"{name}_Cover_{k + 1:02d}", parent=name, type="box", material="metal_dark", position=[round(cx, 2), top, round(cz, 2)], size=[1.6, 1.2, 1.6])


def bridge(name, x0, z0, x1, z1, y, width=4.5):
    """Flat metal walkway between two points (axis-aligned)."""
    cx, cz, L = (x0 + x1) / 2, (z0 + z1) / 2, math.hypot(x1 - x0, z1 - z0)
    along_x = abs(x1 - x0) > abs(z1 - z0)
    add(name=name, type="box", material="metal_grate", position=[cx, y - 0.4, cz], size=[L, 0.4, width] if along_x else [width, 0.4, L])


# --- hazard + perimeter
add(name="HazardFluid", type="box", material="toxic", position=[0, 0, 0], size=[2 * A, FLUID, 2 * A])
for nm, (x, z, w, d) in {"North": (0, -A - 2, 2 * A + 8, 4), "South": (0, A + 2, 2 * A + 8, 4),
                         "West": (-A - 2, 0, 4, 2 * A), "East": (A + 2, 0, 4, 2 * A)}.items():
    add(name="OuterWall_" + nm, type="box", material="metal_dark", position=[x, 0, z], size=[w, 14, d])
# perimeter walkway (inner ledge along the walls)
for nm, (x, z, w, d) in {"North": (0, -A + 2, 2 * A, 4), "South": (0, A - 2, 2 * A, 4),
                         "West": (-A + 2, 0, 4, 2 * A - 8), "East": (A - 2, 0, 4, 2 * A - 8)}.items():
    platform("Walkway_" + nm, x, z, w, d, DECK)
# red banners on the inner wall faces
for nm, x, z, yaw in [("North", -12, -A + 0.03, 0), ("North", 12, -A + 0.03, 0), ("South", -12, A - 0.03, 180), ("South", 12, A - 0.03, 180),
                      ("West", -A + 0.03, -12, 90), ("West", -A + 0.03, 12, 90), ("East", A - 0.03, -12, 270), ("East", A - 0.03, 12, 270)]:
    k = sum(o["name"].startswith("Banner_" + nm) for o in objs) + 1
    add(name=f"Banner_{nm}_{k:02d}", type="panel", material="red_panel", position=[x, 7.5, z], rotation=[0, yaw, 0], size=[2.2, 5.0, 0])

# --- centre: octagonal deck + industrial tower
add(name="Central_Platform", type="group", position=[0, 0, 0])
add(name="Central_Platform_Base", parent="Central_Platform", type="cylinder", sections=8, material="concrete_dark", position=[0, 0, 0], size=[22, DECK - 0.3, 22])
add(name="Central_Platform_Floor", parent="Central_Platform", type="cylinder", sections=8, material="floor_plate", position=[0, DECK - 0.3, 0], size=[22.4, 0.3, 22.4])
add(name="Central_Tower", type="group", position=[0, DECK, 0])
add(name="Central_Tower_Body", parent="Central_Tower", type="box", material="metal_dark", position=[0, 0, 0], size=[7, 13, 7])
add(name="Central_Tower_Cap", parent="Central_Tower", type="box", material="metal_dark", position=[0, 13, 0], size=[8, 1.2, 8])
for k, (px, pz, yaw) in enumerate([(0, 3.53, 0), (3.53, 0, 90), (0, -3.53, 180), (-3.53, 0, 270)]):
    add(name=f"Central_Tower_Banner_{k + 1:02d}", parent="Central_Tower", type="panel", material="red_panel", position=[px, 4, pz], rotation=[0, yaw, 0], size=[2.6, 6.5, 0])
    for s in (-1, 1):  # glowing green strips either side of each banner
        off = 2.4 * s
        add(name=f"Central_Tower_Glow_{k + 1:02d}_{'L' if s < 0 else 'R'}", parent="Central_Tower", type="panel", material="glow_strip",
            position=[px + (off if pz else 0), 1, pz + (off if px else 0)], rotation=[0, yaw, 0], size=[0.6, 10, 0])
for k, (x, z) in enumerate([(-6, -6), (6, 6), (6, -6), (-6, 6)]):  # cover on the central deck
    add(name=f"Central_Cover_{k + 1:02d}", type="box", material="metal_dark", position=[x, DECK, z], size=[2.0, 1.2, 1.0 if k < 2 else 2.0])

# --- four arms: bridge from the centre to a mid platform touching the perimeter walkway
MID = 26.0  # centre of the mid platforms
for nm, (sx, sz) in {"North": (0, -1), "South": (0, 1), "West": (-1, 0), "East": (1, 0)}.items():
    platform(f"Platform_{nm}_01", sx * MID, sz * MID, 12, 12, DECK, lights_to=(-sx or 1, -sz or 1), cover=2)
    bridge(f"Bridge_{nm}_01", sx * 11, sz * 11, sx * (MID - 6), sz * (MID - 6), DECK)

# --- four diagonal platforms (lower) + ramps up to the centre and bridges to the neighbouring arms
D = 17.0
for nm, (sx, sz) in {"NE": (1, -1), "NW": (-1, -1), "SE": (1, 1), "SW": (-1, 1)}.items():
    platform(f"Platform_{nm}_01", sx * D, sz * D, 10, 10, LOW, lights_to=(-sx, -sz), cover=1)
    yaw = math.degrees(math.atan2(-sx, -sz))  # ramp rises towards the centre
    add(name=f"Ramp_{nm}_01", type="ramp", material="metal_grate", position=[sx * 10.3, LOW, sz * 10.3], rotation=[0, round(yaw, 1), 0], size=[4, DECK - LOW, 7.5])
    add(name=f"Stairs_{nm}_N", type="stairs", material="metal_grate", position=[sx * D, LOW, sz * (D + 5 + 4)],
        rotation=[0, 0 if sz > 0 else 180, 0], size=[3, DECK - LOW, 8])  # up to the perimeter walkway

# --- pipes: four corners (diagonal) + one on each side wall, each pouring fluid; plus low pipe runs along the walls
def pipe(name, x, z, yaw, L=11, y=10, r=3.0):
    dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    add(name=name, type="cylinder", sections=10, material="pipe", position=[x, y, z], rotation=[90, yaw, 0], size=[r, L, r])
    ex, ez = x + dx * (L + 0.6), z + dz * (L + 0.6)
    add(name=name + "_Fall", type="box", material="toxic", position=[round(ex, 2), FLUID, round(ez, 2)], rotation=[0, yaw, 0], size=[r * 0.8, y - FLUID - r / 2 + 0.4, 1.0])
for nm, (sx, sz) in {"NE": (1, -1), "NW": (-1, -1), "SE": (1, 1), "SW": (-1, 1)}.items():
    pipe(f"Pipe_{nm}_01", sx * (A - 1), sz * (A - 1), math.degrees(math.atan2(-sx, -sz)))
for nm, (x, z, yaw) in {"West": (-A, 12, 90), "East": (A, -12, 270), "North": (12, -A, 0), "South": (-12, A, 180)}.items():
    pipe(f"Pipe_{nm}_01", x, z, yaw, L=8, y=9.5, r=2.4)
for nm, (x, z, yaw, L) in {"North": (-A + 4, -A + 4.6, 90, 2 * A - 8), "South": (-A + 4, A - 4.6, 90, 2 * A - 8),
                           "West": (-A + 4.6, A - 4, 180, 2 * A - 8), "East": (A - 4.6, A - 4, 180, 2 * A - 8)}.items():
    add(name=f"PipeRun_{nm}_01", type="cylinder", sections=8, material="pipe", position=[x, 2.4, z], rotation=[90, yaw, 0], size=[1.4, L, 1.4])

# --- background industrial blocks outside the walls (silhouette only)
for k, (x, z, w, h) in enumerate([(-30, -50, 10, 24), (0, -52, 14, 30), (28, -48, 9, 20), (-50, -10, 9, 22), (50, 12, 10, 26),
                                 (-48, 30, 8, 18), (30, 50, 12, 22), (-10, 50, 9, 16)]):
    add(name=f"Background_Block_{k + 1:02d}", type="box", material="backdrop_metal", position=[x, 0, z], size=[w, h, w])

objs = [o for o in objs if o]
for o in objs:
    for k in ("position", "size", "rotation"):
        if k in o: o[k] = [round(float(v), 2) for v in o[k]]
mats = {  # Stage 1 PBR library (pipeline/materials.py); art direction from the concept: charcoal metal, grey decks, red/white lights
    "metal_dark": {"type": "industrial_metal", "color": [0.24, 0.25, 0.25], "tile_m": 4.0, "wear": 0.5, "bevel": 0.12},
    "edge_trim": {"type": "trim_light", "color": [0.19, 0.2, 0.2], "tile_m": 1.2, "bevel": 0.05, "accent": [1.0, 0.1, 0.06], "emissive": [1.0, 1.0, 1.0]},
    "metal_grate": {"type": "grating", "color": [0.3, 0.31, 0.3], "tile_m": 2.0},
    "concrete_dark": {"type": "machinery_panel", "color": [0.23, 0.24, 0.24], "tile_m": 4.0, "bevel": 0.1, "accent": [1.0, 0.12, 0.08], "emissive": [1.0, 1.0, 1.0]},
    "floor_plate": {"type": "scifi_floor", "color": [0.42, 0.41, 0.39], "tile_m": 4.0, "wear": 0.5},
    "pipe": {"type": "pipe", "color": [0.24, 0.27, 0.26], "tile_m": 2.5},
    "toxic": {"type": "toxic", "color": [0.5, 1.0, 0.1], "tile_m": 6.0, "emissive": [0.55, 1.0, 0.12]},
    "glow_strip": {"type": "glow", "color": [0.55, 1.0, 0.2], "tile_m": 2.0, "emissive": [0.6, 1.0, 0.25]},
    "red_panel": {"type": "banner", "color": [0.8, 0.1, 0.08], "tile_m": 2.0, "emissive": [1.0, 0.3, 0.25]},
    "backdrop_metal": {"type": "industrial_metal", "color": [0.18, 0.2, 0.19], "tile_m": 8.0, "res": 128, "bevel": 0.3},  # distant: low res
}
walk = [dict(min=[x - w / 2, z - d / 2], max=[x + w / 2, z + d / 2], y=y) for x, z, w, d, y in
        [(0, 0, 22, 22, DECK)] + [(sx * MID, sz * MID, 12, 12, DECK) for sx, sz in ((0, -1), (0, 1), (-1, 0), (1, 0))] +
        [(sx * D, sz * D, 10, 10, LOW) for sx, sz in ((1, -1), (-1, -1), (1, 1), (-1, 1))]]
L = dict(version=1, units="metres, y-up; position = centre of object's base, in parent space; rotation = degrees XYZ",
         source="toxic_arena_concept.png (hand-authored from TOP DOWN LAYOUT + SIDE VIEW)", sky_color=[0.07, 0.1, 0.08],
         spawn=dict(position=[0, DECK, MID], yaw_deg=0), hazards=["HazardFluid"],
         effects=[  # Stage 4 demo (runtime effects; the GLB keeps only static emissive)
             dict(id="Toxic_Surface", type="liquid_surface", target="HazardFluid", scroll=[0.03, 0.015], swirl=0.03, pulse_speed=0.2, pulse_amount=0.18),
             dict(id="Toxic_Falls", type="liquid_flow", targets_glob="Pipe_*_01_Fall", speed=3.0),
             dict(id="Toxic_Bubbles", type="bubbles", area_from="HazardFluid", rate=45),
             dict(id="Fall_Splash", type="splash", at_targets_glob="Pipe_*_01_Fall", anchor="bottom"),
             dict(id="Fall_Steam", type="steam", at_targets_glob="Pipe_*_01_Fall", anchor="bottom"),
             dict(id="Trim_Pulse", type="pulse_light", target_material="edge_trim", speed=0.35, amount=0.35),
             dict(id="Tower_Glow_Pulse", type="pulse_light", target_material="glow_strip", speed=0.9, amount=0.45),
             dict(id="Machinery_Flicker", type="flicker", target_material="concrete_dark", rate=6, amount=0.2),
             dict(id="Tower_Sparks", type="sparks", positions=[[3.7, DECK + 0.4, 3.7], [-3.7, DECK + 0.4, -3.7], [-A + 1, 9.5, 12], [A - 1, 9.5, -12]]),
             dict(id="Toxic_Spores", type="ambient_particles", area=[-A, FLUID, -A, A, 16, A], count=260),
             dict(id="Toxic_Mist", type="fog_sheet", area_from="HazardFluid", height=0.5, opacity=0.32),
             dict(id="Factory_Smoke", type="smoke", at_background="factory_chimneys"),
             dict(id="Sky_Drift", type="sky_drift", speed_deg_s=0.25),
         ],
         environment=dict(  # Stage 2 demo: background only (playable geometry/collision untouched)
             quality="balanced", horizon_distance=460,
             sky=dict(preset="industrial_smog"),
             atmosphere=dict(fog_start=60, height_fog=dict(height=2.5, density=0.15)),
             background=[
                 dict(id="Ground", type="ground", radius=[0, 470], flat_radius=60, rise=16, roughness=5),
                 dict(id="Mountains_Far", type="mountain_ring", radius=430, depth=70, height=[70, 160], fade=0.55, seed=3),
                 dict(id="Mountains_Near", type="mountain_ring", radius=290, depth=45, height=[18, 55], fade=0.3, seed=8, frequency=3.5, sharpness=2.2),
                 dict(id="Spires", type="spires", radius=[95, 210], count=16, height=[22, 65], fade=0.15, seed=5),
                 dict(id="Skyline_North", type="skyline", radius=250, azimuth_deg=[-55, 40], count=26, height=[18, 60], fade=0.35, glow=[0.45, 1.0, 0.25], lit=0.12),
                 dict(id="Factory_NE", type="factory", azimuth_deg=48, distance=165, scale=1.1, seed=1, glow=[0.45, 1.0, 0.25], fade=0.12),
                 dict(id="Factory_E", type="factory", azimuth_deg=105, distance=200, scale=0.9, seed=2, glow=[0.45, 1.0, 0.25], fade=0.18),
                 dict(id="Factory_SW", type="factory", azimuth_deg=215, distance=175, scale=1.0, seed=3, glow=[1.0, 0.25, 0.12], fade=0.15),
                 dict(id="Factory_W", type="factory", azimuth_deg=290, distance=190, scale=1.2, seed=4, glow=[0.45, 1.0, 0.25], fade=0.18),
             ]),
         bounds=dict(min=[-A - 4, 0, -A - 4], max=[A + 4, 20, A + 4]), walkable=walk, materials=mats, objects=objs)
os.makedirs(OUT, exist_ok=True)
json.dump(L, open(os.path.join(OUT, "level.json"), "w"), indent=1)
print(len(objs), "objects ->", OUT)
