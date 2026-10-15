"""Stage 7: reusable procedural architecture modules for the scene-spec generator (spec_to_level.py).

Every module appends NAMED level.json objects (group + children) through a Ctx, using MATERIAL ROLES (deck, wall,
structure, trim, grate, pipe, hazard, glow, accent, ...) that the theme palette (THEMES) turns into Stage 1 PBR /
legacy materials. Objects carry "gen" (the scene-spec element id) and "source" ("visible" | "inferred") so edits and
regeneration can tell generated parts from manual ones. Nothing here invents gameplay numbers: heights/sizes come from
the spec, clearances from config/gameplay.json.

Modules
  arena_floor, arena_walls (rect / octagon / circle boundary; openings), walkway ring
  platform: industrial_pillar | stone_plinth | plain   (rect | octagon | circle)
  connection: bridge | catwalk | ramp | stairs | jump  (auto picks by height difference / gap / max slope)
  structures: tower, building, house (timber/stone/plaster, gable/hip/flat roof), stone_tower (battlements, spire),
              fountain, gate / arch (round or square), wall, machinery, tank, pillar, lamp, crates, rocks, tree, banner
  pipes: outlet (wall pipe + flange + optional pour/fall), run (polyline with flanges)
Extend: add a function and register it in STRUCTURES / PLATFORM_STYLES; keep it closed-mesh and named.
"""
import hashlib, math
import numpy as np
import prefabs

# ------------------------------------------------------------------ themes: material roles + defaults per art direction
_IND = {
    "deck": {"type": "scifi_floor", "color": [0.42, 0.41, 0.39], "tile_m": 4.0, "wear": 0.5},
    "structure": {"type": "machinery_panel", "color": [0.23, 0.24, 0.24], "tile_m": 4.0, "bevel": 0.1, "accent": [1.0, 0.12, 0.08], "emissive": [1.0, 1.0, 1.0]},
    "structure_b": {"type": "industrial_metal", "color": [0.2, 0.21, 0.21], "tile_m": 4.0, "wear": 0.65, "bevel": 0.06},
    "wall": {"type": "industrial_metal", "color": [0.24, 0.25, 0.25], "tile_m": 4.0, "wear": 0.5, "bevel": 0.12},
    "trim": {"type": "trim_light", "color": [0.19, 0.2, 0.2], "tile_m": 1.2, "bevel": 0.05, "accent": [1.0, 0.1, 0.06], "emissive": [1.0, 1.0, 1.0]},
    "grate": {"type": "grating", "color": [0.3, 0.31, 0.3], "tile_m": 2.0},
    "frame": {"type": "industrial_metal", "color": [0.2, 0.2, 0.2], "tile_m": 3.0, "bevel": 0.03},
    "rail": {"type": "painted_metal", "color": [0.55, 0.45, 0.12], "tile_m": 2.0, "res": 256},
    "pipe": {"type": "pipe", "color": [0.24, 0.27, 0.26], "tile_m": 2.5},
    "hazard": {"type": "toxic", "color": [0.5, 1.0, 0.1], "tile_m": 6.0, "emissive": [0.55, 1.0, 0.12]},
    "glow": {"type": "glow", "color": [0.55, 1.0, 0.2], "tile_m": 2.0, "emissive": [0.6, 1.0, 0.25]},
    "accent": {"type": "banner", "color": [0.8, 0.1, 0.08], "tile_m": 2.0, "emissive": [1.0, 0.3, 0.25]},
    "machine": {"type": "machinery_panel", "color": [0.22, 0.23, 0.23], "tile_m": 2.0, "accent": [1.0, 0.55, 0.1], "emissive": [1, 1, 1]},
    "stripe": {"type": "chevron", "color": [0.92, 0.68, 0.1], "tile_m": 1.5, "res": 256},
    "ground": {"type": "concrete", "color": [0.3, 0.3, 0.29], "tile_m": 4.0},
    "rock": {"type": "rock", "color": [0.3, 0.29, 0.27], "tile_m": 6.0, "res": 256},
    "foliage": {"type": "grass", "color": [0.25, 0.35, 0.18], "tile_m": 3.0, "res": 128},
    "water": {"type": "toxic", "color": [0.25, 0.45, 0.5], "tile_m": 4.0},
    "window": {"type": "glow", "color": [0.9, 0.75, 0.4], "tile_m": 1.0, "emissive": [0.9, 0.7, 0.35]},
    "backdrop": {"type": "industrial_metal", "color": [0.18, 0.2, 0.19], "tile_m": 8.0, "res": 128, "bevel": 0.3},
}
_TOWN = {
    "ground": {"type": "cobblestone", "color": [0.56, 0.55, 0.53], "tile_m": 1.4},
    "deck": {"type": "stone_brick", "color": [0.7, 0.67, 0.6], "tile_m": 3.0},
    "structure": {"type": "stone_brick", "color": [0.55, 0.53, 0.48], "tile_m": 3.0},
    "structure_b": {"type": "stone_brick", "color": [0.48, 0.46, 0.42], "tile_m": 3.0},
    "wall": {"type": "stone_brick", "color": [0.66, 0.63, 0.56], "tile_m": 3.0},
    "stone": {"type": "stone_brick", "color": [0.72, 0.68, 0.6], "tile_m": 3.0},
    "trim": {"type": "stone_brick", "color": [0.5, 0.48, 0.44], "tile_m": 2.0},
    "plaster": {"type": "plaster", "color": [0.9, 0.84, 0.7], "tile_m": 2.0},
    "timber": {"type": "wood", "color": [0.3, 0.2, 0.13], "tile_m": 2.0},
    "roof": {"type": "roof_tiles", "color": [0.58, 0.32, 0.24], "tile_m": 2.0},
    "roof_slate": {"type": "roof_slate", "color": [0.32, 0.34, 0.38], "tile_m": 2.0},
    "window": {"type": "window", "color": [0.75, 0.75, 0.7], "tile_m": 1.0},
    "door": {"type": "door_wood", "color": [0.45, 0.3, 0.18], "tile_m": 1.0},
    "grate": {"type": "wood", "color": [0.4, 0.3, 0.2], "tile_m": 2.0},
    "frame": {"type": "wood", "color": [0.28, 0.2, 0.14], "tile_m": 2.0},
    "rail": {"type": "wood", "color": [0.3, 0.22, 0.15], "tile_m": 2.0},
    "pipe": {"type": "painted_metal", "color": [0.2, 0.2, 0.22], "tile_m": 2.0},
    "machine": {"type": "painted_metal", "color": [0.25, 0.25, 0.27], "tile_m": 2.0},
    "water": {"type": "water", "color": [0.45, 0.62, 0.7], "tile_m": 2.0},
    "hazard": {"type": "water", "color": [0.2, 0.35, 0.45], "tile_m": 3.0},
    "glow": {"type": "glow", "color": [1.0, 0.8, 0.45], "tile_m": 1.0, "emissive": [1.0, 0.75, 0.4]},
    "accent": {"type": "banner", "color": [0.7, 0.12, 0.1], "tile_m": 2.0},
    "rock": {"type": "rock", "color": [0.45, 0.43, 0.4], "tile_m": 6.0, "res": 256},
    "foliage": {"type": "grass", "color": [0.3, 0.42, 0.2], "tile_m": 3.0, "res": 128},
    "backdrop": {"type": "plaster", "color": [0.7, 0.66, 0.58], "tile_m": 6.0, "res": 128},
}
THEMES = {
    "industrial": dict(roles=_IND, platform_style="industrial_pillar", wall_style="industrial", sky="industrial_smog", ambient="spores",
                       background=dict(mountains="both", factories=4, skyline=True, spires=True)),
    "toxic_industrial": dict(roles=_IND, platform_style="industrial_pillar", wall_style="industrial", sky="industrial_smog", ambient="spores",
                             background=dict(mountains="both", factories=4, skyline=True, spires=True)),
    "scifi": dict(roles=_IND, platform_style="industrial_pillar", wall_style="industrial", sky="alien", ambient="spores",
                  background=dict(mountains="both", factories=2, skyline=True, spires=True)),
    "medieval_town": dict(roles=_TOWN, platform_style="stone_plinth", wall_style="stone", sky="clear_day", ambient="dust",
                          background=dict(mountains="both", factories=0, skyline=False, spires=False, town=True, ground_type="grass", ground_color=[0.3, 0.36, 0.22])),
    "ruins": dict(roles=dict(_TOWN, ground={"type": "dirt", "color": [0.42, 0.38, 0.32], "tile_m": 4.0}), platform_style="stone_plinth", wall_style="stone",
                  sky="overcast", ambient="dust", background=dict(mountains="both", factories=0, skyline=False, spires=True)),
}
def _with(base, **over):
    r = {k: dict(v) for k, v in base.items()}
    for k, v in over.items(): r[k] = dict(r.get(k, {}), **v)
    return r


# Stage 9 art directions (biome = terrain layer preset, style = scatter / natural prop look)
THEMES.update({
    "futuristic_city": dict(roles=_with(_IND, wall={"type": "concrete", "color": [0.52, 0.54, 0.57], "tile_m": 6.0},
                                        structure={"type": "machinery_panel", "color": [0.26, 0.28, 0.32], "accent": [0.2, 0.8, 1.0]},
                                        trim={"type": "trim_light", "color": [0.2, 0.22, 0.25], "accent": [0.2, 0.85, 1.0]},
                                        glow={"type": "glow", "color": [0.4, 0.85, 1.0], "emissive": [0.35, 0.8, 1.0]},
                                        accent={"type": "banner", "color": [0.15, 0.45, 0.85], "emissive": [0.3, 0.6, 1.0]},
                                        window={"type": "glow", "color": [0.55, 0.75, 0.9], "emissive": [0.4, 0.6, 0.8]},
                                        deck={"type": "concrete", "color": [0.5, 0.5, 0.5], "tile_m": 4.0}, ground={"type": "concrete", "color": [0.42, 0.42, 0.42]},
                                        hazard={"type": "water", "color": [0.2, 0.3, 0.4], "tile_m": 6.0}, water={"type": "water", "color": [0.25, 0.35, 0.42]}),
                            platform_style="industrial_pillar", wall_style="industrial", sky="sunset", ambient="none", biome="urban", style="stylised_scifi",
                            background=dict(mountains="far", factories=0, skyline=True, spires=False)),
    "desert": dict(roles=_with(_TOWN, wall={"type": "stone_brick", "color": [0.78, 0.64, 0.46]}, structure={"type": "stone_brick", "color": [0.7, 0.56, 0.4]},
                               stone={"type": "stone_brick", "color": [0.8, 0.66, 0.48]}, rock={"type": "rock", "color": [0.66, 0.45, 0.3], "tile_m": 8.0},
                               ground={"type": "sand", "color": [0.82, 0.67, 0.45], "tile_m": 5.0}, foliage={"type": "grass", "color": [0.5, 0.48, 0.28]}),
                   platform_style="stone_plinth", wall_style="stone", sky="clear_day", ambient="dust", biome="desert", style="realistic",
                   background=dict(mountains="both", factories=0, skyline=False, spires=True)),
    "alpine": dict(roles=_with(_TOWN, rock={"type": "rock", "color": [0.47, 0.47, 0.5], "tile_m": 8.0}), platform_style="stone_plinth", wall_style="stone",
                   sky="overcast", ambient="snow", biome="alpine", style="realistic", background=dict(mountains="both", factories=0, skyline=False, spires=False)),
    "fantasy_forest": dict(roles=_with(_TOWN, foliage={"type": "moss", "color": [0.28, 0.48, 0.22]}, rock={"type": "rock", "color": [0.46, 0.44, 0.5], "tile_m": 8.0},
                                       glow={"type": "glow", "color": [0.7, 0.5, 1.0], "emissive": [0.6, 0.4, 1.0]}),
                           platform_style="stone_plinth", wall_style="stone", sky="sunrise", ambient="spores", biome="fantasy", style="fantasy",
                           background=dict(mountains="both", factories=0, skyline=False, spires=True)),
    "alien": dict(roles=_with(_IND, rock={"type": "rock", "color": [0.33, 0.28, 0.4], "tile_m": 8.0}, glow={"type": "glow", "color": [0.3, 0.95, 1.0], "emissive": [0.25, 0.9, 1.0]},
                              hazard={"type": "toxic", "color": [0.3, 0.9, 0.9], "emissive": [0.25, 0.85, 0.9]}),
                  platform_style="industrial_pillar", wall_style="industrial", sky="alien", ambient="spores", biome="alien", style="stylised_scifi",
                  background=dict(mountains="both", factories=0, skyline=False, spires=True)),
    "post_apocalyptic": dict(roles=_with(_IND, wall={"type": "damaged_metal", "color": [0.3, 0.27, 0.24], "wear": 0.9}, structure={"type": "damaged_metal", "color": [0.28, 0.25, 0.22]},
                                         deck={"type": "concrete", "color": [0.38, 0.37, 0.35], "wear": 0.8}, ground={"type": "dirt", "color": [0.4, 0.35, 0.28]}),
                             platform_style="industrial_pillar", wall_style="industrial", sky="overcast", ambient="dust", biome="wasteland", style="post_apocalyptic",
                             background=dict(mountains="both", factories=2, skyline=True, spires=False)),
    "cartoon": dict(roles=_with(_TOWN, wall={"type": "plaster", "color": [0.95, 0.85, 0.65]}, roof={"type": "roof_tiles", "color": [0.85, 0.3, 0.25]},
                                rock={"type": "rock", "color": [0.6, 0.56, 0.52], "res": 128}, foliage={"type": "grass", "color": [0.35, 0.65, 0.2], "res": 128}),
                    platform_style="stone_plinth", wall_style="stone", sky="clear_day", ambient="none", biome="cartoon", style="cartoon",
                    background=dict(mountains="both", factories=0, skyline=False, spires=False)),
})
for _k, _b, _s in (("industrial", "industrial", "realistic"), ("toxic_industrial", "industrial", "post_apocalyptic"), ("scifi", "industrial", "stylised_scifi"),
                   ("medieval_town", "temperate", "realistic"), ("ruins", "wasteland", "realistic")):
    THEMES[_k].setdefault("biome", _b); THEMES[_k].setdefault("style", _s)
VARIANT_ROLES = ("wall", "structure", "deck", "plaster")
CORROSION = {"type": "corrosion", "color": [1.0, 1.0, 1.0], "tile_m": 4.0, "res": 128, "toon": True, "emissive": [1.0, 1.0, 1.0], "cutout": 0.5}
FALLBACK = {"belt": "grate", "scan": "glow_yellow", "laser": "glow", "glow_dim": "glow", "glow_yellow": "glow", "glass_clear": "glass", "bigscreen": "glow", "tv_casing": "structure_b", "screen": "glow", "screen_b": "glow", "ceiling": "frame", "ceiling_b": "frame", "lamp": "glow", "glass": "hazard", "wall_works": "wall", "wall_slimed": "wall", "foundation": "structure_b", "timber": "frame", "stone": "structure", "plaster": "wall", "roof": "structure_b", "roof_slate": "structure_b", "door": "structure_b",
            "window": "glow", "foliage": "rock", "water": "hazard", "machine": "structure_b", "backdrop": "wall", "structure_b": "structure",
            "frame": "structure_b", "rail": "frame", "grate": "deck", "trim": "structure_b", "accent": "trim", "glow": "accent", "pipe": "frame",
            "hazard": "water", "fall": "water", "stripe": "trim", "ground": "deck", "deck": "ground", "wall": "structure", "structure": "wall", "rock": "structure"}


def role_material(theme, role):
    """Material definition for a role (variants '<role>_v2' get a tint/wear shift; missing roles fall back sensibly)."""
    roles = THEMES[theme]["roles"]; base = role[:-3] if role.endswith("_v2") else role; seen = set()
    if base == "void" and "void" not in roles: return {"type": "concrete", "color": [0.0, 0.0, 0.0], "tile_m": 4.0}  # pure black (bottomless pits)
    if base == "corrosion" and "corrosion" not in roles: return dict(CORROSION)  # Stage 28: same cut-out band in every theme
    r = base
    while r not in roles and r not in seen: seen.add(r); r = FALLBACK.get(r, "wall")
    m = dict(roles.get(r, _IND["wall"]))
    if base != role:  # variant: slightly different tint + wear (shared material, breaks repetition)
        m["color"] = [round(min(1, c * f), 3) for c, f in zip(m["color"], (0.92, 0.95, 0.9))]; m["wear"] = min(1.0, m.get("wear", 0.5) + 0.2)
    return m


def _h(s):
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


class Ctx:
    """Collects objects + bookkeeping while modules run."""

    def __init__(self, spec, G):
        self.spec, self.G = spec, G; self.theme = THEMES[spec.get("theme", "industrial")]
        self.objects, self.names, self.roles = [], set(), set(); self.walkable, self.hazards, self.pours = [], [], []
        self.detail = {"low": 0, "medium": 1, "high": 2}[spec.get("detail", "medium")]
        self.variation = spec.get("materials", {}).get("variation", True); self.notes = []; self.platforms = {}; self.element = None
        self.exits = []  # level transit triggers (elevator shafts, portals) -> level.json "exits"
        self.entrances = []  # arrivals from the previous level (elevator car coming down) -> level.json "entrances"
        self.relations, self.floor_of, self.landings, self.pending_covers = [], {}, [], []  # Stage 8: scene graph + deferred cover

    def role(self, r, key=None):
        if self.variation and r in VARIANT_ROLES and key and _h(key) % 2: r = r + "_v2"
        self.roles.add(r); return r

    def rel(self, type_, a, b, **kw):
        self.relations.append(dict(type=type_, a=a, b=b, **kw))

    def add(self, name, typ, pos=(0, 0, 0), size=None, mat=None, parent=None, rot=(0, 0, 0), vkey=None, **kw):
        base, k = name, 2
        while name in self.names: name = f"{base}_{k}"; k += 1
        o = dict(name=name, type=typ, position=[round(float(v), 3) for v in pos], rotation=[round(float(v), 2) for v in rot])
        if parent: o["parent"] = parent
        if size is not None: o["size"] = [round(max(float(v), 0.0), 3) for v in size]
        if mat: o["material"] = self.role(mat, vkey or (self.element[0] if self.element else name))
        o.update(kw)
        if self.element: o["gen"], o["source"] = self.element[0], self.element[1]
        self.names.add(name); self.objects.append(o); return name


def yaw_to(dx, dz):
    """Yaw (deg) that turns local +z towards world direction (dx, dz)."""
    return math.degrees(math.atan2(dx, dz))


def local(x, z, yaw):
    """Rotate a local x/z offset by yaw (deg) - same convention as the builder (Ry)."""
    a = math.radians(yaw); return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


# ------------------------------------------------------------------ platforms
def footprint_edge(p, dx, dz):
    """Distance from a platform centre to the edge of its WALKING SURFACE (floor plate incl. overhang) in direction (dx, dz)."""
    w, d = p["size"]; x = p.get("_plate", 0.0); w, d = w + x, d + x; R = min(w, d) / 2
    if p.get("shape") in ("octagon", "circle"):  # regular polygon, circumradius R, flats facing the axes (rotated in _solid)
        n = 8 if p.get("shape") == "octagon" else 24; k = math.pi / n; phi = math.atan2(dz, dx)
        a = ((phi + k) % (2 * k)) - k; return R * math.cos(k) / math.cos(a)
    return min(w / 2 / max(abs(dx), 1e-9), d / 2 / max(abs(dz), 1e-9))


