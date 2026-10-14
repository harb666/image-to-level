"""Procedural PBR material library (CPU, free). Used by build_level.py; one shared glTF material per level.json material.

level.json material entry: {"type": <kind>, "color": [r,g,b], "tile_m": metres per texture repeat,
  optional "res": texture px (default per kind), "emissive": [r,g,b] factor, "accent": [r,g,b] (light colour for
  machinery/trim kinds), "wear": 0..1 (grime/damage amount)}.
Every kind yields: base colour (sRGB jpeg), normal map (from a height field), ORM (R=ambient occlusion,
G=roughness, B=metallic — glTF metallicRoughness + occlusion share it) and, if it glows, an emissive mask.
All maps are tileable. Standard glTF 2.0 PBR, so Godot 4 imports them into StandardMaterial3D directly.
PBR kinds: industrial_metal, painted_metal, damaged_metal, scifi_floor, grating, concrete, rock, sand, dirt, grass,
  toxic, glow, machinery_panel, trim_light, pipe, banner, factory_facade (distant buildings, lit windows),
  hull_plating (worn tower/wall plates: straps, vents, rain streaks), chevron (hazard stripes),
  ceiling_works (olive plates, vents, X-braces, conduit bundles, moss), wall_works (irregular riveted plates, vents, X-braces, green light dashes, conduits), wall_slimed (+ glowing slime drips),
  snow, mud, asphalt ("lines": true = lane line), gravel, moss (Stage 9 terrain layers).  Legacy (stylised, albedo-derived normals): cobblestone,
  stone_brick, plaster, wood, painted_wood, trim_wood, door_wood, window, roof_tiles, roof_slate, metal, water, soil.
"""
import io, os, numpy as np, trimesh
from PIL import Image
from scipy import ndimage

TEX = 256  # px; mobile-friendly (jpeg-compressed in the glb)


def _noise(rng, cells, octaves=3, S=None):
    TEX = S or globals()["TEX"]; out = np.zeros((TEX, TEX))
    for o in range(octaves):
        c = cells * 2 ** o; a = rng.random((c, c))
        big = np.asarray(Image.fromarray(np.tile(a, (3, 3)).astype(np.float32)).resize((TEX * 3, TEX * 3), Image.BICUBIC))
        out += big[TEX:2 * TEX, TEX:2 * TEX] / 2 ** o  # centre of a 3x3 tiling -> seamless
    return (out - out.min()) / (np.ptp(out) + 1e-6)


def _cells(rng, n, S=None):
    """Tileable Voronoi: (id of nearest point, edge closeness 0..1)."""
    TEX = S or globals()["TEX"]; pts = rng.random((n, 2)) * TEX; y, x = np.mgrid[:TEX, :TEX]
    d = np.stack([np.hypot(np.minimum(abs(x - px), TEX - abs(x - px)), np.minimum(abs(y - py), TEX - abs(y - py))) for px, py in pts])
    s = np.sort(d, 0); return d.argmin(0), np.clip((s[1] - s[0]) / 4, 0, 1)


def _bevel(e, w=0.35):
    """Edge closeness 0..1 -> raised-tile shading (dark grout, lit top-left bevel)."""
    return np.clip(e / w, 0, 1) ** 0.6


def legacy_texture(kind):
    """Stylised tileable texture: RGB multiplier around 1.0 (times the material colour)."""
    rng = np.random.default_rng(sum(map(ord, kind))); y, x = np.mgrid[:TEX, :TEX] / TEX
    n = _noise(rng, 4); fine = _noise(rng, 32, 2); tint = np.ones((TEX, TEX, 3))
    if kind == "cobblestone":
        cid, e = _cells(rng, 34); shade = rng.uniform(0.75, 1.15, 34)[cid]
        t = shade * (0.35 + 0.65 * _bevel(e, 0.5)) * (0.85 + 0.25 * fine)
        tint *= rng.uniform(0.97, 1.03, (34, 3))[cid]
    elif kind in ("stone_brick", "concrete_block"):
        rows = 8; row = (y * rows).astype(int); off = (row % 2) * 0.125; col = ((x + off) * 4).astype(int) % 4
        ey = np.minimum((y * rows) % 1, 1 - (y * rows) % 1) * 4; ex = np.minimum(((x + off) * 4) % 1, 1 - ((x + off) * 4) % 1) * 8
        shade = rng.uniform(0.78, 1.1, (rows, 4))[row, col]; t = shade * (0.35 + 0.65 * _bevel(np.minimum(ex, ey), 0.4)) * (0.85 + 0.3 * fine)
        tint *= rng.uniform(0.97, 1.03, (rows, 4, 3))[row, col]
    elif kind in ("wood", "door_wood", "trim_wood", "painted_wood"):
        boards = 4 if kind != "trim_wood" else 2; board = (x * boards).astype(int)
        grain = np.sin((y * 3 + rng.random(boards)[board]) * 60 + 8 * _noise(rng, 6)) * 0.5 + 0.5
        t = (0.8 + 0.2 * grain * (0.4 if kind == "painted_wood" else 1)) * rng.uniform(0.85, 1.1, boards)[board]
        t *= 0.4 + 0.6 * _bevel(np.minimum((x * boards) % 1, 1 - (x * boards) % 1) * 10, 0.5)
        if kind == "door_wood":  # frame + handle
            fr = (x < 0.08) | (x > 0.92) | (y < 0.06); t[fr] *= 0.6; t[(abs(x - 0.8) < 0.03) & (abs(y - 0.55) < 0.03)] = 1.6
    elif kind == "window":  # dark glass, light frame, 2x2 mullions
        glass = 0.35 + 0.25 * (y < 0.5 - 0.4 * x)  # sky reflection streak
        frame = (np.minimum(x, 1 - x) < 0.09) | (np.minimum(y, 1 - y) < 0.07) | (abs(x - 0.5) < 0.03) | (abs(y - 0.5) < 0.03)
        t = np.where(frame, 1.15, glass); tint[~frame] = [0.6, 0.8, 1.2]
    elif kind in ("roof_tiles", "roof_slate"):
        rows = 10 if kind == "roof_tiles" else 14; r = (y * rows) % 1; cols = 8 if kind == "roof_tiles" else 6
        u = (x * cols + (y * rows).astype(int) % 2 * 0.5) % 1
        t = (0.55 + 0.55 * r) * (1 - 0.35 * (np.abs(u - 0.5) > 0.44)) * rng.uniform(0.85, 1.1, (rows, cols + 1))[(y * rows).astype(int), (x * cols + 0.5).astype(int)]
    elif kind == "metal":
        t = 0.85 + 0.1 * _noise(rng, 64, 1)[:, :1].repeat(TEX, 1) + 0.06 * n
        seam = np.minimum(y % 0.5, x % 0.5) < 0.012; t[seam] = 0.5
        riv = (np.hypot((x % 0.5) - 0.04, (y % 0.5) - 0.04) < 0.012) | (np.hypot((x % 0.5) - 0.46, (y % 0.5) - 0.04) < 0.012); t[riv] = 1.25
    elif kind == "grass":
        blades = _noise(rng, 64, 1); t = 0.65 + 0.35 * n + 0.25 * (blades > 0.7) - 0.15 * (blades < 0.25)
        tint[..., 0] *= 0.85 + 0.3 * _noise(rng, 3, 2); tint[..., 2] *= 0.8 + 0.2 * n
    elif kind == "rock":
        cid, e = _cells(rng, 9); t = rng.uniform(0.8, 1.1, 9)[cid] * (0.5 + 0.5 * _bevel(e, 0.9)) * (0.75 + 0.4 * _noise(rng, 6, 4))
        t[(np.abs(_noise(rng, 5, 2) - 0.5) < 0.015)] *= 0.6  # cracks
    elif kind == "water":
        t = 0.85 + 0.3 * np.sin((x + 0.3 * n) * 25) ** 8; tint *= [0.9, 1.0, 1.1]
    elif kind == "floor_plate":  # worn tan deck plates: 2x2 plates, bevelled seams, octagon inlay, scuffs, edge wear
        px, py = (x * 2) % 1, (y * 2) % 1; e = np.minimum(np.minimum(px, 1 - px), np.minimum(py, 1 - py)) * 14
        t = (0.42 + 0.58 * _bevel(e, 0.35)) * (0.86 + 0.16 * fine + 0.1 * n) * rng.uniform(0.9, 1.06, (2, 2))[(y * 2).astype(int), (x * 2).astype(int)]
        oc = np.maximum(np.abs(px - 0.5), np.abs(py - 0.5)) + 0.45 * np.minimum(np.abs(px - 0.5), np.abs(py - 0.5))
        inl = np.abs(oc - 0.33) < 0.012; t[inl] *= 0.75; tint[inl] = [1.3, 1.1, 0.55]
        bolt = np.hypot(np.minimum(px, 1 - px) - 0.06, np.minimum(py, 1 - py) - 0.06) < 0.018; t[bolt] = 0.55
        t *= 1 - 0.25 * np.clip(_noise(rng, 5, 3) - 0.6, 0, 1) * 2.5  # dark scuffs / grime
        tint *= [1.04, 1.0, 0.94]
    elif kind == "industrial_wall":  # dark worn metal: vertical panels, seams, rivet rows, horizontal straps, grime
        cols = 4; cx = (x * cols) % 1; band = (y * 2) % 1
        e = np.minimum(cx, 1 - cx) * 18; pnl = rng.uniform(0.85, 1.12, cols)[(x * cols).astype(int)]
        t = (0.5 + 0.5 * _bevel(e, 0.4)) * pnl * (0.85 + 0.15 * fine + 0.12 * n)
        strap = np.abs(band - 0.5) < 0.05; t[strap] *= 1.25; t[np.abs(band - 0.5) - 0.05 < 0.01] *= 0.7
        riv = (np.abs(band - 0.5) < 0.05) & (np.hypot(((x * cols * 3) % 1) - 0.5, (band - 0.5) * 6) < 0.12); t[riv] = 1.35
        t *= 1 - 0.35 * np.clip(_noise(rng, 6, 3) - 0.55, 0, 1) * 2.2 * (0.6 + 0.4 * y)  # grime, heavier lower
        lamp = (np.abs(cx - 0.5) < 0.05) & (np.abs(band - 0.2) < 0.012); t[lamp] = 1.6; tint[lamp] = [1.6, 1.0, 0.3]  # tiny amber lights
    elif kind == "platform_side":  # chunky block sides: big recessed panels, thick frames, vertical drip grime
        cx, cy = (x * 2) % 1, (y * 2) % 1; e = np.minimum(np.minimum(cx, 1 - cx), np.minimum(cy, 1 - cy))
        frame = e < 0.09; inset = (e > 0.13)
        t = np.where(frame, 1.12, np.where(inset, 0.82, 0.55)) * (0.85 + 0.18 * fine + 0.1 * n)
        t *= 1 - 0.3 * np.clip(_noise(rng, 12, 1)[:1, :].repeat(TEX, 0) - 0.55, 0, 1) * 2.2 * y  # vertical streaks
        tint *= [0.95, 1.02, 0.97]
    elif kind == "grate":  # metal walkway grating: bars over dark gaps, side rails
        bar = (y * 16) % 1 < 0.55; rail = np.minimum(x, 1 - x) < 0.06
        t = np.where(bar | rail, 0.95 + 0.1 * fine, 0.3); t *= 0.9 + 0.15 * n
    elif kind == "pipe_metal":  # dark pipe: segment rings/flanges + bolts, lengthwise sheen, grime
        v = (y * 2) % 1; ring = np.abs(v - 0.5) < 0.06
        sheen = 0.8 + 0.25 * np.sin(x * np.pi * 2) ** 2
        t = sheen * (0.82 + 0.12 * n + 0.08 * fine); t[ring] = 1.25 * sheen[ring]; t[np.abs(np.abs(v - 0.5) - 0.07) < 0.01] *= 0.55
        bolt = ring & (((x * 12) % 1) < 0.2) & (np.abs(v - 0.5) < 0.03); t[bolt] = 1.5
        t *= 1 - 0.3 * np.clip(_noise(rng, 4, 3) - 0.6, 0, 1) * 2.5
    elif kind == "toxic":  # bright neon fluid: swirls + light foam caustics
        sw = np.sin((x + 0.35 * _noise(rng, 3, 2)) * 18) * np.sin((y + 0.35 * _noise(rng, 3, 2)) * 14)
        cid, e = _cells(rng, 30); foam = np.clip(1 - e * 3, 0, 1) ** 3
        t = 0.8 + 0.2 * sw ** 2 + 0.12 * n + 0.35 * foam; tint[..., 0] += 0.4 * foam; tint[..., 2] += 0.3 * foam
    elif kind == "glow":  # emissive tube: hot core, soft falloff to the edges
        t = 0.55 + 0.9 * np.exp(-((x - 0.5) / 0.22) ** 2) + 0.05 * n; tint[..., 0] += 0.3 * np.exp(-((x - 0.5) / 0.12) ** 2)
    elif kind == "red_panel":  # banner: dark frame, red cloth with pennant V-cut, ring+cross emblem, stitched border
        frame = (np.minimum(x, 1 - x) < 0.07) | (y < 0.05)
        vcut = y > 0.86 + 0.14 * np.abs(x - 0.5) * 2  # dark notch at the bottom
        r = np.hypot(x - 0.5, (y - 0.42) * 1.2); emb = (np.abs(r - 0.17) < 0.022) | ((r < 0.25) & ((np.abs(x - 0.5) < 0.012) | (np.abs(y - 0.42) < 0.012)))
        cloth = 0.85 + 0.12 * np.sin(x * 40 + 4 * n) * 0.3 + 0.1 * fine - 0.25 * y
        t = np.where(frame | vcut, 0.18, cloth); t[emb & ~frame] = 1.45; tint[emb & ~frame] = [1.0, 0.75, 0.4]
        t[(np.abs(np.minimum(x, 1 - x) - 0.1) < 0.008) & ~vcut & (y > 0.05)] = 1.2
    elif kind == "plaster":
        t = 0.93 + 0.1 * fine - 0.12 * np.clip(_noise(rng, 3, 2) - 0.6, 0, 1) * 3 * (1 - y)  # stains near the bottom
    elif kind in ("sand", "soil"):
        t = 0.82 + 0.25 * _noise(rng, 6, 3) + 0.12 * (fine > 0.75)
    else:  # concrete
        t = 0.88 + 0.15 * fine + 0.05 * n; t[(x % 0.5 < 0.006) | (y % 0.5 < 0.006)] *= 0.75
    return np.clip(t[..., None] * tint, 0, 1.4)

