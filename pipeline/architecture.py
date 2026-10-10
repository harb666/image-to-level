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
VARIANT_ROLES = ("wall", "structure", "deck", "plaster")
FALLBACK = {"timber": "frame", "stone": "structure", "plaster": "wall", "roof": "structure_b", "roof_slate": "structure_b", "door": "structure_b",
            "window": "glow", "foliage": "rock", "water": "hazard", "machine": "structure_b", "backdrop": "wall", "structure_b": "structure",
            "frame": "structure_b", "rail": "frame", "grate": "deck", "trim": "structure_b", "accent": "trim", "glow": "accent", "pipe": "frame",
            "hazard": "water", "ground": "deck", "deck": "ground", "wall": "structure", "structure": "wall", "rock": "structure"}


def role_material(theme, role):
    """Material definition for a role (variants '<role>_v2' get a tint/wear shift; missing roles fall back sensibly)."""
    roles = THEMES[theme]["roles"]; base = role[:-3] if role.endswith("_v2") else role; seen = set()
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

    def role(self, r, key=None):
        if self.variation and r in VARIANT_ROLES and key and _h(key) % 2: r = r + "_v2"
        self.roles.add(r); return r

    def add(self, name, typ, pos=(0, 0, 0), size=None, mat=None, parent=None, rot=(0, 0, 0), **kw):
        base, k = name, 2
        while name in self.names: name = f"{base}_{k}"; k += 1
        o = dict(name=name, type=typ, position=[round(float(v), 3) for v in pos], rotation=[round(float(v), 2) for v in rot])
        if parent: o["parent"] = parent
        if size is not None: o["size"] = [round(max(float(v), 0.0), 3) for v in size]
        if mat: o["material"] = self.role(mat, self.element[0] if self.element else name)
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
    """Distance from a platform centre to its edge in direction (dx, dz) (unit)."""
    w, d = p["size"]
    if p.get("shape") == "circle": return min(w, d) / 2
    if p.get("shape") == "octagon": a = min(w, d) / 2; return a / max(abs(dx), abs(dz), (abs(dx) + abs(dz)) / math.sqrt(2))
    return min(w / 2 / max(abs(dx), 1e-9), d / 2 / max(abs(dz), 1e-9))


def platform(ctx, p, base_y, centre):
    style = p.get("style") or ctx.theme["platform_style"]; return PLATFORM_STYLES[style](ctx, p, base_y, centre)


def _solid(ctx, name, parent, shape, w, h, d, y, mat, extra=0.0):
    if shape in ("octagon", "circle"):
        return ctx.add(name, "cylinder", [0, y, 0], [w + extra, h, d + extra], mat, parent, sections=8 if shape == "octagon" else 24)
    return ctx.add(name, "box", [0, y, 0], [w + extra, h, d + extra], mat, parent)


def industrial_pillar(ctx, p, base_y, centre):
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); h = max(0.3, top - 0.3 - base_y)
    _solid(ctx, n + "_Base", g, shape, w, h, d, base_y, "structure")
    _solid(ctx, n + "_Floor", g, shape, w, 0.3, d, top - 0.3, "deck", 0.3)
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
    _solid(ctx, n + "_Cap", g, shape, w, 0.4, d, top - 0.4, "deck", 0.3)
    if h > 1.5 and ctx.detail >= 1: _solid(ctx, n + "_Plinth", g, shape, w, 0.5, d, base_y, "trim", 0.4)
    _cover(ctx, p, g, top, "structure")
    ctx.walkable.append(_walk_rect(p, top))


def plain(ctx, p, base_y, centre):
    n, (cx, cz), (w, d), top, shape = p["id"], p["center"], p["size"], p["top"], p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); _solid(ctx, n + "_Base", g, shape, w, max(0.3, top - base_y), d, base_y, p.get("material", "deck"))
    _cover(ctx, p, g, top, "structure_b"); ctx.walkable.append(_walk_rect(p, top))