def footprint_poly(p, inset=0.0):
    """2D outline (world x, z) of a platform top, matching the built mesh (rect / octagon / circle rotated flats-to-axes)."""
    (cx, cz), (w, d) = p["center"], p["size"]; x = p.get("_plate", 0.0); w, d = w + x, d + x
    if p.get("shape") in ("octagon", "circle"):
        n = 8 if p.get("shape") == "octagon" else 24; R = min(w, d) / 2 - inset / math.cos(math.pi / n)
        return [(cx + R * math.cos(2 * math.pi * k / n + math.pi / n), cz + R * math.sin(2 * math.pi * k / n + math.pi / n)) for k in range(n)]
    return [(cx - w / 2 + inset, cz - d / 2 + inset), (cx + w / 2 - inset, cz - d / 2 + inset), (cx + w / 2 - inset, cz + d / 2 - inset), (cx - w / 2 + inset, cz + d / 2 - inset)]


def _inside(poly, x, z):
    c = False
    for (x1, z1), (x2, z2) in zip(poly, poly[1:] + poly[:1]):
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1): c = not c
    return c


def support_depth(p, e, t, width):
    """How far a connector end at point e (heading into platform p along unit t) must reach so its whole width rests on
    the platform: 0 for a flat edge, ~width/2 at a 45° corner. None if it never does within 2*width."""
    poly = footprint_poly(p, 0.1); v = (-t[1], t[0])
    for k in range(0, int(width * 40) + 1):
        x = k * 0.05
        if all(_inside(poly, e[0] + v[0] * s + t[0] * x, e[1] + v[1] * s + t[1] * x) for s in (-width / 2, 0, width / 2)): return x
    return None


def platform(ctx, p, base_y, centre):
    style = p.get("style") or ctx.theme["platform_style"]; return PLATFORM_STYLES[style](ctx, p, base_y, centre)


def _solid(ctx, name, parent, shape, w, h, d, y, mat, extra=0.0, vkey=None):
    if shape in ("octagon", "circle"):
        n = 8 if shape == "octagon" else 24  # rotated half a segment so flat faces (not corners) face the axes / bridges
        return ctx.add(name, "cylinder", [0, y, 0], [w + extra, h, d + extra], mat, parent, rot=[0, 180 / n, 0], vkey=vkey, sections=n)
    return ctx.add(name, "box", [0, y, 0], [w + extra, h, d + extra], mat, parent, vkey=vkey)


def industrial_pillar(ctx, p, base_y, centre):
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); h = max(0.3, top - 0.3 - base_y)
    _solid(ctx, n + "_Base", g, shape, w, h, d, base_y, "structure")
    ctx.floor_of[n] = _solid(ctx, n + "_Floor", g, shape, w, 0.3, d, top - 0.3, "deck", 0.3, vkey=f"floor@{top:.2f}"); p["_plate"] = 0.3
    if h > 1.6: _solid(ctx, n + "_Trim", g, shape, w, 0.6, d, top - 1.1, "trim", 0.5)
    tx, tz = centre[0] - cx, centre[1] - cz; L = math.hypot(tx, tz) or 1.0
    if shape == "rect" and ctx.detail >= 1 and h > 3:  # corner ribs break up the box silhouette
        for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            ctx.add(f"{n}_Rib_{i + 1:02d}", "box", [sx * (w / 2 - 0.15), base_y, sz * (d / 2 - 0.15)], [0.8, h - 1.4, 0.8], "structure_b", g)
    if p.get("lights", True) and h > 3.5:  # light panels on the faces that look at the arena centre
        faces = []
        if abs(tx) > 0.2 * L: faces.append(("X", math.copysign(1, tx)))
        if abs(tz) > 0.2 * L: faces.append(("Z", math.copysign(1, tz)))
        for k, (ax, s) in enumerate(faces or [("Z", 1)]):
            e = footprint_edge(p, 1 if ax == "X" else 0, 1 if ax == "Z" else 0) + 0.03
            pos = [s * e, top - 3.2, 0] if ax == "X" else [0, top - 3.2, s * e]; yaw = (90 if s > 0 else 270) if ax == "X" else (0 if s > 0 else 180)
            ctx.add(f"{n}_Light_{k + 1:02d}", "panel", pos, [1.4, 1.8, 0], "accent", g, [0, yaw, 0])
            if ctx.detail >= 1 and h > 5:
                for side in (-1, 1):
                    off = side * 1.3; gp = [pos[0], base_y + 1.0, pos[2] + off] if ax == "X" else [pos[0] + off, base_y + 1.0, pos[2]]
                    ctx.add(f"{n}_Glow_{k + 1:02d}{'LR'[side > 0]}", "panel", gp, [0.3, max(1.0, h - 5.5), 0], "glow", g, [0, yaw, 0])
    _cover(ctx, p, g, top, "structure_b")
    ctx.walkable.append(_walk_rect(p, top))


def stone_plinth(ctx, p, base_y, centre):
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); h = max(0.3, top - 0.4 - base_y)
    _solid(ctx, n + "_Base", g, shape, w, h, d, base_y, "structure")
    ctx.floor_of[n] = _solid(ctx, n + "_Cap", g, shape, w, 0.4, d, top - 0.4, "deck", 0.3, vkey=f"floor@{top:.2f}"); p["_plate"] = 0.3
    if h > 1.5 and ctx.detail >= 1: _solid(ctx, n + "_Plinth", g, shape, w, 0.5, d, base_y, "trim", 0.4)
    _cover(ctx, p, g, top, "structure")
    ctx.walkable.append(_walk_rect(p, top))


def plain(ctx, p, base_y, centre):
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); ctx.floor_of[n] = _solid(ctx, n + "_Base", g, shape, w, max(0.3, top - base_y), d, base_y, p.get("material", "deck"))
    _cover(ctx, p, g, top, "structure_b"); ctx.walkable.append(_walk_rect(p, top))


def _cover(ctx, p, g, top, mat):
    ctx.pending_covers.append((p, g, top, mat, ctx.element))  # placed after connections so cover never blocks a landing


def place_covers(ctx):
    """Cover crates on platforms, avoiding connection landings, structures and edges (Stage 8)."""
    for p, g, top, mat, el in ctx.pending_covers:
        ctx.element = el; w, d = p["size"]; (pcx, pcz) = p["center"]; ch = ctx.G["design"]["cover_height"]; want = min(int(p.get("cover", 0)), 4)
        spots = [(-w / 4, -d / 4), (w / 4, d / 4), (w / 4, -d / 4), (-w / 4, d / 4), (0, -d / 3), (0, d / 3), (-w / 3, 0), (w / 3, 0)]
        spots += [(w * 0.33 * math.cos(math.radians(a)), d * 0.33 * math.sin(math.radians(a))) for a in (22.5, 202.5, 112.5, 292.5, 67.5, 247.5, 157.5, 337.5)]
        k = 0; placed = []
        for sx, sz in spots:
            if k >= want: break
            wx, wz = pcx + sx, pcz + sz; s = 1.6 if k % 2 == 0 else 2.0; dd = 1.2 if k % 2 else 1.6
            if any(math.hypot(wx - x, wz - z) < r + s / 2 + 0.4 for x, z, r in ctx.landings + getattr(ctx, "platform_blocks", [])): continue
            if p.get("shape") in ("octagon", "circle") and math.hypot(sx, sz) > min(w, d) / 2 * 0.8: continue
            if any(abs(sx - qx) < (s + qs) / 2 + 0.4 and abs(sz - qz) < (dd + qd) / 2 + 0.4 for qx, qz, qs, qd in placed): continue  # Stage 36: crates never inside each other
            ctx.add(f"{p['id']}_Cover_{k + 1:02d}", "box", [round(sx, 2), top, round(sz, 2)], [s, ch, dd], mat, g); k += 1; placed.append((sx, sz, s, dd))
        if k < want: ctx.notes.append(f"{p['id']}: {want - k} cover crate(s) dropped - no free spot clear of landings")


def _walk_rect(p, top):
    (cx, cz), (w, d) = p["center"], p["size"]; k = 0.7 if p.get("shape") in ("octagon", "circle") else 1.0
    return dict(name=p["id"], min=[cx - w * k / 2, cz - d * k / 2], max=[cx + w * k / 2, cz + d * k / 2], y=p["top"])


def sky_pylon(ctx, p, base_y, centre):
    """Raised / floating deck (Stage 9): floor plate, lit trim band, deck body, a tapered underframe and a slimmer
    support column down to base_y (ground, sea bed). Reads as a platform held up by machinery, not a solid tower."""
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); sec = {"octagon": 8, "circle": 24}.get(shape, 0)
    ctx.floor_of[n] = _solid(ctx, n + "_Floor", g, shape, w, 0.3, d, top - 0.3, "deck", 0.3, vkey=f"floor@{top:.2f}"); p["_plate"] = 0.3
    _solid(ctx, n + "_Trim", g, shape, w, 0.7, d, top - 1.0, "trim", 0.2)
    _solid(ctx, n + "_Body", g, shape, w, 1.3, d, top - 2.3, "structure")
    fh = min(8.0, max(2.0, (top - 2.3 - base_y) * 0.4)); k = p.get("taper", 0.45)
    ctx.add(n + "_Underframe", "frustum", [0, top - 2.3 - fh, 0], [w, fh + 0.01, d], "structure_b", g, sections=sec, bottom_scale=k)
    ch = top - 2.3 - fh - base_y
    if ch > 0.3: _solid(ctx, n + "_Column", g, shape, w * k * 0.9, ch + 0.02, d * k * 0.9, base_y, "structure_b")
    if p.get("underside", True) and ctx.detail >= 1:  # radial ribs under the deck body + collar bands on the column (shared materials)
        nr = {"octagon": 8, "circle": 8}.get(shape, 4); rw, rd = (w, d) if not sec else (w * 0.92, d * 0.92)
        for i in range(nr):
            a = 2 * math.pi * i / nr + (math.pi / nr if sec else 0); ca, sa = math.cos(a), math.sin(a)
            reach = (rw / 2 * abs(ca) + rd / 2 * abs(sa)) if not sec else rw / 2  # out to the body edge (rect: along the axis)
            L_ = max(0.5, reach * (1 - k) + 0.3); r0 = reach - L_ / 2 - 0.15
            ctx.add(f"{n}_Rib_{i + 1:02d}", "box", [ca * r0, top - 2.3 - fh * 0.55, sa * r0], [0.45, fh * 0.55 + 0.02, L_], "frame", g, [0, math.degrees(math.atan2(ca, sa)), 0])
        for j, f in enumerate((0.3, 0.75)):
            if ch > 12: _solid(ctx, f"{n}_Collar_{j + 1}", g, shape, w * k * 0.9 + 0.6, 0.8, d * k * 0.9 + 0.6, base_y + ch * f, "frame")
    _cover(ctx, p, g, top, "structure_b")
    ctx.walkable.append(_walk_rect(p, top))


PLATFORM_STYLES = dict(industrial_pillar=industrial_pillar, stone_plinth=stone_plinth, plain=plain, sky_pylon=sky_pylon)


def _rails(ctx, cid, g, width, z0, z1, y_at, inset=0.05, height=1.05, zs=None, spacing=1.6):
    """Both side railings of a connector as rail_run objects in its local frame (+z along it): post bases are ON the
    walking surface y_at(z), so they follow slopes; flat->slope->flat changes become polyline vertices (corner posts).
    zs: explicit post stations (stairs: tread centres, so no post stands on a riser edge); then posts only there."""
    zs = [z for z in (zs or [z0, z1]) if z0 - 1e-6 <= z <= z1 + 1e-6]
    if len(zs) < 2 or zs[-1] - zs[0] < 0.4: return
    ys = [y_at(z) for z in zs]
    for s, side in ((-1, "L"), (1, "R")):
        x = s * (width / 2 - inset); pts = [[round(x, 3), round(float(y), 3), round(float(z), 3)] for y, z in zip(ys, zs)]
        ctx.add(f"{cid}_Rail_{side}", "rail_run", [0, 0, 0], [round(math.hypot(zs[-1] - zs[0], ys[-1] - ys[0]), 3), height, 0.07], "rail", g,
                points=pts, post_spacing=spacing if len(zs) == 2 else 99.0)