# ---------------------------------------------------------------- PBR kinds
ALIASES = {"industrial_wall": "industrial_metal", "platform_side": "machinery_panel", "floor_plate": "scifi_floor",
           "grate": "grating", "pipe_metal": "pipe", "red_panel": "banner", "cliff": "rock"}
DEFAULT_RES = {"screen_atlas": 1024, "bigscreen": 1024, "tv_casing": 512, "screen_ui": 512, "ceiling_works": 1024, "wall_works": 512, "wall_slimed": 512, "hull_plating": 512, "industrial_metal": 512, "scifi_floor": 512, "rock": 512, "painted_metal": 512, "damaged_metal": 512,
               "concrete": 256, "glow": 128}


def _xy(S):
    y, x = np.mgrid[:S, :S] / S; return x, y


def _blur(a, s):
    return ndimage.gaussian_filter(a, s, mode="wrap")


def _dome(d, r):
    return np.clip(1 - (d / r) ** 2, 0, 1) ** 0.5


def _edge(px, py):
    """Distance (0..0.5) to the nearest edge of a unit cell."""
    return np.minimum(np.minimum(px, 1 - px), np.minimum(py, 1 - py))


def _rivets(px, py, count, inset, r):
    """Raised rivet domes along the top and bottom edges of a cell."""
    u = ((px * count) % 1 - 0.5) / count
    return np.maximum(_dome(np.hypot(u, py - inset), r), _dome(np.hypot(u, py - 1 + inset), r))


def _grime(rng, S, y, wear):
    return np.clip(_noise(rng, 6, 3, S) - 0.62 + 0.25 * wear, 0, 1) * 2.5 * (0.55 + 0.45 * y)


def _panels(S, rng, c, m, cols=2, rows=2):
    """Shared base for metal panel kinds: returns dict + useful masks."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); n = _noise(rng, 4, 3, S); wear = m.get("wear", 0.5)
    px, py = (x * cols) % 1, (y * rows) % 1; e = _edge(px, py)
    seam = np.clip(e * 40, 0, 1) ** 0.7
    pid = (y * rows).astype(int) * cols + (x * cols).astype(int); pv = rng.uniform(0.82, 1.12, cols * rows)[pid]
    riv = _rivets(px, py, 6, 0.06, 0.018)
    strap = (np.abs(py - 0.5) < 0.035).astype(float)
    grime = _grime(rng, S, y, wear)
    edgewear = np.clip(1 - e * 30, 0, 1) * (seam > 0.6) * (_noise(rng, 16, 2, S) > 0.45)
    h = 0.55 * seam + 0.12 * strap + 0.3 * riv + 0.04 * fine
    alb = c[None, None] * (pv * (0.86 + 0.14 * fine) * (1 - 0.5 * grime) * (0.45 + 0.55 * seam) * (1 + 0.25 * riv))[..., None]
    alb = alb + (np.clip(c * 1.9 + 0.08, 0, 1) - alb) * (0.55 * edgewear)[..., None]
    rough = 0.42 + 0.3 * grime + 0.08 * n - 0.12 * edgewear
    metal = 0.35 + 0.5 * edgewear - 0.25 * np.clip(grime, 0, 1)  # coated/dirty metal: mostly diffuse, bare edges metallic
    return dict(alb=alb, h=h, rough=rough, metal=metal, nstr=1.0), dict(x=x, y=y, px=px, py=py, e=e, fine=fine, n=n, grime=grime, seam=seam)


def k_industrial_metal(S, rng, c, m):
    return _panels(S, rng, c, m)[0]


def k_painted_metal(S, rng, c, m):
    d, k = _panels(S, rng, c, m)
    chip = (_noise(rng, 18, 2, S) > 0.78 - 0.5 * np.clip(1 - k["e"] * 12, 0, 1) * m.get("wear", 0.5)) & (k["seam"] > 0.5)
    bare = np.full(3, 0.5)
    d["alb"] = np.where(chip[..., None], bare * (0.8 + 0.2 * k["fine"][..., None]), d["alb"])
    d["metal"] = np.where(chip, 0.9, 0.05); d["rough"] = np.where(chip, 0.35, 0.55 + 0.25 * k["grime"]); d["h"] = d["h"] - 0.06 * chip
    return d


def k_damaged_metal(S, rng, c, m):
    d, k = _panels(S, rng, c, dict(m, wear=max(m.get("wear", 0.8), 0.8)))
    scorch = np.clip(_noise(rng, 3, 3, S) - 0.55, 0, 1) * 3; rust = np.clip(_noise(rng, 7, 3, S) - 0.6, 0, 1) * 3
    dents = _blur(_noise(rng, 5, 2, S), S / 40)
    d["alb"] = d["alb"] * (1 - 0.6 * np.clip(scorch, 0, 1))[..., None]
    d["alb"] = d["alb"] + (np.array([0.42, 0.2, 0.08]) - d["alb"]) * np.clip(rust, 0, 0.85)[..., None]
    d["rough"] = np.clip(d["rough"] + 0.4 * rust + 0.2 * scorch, 0, 1); d["metal"] = d["metal"] * (1 - np.clip(rust, 0, 1))
    d["h"] = d["h"] - 0.25 * dents; return d


def k_scifi_floor(S, rng, c, m):
    """Large worn deck plates: bevelled seams, inset service panels, corner bolts, scratches, grime in recesses."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); n = _noise(rng, 4, 3, S); wear = m.get("wear", 0.5)
    px, py = (x * 2) % 1, (y * 2) % 1; e = _edge(px, py); seam = np.clip(e * 45, 0, 1) ** 0.7
    pid = (y * 2).astype(int) * 2 + (x * 2).astype(int); pv = rng.uniform(0.88, 1.08, 4)[pid]
    inset_e = _edge(np.clip((px - 0.22) / 0.56, 0, 1), np.clip((py - 0.3) / 0.4, 0, 1))
    inset = ((pid % 3) == 0) & (np.abs(px - 0.5) < 0.28) & (np.abs(py - 0.5) < 0.2)
    diag = ((pid % 3) == 1) & (np.abs(px - py) < 0.008)
    bolt = np.maximum.reduce([_dome(np.hypot(px - a, py - b), 0.022) for a in (0.06, 0.94) for b in (0.06, 0.94)])
    scratch = (np.abs(_noise(rng, 20, 1, S) - 0.5) < 0.005) * np.clip((_noise(rng, 3, 2, S) - 0.55) * 4, 0, 1)  # broken-up wear lines
    grime = _grime(rng, S, y, wear)
    h = 0.6 * seam - 0.12 * inset + 0.12 * inset * np.clip(inset_e * 40, 0, 1) - 0.15 * diag + 0.25 * bolt + 0.03 * fine
    alb = c[None, None] * (pv * (0.9 + 0.12 * fine) * (1 - 0.35 * grime) * (0.45 + 0.55 * seam) * (1 - 0.35 * diag)
                           * np.where(inset, 0.85, 1.0) * (1 + 0.3 * bolt))[..., None] + 0.06 * scratch[..., None]
    gl = m.get("gloss", 0.0)  # 0 = matt coated deck (default); >0 = polished, reflective plates (sunset reflections)
    rough = np.clip(0.62 - 0.3 * gl + 0.2 * grime + 0.06 * n - 0.3 * scratch + 0.15 * gl * np.clip(grime, 0, 1), 0, 1)
    return dict(alb=alb, h=h, rough=rough, metal=np.clip(m.get("metallic", 0.2) + 0.4 * scratch - 0.15 * grime, 0, 1), nstr=0.9)  # coated deck: mostly diffuse


def k_hull_plating(S, rng, c, m):
    """Heavy sci-fi hull plating for towers / walls: tall plates with bevelled seams, riveted horizontal straps, louvred
    vent grilles in some plates, rain streaks running down from seams and rivets, scuffed bare-metal edges, roughness
    breakup (wet streaks glossier). Dark, worn, NOT uniformly glossy."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); n = _noise(rng, 4, 3, S); wear = m.get("wear", 0.55)
    cols, rows = 2, 2; px, py = (x * cols) % 1, (y * rows) % 1; e = _edge(px, py); seam = np.clip(e * 42, 0, 1) ** 0.7
    pid = (y * rows).astype(int) * cols + (x * cols).astype(int); pv = rng.uniform(0.8, 1.1, cols * rows)[pid]
    strap = (np.abs(py - 0.18) < 0.03); riv = _rivets(px, np.clip((py - 0.18) * 6 + 0.5, 0, 1), 8, 0.5, 0.05) * (np.abs(py - 0.18) < 0.06)
    vent = (pid == 2) & (np.abs(px - 0.5) < 0.3) & (np.abs(py - 0.62) < 0.18); louv = vent & (((py * 40) % 1) < 0.45)
    # streaks: dirt washed down from seams / straps (v grows downwards in the image = down the wall)
    src = np.clip(1 - seam, 0, 1) * 0.6 + strap * 0.8 + _noise(rng, 24, 1, S) * 0.15
    k = np.zeros_like(src); acc = np.zeros(S)
    for r in range(S): acc = acc * 0.985 + src[r]; k[r] = acc
    streak = np.clip(k / 18 * (0.4 + 0.6 * _noise(rng, 48, 1, S)), 0, 1) * np.clip((_noise(rng, 40, 1, S) - 0.35) * 3, 0, 1)
    grime = np.clip(_grime(rng, S, y, wear) + 0.6 * streak, 0, 1.5)
    edgewear = np.clip(1 - e * 28, 0, 1) * (seam > 0.6) * (_noise(rng, 16, 2, S) > 0.42)
    scratch = (np.abs(_noise(rng, 22, 1, S) - 0.5) < 0.006) * np.clip((_noise(rng, 3, 2, S) - 0.5) * 4, 0, 1)
    h = 0.55 * seam + 0.18 * strap + 0.3 * riv - 0.25 * vent + 0.15 * louv + 0.04 * fine
    alb = c[None, None] * (pv * (0.85 + 0.15 * fine) * (1 - 0.45 * grime) * (0.42 + 0.58 * seam) * np.where(vent, 0.45 + 0.6 * louv, 1.0)
                           * (1 + 0.15 * strap) * (1 + 0.3 * riv))[..., None]
    bare = np.clip(c * 1.8 + 0.1, 0, 1); alb = alb + (bare - alb) * (0.6 * edgewear + 0.35 * scratch)[..., None]
    rough = np.clip(0.5 + 0.22 * grime + 0.1 * n - 0.18 * streak - 0.2 * edgewear, 0.18, 1)
    metal = np.clip(0.45 + 0.45 * edgewear + 0.3 * scratch - 0.3 * np.clip(grime, 0, 1), 0, 1)
    return dict(alb=alb, h=h, rough=rough, metal=metal, nstr=1.1)


def k_chevron(S, rng, c, m):
    """Worn hazard chevrons (accent colour + near-black), chipped paint showing bare metal, dirt in the lower half."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); grime = _grime(rng, S, y, m.get("wear", 0.6))
    band = ((x * 4 + np.abs(y - 0.5) * 2) % 1) < 0.5; dark = np.array(m.get("dark", [0.06, 0.06, 0.06]))
    chip = _noise(rng, 20, 2, S) > 0.9 - 0.12 * m.get("wear", 0.6); edge = (y < 0.06) | (y > 0.94)
    alb = np.where(band[..., None], c[None, None], dark[None, None]) * ((0.85 + 0.15 * fine) * (1 - 0.45 * grime))[..., None]
    alb = np.where((chip | edge)[..., None], np.full(3, 0.42) * (0.8 + 0.2 * fine[..., None]), alb)
    return dict(alb=alb, h=0.6 - 0.1 * chip - 0.3 * edge + 0.03 * fine, rough=np.where(chip, 0.4, 0.62 + 0.25 * grime), metal=np.where(chip | edge, 0.85, 0.05), nstr=0.8)