def _cover(ctx, p, g, top, mat):
    w, d = p["size"]; ch = ctx.G["design"]["cover_height"]
    spots = [(-w / 4, -d / 4), (w / 4, d / 4), (w / 4, -d / 4), (-w / 4, d / 4)]
    for k in range(min(int(p.get("cover", 0)), 4)):
        cx, cz = spots[k]; s = 1.6 if k % 2 == 0 else 2.0
        ctx.add(f"{p['id']}_Cover_{k + 1:02d}", "box", [round(cx, 2), top, round(cz, 2)], [s, ch, 1.2 if k % 2 else 1.6], mat, g)


def _walk_rect(p, top):
    (cx, cz), (w, d) = p["center"], p["size"]; k = 0.7 if p.get("shape") in ("octagon", "circle") else 1.0
    return dict(name=p["id"], min=[cx - w * k / 2, cz - d * k / 2], max=[cx + w * k / 2, cz + d * k / 2], y=p["top"])


PLATFORM_STYLES = dict(industrial_pillar=industrial_pillar, stone_plinth=stone_plinth, plain=plain)


# ------------------------------------------------------------------ connections
def connection(ctx, c, A, B, floor_y):
    """Bridge / ramp / stairs between the facing edges of platforms A and B (any angle)."""
    ax, az = A["center"]; bx, bz = B["center"]; dx, dz = bx - ax, bz - az; L = math.hypot(dx, dz) or 1.0; ux, uz = dx / L, dz / L
    ea, eb = footprint_edge(A, ux, uz), footprint_edge(B, -ux, -uz); gap = L - ea - eb
    lo, hi = (A, B) if A["top"] <= B["top"] else (B, A); dy = hi["top"] - lo["top"]
    P = ctx.G["player"]; kind = c.get("kind", "auto"); width = c.get("width", max(ctx.G["design"]["min_bridge_width"] + 0.5, 4.0))
    if kind == "auto":
        kind = "bridge" if dy <= P["step_height"] else "ramp" if gap > 0 and math.degrees(math.atan2(dy, gap)) <= min(P["max_slope_deg"], 35) else "stairs"
    if kind == "jump":
        ctx.notes.append(f"{c['id']}: jump link {A['id']}->{B['id']} (gap {gap:.1f} m, dy {dy:.1f} m) - no geometry"); return
    if gap < 0.2 and kind in ("bridge", "catwalk"): return  # platforms touch
    pa = (ax + ux * (ea - 0.3), az + uz * (ea - 0.3)); pb = (bx - ux * (eb - 0.3), bz - uz * (eb - 0.3)); span = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
    mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2)
    if kind in ("bridge", "catwalk"):
        y = (A["top"] + B["top"]) / 2; yaw = yaw_to(ux, uz)
        g = ctx.add(c["id"], "group", [mid[0], 0, mid[1]], rot=[0, yaw, 0])  # local +z along the bridge
        ctx.add(c["id"] + "_Deck", "box", [0, y - 0.4, 0], [width, 0.4, span], "grate", g)
        for s, side in ((-1, "L"), (1, "R")):
            ctx.add(f"{c['id']}_Beam_{side}", "ibeam", [s * (width / 2 - 0.15), y - 0.85, 0], [span, 0.45, 0.3], "frame", g, [0, 90, 0])
            if c.get("rails", kind == "catwalk"):
                ctx.add(f"{c['id']}_Rail_{side}", "railing", [s * (width / 2 - 0.05), y, 0], [span - 0.6, 1.05, 0.06], "rail", g, [0, 90, 0])
        if span > 10 and y - floor_y > 1.5:
            n = max(1, int(span / 9))
            for i in range(n):
                z = -span / 2 + span * (i + 1) / (n + 1)
                ctx.add(f"{c['id']}_Support_{i + 1:02d}", "box", [0, floor_y, z], [width * 0.5, y - 0.85 - floor_y, 0.6], "frame", g)
        if abs(ux) < 0.05 or abs(uz) < 0.05:
            hw, hl = (width / 2, span / 2) if abs(ux) < 0.05 else (span / 2, width / 2)
            ctx.walkable.append(dict(name=c["id"], min=[mid[0] - hw, mid[1] - hl], max=[mid[0] + hw, mid[1] + hl], y=y))
        return
    # ramp / stairs: base at the lower platform's edge, rising towards the higher one
    toward = (ux, uz) if lo is A else (-ux, -uz); yaw = yaw_to(*toward)
    run = max(gap, dy / math.tan(math.radians(min(P["max_slope_deg"], 35))))  # ramps and stairs <= 35° (walkable with step_height)
    hi_edge = pb if hi is B else pa; start = (hi_edge[0] - toward[0] * (run + 0.3), hi_edge[1] - toward[1] * (run + 0.3))
    ctr = ((start[0] + hi_edge[0]) / 2, (start[1] + hi_edge[1]) / 2)
    if lo["top"] - floor_y > 1.5 and kind == "ramp":  # elevated: sloped bridge (tilted grated deck + beams + supports), not a solid wedge
        Ls = math.hypot(run + 0.3, dy); pitch = math.degrees(math.atan2(dy, run + 0.3)); ym = (lo["top"] + hi["top"]) / 2
        g = ctx.add(c["id"], "group", [ctr[0], 0, ctr[1]], rot=[0, yaw, 0])
        ctx.add(c["id"] + "_Deck", "box", [0, ym - 0.4, 0], [width, 0.4, Ls], "grate", g, [-pitch, 0, 0])
        for s, side in ((-1, "L"), (1, "R")):
            ctx.add(f"{c['id']}_Beam_{side}", "box", [s * (width / 2 - 0.15), ym - 0.85, 0], [0.3, 0.45, Ls], "frame", g, [-pitch, 0, 0])
            if c.get("rails"): ctx.add(f"{c['id']}_Rail_{side}", "railing", [s * (width / 2 - 0.05), ym, 0], [Ls - 0.6, 1.05, 0.06], "rail", g, [-pitch, 90, 0])
        if ym - floor_y > 1.5:
            ctx.add(c["id"] + "_Support", "box", [0, floor_y, 0], [width * 0.5, ym - 0.9 - floor_y, 0.6], "frame", g)
    else:
        ctx.add(c["id"], kind if kind == "ramp" else "stairs", [ctr[0], lo["top"], ctr[1]], [width, dy, run + 0.3], "grate", rot=[0, yaw, 0])
        if lo["top"] - floor_y > 1.5:  # elevated stairs: a support block underneath (no floating solid)
            ctx.add(c["id"] + "_Support", "box", [ctr[0], floor_y, ctr[1]], [width * 0.6, lo["top"] - floor_y, (run + 0.3) * 0.5], "structure_b", rot=[0, yaw, 0])
    if run > gap + 0.5: ctx.notes.append(f"{c['id']}: {kind} run {run:.1f} m > gap {gap:.1f} m - extends {run - gap:.1f} m onto {lo['id']}")