# ------------------------------------------------------------------ connections
def connection(ctx, c, A, B, floor_y):
    """Bridge / ramp / stairs between the facing edges of platforms A and B (any angle). Stage 8 construction rules:
    exact polygon edges (octagon/circle flats), bridge decks 1 cm under the floors they overlap (no z-fighting),
    ramps/stairs meet the upper floor flush AT its edge and start on / dip under the lower floor, elevated pieces get
    supports, every end is recorded as a walkable_connection relation + landing (kept clear of cover)."""
    ax, az = A["center"]; bx, bz = B["center"]; dx, dz = bx - ax, bz - az; L = math.hypot(dx, dz) or 1.0; ux, uz = dx / L, dz / L
    ea, eb = footprint_edge(A, ux, uz), footprint_edge(B, -ux, -uz); gap = L - ea - eb
    lo, hi = (A, B) if A["top"] <= B["top"] else (B, A); dy = hi["top"] - lo["top"]
    P = ctx.G["player"]; kind = c.get("kind", "auto"); width = c.get("width", max(ctx.G["design"]["min_bridge_width"] + 0.5, 4.0))
    smax = min(P["max_slope_deg"], 35)
    if kind == "auto":
        kind = "bridge" if dy <= P["step_height"] else "ramp" if gap > 0 and math.degrees(math.atan2(dy, gap)) <= smax else "stairs"
    fa, fb = ctx.floor_of.get(A["id"], A["id"]), ctx.floor_of.get(B["id"], B["id"])
    if kind == "jump":
        ctx.rel("intentional_gap", A["id"], B["id"], note=f"jump link (gap {gap:.1f} m, dy {dy:.1f} m)", intentional=True)
        ctx.notes.append(f"{c['id']}: jump link {A['id']}->{B['id']} (gap {gap:.1f} m, dy {dy:.1f} m) - no geometry"); return
    if gap < 0.2 and kind in ("bridge", "catwalk"): return  # platforms touch
    ov = 0.3; width_ = width
    oa = max(ov, (support_depth(A, (ax + ux * ea, az + uz * ea), (-ux, -uz), width_) or 0) + 0.1)  # junction depth at corners / angled edges
    ob = max(ov, (support_depth(B, (bx - ux * eb, bz - uz * eb), (ux, uz), width_) or 0) + 0.1)
    pa = (ax + ux * (ea - oa), az + uz * (ea - oa)); pb = (bx - ux * (eb - ob), bz - uz * (eb - ob)); span = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
    edge = lambda p, t, e: (p["center"][0] + t[0] * e, p["center"][1] + t[1] * e)
    if kind in ("bridge", "catwalk"):
        y = min(A["top"], B["top"]) - 0.01; yaw = yaw_to(ux, uz)  # 1 cm under the floors it overlaps: no coplanar flicker
        g = ctx.add(c["id"], "group", [mid[0], 0, mid[1]], rot=[0, yaw, 0])  # local +z along the bridge (A -> B)
        deck = ctx.add(c["id"] + "_Deck", "box", [0, y - 0.4, 0], [width, 0.4, span], "grate", g, connector=True, axis="z")
        for s, side in ((-1, "L"), (1, "R")):
            ctx.add(f"{c['id']}_Beam_{side}", "ibeam", [s * (width / 2 - 0.3), y - 0.855, (oa - ob) / 2], [max(0.5, span - oa - ob), 0.45, 0.3], "frame", g, [0, 90, 0])
        if c.get("rails", kind == "catwalk"):
            _rails(ctx, c["id"], g, width, -span / 2 + oa + 0.3, span / 2 - ob - 0.3, lambda z: y)
        if c.get("lamp_posts"):  # Stage 57: warm lamps along one edge
            lamp_posts(ctx, c["id"], g, width, -span / 2 + oa + 0.6, span / 2 - ob - 0.6, y, int(c["lamp_posts"]), c.get("lamp_side", 1), (mid[0], mid[1]), yaw)
        if ctx.detail >= 1 and span > 3:  # transverse beams under the deck between the side I-beams (bridge underside)
            for i in range(max(1, int(span / 2.5))):
                z = -span / 2 + oa + (span - oa - ob) * (i + 0.5) / max(1, int(span / 2.5))
                ctx.add(f"{c['id']}_Cross_{i + 1:02d}", "box", [0, y - 0.7, z], [width - 0.6, 0.3, 0.25], "frame", g)
        if span > 10 and y - floor_y > 1.5:
            n = max(1, int(span / 9))
            for i in range(n):
                z = -span / 2 + span * (i + 1) / (n + 1)
                sup = pier(ctx, f"{c['id']}_Support_{i + 1:02d}", g, 0, floor_y, z, y - 0.37, width * 0.4, 0.8); ctx.rel("supported_by", deck, sup)
        ctx.rel("walkable_connection", deck, fa, a_anchor="end_a"); ctx.rel("walkable_connection", deck, fb, a_anchor="end_b")
        for p_, t in ((A, (ux, uz)), (B, (-ux, -uz))):
            e = footprint_edge(p_, *t); ctx.landings.append((p_["center"][0] + t[0] * (e - 1.0), p_["center"][1] + t[1] * (e - 1.0), width / 2))
        if abs(ux) < 0.05 or abs(uz) < 0.05:
            hw, hl = (width / 2, span / 2) if abs(ux) < 0.05 else (span / 2, width / 2)
            ctx.walkable.append(dict(name=c["id"], min=[mid[0] - hw, mid[1] - hl], max=[mid[0] + hw, mid[1] + hl], y=y))
        return
    # ramp / stairs: the high end meets the upper floor exactly at its edge; the low end starts on (or dips under) the lower floor
    toward = (ux, uz) if lo is A else (-ux, -uz); yaw = yaw_to(*toward)
    e_hi = footprint_edge(hi, -toward[0], -toward[1]); e_lo = footprint_edge(lo, *toward)
    hi_pt = edge(hi, (-toward[0], -toward[1]), e_hi - 0.05); lo_pt = edge(lo, toward, e_lo)
    dy = dy - 0.01  # top meets the upper floor 1 cm under its surface: overlap without coplanar flicker
    gap2 = math.hypot(hi_pt[0] - lo_pt[0], hi_pt[1] - lo_pt[1]); run = max(gap2, dy / math.tan(math.radians(smax)))
    flo, fhi = ctx.floor_of.get(lo["id"], lo["id"]), ctx.floor_of.get(hi["id"], hi["id"])
    if lo["top"] - floor_y > 1.5 and kind == "ramp":  # elevated: sloped bridge (tilted deck + beams + support), not a floating wedge
        slope = dy / run; ext = ov if run <= gap2 + 1e-6 else 0.0  # dip under the lower floor plate when spanning the gap exactly
        p0 = (hi_pt[0] - toward[0] * (run + ext), hi_pt[1] - toward[1] * (run + ext)); y0 = lo["top"] - ext * slope
        Lh = run + ext; Ls = math.hypot(Lh, hi["top"] - y0); pitch = math.degrees(math.atan2(hi["top"] - y0, Lh))
        ctr = ((p0[0] + hi_pt[0]) / 2, (p0[1] + hi_pt[1]) / 2); ym = (y0 + hi["top"]) / 2; t = 0.4
        g = ctx.add(c["id"], "group", [ctr[0], 0, ctr[1]], rot=[0, yaw, 0])
        # box base-centred; rotating about its base centre: lift by t*cos so the TOP surface passes through the end points
        deck = ctx.add(c["id"] + "_Deck", "box", [0, ym - t * math.cos(math.radians(pitch)), t * math.sin(math.radians(pitch))], [width, t, Ls], "grate", g, [-pitch, 0, 0], connector=True, axis="z")
        cp, sp_ = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        def on_slope(x, z, down, h):  # base centre of a pitched box whose top centre sits `down` m (along the deck normal) under the deck top above (x, z)
            yt = ym + z * math.tan(math.radians(pitch)) - down / cp; return [x, yt - h * cp, z + h * sp_]
        for s, side in ((-1, "L"), (1, "R")):
            ctx.add(f"{c['id']}_Beam_{side}", "box", [s * (width / 2 - 0.3), ym - 0.86, 0], [0.3, 0.45, Ls * 0.9], "frame", g, [-pitch, 0, 0])
            # Stage 46: hull cladding over the deck edge and girder (top 3 cm under the walking surface; hides the
            # girder ends - no V-notch at the floors; stops 25 cm short of the low end, clear of its landing), a red light strip along it
            ctx.add(f"{c['id']}_Clad_{side}", "box", on_slope(s * (width / 2 + 0.03), 0.125 * cp, 0.03, 0.95), [0.12, 0.95, Ls - 0.29], "structure_b", g, [-pitch, 0, 0], collision=False)
            ctx.add(f"{c['id']}_CladLight_{side}", "box", on_slope(s * (width / 2 + 0.105), 0, 0.3, 0.11), [0.05, 0.11, max(0.5, Ls - 1.6)], "glow", g, [-pitch, 0, 0],
                    collision=False, outline=False)
        # hazard-stripe thresholds: a flat caution mat on the lower floor at the ramp's foot, a plate on the deck at its top
        ctx.add(f"{c['id']}_Threshold_Lo", "box", [0, lo["top"] + 0.01, -Lh / 2 + ext - 0.45], [width - 0.5, 0.03, 0.8], "stripe", g, collision=False, outline=False)
        ctx.add(f"{c['id']}_Threshold_Hi", "box", on_slope(0, Lh / 2 - 0.55, -0.04, 0.03), [width - 0.5, 0.03, 0.8], "stripe", g, [-pitch, 0, 0], collision=False, outline=False)
        if c.get("rails"):  # posts on the sloped deck top (it passes through (-Lh/2, y0) and (+Lh/2, hi top)), from where it leaves the lower floor
            _rails(ctx, c["id"], g, width, -Lh / 2 + ext + 0.3, Lh / 2 - 0.3, lambda z, y0=y0, Lh=Lh, yh=hi["top"]: y0 + (z + Lh / 2) / Lh * (yh - y0))
        if ym - floor_y > 1.5:
            zs = min(1.2, Lh * 0.15)  # Stage 45: a real pier, head tilted to the deck, a little toward the high end (clear of the low landing)
            sup = pier(ctx, c["id"] + "_Support", g, 0, floor_y, zs, ym - t / math.cos(math.radians(pitch)) + zs * math.tan(math.radians(pitch)), width * 0.4, 0.8, pitch=pitch)
            ctx.rel("supported_by", deck, sup)
        ends = {"lo": (deck, "end_a"), "hi": (deck, "end_b")}
    else:  # solid ramp / stairs standing on the lower floor (+ a plinth down to the ground when raised)
        lead = 0.3 if run <= gap2 + 1e-6 else 0.0
        p0 = (hi_pt[0] - toward[0] * (run + lead), hi_pt[1] - toward[1] * (run + lead)); ctr = ((p0[0] + hi_pt[0]) / 2, (p0[1] + hi_pt[1]) / 2)
        h_ = dy * (run + lead) / run  # keep the slope; the 0.3 m lead-in dips under the lower floor plate (hidden)
        base = lo["top"] - (h_ - dy)
        o = ctx.add(c["id"], kind if kind == "ramp" else "stairs", [ctr[0], base, ctr[1]], [width, h_, run + lead], "grate", rot=[0, yaw, 0], connector=True)
        if base - floor_y > 0.05 and run <= gap2 + 1e-6:  # raised over a gap: a plinth underneath (no floating solid / open underside)
            gc = ((lo_pt[0] + hi_pt[0]) / 2, (lo_pt[1] + hi_pt[1]) / 2)
            sup = ctx.add(c["id"] + "_Support", "box", [gc[0], floor_y, gc[1]], [width * 0.9, base - floor_y + 0.02, max(0.5, gap2 - 0.2)], "structure_b", rot=[0, yaw, 0]); ctx.rel("supported_by", o, sup)
        if c.get("rails"):  # along the slope line of the treads / ramp surface, from the lower floor up to the upper edge
            gr = ctx.add(c["id"] + "_Rails", "group", [ctr[0], 0, ctr[1]], rot=[0, yaw, 0]); Lr = run + lead
            if kind == "stairs":  # posts on tread centres (every 2nd tread), rails parallel to the nosing line
                n_ = max(2, int(round(h_ / 0.25))); zt = [-Lr / 2 + Lr / n_ * (k + 0.5) for k in range(n_)]
                yt = {round(z, 4): base + h_ * (k + 1) / n_ for k, z in enumerate(zt)}; pick = [z for z in zt if z >= -Lr / 2 + lead + 0.2][::2]
                _rails(ctx, c["id"], gr, width, -Lr / 2, Lr / 2, lambda z: yt[round(z, 4)], zs=pick)
            else:
                _rails(ctx, c["id"], gr, width, -Lr / 2 + lead + 0.3, Lr / 2 - 0.3, lambda z, Lr=Lr: base + (z + Lr / 2) / Lr * h_)
        ends = {"lo": (o, "low"), "hi": (o, "high")}
    for key, pl, pt, t, fl_, yy in (("hi", hi, hi_pt, toward, fhi, hi["top"]), ("lo", lo, lo_pt, (-toward[0], -toward[1]), flo, lo["top"])):
        jd = support_depth(pl, pt, t, width); target = fl_
        if jd and jd - 0.1 > 0.15:  # junction plate (support_depth includes the 0.1 m inset): flat piece just under the floor, in the floor's material, filling the corner gaps
            jc = (pt[0] + t[0] * jd / 2, pt[1] + t[1] * jd / 2)
            fmat = next((o["material"] for o in ctx.objects if o["name"] == fl_ and o.get("material")), "grate")  # the platform's own floor:
            target = ctx.add(f"{c['id']}_Junction_{'Hi' if pl is hi else 'Lo'}", "box", [jc[0], yy - 0.43, jc[1]], [width + 0.06, 0.4, jd + 0.1], None, rot=[0, yaw, 0],
                             connector=False, material=fmat)  # 3 cm under it: hidden where it overlaps, reads as the deck continuing where it fills the gap
            ctx.rel("supported_by", target, fl_); ctx.notes.append(f"{c['id']}: {jd:.2f} m junction plate where it meets {pl['id']}'s {'corner' if jd > width / 3 else 'angled edge'}")
        ctx.rel("walkable_connection", ends[key][0], target, a_anchor=ends[key][1])
    foot = p0 if run > gap2 + 0.05 else lo_pt  # a run longer than the gap lands ON the lower platform: keep its real foot clear
    ctx.landings += [(foot[0] - toward[0] * 1.0, foot[1] - toward[1] * 1.0, width / 2), (hi_pt[0] + toward[0] * 1.0, hi_pt[1] + toward[1] * 1.0, width / 2)]
    if run > gap2 + 0.5: ctx.notes.append(f"{c['id']}: {kind} run {run:.1f} m > gap {gap2:.1f} m - extends {run - gap2:.1f} m onto {lo['id']}")


# ------------------------------------------------------------------ walls / arena
def wall_segment(ctx, name, p0, p1, height, thick, base_y, style, inner=None, decor=True, dress=None):
    """Straight wall from p0 to p1 (x, z); 'inner' = point on the playable side (pilasters/banners face it).
    dress = {"dressing": "varied", "dress_y": y}: Stage 18 irregular wall modules instead of the pilaster rhythm."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dz); ux, uz = dx / L, dz / L
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2); yaw = yaw_to(ux, uz) - 90  # local +x along the wall, +z = normal
    nx, nz = uz, -ux
    if inner and (inner[0] - mid[0]) * nx + (inner[1] - mid[1]) * nz > 0: yaw += 180  # local +z = -n after the yaw above: turn it to the inner side
    g = ctx.add(name, "group", [mid[0], 0, mid[1]], rot=[0, yaw, 0])
    body = "wall"
    if dress and dress.get("dressing") == "varied" and decor:  # Stage 19: wall stretches in different textures (plates, slime-stained, plain hull)
        body = str(np.random.default_rng(_h("body" + name)).choice(["wall_works", "wall_works", "wall", "wall", "wall_slimed"]))
    uvw = dict(uv_space="world") if dress and dress.get("dressing") == "varied" else {}  # pattern runs on across segments, plates and openings
    ctx.add(name + "_Body", "box", [0, base_y, 0], [L, height - base_y, thick], body, g, **uvw)
    ctx.add(name + "_Cap", "box", [0, height, 0], [L + 0.3, 0.5, thick + 0.4], "trim" if style == "stone" else "structure_b", g)
    if not decor: return g
    if dress and dress.get("dressing") == "varied": _wall_varied(ctx, name, g, L, height, thick, base_y, dress, body); return g
    step = 12.0 if ctx.detail >= 1 else 24.0; n = max(0, int(L / step))
    for i in range(n):  # pilasters / buttresses on the inner face
        x = -L / 2 + L * (i + 0.5) / n
        if style == "stone": ctx.add(f"{name}_Buttress_{i + 1:02d}", "wedge", [x, base_y, thick / 2 + 0.6], [1.2, (height - base_y) * 0.7, 1.2], "structure", g, [0, 180, 0])
        else: ctx.add(f"{name}_Pilaster_{i + 1:02d}", "box", [x, base_y, thick / 2 + 0.25], [1.0, height - base_y, 0.5], "structure_b", g)
        if style != "stone" and i % 2 == 0 and height - base_y > 8:
            ctx.add(f"{name}_Banner_{i // 2 + 1:02d}", "panel", [x + L / n / 2, base_y + (height - base_y) * 0.45, thick / 2 + 0.03], [2.2, min(5.0, (height - base_y) * 0.4), 0], "accent", g)
    if style != "stone" and ctx.detail >= 2 and L > 10:  # horizontal pipe along the inner face
        ctx.add(name + "_Pipe", "cylinder", [-L / 2 + 1, base_y + 2.2, thick / 2 + 0.7], [1.2, L - 2, 1.2], "pipe", g, [0, 0, -90], sections=8)
    return g


def fan_unit(ctx, nm, parent, c, R, depth, wall=True, rpm=None, seed=0, st=None):
    """Big industrial fan (Stage 19, user reference): thick housing ring with four clamp brackets, a grate disc with a
    green glow behind it, and a smooth bladed rotor on its own node that SPINS (object "spin": rpm -> effect "spin";
    mobile: kept as a separate node so Godot / the preview can rotate it). wall=True: axis = parent local +z (fan on a
    wall face at c = (x, y, z_face)); wall=False: axis vertical (ceiling fan, c = centre of its top)."""
    st = {k: v for k, v in (st or {}).items() if k != "collision"}; rng = np.random.default_rng(seed); x, y, z = c; rot = [90, 0, 0] if wall else [0, 0, 0]
    def at(a, b, k):  # in-plane (a, b) + k along the axis -> parent local
        return [x + a, y + b, z + k] if wall else [x + a, y - k, z + b]
    ctx.add(nm, "cylinder", at(0, 0, 0) if wall else [x, y - depth, z], [2 * R + 1.2, depth, 2 * R + 1.2], "structure_b", parent, rot, sections=20, hole=R, collision=False, **st)
    for k in range(4):
        a = math.radians(45 + 90 * k); ca, sa = math.cos(a), math.sin(a)
        ctx.add(f"{nm}_Clamp_{k + 1}", "box", at(ca * (R + 0.75), sa * (R + 0.75) - (0.4 if wall else 0), -0.15) if wall else [x + ca * (R + 0.75), y - depth - 0.15, z + sa * (R + 0.75)],
                [1.3, 0.8, depth + 0.3] if wall else [1.3, depth + 0.3, 0.8], "frame", parent, [0, 0, math.degrees(a)] if wall else [0, -math.degrees(a), 0], collision=False, **st)
    gl = "fall" if "fall" in ctx.spec.get("materials", {}).get("roles", {}) else "glow"
    if wall: gl = ctx.role("glow_dim")  # Stage 41: wall fans - dark, gloomy light behind the blades
    if not wall:  # Stage 39: ceiling fans glow yellow and cast a soft yellow light (effect "point_light")
        gl = ctx.role("glow_yellow"); ctx.fan_lights = getattr(ctx, "fan_lights", []) + [[round(x, 2), round(y - depth - 1.2, 2), round(z, 2), round(R, 2)]]
    ctx.add(nm + "_Glow", "cylinder", at(0, 0, 0.05) if wall else [x, y - 0.12, z], [2 * R - 0.1, 0.05, 2 * R - 0.1], gl, parent, rot, sections=16, collision=False, outline=False, **st)
    nb = 4  # open grille of thin bars in front of the glow (an opaque grate disc hid it): dark blades read against green light
    for k in range(nb):
        o_ = -R + 2 * R * (k + 0.5) / nb; half = math.sqrt(max(R * R - o_ * o_, 0.1)) * 0.98
        for j, (bw, bh) in enumerate(((2 * half, 0.12), (0.12, 2 * half))):
            pos = at(0, o_, depth * 0.22) if j == 0 else at(o_, 0, depth * 0.22)
            if not wall: pos = [x, y - depth * 0.22 - 0.1, z + o_] if j == 0 else [x + o_, y - depth * 0.22 - 0.1, z]
            ctx.add(f"{nm}_Grille_{j}{k + 1}", "box", pos, [bw, bh, 0.1] if wall else ([bw, 0.1, bh] if j == 0 else [bh, 0.1, bw]), "frame", parent, collision=False, outline=False, **st)
    ctx.add(nm + "_Rotor", "fan_rotor", at(0, 0, depth * 0.62) if wall else [x, y - depth * 0.62, z], [2 * R * 0.95, depth * 0.45, 2 * R * 0.95], "frame", parent, rot,
            blades=int(rng.choice([6, 7, 8, 8])), sweep=float(rng.uniform(15, 28)), collision=False, outline=False, spin=round(float(rpm or rng.uniform(14, 34)) * float(rng.choice([1, -1])), 1),
            **dict(st, mobile={"merge": False}))  # own node: it spins


def louvred_vent(ctx, nm, g, x, yy, vw, vh, f, st):
    """Stage 35 louvred wall vent (Stage 68: shared helper): frame, dark duct behind, louvres tilted 35 deg (ends 2 cm into
    the side frames), status light. (x, yy) = bottom centre on the wall face at local z = f, facing +z."""
    fw = 0.3
    ctx.add(nm, "box", [x, yy + vh - fw, f + 0.15], [vw, fw, 0.3], "structure_b", g, collision=False, **st)  # top of the frame
    ctx.add(nm + "_FrameLow", "box", [x, yy, f + 0.15], [vw, fw, 0.3], "structure_b", g, collision=False, **st)
    for k_, sd in enumerate((-1, 1)): ctx.add(f"{nm}_FrameSide_{k_ + 1}", "box", [x + sd * (vw / 2 - fw / 2), yy + fw - 0.02, f + 0.15], [fw, vh - 2 * fw + 0.04, 0.3], "structure_b", g,
                                              collision=False, **st)
    ctx.add(nm + "_Duct", "panel", [x, yy + fw - 0.02, f + 0.02], [vw - 2 * fw + 0.04, vh - 2 * fw + 0.04, 0], ctx.role("accent"), g, uv_region="void", collision=False, outline=False, **st)
    nl = max(3, int((vh - 2 * fw) / 0.42))
    for j in range(nl):
        ly = yy + fw + (vh - 2 * fw) * (j + 0.5) / nl - 0.15
        ctx.add(f"{nm}_Slat_{j + 1}", "box", [x, ly, f + 0.2], [vw - 2 * fw + 0.04, 0.3, 0.07], "frame", g, [35, 0, 0], collision=False, outline=False, **st)
    ctx.add(nm + "_Status", "box", [x + vw / 2 - 0.45, yy + vh - fw + 0.07, f + 0.31], [0.3, 0.16, 0.06], "glow", g, collision=False, outline=False, **st)


WALL_MODULES = (("pipes", 3), ("machine", 2), ("fan", 1.5), ("emblem", 1.5), ("vent", 1.5), ("monitor", 2), ("door", 0.7), ("plain", 1.2))


def _wall_varied(ctx, name, g, L, height, thick, base_y, dress, body="wall"):
    """Stage 18 wall dressing: the inner face is cut into slots of random width (5-13 m) and every slot gets a module,
    never the same twice in a row: vertical pipe bundle with brackets, machine housing on a bracket, big wall fan,
    painted emblem (banner panel), vent grille, glowing slime-tank window, sealed side door (at most one per wall),
    plain stretch with a light strip. Red lights here and there. Seeded by the wall name -> stable between builds."""
    rng = np.random.default_rng(_h("wall" + name)); fy = float(dress.get("dress_y", 7.0)); f = thick / 2; st = dict(mobile={"static": True})
    u = -L / 2 + thick + rng.uniform(0.5, 2.0); end = L / 2 - thick - 0.5; prev = None; k = 0; doors = 0; fans = 0; H = height - base_y  # corners: the segment runs into the next wall
    mods, wts = zip(*WALL_MODULES)
    while u < end - 2.5:
        sw = min(rng.uniform(5, 13), end - u); x = u + sw / 2; k += 1
        p = np.array(wts, float); p[[i for i, m in enumerate(mods) if m == prev or (m == "door" and doors) or (m == "fan" and (fans or sw < 7.5))]] = 0; m = mods[int(rng.choice(len(mods), p=p / p.sum()))]
        if sw < 4.5: m = "pipes" if prev != "pipes" else "plain"
        nm = f"{name}_M{k:02d}{m.capitalize()}"  # module kind in the name (level.json readers, tests)
        if m == "pipes":
            nps = int(rng.integers(2, 5)); r = rng.uniform(0.25, 0.55); y1 = height - rng.uniform(0.5, 4)
            while nps > 1 and nps * (2 * r + 0.25) + 0.3 > sw - 0.4: nps -= 1  # the bundle stays inside its slot
            for i in range(nps):
                px = x + (i - (nps - 1) / 2) * (2 * r + 0.25)
                ctx.add(f"{nm}_Pipe_{i + 1}", "cylinder", [px, base_y + 0.5, f + r + 0.1], [2 * r, y1 - base_y - 0.5, 2 * r], "pipe", g, sections=6, outline=False, **st)  # solid: it stands on walkways
            for j, yy in enumerate(sorted(rng.uniform(fy + 2, y1 - 1, int(rng.integers(2, 4))))):
                ctx.add(f"{nm}_Bracket_{j + 1}", "box", [x, yy, f + 0.09 + r], [nps * (2 * r + 0.25) + 0.3, 0.35, 2 * r + 0.14], "frame", g, collision=False, outline=False, **st)  # 6 cm proud of the pipes, never level with a hex face
        elif m == "machine":
            mw, mh = sw * rng.uniform(0.5, 0.8), rng.uniform(3, 6.5); my = fy + 3.3  # hung above head height: walkways along the wall stay clear
            ctx.add(nm + "_Bracket", "box", [x, my - 0.8, f + 0.7], [mw * 0.8, 0.8, 1.4], "frame", g, collision=False, **st)
            ctx.add(nm, "machinery", [x, my, f + 0.8], [mw, mh, 1.6], "machine", g, seed=int(rng.integers(1 << 20)), collision=False, **st)
            ctx.add(nm + "_Light", "box", [x - mw * 0.3, my + mh + 0.3, f + 0.15], [0.6, 0.35, 0.3], "glow", g, collision=False, outline=False, **st)  # on the wall above the housing
        elif m == "fan":
            fans += 1; rr = min(sw / 2 - 1.2, rng.uniform(2.6, 4.4)); yy = rng.uniform(fy + 4 + rr, max(fy + 4.5 + rr, height - rr - 2))
            fan_unit(ctx, nm, g, (x, yy, f), rr, 1.0, wall=True, seed=_h(nm), st=st)
        elif m == "emblem":
            ew = min(sw * 0.8, rng.uniform(4, 7)); eh = min(H - (fy + 3 - base_y) - 1, ew * rng.uniform(1.4, 2.0))
            if eh > 3: ctx.add(nm, "panel", [x, fy + 2.5, f + 0.03], [ew, eh, 0], "accent", g, collision=False, outline=False, **st)
        elif m == "vent":
            vw = sw * rng.uniform(0.4, 0.7); yy = rng.uniform(fy + 1, fy + 8); vh = rng.uniform(2, 4)  # framed louvred vent (boxes: cheap)
            louvred_vent(ctx, nm, g, x, yy, vw, vh, f, st)
        elif m == "monitor":  # Stage 22-23: wall TV - moulded tv_body (casing texture: screws, vents, speaker grille, knobs, LED), glass screen, mount arms
            tw = min(sw * rng.uniform(0.5, 0.7), rng.uniform(3.2, 5.2)); th = tw * 0.74; yy = fy + rng.uniform(1.4, 2.6); scr = "a" if rng.random() < 0.5 else "b"  # which of the two layouts
            scr, sid = screen_slot(ctx, "screen", scr)  # Stage 52: own picture variant + id (flicker timing / easter egg)
            bf, cf, depth, stand = 0.07, 0.2, 0.9, 0.35; W_ = tw / (1 - 2 * bf); H_ = W_ * 0.8; th = H_ * (1 - cf - bf * 1.33) * 0.98; y0 = yy - H_ * cf
            ctx.add(nm + "_Body", "tv_body", [x, y0, f + stand], [W_, H_, depth], "tv_casing", g, border=bf, chin=cf, **st)
            ctx.add(nm + "_Screen", "panel", [x, yy + H_ * 0.003, f + stand + depth - 0.12 + 0.02], [W_ * (1 - 2 * bf) * 0.995, th, 0], "screen", g, uv_region=scr, uv_shift=sid, collision=False, outline=False, **st)
            for k_ in (-1, 1): ctx.add(f"{nm}_Arm_{k_ + 1}", "box", [x + k_ * W_ * 0.2, y0 + H_ * 0.45, f + 0.0], [0.25, 0.3, stand + 0.1], "frame", g, collision=False, outline=False, **st)
            ctx.add(nm + "_Cable", "cylinder", [x - W_ * 0.28, y0 + H_ * 0.85, f + 0.15], [0.24, max(0.5, min(3.5, height - (y0 + H_ * 0.85) - 0.5)), 0.24], "frame", g, sections=6, collision=False, outline=False, **st)
        elif m == "door":
            doors += 1; dw = min(sw * 0.6, 3.6); dh = 4.4
            ctx.add(nm + "_Frame", "box", [x, fy, f + 0.15], [dw + 1.0, dh + 0.7, 0.3], "glow", g, collision=False, outline=False, **st)
            ctx.add(nm, "box", [x, fy + 0.02, f + 0.25], [dw, dh - 0.02, 0.3], "structure_b", g, collision=False, **st)  # 2 cm up: no shared bottom face with the frame
            ctx.add(nm + "_Sign", "box", [x, fy + dh + 0.7, f + 0.2], [1.6, 0.5, 0.2], "glow", g, collision=False, outline=False, **st)
        else:
            ctx.add(nm + "_Strip", "box", [x, fy + rng.uniform(3, 8), f + 0.05], [sw * 0.7, 0.18, 0.1], "glow", g, collision=False, outline=False, **st)
        if rng.random() < 0.35 and m not in ("door",):  # a stray red light box
            ctx.add(nm + "_Red", "box", [x + rng.uniform(-sw / 2 + 0.5, sw / 2 - 0.5), rng.uniform(fy + 2, height - 3), f + 0.15], [0.5, 0.35, 0.3], "glow", g, collision=False, outline=False, **st)
        if rng.random() < 0.7:  # raised wall plate in another tone over part of the slot: the face reads as panels, not one tiled sheet
            y0 = rng.uniform(fy + 4.5, fy + 9) if m not in ("pipes", "fan") else rng.uniform(base_y + 1, fy - 1); y1 = min(height - 0.8, y0 + rng.uniform(5, 14))
            if y1 - y0 > 2:  # (random draws in the original order: same plates, same textures as before)
                pw, pm = sw * rng.uniform(0.7, 0.96), str(rng.choice(["wall_works", "structure_b", "frame", "wall_works", "structure_b", "wall_slimed"]))
                if dress.get("plate_blend", True):  # Stage 29: worn ragged outline 1.2 cm off the wall (corrosion band 2.1 cm, emblems 3 cm): the plate's texture dissolves into the wall's
                    ctx.add(nm + "_Plate", "panel", [x, y0, f + 0.012], [pw, y1 - y0, 0], pm, g, cut="ragged", seed=_h(nm) % 100000, collision=False, outline=False,
                            uv_space="world", **st)
                else: ctx.add(nm + "_Plate", "box", [x, y0, f + 0.06], [pw, y1 - y0, 0.12], pm, g, collision=False, outline=False, uv_space="world", **st)
        prev = m; u += sw


def window_frame(ctx, name, p0, p1, y0, y1, thick, inner):
    """Frame bars across a wall window (mullions every ~5 m + one transom), centred in the wall thickness; visual only."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dz); yaw = yaw_to(dx / L, dz / L) - 90
    g = ctx.add(name, "group", [(p0[0] + p1[0]) / 2, 0, (p0[1] + p1[1]) / 2], rot=[0, yaw, 0]); n = max(1, int(round(L / 5.0)))
    for k in range(1, n):
        ctx.add(f"{name}_Mullion_{k:02d}", "box", [-L / 2 + L * k / n, y0, 0], [0.35, y1 - y0, 0.5], "frame", g, collision=False, mobile={"static": True})
    ctx.add(name + "_Transom", "box", [0, y0 + (y1 - y0) * 0.55, 0], [L, 0.35, 0.5], "frame", g, collision=False, mobile={"static": True})
    return g