def k_grating(S, rng, c, m):
    """Perforated walkway plate (oval holes) with solid side rails."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); grime = _grime(rng, S, y, m.get("wear", 0.5))
    hx, hy = (x * 8) % 1, (y * 10) % 1; hy = (hy + ((x * 8).astype(int) % 2) * 0.5) % 1
    ell = ((hx - 0.5) / 0.3) ** 2 + ((hy - 0.5) / 0.36) ** 2
    rail = np.minimum(x, 1 - x) < 0.07
    hole = (ell < 1) & ~rail
    h = np.where(hole, 0.0, 0.7 + 0.3 * np.clip((ell - 1) * 2, 0, 1)) + 0.03 * fine
    alb = np.where(hole[..., None], 0.03, c[None, None] * ((0.85 + 0.15 * fine) * (1 - 0.4 * grime))[..., None])
    return dict(alb=alb, h=h, rough=np.where(hole, 1.0, 0.45 + 0.3 * grime), metal=np.where(hole, 0.0, 0.6), nstr=1.6)


def k_concrete(S, rng, c, m):
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); n = _noise(rng, 4, 3, S); wear = m.get("wear", 0.3)
    pores = (_noise(rng, 64, 1, S) > 0.8).astype(float); line = (np.minimum(x % 0.5, y % 1.0) < 0.004).astype(float)
    crack = (np.abs(_noise(rng, 5, 2, S) - 0.5) < 0.004 + 0.006 * wear).astype(float) * (wear > 0.2)
    h = 0.5 + 0.12 * n + 0.05 * fine - 0.15 * pores - 0.3 * line - 0.4 * crack
    alb = c[None, None] * ((0.88 + 0.12 * fine + 0.06 * n) * (1 - 0.25 * pores) * (1 - 0.5 * crack) * (1 - 0.35 * _grime(rng, S, y, wear)))[..., None]
    return dict(alb=alb, h=h, rough=0.85 + 0.1 * fine, metal=0.0, nstr=0.8)


def k_rock(S, rng, c, m):
    """Faceted cliff rock: Voronoi slabs, strata, cracks, colour variation."""
    x, y = _xy(S); cid, e = _cells(rng, 14, S); n = _noise(rng, 6, 4, S)
    facet = rng.uniform(0.5, 1.0, 14)[cid]
    strata = 0.5 + 0.5 * np.sin((y + 0.12 * n) * 2 * np.pi * 6)
    crack = (np.abs(_noise(rng, 5, 2, S) - 0.5) < 0.006).astype(float)
    h = facet * np.clip(e * 3, 0, 1) ** 0.5 + 0.35 * n + 0.1 * strata - 0.4 * crack
    alb = c[None, None] * ((rng.uniform(0.85, 1.12, 14)[cid][..., None] * rng.uniform(0.96, 1.04, (14, 3))[cid]) * (0.65 + 0.45 * np.clip(h, 0, 1))[..., None]) * (1 - 0.5 * crack)[..., None]
    d = dict(alb=alb, h=h, rough=0.88 + 0.1 * n, metal=0.0, nstr=1.8)
    if m.get("veins"):  # Stage 56: glowing slime veins - a few long wandering cracks, emissive, crisp through the toon pass
        vn = _noise(rng, 2, 2, S); w = float(m.get("vein_width", 0.006))
        mask = ndimage.binary_dilation(np.abs(vn - 0.5) < w, iterations=max(1, S // 256))
        lab, nl = ndimage.label(mask); keep = rng.random(nl + 1) < float(m.get("vein_share", 0.55)); keep[0] = False; mask = keep[lab]  # only some of the cracks glow
        vc = np.array(m["veins"], float); glow_ = ndimage.gaussian_filter(mask.astype(float), S / 128)
        d["alb"] = alb * (1 - 0.35 * glow_[..., None]) + vc[None, None] * 0.3 * glow_[..., None]  # rock lit green round the veins
        d["alb"][mask] = vc; d["emit"] = np.clip(mask + 0.35 * glow_, 0, 1); ys, xs = np.nonzero(mask); d["_post"] = [(ys, xs, vc)]
    return d


def k_sand(S, rng, c, m):
    x, y = _xy(S); n = _noise(rng, 4, 3, S); fine = _noise(rng, 64, 1, S)
    h = 0.5 + 0.3 * np.sin((y + 0.15 * n) * 2 * np.pi * 8) + 0.2 * fine
    return dict(alb=c[None, None] * (0.9 + 0.12 * h + 0.05 * fine)[..., None], h=h, rough=0.95, metal=0.0, nstr=0.5)


def k_dirt(S, rng, c, m):
    x, y = _xy(S); n = _noise(rng, 8, 4, S); cid, e = _cells(rng, 60, S)
    peb = (rng.random(60) > 0.7)[cid] * np.clip(e * 4, 0, 1)
    h = 0.6 * n + 0.4 * peb
    alb = c[None, None] * (0.8 + 0.3 * n + 0.15 * peb)[..., None]
    return dict(alb=alb, h=h, rough=0.95, metal=0.0, nstr=1.0)


def k_grass(S, rng, c, m):
    x, y = _xy(S); fine = _noise(rng, 64, 1, S); patch = _noise(rng, 3, 3, S)
    dry = np.clip((patch - 0.6) * 3, 0, 1)
    alb = c[None, None] * (0.7 + 0.5 * fine)[..., None]
    alb = alb + (np.array([0.45, 0.38, 0.2]) - alb) * (0.6 * dry)[..., None]
    return dict(alb=alb, h=fine, rough=0.95, metal=0.0, nstr=0.7)


def k_toxic(S, rng, c, m):
    x, y = _xy(S); n = _noise(rng, 4, 3, S)
    sw = np.sin((x + 0.35 * _noise(rng, 3, 2, S)) * 2 * np.pi * 3) * np.sin((y + 0.35 * _noise(rng, 3, 2, S)) * 2 * np.pi * 2)
    cid, e = _cells(rng, 30, S); foam = np.clip(1 - e * 3, 0, 1) ** 3
    t = 0.8 + 0.2 * sw ** 2 + 0.12 * n + 0.35 * foam
    if m.get("streaks"):  # falling liquid: long streaks along v (the flow direction of falls / pours) - motion reads clearly
        st = ndimage.gaussian_filter1d(_noise(rng, 28, 2, S), S / 5, axis=0, mode="wrap"); st = (st - st.min()) / (np.ptp(st) + 1e-6)
        t = 0.62 + 0.55 * st + 0.25 * (st > 0.72) + 0.1 * n; foam = foam * 0.3
    alb = np.clip(c[None, None] * t[..., None] + np.stack([0.4 * foam, 0.1 * foam, 0.3 * foam], -1), 0, 1)
    return dict(alb=alb, h=0.5 * sw ** 2 + 0.3 * foam, rough=0.12, metal=0.0, emit=np.ones((S, S)), nstr=0.4)


def k_glow(S, rng, c, m):
    x, y = _xy(S); core = np.exp(-((x - 0.5) / 0.22) ** 2)
    alb = np.clip(c[None, None] * (0.55 + 0.9 * core)[..., None] + 0.3 * np.exp(-((x - 0.5) / 0.1) ** 2)[..., None], 0, 1)
    return dict(alb=alb, h=core, rough=0.2, metal=0.0, emit=np.clip(0.4 + core, 0, 1), nstr=0.3)


def k_machinery_panel(S, rng, c, m):
    """Dark industrial panels with recessed lights: red indicator blocks + white vertical light slots (emissive)."""
    d, k = _panels(S, rng, c, m)
    px, py, pid = k["px"], k["py"], (k["y"] * 2).astype(int) * 2 + (k["x"] * 2).astype(int)
    red = (pid == 0) & (np.abs(px - 0.5) < 0.16) & (np.abs(py - 0.78) < 0.05)
    white = (pid == 3) & (np.abs(px - 0.5) < 0.05) & (np.abs(py - 0.5) < 0.32)
    frame = ((pid == 0) & (np.abs(px - 0.5) < 0.2) & (np.abs(py - 0.78) < 0.09) | (pid == 3) & (np.abs(px - 0.5) < 0.09) & (np.abs(py - 0.5) < 0.36)) & ~red & ~white
    acc = np.array(m.get("accent", [1.0, 0.12, 0.08]))
    d["alb"] = np.where(red[..., None], acc, np.where(white[..., None], [1.0, 0.97, 0.9], np.where(frame[..., None], d["alb"] * 0.4, d["alb"])))
    d["h"] = np.where(frame, d["h"] - 0.25, d["h"]); d["emit"] = (red | white).astype(float)
    d["rough"] = np.where(red | white, 0.2, d["rough"]); d["metal"] = np.where(red | white, 0.0, d["metal"]); return d


def k_trim_light(S, rng, c, m):
    """Edge trim: dark metal with continuous red light lines (every half tile in v) and small white lamps."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); grime = _grime(rng, S, y, m.get("wear", 0.4))
    v = (y * 2) % 1; line = np.abs(v - 0.5) < 0.07; groove = (np.abs(v - 0.5) < 0.11) & ~line
    lamp = (np.abs(((x * 2) % 1) - 0.5) < 0.06) & (np.abs(v - 0.15) < 0.04)
    acc = np.array(m.get("accent", [1.0, 0.1, 0.06]))
    base = c[None, None] * ((0.85 + 0.15 * fine) * (1 - 0.4 * grime))[..., None]
    alb = np.where(line[..., None], acc, np.where(lamp[..., None], [1.0, 0.97, 0.9], np.where(groove[..., None], base * 0.35, base)))
    h = 0.7 - 0.4 * groove - 0.2 * line + 0.15 * lamp + 0.03 * fine
    emit = (line | lamp).astype(float)
    return dict(alb=alb, h=h, rough=np.where(emit > 0, 0.2, 0.45 + 0.3 * grime), metal=np.where(emit > 0, 0.0, 0.45), emit=emit, nstr=1.2)