# ------------------------------------------------------------------ walls / arena
def wall_segment(ctx, name, p0, p1, height, thick, base_y, style, inner=None, decor=True):
    """Straight wall from p0 to p1 (x, z); 'inner' = point on the playable side (pilasters/banners face it)."""
    dx, dz = p1[0] - p0[0], p1[1] - p0[1]; L = math.hypot(dx, dz); ux, uz = dx / L, dz / L
    mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2); yaw = yaw_to(ux, uz) - 90  # local +x along the wall, +z = normal
    nx, nz = uz, -ux
    if inner and (inner[0] - mid[0]) * nx + (inner[1] - mid[1]) * nz < 0: yaw += 180
    g = ctx.add(name, "group", [mid[0], 0, mid[1]], rot=[0, yaw, 0])
    ctx.add(name + "_Body", "box", [0, base_y, 0], [L, height - base_y, thick], "wall", g)
    ctx.add(name + "_Cap", "box", [0, height, 0], [L + 0.3, 0.5, thick + 0.4], "trim" if style == "stone" else "structure_b", g)
    if not decor: return g
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


def arena_outline(arena):
    """Corner points (x, z) of the arena boundary, clockwise from north-west."""
    (cx, cz), (w, d) = arena.get("center", [0, 0]), arena["size"]; sh = arena.get("shape", "rect")
    if sh == "rect": return [(cx - w / 2, cz - d / 2), (cx + w / 2, cz - d / 2), (cx + w / 2, cz + d / 2), (cx - w / 2, cz + d / 2)]
    n = 8 if sh == "octagon" else 20; r = min(w, d) / 2 / math.cos(math.pi / n)
    return [(cx + r * math.sin(math.pi / n * (2 * i + 1) - math.pi), cz + r * math.cos(math.pi / n * (2 * i + 1) - math.pi)) for i in range(n)][::-1]