def arena_outline(arena):
    """Corner points (x, z) of the arena boundary, clockwise from north-west."""
    (cx, cz), (w, d) = arena.get("center", [0, 0]), arena["size"]; sh = arena.get("shape", "rect")
    if sh == "rect": return [(cx - w / 2, cz - d / 2), (cx + w / 2, cz - d / 2), (cx + w / 2, cz + d / 2), (cx - w / 2, cz + d / 2)]
    n = 8 if sh == "octagon" else 20; r = min(w, d) / 2 / math.cos(math.pi / n)
    return [(cx + r * math.sin(math.pi / n * (2 * i + 1) - math.pi), cz + r * math.cos(math.pi / n * (2 * i + 1) - math.pi)) for i in range(n)][::-1]


SIDES = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def arena(ctx, a, floor_y, pre=""):
    """The arena enclosure; also used for spec "annexes" (extra roofed wings next to it): pre = name prefix
    ("<id>_"), walls.skip = sides not built (the side shared with the arena, whose wall carries the doorway)."""
    (cx, cz), (w, d) = a.get("center", [0, 0]), a["size"]; fl = a.get("floor", {"kind": "ground"}); sh = a.get("shape", "rect")
    el = (pre[:-1] if pre else "arena")
    big = [w + 2 * a.get("walls", {}).get("thickness", 2), 0, d + 2 * a.get("walls", {}).get("thickness", 2)]
    if fl["kind"] == "hazard":
        ctx.element = (el + ".floor", fl.get("source", "visible"))
        n = ctx.add(fl.get("name", pre + "HazardFluid"), "box" if sh == "rect" else "cylinder", [cx, 0, cz], [w, fl["y"], d], fl.get("material", "hazard"),
                    **({} if sh == "rect" else {"sections": 8 if sh == "octagon" else 24}))
        ctx.hazards.append(n)
    else:
        ctx.element = ("arena.floor", fl.get("source", "visible"))
        mat = fl.get("material", "ground" if fl["kind"] == "ground" else "deck")
        ex = 2.4 if getattr(ctx, "TR", None) is not None else 1  # on world terrain: the slab reaches past the wall pilasters into the pad
        ctx.add(fl.get("name", "Ground"), "box", [cx, fl["y"] - 0.5, cz], [big[0] + ex, 0.5, big[2] + ex], mat)
        ctx.walkable.append(dict(name=fl.get("name", "Ground"), min=[cx - w / 2 + 1, cz - d / 2 + 1], max=[cx + w / 2 - 1, cz + d / 2 - 1], y=fl["y"]))
    W = a.get("walls")
    if W and W.get("style", "auto") != "none":
        ctx.element = (el + ".walls", W.get("source", "visible")); style = ctx.theme["wall_style"] if W.get("style", "auto") == "auto" else W["style"]
        pts = arena_outline(a); t = W.get("thickness", 3.0); names = ["North", "East", "South", "West"] if sh == "rect" else [f"{i + 1:02d}" for i in range(len(pts))]
        WN = (pre or "Outer") + "Wall_"
        for i, (p0, p1) in enumerate(zip(pts, pts[1:] + pts[:1])):
            if sh == "rect" and names[i].lower() in W.get("skip", []): continue
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uz = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L; nx, nz = uz, -ux  # outward normal (clockwise)
            q0 = (p0[0] + nx * t / 2 - ux * t / 2, p0[1] + nz * t / 2 - uz * t / 2); q1 = (p1[0] + nx * t / 2 + ux * t / 2, p1[1] + nz * t / 2 + uz * t / 2)
            SL = math.hypot(q1[0] - q0[0], q1[1] - q0[1]); P = lambda u: (q0[0] + ux * u, q0[1] + uz * u)  # u: metres along the side from q0
            ops = sorted([op for op in W.get("openings", []) if sh == "rect" and op["side"].capitalize() == names[i]], key=lambda op: op.get("at", 0))
            cuts = []
            for j, op in enumerate(ops):  # every opening in the SIDE's own coordinates (several per side stay where they were asked)
                c = SL / 2 + op.get("at", 0); h0, h1 = max(0.0, c - op["width"] / 2), min(SL, c + op["width"] / 2); cuts.append((h0, h1))
                m0, m1 = P(h0), P(h1); tag = f"{WN}{names[i]}_Op{j + 1}"
                if op.get("height", 0) and op["height"] < W["height"] - 0.5:  # lintel above the opening
                    wall_segment(ctx, tag + "_Lintel" if len(ops) > 1 else f"{WN}{names[i]}_Lintel", m0, m1, W["height"], t, op["height"], style, (cx, cz), decor=False)
                if op.get("sill"):  # window: wall kept below the sill (out of reach), frame bars across the opening
                    wall_segment(ctx, tag + "_Sill", m0, m1, op["sill"], t, 0.0, style, (cx, cz), decor=False)
                    if op.get("frame", True): window_frame(ctx, tag + "_Frame", m0, m1, op["sill"], op.get("height") or W["height"], t, (cx, cz))
                    if op.get("fill") == "slime":  # Stage 18: a giant slime-tank window instead of a view out (glowing glass in the wall)
                        mx_, mz_ = (m0[0] + m1[0]) / 2, (m0[1] + m1[1]) / 2; yaw_ = yaw_to(ux, uz) - 90
                        ctx.add(tag + "_Slime", "box", [mx_, op["sill"] + 0.25, mz_], [op["width"] - 0.1, (op.get("height") or W["height"]) - op["sill"] - 0.25, 0.6], "hazard", None, [0, yaw_, 0],
                                collision=True, outline=False, mobile={"static": True})
                    elif op.get("fill") in ("screen", "specimen"):  # Stage 24: giant broadcast viewscreen / specimen containment window
                        mx_, mz_ = (m0[0] + m1[0]) / 2, (m0[1] + m1[1]) / 2; yaw_ = yaw_to(ux, uz) - 90; ox_, oz_ = -nx * (t / 2 + 0.04), -nz * (t / 2 + 0.04)  # room side
                        y0_, hh_ = op["sill"] + 0.25, (op.get("height") or W["height"]) - op["sill"] - 0.5
                        ctx.add(tag + "_Back", "box", [mx_, y0_, mz_], [op["width"] - 0.1, hh_, t - 0.04], "frame", None, [0, yaw_, 0], collision=True, outline=False, mobile={"static": True})
                        reg_, sid_ = screen_slot(ctx, "bigscreen", "a" if op["fill"] == "screen" else "b")  # Stage 52: variant + id
                        ctx.add(tag + "_Screen", "panel", [mx_ + ox_, y0_, mz_ + oz_], [op["width"] - 0.4, hh_, 0], "bigscreen", None, [0, yaw_, 0],
                                uv_region=reg_, uv_shift=sid_, collision=False, outline=False, mobile={"static": True})
                        ctx.add(tag + "_SillLight", "box", [mx_ - nx * (t / 2 + 0.24), op["sill"] + 0.16, mz_ - nz * (t / 2 + 0.24)], [op["width"] * 0.6, 0.18, 0.12], "glow", None, [0, yaw_, 0], collision=False, outline=False, mobile={"static": True})
            segs, u = [], 0.0
            for h0, h1 in cuts + [(SL, SL)]:
                if h0 - u > 0.5: segs.append((P(u), P(h0)))
                u = max(u, h1)
            for k, (s0, s1) in enumerate(segs):
                nm = f"{WN}{names[i]}" + (f"_{k + 1:02d}" if len(segs) > 1 else "")
                wall_segment(ctx, nm, s0, s1, W["height"], t, 0.0, style, (cx, cz), dress=W if W.get("dressing") else None)
    if a.get("walkway"):
        ww = a["walkway"]; ctx.element = (el + ".walkway", ww.get("source", "visible")); wd = ww.get("width", 4.0)
        if sh != "rect": ctx.notes.append("walkway ring is only generated for rect arenas")
        else:
            for nm, (x, z, sw, sd) in {"North": (cx, cz - d / 2 + wd / 2, w, wd), "South": (cx, cz + d / 2 - wd / 2, w, wd),
                                       "West": (cx - w / 2 + wd / 2, cz, wd, d - 2 * wd), "East": (cx + w / 2 - wd / 2, cz, wd, d - 2 * wd)}.items():
                platform(ctx, dict(id=pre + "Walkway_" + nm, center=[x, z], size=[sw, sd], top=ww["y"], shape="rect", lights=False, cover=0,
                                   style=ww.get("style")), 0.0, (cx, cz))
    if a.get("ceiling") not in (None, False) and W: ceiling(ctx, a, W, pre)  # {} = a roof with defaults
    if a.get("boundary", "walls" if W else "invisible") == "invisible" or not W:
        ctx.element = (el + ".boundary", "inferred"); pts = arena_outline(a)
        for i, (p0, p1) in enumerate(zip(pts, pts[1:] + pts[:1])):
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); yaw = yaw_to((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L) - 90
            ctx.add(f"{pre}Boundary_{i + 1:02d}", "boundary", [(p0[0] + p1[0]) / 2, fl.get("y", 0), (p0[1] + p1[1]) / 2], [L, 12, 0.5], rot=[0, yaw, 0])


def ceiling(ctx, a, W, pre=""):
    """Indoor arena (arena.ceiling): roof slab resting on the wall tops (y = walls.height), optional round opening
    ("opening": radius, at "opening_at" [x, z], default the arena centre) for an elevator shaft, a grid of girders
    under it ("beam_step" m, beams never cross the opening) and lamp panels between them. Every part is tagged
    "cutaway" (the preview hides it when the camera rises above the roof) and grouped for the mobile export
    ("mobile.group" "Ceiling": a few separate nodes, never mixed into wall cells)."""
    C = a["ceiling"] if isinstance(a["ceiling"], dict) else {}; ctx.element = ((pre[:-1] if pre else "arena") + ".ceiling", C.get("source", "visible"))
    (cx, cz), (w, d) = a.get("center", [0, 0]), a["size"]; t = W.get("thickness", 3.0); y = float(W["height"]) + 0.5  # on the wall caps
    th = float(C.get("thickness", 1.0)); R = C.get("opening"); ox, oz = C.get("opening_at", [cx, cz])
    tag = dict(cutaway=True, mobile={"group": "Ceiling"})
    hole = {} if not R else dict(hole=float(R), collision_mesh=True)
    if R and (abs(ox - cx) > 0.01 or abs(oz - cz) > 0.01): ctx.notes.append("ceiling opening must be at the arena centre - moved there"); ox, oz = cx, cz
    sk = W.get("skip", []); ex = {s_: (-0.3 if s_ in sk else t + 0.3) for s_ in ("north", "south", "east", "west")}  # a skipped side meets the arena's slab edge
    x0, x1, z0, z1 = cx - w / 2 - ex["west"], cx + w / 2 + ex["east"], cz - d / 2 - ex["north"], cz + d / 2 + ex["south"]
    ctx.add(pre + "Ceiling_Slab", "box", [(x0 + x1) / 2, y, (z0 + z1) / 2], [x1 - x0, th, z1 - z0], C.get("material", "wall"), **hole, **tag, outline=False)
    if C.get("style") == "varied":  # Stage 18: irregular dressing, built after the platforms (pods keep headroom over decks)
        ctx.pending_ceilings = getattr(ctx, "pending_ceilings", []) + [dict(pre=pre, cx=cx, cz=cz, w=w, d=d, y=y, R=R or 0.0, ox=ox, oz=oz, C=C, tag=tag)]
        ctx.ceiling_y = y; ctx.notes.append(f"{pre}ceiling: roof slab at y {y:.1f} m, varied dressing"); return
    step = float(C.get("beam_step", 12.0)); bh = float(C.get("beam_depth", 1.1)); keep = (R or 0) + 0.8
    xs = [cx + k * step for k in range(-int(w / 2 / step), int(w / 2 / step) + 1) if abs(k * step) < w / 2 - 1 and abs(k * step) > keep]
    zs = [cz + k * step for k in range(-int(d / 2 / step), int(d / 2 / step) + 1) if abs(k * step) < d / 2 - 1 and abs(k * step) > keep]
    for i, x in enumerate(xs):  # girders north-south, then east-west (wall face to wall face)
        ctx.add(f"{pre}Ceiling_Beam_NS_{i + 1:02d}", "ibeam", [x, y - bh, cz], [d, bh, 0.6], "frame", None, [0, 90, 0], collision=False, outline=False, **tag)
    for i, z in enumerate(zs):
        ctx.add(f"{pre}Ceiling_Beam_EW_{i + 1:02d}", "ibeam", [cx, y - bh - 0.02, z], [w, bh, 0.6], "frame", None, collision=False, outline=False, **tag)
    if C.get("lamps", True):  # lamp panels in the bays between the girders (glow material: emissive, no extra light cost)
        bx = [cx - w / 2] + xs + [cx + w / 2]; bz = [cz - d / 2] + zs + [cz + d / 2]; k = 0
        for x0, x1 in zip(bx, bx[1:]):
            for z0, z1 in zip(bz, bz[1:]):
                mx, mz = (x0 + x1) / 2, (z0 + z1) / 2
                if R and math.hypot(mx - ox, mz - oz) < R + 3: continue
                k += 1; ctx.add(f"{pre}Ceiling_Lamp_{k:02d}", "box", [mx, y - 0.18, mz], [min(4.0, (x1 - x0) * 0.4), 0.18, min(1.2, (z1 - z0) * 0.2)], "glow", None,
                                collision=False, outline=False, **tag)
    ctx.ceiling_y = y; ctx.notes.append(f"{pre}ceiling: roof slab at y {y:.1f} m" + (f" with a {R} m opening for the shaft" if R else "") + f", {len(xs) + len(zs)} girders")


def _floor_under(ctx, x, z, r=3.0):
    """Highest walkable surface within r m of (x, z) (platforms, walkways, decks), else the arena floor."""
    ys = [w_["y"] for w_ in ctx.walkable if w_["min"][0] - r <= x <= w_["max"][0] + r and w_["min"][1] - r <= z <= w_["max"][1] + r]
    return max(ys + [getattr(ctx, "floor_y", 0.0)])


def dress_ceilings(ctx):
    """Stage 18 "varied" ceilings (after platforms + structures): no grid. Seeded per room:
      - main beams across the short span at irregular spacing, mixed I-beams and deep trusses, split round the shaft
      - stepped ceiling sections (coffers) hanging at different depths, some edged with red light strips
      - long ducts at different heights, a ventilation fan ring
      - clusters of hanging green cage lamps of mixed size and drop (bottoms >= 4.5 m over any deck below)
      - sagging cable runs, scattered pairs of red ceiling lights
    Visual only (no colliders), cutaway + mobile group "Ceiling" like the slab."""
    for P in getattr(ctx, "pending_ceilings", []):
        pre, cx, cz, w, d, y, R, ox, oz, C, tag = (P[k] for k in ("pre", "cx", "cz", "w", "d", "y", "R", "ox", "oz", "C", "tag"))
        ctx.element = ((pre[:-1] if pre else "arena") + ".ceiling", C.get("source", "visible"))
        rng = np.random.default_rng(_h("ceiling" + pre + str(C.get("seed", 0)))); vis = dict(collision=False, **tag); n = pre + "Ceil_"
        along_z = d >= w; L, S = (d, w) if along_z else (w, d)  # beams span S (short), stand along L
        def P2(u, v): return (cx + v, cz + u) if along_z else (cx + u, cz + v)  # u along L, v across
        ou, ov = ((oz - cz, ox - cx) if along_z else (ox - cx, oz - cz)) if R else (1e9, 1e9)
        def clear_of_shaft(x, z, m): return not R or math.hypot(x - ox, z - oz) > R + m
        u = -L / 2 + rng.uniform(4, 9); k = 0
        while u < L / 2 - 3:  # ---- main beams
            k += 1; deep = rng.random() < 0.35; bh = rng.uniform(2.0, 3.2) if deep else rng.uniform(0.9, 2.0)
            spans = [(-S / 2, S / 2)]
            if R and abs(u - ou) < R + 1.5: spans = [(-S / 2, ov - R - 1.2), (ov + R + 1.2, S / 2)]
            for j, (v0, v1) in enumerate(spans):
                if v1 - v0 < 2: continue
                x, z = P2(u, (v0 + v1) / 2); ln = v1 - v0; rot = [0, 0 if along_z else 90, 0]; nm = f"{n}Beam_{k:02d}_{j + 1}"
                if deep:  # truss: two chords + alternating web diagonals
                    for yy, c in ((y - 0.45, "T"), (y - bh, "B")): ctx.add(f"{nm}_{c}", "box", [x, yy, z], [ln, 0.45, 0.45], "frame", None, rot, outline=c == "B", **vis)
                    nw = max(2, int(ln / 3.2)); ang = math.degrees(math.atan2(ln / nw, bh - 0.45))
                    for i in range(nw):
                        vv = v0 + ln * (i + 0.5) / nw; wx, wz = P2(u, vv)
                        ctx.add(f"{nm}_W{i + 1:02d}", "box", [wx, y - bh + 0.45, wz], [0.22, (bh - 0.9) / max(math.cos(math.radians(ang)), 0.3), 0.22], "frame", None,
                                ([0, 0, ang if i % 2 else -ang] if along_z else [ang if i % 2 else -ang, 0, 0]), outline=False, **vis)
                else: bw_ = rng.uniform(0.5, 0.9); ctx.add(nm, "ibeam", [x, y - bh, z], [ln, bh, bw_], "frame", None, [0, 0 if along_z else 90, 0], outline=False, **vis)
                sw_ = (0.45 if deep else bw_) + 0.1  # stripe band 5 cm proud of the beam on each side
                for e_, vv in (("A", v0 + 1.0), ("B", v1 - 1.0)):  # 10 cm in from the beam end (no shared end face)  # hazard-striped ends where the beam meets a wall / the shaft
                    ex_, ez_ = P2(u, vv); ctx.add(f"{nm}_Stripe{e_}", "box", [ex_, y - bh - 0.04, ez_], [1.8, min(bh, 1.2) * 0.7, sw_] if along_z else [sw_, min(bh, 1.2) * 0.7, 1.8],
                                                  "stripe", None, outline=False, **vis)
                vv = v0 + rng.uniform(2, 6)
                while vv < v1 - 2:  # warm pill lights under the beam at irregular spacing
                    lx, lz = P2(u, vv); ctx.add(f"{nm}_Lamp_{int(vv * 10) % 10000:04d}", "box", [lx, y - bh - 0.14, lz], [1.4, 0.12, 0.34] if along_z else [0.34, 0.12, 1.4],
                                                "lamp", None, outline=False, **vis)
                    vv += rng.uniform(5, 13)
            beam_u = getattr(ctx, "_beam_u", []) + [(pre, u)]; ctx._beam_u = beam_u; u += rng.uniform(8, 21)
        area = w * d; nc = max(2, int(area / 2600))  # ---- stepped sections
        for i in range(nc):
            for _ in range(20):
                sw, sd = rng.uniform(10, 26), rng.uniform(8, 22); x = cx + rng.uniform(-w / 2 + sw / 2, w / 2 - sw / 2); z = cz + rng.uniform(-d / 2 + sd / 2, d / 2 - sd / 2)
                if clear_of_shaft(x, z, max(sw, sd) / 2 + 2): break
            else: continue
            drop = rng.uniform(1.6, 4.2); ctx.add(f"{n}Step_{i + 1:02d}", "box", [x, y - drop, z], [sw, drop - 0.05, sd], C.get("material", "wall"), None, outline=False, **vis)
            if rng.random() < 0.6:
                ctx.add(f"{n}Step_{i + 1:02d}_Strip", "box", [x, y - drop - 0.12, z + sd / 2 - 0.4], [sw * rng.uniform(0.4, 0.8), 0.12, 0.25], "glow", None, outline=False, **vis)
        for i in range(int(rng.integers(2, 4))):  # ---- ducts along L at different heights / offsets, clear of the shaft
            for _ in range(20):
                v = rng.uniform(-S / 2 + 3, S / 2 - 3)
                if not R or abs(v - ov) > R + 2.5: break
            r = rng.uniform(0.6, 1.3); u0, u1 = sorted(rng.uniform(-L / 2 + 1, L / 2 - 1, 2)); u1 = max(u1, u0 + L * 0.35)
            x, z = P2(u0, v); yy = y - rng.uniform(2.4, 4.5)
            dl = min(u1, L / 2 - 1) - u0
            ctx.add(f"{n}Duct_{i + 1}", "cylinder", [x, yy, z], [2 * r, dl, 2 * r], "pipe", None, [90, 0, 0] if along_z else [0, 0, -90], sections=8, outline=False, **vis)
            for j in range(max(2, int(dl / 12)) + 1):  # hangers from the roof
                hx, hz = P2(u0 + 0.5 + (dl - 1.0) * j / max(2, int(dl / 12)), v)
                ctx.add(f"{n}Duct_{i + 1}_Hanger_{j + 1}", "box", [hx, yy + r - 0.1, hz], [0.18, y - yy - r + 0.1, 0.18], "frame", None, outline=False, **vis)
        for i in range(int(rng.integers(1, 3))):  # ---- ventilation fan rings
            rr = rng.uniform(2.2, 3.6); boxes = _ceiling_boxes(ctx, y, 3.5)
            for _ in range(60):  # Stage 37: clear of the shaft AND of girders / steps / anything already under the roof
                x, z = cx + rng.uniform(-w / 2 + 6, w / 2 - 6), cz + rng.uniform(-d / 2 + 6, d / 2 - 6)
                if clear_of_shaft(x, z, 8) and not any(lo[0] < x + rr + 0.8 and hi[0] > x - rr - 0.8 and lo[2] < z + rr + 0.8 and hi[2] > z - rr - 0.8 for lo, hi in boxes): break
            fan_unit(ctx, f"{n}Fan_{i + 1}", None, (x, y - 0.12, z), rr, 0.9, wall=False, seed=_h(n + str(i)), st=vis)
        npods = int(area / 800 * C.get("pods", 1.0)); placed = 0  # ---- hanging cage lamps on lamp rails (Stage 32)
        nl_ = int(C.get("lamp_rails", 0))  # Stage 54: "lamp_rails": n - rails even without pods ("pods": 0 -> bare rails)
        if npods or nl_:
            nl = nl_ or max(1, int(round(npods / 6))); per = int(math.ceil(npods / nl)); ry = y - 3.07  # odd height: never flush with a ceiling step
            busy = [k[1] for k in getattr(ctx, "crane_rails", set()) if abs(k[2]) < 1e-6]  # crane runways (world z of each line)
            for li in range(nl):
                z = cz - d / 2 + d * (li + 0.5) / nl + rng.uniform(-2, 2)
                for _ in range(8):  # keep clear of the crane runways and the lift shaft
                    if all(abs(z - b) > 3.5 for b in busy) and clear_of_shaft(cx, z, 3.0) or not (cz - d / 2 + 4 < z < cz + d / 2 - 4): break
                    z += 4.0 if z < cz + d / 2 - 8 else -9.0
                Lr = w - 6; ln = f"{n}LampRail_{li + 1}"
                ctx.add(ln, "ibeam", [cx, ry, z], [Lr, 0.5, 0.4], "frame", None, **vis)
                m = max(2, int(round(Lr / 11)))
                for k in range(m + 1):
                    hx = cx - Lr / 2 + 0.5 + (Lr - 1.0) * k / m
                    ctx.add(f"{ln}_Hanger_{k + 1}", "box", [hx, ry + 0.5, z], [0.16, y - ry - 0.5 + 0.08, 0.16], "frame", None, outline=False, **vis)
                for j in range(per):
                    if placed >= npods: break
                    x = cx - Lr / 2 + 2 + (Lr - 4) * (j + 0.5) / per + rng.uniform(-1.5, 1.5)
                    if not clear_of_shaft(x, z, 2.5): continue
                    big = rng.random() < 0.2; r = rng.uniform(1.3, 2.0) if big else rng.uniform(0.6, 1.0); h = r * rng.uniform(1.8, 2.4)
                    low = _floor_under(ctx, x, z, r + 2.0) + 4.5 + h; bot = max(low, ry - h - rng.uniform(0.8, 6.0))
                    if bot + h + 0.4 > ry: continue  # too little room under the rail here
                    placed += 1; nm = f"{n}Pod_{placed:02d}"
                    ctx.add(nm + "_Cable", "box", [x, bot + h, z], [0.1, ry - bot - h + 0.05, 0.1], "frame", None, outline=False, **vis)  # from the rail
                    ctx.add(nm + "_Cap", "cylinder", [x, bot + h - 0.1, z], [2 * r + 0.3, 0.45, 2 * r + 0.3], "structure_b", None, sections=6, **vis)
                    ctx.add(nm, "cylinder", [x, bot + 0.2, z], [2 * r, h - 0.25, 2 * r], ctx.role("glass_clear"), None, sections=6, outline=False, double_sided=True,
                            **vis)  # clear shell, ends tucked 5 cm into base and cap (its lids hidden there: no flicker)
                    ctx.add(nm + "_Base", "cylinder", [x, bot, z], [2 * r + 0.2, 0.3, 2 * r + 0.2], "structure_b", None, sections=6, outline=False, **vis)
                    for b in range(3):  # cage: three posts on the outside corners (nothing through the glass)
                        a_ = math.radians(120 * b); ctx.add(f"{nm}_Bar_{b + 1}", "box", [x + math.cos(a_) * (r + 0.04), bot + 0.2, z - math.sin(a_) * (r + 0.04)], [0.14, h - 0.25, 0.14],
                                                           "frame", None, [0, 120 * b, 0], outline=False, **vis)
        for i in range(int(area / 1400)):  # ---- sagging cable runs (4 segments)
            x0, z0 = cx + rng.uniform(-w / 2 + 2, w / 2 - 2), cz + rng.uniform(-d / 2 + 2, d / 2 - 2); a = rng.uniform(0, 2 * math.pi); ln = rng.uniform(8, 20)
            x1, z1 = x0 + math.cos(a) * ln, z0 + math.sin(a) * ln
            if abs(x1 - cx) > w / 2 - 1 or abs(z1 - cz) > d / 2 - 1: continue
            sag = rng.uniform(1.5, 4.5); pts = [(x0 + (x1 - x0) * t, y - 0.6 - sag * 4 * t * (1 - t), z0 + (z1 - z0) * t) for t in np.linspace(0, 1, 5)]
            for j, (pa, pb) in enumerate(zip(pts, pts[1:])):
                dx, dy, dz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]; sl = math.sqrt(dx * dx + dy * dy + dz * dz)
                yaw = math.degrees(math.atan2(dx, dz)); pitch = math.degrees(math.asin(max(-1, min(1, dy / sl))))
                ctx.add(f"{n}Cable_{i + 1:02d}_{j + 1}", "box", [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 - 0.08, (pa[2] + pb[2]) / 2], [0.16, 0.16, sl + 0.1], "frame", None,
                        [-pitch, yaw, 0], outline=False, **vis)
        for i in range(int(rng.integers(2, 4))):  # ---- conduit bundles (3-4 thin pipes on brackets) along L
            v = rng.uniform(-S / 2 + 3, S / 2 - 3)
            if R and abs(v - ov) < R + 2: continue
            u0, u1 = -L / 2 + rng.uniform(1, 10), L / 2 - rng.uniform(1, 10); npipe = int(rng.integers(3, 5))
            for j in range(npipe):
                x, z = P2(u0, v + (j - npipe / 2) * 0.34)
                ctx.add(f"{n}Conduit_{i + 1}_{j + 1}", "cylinder", [x, y - 0.6, z], [0.24, u1 - u0, 0.24], "pipe", None, [90, 0, 0] if along_z else [0, 0, -90], sections=6, outline=False, **vis)
            uu = u0 + 2
            while uu < u1 - 1:
                x, z = P2(uu, v - 0.17); bwid = npipe * 0.34 + 0.3; bn = f"{n}Conduit_{i + 1}_Br_{int(uu) + 1000}"  # tray the pipes rest on, hung from the roof
                ctx.add(bn, "box", [x, y - 0.85, z], [bwid, 0.12, 0.25] if along_z else [0.25, 0.12, bwid], "frame", None, outline=False, **vis)
                for hs in (-1, 1):
                    hx, hz = P2(uu, v - 0.17 + hs * (bwid / 2 - 0.06)); ctx.add(f"{bn}_H{hs + 1}", "box", [hx, y - 0.74, hz], [0.08, 0.72, 0.08], "frame", None, outline=False, **vis)
                uu += rng.uniform(4, 9)
        caps = 0
        for side in (-1, 1):  # ---- green glass capsule tubes along the long walls under the roof (irregular runs)
            u = -L / 2 + rng.uniform(3, 10)
            while u < L / 2 - 6:
                cl = rng.uniform(3, 5.5); v = side * (S / 2 - 1.3); x, z = P2(u, v); caps += 1; cn = f"{n}Capsule_{caps:02d}"
                ctx.add(cn, "cylinder", [x, y - 1.7, z], [0.9, cl, 0.9], ctx.role(C["capsule_role"]) if C.get("capsule_role") else  # Stage 57: e.g. warm "glow_yellow"
                        ("fall" if "fall" in ctx.spec.get("materials", {}).get("roles", {}) else "glow"), None,
                        [90, 0, 0] if along_z else [0, 0, -90], sections=8, outline=False, **vis)
                for j, f_ in enumerate((0.1, 0.5, 0.9)):  # bands inside the tube's length (never flush with its end caps)
                    bx, bz = P2(u + f_ * cl - 0.2, v)
                    ctx.add(f"{cn}_Band_{j + 1}", "cylinder", [bx, y - 1.7, bz], [1.15, 0.4, 1.15], "structure_b", None, [90, 0, 0] if along_z else [0, 0, -90], sections=8, **vis)
                hx, hz = P2(u + cl / 2, v); ctx.add(cn + "_Hanger", "box", [hx, y - 1.7 + 0.45, hz], [0.3, 1.3, 0.3], "frame", None, outline=False, **vis)
                u += cl + rng.uniform(4, 16)
        for f_ in [o for o in ctx.objects if o["name"].startswith(f"{n}Fan_") and o["name"].count("_") == (n + "Fan_1").count("_")]:  # ---- square recess round each fan
            fx_, fy_, fz_ = f_["position"]; hw = f_["size"][0] / 2 + 0.8
            for j, (ox_, oz_, sx_, sz_) in enumerate(((0, -hw, 2 * hw + 0.6, 0.6), (0, hw, 2 * hw + 0.6, 0.6), (-hw, 0, 0.6, 2 * hw - 0.6), (hw, 0, 0.6, 2 * hw - 0.6))):
                ctx.add(f"{f_['name']}_Recess_{j + 1}", "box", [fx_ + ox_, y - 1.25, fz_ + oz_], [sx_, 1.2, sz_], "structure_b", None, **vis)
        for i in range(int(area / 700)):  # ---- red ceiling lights in pairs ("II")
            x, z = cx + rng.uniform(-w / 2 + 2, w / 2 - 2), cz + rng.uniform(-d / 2 + 2, d / 2 - 2)
            if not clear_of_shaft(x, z, 1.5): continue
            uu_ = z - cz if along_z else x - cx
            if any(p_ == pre and abs(uu_ - bu) < 1.2 for p_, bu in getattr(ctx, "_beam_u", [])): continue  # not on a beam line
            rot = [0, float(rng.choice([0, 90])), 0]
            for j, o in enumerate((-0.35, 0.35)):
                ox_, oz_ = local(o, 0, rot[1]); ctx.add(f"{n}Red_{i + 1:02d}_{j + 1}", "box", [x + ox_, y - 0.27, z + oz_], [0.3, 0.2, 1.1], "glow", None, rot, outline=False, **vis)
    ctx.element = None