def k_pipe(S, rng, c, m):
    """Large pipe: raised segment rings with bolts, lengthwise sheen, grime (v runs along the pipe)."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); grime = _grime(rng, S, y, m.get("wear", 0.5))
    v = (y * 2) % 1; ring = np.clip(1 - np.abs(v - 0.5) / 0.06, 0, 1)
    bolt = _dome(np.hypot(((x * 12) % 1 - 0.5) / 12, (v - 0.5) / 2), 0.01) * (ring > 0)
    h = 0.5 * np.clip(ring * 3, 0, 1) + 0.3 * bolt + 0.04 * fine
    alb = c[None, None] * ((0.85 + 0.15 * fine) * (1 + 0.25 * (ring > 0)) * (1 - 0.45 * grime))[..., None]
    return dict(alb=alb, h=h, rough=0.38 + 0.35 * grime, metal=0.55 - 0.3 * np.clip(grime, 0, 1), nstr=1.2)


def emblem_mask(src, W, H):
    """Emblem image -> float mask (H, W) fitted (aspect kept, centred). Alpha if the image has transparency, else every
    pixel that differs from the border colour (a logo on a plain background). Paths are relative to the repo root."""
    import os
    p = src if os.path.isabs(src) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), src)
    im = Image.open(p); a = np.asarray(im.convert("RGBA"), float) / 255
    if a[..., 3].min() < 0.5: k = a[..., 3]
    else:
        b = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]]); bg = np.median(b, 0)
        k = np.clip((np.abs(a[..., :3] - bg).max(-1) - 0.12) * 5, 0, 1)
    ys, xs = np.nonzero(k > 0.5); k = k[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sc = min(W / k.shape[1], H / k.shape[0]); w, h = max(1, int(k.shape[1] * sc)), max(1, int(k.shape[0] * sc))
    r = np.asarray(Image.fromarray((k * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS), float) / 255
    out = np.zeros((H, W)); y0, x0 = (H - h) // 2, (W - w) // 2; out[y0:y0 + h, x0:x0 + w] = r; return out


def _proc_emblem(W, H):
    """Default (original) alien emblem when no image is given: horned crest over an eye and a spike."""
    y, x = np.mgrid[0:H, 0:W] / np.array([H, W])[:, None, None]; x = x * W / H - (W / H - 1) / 2 if W > H else x  # square-ish coords
    crest = (y > 0.18) & (y < 0.5) & (np.abs(x - 0.5) < 0.42 - (y - 0.18) * 0.7) & ~(np.hypot(x - 0.5, y - 0.62) < 0.2)
    horns = ((np.abs(np.abs(x - 0.5) - 0.3) < 0.05 * (0.18 - y) / 0.13) & (y > 0.05) & (y < 0.18))
    eye = np.hypot(x - 0.5, y - 0.6) < 0.13
    spike = (y > 0.76) & (y < 0.97) & (np.abs(x - 0.5) < 0.09 * (0.97 - y) / 0.21)
    return (crest | horns | eye | spike).astype(float)


def crate_face(kind, W, H, m, fine=None):
    """One printed face of the alien cargo crate (W x H texels, rows top -> bottom): grey hull, dark corner brackets
    with glowing triangles, dark edge rails with light strips, and per face: "front" maroon plate with a black glyph
    (downward spike, ring, antenna), "side" plain maroon plate with dash marks, "top" bevelled frame round a glowing
    square. Returns (albedo, height, emission). Colours: crate_body, crate_plate, crate_glow."""
    y, x = (np.mgrid[0:H, 0:W] + 0.5) / np.array([H, W])[:, None, None]
    body, dark = np.array(m.get("crate_body", [0.46, 0.42, 0.47])), np.array([0.17, 0.11, 0.17])
    plate, glow, ink = np.array(m.get("crate_plate", [0.36, 0.09, 0.24])), np.array(m.get("crate_glow", [1.0, 0.12, 0.62])), np.array([0.03, 0.01, 0.04])
    f = fine if fine is not None else np.zeros((H, W))
    col = body * (0.94 + 0.06 * f)[..., None]; hgt = np.full((H, W), 0.5); em = np.zeros((H, W))
    def put(mask, c, hv=None, e=None):
        nonlocal col, hgt, em
        col = np.where(mask[..., None], c, col)
        if hv is not None: hgt = np.where(mask, hv, hgt)
        if e is not None: em = np.where(mask, e, em)
    dx, dy = np.minimum(x, 1 - x), np.minimum(y, 1 - y)
    if kind != "top":  # dark rails down both vertical edges with two light strips each
        put(dx < 0.1, dark, 0.7); put((dx > 0.03) & (dx < 0.065) & (np.abs(y - 0.5) < 0.24) & (np.abs(y - 0.5) > 0.03), glow, 0.75, 1.0)
    put(dx + dy < 0.2, dark, 0.8)  # corner brackets
    put((dx + dy < 0.12) & (dx > 0.015) & (dy > 0.015), glow, 0.85, 1.0)  # glowing corner triangles
    if kind == "front":  # maroon plate narrowing downwards (notch bottom right) with the black glyph
        top_w = 0.31 - 0.13 * (y - 0.2) / 0.66; pm = (y > 0.2) & (y < 0.86) & (np.abs(x - 0.52) < top_w) & ~((x > 0.6) & (y > 0.7))
        put(pm, plate, 0.4)
        tri = (y > 0.38) & (y < 0.68) & (np.abs(x - 0.5) < 0.17 * (0.68 - y) / 0.3)  # black downward triangle
        spike = (y >= 0.64) & (y < 0.84) & (np.abs(x - 0.5 - 0.04 * (y - 0.64) / 0.2) < 0.03 * (0.84 - y) / 0.2 + 0.004)
        ring = np.hypot((x - 0.53) * 1.15, y - 0.47) < 0.06; hole = np.hypot((x - 0.53) * 1.15, y - 0.47) < 0.03
        ant = ((np.abs(x - 0.5) < 0.011) & (y > 0.22) & (y < 0.39)) | (np.hypot(x - 0.5, y - 0.21) < 0.022)
        put(((tri & ~ring) | (ring & ~hole) | spike | ant), ink, 0.55); put(ring & ~hole & ~tri, ink, 0.55)
        put((ring & ~hole) & tri, plate, 0.45); put(hole, ink, 0.55)  # ring cut out of the triangle (plate colour), black eye
    elif kind == "side":
        pm = (y > 0.16) & (y < 0.86) & (x > 0.26 - 0.04 * (y - 0.16)) & (x < 0.74 + 0.02 * (y - 0.16)); put(pm, plate, 0.4)
        for k in range(2): put((y > 0.66 + k * 0.07) & (y < 0.69 + k * 0.07) & (x > 0.3 + 0.03 * k) & (x < 0.45 - 0.02 * k), dark, 0.45)
    else:
        put((np.abs(x - 0.5) < 0.26) & (np.abs(y - 0.5) < 0.26), plate * 0.8, 0.65)  # bevelled frame
        put((np.abs(x - 0.5) < 0.17) & (np.abs(y - 0.5) < 0.17), glow, 0.6, 1.0)
        put(((np.abs(x - 0.5) < 0.006) | (np.abs(y - 0.5) < 0.006)) & ((np.abs(x - 0.5) > 0.3) | (np.abs(y - 0.5) > 0.3)) & (dx > 0.12) & (dy > 0.12), dark, 0.45)  # seams
    return col, hgt, em


def _banner_atlas(S, rng, c, m):
    """Banner atlas ("atlas" in the material): pennant banner cloth with a glowing emblem ("emblem": image path, else a
    procedural one) in its "banner" rectangle, plus liquid decal cells ("drip", "puddle": slime running down walls /
    pooling on floors, colour "slime") so leaks share the banner's draw call. Rectangles are UV (u0, v0, u1, v1),
    trimesh convention (v up). The emblem sits in the "emblem_band" of the banner (fixed aspect, see shapes.cut_panel)."""
    x, y = _xy(S); fine = _noise(rng, 48, 2, S); n = _noise(rng, 6, 3, S)
    alb = np.zeros((S, S, 3)); h = np.full((S, S), 0.5); emit = np.zeros((S, S)); rough = np.full((S, S), 0.8)
    A = m["atlas"]; pix = lambda r: (int(r[0] * S), int((1 - r[3]) * S), int(r[2] * S), int((1 - r[1]) * S))  # x0, y0, x1, y1
    x0, y0, x1, y1 = pix(A["banner"]); W, H = x1 - x0, y1 - y0
    bx = (x[y0:y1, x0:x1] - x0 / S) / (W / S); v = 1 - (y[y0:y1, x0:x1] - y0 / S) / (H / S)
    cloth = c[None, None] * (0.7 + 0.035 * np.sin(bx * np.pi * 6) + 0.03 * fine[y0:y1, x0:x1])[..., None]
    border = (np.minimum(bx, 1 - bx) < 0.07) | (v > 0.965)
    sub = np.where(border[..., None], c * 0.32, cloth); hh = np.where(border, 0.75, 0.5)
    b0, b1 = m.get("emblem_band", (0.2, 0.8)); ea = m.get("emblem_aspect", 1.3)
    ey0, ey1 = y0 + int((1 - b1) * H), y0 + int((1 - b0) * H)  # emblem band rows (the band shows as w x ea*w)
    bw = int(W * 0.86); bh = int((ey1 - ey0) * 0.92)
    # mask drawn in display aspect (w : ea*w), then squashed into the band's texel aspect
    disp_h = int(bw * ea / 0.86 * 0.92); mk = emblem_mask(m["emblem"], bw, disp_h) if m.get("emblem") else _proc_emblem(bw, disp_h)
    mk = np.asarray(Image.fromarray((mk * 255).astype(np.uint8)).resize((bw, bh), Image.LANCZOS), float) / 255
    E = np.zeros((H, W)); oy, ox = ey0 - y0 + ((ey1 - ey0) - bh) // 2, (W - bw) // 2; E[oy:oy + bh, ox:ox + bw] = mk
    ec = np.array(m.get("emblem_color", [1.0, 0.16, 0.2]))
    sub = sub * (1 - E[..., None]) + ec * E[..., None]; hh = hh + 0.35 * E
    alb[y0:y1, x0:x1] = sub; h[y0:y1, x0:x1] = hh; emit[y0:y1, x0:x1] = np.maximum(E, np.where(border, 0.0, m.get("cloth_glow", 0.22)))
    sl = np.array(m.get("slime", [0.45, 1.0, 0.18]))
    if "drip" in A:  # runny slime: vertical streaks, bright core, darker edges
        x0, y0, x1, y1 = pix(A["drip"]); bx = (x[y0:y1, x0:x1] - x0 / S) / ((x1 - x0) / S)
        st = ndimage.gaussian_filter1d(_noise(rng, 24, 2, S)[y0:y1, x0:x1], S / 20, axis=0); st = (st - st.min()) / (np.ptp(st) + 1e-6)
        k = 0.65 + 0.35 * st + 0.25 * (np.abs(bx - 0.5) < 0.18)
        alb[y0:y1, x0:x1] = np.clip(sl * k[..., None], 0, 1); h[y0:y1, x0:x1] = 0.7; emit[y0:y1, x0:x1] = 0.55 + 0.25 * st; rough[y0:y1, x0:x1] = 0.15
    if "puddle" in A:  # pooled slime: brighter rim, glossy spots
        x0, y0, x1, y1 = pix(A["puddle"]); px_ = (x[y0:y1, x0:x1] - x0 / S) / ((x1 - x0) / S); py_ = (y[y0:y1, x0:x1] - y0 / S) / ((y1 - y0) / S)
        r = np.hypot(px_ - 0.5, py_ - 0.5) * 2; spot = n[y0:y1, x0:x1] > 0.68
        k = 0.7 + 0.3 * np.clip((r - 0.6) * 3, 0, 1) + 0.3 * spot
        alb[y0:y1, x0:x1] = np.clip(sl * k[..., None], 0, 1); h[y0:y1, x0:x1] = 0.7; emit[y0:y1, x0:x1] = 0.5 + 0.2 * spot; rough[y0:y1, x0:x1] = 0.1
    for cell in ("crate_front", "crate_side", "crate_top"):  # printed crate faces (crate_face: grey hull, pink lights)
        if cell in A:
            x0, y0, x1, y1 = pix(A[cell]); cc, hh, ee = crate_face(cell[6:], x1 - x0, y1 - y0, m, fine[y0:y1, x0:x1])
            alb[y0:y1, x0:x1] = cc; h[y0:y1, x0:x1] = hh; emit[y0:y1, x0:x1] = ee; rough[y0:y1, x0:x1] = 0.8
    post = []
    for cell in ("crate_front", "crate_side", "crate_top"):  # keep the printed crate colours exact (not posterised); ink their edges here
        if cell not in A: continue
        x0, y0, x1, y1 = pix(A[cell]); hh = _blur(h[y0:y1, x0:x1], 0.8); gy, gx = np.gradient(hh); g = np.hypot(gx, gy)
        ink = np.clip(g / (np.percentile(g, 99) + 1e-6) * 1.6 - 0.35, 0, 1) * (emit[y0:y1, x0:x1] < 0.5)
        post.append((slice(y0, y1), slice(x0, x1), alb[y0:y1, x0:x1] * (1 - ink[..., None]) + np.array([0.03, 0.01, 0.05]) * ink[..., None]))
    if "void" in A:  # bottomless-shaft fade: wall colour at the top -> pure black (no light, no emission) over the lower part
        x0, y0, x1, y1 = pix(A["void"]); vv = 1 - (np.arange(y0, y1) - y0 + 0.5) / (y1 - y0)  # v: 0 bottom .. 1 top
        k = np.clip((vv - m.get("void_black", 0.45)) / (1 - m.get("void_black", 0.45)), 0, 1) ** 1.6
        col = np.array(m.get("void_top", [0.2, 0.15, 0.27]))[None, :] * k[:, None]
        alb[y0:y1, x0:x1] = col[:, None, :]; h[y0:y1, x0:x1] = 0.5; emit[y0:y1, x0:x1] = 0.0; rough[y0:y1, x0:x1] = 1.0
        alb[:y0, x0:x1] = col[0]; h[:y0, x0:x1] = 0.5  # the column above continues the top colour (no bleeding at small mips)
        post.append((slice(0, y1), slice(x0, x1), alb[:y1, x0:x1].copy()))
        aom = np.ones((S, S)); aom[y0:y1, x0:x1] = k[:, None]  # occlusion: black part gets no sky light / reflection
    return dict(alb=alb, h=_blur(h, 0.6), rough=rough, metal=0.0, emit=emit, nstr=0.6, _post=post, **({"ao_mul": aom} if "void" in A else {}))


def k_banner(S, rng, c, m):
    if m.get("atlas"): return _banner_atlas(S, rng, c, m)
    alb = np.clip(legacy_texture_at("red_panel", S) * c[None, None] * 1.1, 0, 1)
    x, y = _xy(S); r = np.hypot(x - 0.5, (y - 0.42) * 1.2)
    emb = (np.abs(r - 0.17) < 0.022) | ((r < 0.25) & ((np.abs(x - 0.5) < 0.012) | (np.abs(y - 0.42) < 0.012)))
    frame = (np.minimum(x, 1 - x) < 0.07) | (y < 0.05) | (y > 0.86 + 0.14 * np.abs(x - 0.5) * 2)
    return dict(alb=alb, h=0.5 + 0.3 * emb - 0.3 * frame, rough=0.8, metal=np.where(frame, 0.7, 0.0),
                emit=np.where(emb, 1.0, np.where(frame, 0.0, 0.3)), nstr=0.8)


def k_factory_facade(S, rng, c, m):
    """Distant factory/skyline walls: dark panels, floor bands, sparse grid of lit windows (emissive, accent colour)."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); n = _noise(rng, 4, 3, S)
    fl, cols = 8, 10; fy, fx = (y * fl) % 1, (x * cols) % 1; cell = (y * fl).astype(int) * cols + (x * cols).astype(int)
    win = (np.abs(fx - 0.5) < 0.16) & (np.abs(fy - 0.5) < 0.14)
    lit = win & (rng.random(fl * cols) < m.get("lit", 0.3))[cell]
    band = np.abs(fy - 0.05) < 0.04
    acc = np.array(m.get("accent", [0.45, 1.0, 0.25]))
    base = c[None, None] * ((0.8 + 0.2 * fine + 0.1 * n) * np.where(band, 1.3, 1.0))[..., None]
    alb = np.where(lit[..., None], acc, np.where(win[..., None], base * 0.35, base))
    return dict(alb=alb, h=0.6 - 0.4 * win + 0.2 * band, rough=np.where(win, 0.25, 0.7), metal=np.where(win, 0.0, 0.4),
                emit=lit.astype(float), nstr=0.8)


def k_snow(S, rng, c, m):
    """Wind-packed snow: soft drifts, sparkle-free (mobile), slightly blue in the hollows."""
    x, y = _xy(S); n = _noise(rng, 3, 4, S); fine = _noise(rng, 48, 1, S)
    h = 0.7 * n + 0.15 * fine
    alb = c[None, None] * (0.9 + 0.1 * n)[..., None] * np.array([1.0, 1.0, 1.0]) + np.array([-0.03, -0.01, 0.02]) * (1 - n)[..., None]
    return dict(alb=alb, h=h, rough=0.75 + 0.1 * fine, metal=0.0, nstr=0.4)


def k_mud(S, rng, c, m):
    """Wet mud: dark puddles (smooth, shiny) between drier lumps."""
    x, y = _xy(S); n = _noise(rng, 5, 4, S); fine = _noise(rng, 40, 2, S)
    wet = np.clip((0.45 - n) * 5, 0, 1)
    h = (1 - wet) * (0.6 * n + 0.3 * fine)
    alb = c[None, None] * ((0.85 + 0.25 * fine) * (1 - 0.35 * wet))[..., None]
    return dict(alb=alb, h=h, rough=0.9 - 0.6 * wet, metal=0.0, nstr=0.9)


def k_asphalt(S, rng, c, m):
    """Road surface: fine aggregate, darker tyre tracks, cracks, faded lane line at u=0.5 if "lines": true."""
    x, y = _xy(S); fine = _noise(rng, 96, 1, S); n = _noise(rng, 4, 3, S); wear = m.get("wear", 0.4)
    crack = (np.abs(_noise(rng, 6, 3, S) - 0.5) < 0.004 * (0.5 + wear)).astype(float)
    tracks = np.exp(-((x - 0.28) / 0.07) ** 2) + np.exp(-((x - 0.72) / 0.07) ** 2)
    h = 0.2 * fine + 0.1 * n - 0.5 * crack
    alb = c[None, None] * ((0.88 + 0.2 * fine) * (1 - 0.12 * tracks) * (1 - 0.4 * crack) * (0.92 + 0.12 * n))[..., None]
    if m.get("lines"):
        line = (np.abs(x - 0.5) < 0.012) & ((y * 4) % 1 < 0.6); alb = np.where(line[..., None], np.array([0.75, 0.7, 0.55]) * (0.7 + 0.3 * n[..., None]), alb)
    return dict(alb=alb, h=h, rough=0.85 - 0.1 * tracks, metal=0.0, nstr=0.45)


def k_gravel(S, rng, c, m):
    """Loose gravel / path: many small stones of varied tint over dirt."""
    x, y = _xy(S); cid, e = _cells(rng, 140, S); n = _noise(rng, 6, 3, S)
    stone = (rng.random(140) > 0.25)[cid] * np.clip(e * 3, 0, 1) ** 0.6
    tint = rng.uniform(0.8, 1.15, 140)[cid]
    h = 0.75 * stone + 0.25 * n
    alb = c[None, None] * (np.where(stone > 0.05, tint * (0.75 + 0.35 * stone), 0.6 + 0.2 * n))[..., None]
    return dict(alb=alb, h=h, rough=0.92, metal=0.0, nstr=1.4)


def k_moss(S, rng, c, m):
    """Mossy forest floor / fantasy turf: clumps with darker gaps."""
    x, y = _xy(S); cid, e = _cells(rng, 40, S); fine = _noise(rng, 64, 1, S); n = _noise(rng, 4, 3, S)
    clump = np.clip(e * 2.5, 0, 1) ** 0.5
    h = 0.6 * clump + 0.3 * fine
    alb = c[None, None] * ((0.55 + 0.5 * clump) * (0.85 + 0.25 * fine) * rng.uniform(0.9, 1.1, 40)[cid])[..., None]
    return dict(alb=alb, h=h, rough=0.95, metal=0.0, nstr=1.0)