SIDES = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0)}


def arena(ctx, a, floor_y):
    (cx, cz), (w, d) = a.get("center", [0, 0]), a["size"]; fl = a.get("floor", {"kind": "ground"}); sh = a.get("shape", "rect")
    big = [w + 2 * a.get("walls", {}).get("thickness", 2), 0, d + 2 * a.get("walls", {}).get("thickness", 2)]
    if fl["kind"] == "hazard":
        ctx.element = ("arena.floor", fl.get("source", "visible"))
        n = ctx.add(fl.get("name", "HazardFluid"), "box" if sh == "rect" else "cylinder", [cx, 0, cz], [w, fl["y"], d], fl.get("material", "hazard"),
                    **({} if sh == "rect" else {"sections": 8 if sh == "octagon" else 24}))
        ctx.hazards.append(n)
    else:
        ctx.element = ("arena.floor", fl.get("source", "visible"))
        mat = fl.get("material", "ground" if fl["kind"] == "ground" else "deck")
        ctx.add(fl.get("name", "Ground"), "box", [cx, fl["y"] - 0.5, cz], [big[0] + 1, 0.5, big[2] + 1], mat)
        ctx.walkable.append(dict(name=fl.get("name", "Ground"), min=[cx - w / 2 + 1, cz - d / 2 + 1], max=[cx + w / 2 - 1, cz + d / 2 - 1], y=fl["y"]))
    W = a.get("walls")
    if W and W.get("style", "auto") != "none":
        ctx.element = ("arena.walls", W.get("source", "visible")); style = ctx.theme["wall_style"] if W.get("style", "auto") == "auto" else W["style"]
        pts = arena_outline(a); t = W.get("thickness", 3.0); names = ["North", "East", "South", "West"] if sh == "rect" else [f"{i + 1:02d}" for i in range(len(pts))]
        for i, (p0, p1) in enumerate(zip(pts, pts[1:] + pts[:1])):
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); ux, uz = (p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L; nx, nz = uz, -ux  # outward normal (clockwise)
            q0 = (p0[0] + nx * t / 2 - ux * t / 2, p0[1] + nz * t / 2 - uz * t / 2); q1 = (p1[0] + nx * t / 2 + ux * t / 2, p1[1] + nz * t / 2 + uz * t / 2)
            segs = [(q0, q1)]
            for op in W.get("openings", []):  # split around openings (rect arenas: by side name)
                if sh == "rect" and op["side"].capitalize() == names[i]:
                    new = []
                    for s0, s1 in segs:
                        SL = math.hypot(s1[0] - s0[0], s1[1] - s0[1]); c = SL / 2 + op.get("at", 0) * (1 if names[i] in ("North", "South") else 1)
                        h0, h1 = c - op["width"] / 2, c + op["width"] / 2
                        if h0 > 0.5: new.append((s0, (s0[0] + ux * h0, s0[1] + uz * h0)))
                        if h1 < SL - 0.5: new.append(((s0[0] + ux * h1, s0[1] + uz * h1), s1))
                        if op.get("height", 0) and op["height"] < W["height"] - 0.5:
                            m0 = (s0[0] + ux * h0, s0[1] + uz * h0); m1 = (s0[0] + ux * h1, s0[1] + uz * h1)
                            wall_segment(ctx, f"OuterWall_{names[i]}_Lintel", m0, m1, W["height"], t, op["height"], style, (cx, cz), decor=False)
                    segs = new
            for k, (s0, s1) in enumerate(segs):
                nm = f"OuterWall_{names[i]}" + (f"_{k + 1:02d}" if len(segs) > 1 else "")
                wall_segment(ctx, nm, s0, s1, W["height"], t, 0.0, style, (cx, cz))
    if a.get("walkway"):
        ww = a["walkway"]; ctx.element = ("arena.walkway", ww.get("source", "visible")); wd = ww.get("width", 4.0)
        if sh != "rect": ctx.notes.append("walkway ring is only generated for rect arenas")
        else:
            for nm, (x, z, sw, sd) in {"North": (cx, cz - d / 2 + wd / 2, w, wd), "South": (cx, cz + d / 2 - wd / 2, w, wd),
                                       "West": (cx - w / 2 + wd / 2, cz, wd, d - 2 * wd), "East": (cx + w / 2 - wd / 2, cz, wd, d - 2 * wd)}.items():
                platform(ctx, dict(id="Walkway_" + nm, center=[x, z], size=[sw, sd], top=ww["y"], shape="rect", lights=False, cover=0,
                                   style=ww.get("style")), 0.0, (cx, cz))
    if a.get("boundary", "walls" if W else "invisible") == "invisible" or not W:
        ctx.element = ("arena.boundary", "inferred"); pts = arena_outline(a)
        for i, (p0, p1) in enumerate(zip(pts, pts[1:] + pts[:1])):
            L = math.hypot(p1[0] - p0[0], p1[1] - p0[1]); yaw = yaw_to((p1[0] - p0[0]) / L, (p1[1] - p0[1]) / L) - 90
            ctx.add(f"Boundary_{i + 1:02d}", "boundary", [(p0[0] + p1[0]) / 2, fl.get("y", 0), (p0[1] + p1[1]) / 2], [L, 12, 0.5], rot=[0, yaw, 0])


# ------------------------------------------------------------------ structures
def _place(ctx, s, plats, floor_y, centre):
    """World base position + yaw for a structure (on a platform, at x/z on the floor, or explicit x/y/z)."""
    if s.get("on"):
        p = plats[s["on"]]; off = s.get("offset", [0, 0]); x, z, y = p["center"][0] + off[0], p["center"][1] + off[1], p["top"]
    else:
        pos = s["position"]; x, z = pos[0], pos[-1]; y = pos[1] if len(pos) == 3 else floor_y
    if "yaw" in s: yaw = s["yaw"]
    elif s.get("facing", "center") == "center": yaw = yaw_to(centre[0] - x, centre[1] - z) if math.hypot(centre[0] - x, centre[1] - z) > 0.5 else 0.0
    else: yaw = {"north": 180, "south": 0, "east": 90, "west": 270}.get(s["facing"], 0)
    return x, y, z, yaw


def tower(ctx, s, x, y, z, yaw):
    """Industrial tower: bevelled body, wider cap, setback top, corner ribs, banner + glow strips per face, vents."""
    n = s["id"]; w, h, d = s["size"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); dec = s.get("decor", ["banners", "glow_strips", "vents"])
    ctx.add(n + "_Body", "box", [0, 0, 0], [w, h, d], "wall", g)
    ctx.add(n + "_Cap", "box", [0, h, 0], [w + 1, 1.2, d + 1], "structure_b", g)
    if ctx.detail >= 1: ctx.add(n + "_Top", "box", [0, h + 1.2, 0], [w * 0.55, h * 0.12, d * 0.55], "wall", g)
    if ctx.detail >= 1:
        for i, (sx, sz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
            ctx.add(f"{n}_Rib_{i + 1:02d}", "box", [sx * w / 2, 0, sz * d / 2], [0.7, h, 0.7], "structure_b", g)
    for k, (px, pz, fy, fw) in enumerate(((0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d))):
        nx, nz = (px and math.copysign(0.03, px)), (pz and math.copysign(0.03, pz))
        if "banners" in dec: ctx.add(f"{n}_Banner_{k + 1:02d}", "panel", [px + nx, h * 0.3, pz + nz], [min(2.6, fw * 0.4), h * 0.5, 0], "accent", g, [0, fy, 0])
        if "glow_strips" in dec:
            for sd in (-1, 1):
                ox, oz = local(sd * fw * 0.34, 0, fy)
                ctx.add(f"{n}_Glow_{k + 1:02d}{'LR'[sd > 0]}", "panel", [px + nx + ox, h * 0.08, pz + nz + oz], [0.5, h * 0.78, 0], "glow", g, [0, fy, 0])
        if "vents" in dec and ctx.detail >= 2:
            ctx.add(f"{n}_Vent_{k + 1:02d}", "vent", [px + nx * 6, h * 0.86, pz + nz * 6], [fw * 0.4, 0.9, 0.3], "machine", g, [0, fy, 0])
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
    for o in prefabs.machinery_bank(s["id"], [x, y, z], yaw, seed=_h(s["id"]) % 97, material="machine", tank_material="pipe"):
        _adopt(ctx, o)


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
    if p.get("kind", "outlet") == "run":
        for o in prefabs.pipe_run(p["id"], p["points"], radius=p.get("radius", 0.5), material="pipe", junction="frame"): _adopt(ctx, o)
        return
    r = p.get("radius", 1.2); L = p.get("length", 8.0); y = p.get("y", 9.0)
    if "position" in p: x, z = p["position"][0], p["position"][-1]; yaw = p.get("yaw", 0)
    else:  # on the inner face of an arena wall: side + offset along it, pointing inwards
        (cx, cz), (w, d) = arena_spec.get("center", [0, 0]), arena_spec["size"]; side = p["wall"].lower(); at = p.get("at", 0)
        corners = {"ne": (1, -1), "nw": (-1, -1), "se": (1, 1), "sw": (-1, 1)}
        if side in corners:
            sx, sz = corners[side]; x, z = cx + sx * (w / 2 - 1), cz + sz * (d / 2 - 1); yaw = yaw_to(-sx, -sz)
        else:
            sx, sz = SIDES[side]; x = cx + sx * w / 2 + (at if sz else 0); z = cz + sz * d / 2 + (at if sx else 0); yaw = yaw_to(-sx, -sz)
    dx, dz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw))
    n = ctx.add(p["id"], "cylinder", [x, y, z], [2 * r, L, 2 * r], "pipe", rot=[90, yaw, 0], sections=10)
    if ctx.detail >= 1:
        ctx.add(n + "_Flange", "cylinder", [x + dx * (L - 0.4), y, z + dz * (L - 0.4)], [2 * r * 1.25, 0.45, 2 * r * 1.25], "frame", rot=[90, yaw, 0], sections=10)
        ctx.add(n + "_Mount", "box", [x + dx * 0.3, y - r * 1.3, z + dz * 0.3], [r * 2.6, r * 2.6, 0.6], "frame", rot=[0, yaw, 0])  # wall plate: never blocks a floor
    if p.get("pour", False):
        ex, ez = x + dx * (L + 0.6), z + dz * (L + 0.6)
        f = ctx.add(n + "_Fall", "box", [ex, floor_y, ez], [2 * r * 0.8, y - floor_y - r / 2 + 0.4, 1.0], p.get("pour_material", "hazard"), rot=[0, yaw, 0])
        ctx.pours.append(f)