# ------------------------------------------------------------------ structures
def terrain(ctx, t, floor_y):
    """Natural terrain patch (Stage 8): heightfield over area [x0, z0, x1, z1] rising from the floor (edges stay at floor
    level so it meets the arena floor without cracks), fbm-like hills up to height[1]; skirts close it underneath.
    Registers itself for ground_height() so rocks / buildings placed on it are grounded."""
    import numpy as np
    x0, z0, x1, z1 = t["area"]; c = t.get("cell", 2.0); nx, nz = int(round((x1 - x0) / c)) + 1, int(round((z1 - z0) / c)) + 1
    rng = np.random.default_rng(t.get("seed", 1)); X, Z = np.meshgrid(np.linspace(0, 1, nx), np.linspace(0, 1, nz))
    h = np.zeros_like(X)
    for k in range(4):
        f = 2 ** k * 1.5; h += (0.5 ** k) * np.sin(X * f * 6.28 + rng.uniform(0, 6.28)) * np.cos(Z * f * 5.1 + rng.uniform(0, 6.28))
    h = (h - h.min()) / (np.ptp(h) or 1); edge = np.clip(np.minimum.reduce([X, 1 - X, Z, 1 - Z]) * 4, 0, 1)  # 0 at the border
    lo_, hi_ = t.get("height", [0, 5]); sink = t.get("shore_depth", 0.3)  # border tucked under the floor / liquid: no coplanar seam
    H = floor_y - sink + (lo_ + sink + (hi_ - lo_) * h) * edge
    name = ctx.add(t["id"], "terrain", [x0, 0, z0], None, t.get("material", "rock"), heights=np.round(H, 3).tolist(), cell=c,
                   top_material=ctx.role(t.get("top_material", "foliage")), skirt=3.0)
    ctx.terrains = getattr(ctx, "terrains", []) + [(x0, z0, c, H)]
    if t.get("walkable", True): ctx.walkable.append(dict(name=t["id"], min=[x0 + c, z0 + c], max=[x1 - c, z1 - c], y=float(H.max())))
    return name