def _bsp_plates(rng, S, n=14, minside=0.12):
    """Irregular tileable plate layout (Stage 19): the unit square split recursively into ~n rectangles (seams at the tile
    edges line up with the neighbour tile). Returns (plate id map, edge distance in uv, list of rects)."""
    rects = [(0.0, 0.0, 1.0, 1.0)]
    while len(rects) < n:
        i = max(range(len(rects)), key=lambda k: (rects[k][2] - rects[k][0]) * (rects[k][3] - rects[k][1]) * rng.uniform(0.6, 1.4))
        x0, y0, x1, y1 = rects.pop(i)
        if (x1 - x0) > (y1 - y0) * rng.uniform(0.7, 1.3) and x1 - x0 > 2 * minside:
            cx = x0 + (x1 - x0) * rng.uniform(0.3, 0.7); rects += [(x0, y0, cx, y1), (cx, y0, x1, y1)]
        elif y1 - y0 > 2 * minside:
            cy = y0 + (y1 - y0) * rng.uniform(0.3, 0.7); rects += [(x0, y0, x1, cy), (x0, cy, x1, y1)]
        else: rects.append((x0, y0, x1, y1)); break
    x, y = _xy(S); pid = np.zeros((S, S), int); e = np.ones((S, S))
    for k, (x0, y0, x1, y1) in enumerate(rects):
        msk = (x >= x0) & (x < x1) & (y >= y0) & (y < y1); pid[msk] = k
        e = np.where(msk, np.minimum(np.minimum(x - x0, x1 - x), np.minimum(y - y0, y1 - y)), e)
    return pid, e, rects


