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
  snow, mud, asphalt ("lines": true = lane line), gravel, moss (Stage 9 terrain layers).  Legacy (stylised, albedo-derived normals): cobblestone,
  stone_brick, plaster, wood, painted_wood, trim_wood, door_wood, window, roof_tiles, roof_slate, metal, water, soil.
"""
import io, numpy as np, trimesh
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
DEFAULT_RES = {"hull_plating": 512, "industrial_metal": 512, "scifi_floor": 512, "rock": 512, "painted_metal": 512, "damaged_metal": 512,
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
    return dict(alb=alb, h=h, rough=0.88 + 0.1 * n, metal=0.0, nstr=1.8)


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
    return dict(alb=alb, h=_blur(h, 0.6), rough=rough, metal=0.0, emit=emit, nstr=0.6)


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
    rng = np.random.default_rng(sum(map(ord, kind)))
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
    orm = np.stack([_ao(d["h"]) if d["nstr"] > 0 else np.ones_like(d["rough"]), np.clip(d["rough"], 0.04, 1), np.clip(d["metal"], 0, 1)], -1)
    kw = dict(name=name, baseColorTexture=_img(alb, 85), metallicFactor=1.0, roughnessFactor=1.0)
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