def ground_height(ctx, x, z, floor_y, half=0.0):
    """Lowest terrain height under a footprint (centre +- half) - objects sink into slopes instead of floating."""
    if getattr(ctx, "TR", None) is not None:  # Stage 9 world terrain
        import numpy as np
        pts = np.array([(x, z), (x - half, z - half), (x + half, z - half), (x - half, z + half), (x + half, z + half)])
        return float(ctx.TR.height(pts[:, 0], pts[:, 1]).min())
    best = None
    for x0, z0, c, H in getattr(ctx, "terrains", []):
        nz, nx = H.shape
        for px, pz in ((x, z), (x - half, z - half), (x + half, z - half), (x - half, z + half), (x + half, z + half)):
            fx, fz = (px - x0) / c, (pz - z0) / c
            if 0 <= fx <= nx - 1 and 0 <= fz <= nz - 1:
                i, j = min(int(fz), nz - 2), min(int(fx), nx - 2); u, v = fx - j, fz - i
                hh = (H[i, j] * (1 - u) + H[i, j + 1] * u) * (1 - v) + (H[i + 1, j] * (1 - u) + H[i + 1, j + 1] * u) * v
                best = hh if best is None else min(best, hh)
    return floor_y if best is None else float(best)


def _place(ctx, s, plats, floor_y, centre):
    """World base position + yaw for a structure (on a platform, at x/z on the floor, or explicit x/y/z)."""
    if s.get("on"):
        p = plats[s["on"]]; off = s.get("offset", [0, 0]); x, z, y = p["center"][0] + off[0], p["center"][1] + off[1], p["top"]
    else:
        pos = s["position"]; x, z = pos[0], pos[-1]
        half = max(s.get("size", [1, 1, 1])[0], s.get("size", [1, 1, 1])[-1]) / 2 if s["kind"] not in ("rocks", "tree", "lamp", "pillar") else 0.3  # thin bases: ground at the centre
        y = pos[1] if len(pos) == 3 else ground_height(ctx, x, z, floor_y, half) - (0.25 if (getattr(ctx, "terrains", None) or getattr(ctx, "TR", None) is not None) and s["kind"] in ("rocks", "tree") else 0.0)
        if s.get("_pad_y") is not None: y = s["_pad_y"] + s.get("_found", 0.0)  # Stage 9: on its terrain pad, above the foundation
    return x, y, z, structure_yaw(s, x, z, centre)


def structure_yaw(s, x, z, centre):
    if "yaw" in s: yaw = s["yaw"]
    elif s.get("facing", "center") == "center": yaw = yaw_to(centre[0] - x, centre[1] - z) if math.hypot(centre[0] - x, centre[1] - z) > 0.5 else 0.0
    else: yaw = {"north": 180, "south": 0, "east": 90, "west": 270}.get(s["facing"], 0)
    return yaw


def tower(ctx, s, x, y, z, yaw):
    """Industrial tower: bevelled body, wider cap, setback top, corner ribs, banner + glow strips per face, vents.
    Opt-in decor kit (s["decor"]): bands (structural straps), pipes (side conduits), boxes (machinery junction boxes),
    hazard (plinth + worn chevrons), antenna (masts + beacons). Ground-level kit parts stick out <= 0.35 m (inside the
    player capsule radius) and are collision: false, so the tower's collider / navigation stay exactly as before."""
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); dec = s.get("decor", ["banners", "glow_strips", "vents"])
    ctx.add(n + "_Body", "box", [0, 0, 0], [w, h, d], "wall", g)
    ctx.add(n + "_Cap", "box", [0, h, 0], [w + 1, 1.2, d + 1], "structure_b", g)
    if ctx.detail >= 1: ctx.add(n + "_Top", "box", [0, h + 1.2, 0], [w * 0.55, h * 0.12, d * 0.55], "wall", g)
    if ctx.detail >= 1:
        for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            ctx.add(f"{n}_Rib_{i + 1:02d}", "box", [sx * w / 2, 0, sz * d / 2], [0.7, h, 0.7], "structure_b", g)
    for k, (px, pz, fy, fw) in enumerate(((0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d))):
        nx, nz = (px and math.copysign(0.03, px)), (pz and math.copysign(0.03, pz))
        if "banners" in dec:  # emblem (pennant banner materials) centred between the strap bands when there are bands
            at = {"emblem_at": round(((0.42 * h + 0.45 + 0.7 * h) / 2 - 0.3 * h) / (0.5 * h), 3)} if "bands" in dec and h > 6 else {}
            ctx.add(f"{n}_Banner_{k + 1:02d}", "panel", [px + nx, h * 0.3, pz + nz], [min(2.6, fw * 0.4), h * 0.5, 0], "accent", g, [0, fy, 0], **at)
        if "glow_strips" in dec:
            for sd in (-1, 1):
                ox, oz = local(sd * fw * 0.34, 0, fy)
                ctx.add(f"{n}_Glow_{k + 1:02d}{'LR'[sd > 0]}", "panel", [px + nx + ox, h * 0.08, pz + nz + oz], [0.5, h * 0.78, 0], "glow", g, [0, fy, 0])
        if "vents" in dec and ctx.detail >= 2:
            ctx.add(f"{n}_Vent_{k + 1:02d}", "vent", [px + nx * 6, h * 0.86, pz + nz * 6], [fw * 0.4, 0.9, 0.3], "machine", g, [0, fy, 0])
        if "boxes" in dec and h > 6 and k % 2 == 1:  # machinery junction boxes with indicator lights on two faces (shared material)
            ox, oz = local(0, 0.17, fy); ctx.add(f"{n}_Box_{k + 1:02d}", "box", [px + ox, h * 0.12, pz + oz], [min(1.6, fw * 0.45), min(2.2, h * 0.14), 0.34], "machine", g, [0, fy, 0], collision=False)
        if "pipes" in dec and h > 6 and k in (1, 3):  # vertical conduits up the side faces, standing on the floor
            for sd in (-1, 1):
                ox, oz = local(sd * fw * 0.18, 0.17, fy)
                ctx.add(f"{n}_Pipe_{k + 1:02d}{'LR'[sd > 0]}", "cylinder", [px + ox, 0, pz + oz], [0.32, h * 0.92, 0.32], "frame", g, sections=8, collision=False)
    hz = max(0.6, min(1.2, h * 0.06))
    if "bands" in dec and h > 6:  # structural straps: break the silhouette, read at gameplay distance
        for i, f in enumerate((0.42, 0.7)):
            ctx.add(f"{n}_Band_{i + 1}", "box", [0, h * f, 0], [w + 0.36, 0.45, d + 0.36], "structure_b", g)
    if "hazard" in dec and h > 4:  # reinforced plinth with worn hazard chevrons on every face
        ctx.add(n + "_Plinth", "box", [0, 0, 0], [w + 0.5, hz, d + 0.5], "structure_b", g, collision=False)
        for k, (px, pz, fy, fw) in enumerate(((0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d))):
            ox, oz = local(0, 0.27, fy); ctx.add(f"{n}_Chevron_{k + 1:02d}", "panel", [px + ox, hz * 0.18, pz + oz], [fw + 0.3, hz * 0.62, 0], "stripe", g, [0, fy, 0])
    if "antenna" in dec and h > 10:  # masts with red beacons on the roof
        top = h + 1.2 + (h * 0.12 if ctx.detail >= 1 else 0)
        for i, (ax, az, hh) in enumerate(((w * 0.12, d * 0.1, h * 0.28), (-w * 0.15, -d * 0.12, h * 0.18))):
            ctx.add(f"{n}_Mast_{i + 1}", "cylinder", [ax, top, az], [0.18, hh, 0.18], "frame", g, sections=6)
            ctx.add(f"{n}_Beacon_{i + 1}", "box", [ax, top + hh, az], [0.32, 0.32, 0.32], "trim", g)
    ctx.platform_blocks = getattr(ctx, "platform_blocks", []) + [(x, z, max(w, d) / 2 + 0.6)]


def building(ctx, s, x, y, z, yaw):
    """Industrial hall / block: body, roof clutter (vents, tank), lit window strip + door on the front (+z)."""
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Body", "box", [0, 0, 0], [w, h, d], "wall", g)
    ctx.add(n + "_Parapet", "box", [0, h, 0], [w + 0.4, 0.6, d + 0.4], "trim", g)
    if s.get("roof", "flat") in ("gable", "hip"): ctx.add(n + "_Roof", "hip_roof" if s["roof"] == "hip" else "roof", [0, h + 0.6, 0], [w, min(w, d) * 0.3, d], "structure_b", g, overhang=0.3)
    elif ctx.detail >= 1:
        ctx.add(n + "_RoofUnit", "machinery", [-w * 0.2, h + 0.6, 0], [min(4, w * 0.4), 2.2, min(3, d * 0.4)], "machine", g, seed=_h(n) % 97)
        if ctx.detail >= 2: ctx.add(n + "_Tank", "tank", [w * 0.28, h + 0.6, -d * 0.15], [2.2, 3.5, 2.2], "pipe", g)
    ctx.add(n + "_Windows", "panel", [0, h * 0.62, d / 2 + 0.03], [w * 0.8, min(1.4, h * 0.15), 0], "glow" if s.get("lit", True) else "window", g)
    ctx.add(n + "_Door", "panel", [0, 0, d / 2 + 0.03], [min(4, w * 0.3), min(4.5, h * 0.4), 0], "structure_b", g)


def house(ctx, s, x, y, z, yaw):
    """Town house: stone ground floor, timber-framed / plaster / stone upper floors with jetties, gable or hip roof,
    chimney, windows and door on the front (+z) and sides. Size = footprint w x d, h = eaves height."""
    n = s["id"]; w, h, d = s["size"]; st = s.get("style", "timber"); floors = max(1, int(s.get("floors", max(1, round(h / 3.2)))))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); fh = h / floors; jet = 0.35 if st == "timber" else 0.0
    ctx.add(n + "_Ground", "box", [0, 0, 0], [w, fh, d], "stone" if st != "plaster" else "plaster", g)
    for f in range(1, floors):
        k = f * jet; ctx.add(f"{n}_Floor_{f + 1}", "box", [0, f * fh, k / 2], [w + k * 0.0, fh, d + k], "plaster" if st in ("timber", "plaster") else "stone", g)
        if st == "timber":  # timber framing on front + sides: posts, sill/head rails, braces
            for face, (fx, fz, fy, fw) in enumerate(((0, (d + k) / 2 + k / 2, 0, w), (w / 2, k / 2, 90, d + k), (-w / 2, k / 2, 270, d + k))):
                nposts = max(2, int(fw / 1.4)) + 1
                for i in range(nposts):
                    ox, oz = local(-fw / 2 + 0.12 + (fw - 0.24) * i / (nposts - 1), 0.06, fy)
                    ctx.add(f"{n}_Post_{f + 1}{face}{i:02d}", "box", [fx + ox, f * fh, fz + oz], [0.18, fh, 0.12], "timber", g, [0, fy, 0])
                ox, oz = local(0, 0.06, fy)
                ctx.add(f"{n}_Rail_{f + 1}{face}", "box", [fx + ox, f * fh, fz + oz], [fw + 0.1, 0.2, 0.14], "timber", g, [0, fy, 0])
                if ctx.detail >= 1:
                    ctx.add(f"{n}_Mid_{f + 1}{face}", "box", [fx + ox, f * fh + fh * 0.45, fz + oz], [fw, 0.14, 0.12], "timber", g, [0, fy, 0])
    top_k = (floors - 1) * jet; dd = d + top_k
    # windows + door
    for f in range(floors):
        k = f * jet; nwin = max(1, int(w / 2.4))
        for i in range(nwin):
            wx = -w / 2 + w * (i + 0.5) / nwin
            if f == 0 and i == nwin // 2: continue
            ctx.add(f"{n}_Win_{f + 1}{i:02d}", "panel", [wx, f * fh + fh * 0.35, (d + k) / 2 + k / 2 + 0.08], [0.9, min(1.3, fh * 0.4), 0], "window", g)
    ctx.add(n + "_Door", "panel", [0, 0, d / 2 + 0.05], [1.3, min(2.4, fh * 0.75), 0], "door", g)
    roof = s.get("roof", "gable"); rh = s.get("roof_height", min(w, dd) * 0.55)
    if roof == "gable": ctx.add(n + "_Roof", "roof", [0, h, top_k / 2], [w + 0.6, rh, dd + 0.6], "roof", g)
    elif roof == "hip": ctx.add(n + "_Roof", "hip_roof", [0, h, top_k / 2], [w, rh, dd], "roof", g, overhang=0.35)
    else: ctx.add(n + "_Roof", "box", [0, h, top_k / 2], [w + 0.3, 0.4, dd + 0.3], "trim", g)
    if s.get("chimney", ctx.detail >= 1):
        ctx.add(n + "_Chimney", "box", [w * 0.3, h + rh * 0.3, -d * 0.15], [0.7, rh * 0.85, 0.7], "stone", g)


def stone_tower(ctx, s, x, y, z, yaw):
    """Stone / gothic tower: body with string courses, corner buttresses, slit windows, battlements or a spire."""
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Body", "box", [0, 0, 0], [w, h, d], "stone", g)
    for i in range(1, max(2, int(h / 7))):
        ctx.add(f"{n}_Course_{i:02d}", "box", [0, h * i / max(2, int(h / 7)), 0], [w + 0.3, 0.35, d + 0.3], "trim", g)
    ctx.add(n + "_Corbel", "box", [0, h, 0], [w + 0.8, 0.6, d + 0.8], "trim", g)
    if ctx.detail >= 1:
        for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            ctx.add(f"{n}_Buttress_{i + 1:02d}", "box", [sx * (w / 2), 0, sz * (d / 2)], [1.0, h * 0.85, 1.0], "structure", g)
    for k, (px, pz, fy, fw) in enumerate(((0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d))):
        nx, nz = (px and math.copysign(0.04, px)), (pz and math.copysign(0.04, pz))
        for lvl in range(1, max(2, int(h / 7))):
            ctx.add(f"{n}_Window_{k + 1}{lvl:02d}", "panel", [px + nx, h * lvl / max(2, int(h / 7)) - 2.6, pz + nz], [min(1.2, fw * 0.2), 2.0, 0], "window", g, [0, fy, 0])
    top = s.get("roof", "crenellated")
    if top in ("crenellated", "battlements"):
        ctx.add(n + "_Battlements", "battlement", [0, h + 0.6, 0], [w + 0.8, 1.2, d + 0.8], "stone", g)
        if ctx.detail >= 1:
            for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
                ctx.add(f"{n}_Pinnacle_{i + 1:02d}", "spire", [sx * (w / 2 + 0.2), h + 0.6, sz * (d / 2 + 0.2)], [1.1, 3.0, 1.1], "trim", g)
    elif top == "spire": ctx.add(n + "_Spire", "spire", [0, h + 0.6, 0], [w + 0.4, h * 0.6, d + 0.4], "roof_slate", g)
    elif top == "hip": ctx.add(n + "_Roof", "hip_roof", [0, h + 0.6, 0], [w, min(w, d) * 0.6, d], "roof", g, overhang=0.4)