def k_wall_works(S, rng, c, m):
    """Factory wall from the user's fan reference (Stage 19): big riveted plates in an IRREGULAR layout (no 2x2 grid),
    bevelled seams, rivets near plate corners, some plates with louvred vents, some with an X-braced inset, some with
    pairs of green light dashes (emissive), vertical conduit runs, dirt streaks washed down from seams. Tile it large
    (tile_m ~12 m): within one tile nothing repeats."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S); wear = m.get("wear", 0.5)
    pid, e, rects = _bsp_plates(rng, S, int(m.get("plates", 14)))
    seam = np.clip(e * S / 3.0, 0, 1) ** 0.7; pv = rng.uniform(0.78, 1.12, len(rects))[pid]
    h = 0.55 * seam + 0.03 * fine; alb_k = pv * (0.42 + 0.58 * seam); emit = np.zeros((S, S)); dash = np.zeros((S, S), bool)
    for k, (x0, y0, x1, y1) in enumerate(rects):
        msk = pid == k; w_, h_ = x1 - x0, y1 - y0; kind = rng.choice(["plain", "vent", "brace", "lights", "inset", "plain"], p=[0.28, 0.22, 0.17, 0.07, 0.16, 0.1])
        for cx_, cy_ in ((x0 + 0.018, y0 + 0.018), (x1 - 0.018, y0 + 0.018), (x0 + 0.018, y1 - 0.018), (x1 - 0.018, y1 - 0.018)):  # corner rivets
            r_ = np.hypot(x - cx_, y - cy_); h = h + 0.3 * _dome(r_, 0.008) * msk; alb_k = alb_k * np.where(msk & (r_ < 0.008), 1.25, 1.0)
        ix0, iy0, ix1, iy1 = x0 + w_ * 0.18, y0 + h_ * 0.18, x1 - w_ * 0.18, y1 - h_ * 0.18; inner = msk & (x > ix0) & (x < ix1) & (y > iy0) & (y < iy1)
        if kind == "vent":
            louv = inner & ((((y - iy0) / max(iy1 - iy0, 1e-3)) * int(rng.integers(6, 11))) % 1 < 0.45); h = h - 0.25 * inner + 0.18 * louv; alb_k = alb_k * np.where(inner, np.where(louv, 0.85, 0.35), 1)
        elif kind == "brace":
            u_, v_ = (x - ix0) / (ix1 - ix0 + 1e-6), (y - iy0) / (iy1 - iy0 + 1e-6); bar = inner & ((np.abs(u_ - v_) < 0.07) | (np.abs(u_ + v_ - 1) < 0.07) | (_edge(u_, v_) < 0.05))
            h = h - 0.12 * inner + 0.2 * bar; alb_k = alb_k * np.where(inner & ~bar, 0.6, 1.0)
        elif kind == "lights":
            n_ = int(rng.integers(2, 4)); lw = min(0.06, w_ * 0.22)
            for j in range(n_):
                yy = iy0 + (iy1 - iy0) * (j + 0.5) / n_
                for xx in (x0 + w_ * 0.35, x0 + w_ * 0.65):
                    dmask = msk & (np.abs(x - xx) < lw / 2) & (np.abs(y - yy) < 0.008); dash |= dmask
        elif kind == "inset":
            h = h - 0.15 * inner; alb_k = alb_k * np.where(inner, 0.82, 1.0)
    for k in range(int(rng.integers(2, 4))):  # vertical conduits (two thin pipes) crossing plates
        cx_ = rng.uniform(0.05, 0.95); pipe = np.abs(x - cx_) < 0.006; pipe2 = np.abs(x - cx_ - 0.016) < 0.005
        h = np.where(pipe | pipe2, 0.85, h); alb_k = np.where(pipe | pipe2, 0.55 + 0.4 * np.clip(1 - np.abs(x - cx_) / 0.006, 0, 1), alb_k)
    src = np.clip(1 - seam, 0, 1) * 0.5 + _noise(rng, 24, 1, S) * 0.1; acc = np.zeros(S); kk = np.zeros_like(src)
    for r in range(S): acc = acc * 0.985 + src[r]; kk[r] = acc
    streak = np.clip(kk / 16 * _noise(rng, 48, 1, S), 0, 1) * np.clip((_noise(rng, 40, 1, S) - 0.4) * 3, 0, 1)
    grime = np.clip(_grime(rng, S, y, wear) + 0.5 * streak, 0, 1.4)
    alb = c[None, None] * (alb_k * (0.88 + 0.12 * fine) * (1 - 0.4 * grime))[..., None]
    lc = np.array(m.get("light_color", [0.45, 1.0, 0.25])); alb = np.where(dash[..., None], lc, alb); emit = dash.astype(float)
    d = dict(alb=alb, h=h, rough=np.clip(0.6 + 0.2 * grime, 0, 1), metal=0.3 * np.ones((S, S)), nstr=1.0)
    if m.get("emissive"): d["emit"] = emit
    d["_post"] = [(*np.nonzero(dash), lc)] if dash.any() else None  # light dashes stay crisp through the toon pass
    return d


def k_wall_slimed(S, rng, c, m):
    """The same irregular plates (another layout) with green slime leaking from seams and vents: drips that run down,
    pool along horizontal seams and stain the plates; the slime glows (emissive mask)."""
    d = k_wall_works(S, rng, c, dict(m, emissive=None, plates=int(m.get("plates", 11))))
    x, y = _xy(S); seam = d["h"] < 0.3
    src = (seam & (_noise(rng, 20, 1, S) > float(m.get("leak_threshold", 0.8)))).astype(float)  # leak sources along a few seams (user: less green)
    acc = np.zeros(S); run = np.zeros((S, S)); jit = _noise(rng, 60, 1, S)
    for r in range(S): acc = np.maximum(acc * (0.975 + 0.02 * jit[r]), src[r]); run[r] = acc
    drip = (run > 0.55) & (np.abs(((x * 90 + 3 * _noise(rng, 8, 1, S)) % 1) - 0.5) < 0.1 + 0.14 * run)  # thinner drips
    stain = np.clip(_blur(run, S / 128) * 1.1 - 0.35, 0, 1) * (_noise(rng, 14, 2, S) > 0.5)  # fainter, patchier stains
    sc = np.array(m.get("slime_color", [0.42, 1.0, 0.18]))
    alb = d["alb"] * (1 - 0.55 * stain[..., None]) + sc * 0.55 * stain[..., None]; alb = np.where(drip[..., None], sc * (0.75 + 0.25 * run[..., None]), alb)
    d.update(alb=alb, h=d["h"] + 0.08 * drip, rough=np.where(drip, 0.25, d["rough"]))
    if m.get("emissive"): d["emit"] = np.clip(drip * 0.9 + stain * 0.35, 0, 1)
    d["_post"] = [(*np.nonzero(drip), None)] if False else d.get("_post")
    return d


def k_ceiling_works(S, rng, c, m):
    """Factory ceiling from the user's ceiling reference (Stage 21): dark olive riveted plates in an irregular layout
    (recursive split, "seed" changes it per room), rivet rows along the seams, vent grilles of different sizes (bars
    one way or the other), X-braced panels, small slot vents, bundles of 3-5 conduits with brackets running across
    plates, and patchy green moss grime (not glowing). Tile large (~20 m): nothing in one tile repeats."""
    x, y = _xy(S); fine = _noise(rng, 32, 2, S)
    pid, e, rects = _bsp_plates(rng, S, int(m.get("plates", 18)), 0.08)
    seam = np.clip(e * S / 2.5, 0, 1) ** 0.7; pv = rng.uniform(0.8, 1.15, len(rects))[pid]
    h = 0.55 * seam + 0.03 * fine; k_ = pv * (0.45 + 0.55 * seam)
    rv = (e < 0.012) & (e > 0.004) & ((((x + y) * S / 9) % 1) < 0.22)  # rivet rows just inside the seams
    h = h + 0.25 * rv; k_ = k_ * np.where(rv, 1.3, 1.0)
    for k, (x0, y0, x1, y1) in enumerate(rects):
        msk = pid == k; w_, h_ = x1 - x0, y1 - y0
        kind = rng.choice(["plain", "vent_h", "vent_v", "brace", "slots", "inset"], p=[0.3, 0.17, 0.13, 0.14, 0.12, 0.14])
        mx, my = min(0.2, 0.1 + rng.uniform(0, 0.1)), min(0.2, 0.1 + rng.uniform(0, 0.1))
        ix0, iy0, ix1, iy1 = x0 + w_ * mx, y0 + h_ * my, x1 - w_ * mx, y1 - h_ * my
        inner = msk & (x > ix0) & (x < ix1) & (y > iy0) & (y < iy1); u_, v_ = (x - ix0) / (ix1 - ix0 + 1e-6), (y - iy0) / (iy1 - iy0 + 1e-6)
        if kind in ("vent_h", "vent_v"):
            bars = inner & ((((v_ if kind == "vent_h" else u_) * int(rng.integers(7, 15))) % 1) < 0.42)
            frame = inner & (_edge(u_, v_) < 0.05)
            h = h - 0.3 * inner + 0.22 * bars + 0.3 * frame; k_ = k_ * np.where(inner, np.where(bars | frame, 0.9, 0.18), 1)
        elif kind == "brace":
            bar = inner & ((np.abs(u_ - v_) < 0.05) | (np.abs(u_ + v_ - 1) < 0.05) | (_edge(u_, v_) < 0.04))
            h = h - 0.1 * inner + 0.22 * bar; k_ = k_ * np.where(inner & ~bar, 0.7, 1.0)
        elif kind == "slots":
            n_ = int(rng.integers(2, 5)); sl = np.zeros_like(inner)
            for j in range(n_): sl |= inner & (np.abs(v_ - (j + 0.5) / n_) < 0.05) & (np.abs(u_ - 0.5) < 0.3)
            h = h - 0.2 * sl; k_ = k_ * np.where(sl, 0.2, 1.0)
        elif kind == "inset":
            h = h - 0.12 * inner; k_ = k_ * np.where(inner, 0.85, 1.0)
    for b in range(int(rng.integers(2, 4))):  # conduit bundles (3-5 parallel pipes) with brackets
        vert = rng.random() < 0.6; c0 = rng.uniform(0.05, 0.85); n_ = int(rng.integers(3, 6)); a, b_ = (x, y) if vert else (y, x)
        for j in range(n_):
            cc = c0 + j * 0.013; p_ = np.abs(a - cc) < 0.005; prof = np.clip(1 - np.abs(a - cc) / 0.005, 0, 1)
            h = np.where(p_, 0.75 + 0.2 * prof, h); k_ = np.where(p_, 0.5 + 0.45 * prof, k_)
        br = (np.abs(a - (c0 + n_ * 0.0065)) < n_ * 0.0075) & ((((b_ * 9) % 1) < 0.025))
        h = np.where(br, 0.95, h); k_ = np.where(br, 0.95, k_)
    moss = np.clip((_noise(rng, 10, 3, S) - 0.62) * 4, 0, 1) * np.clip((_noise(rng, 40, 2, S) - 0.4) * 3, 0, 1)  # patchy, never a whole plate
    mc = np.array(m.get("moss", [0.27, 0.33, 0.12]))
    alb = c[None, None] * (k_ * (0.88 + 0.12 * fine))[..., None]; alb = alb * (1 - 0.55 * moss[..., None]) + mc * 0.55 * moss[..., None] * k_[..., None]
    return dict(alb=alb, h=h, rough=np.full((S, S), 0.75), metal=0.25 * np.ones((S, S)), nstr=1.0)


def k_screen_ui(S, rng, c, m):
    """Glowing alien control screen (Stage 22, user's monitor reference): deep purple panel with a faint grid, a big
    radar circle holding a green wireframe robot schematic (original design: boxy head, antenna, round eyes), dials and
    buttons in orange / magenta, a column of alien glyphs with a red horned emblem, a grinning orange icon, indicator
    dots. Drawn for a 4:3 screen (squeezed into the square texture; the panel stretches it back). "seed" = another layout.
    Fully emissive (screens light themselves), no normals."""
    from PIL import ImageDraw
    W, H = int(S * 4 / 3), S; im = Image.new("RGB", (W, H), (34, 10, 58)); d = ImageDraw.Draw(im); u = S / 512
    R = lambda *a: [int(v * u) for v in a]
    for y in range(H):  # vertical gradient
        t = y / H; d.line([(0, y), (W, y)], fill=(int(40 + 25 * t), int(12 + 6 * t), int(70 + 30 * t)))
    for g in range(0, int(W / u), 24): d.line(R(g, 0, g, 512), fill=(58, 24, 96))
    for g in range(0, 512, 24): d.line([(0, int(g * u)), (W, int(g * u))], fill=(58, 24, 96))
    ORANGE, MAG, PINK, PURP, GREEN, RED = (255, 110, 30), (220, 40, 230), (255, 60, 150), (150, 60, 255), (120, 255, 60), (255, 40, 70)
    cx, cy, rr = rng.uniform(300, 360), rng.uniform(250, 280), rng.uniform(150, 175)
    d.ellipse(R(cx - rr - 10, cy - rr - 10, cx + rr + 10, cy + rr + 10), outline=PURP, width=int(10 * u))
    d.ellipse(R(cx - rr, cy - rr, cx + rr, cy + rr), fill=(30, 12, 52), outline=(90, 40, 160), width=int(3 * u))
    for k in range(-3, 4): d.line(R(cx + k * rr / 4, cy - rr * 0.95, cx + k * rr / 4, cy + rr * 0.95), fill=(60, 30, 110), width=1)
    for k in range(-3, 4): d.line(R(cx - rr * 0.95, cy + k * rr / 4, cx + rr * 0.95, cy + k * rr / 4), fill=(60, 30, 110), width=1)
    s_ = rr / 150; DK = (24, 70, 26)  # robot schematic (user reference): green outlines over a dark green fill
    P_ = lambda px, py: (int((cx + px * s_) * u), int((cy + py * s_) * u)); lw = max(1, int(3 * u))
    def box(x0, y0, x1, y1, r=4, w=lw): d.rounded_rectangle([P_(x0, y0), P_(x1, y1)], radius=max(1, int(r * s_ * u)), fill=DK, outline=GREEN, width=w)
    def circ(px, py, r, fill=DK, w=lw): d.ellipse([P_(px - r, py - r), P_(px + r, py + r)], fill=fill, outline=GREEN, width=w)
    def seg(*pts, w=lw): d.line([P_(*q) for q in pts], fill=GREEN, width=w)
    seg((-56, -24), (-110, -30), w=max(1, int(1.5 * u))); seg((56, -24), (110, -30), w=max(1, int(1.5 * u)))  # thin lines out from the shoulders
    seg((0, -112), (0, -128)); circ(0, -132, 5, fill=GREEN)  # antenna
    box(-34, -112, 34, -62, 6); circ(-37, -88, 4); circ(37, -88, 4)  # head + ear bolts
    for ex in (-15, 15): circ(ex, -92, 11); circ(ex, -92, 5); d.ellipse([P_(ex - 2, -94), P_(ex + 2, -90)], fill=GREEN)  # ringed eyes
    box(-10, -76, 10, -68, 2); seg((-4, -76), (-4, -68), w=1); seg((4, -76), (4, -68), w=1)  # mouth grille
    box(-9, -62, 9, -52, 2)  # neck
    d.polygon([P_(-44, -52), P_(44, -52), P_(36, -4), P_(-36, -4)], fill=DK, outline=GREEN); d.line([P_(-44, -52), P_(44, -52), P_(36, -4), P_(-36, -4), P_(-44, -52)], fill=GREEN, width=lw)  # torso
    box(-16, -42, 16, -14, 2); box(-9, -35, 9, -21, 1, max(1, lw - 1))  # chest panel
    box(-26, -4, 26, 8, 3); box(-18, 8, 18, 20, 3)  # waist + hip block
    for sd in (-1, 1):
        circ(sd * 50, -44, 9)  # shoulder joint
        d.polygon([P_(sd * 52, -38), P_(sd * 62, -34), P_(sd * 76, -6), P_(sd * 66, -2)], fill=DK, outline=GREEN); seg((sd * 52, -38), (sd * 62, -34), (sd * 76, -6), (sd * 66, -2), (sd * 52, -38))  # upper arm
        circ(sd * 72, -2, 7)  # elbow
        d.polygon([P_(sd * 70, 4), P_(sd * 80, 0), P_(sd * 90, 24), P_(sd * 80, 28)], fill=DK, outline=GREEN); seg((sd * 70, 4), (sd * 80, 0), (sd * 90, 24), (sd * 80, 28), (sd * 70, 4))  # forearm
        seg((sd * 82, 28), (sd * 78, 40), (sd * 86, 44)); seg((sd * 88, 26), (sd * 98, 36), (sd * 94, 44))  # two-pronged claw
        box(sd * 6 - 7, 20, sd * 6 + 7 + sd * 4, 52, 3)  # thigh
        circ(sd * 10, 56, 6)  # knee
        box(sd * 10 - 7, 60, sd * 10 + 7, 86, 3)  # shin
        box(sd * 10 - 12 + sd * 2, 86, sd * 10 + 12 + sd * 2, 98, 3)  # boot
    for tx, ty in ((cx + rr * 0.55, cy - rr * 0.6), (cx - rr * 0.95, cy + rr * 0.5)):  # callout boxes with glyph lines
        d.rectangle(R(tx, ty, tx + 60, ty + 34), outline=PINK, width=int(2 * u))
        for j in range(3): d.line(R(tx + 6, ty + 8 + j * 9, tx + 6 + rng.uniform(25, 50), ty + 8 + j * 9), fill=PINK, width=int(3 * u))
    dx, dy = rng.uniform(70, 95), rng.uniform(95, 130)  # big dial, left
    d.pieslice(R(dx - 60, dy - 60, dx + 60, dy + 60), 90, 360, fill=MAG); d.ellipse(R(dx - 34, dy - 34, dx + 34, dy + 34), fill=ORANGE)
    d.ellipse(R(dx - 12, dy - 12, dx + 12, dy + 12), fill=(40, 12, 60))
    for a in range(90, 360, 30): d.line(R(dx, dy, dx + 60 * np.cos(np.radians(a)), dy + 60 * np.sin(np.radians(a))), fill=(40, 12, 60), width=int(3 * u))
    for k in range(int(rng.integers(4, 7))):  # scattered dots / buttons
        bx, by_, br = rng.uniform(30, 200), rng.uniform(200, 470), rng.uniform(8, 20); d.ellipse(R(bx - br, by_ - br, bx + br, by_ + br), fill=[ORANGE, MAG, PINK, PURP][k % 4])
    for k in range(2): d.rounded_rectangle(R(200 + k * 70, 28, 255 + k * 70, 48), radius=int(8 * u), fill=ORANGE)
    fx, fy_ = rng.uniform(520, 560), 70  # grinning icon
    d.ellipse(R(fx - 32, fy_ - 32, fx + 32, fy_ + 32), fill=ORANGE, outline=(60, 15, 20), width=int(3 * u))
    d.polygon(R(fx - 20, fy_ - 12, fx - 6, fy_ - 4, fx - 20, fy_ - 2), fill=(50, 10, 20)); d.polygon(R(fx + 20, fy_ - 12, fx + 6, fy_ - 4, fx + 20, fy_ - 2), fill=(50, 10, 20))
    d.chord(R(fx - 22, fy_ - 12, fx + 22, fy_ + 22), 0, 180, fill=(50, 10, 20))
    gx = rng.uniform(560, 600); d.rounded_rectangle(R(gx - 40, 130, gx + 40, 495), radius=int(30 * u), outline=PURP, width=int(4 * u))
    d.polygon(R(gx - 22, 170, gx + 22, 170, gx + 14, 205, gx, 225, gx - 14, 205), fill=RED); d.polygon(R(gx - 22, 170, gx - 30, 150, gx - 12, 172), fill=RED); d.polygon(R(gx + 22, 170, gx + 30, 150, gx + 12, 172), fill=RED)
    for row in range(8):  # alien glyph column
        for col in range(2):
            x0, y0 = gx - 26 + col * 30, 250 + row * 29; t = rng.integers(4)
            if t == 0: d.polygon(R(x0, y0 + 18, x0 + 9, y0, x0 + 18, y0 + 18), outline=MAG, width=int(3 * u))
            elif t == 1: d.rectangle(R(x0, y0, x0 + 16, y0 + 18), outline=MAG, width=int(3 * u)); d.line(R(x0 + 8, y0, x0 + 8, y0 + 18), fill=MAG, width=int(3 * u))
            elif t == 2: d.line(R(x0, y0 + 4, x0 + 6, y0 + 16, x0 + 11, y0 + 2, x0 + 17, y0 + 14), fill=MAG, width=int(3 * u))  # zigzag
            else: d.ellipse(R(x0 + 2, y0 + 2, x0 + 16, y0 + 16), outline=MAG, width=int(3 * u)); d.line(R(x0 + 9, y0 - 2, x0 + 9, y0 + 20), fill=MAG, width=int(3 * u))
    for k in range(4): d.ellipse(R(470 + k * 0, 290 + k * 40, 492, 312 + k * 40), fill=[GREEN, PINK, ORANGE, MAG][k]); d.line(R(498, 301 + k * 40, 540, 301 + k * 40), fill=PURP, width=int(4 * u))
    a = np.asarray(im.resize((S, S), Image.BILINEAR), float) / 255.0
    xx, yy = _xy(S); ax = (xx - 0.5) * 4 / 3; ay = yy - 0.5  # screen glass (Stage 23): scanlines, vignette, glare, pixel grid, rounded corners
    a = a * (1 - 0.18 * (((np.arange(S) // max(1, S // 170)) % 2)[:, None]))
    a = a * np.clip(1.15 - 1.1 * (ax ** 2 + ay ** 2), 0.45, 1)[..., None]
    glare = np.clip(1 - np.abs((xx + yy * 0.6) - 0.42) / 0.06, 0, 1) * np.clip(1 - yy * 1.6, 0, 1); a = a + 0.22 * glare[..., None]
    a = a * (1 - 0.08 * ((np.arange(S) % max(2, S // 128)) == 0)[None, :, None])
    rc = 0.06; qx, qy = np.clip(np.abs(ax) - (2 / 3 - rc), 0, None), np.clip(np.abs(ay) - (0.5 - rc), 0, None)
    a = np.where((np.hypot(qx, qy) > rc)[..., None], 0.015, a)
    return dict(alb=np.clip(a, 0, 1), h=np.zeros((S, S)), rough=np.full((S, S), 0.5), metal=0.0, emit=np.ones((S, S)), nstr=0.0)


def k_tv_casing(S, rng, c, m):
    """TV / monitor casing for the tv_body shape's front UVs (Stage 23): moulded dark plastic with a lit top-left edge
    bevel and a shadow lip round the screen opening, screw heads in the corners, vent slits along the top, and a chin
    with a dotted speaker grille, a badge plate, two knobs and a power LED (emissive). "border" / "chin" must match the
    shape (fractions of width / height)."""
    from PIL import ImageDraw
    bf, cf = m.get("border", 0.07), m.get("chin", 0.2)
    x, y = _xy(S); v = 1 - y  # v = 0 at the bottom of the TV
    fine = _noise(rng, 32, 2, S); base = c[None, None] * (0.9 + 0.12 * v[..., None] + 0.05 * fine[..., None])
    e_out = np.minimum(np.minimum(x, 1 - x), np.minimum(v, 1 - v)); inside = (x > bf) & (x < 1 - bf) & (v > cf) & (v < 1 - bf * 1.33)
    band = lambda dist: np.clip(1 - dist / 0.018, 0, 1)
    hi = np.maximum(band(1 - v), band(x)) - 0.6 * np.maximum(band(v), band(1 - x))  # bevel: lit top / left edges, dark bottom / right (smooth, no seams)
    ddx = np.maximum.reduce([bf - x, np.zeros_like(x), x - (1 - bf)]); ddy = np.maximum.reduce([cf - v, np.zeros_like(v), v - (1 - bf * 1.33)])
    lip = np.clip(1 - np.hypot(ddx, ddy) / 0.012, 0, 1) * ~inside  # shadow lip hugging the opening (true distance to the rectangle)
    k_ = 1 + 0.45 * hi - 0.45 * lip; h = 0.6 + 0.3 * np.clip(hi, 0, 1) - 0.4 * lip
    im = Image.new("L", (S, S), 0); dr = ImageDraw.Draw(im); em = Image.new("L", (S, S), 0); de = ImageDraw.Draw(em)
    P = lambda u, vv: (int(u * S), int((1 - vv) * S))
    for u, vv in ((0.03, 0.035), (0.97, 0.035), (0.03, 0.965), (0.97, 0.965)):  # screws
        a, b = P(u - 0.012, vv + 0.016), P(u + 0.012, vv - 0.016); dr.ellipse([a, b], fill=200); dr.line([P(u - 0.009, vv), P(u + 0.009, vv)], fill=60, width=max(1, S // 256))
    for k in range(9):  # vent slits along the top
        u = 0.32 + k * 0.045; dr.rectangle([P(u, 0.985), P(u + 0.018, 1 - bf * 1.33 + 0.012)], fill=40)
    for i in range(14):  # dotted speaker grille (left of the chin)
        for j in range(4):
            u, vv = 0.08 + i * 0.023, cf * (0.25 + j * 0.17); a, b = P(u - 0.006, vv + 0.008), P(u + 0.006, vv - 0.008); dr.ellipse([a, b], fill=35)
    dr.rounded_rectangle([P(0.45, cf * 0.72), P(0.6, cf * 0.28)], radius=max(2, S // 128), fill=170)  # badge plate
    for k in range(3): dr.line([P(0.47 + k * 0.035, cf * 0.5), P(0.49 + k * 0.035, cf * 0.5)], fill=240, width=max(1, S // 200))
    for u in (0.7, 0.8):  # knobs
        a, b = P(u - 0.03, cf * 0.5 + 0.04), P(u + 0.03, cf * 0.5 - 0.04); dr.ellipse([a, b], fill=120, outline=230, width=max(1, S // 256))
        dr.line([P(u, cf * 0.5), P(u + 0.012, cf * 0.5 + 0.025)], fill=250, width=max(1, S // 200))
    a, b = P(0.9 - 0.012, cf * 0.5 + 0.016), P(0.9 + 0.012, cf * 0.5 - 0.016); de.ellipse([a, b], fill=255)  # power LED
    dmask = np.asarray(im, float) / 255.0; led = np.asarray(em, float) / 255.0
    det = dmask > 0; k_ = np.where(det, 0.3 + 1.1 * dmask, k_); h = np.where(det, 0.3 + 0.6 * dmask, h)
    badge = np.asarray(m.get("badge", [0.85, 0.15, 0.35])); lc = np.asarray(m.get("led", [0.4, 1.0, 0.3]))
    alb = base * k_[..., None]; bmask = (dmask > 0.6) & (np.abs(x - 0.525) < 0.075) & (v < cf * 0.75) & (v > cf * 0.25)
    alb = np.where(bmask[..., None], badge * (0.6 + 0.4 * dmask[..., None]), alb); alb = np.where((led > 0.5)[..., None], lc, alb)
    d = dict(alb=alb, h=_blur(h, 0.6), rough=np.full((S, S), 0.45), metal=0.0, nstr=0.8)
    if m.get("emissive"): d["emit"] = (led > 0.5).astype(float)
    d["_post"] = [(*np.nonzero(led > 0.5), lc)]
    return d


def k_bigscreen(S, rng, c, m):
    """Wall-sized window fills (Stage 24, Invader-Zim-like, original designs). m["mode"]:
      "broadcast": giant robot propaganda viewscreen - purple broadcast, a riveted robot head with antenna bolts, visor
                   with two glaring red eyes and a jaw grille in a ringed target with rays, red glyph headline, a ticker of
                   marching robot heads, warning triangles, a production panel (cog in a crosshair) and status bars;
                   scanlines + vignette.
      "specimen":  robot assembly tank - glowing green liquid with bubbles and caustics, a half-built robot (open chest
                   with a power core, dangling arms and legs, one eye booting) hung from feed cables, glass glare,
                   glyph label plate, hazard edge.
    Drawn for m["aspect"] (w / h) and squeezed into the square texture; fully emissive."""
    from PIL import ImageDraw
    ar = float(m.get("aspect", 1.7)); W, H = int(S * ar), S; u = S / 512; R = lambda *a: [int(v * u) for v in a]
    ORANGE, MAG, PINK, PURP, GREEN, RED, BLK = (255, 110, 30), (220, 40, 230), (255, 60, 150), (150, 60, 255), (120, 255, 60), (255, 40, 70), (12, 4, 18)
    def glyph_row(dr, x0, y0, n, size, col, w=3):
        for k in range(n):
            x, t = x0 + k * size * 1.35, rng.integers(5)
            if t == 0: dr.polygon(R(x, y0 + size, x + size / 2, y0, x + size, y0 + size), outline=col, width=int(w * u))
            elif t == 1: dr.rectangle(R(x, y0, x + size, y0 + size), outline=col, width=int(w * u)); dr.line(R(x + size / 2, y0, x + size / 2, y0 + size), fill=col, width=int(w * u))
            elif t == 2: dr.line(R(x, y0 + size * 0.2, x + size * 0.35, y0 + size, x + size * 0.65, y0, x + size, y0 + size * 0.8), fill=col, width=int(w * u))
            elif t == 3: dr.ellipse(R(x, y0, x + size, y0 + size), outline=col, width=int(w * u)); dr.line(R(x + size / 2, y0 - 3, x + size / 2, y0 + size + 3), fill=col, width=int(w * u))
            else: dr.line(R(x, y0, x + size, y0 + size), fill=col, width=int(w * u)); dr.line(R(x + size, y0, x, y0 + size), fill=col, width=int(w * u)); dr.ellipse(R(x + size * 0.35, y0 + size * 0.35, x + size * 0.65, y0 + size * 0.65), fill=col)
    if m.get("mode", "broadcast") == "broadcast":
        im = Image.new("RGB", (W, H), (30, 8, 50)); d = ImageDraw.Draw(im); Wu = W / u
        for y in range(H): t = y / H; d.line([(0, y), (W, y)], fill=(int(36 + 30 * t), int(8 + 6 * t), int(64 + 26 * t)))
        cx, cy = Wu / 2, 270
        for k in range(16):  # targeting rays
            a = 2 * np.pi * k / 16; d.line(R(cx + 120 * np.cos(a), cy + 120 * np.sin(a), cx + 330 * np.cos(a), cy + 330 * np.sin(a)), fill=(70, 20, 110), width=int(6 * u))
        for rr_, col, w_ in ((205, PURP, 12), (185, MAG, 6), (165, (60, 16, 90), 0)):
            if w_: d.ellipse(R(cx - rr_, cy - rr_, cx + rr_, cy + rr_), outline=col, width=int(w_ * u))
            else: d.ellipse(R(cx - rr_, cy - rr_, cx + rr_, cy + rr_), fill=col)
        STEEL, DARK = (150, 150, 175), (70, 66, 92)
        for sx in (-1, 1):  # antenna bolts and ear dishes
            d.line(R(cx + sx * 55, cy - 115, cx + sx * 85, cy - 175), fill=DARK, width=int(8 * u)); d.ellipse(R(cx + sx * 85 - 13, cy - 188, cx + sx * 85 + 13, cy - 162), fill=RED, outline=BLK, width=int(3 * u))
            d.rectangle(R(cx + sx * 118 - 18, cy - 50, cx + sx * 118 + 18, cy + 30), fill=DARK, outline=BLK, width=int(4 * u))
        d.polygon(R(cx - 115, cy - 120, cx + 115, cy - 120, cx + 100, cy + 95, cx - 100, cy + 95), fill=STEEL, outline=BLK)  # the robot head
        d.rectangle(R(cx - 115, cy - 120, cx + 115, cy - 96), fill=(185, 185, 205))
        for rx in (-98, 98):
            for ry in (-108, 80): d.ellipse(R(cx + rx - 5, cy + ry - 5, cx + rx + 5, cy + ry + 5), fill=DARK)  # rivets
        d.rectangle(R(cx - 92, cy - 72, cx + 92, cy + 8), fill=BLK, outline=DARK, width=int(5 * u))  # visor
        for ex, er in ((-44, 30), (44, 30)):  # two glaring eyes in the visor
            d.ellipse(R(cx + ex - er, cy - 32 - er, cx + ex + er, cy - 32 + er), fill=RED); d.ellipse(R(cx + ex - er * 0.45, cy - 32 - er * 0.45, cx + ex + er * 0.45, cy - 32 + er * 0.45), fill=(255, 210, 120))
            d.polygon(R(cx + ex - er - 6, cy - 70, cx + ex + er + 6, cy - 70, cx + ex + (er + 6) * (1 if ex > 0 else -1) * 0, cy - 52), fill=BLK)  # angry brow
        d.rectangle(R(cx - 62, cy + 30, cx + 62, cy + 78), fill=DARK, outline=BLK, width=int(4 * u))  # jaw grille
        for k in range(7): d.line(R(cx - 50 + k * 16.6, cy + 36, cx - 50 + k * 16.6, cy + 72), fill=(30, 26, 40), width=int(5 * u))
        d.rectangle(R(30, 20, Wu - 30, 82), fill=(60, 10, 40), outline=RED, width=int(4 * u)); glyph_row(d, 60, 32, int((Wu - 120) / 52), 38, RED, 5)  # headline
        d.rectangle(R(0, 470, Wu, 512), fill=(20, 4, 30))  # ticker: a marching robot army
        for k in range(int(Wu / 34)):
            x = 14 + k * 34; d.rectangle(R(x, 478, x + 22, 500), fill=MAG if k % 4 else ORANGE); d.rectangle(R(x + 4, 484, x + 18, 490), fill=BLK); d.line(R(x + 11, 478, x + 11, 472), fill=MAG, width=int(2 * u))
        px, py = 120, 280; d.rectangle(R(px - 95, py - 120, px + 95, py + 140), outline=PURP, width=int(5 * u))  # production panel: a cog in a crosshair
        cog = [(px + (62 if (k // 2) % 2 == 0 else 48) * np.cos(2 * np.pi * (k + 0.5 * (k % 2)) / 24), py + (62 if (k // 2) % 2 == 0 else 48) * np.sin(2 * np.pi * (k + 0.5 * (k % 2)) / 24)) for k in range(24)]
        d.polygon([(int(x * u), int(y * u)) for x, y in cog], fill=(200, 200, 220), outline=BLK); d.ellipse(R(px - 22, py - 22, px + 22, py + 22), fill=(40, 10, 60))
        d.line(R(px - 85, py, px + 85, py), fill=RED, width=int(3 * u)); d.line(R(px, py - 85, px, py + 85), fill=RED, width=int(3 * u)); d.ellipse(R(px - 75, py - 75, px + 75, py + 75), outline=RED, width=int(3 * u))
        glyph_row(d, px - 80, py + 95, 5, 24, ORANGE, 3)
        bx = Wu - 215  # status bars
        d.rectangle(R(bx - 10, 160, bx + 190, 440), outline=PURP, width=int(5 * u))
        for k in range(6):
            v = rng.uniform(0.3, 1.0); d.rectangle(R(bx + 10, 180 + k * 42, bx + 10 + 160 * v, 205 + k * 42), fill=[GREEN, ORANGE, PINK][k % 3])
        for x0 in (40, Wu - 100):
            for y0 in (100, 400): d.polygon(R(x0, y0 + 50, x0 + 30, y0, x0 + 60, y0 + 50), fill=ORANGE, outline=BLK); d.line(R(x0 + 30, y0 + 15, x0 + 30, y0 + 35), fill=BLK, width=int(5 * u))
        a = np.asarray(im.resize((S, S), Image.BILINEAR), float) / 255.0
        xx, yy = _xy(S); a = a * (1 - 0.2 * (((np.arange(S) // max(1, S // 200)) % 2)[:, None, None]))
        a = a * np.clip(1.2 - 1.2 * (((xx - 0.5) * 1.2) ** 2 + (yy - 0.5) ** 2), 0.5, 1)[..., None]
    else:
        im = Image.new("RGB", (W, H), (20, 60, 14)); d = ImageDraw.Draw(im); Wu = W / u
        for y in range(H): t = y / H; d.line([(0, y), (W, y)], fill=(int(40 + 60 * t), int(140 + 80 * t), int(20 + 30 * t)))
        cx, cy = Wu / 2, 250
        RB, RD, LIT = (88, 100, 96), (34, 44, 40), (255, 90, 60); cy = 212  # robot hangs clear of the label plate
        for k in range(3):  # feed cables from the top into the robot's head and shoulders
            tx, ty = cx + (k - 1) * 70, (cy - 140) if k == 1 else (cy - 20)
            d.line(R(tx, 0, tx, ty), fill=(30, 50, 26), width=int(14 * u)); d.line(R(tx, 0, tx, ty), fill=(90, 130, 70), width=int(4 * u))
        for sx in (-1, 1):  # dangling arms (shoulder, elbow, claw) and legs
            d.line(R(cx + sx * 78, cy - 10, cx + sx * 120, cy + 70), fill=RD, width=int(22 * u)); d.line(R(cx + sx * 120, cy + 70, cx + sx * 112, cy + 150), fill=RD, width=int(18 * u))
            d.ellipse(R(cx + sx * 120 - 14, cy + 56, cx + sx * 120 + 14, cy + 84), fill=RB, outline=RD, width=int(3 * u))
            d.polygon(R(cx + sx * 112 - 16, cy + 150, cx + sx * 112 + 16, cy + 150, cx + sx * 112 + 8, cy + 178, cx + sx * 112 - 8, cy + 178), fill=RB, outline=RD)
            d.line(R(cx + sx * 30, cy + 110, cx + sx * 38, cy + 200), fill=RD, width=int(24 * u)); d.rectangle(R(cx + sx * 38 - 24, cy + 196, cx + sx * 38 + 24, cy + 214), fill=RB, outline=RD, width=int(3 * u))
        d.rounded_rectangle(R(cx - 80, cy - 30, cx + 80, cy + 115), radius=int(22 * u), fill=RB, outline=RD, width=int(5 * u))  # torso
        d.rectangle(R(cx - 40, cy, cx + 40, cy + 60), fill=RD); d.ellipse(R(cx - 16, cy + 14, cx + 16, cy + 46), fill=(120, 255, 90))  # open chest, power core
        for k in range(3): d.line(R(cx - 34, cy + 72 + k * 12, cx + 34, cy + 72 + k * 12), fill=RD, width=int(4 * u))
        d.rectangle(R(cx - 12, cy - 48, cx + 12, cy - 28), fill=RD)  # neck
        d.rounded_rectangle(R(cx - 62, cy - 140, cx + 62, cy - 46), radius=int(14 * u), fill=RB, outline=RD, width=int(5 * u))  # head
        d.rectangle(R(cx - 48, cy - 118, cx + 48, cy - 80), fill=(14, 22, 18))  # dark visor, one eye still booting
        d.ellipse(R(cx - 38, cy - 112, cx - 12, cy - 86), fill=LIT); d.ellipse(R(cx + 12, cy - 112, cx + 38, cy - 86), outline=(60, 80, 60), width=int(3 * u))
        d.line(R(cx, cy - 140, cx, cy - 165), fill=RD, width=int(6 * u)); d.ellipse(R(cx - 9, cy - 174, cx + 9, cy - 156), fill=LIT)  # antenna
        for k in range(4): d.line(R(cx - 40 + k * 26, cy - 66, cx - 40 + k * 26, cy - 54), fill=RD, width=int(5 * u))  # mouth slits
        for k in range(int(rng.integers(30, 50))):  # bubbles
            bx, by, br = rng.uniform(20, Wu - 20), rng.uniform(20, 460), rng.uniform(3, 12); d.ellipse(R(bx - br, by - br, bx + br, by + br), outline=(210, 255, 180), width=max(1, int(2 * u)))
        d.rectangle(R(cx - 140, 440, cx + 140, 492), fill=(40, 40, 46), outline=(200, 200, 200), width=int(3 * u)); glyph_row(d, cx - 120, 452, 8, 26, (255, 200, 60), 3)
        a = np.asarray(im.resize((S, S), Image.BILINEAR), float) / 255.0
        xx, yy = _xy(S); caus = np.abs(np.sin(_noise(rng, 12, 2, S) * 18)) ** 8; a = a + 0.12 * caus[..., None] * np.array([0.6, 1, 0.5])
        glare = np.clip(1 - np.abs((xx - yy * 0.4) - 0.25) / 0.05, 0, 1) + np.clip(1 - np.abs((xx - yy * 0.4) - 0.33) / 0.02, 0, 1); a = a + 0.2 * glare[..., None]
        edge = np.minimum(np.minimum(xx, 1 - xx), np.minimum(yy, 1 - yy)) < 0.025; hz = (((xx + yy) * 30) % 1) < 0.5
        a = np.where(edge[..., None], np.where(hz[..., None], np.array([0.95, 0.75, 0.1]), np.array([0.05, 0.05, 0.05])), a)
    return dict(alb=np.clip(a, 0, 1), h=np.zeros((S, S)), rough=np.full((S, S), 0.4), metal=0.0, emit=np.ones((S, S)), nstr=0.0)


def k_corrosion(S, rng, c, m):
    """Stage 28 corroded band (cut-out: d["alpha"] 0 = no corrosion): u runs along the wall (tiles), v = 0 at the band
    top -> 1 just under the liquid line (v ~ 0.89). Rust-black pits with bright green crust rims, olive-brown stained
    metal, drips reaching up from the liquid, a ragged top edge; denser towards the liquid. The crust glows."""
    x, y = _xy(S); line = float(m.get("line_v", 0.89))
    dens = np.clip((y - 0.08) / (line - 0.08), 0, 1) ** 1.4  # 0 at the band top, 1 at the liquid line
    n1, n2 = _noise(rng, 3, 3, S), _noise(rng, 9, 2, S)
    col = _noise(rng, 16, 1, S)[0]  # per-column drip height (tileable along u)
    drip = (np.abs(((x * 7 + 0.15 * n2) % 1) - 0.5) < 0.05 + 0.05 * dens) & (y > line - 0.5 * np.clip(col[None, :] * 1.6 - 0.45, 0, 1))
    cover = (n1 * 1.1 + dens * 0.8 + 0.15 * n2 > 1.05) | drip | (y > line - 0.03)  # ragged patches: some reach high, most stay low ("slightly")
    pn = _noise(rng, int(m.get("pits", 14)), 2, S)
    pit = cover & (pn > 0.76 - 0.08 * dens)  # irregular rust-black pits, more near the liquid
    rim = cover & ~pit & (pn > 0.66 - 0.08 * dens)  # green crust ring round each pit
    stain = np.array([0.17, 0.19, 0.08]) * (0.85 + 0.3 * n2[..., None]) + np.array([0.05, 0.12, 0.0]) * dens[..., None]; crust = np.array([0.45, 1.0, 0.16])
    alb = np.where(pit[..., None], np.array([0.02, 0.04, 0.02]), np.where(rim[..., None], crust * (0.7 + 0.3 * dens[..., None]), stain))
    alb = np.where(drip[..., None] & ~pit[..., None], crust * 0.8, alb)
    h = np.where(pit, 0.0, 0.5)
    emit = (rim | drip).astype(float) * (0.4 + 0.6 * dens)
    ys, xs = np.nonzero(pit)
    return dict(alb=alb, h=h, rough=0.6, metal=0.0, emit=emit, nstr=0.4, alpha=cover.astype(float),
                _post=[(ys, xs, np.array([0.02, 0.035, 0.02]))])  # pits stay near-black after the toon pass


def _atlas_cell(sub, S_w, S_h):
    """One atlas cell (float RGB, S_h x S_w): a generated screen (material dict) or {"image": path} (repo-relative,
    resized to the cell - e.g. the slime arena's TV easter egg)."""
    if sub.get("image"):
        path = sub["image"] if os.path.isabs(sub["image"]) else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), sub["image"])
        return np.asarray(Image.open(path).convert("RGB").resize((S_w, S_h), Image.LANCZOS), float) / 255.0
    sub = dict(sub); S = max(S_w, S_h); sub["res"] = S
    d = PBR[sub["type"]](S, np.random.default_rng(sum(map(ord, sub["type"])) + int(sub.get("seed", 0)) * 7919), np.array(sub.get("color", [1, 1, 1]), float), sub)
    return np.asarray(Image.fromarray((np.clip(d["alb"], 0, 1) * 255).astype(np.uint8)).resize((S_w, S_h), Image.BILINEAR), float) / 255.0