def party_walls(ctx):
    """Buildings standing wall-to-wall: side decoration (timber posts / rails / windows) that would sit flat against the
    neighbour's wall is removed (it could never be seen and would z-fight). Generic: any group with a _Body / _Ground."""
    by = {o["name"]: o for o in ctx.objects}; boxes = []
    for o in ctx.objects:
        if o["type"] != "group" or o.get("parent"): continue
        body = by.get(o["name"] + "_Ground") or by.get(o["name"] + "_Body")
        if not body: continue
        w, h, d = body["size"]; extra = max([k["size"][2] for k in ctx.objects if k.get("parent") == o["name"] and "_Floor_" in k["name"]] or [d])
        boxes.append((o["name"], o["position"][0], o["position"][2], o["rotation"][1], w / 2 + 0.3, max(d, extra) / 2 + 0.3))

    def inside(px, pz, b):
        _, cx, cz, yw, hw, hd = b; lx, lz = local(px - cx, pz - cz, -yw); return abs(lx) <= hw and abs(lz) <= hd
    drop = set(); bnames = {b[0] for b in boxes}
    for o in ctx.objects:
        p = o.get("parent")
        if not p or p not in bnames: continue  # only decoration of buildings, matched on the part name after the group's own name
        part = o["name"][len(p):] if o["name"].startswith(p) else ""
        if not any(part.startswith(t) for t in ("_Post_", "_Rail_", "_Mid_", "_Win_")): continue
        g = by[p]; ox, oz = local(o["position"][0], o["position"][2], g["rotation"][1]); wx, wz = g["position"][0] + ox, g["position"][2] + oz
        if any(inside(wx, wz, b) for b in boxes if b[0] != p): drop.add(o["name"])
    if drop:
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
        ctx.notes.append(f"party walls: {len(drop)} hidden side decorations removed between touching buildings")


def fountain(ctx, s, x, y, z, yaw):
    n = s["id"]; w = s.get("size", [8, 3, 8])[0]; g = ctx.add(n, "group", [x, y, z])
    ctx.add(n + "_Step", "cylinder", [0, 0, 0], [w + 1.2, 0.3, w + 1.2], "stone", g, sections=16)
    ctx.add(n + "_Basin", "cylinder", [0, 0.3, 0], [w, 0.75, w], "stone", g, sections=16)
    ctx.add(n + "_Water", "cylinder", [0, 0.3, 0], [w - 0.6, 0.65, w - 0.6], "water", g, sections=16)
    ctx.add(n + "_Column", "cylinder", [0, 0.3, 0], [0.9, 2.2, 0.9], "stone", g, sections=10)
    ctx.add(n + "_Bowl", "cylinder", [0, 2.5, 0], [w * 0.35, 0.45, w * 0.35], "stone", g, sections=12)
    ctx.add(n + "_Top", "cylinder", [0, 2.95, 0], [0.4, 1.0, 0.4], "stone", g, sections=8)
    ctx.fountains = getattr(ctx, "fountains", []) + [n + "_Water"]


def gate(ctx, s, x, y, z, yaw):
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Arch", "round_arch" if s.get("round", True) else "arch", [0, 0, 0], [w, h, d], s.get("material", "stone" if ctx.theme["wall_style"] == "stone" else "wall"), g, opening=s.get("opening", 0.55))
    if ctx.detail >= 1: ctx.add(n + "_Cap", "box", [0, h, 0], [w + 0.4, 0.5, d + 0.4], "trim", g)


def wall_struct(ctx, s, x, y, z, yaw):
    a, b = s["from"], s["to"]; wall_segment(ctx, s["id"], a, b, s.get("height", 6), s.get("thickness", 1.5), y, s.get("style", ctx.theme["wall_style"]), s.get("inner"))


def machinery(ctx, s, x, y, z, yaw):
    pl = next((p for p in ctx.spec.get("platforms", []) if p["id"] == s.get("on")), None)
    def on_deck(o):  # Stage 41: parts that would hang over the deck edge are left out (the bank stays where it was put)
        if not pl or o.get("type") == "group": return True
        (pcx, pcz), (pw, pd) = pl["center"], pl["size"]; u = o["position"][0]; hw, hd = o["size"][0] / 2, o["size"][2] / 2
        for a_ in (u - hw, u + hw):
            for b_ in (-hd, hd):
                wx, wz = local(a_, b_, yaw)
                if not (pcx - pw / 2 - 0.05 <= x + wx <= pcx + pw / 2 + 0.05 and pcz - pd / 2 - 0.05 <= z + wz <= pcz + pd / 2 + 0.05): return False
        return True
    for o in prefabs.machinery_bank(s["id"], [x, y, z], yaw, seed=_h(s["id"]) % 97, material="machine", tank_material="pipe"):
        if on_deck(o): _adopt(ctx, o)
        else: ctx.notes.append(f"{o['name']}: left out - it would hang over the edge of {pl['id']}")


def tank(ctx, s, x, y, z, yaw):
    w, h, d = s.get("size", [3, 5, 3]); ctx.add(s["id"], "tank", [x, y, z], [w, h, d], s.get("material", "pipe"), rot=[0, yaw, 0])


def pillar(ctx, s, x, y, z, yaw):
    w, h, d = s.get("size", [1.2, 6, 1.2]); n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Shaft", "cylinder" if s.get("round", True) else "box", [0, 0, 0], [w, h, d], s.get("material", "stone" if ctx.theme["wall_style"] == "stone" else "structure"), g, sections=10)
    ctx.add(n + "_Capital", "box", [0, h, 0], [w * 1.4, 0.4, d * 1.4], "trim", g)


def lamp(ctx, s, x, y, z, yaw):
    n = s["id"]; h = s.get("size", [0.3, 4, 0.3])[1]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Post", "cylinder", [0, 0, 0], [0.22, h, 0.22], "frame" if ctx.theme["wall_style"] != "stone" else "pipe", g, sections=6)
    ctx.add(n + "_Light", "box", [0, h, 0], [0.5, 0.6, 0.5], "glow", g)


def crates(ctx, s, x, y, z, yaw):
    n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); ch = ctx.G["design"]["cover_height"]
    for i, (ox, oy, oz) in enumerate(((0, 0, 0), (1.7, 0, 0.2), (0.8, ch, 0.1))[:int(s.get("count", 3))]):
        ctx.add(f"{n}_{i + 1:02d}", "box", [ox, oy, oz], [1.5, ch, 1.5], s.get("material", "structure_b"), g)


def rocks(ctx, s, x, y, z, yaw):
    for o in prefabs.rock_cluster(s["id"], [x, y, z], radius=s.get("radius", 5), count=s.get("count", 5), seed=_h(s["id"]) % 97, material="rock"):
        _adopt(ctx, o)


def tree(ctx, s, x, y, z, yaw):
    n = s["id"]; h = s.get("size", [4, 7, 4])[1]; w = s.get("size", [4, 7, 4])[0]; g = ctx.add(n, "group", [x, y, z])
    ctx.add(n + "_Trunk", "cylinder", [0, 0, 0], [0.5, h * 0.5, 0.5], "timber", g, sections=6)
    ctx.add(n + "_Crown", "rock", [0, h * 0.4, 0], [w, h * 0.6, w], "foliage", g, seed=_h(n) % 97)


def banner(ctx, s, x, y, z, yaw):
    w, h = s.get("size", [2.2, 5, 0])[:2]; ctx.add(s["id"], "panel", [x, y, z], [w, h, 0], "accent", rot=[0, yaw, 0])


def _adopt(ctx, o):
    """Prefab objects (pf_* materials): keep geometry, map materials onto roles."""
    o = dict(o); name = o.pop("name"); typ = o.pop("type"); pos = o.pop("position", [0, 0, 0]); size = o.pop("size", None)
    mat = o.pop("material", None); par = o.pop("parent", None); rot = o.pop("rotation", [0, 0, 0])
    mat = {"pf_metal": "frame", "pf_grating": "grate", "pf_rail": "rail", "pf_pipe": "pipe", "pf_rock": "rock", "pf_machine": "machine", "pf_concrete": "structure"}.get(mat, mat)
    ctx.add(name, typ, pos, size, mat, par, rot, **o)


STRUCTURES = dict(tower=tower, building=building, house=house, stone_tower=stone_tower, fountain=fountain, gate=gate, arch=gate,
                  wall=wall_struct, machinery=machinery, tank=tank, pillar=pillar, lamp=lamp, crates=crates, rocks=rocks, tree=tree, banner=banner)


# ------------------------------------------------------------------ pipes
def pipe(ctx, p, floor_y, arena_spec):
    """Pipes and liquid outlets (Stage 8). The liquid is a "stream" that starts INSIDE the real opening (same direction,
    cross-section matched to the opening), follows a gravity arc and ends submerged in the receiving pool; relations
    emits_from / flows_into record the attachment (anchors: pipe.outlet -> stream.source, stream.sink -> pool).
    outlet: "circle" (round pipe, default) | "drain" (rectangular channel through the wall) | "spillway" (wide open
    channel, sheet of liquid) | "vertical" (pipe pointing down, straight column) | "broken" (round pipe, weak tilted gush)."""
    if p.get("kind", "outlet") == "run":
        for o in prefabs.pipe_run(p["id"], p["points"], radius=p.get("radius", 0.5), material="pipe", junction="frame"): _adopt(ctx, o)
        if p.get("fitting", True):  # Stage 36: fittings where the run comes out of a wall
            pts_ = [np.asarray(q, float) for q in p["points"]]
            for k_, (a_, b_) in enumerate(((pts_[0], pts_[1]), (pts_[-1], pts_[-2]))):
                v_ = b_ - a_; v_[1] = 0.0; Lv = float(np.linalg.norm(v_))
                if Lv < 1e-6 or abs(b_[1] - a_[1]) > 0.1 * Lv: continue
                dd_ = v_ / Lv
                if _on_wall(ctx, a_[0], a_[2], dd_[0], dd_[2]): wall_fitting(ctx, f"{p['id']}_End{k_ + 1}", tuple(a_), (dd_[0], dd_[2]), p.get("radius", 0.5))
        cy_, r_ = getattr(ctx, "ceiling_y", None), p.get("radius", 0.5)
        if cy_ is not None and p.get("hangers", True):  # Stage 31: overhead runs hang from the roof on rods (every ~8 m)
            pts = [np.asarray(q, float) for q in p["points"]]; k = 0
            for a_, b_ in zip(pts, pts[1:]):
                v = b_ - a_; Ls = float(np.linalg.norm(v))
                if Ls < 1 or abs(v[1]) > 0.1 * Ls or cy_ - a_[1] < r_ + 0.5: continue  # horizontal segments under the roof only
                m = max(1, int(Ls // 8))
                for i in range(m):
                    q = a_ + v * (i + 0.5) / m; k += 1; y0 = q[1] + r_ - 0.05
                    ctx.add(f"{p['id']}_Hanger_{k:02d}", "box", [q[0], y0, q[2]], [0.18, cy_ - y0 + 0.05, 0.18], "frame", collision=False, outline=False, mobile={"static": True})
                    ctx.add(f"{p['id']}_Clamp_{k:02d}", "box", [q[0], q[1] - r_ - 0.08, q[2]], [0.3, 2 * r_ + 0.16, 2 * r_ + 0.16] if abs(v[0]) > abs(v[2]) else [2 * r_ + 0.16, 2 * r_ + 0.16, 0.3],
                            "frame", collision=False, outline=False, mobile={"static": True})
        return
    out_t = p.get("outlet", "circle"); r = p.get("radius", 1.2); L = p.get("length", 8.0); y = p.get("y", 9.0); embed = 0.0; corner = False
    if "position" in p: x, z = p["position"][0], p["position"][-1]; yaw = p.get("yaw", 0); y = p["position"][1] if len(p["position"]) == 3 else y
    else:  # on the inner face of an arena wall: side + offset along it, pointing inwards; base embedded in the wall
        (cx, cz), (w, d) = arena_spec.get("center", [0, 0]), arena_spec["size"]; side = p["wall"].lower(); at = p.get("at", 0)
        corners = {"ne": (1, -1), "nw": (-1, -1), "se": (1, 1), "sw": (-1, 1)}
        if side in corners:  # corner pipe: start inside the wall corner so the whole cap is buried (no gap behind it)
            sx, sz = corners[side]; embed = r * 1.1 + 0.3; x, z = cx + sx * (w / 2 + embed / math.sqrt(2)), cz + sz * (d / 2 + embed / math.sqrt(2)); yaw = yaw_to(-sx, -sz); corner = True
        else:
            sx, sz = SIDES[side]; embed = 0.4; x = cx + sx * (w / 2 + embed) + (at if sz else 0); z = cz + sz * (d / 2 + embed) + (at if sx else 0); yaw = yaw_to(-sx, -sz)
    L += embed; dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw)); n = p["id"]; ox, oz = x + dx * L, z + dz * L
    on_face = not embed and "position" in p and out_t in ("circle", "broken") and _on_wall(ctx, x, z, dx, dz, tol=0.3)
    if (embed or on_face) and out_t in ("circle", "broken") and p.get("fitting", True):  # Stage 36: a proper fitting where it leaves the wall
        wall_fitting(ctx, n, (x + dx * embed, y, z + dz * embed), (dx, dz), r, corner=corner)  # Stage 51: also pipes placed by "position" on a wall face
    mat = p.get("pour_material", "hazard"); by_ = {o["name"]: o for o in ctx.objects}
    def _in(h, px, pz):
        o = by_.get(h); return o is not None and o.get("size") and abs(px - o["position"][0]) <= o["size"][0] / 2 and abs(pz - o["position"][2]) <= o["size"][2] / 2
    pool = next((h for h in ctx.hazards if _in(h, x + dx * L, z + dz * L)), (ctx.hazards or [None])[0])  # the pool under the outlet (annexes have their own)
    if out_t in ("circle", "broken", "vertical"):
        if out_t == "vertical":  # pipe hanging down from (x, y, z): outlet at the bottom
            src = ctx.add(n, "cylinder", [x, y, z], [2 * r, L, 2 * r], "pipe", rot=[180, 0, 0], sections=10); oy = y - L; ox, oz = x, z
            cy_ = getattr(ctx, "ceiling_y", None)
            if cy_ is not None and cy_ - y > 0.3:  # Stage 31: fed from the roof - never a pipe hanging in mid-air
                ctx.add(n + "_Feed", "cylinder", [x, y - 0.1, z], [2 * r * 0.8, cy_ - y + 0.08, 2 * r * 0.8], "pipe", sections=10, collision=False)
                ctx.add(n + "_RoofPlate", "box", [x, cy_ - 0.24, z], [2 * r * 1.8, 0.22, 2 * r * 1.8], "frame", collision=False)
        else:
            src = ctx.add(n, "cylinder", [x, y, z], [2 * r, L, 2 * r], "pipe", rot=[90, yaw, 0], sections=10); oy = y
        if ctx.detail >= 1 and out_t != "broken":
            fl = L - 0.47  # flange ends 2 cm behind the mouth: no coplanar end discs
            if out_t == "vertical": ctx.add(n + "_Flange", "cylinder", [x, y - fl, z], [2 * r * 1.25, 0.45, 2 * r * 1.25], "frame", rot=[180, 0, 0], sections=10)
            else: ctx.add(n + "_Flange", "cylinder", [x + dx * fl, y, z + dz * fl], [2 * r * 1.25, 0.45, 2 * r * 1.25], "frame", rot=[90, yaw, 0], sections=10)
        if ctx.detail >= 1 and out_t != "vertical" and embed == 0.0 and not on_face and p.get("mount", True):  # free-standing pipe: wall plate (arena pipes are embedded in the wall)
            ctx.add(n + "_Mount", "box", [x + dx * 0.3, y - r * 1.3, z + dz * 0.3], [r * 2.6, r * 2.6, 0.6], "frame", rot=[0, yaw, 0])
        sec, sw, sd, anchor = "circle", 2 * r * 0.86, 2 * r * 0.86, "outlet"
        pitch = -90 if out_t == "vertical" else (-20 if out_t == "broken" else 0); speed = 0 if out_t == "vertical" else (0.8 if out_t == "broken" else round(1.2 + 0.5 * r, 2))
    else:  # drain / spillway: open rectangular channel through the wall
        cw = p.get("width", 2 * r if out_t == "drain" else 6.0); chh = 0.7 if out_t == "drain" else 0.5
        src = ctx.add(n, "channel", [x + dx * L / 2, y - 0.2, z + dz * L / 2], [cw, chh, L], "structure_b", rot=[0, yaw, 0], wall=0.2)
        ctx.add(n + "_Liquid", "box", [x + dx * (L / 2 - 0.1), y, z + dz * (L / 2 - 0.1)], [cw - 0.42, 0.12, L - 0.2], mat, rot=[0, yaw, 0])
        if p.get("mouth", True): outlet_mouth(ctx, n, x, y - 0.2, z, yaw, cw, chh)  # Stage 30: a real opening in the wall it pours from
        sec, sw, sd, anchor = ("rect", cw - 0.4, 0.3, "outlet") if out_t == "drain" else ("rect", cw - 0.4, 0.18, "outlet")  # spillway: thin sheet
        pitch, speed, oy = 0, 1.0, y; ox, oz = x + dx * L, z + dz * L
    if p.get("pour", True):
        drop = oy - floor_y + 0.3
        st = ctx.add(n + "_Fall", "stream", [ox, oy, oz], [round(sw, 3), round(drop, 3), round(sd, 3)], mat, rot=[0, yaw if out_t != "vertical" else 0, 0],
                     section=sec, speed=speed, pitch=pitch, inset=0.25 if out_t != "vertical" else 0.3)
        ctx.rel("emits_from", st, src, b_anchor=anchor)
        if pool: ctx.rel("flows_into", st, pool)
        ctx.pours.append(st)


def _on_wall(ctx, x, z, dx, dz, tol=0.15):
    """True when (x, z) lies on an inner wall face of the arena / an annex and (dx, dz) points into that room."""
    for a in [ctx.spec.get("arena") or {}] + list(ctx.spec.get("annexes") or []):
        if not a.get("size"): continue
        (cx, cz), (w, d) = a.get("center", [0, 0]), a["size"]
        if not (cx - w / 2 - tol <= x <= cx + w / 2 + tol and cz - d / 2 - tol <= z <= cz + d / 2 + tol): continue
        if abs(x - (cx - w / 2)) < tol and dx > 0.7 or abs(x - (cx + w / 2)) < tol and dx < -0.7: return True
        if abs(z - (cz - d / 2)) < tol and dz > 0.7 or abs(z - (cz + d / 2)) < tol and dz < -0.7: return True
    return False