def k_screen_atlas(S, rng, c, m):
    """Two screens side by side in ONE texture (one material, one draw call): left = m["left"], right = m["right"]
    (material dicts of screen_ui / bigscreen); objects choose a half with uv_region (atlas cells "a" / "b").
    Stage 52: m["grid"] = [[top-left, top-right], [bottom-left, bottom-right]] - four cells (S/2 x S/2) in the same
    texture size, each a material dict or {"image": path}; pair it with atlas rects (UV v runs up: bottom row v 0..0.5)."""
    if m.get("grid"):
        G = m["grid"]; h, w = S // len(G), S // len(G[0])
        alb = np.concatenate([np.concatenate([_atlas_cell(cell, w, h) for cell in row], 1) for row in G], 0)
        return dict(alb=alb, h=np.zeros((S, S)), rough=np.full((S, S), 0.45), metal=0.0, emit=np.ones((S, S)), nstr=0.0)
    out, dflt = {}, {"left": {"type": "screen_ui", "seed": 1}, "right": {"type": "screen_ui", "seed": 2}}
    for k_ in ("left", "right"):
        sub = dict(m.get(k_) or dflt[k_]); sub["res"] = S; d = PBR[sub["type"]](S, np.random.default_rng(sum(map(ord, sub["type"])) + int(sub.get("seed", 0)) * 7919), np.array(sub.get("color", [1, 1, 1]), float), sub)
        out[k_] = np.asarray(Image.fromarray((np.clip(d["alb"], 0, 1) * 255).astype(np.uint8)).resize((S // 2, S), Image.BILINEAR), float) / 255.0
    return dict(alb=np.concatenate([out["left"], out["right"]], 1), h=np.zeros((S, S)), rough=np.full((S, S), 0.45), metal=0.0, emit=np.ones((S, S)), nstr=0.0)

PBR = {k[2:]: f for k, f in globals().items() if k.startswith("k_")}


def legacy_texture_at(kind, S):
    global TEX
    old, TEX = TEX, S
    try: return legacy_texture(kind)
    finally: TEX = old


# ---------------------------------------------------------------- maps -> glTF material
def _normal(h, strength):
    S = h.shape[0]; k = strength * S / 24
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / 2 * k; dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / 2 * k
    n = np.stack([-dx, -dy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5  # glTF tangent space: +Y = increasing v (down the image)


def _ao(h):
    S = h.shape[0]; cav = _blur(h, S / 48) - h
    return np.clip(1 - 2.2 * np.clip(cav, 0, None), 0.35, 1)


def _img(a, q):
    b = io.BytesIO(); Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).save(b, "JPEG", quality=q)
    return Image.open(io.BytesIO(b.getvalue()))  # JPEG-backed -> embedded as jpeg


def maps(m):
    """level.json material -> dict of float maps (alb, h, rough, metal, emit|None) + resolution."""
    kind = ALIASES.get(m["type"], m["type"]); c = np.array(m["color"], float)
    rng = np.random.default_rng(sum(map(ord, kind)) + int(m.get("seed", 0)) * 7919)  # "seed": another layout of the same kind
    if kind in PBR:
        S = int(m.get("res", DEFAULT_RES.get(kind, 256)))
        d = PBR[kind](S, rng, c, m)
    else:  # legacy stylised kinds: albedo as before, normals/roughness derived from it
        S = int(m.get("res", TEX)); a = legacy_texture_at(kind, S) * c[None, None] * 1.1
        lum = a.mean(-1); shiny = kind in ("metal", "window", "water")
        d = dict(alb=a, h=_blur(lum / (lum.max() + 1e-6), 0.8), rough=(0.45 if shiny else 0.85) + 0.1 * (1 - lum), metal=0.6 if kind == "metal" else 0.0,
                 nstr=0.0 if kind in ("window", "water") else 0.6)
        if m.get("emissive"): d["emit"] = np.ones((S, S))
    for k in ("rough", "metal"):
        d[k] = np.broadcast_to(np.asarray(d[k], float), (S, S))
    d.setdefault("emit", None); d["S"] = S; d["kind"] = kind
    if m.get("toon"): d = toonify(d, m)
    for ys, xs, a in d.pop("_post", None) or []: d["alb"][ys, xs] = a  # cells that must stay smooth (not posterised / inked)
    return d


def toonify(d, m):
    """Cartoon version of any kind ("toon": true): surface noise smoothed away, colour posterised into a few flat
    steps, dark INK lines wherever the height map has an edge (panel seams, rivets, grating holes, frames), matte and
    non-metallic (no realistic reflections), weak normals. Emissive parts keep their colour."""
    S = d["S"]; h = _blur(np.asarray(d["h"], float), max(0.6, S / 256)); alb = _blur3(np.clip(d["alb"], 0, 1), S / 160)
    med = np.median(alb.reshape(-1, 3), 0); dev = alb - med; big = np.clip((np.abs(dev).max(-1) - 0.12) * 8, 0, 1)[..., None]
    alb = med + dev * (big + (1 - big) * m.get("toon_flatten", 0.2))  # grime / wear blotches flattened, accents kept
    lv = m.get("toon_levels", 5); alb = np.round(alb * lv) / lv * 0.85 + alb * 0.15  # mostly flat steps, a hint of the original
    gy, gx = np.gradient(h); g = np.hypot(gx, gy) * S; ref = np.percentile(g, 99.5) + 1e-6
    ink = np.clip((g / ref - m.get("ink_threshold", 0.18)) * 3.0, 0, 1) * m.get("ink", 0.9)
    ink_col = np.array(m.get("ink_color", [0.03, 0.01, 0.05]))
    alb = alb * (1 - ink[..., None]) + ink_col * ink[..., None]
    d.update(alb=alb, rough=np.full((S, S), m.get("toon_rough", 0.9)), metal=np.zeros((S, S)), nstr=d.get("nstr", 1.0) * 0.25, h=h)
    return d


def _blur3(a, s):
    return np.stack([_blur(a[..., k], s) for k in range(a.shape[-1])], -1)


def make_material(name, m):
    """Returns (trimesh PBRMaterial, [pixel counts of the images it embeds])."""
    if name == "_invisible":
        return trimesh.visual.material.PBRMaterial(name="Collider_invisible", baseColorFactor=[1, 0, 0, 0], alphaMode="BLEND"), []
    d = maps(m); alb = np.clip(d["alb"], 0, 1)
    ao = _ao(d["h"]) if d["nstr"] > 0 else np.ones_like(d["rough"])
    if d.get("ao_mul") is not None: ao = ao * d["ao_mul"]  # e.g. bottomless-shaft cell: no sky light / reflections at all
    orm = np.stack([ao, np.clip(d["rough"], 0.04, 1), np.clip(d["metal"], 0, 1)], -1)
    kw = dict(name=name, baseColorTexture=_img(alb, 85), metallicFactor=1.0, roughnessFactor=1.0)
    if d.get("alpha") is not None and m.get("cutout"):  # Stage 28: cut-out decal (corrosion band): RGBA, alpha-tested, opaque pass
        b = io.BytesIO(); Image.fromarray((np.clip(np.dstack([alb, d["alpha"]]), 0, 1) * 255).astype(np.uint8), "RGBA").save(b, "PNG")
        kw.update(baseColorTexture=Image.open(io.BytesIO(b.getvalue())), alphaMode="MASK", alphaCutoff=float(m["cutout"]))
    if m.get("alpha") is not None:  # Stage 20: see-through (e.g. tube glass): blended, both sides drawn
        kw.update(baseColorFactor=[1.0, 1.0, 1.0, float(m["alpha"])], alphaMode="BLEND", doubleSided=True)
    ormi = _img(orm, 88); kw["metallicRoughnessTexture"] = ormi; kw["occlusionTexture"] = ormi
    px = [d["S"] ** 2] * 2
    if d["nstr"] > 0:
        kw["normalTexture"] = _img(_normal(d["h"], d["nstr"]), 92); px.append(d["S"] ** 2)
    if d["emit"] is not None:
        kw["emissiveTexture"] = _img(alb * d["emit"][..., None], 85); kw["emissiveFactor"] = m.get("emissive", [1.0, 1.0, 1.0]); px.append(d["S"] ** 2)
    return trimesh.visual.material.PBRMaterial(**kw), px


_AVG = {}


def avg_linear_color(m):
    """Mean albedo of a material's texture x colour, in LINEAR space (for vertex-coloured distant terrain)."""
    key = repr(sorted(m.items()))
    if key not in _AVG:
        d = maps(dict(m, res=64)); a = np.clip(d["alb"], 0, 1).reshape(-1, 3).mean(0); _AVG[key] = (a ** 2.2).tolist()
    return _AVG[key]


def atlas_material(name, defs, cell=128, cols=4):
    """One material for many small props (Stage 9 scatter): each def's maps in its own atlas cell -> one draw call per
    merged mesh. Returns (material, pixel counts, {index: (u0, v0, u1, v1)} with a 3 px inset against bleeding)."""
    rows = (len(defs) + cols - 1) // cols; W, H = cols * cell, rows * cell
    alb = np.zeros((H, W, 3)); h = np.zeros((H, W)); rough = np.ones((H, W)); metal = np.zeros((H, W)); emit = np.zeros((H, W)); rects = {}; anyemit = False
    for k, m in enumerate(defs):
        d = maps(dict(m, res=cell)); r, c = divmod(k, cols); ys, xs = slice(r * cell, (r + 1) * cell), slice(c * cell, (c + 1) * cell)
        alb[ys, xs] = np.clip(d["alb"], 0, 1); h[ys, xs] = d["h"] * d["nstr"] / 1.5; rough[ys, xs] = d["rough"]; metal[ys, xs] = d["metal"]
        if m.get("emissive"): emit[ys, xs] = 1.0; anyemit = True
        p = 3 / cell; rects[k] = (c / cols + p / cols, r / rows + p / rows, (c + 1) / cols - p / cols, (r + 1) / rows - p / rows)
    orm = np.stack([_ao(h), np.clip(rough, 0.04, 1), np.clip(metal, 0, 1)], -1); ormi = _img(orm, 88)
    kw = dict(name=name, baseColorTexture=_img(alb, 85), metallicFactor=1.0, roughnessFactor=1.0, metallicRoughnessTexture=ormi, occlusionTexture=ormi,
              normalTexture=_img(_normal(h, 1.0), 92))
    if anyemit: kw["emissiveTexture"] = _img(alb * emit[..., None], 85); kw["emissiveFactor"] = [1.0, 1.0, 1.0]
    return trimesh.visual.material.PBRMaterial(**kw), [W * H] * (4 if anyemit else 3), rects