def wall_fitting(ctx, n, P, d, r, corner=False):
    """Stage 36: where a pipe of radius r comes out of a wall at P = (x, y, z) (axis height y) heading along d = (dx, dz):
    a square mounting plate on the wall face with four bolts, a hazard stripe across its top and a red light, and a
    flange collar round the pipe. Into a corner (no flat face): a thick boot round the pipe and the flange collar.
    Visual only; existing materials (frame, structure_b, machine, stripe, glow)."""
    x, y, z = P; dx, dz = d; yaw = math.degrees(math.atan2(dx, dz)); st = dict(collision=False, mobile={"static": True})
    at = lambda t: [x + dx * t, y, z + dz * t]
    if corner:
        ctx.add(n + "_Boot", "cylinder", at(-0.6), [2 * r * 1.22, r + 1.5, 2 * r * 1.22], "frame", None, [90, yaw, 0], sections=10, **st)
        ctx.add(n + "_Collar", "cylinder", at(r + 0.88), [2 * r * 1.38, 0.4, 2 * r * 1.38], "structure_b", None, [90, yaw, 0], sections=10, **st)
        return
    S = 2 * r + 1.2; px, pz = x + dx * 0.0, z + dz * 0.0
    ctx.add(n + "_Plate", "box", [px + dx * 0.14, y - S / 2, pz + dz * 0.14], [S, S, 0.32], "frame", None, [0, yaw, 0], **st)  # back 2 cm into the wall (pipe ends sit at the face)
    ctx.add(n + "_Collar", "cylinder", at(0.28), [2 * r * 1.32, 0.42, 2 * r * 1.32], "structure_b", None, [90, yaw, 0], sections=10, **st)
    ux, uz = dz, -dx  # along the wall
    for i, (a_, b_) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):  # bolts in the plate's corners
        o = S / 2 - 0.3
        ctx.add(f"{n}_Bolt_{i + 1}", "box", [px + ux * a_ * o + dx * 0.27, y + b_ * o - 0.11, pz + uz * a_ * o + dz * 0.27], [0.22, 0.22, 0.14], "machine", None, [0, yaw, 0],
                outline=False, **st)
    ctx.add(n + "_Stripe", "box", [px + dx * 0.29, y + S / 2 - 0.42, pz + dz * 0.29], [S - 1.0, 0.24, 0.06], "stripe", None, [0, yaw, 0], outline=False, **st)
    ctx.add(n + "_Light", "box", [px + ux * (S / 2 - 0.3) + dx * 0.29, y - S / 2 + 0.3, pz + uz * (S / 2 - 0.3) + dz * 0.29], [0.26, 0.16, 0.06], "glow", None, [0, yaw, 0],
            outline=False, **st)


def screen_slot(ctx, role, base):
    """Stage 52: (atlas cell, id) for the next screen of `role`. Screens are numbered 1, 2, 3 ... per role; the id goes
    into the panel's UVs as a whole-number u shift (same texels - the texture repeats) so the screen shader can tell
    screens apart (own flicker timing / tint, the easter egg). With a 2x2 atlas (cells a-d) the picture varies too:
    TVs cycle a, b, c (d is reserved for the easter egg when "egg" is set); window fills alternate a/c (broadcast)
    and b/d (specimen)."""
    n = getattr(ctx, "screen_ids", {}); n[role] = n.get(role, 0) + 1; ctx.screen_ids = n; i = n[role]
    R = (ctx.spec.get("materials", {}).get("roles", {}).get(role) or {}); atl = R.get("atlas") or {}
    if not {"c", "d"} <= set(atl): return base, i
    if role == "screen": return ("a", "b", "c")[(i - 1) % 3] if R.get("egg") else ("a", "b", "c", "d")[(i - 1) % 4], i
    k = n.get(role + base, 0) + 1; n[role + base] = k  # alternate the two variants of each kind
    return {"a": ("a", "c"), "b": ("b", "d")}.get(base, (base, base))[(k - 1) % 2], i


def _wall_at(ctx, px, py, pz, d=None):
    """(material, metres to the wall face) of the wall body containing world point (px, py, pz), or None. The distance
    runs along d (x, z) from (px, pz) + d * 0.5 m to the body's face pointing that way."""
    from anchors import world_matrices
    W, by = world_matrices({"objects": ctx.objects})
    for o in ctx.objects:
        if not o["name"].endswith("_Body") or o["type"] != "box" or not o.get("size"): continue
        M = W[o["name"]]; Mi = np.linalg.inv(M); q = Mi @ np.array([px, py, pz, 1.0]); w, h, dd = o["size"]
        if not (abs(q[0]) <= w / 2 and 0 <= q[1] <= h and abs(q[2]) <= dd / 2): continue
        if d is None: return o.get("material"), 0.0
        dl = Mi[:3, :3] @ np.array([d[0], 0.0, d[1]]); k = 0 if abs(dl[0]) > abs(dl[2]) else 2; sg = np.sign(dl[k]) or 1.0
        half = (w if k == 0 else dd) / 2; return o.get("material"), float((sg * half - q[k]) * sg) - 0.5
    return None


def outlet_mouth(ctx, n, x, y0, z, yaw, cw, chh, depth=1.4, rise=2.4):
    """Stage 30: housing round a drain / spillway where it leaves the wall, so the liquid comes OUT of an opening: jambs,
    sill and lintel in the surrounding wall's own texture jutting depth m from the face, a dark tunnel back (accent atlas
    "void" cell), a structure_b trim round the mouth and a hazard stripe on the lintel. Only where a wall is right
    behind (x, z) - free-standing channels keep their old look; the housing sits on that wall's face even when the
    channel starts inside the wall. Visual only (no collision), no new materials."""
    dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    hit = _wall_at(ctx, x - dx * 0.5, y0 + 0.5, z - dz * 0.5, (dx, dz))
    if hit is None: return None
    wm, gap = hit; x, z = x + dx * gap, z + dz * gap  # sit on the wall's face (the channel may start inside the wall)
    mw, mh, j, D = cw + 0.5, chh + rise, 0.9, depth; st = dict(collision=False, mobile={"static": True})
    g = ctx.add(n + "_Mouth", "group", [x, y0, z], rot=[0, yaw, 0])
    for s_ in (-1, 1): ctx.add(f"{n}_Mouth_Jamb_{s_ + 1}", "box", [s_ * (mw / 2 + j / 2), -0.8, D / 2], [j, mh + 0.8, D], wm, g, uv_space="world", **st)
    ctx.add(n + "_Mouth_Lintel", "box", [0, mh, D / 2], [mw + 2 * j, 1.1, D], wm, g, uv_space="world", **st)
    ctx.add(n + "_Mouth_Sill", "box", [0, -0.8, D / 2], [mw, 0.76, D], wm, g, uv_space="world", **st)
    ctx.add(n + "_Mouth_Dark", "panel", [0, -0.04, 0.03], [mw, mh + 0.04, 0], ctx.role("accent"), g, uv_region="void", outline=False, **st)  # the tunnel going in
    for s_ in (-1, 1): ctx.add(f"{n}_Mouth_Trim_{s_ + 1}", "box", [s_ * (mw / 2 + 0.2), -0.8, D + 0.06], [0.4, mh + 1.9, 0.12], ctx.role("structure_b"), g, outline=False, **st)
    ctx.add(n + "_Mouth_TrimTop", "box", [0, mh + 0.7, D + 0.06], [mw, 0.4, 0.12], ctx.role("structure_b"), g, outline=False, **st)
    ctx.add(n + "_Mouth_Stripe", "box", [0, mh + 0.2, D + 0.04], [mw - 0.2, 0.36, 0.1], ctx.role("stripe"), g, outline=False, **st)
    return g


def _aabb_all(ctx):
    """{name: (lo, hi)} world boxes of every sized, non-group object."""
    from anchors import world_matrices
    W, _ = world_matrices({"objects": ctx.objects}); out = {}
    for o in ctx.objects:
        if o["type"] in ("group", "band") or not o.get("size"): continue
        w_, h_, d_ = o["size"]; C = np.array([[sx * w_ / 2, yy, sz * d_ / 2, 1] for sx in (-1, 1) for yy in (0, h_) for sz in (-1, 1)]) @ W[o["name"]].T
        out[o["name"]] = (C[:, :3].min(0), C[:, :3].max(0))
    return out


def _ceiling_boxes(ctx, y, depth):
    """World boxes of the ceiling parts hanging within `depth` m under the roof (y), except the roof slab itself."""
    return [b for n, b in _aabb_all(ctx).items() if b[1][1] > y - depth and b[0][1] < y - 0.05 and not n.endswith("Ceiling_Slab")]


THIN = ("Hanger", "Cable", "Clamp", "Bracket", "Strut", "Rod", "Chain")


def clear_fixtures(ctx, pad=0.05):
    """Stage 37: nothing pokes into fans and vents. For every ceiling fan (<room>Fan_<n>) and wall Fan / Vent module:
    thin fixtures (hangers, cables, clamps, brackets ...) that cut into it are removed; a wall module that anything
    else cuts into (crane rail, pipe run, fitting ...) is removed itself - the bigger thing stays."""
    import re
    B = _aabb_all(ctx); units = {}
    for n in B:
        m_ = re.match(r"^(.*?(?:Fan_\d+|_M\d\d(?:Fan|Vent)))(?:_|$)", n)
        if m_: units.setdefault(m_.group(1), []).append(n)
    drop, gone_units = set(), set()
    for u, parts in units.items():
        lo = np.min([B[p][0] for p in parts], 0) - pad; hi = np.max([B[p][1] for p in parts], 0) + pad
        wall_unit = "_M" in u
        for n, (a, b) in B.items():
            if n in drop or n.startswith(u) or (np.minimum(hi, b) - np.maximum(lo, a) <= 0.02).any(): continue
            if re.search(r"(Ceiling_Slab|Ceil_Step|_Body$|_Cap$|_Plate$|_Duct$|Ceil_Beam|_Base$)", n) and not wall_unit: continue
            if wall_unit and (n.startswith(u.split("_M")[0] + "_") or re.match(r".*_(Body|Cap)$", n)): continue  # its own wall segment
            if any(t in n for t in THIN): drop.add(n)
            elif wall_unit: gone_units.add(u); break
    for u in gone_units: drop |= {n for n in B if n.startswith(u)}
    if drop:
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
        ctx.notes.append(f"fixtures: {len(drop)} parts cleared out of fans / vents" + (f" (wall units removed: {', '.join(sorted(gone_units))})" if gone_units else ""))
    return drop


def lamp_posts(ctx, n, g, w, z0, z1, y, k, side, origin, yaw):
    """Stage 57: k warm lamps on posts along one edge (side +1 / -1 = local +x / -x) of a deck in group g (local +z
    along it, deck top at y): a post from under the deck edge to 2.7 m above it, a hood over the walkway edge and a
    glow_yellow bulb under it; each adds a soft yellow point light (effect Fan_Lights). Visual only."""
    sd = 1 if side >= 0 else -1; st = dict(collision=False, mobile={"static": True}); yl = ctx.role("glow_yellow")
    for i in range(k):
        lz = z0 + (z1 - z0) * (i + 0.5) / k
        ctx.add(f"{n}_Lamp_{i + 1}_Post", "box", [sd * (w / 2 + 0.05), y - 0.88, lz], [0.16, 3.55, 0.16], "frame", g, **st)
        ctx.add(f"{n}_Lamp_{i + 1}_Hood", "box", [sd * (w / 2 - 0.2), y + 2.6, lz], [0.62, 0.13, 0.9], "frame", g, outline=False, **st)
        ctx.add(f"{n}_Lamp_{i + 1}_Bulb", "box", [sd * (w / 2 - 0.2), y + 2.48, lz], [0.4, 0.14, 0.66], yl, g, outline=False, **st)
        ox, oz = local(sd * (w / 2 - 0.2), lz, yaw)
        ctx.fan_lights = getattr(ctx, "fan_lights", []) + [[round(origin[0] + ox, 2), round(y + 2.2, 2), round(origin[1] + oz, 2), 1.0]]


def clear_portals(ctx):
    """Stage 59: thin fixtures (struts, hangers, brackets ...) that a doorway portal now covers are removed - e.g. the
    gallery struts that dropped down the wall where the portal's pillars and header stand."""
    P = getattr(ctx, "portals", [])
    if not P: return set()
    B = _aabb_all(ctx); drop = set()
    for p in P:
        c = np.asarray(p["center"], float); hx, hy, hz = p["half"]
        if round(p.get("yaw", 0) / 90) % 2: hx, hz = hz, hx
        lo, hi = c - [hx, 0, hz], c + [hx, 2 * hy, hz]
        for n, (a, b) in B.items():
            if n.startswith(p["id"]) or not any(t in n for t in THIN): continue
            if (np.minimum(hi, b) - np.maximum(lo, a) > 0.01).all(): drop.add(n)
    if drop:
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
        ctx.notes.append(f"portals: {len(drop)} thin fixtures covered by a doorway portal removed ({', '.join(sorted(drop)[:6])})")
    return drop


def clear_ducts(ctx, gap=0.6, keep=6.0):
    """Stage 50: ceiling ducts (<room>Ceil_Duct_<n>) never run through something standing up from below (columns, vats,
    towers, machinery): the duct ends `gap` m before it; the pieces either side stay as separate ducts if at least `keep`
    m long. Hangers outside the kept pieces go; every piece keeps a hanger near each end."""
    import re
    B = _aabb_all(ctx); by = {o["name"]: o for o in ctx.objects}; drop, notes = set(), []
    def root(n):
        while by.get(n, {}).get("parent"): n = by[n]["parent"]
        return n
    low = {}  # lowest point of every top-level structure (a column's capital counts as part of a standing column)
    for n, (a, _) in B.items(): r_ = root(n); low[r_] = min(low.get(r_, 1e9), float(a[1]))
    for dn in [n for n in B if re.search(r"Ceil_Duct_\d+$", n)]:
        lo, hi = B[dn]; o = by[dn]; ax = 2 if hi[2] - lo[2] > hi[0] - lo[0] else 0; pre = dn.split("Duct_")[0]
        blocked = []
        for n, (a, b) in B.items():
            if n.startswith(pre) or n == dn or low[root(n)] > lo[1] - 2.0: continue  # same ceiling's dressing / anything not rising from below
            if (np.minimum(hi + 0.4, b) - np.maximum(lo - 0.4, a) <= 0).any(): continue
            blocked.append((a[ax] - gap, b[ax] + gap))
        if not blocked: continue
        segs = [(lo[ax], hi[ax])]
        for a, b in sorted(blocked):
            segs = [q for s0, s1 in segs for q in ((s0, min(s1, a)), (max(s0, b), s1)) if q[1] - q[0] > 0.01]
        segs = [q for q in segs if q[1] - q[0] >= keep]
        hangers = [n for n in by if n.startswith(dn + "_Hanger_")]; y = dict(by[hangers[0]]) if hangers else None
        ctx.objects[:] = [q for q in ctx.objects if q["name"] not in hangers]; ctx.names -= set(hangers)  # re-hung below
        if not segs: drop.add(dn); notes.append(f"{dn} removed"); continue
        for k, (s0, s1) in enumerate(segs):
            nm = dn if k == 0 else f"{dn}{chr(97 + k)}"
            pos = list(o["position"]); pos[ax] = round(s0, 3)
            if k == 0: o["position"] = pos; o["size"] = [o["size"][0], round(s1 - s0, 3), o["size"][2]]
            else: ctx.add(nm, "cylinder", pos, [o["size"][0], round(s1 - s0, 3), o["size"][2]], o["material"], None, o.get("rotation"), sections=o.get("sections", 8), outline=False,
                          collision=o.get("collision", False), **({"mobile": o["mobile"]} if o.get("mobile") else {}), **({"cutaway": o["cutaway"]} if o.get("cutaway") else {}))
            if y is not None:  # a hanger 0.5 m in from each end (+ one per 12 m between)
                m = max(1, int((s1 - s0) / 12))
                for j in range(m + 1):
                    hp = list(y["position"]); hp[ax] = round(s0 + 0.5 + (s1 - s0 - 1.0) * j / m, 3)
                    ctx.add(f"{nm}_Hanger_{j + 1}", "box", hp, y["size"], y["material"], None, outline=False, collision=y.get("collision", False),
                            **({"mobile": y["mobile"]} if y.get("mobile") else {}), **({"cutaway": y["cutaway"]} if y.get("cutaway") else {}))
        notes.append(f"{dn} trimmed to {len(segs)} piece(s) clear of {len(blocked)} standing part(s)")
    if drop: ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
    if notes: ctx.notes.append("ducts: " + "; ".join(notes))


def pier(ctx, n, g, x, y0, z, top, w, d, rot=(0, 0, 0), pitch=0.0):
    """Stage 37 bridge support instead of a plain block: a flared footing sunk into the floor / liquid, a hull-plated
    column with two ribs on each broad face, a flared head under the deck and a red light near the top. Returns the
    head (what the deck rests on). Stage 45: "pitch" (deg, deck rising toward local +z; rot must be 0) tilts the head so
    its top lies 6 cm inside a sloped deck whose underside passes through `top` above the pier's axis."""
    if pitch:
        p = math.radians(pitch); hb = top + 0.06 - 0.92 / math.cos(p)  # head base centre on the axis, top centre on the underside
        top = hb + 0.9 + 0.25  # the column reaches 25 cm up into the tilted head (covers its slanted bottom)
    H = top - y0
    ctx.add(n + "_Footing", "frustum", [x, y0 - 0.5, z], [w + 0.5, 1.2, d + 0.5], "structure_b", g, rot, bottom_scale=1.3)
    ctx.add(n, "box", [x, y0 + 0.6, z], [w, H - 1.4, d], "structure_b", g, rot)
    for sd in (-1, 1):
        for fz in (-1, 1):  # ribs on both broad faces (proud 6 cm)
            ox, oz = local(sd * (w / 2 - 0.22), fz * (d / 2 + 0.03), rot[1])
            ctx.add(f"{n}_Rib_{sd + 1}{fz + 1}", "box", [x + ox, y0 + 0.65, z + oz], [0.2, H - 1.5, 0.1], "frame", g, rot, outline=False)
    if pitch: ctx.add(n + "_Head", "frustum", [x, hb, z], [w + 0.9, 0.92, d + 0.9], "structure_b", g, [-pitch, 0, 0], bottom_scale=0.55)
    else: ctx.add(n + "_Head", "frustum", [x, top - 0.9, z], [w + 0.9, 0.92, d + 0.9], "structure_b", g, rot, bottom_scale=0.55)
    ox, oz = local(0, d / 2 + 0.04, rot[1])
    ctx.add(n + "_Light", "box", [x + ox, top - 1.6, z + oz], [w * 0.5, 0.16, 0.08], "glow", g, rot, outline=False, collision=False)
    return n + "_Head"


def clear_outlets(ctx, margin=3.0):
    """Stage 30: wall dressing (TVs, machines, fans, vents, emblems, side doors) never hangs in front of / under a pour:
    every such module whose parts come within `margin` m of an outlet's mouth or its fall is removed."""
    import re
    from anchors import world_matrices
    W, by = world_matrices({"objects": ctx.objects}); zones = []
    for st in ctx.pours:
        o = by.get(st)
        if not o: continue
        P = W[st][:3, 3]; w = max(o["size"][0], 2.0); zones.append((P, w / 2 + margin, P[1] + 4.0))
    if not zones: return 0
    pat = re.compile(r"^(.*_M\d\d(?:Monitor|Machine|Fan|Vent|Emblem|Door))(?:_|$)"); hit = set()
    for o in ctx.objects:
        m_ = pat.match(o["name"])
        if not m_ or m_.group(1) in hit or o["type"] == "group": continue
        q = W[o["name"]][:3, 3]
        for P, r, ytop in zones:
            if np.hypot(q[0] - P[0], q[2] - P[2]) < r + (o.get("size") or [0])[0] / 2 and q[1] < ytop: hit.add(m_.group(1)); break
    if hit:
        drop = {o["name"] for o in ctx.objects if any(o["name"] == h or o["name"].startswith(h + "_") for h in hit)}
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
        ctx.notes.append(f"outlets: removed wall dressing in front of pours: {', '.join(sorted(hit))}")
    return len(hit)


# ------------------------------------------------------------------ Stage 9: pluggable modules (pipeline/modules/*.py register more kinds)
from modules import load_all as _load_modules
_load_modules()
