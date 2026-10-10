"""Stage 9: universal procedural terrain (CPU, deterministic) from level.json["terrain"] - the editable master.

  python3 pipeline/terrain.py levels/<name>      # print terrain stats / chunk hashes (build_level.py builds it)

Definition (all keys optional except extent; see SCENE_SPEC.md "world"):
  seed, extent [x0, z0, x1, z1] (detailed NEAR grid), cell (m, 2), chunk (cells per chunk side, multiple of 4),
  base_y, biome (layer preset), noise {amplitude, scale, octaves, ridged 0..1, warp},
  features [ {id, type, ...} ]   named, individually editable shapes (hill, mountain, ridge, barrier, valley, canyon,
                                 plateau/mesa, crater, cliff, dunes, field, river, lake, coast, road/path/street, pad,
                                 heightmap (image), mask (image))
  layers [ {id, material, mask|slope|height|above_water|patch} ]  per-triangle material rules (first match wins)
  water {level}                  sea level (a coast feature lowers terrain below it)
  boundary {points}              playable polygon (invisible colliders + natural barrier feature)
  zones {middle: {radius, rise}} middle ring (simplified continuation, no collision); far = Stage 2 background
  scatter [...]                  instanced vegetation / rocks (scatter.py)
  lod {ranges: [r0, r1]}         LOD switch distances for the mobile export

Determinism + locality: every feature has its own noise seed derived from (terrain seed, feature id), and a finite
influence box, so editing one feature only changes the chunks it touches (chunk hashes in terrain.json prove it).
Seamless: chunks are slices of ONE global vertex grid (shared border vertices, normals from the global height field);
lower LODs keep full-resolution borders and stitch inwards, so neighbouring chunks never crack whatever LOD they use.
"""
import hashlib, json, math, os, sys
import numpy as np
import trimesh

HERE = os.path.dirname(os.path.abspath(__file__))


# ------------------------------------------------------------------ noise (gradient noise, vectorised)
class Perlin:
    def __init__(self, seed):
        r = np.random.default_rng(int(seed) & 0xFFFFFFFF)
        p = r.permutation(256); self.p = np.r_[p, p]
        a = r.uniform(0, 2 * np.pi, 256); self.g = np.c_[np.cos(a), np.sin(a)]
        self.off = r.uniform(-1000, 1000, (8, 2))

    def __call__(self, x, y):
        x = np.asarray(x, float); y = np.asarray(y, float)
        xi = np.floor(x).astype(np.int64); yi = np.floor(y).astype(np.int64); xf, yf = x - xi, y - yi; xi &= 255; yi &= 255
        u = xf ** 3 * (xf * (xf * 6 - 15) + 10); v = yf ** 3 * (yf * (yf * 6 - 15) + 10); p, g = self.p, self.g
        def dot(ix, iy, dx, dy):
            h = p[p[ix] + iy]; return g[h, 0] * dx + g[h, 1] * dy
        a = dot(xi, yi, xf, yf) + u * (dot(xi + 1, yi, xf - 1, yf) - dot(xi, yi, xf, yf))
        b = dot(xi, yi + 1, xf, yf - 1) + u * (dot(xi + 1, yi + 1, xf - 1, yf - 1) - dot(xi, yi + 1, xf, yf - 1))
        return (a + v * (b - a)) * 1.414

    def fbm(self, x, y, octaves=4, lac=2.03, gain=0.5):
        s, amp, tot = 0.0, 1.0, 0.0
        for o in range(octaves):
            ox, oy = self.off[o % 8]; s = s + amp * self(x * lac ** o + ox, y * lac ** o + oy); tot += amp; amp *= gain
        return s / tot

    def ridged(self, x, y, octaves=4, lac=2.1, gain=0.5):
        """0..1, sharp crests (mountain ridges)."""
        s, amp, tot, w = 0.0, 1.0, 0.0, 1.0
        for o in range(octaves):
            ox, oy = self.off[(o + 3) % 8]; r = (1 - np.abs(self(x * lac ** o + ox, y * lac ** o + oy))) ** 2
            s = s + amp * r * w; w = np.clip(r * 1.6, 0, 1); tot += amp; amp *= gain
        return s / tot


def smooth(e0, e1, x):
    den = np.asarray(e1, float) - e0; den = np.where(np.abs(den) < 1e-9, 1e-9, den)
    t = np.clip((np.asarray(x, float) - e0) / den, 0, 1); return t * t * (3 - 2 * t)


def bell(d):
    d = np.asarray(d, float); return np.where(d < 1, 0.5 * (1 + np.cos(np.pi * np.clip(d, 0, 1))), 0.0)


def _sid(*parts):
    return int(hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


# ------------------------------------------------------------------ polylines
def poly_query(pts, X, Z, closed=False):
    """Distance from (X, Z) to a polyline; arc-length t of the closest point; signed side (+ = left of travel)."""
    P = np.asarray(pts, float)
    if closed: P = np.vstack([P, P[:1]])
    A, B = P[:-1], P[1:]; AB = B - A; L2 = np.maximum((AB ** 2).sum(1), 1e-9); seg = np.sqrt(L2); cum = np.r_[0, np.cumsum(seg)]
    X = np.asarray(X, float); Z = np.asarray(Z, float); shp = X.shape; x, z = X.ravel(), Z.ravel()
    best = np.full(len(x), np.inf); tb = np.zeros(len(x)); sb = np.zeros(len(x))
    for k in range(len(A)):  # loop over segments (few), vectorised over points (many)
        u = np.clip(((x - A[k, 0]) * AB[k, 0] + (z - A[k, 1]) * AB[k, 1]) / L2[k], 0, 1)
        px, pz = A[k, 0] + u * AB[k, 0], A[k, 1] + u * AB[k, 1]; d = np.hypot(x - px, z - pz)
        m = d < best; best[m] = d[m]; tb[m] = cum[k] + u[m] * seg[k]
        sb[m] = np.sign(AB[k, 0] * (z[m] - A[k, 1]) - AB[k, 1] * (x[m] - A[k, 0]))
    return best.reshape(shp), tb.reshape(shp), sb.reshape(shp), float(cum[-1])


def resample(pts, step):
    P = np.asarray(pts, float); seg = np.linalg.norm(np.diff(P, axis=0), axis=1); cum = np.r_[0, np.cumsum(seg)]
    t = np.linspace(0, cum[-1], max(2, int(math.ceil(cum[-1] / step)) + 1))
    return np.c_[np.interp(t, cum, P[:, 0]), np.interp(t, cum, P[:, 1])], t


def inside_poly(pts, X, Z):
    P = np.asarray(pts, float); x, z = np.asarray(X, float), np.asarray(Z, float); ins = np.zeros(x.shape, bool); j = len(P) - 1
    for i in range(len(P)):
        xi, zi, xj, zj = P[i, 0], P[i, 1], P[j, 0], P[j, 1]
        c = ((zi > z) != (zj > z)) & (x < (xj - xi) * (z - zi) / ((zj - zi) if zj != zi else 1e-12) + xi); ins ^= c; j = i
    return ins


# ------------------------------------------------------------------ layer presets (biomes)
def _m(kind, color, tile=4.0, res=256, **kw):
    return dict(type=kind, color=color, tile_m=tile, res=res, **kw)


BIOMES = {
    "temperate": dict(materials=dict(rock=_m("rock", [0.42, 0.4, 0.37], 8.0), grass=_m("grass", [0.3, 0.42, 0.2], 4.0), dirt=_m("dirt", [0.42, 0.34, 0.25], 4.0),
                                     gravel=_m("gravel", [0.5, 0.48, 0.45], 3.0), sand=_m("sand", [0.7, 0.63, 0.47], 4.0), mud=_m("mud", [0.3, 0.25, 0.19], 4.0),
                                     road=_m("asphalt", [0.22, 0.22, 0.23], 6.0), snow=_m("snow", [0.9, 0.92, 0.95], 6.0)),
                      layers=["road", "path:gravel", "riverbed:mud", "cliff", "snow@70", "scree", "shore", "dirt_patch", "grass"]),
    "rocky": dict(materials=dict(rock=_m("rock", [0.46, 0.42, 0.38], 8.0), grass=_m("grass", [0.34, 0.4, 0.22], 4.0), dirt=_m("dirt", [0.45, 0.37, 0.28], 4.0),
                                 gravel=_m("gravel", [0.52, 0.49, 0.45], 3.0), sand=_m("sand", [0.66, 0.58, 0.44], 4.0), mud=_m("mud", [0.32, 0.27, 0.21], 4.0),
                                 road=_m("gravel", [0.48, 0.44, 0.39], 3.0), snow=_m("snow", [0.9, 0.92, 0.95], 6.0)),
                  layers=["road", "path:gravel", "riverbed:gravel", "cliff@34", "snow@80", "scree@24", "shore", "dirt_patch@0.55", "grass"]),
    "desert": dict(materials=dict(rock=_m("rock", [0.62, 0.42, 0.28], 8.0), sand=_m("sand", [0.82, 0.66, 0.44], 5.0), gravel=_m("gravel", [0.62, 0.52, 0.4], 3.0),
                                  dirt=_m("dirt", [0.6, 0.45, 0.3], 4.0), mud=_m("mud", [0.42, 0.33, 0.22], 4.0), road=_m("asphalt", [0.3, 0.28, 0.26], 6.0),
                                  grass=_m("grass", [0.5, 0.48, 0.28], 4.0)),
                   layers=["road", "path:gravel", "riverbed:mud", "cliff@32", "scree@22", "dirt_patch@0.7", "sand"]),
    "alpine": dict(materials=dict(rock=_m("rock", [0.45, 0.45, 0.47], 8.0), snow=_m("snow", [0.92, 0.94, 0.97], 6.0), grass=_m("grass", [0.28, 0.38, 0.22], 4.0),
                                  gravel=_m("gravel", [0.55, 0.55, 0.55], 3.0), dirt=_m("dirt", [0.38, 0.32, 0.26], 4.0), mud=_m("mud", [0.3, 0.27, 0.22], 4.0),
                                  sand=_m("sand", [0.6, 0.58, 0.52], 4.0), road=_m("gravel", [0.45, 0.43, 0.4], 3.0)),
                   layers=["road", "path:gravel", "riverbed:gravel", "cliff@36", "snow@25", "scree@26", "shore", "grass"]),
    "urban": dict(materials=dict(road=_m("asphalt", [0.2, 0.2, 0.21], 8.0, lines=True), concrete=_m("concrete", [0.46, 0.46, 0.45], 4.0),
                                 rock=_m("concrete", [0.36, 0.36, 0.35], 4.0), grass=_m("grass", [0.28, 0.36, 0.2], 4.0), dirt=_m("dirt", [0.35, 0.3, 0.25], 4.0),
                                 gravel=_m("gravel", [0.42, 0.41, 0.4], 3.0), mud=_m("mud", [0.25, 0.22, 0.2], 4.0), sand=_m("sand", [0.55, 0.5, 0.42], 4.0)),
                  layers=["road", "path:concrete", "pad:concrete", "riverbed:mud", "cliff", "plaza:concrete", "park:grass", "grass_patch@0.82", "concrete"]),
    "industrial": dict(materials=dict(concrete=_m("concrete", [0.38, 0.38, 0.36], 4.0), road=_m("asphalt", [0.2, 0.2, 0.2], 8.0),
                                      rock=_m("rock", [0.33, 0.31, 0.29], 8.0), dirt=_m("dirt", [0.34, 0.3, 0.25], 4.0), mud=_m("mud", [0.24, 0.22, 0.18], 4.0),
                                      gravel=_m("gravel", [0.4, 0.39, 0.37], 3.0), grass=_m("grass", [0.3, 0.33, 0.2], 4.0), sand=_m("sand", [0.5, 0.46, 0.38], 4.0)),
                       layers=["road", "path:gravel", "pad:concrete", "riverbed:mud", "cliff", "plaza:concrete", "scree", "mud_patch@0.7", "dirt_patch@0.45", "grass"]),
    "alien": dict(materials=dict(rock=_m("rock", [0.33, 0.28, 0.4], 8.0), moss=_m("moss", [0.36, 0.22, 0.48], 4.0), sand=_m("sand", [0.5, 0.45, 0.6], 4.0),
                                 gravel=_m("gravel", [0.4, 0.36, 0.45], 3.0), mud=_m("mud", [0.2, 0.25, 0.3], 4.0), road=_m("scifi_floor", [0.35, 0.36, 0.38], 4.0),
                                 dirt=_m("dirt", [0.3, 0.26, 0.34], 4.0), crystal=_m("glow", [0.3, 0.9, 1.0], 2.0, emissive=[0.2, 0.7, 0.9])),
                  layers=["road", "path:gravel", "riverbed:mud", "cliff@34", "scree", "shore", "dirt_patch@0.7", "moss"]),
    "wasteland": dict(materials=dict(dirt=_m("dirt", [0.4, 0.34, 0.27], 4.0), mud=_m("mud", [0.28, 0.24, 0.19], 4.0), rock=_m("rock", [0.37, 0.34, 0.3], 8.0),
                                     gravel=_m("gravel", [0.45, 0.42, 0.38], 3.0), sand=_m("sand", [0.58, 0.5, 0.38], 4.0), road=_m("asphalt", [0.23, 0.22, 0.21], 8.0, wear=0.9),
                                     grass=_m("grass", [0.42, 0.4, 0.24], 4.0), concrete=_m("concrete", [0.4, 0.39, 0.37], 4.0, wear=0.8)),
                      layers=["road", "path:gravel", "pad:concrete", "riverbed:mud", "cliff", "scree", "grass_patch@0.68", "mud_patch@0.6", "dirt"]),
    "fantasy": dict(materials=dict(grass=_m("grass", [0.32, 0.5, 0.22], 4.0), moss=_m("moss", [0.25, 0.42, 0.2], 4.0), rock=_m("rock", [0.45, 0.43, 0.48], 8.0),
                                   dirt=_m("dirt", [0.44, 0.33, 0.24], 4.0), gravel=_m("gravel", [0.55, 0.52, 0.48], 3.0), sand=_m("sand", [0.75, 0.68, 0.5], 4.0),
                                   mud=_m("mud", [0.3, 0.26, 0.2], 4.0), road=_m("cobblestone", [0.55, 0.53, 0.5], 2.0), snow=_m("snow", [0.92, 0.94, 0.98], 6.0)),
                    layers=["road", "path:dirt", "riverbed:gravel", "cliff", "snow@80", "shore", "moss_patch@0.6", "grass"]),
    "cartoon": dict(materials=dict(grass=_m("grass", [0.38, 0.62, 0.22], 6.0, res=128), rock=_m("rock", [0.55, 0.5, 0.45], 8.0, res=128),
                                   sand=_m("sand", [0.9, 0.8, 0.55], 6.0, res=128), dirt=_m("dirt", [0.6, 0.42, 0.26], 5.0, res=128),
                                   gravel=_m("gravel", [0.62, 0.58, 0.52], 4.0, res=128), mud=_m("mud", [0.42, 0.3, 0.2], 4.0, res=128),
                                   road=_m("dirt", [0.68, 0.52, 0.34], 4.0, res=128), snow=_m("snow", [0.95, 0.97, 1.0], 6.0, res=128)),
                    layers=["road", "path:dirt", "riverbed:sand", "cliff@40", "snow@70", "shore", "grass"]),
}


def _parse_layer(tok, mats):
    """Compact preset token -> rule. 'name[:material][@value]'."""
    val = None
    if "@" in tok: tok, val = tok.split("@"); val = float(val)
    name, mat = (tok.split(":") + [None])[:2]
    if name == "road": return dict(id="road", material=mat or "road", mask="road")
    if name in ("path", "riverbed", "pad", "plaza", "park"):
        return dict(id=name, material=mat or {"path": "gravel", "riverbed": "mud", "pad": "concrete", "plaza": "concrete", "park": "grass"}[name],
                    mask={"riverbed": "river"}.get(name, name))
    if name == "cliff": return dict(id="cliff", material="rock", slope=[val or 38, 90])
    if name == "scree": return dict(id="scree", material="gravel", slope=[val or 28, (val or 28) + 10])
    if name == "snow": return dict(id="snow", material="snow", height=[val or 70, 1e9], slope=[0, 40])
    if name == "shore": return dict(id="shore", material="sand", above_water=[-50, 1.2])
    if name.endswith("_patch"):
        m = name[:-6]; return dict(id=name, material=m, patch=val or 0.72)
    return dict(id=name, material=mat or name)  # default (no condition)


def layers_of(T):
    """Resolved layer rules + material definitions (level material names 'ter_<material>')."""
    b = BIOMES[T.get("biome", "temperate")]; mats = dict(b["materials"]); mats.update(T.get("materials", {}))
    rules = T.get("layers") or [_parse_layer(t, mats) for t in b["layers"]]
    return rules, mats


# ------------------------------------------------------------------ the terrain function
ADD, CARVE, FLAT = 0, 1, 2
STAGE = dict(hill=ADD, mountain=ADD, ridge=ADD, barrier=1.5, crater=ADD, dunes=ADD, cliff=ADD, heightmap=ADD, plateau=ADD, mesa=ADD, field=ADD,
             valley=CARVE, canyon=CARVE, river=CARVE, lake=CARVE, coast=CARVE, trench=CARVE, pad=FLAT, road=FLAT, path=FLAT, street=FLAT, mask=FLAT)
FEATURE_TYPES = sorted(STAGE)


class Terrain:
    def __init__(self, T, level_dir=None):
        self.T = T; self.dir = level_dir; self.seed = int(T.get("seed", 1)); self.cell = float(T.get("cell", 2.0)); self.C = int(T.get("chunk", 32))
        x0, z0, x1, z1 = T["extent"]; n = self.C * self.cell
        self.ncx, self.ncz = max(1, int(math.ceil((x1 - x0) / n - 1e-6))), max(1, int(math.ceil((z1 - z0) / n - 1e-6)))
        self.x0, self.z0 = float(x0), float(z0); self.x1, self.z1 = self.x0 + self.ncx * n, self.z0 + self.ncz * n
        self.base_y = float(T.get("base_y", 0.0)); N = T.get("noise", {})
        self.amp, self.scale, self.oct = N.get("amplitude", 2.5), N.get("scale", 70.0), int(N.get("octaves", 5))
        self.ridged_w, self.warp = N.get("ridged", 0.25), N.get("warp", 0.6)
        self.n0, self.n1, self.n2, self.n3 = (Perlin(_sid(self.seed, "base", k)) for k in range(4))
        feats = list(T.get("features", []))
        order = {"pad": 0, "mask": 0}  # flatten stage: building / arena pads first, roads drawn over them (no steps at pad edges)
        self.features = sorted(feats, key=lambda f: (STAGE.get(f["type"], ADD), order.get(f["type"], 1) if STAGE.get(f["type"]) == FLAT else 0))  # stable within a stage
        self._noise, self._prof, self._img = {}, {}, {}
        self.water_level = T.get("water", {}).get("level")
        self.rules, self.mats = layers_of(T)
        for i, f in enumerate(self.features): self._prepare(i, f)

    # ---- helpers
    def fnoise(self, f):
        k = f["id"]
        if k not in self._noise: self._noise[k] = Perlin(_sid(self.seed, k, f.get("seed", 0)))
        return self._noise[k]

    def _radial(self, f, X, Z, irregular=0.3):
        cx, cz = f["center"]; r = float(f["radius"]); sx, sz = f.get("stretch", [1, 1]); a = math.radians(f.get("yaw", 0))
        dx, dz = X - cx, Z - cz; lx, lz = dx * math.cos(a) + dz * math.sin(a), -dx * math.sin(a) + dz * math.cos(a)
        d = np.hypot(lx / sx, lz / sz) / r
        if irregular: d = d * (1 + irregular * f.get("irregular", 1.0) * self.fnoise(f).fbm(X / (r * 0.8), Z / (r * 0.8), 3))
        return d

    def bbox(self, f):
        """Influence box [x0, z0, x1, z1] of a feature (None = global)."""
        t = f["type"]
        if t in ("heightmap", "mask"): return list(f["area"])
        if t == "coast": return None
        if "center" in f:
            r = f.get("radius") or max(f.get("size", [10, 10])) / 2; s = max(f.get("stretch", [1, 1])); m = r * s * 1.45 + f.get("margin", 4)
            return [f["center"][0] - m, f["center"][1] - m, f["center"][0] + m, f["center"][1] + m]
        if "points" in f:
            P = np.asarray(f["points"], float); w = f.get("width", 10) / 2 + f.get("shoulder", 3) + f.get("offset", 0) + f.get("reach", 0) + 8
            if t == "barrier": return None  # the outside of a playable boundary: unbounded
            return [P[:, 0].min() - w, P[:, 1].min() - w, P[:, 0].max() + w, P[:, 1].max() + w]
        return None

    def _image(self, path):
        if path not in self._img:
            from PIL import Image
            im = Image.open(os.path.join(self.dir or ".", path)).convert("L"); self._img[path] = np.asarray(im, float) / 255.0
        return self._img[path]

    def _sample_img(self, f, X, Z):
        a = self._image(f["image"]); x0, z0, x1, z1 = f["area"]; H_, W_ = a.shape
        u = (X - x0) / (x1 - x0) * (W_ - 1); v = (Z - z0) / (z1 - z0) * (H_ - 1); ins = (u >= 0) & (u <= W_ - 1) & (v >= 0) & (v <= H_ - 1)
        u, v = np.clip(u, 0, W_ - 1.001), np.clip(v, 0, H_ - 1.001); i, j = v.astype(int), u.astype(int); fu, fv = u - j, v - i
        val = (a[i, j] * (1 - fu) + a[i, j + 1] * fu) * (1 - fv) + (a[i + 1, j] * (1 - fu) + a[i + 1, j + 1] * fu) * fv
        fe = f.get("feather", 0)
        w = np.ones_like(val) if not fe else smooth(0, fe, np.minimum.reduce([X - x0, x1 - X, Z - z0, z1 - Z]))
        return np.where(ins, val, 0.0), np.where(ins, w, 0.0)

    def _prepare(self, i, f):
        """Profiles that depend on the terrain before this feature (rivers, roads, lakes, fields) - computed once."""
        t = f["type"]
        if t in ("river", "road", "path", "street"):
            P, s = resample(f["points"], 2.0); h = self._eval(P[:, 0], P[:, 1], i)[0]
            if t != "river":  # across a river channel the road keeps the bank height (the bridge spans it): interpolate over the gap
                rv = self._river_mask(P[:, 0], P[:, 1]) > 0
                if rv.any() and (~rv).sum() >= 2: h = np.where(rv, np.interp(s, s[~rv], h[~rv]), h)
            win = max(1, int(f.get("smooth", 30 if t != "river" else 16) / 2.0))
            k = np.ones(2 * win + 1) / (2 * win + 1); hp = np.convolve(np.pad(h, win, mode="edge"), k, mode="valid")
            if t == "river":
                D = np.gradient(P, axis=0); D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9); Nr = np.c_[-D[:, 1], D[:, 0]]
                hw = f.get("width", 8) * 0.35 + f.get("depth", 1.2) / f.get("bank_slope", 0.5) + 1.2
                banks = np.minimum(self._eval(*(P + Nr * hw).T, i)[0], self._eval(*(P - Nr * hw).T, i)[0])
                water = np.minimum(hp - f.get("bank", 0.8), banks - 0.35)  # never above either bank (no perched water)
                if f.get("flow", True): water = np.minimum.accumulate(water)  # downstream = end of the list: never flows uphill
                prof = dict(s=s, water=water, bed=water - f.get("depth", 1.2))
            else:
                g = f.get("max_grade", 0.1 if t != "path" else 0.22) * 2.0
                for _ in range(3):  # grade limit forwards + backwards
                    for k_ in range(1, len(hp)): hp[k_] = np.clip(hp[k_], hp[k_ - 1] - g, hp[k_ - 1] + g)
                    for k_ in range(len(hp) - 2, -1, -1): hp[k_] = np.clip(hp[k_], hp[k_ + 1] - g, hp[k_ + 1] + g)
                prof = dict(s=s, y=hp)
            self._prof[f["id"]] = prof
        elif t == "lake":
            a = np.linspace(0, 2 * np.pi, 48, endpoint=False); r = f["radius"] * 1.15
            h = self._eval(f["center"][0] + r * np.cos(a), f["center"][1] + r * np.sin(a), i)[0]
            self._prof[f["id"]] = dict(level=f.get("level", float(h.min()) - 0.4))
        elif t in ("field", "pad") and "y" not in f:
            a = np.linspace(0, 2 * np.pi, 16, endpoint=False); r = (f.get("radius") or max(f.get("size", [8, 8])) / 2) * 0.6
            h = self._eval(np.r_[f["center"][0], f["center"][0] + r * np.cos(a)], np.r_[f["center"][1], f["center"][1] + r * np.sin(a)], i)[0]
            self._prof[f["id"]] = dict(y=float(np.median(h)))

    def base(self, X, Z):
        x, z = X / self.scale, Z / self.scale
        if self.warp: x, z = x + self.warp * self.n1.fbm(x * 0.5 + 3.1, z * 0.5 + 7.7, 3), z + self.warp * self.n2.fbm(x * 0.5 - 5.3, z * 0.5 + 1.9, 3)
        h = (1 - self.ridged_w) * self.n0.fbm(x, z, self.oct) + self.ridged_w * (self.n3.ridged(x * 0.7, z * 0.7, 4) * 2 - 1)
        return self.base_y + self.amp * h

    def _eval(self, X, Z, upto=None):
        """Height (+ masks) at world points, applying features[:upto]."""
        X = np.asarray(X, float); Z = np.asarray(Z, float); H = self.base(X, Z); M = {}
        rough = np.ones_like(H)
        for i, f in enumerate(self.features):
            if upto is not None and i >= upto: break
            bb = self.bbox(f)
            if bb is not None:
                sel = (X >= bb[0]) & (X <= bb[2]) & (Z >= bb[1]) & (Z <= bb[3])
                if not sel.any(): continue
                if sel.all(): sel = slice(None)
            else: sel = slice(None)
            Hs = H[sel]; ms = {}
            Hn = self._apply(i, f, X[sel], Z[sel], Hs, ms)
            H[sel] = Hn
            for k, v in ms.items():
                if k not in M: M[k] = np.zeros_like(H)
                M[k][sel] = np.maximum(M[k][sel], v)
        return H, M

    def _apply(self, i, f, X, Z, H, ms):
        t = f["type"]; nz = self.fnoise(f)
        if t in ("hill", "mountain"):
            d = self._radial(f, X, Z, 0.35); r = f["radius"]
            if t == "hill":
                return H + f["height"] * bell(d) ** f.get("shape", 1.0) * (0.85 + 0.3 * nz.fbm(X / (r * 0.4) + 11, Z / (r * 0.4), 3))
            return H + f["height"] * bell(d) ** 1.15 * (0.5 + 0.65 * nz.ridged(X / (r * 0.45), Z / (r * 0.45), 4))
        if t in ("ridge", "barrier"):
            if t == "ridge":
                d, s, _, Lp = poly_query(f["points"], X, Z); w = f.get("width", 30) / 2
                prof = bell(d / w * (1 + 0.25 * nz.fbm(X / 25, Z / 25, 2)))
            else:  # natural barrier just OUTSIDE the playable polygon: rises from the boundary, stays high beyond
                P = f["points"]; d, s, _, Lp = poly_query(P, X, Z, closed=True); out = ~inside_poly(P, X, Z)
                o = f.get("offset", 14.0); wd = f.get("width", 40.0); dd = np.where(out, d, 0.0) * (1 + 0.3 * nz.fbm(X / 30, Z / 30, 2))
                prof = np.where(dd < o, smooth(0, o, dd), 1 - f.get("falloff", 0.35) * smooth(o, o + wd, dd))
                prof = np.where(out, prof, 0.0)
                for g_ in self.features:  # applied after carving: valleys don't breach it, but rivers / roads pass through a gap
                    if g_["type"] in ("river", "road", "street"):
                        dl, _, _, _ = poly_query(g_["points"], X, Z); gw = g_.get("width", 8) / 2 + 4
                        prof = prof * smooth(gw, gw + 18, dl)
            if t == "barrier":  # dependable minimum height: a boundary must stay a barrier everywhere
                return H + f["height"] * prof ** 1.2 * (0.78 + 0.3 * nz.fbm(s / 45.0, 0.37, 2)) * (0.75 + 0.45 * nz.ridged(X / 28, Z / 28, 4))
            along = 0.65 + 0.5 * nz.fbm(s / 45.0, 0.37, 2)
            return H + f["height"] * prof ** 1.2 * along * (0.55 + 0.6 * nz.ridged(X / 28, Z / 28, 4))
        if t == "crater":
            d = self._radial(f, X, Z, 0.15)
            bowl = np.where(d < 1, -f.get("depth", 4) * (1 - d ** 2), 0); rim = f.get("rim", 2.0) * np.exp(-((d - 1) / 0.22) ** 2)
            return H + bowl + rim
        if t in ("plateau", "mesa"):
            d = self._radial(f, X, Z, 0.25); r = f["radius"]; e = min(0.95, f.get("edge", 4.0 if t == "plateau" else 1.5) / r)
            w = smooth(1.0, 1.0 - e, d); top = f.get("y", self.base_y + f.get("height", 8)) + 0.4 * nz.fbm(X / 12, Z / 12, 2)
            if t == "mesa":  # stepped strata on the walls, never lowers higher ground
                k = f.get("steps", 3); w = np.where(w < 0.999, np.floor(w * k + 0.5 * smooth(0.3, 0.7, (w * k) % 1)) / k, 1.0)
                return H + (np.maximum(H, top) - H) * w
            return H + (top - H) * w
        if t == "field":
            d = self._radial(f, X, Z, 0.3); w = smooth(1.0, 0.55, d) * f.get("strength", 0.75); y = f.get("y", self._prof.get(f["id"], {}).get("y", self.base_y))
            if f.get("surface"): ms[f["surface"]] = (d < 1.0).astype(float)  # e.g. "park" -> grass layer in a paved city
            return H + (y + 0.35 * nz.fbm(X / 20, Z / 20, 2) - H) * w
        if t == "dunes":
            d = self._radial(f, X, Z, 0.3); a = math.radians(f.get("direction", 30)); wl = f.get("wavelength", 18)
            ph = (X * math.cos(a) + Z * math.sin(a)) / wl * 2 * np.pi + 2.2 * nz.fbm(X / 40, Z / 40, 3)
            return H + f.get("height", 3) * bell(d * 0.9) * (0.5 + 0.5 * np.sin(ph)) ** 1.6 * (0.7 + 0.3 * nz.fbm(X / 25, Z / 25, 2))
        if t == "cliff":
            d, s, side, Lp = poly_query(f["points"], X, Z); sg = side * (1 if f.get("side", "left") == "left" else -1)
            sd = sg * d; tw = f.get("transition", 1.5); reach = f.get("reach", 30.0)
            w = smooth(-tw / 2, tw / 2, sd) * (1 - smooth(reach, reach + 25, sd)); tl = f.get("taper", 10.0)
            P = np.asarray(f["points"], float); ends = np.minimum(np.hypot(X - P[0, 0], Z - P[0, 1]), np.hypot(X - P[-1, 0], Z - P[-1, 1]))
            on_seg = (s > 0.01) & (s < Lp - 0.01)
            taper = np.where(on_seg, smooth(0, tl, s) * smooth(Lp, Lp - tl, s), 1 - smooth(0, tl, ends))
            ms["cliff"] = (np.abs(sd) < tw) * taper
            return H + f["height"] * w * taper * (0.85 + 0.25 * nz.fbm(X / 15, Z / 15, 3))
        if t == "heightmap":
            v, w = self._sample_img(f, X, Z); lo, hi = f.get("height", [0, 10]); y = lo + (hi - lo) * v
            mode = f.get("mode", "add")
            if mode == "replace": return H + (y - H) * w
            if mode == "max": return H + (np.maximum(H, y) - H) * w
            return H + y * w
        if t == "mask":
            v, w = self._sample_img(f, X, Z); ms[f.get("name", f["id"])] = v * w; return H
        if t == "valley":
            d, s, _, _ = poly_query(f["points"], X, Z); w = bell(d / (f.get("width", 40) / 2) * (1 + 0.2 * nz.fbm(X / 30, Z / 30, 2)))
            return H - f.get("depth", 6) * w
        if t == "canyon":
            d, s, _, _ = poly_query(f["points"], X, Z); hw = f.get("width", 24) / 2 * (1 + 0.15 * nz.fbm(X / 20, Z / 20, 3))
            w = smooth(1.0, f.get("floor", 0.55), d / hw); ms["canyon"] = w
            return H - f.get("depth", 10) * w * (0.92 + 0.12 * nz.fbm(X / 14, Z / 14, 2))
        if t == "river":
            p = self._prof[f["id"]]; d, s, _, _ = poly_query(f["points"], X, Z); wb = f.get("width", 8) * 0.35
            bed = np.interp(s, p["s"], p["bed"]); water = np.interp(s, p["s"], p["water"]); k = f.get("bank_slope", 0.5)
            target = bed + k * np.maximum(0, d - wb) + 0.15 * nz.fbm(X / 6, Z / 6, 2)
            hw = wb + (water - bed) / k; ms["river"] = (d < hw).astype(float); ms["bank"] = (d < hw + 2.5).astype(float)
            return np.minimum(H, target)
        if t == "trench":  # flat-floored cut at absolute height y (tunnels, sunken roads); only ever lowers the ground
            d, s, _, Lp = poly_query(f["points"], X, Z); hw = f.get("width", 8) / 2; tr = f.get("transition", 6.0)
            w = smooth(hw + tr, hw, d); ms["trench"] = (d <= hw).astype(float)
            return H + (np.minimum(H, f["y"]) - H) * w
        if t == "lake":
            lv = self._prof[f["id"]]["level"]; d = self._radial(f, X, Z, 0.25); r = f["radius"]
            target = np.where(d < 1, lv - f.get("depth", 2.5) * (1 - d ** 2), lv + (d - 1) * r * f.get("bank_slope", 0.35))
            ms["river"] = (d < 1.02).astype(float); ms["bank"] = (d < 1.15).astype(float)
            return np.minimum(H, target)
        if t == "coast":
            d, s, side, _ = poly_query(f["points"], X, Z); sd = d * side * (1 if f.get("side", "left") == "left" else -1)
            lv = self.water_level if self.water_level is not None else self.base_y - 1; target = lv - f.get("depth", 4)
            w = smooth(0, f.get("width", 30), sd + 6 * nz.fbm(X / 40, Z / 40, 2)); return H + (np.minimum(H, target) - H) * w
        if t == "pad":
            y = f.get("y", self._prof.get(f["id"], {}).get("y", self.base_y)); m = f.get("margin", 3.0)
            if "size" in f:
                cx, cz = f["center"]; a = math.radians(f.get("yaw", 0)); dx, dz = X - cx, Z - cz
                lx, lz = np.abs(dx * math.cos(a) - dz * math.sin(a)), np.abs(dx * math.sin(a) + dz * math.cos(a))
                ex = np.maximum(lx - f["size"][0] / 2, 0); ez = np.maximum(lz - f["size"][1] / 2, 0); dist = np.hypot(ex, ez)
            else: dist = np.maximum(np.hypot(X - f["center"][0], Z - f["center"][1]) - f["radius"], 0)
            w = smooth(m, 0, dist); ms[f.get("surface", "pad")] = (dist <= 0.01).astype(float)
            if f.get("mode") == "lower": return H + (np.minimum(H, y) - H) * w  # repairs: only ever digs the ground out
            return H + (y - H) * w
        if t in ("road", "path", "street"):
            p = self._prof[f["id"]]; d, s, _, _ = poly_query(f["points"], X, Z); hw = f.get("width", 6 if t != "path" else 3) / 2
            if t == "path": hw = hw * (1 + 0.18 * nz.fbm(X / 6, Z / 6, 2))
            fw = np.maximum(hw, f.get("flat_width", 0) / 2); sh = f.get("shoulder", 3.0 if t != "path" else 1.5); w = smooth(fw + sh, fw, d)  # flat under kerbs too
            y = np.interp(s, p["s"], p["y"]); ms["road" if t != "path" else "path"] = (d <= hw).astype(float)
            if t == "street": ms["road"] = (d <= hw).astype(float)
            out = H + (y - H) * w
            rv = self._river_mask(X, Z)  # a road never fills a river: the crossing needs a bridge (the generator adds one)
            return np.where(rv > 0, H, out)
        return H

    def _river_mask(self, X, Z):
        m = np.zeros(np.shape(X))
        for f in self.features:
            if f["type"] != "river": continue
            p = self._prof[f["id"]]; d, s, _, _ = poly_query(f["points"], X, Z); wb = f.get("width", 8) * 0.35
            water = np.interp(s, p["s"], p["water"]); bed = np.interp(s, p["s"], p["bed"]); hw = wb + (water - bed) / f.get("bank_slope", 0.5)
            m = np.maximum(m, (d < hw + 1.0).astype(float))
        return m

    def height(self, X, Z):
        return self._eval(X, Z)[0]

    def height_at(self, x, z):
        return float(self.height(np.array([x]), np.array([z]))[0])

    def water_y(self, X, Z):
        """Water surface height at points (-inf where no water)."""
        X = np.asarray(X, float); Z = np.asarray(Z, float); W = np.full(X.shape, -np.inf)
        if self.water_level is not None: W[:] = self.water_level
        for f in self.features:
            if f["type"] == "river":
                p = self._prof[f["id"]]; d, s, _, _ = poly_query(f["points"], X, Z); wb = f.get("width", 8) * 0.35
                water = np.interp(s, p["s"], p["water"]); bed = np.interp(s, p["s"], p["bed"]); hw = wb + (water - bed) / f.get("bank_slope", 0.5)
                W = np.where(d < hw + 0.6, np.maximum(W, water), W)
            elif f["type"] == "lake":
                d = self._radial(f, X, Z, 0.25); W = np.where(d < 1.15, np.maximum(W, self._prof[f["id"]]["level"]), W)
        return W

    # ------------------------------------------------------------ global grid
    def grid(self):
        if hasattr(self, "_grid"): return self._grid
        c = self.cell; nx, nz = self.ncx * self.C + 1, self.ncz * self.C + 1
        xs = self.x0 + (np.arange(-1, nx + 1)) * c; zs = self.z0 + (np.arange(-1, nz + 1)) * c
        X, Z = np.meshgrid(xs, zs); Hp, Mp = self._eval(X, Z)
        gx = (Hp[1:-1, 2:] - Hp[1:-1, :-2]) / (2 * c); gz = (Hp[2:, 1:-1] - Hp[:-2, 1:-1]) / (2 * c)
        N = np.stack([-gx, np.ones_like(gx), -gz], -1); N /= np.linalg.norm(N, axis=-1, keepdims=True)
        H = Hp[1:-1, 1:-1]; M = {k: v[1:-1, 1:-1] for k, v in Mp.items()}
        W = self.water_y(X[1:-1, 1:-1], Z[1:-1, 1:-1]); M["wet"] = (H < W + 0.05).astype(float)
        self._grid = dict(X=X[1:-1, 1:-1], Z=Z[1:-1, 1:-1], H=H, N=N, M=M, W=W)
        return self._grid

    # ------------------------------------------------------------ materials per triangle
    def classify(self, P, nrm, masks, water, zone="near"):
        """P (n,3) triangle centres, nrm (n,3) unit normals, masks name->(n,), water (n,) -> layer index per triangle.
        zone "middle": patch rules are skipped (big coarse triangles would show as blotches)."""
        slope = np.degrees(np.arccos(np.clip(nrm[:, 1], -1, 1))); nz = Perlin(_sid(self.seed, "layers"))
        nb = nz.fbm(P[:, 0] / 9.0, P[:, 2] / 9.0, 3); patch = nz.fbm(P[:, 0] / 22.0 + 50, P[:, 2] / 22.0, 4) * 0.5 + 0.5
        out = np.full(len(P), len(self.rules) - 1); done = np.zeros(len(P), bool)
        for k, r in enumerate(self.rules):
            ok = ~done
            if "mask" in r: ok &= masks.get(r["mask"], np.zeros(len(P))) >= r.get("mask_min", 0.5)
            if "slope" in r: j = r.get("jitter", 4.0) * nb; ok &= (slope + j >= r["slope"][0]) & (slope + j < r["slope"][1])
            if "height" in r: j = r.get("hjitter", 4.0) * nb; ok &= (P[:, 1] + j >= r["height"][0]) & (P[:, 1] + j < r["height"][1])
            if "above_water" in r:
                aw = P[:, 1] - water; ok &= np.isfinite(aw) & (aw + 0.4 * nb >= r["above_water"][0]) & (aw + 0.4 * nb < r["above_water"][1])
            if "patch" in r: ok &= (patch > r["patch"]) & (zone == "near")
            if zone == "middle" and r["id"] in ("scree", "path", "pad", "plaza"): ok &= False  # coarse triangles: broad layers only
            out[ok] = k; done |= ok
        return out

    def layer_material(self, k):
        return "ter_" + self.rules[k]["material"]

    def materials(self):
        """Level material entries for every layer material used by the rules."""
        return {"ter_" + r["material"]: dict(self.mats[r["material"]]) for r in self.rules if r["material"] in self.mats}

    # ------------------------------------------------------------ chunk meshes
    def chunk_ids(self):
        return [(i, j) for i in range(self.ncz) for j in range(self.ncx)]

    def chunk_bounds(self, i, j):
        n = self.C * self.cell; return [self.x0 + j * n, self.z0 + i * n, self.x0 + (j + 1) * n, self.z0 + (i + 1) * n]

    def chunk_hash(self, i, j):
        """Depends only on global settings + features whose influence box touches the chunk (edit locality)."""
        b = self.chunk_bounds(i, j); pad = 2 * self.cell
        glob = {k: self.T.get(k) for k in ("seed", "cell", "chunk", "base_y", "noise", "biome", "layers", "materials", "water")}
        fs = []
        for f in self.features:
            bb = self.bbox(f)
            if bb is None or not (bb[2] < b[0] - pad or bb[0] > b[2] + pad or bb[3] < b[1] - pad or bb[1] > b[3] + pad): fs.append(f)
        return hashlib.sha1(json.dumps([glob, fs], sort_keys=True).encode()).hexdigest()[:12]

    def layer_colors(self, L=None):
        from materials import avg_linear_color
        mats = (L or {}).get("materials", {})
        return np.array([avg_linear_color(mats.get("ter_" + r["material"]) or self.mats[r["material"]]) for r in self.rules])

    def vertex_colors(self, V, N, L=None):
        """Per-vertex linear colour of the broad layer at each vertex (smooth colour blends between layers)."""
        _, M = self._eval(V[:, 0], V[:, 2]); W = self.water_y(V[:, 0], V[:, 2]); lay = self.classify(V, N, M, W, zone="middle")
        c = self.layer_colors(L)[lay]; return np.c_[np.clip(c, 0, 1) * 255, np.full(len(c), 255)].astype(np.uint8)

    def chunk_mesh(self, i, j, lod=0, broad=False, far=False, L=None):
        """{material: trimesh} for chunk (i, j). LOD k samples every 2^k vertices inside; borders stay full-res.
        broad=True: distant LODs use the broad layer set (no patches / scree / paths) -> fewer materials, fewer draw calls."""
        G = self.grid(); C, s = self.C, 2 ** lod
        r0, c0 = i * C, j * C
        def vid(r, c): return (r - r0) * (C + 1) + (c - c0)
        RR, CC = np.mgrid[r0:r0 + C + 1, c0:c0 + C + 1]
        V = np.c_[G["X"][RR, CC].ravel(), G["H"][RR, CC].ravel(), G["Z"][RR, CC].ravel()]; Nn = G["N"][RR, CC].reshape(-1, 3)
        Mk = {k: v[RR, CC].ravel() for k, v in G["M"].items()}; Wv = G["W"][RR, CC].ravel()
        F = []
        def quads(rows, cols):
            for a_ in range(len(rows) - 1):
                for b_ in range(len(cols) - 1):
                    ra, rb, ca, cb = rows[a_], rows[a_ + 1], cols[b_], cols[b_ + 1]
                    a, b, c, d = vid(ra, ca), vid(ra, cb), vid(rb, cb), vid(rb, ca)
                    if abs(V[a, 1] - V[c, 1]) <= abs(V[b, 1] - V[d, 1]): F.extend([[a, d, c], [a, c, b]])
                    else: F.extend([[a, d, b], [b, d, c]])
        if s == 1 or C // s < 3:
            quads(list(range(r0, r0 + C + 1)), list(range(c0, c0 + C + 1)))
        else:
            inner = list(range(r0 + s, r0 + C - s + 1, s)); innc = list(range(c0 + s, c0 + C - s + 1, s)); quads(inner, innc)
            def loop(ra, rb, ca, cb, step):  # perimeter, clockwise from (ra, ca) when seen from above, with param 0..1
                pts = [(ra, c) for c in range(ca, cb, step)] + [(r, cb) for r in range(ra, rb, step)] + \
                      [(rb, c) for c in range(cb, ca, -step)] + [(r, ca) for r in range(rb, ra, -step)]
                per = 2 * ((cb - ca) + (rb - ra)); acc, prm = 0, []
                for k_ in range(len(pts)): prm.append(acc / per); acc += step
                return [vid(*p) for p in pts], prm
            A, pa = loop(r0, r0 + C, c0, c0 + C, 1); B, pb = loop(inner[0], inner[-1], innc[0], innc[-1], s)
            F.extend(stitch(A, pa, B, pb))
        F = np.array(F)
        tri = V[F]; fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
        flip = fn[:, 1] < 0; F[flip] = F[flip][:, ::-1]; fn[flip] *= -1
        cen = tri.mean(1); mk = {k: v[F].mean(1) for k, v in Mk.items()}; wat = Wv[F].max(1)
        if far:  # one vertex-coloured mesh (1 draw call) for distant LODs
            used, inv = np.unique(F.ravel(), return_inverse=True); v = V[used]; n = Nn[used]
            m = trimesh.Trimesh(v, inv.reshape(-1, 3), vertex_normals=n, process=False); m.metadata["vertex_colors"] = self.vertex_colors(v, n, L)
            return {"ter_far": m}
        lay = self.classify(cen, fn, mk, wat, zone="middle" if broad else "near")
        mat_of = np.array([self.layer_material(k) for k in range(len(self.rules))])[lay]  # several layers may share one material
        out = {}
        for mname in np.unique(mat_of):
            mat = mname[4:]; out[str(mname)] = _submesh(V, Nn, F[mat_of == mname], self.mats[mat].get("tile_m", 4.0), steep=mat == "rock")
        return out

    def map_image(self, L):
        return map_image(self, L)

    def collider(self, i, j):
        G = self.grid(); C = self.C; r0, c0 = i * C, j * C
        return dict(shape="heightmap", origin=[round(float(G["X"][r0, c0]), 3), 0.0, round(float(G["Z"][r0, c0]), 3)], cell=self.cell,
                    heights=np.round(G["H"][r0:r0 + C + 1, c0:c0 + C + 1], 3).tolist())


def stitch(A, pa, B, pb):
    """Triangle strip between two closed loops ordered the same way, matched by their 0..1 parameters."""
    F = []; i = j = 0; nA, nB = len(A), len(B); pa = list(pa) + [1.0]; pb = list(pb) + [1.0]
    while i < nA or j < nB:
        if j >= nB or (i < nA and pa[i + 1] <= pb[j + 1]):
            F.append([A[i % nA], A[(i + 1) % nA], B[j % nB]]); i += 1
        else:
            F.append([A[i % nA], B[(j + 1) % nB], B[j % nB]]); j += 1
    return F


def _submesh(V, N, F, tile, steep=False):
    """Mesh with smooth (global) normals + world UVs; steep layers get per-face planar UVs (no stretching on cliffs)."""
    if steep:
        v = V[F].reshape(-1, 3); n = N[F].reshape(-1, 3); f = np.arange(len(v)).reshape(-1, 3)
        tri = V[F]; fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); ax = np.abs(fn).argmax(1).repeat(3)
        uv = np.where(ax[:, None] == 0, v[:, [2, 1]], np.where(ax[:, None] == 1, v[:, [0, 2]], v[:, [0, 1]])) / tile
    else:
        used, inv = np.unique(F.ravel(), return_inverse=True); v = V[used]; n = N[used]; f = inv.reshape(-1, 3); uv = v[:, [0, 2]] / tile
    m = trimesh.Trimesh(v, f, vertex_normals=n, process=False); m.metadata["uv"] = uv; return m


def _concat(ms):
    v, f, n, uv, o = [], [], [], [], 0
    for m in ms:
        v.append(m.vertices); f.append(m.faces + o); n.append(m.vertex_normals); uv.append(m.metadata["uv"]); o += len(m.vertices)
    m = trimesh.Trimesh(np.vstack(v), np.vstack(f), vertex_normals=np.vstack(n), process=False); m.metadata["uv"] = np.vstack(uv); return m


def shifted(m, d):
    """Translated copy that keeps the explicit (global) normals + UV / colour metadata (trimesh would recompute normals)."""
    out = trimesh.Trimesh(m.vertices + np.asarray(d, float), m.faces, vertex_normals=m.vertex_normals.copy(), process=False); out.metadata.update(m.metadata); return out


def textured(m, material):
    """Attach UVs + material keeping the explicit normals (glTF export writes them). Vertex-coloured far meshes get
    COLOR_0 instead (their shared matte material is added after export: glb_tools.far_material)."""
    n = m.vertex_normals.copy()
    if "vertex_colors" in m.metadata: m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=m.metadata["vertex_colors"])
    else: m.visual = trimesh.visual.TextureVisuals(uv=m.metadata["uv"], material=material)
    m.vertex_normals = n; return m


# ------------------------------------------------------------------ water surfaces (rivers, lakes, sea)
def water_meshes(TR):
    """{feature id: closed thin slab mesh} - rivers follow their profile; edges tuck under the banks."""
    out = {}
    for f in TR.features:
        if f["type"] == "river":
            p = TR._prof[f["id"]]; P, s = resample(f["points"], 3.0)
            inside = (P[:, 0] > TR.x0 - 6) & (P[:, 0] < TR.x1 + 6) & (P[:, 1] > TR.z0 - 6) & (P[:, 1] < TR.z1 + 6)
            keep = inside | (np.arange(len(P)) % 4 == 0); keep[[0, -1]] = True; P, s = P[keep], s[keep]  # coarser out in the middle zone
            wy = np.interp(s, p["s"], p["water"]); bed = np.interp(s, p["s"], p["bed"])
            hw = f.get("width", 8) * 0.35 + (wy - bed) / f.get("bank_slope", 0.5) + 0.6
            D = np.gradient(P, axis=0); D /= np.maximum(np.linalg.norm(D, axis=1, keepdims=True), 1e-9); Nr = np.c_[-D[:, 1], D[:, 0]]
            L_, R_ = P + Nr * hw[:, None], P - Nr * hw[:, None]
            top = np.r_[np.c_[L_[:, 0], wy, L_[:, 1]], np.c_[R_[:, 0], wy, R_[:, 1]]]
            out[f["id"]] = _slab(top, len(P), 0.25)
        elif f["type"] == "lake":
            lv = TR._prof[f["id"]]["level"]; a = np.linspace(0, 2 * np.pi, 40, endpoint=False); r = f["radius"] * 1.2 * max(f.get("stretch", [1, 1]))
            ring = np.c_[f["center"][0] + r * np.cos(a), np.full(len(a), lv), f["center"][1] + r * np.sin(a)]
            out[f["id"]] = _disc(ring, 0.25)
    if TR.water_level is not None:
        x0, z0, x1, z1 = TR.x0, TR.z0, TR.x1, TR.z1; m = TR.T.get("zones", {}).get("middle", {}).get("radius", 0) or 0
        r = max(x1 - x0, z1 - z0) / 2 + m; cx, cz = (x0 + x1) / 2, (z0 + z1) / 2; a = np.linspace(0, 2 * np.pi, 32, endpoint=False)
        out["Sea"] = _disc(np.c_[cx + r * 1.5 * np.cos(a), np.full(32, TR.water_level), cz + r * 1.5 * np.sin(a)], 0.25)
    return out


def _slab(top, n, t):
    """Ribbon top (2n points: left row then right row) -> closed slab of thickness t."""
    bot = top - [0, t, 0]; V = np.vstack([top, bot]); F = []
    for k in range(n - 1):
        a, b, c, d = k, k + 1, n + k + 1, n + k  # top quad (left k..k+1, right k..k+1)
        F += [[a, c, b], [a, d, c]]
        a2, b2, c2, d2 = a + 2 * n, b + 2 * n, c + 2 * n, d + 2 * n; F += [[a2, b2, c2], [a2, c2, d2]]
        F += [[a, b, b2], [a, b2, a2], [d, d2, c2], [d, c2, c]]
    F += [[0, n, 3 * n], [0, 3 * n, 2 * n], [n - 1, n - 1 + 2 * n, 2 * n - 1 + 2 * n], [n - 1, 4 * n - 1, 2 * n - 1]]
    m = trimesh.Trimesh(V, F, process=True); m.fix_normals(); return m


def _disc(ring, t):
    c = ring.mean(0); n = len(ring); top = np.vstack([ring, c]); bot = top - [0, t, 0]; V = np.vstack([top, bot]); F = []
    for k in range(n):
        a, b = k, (k + 1) % n; F += [[n, b, a], [n + n + 1, a + n + 1, b + n + 1], [a, b, b + n + 1], [a, b + n + 1, a + n + 1]]
    m = trimesh.Trimesh(V, F, process=True); m.fix_normals(); return m


# ------------------------------------------------------------------ build entry points
def build_into(scene, L, mats, level_dir, material_fn):
    """Add terrain chunks (LOD0) + water to the dev scene. Returns (triangles, info dict for terrain.json)."""
    T = L["terrain"]; TR = Terrain(T, level_dir); tris = 0; chunks = []
    for (i, j) in TR.chunk_ids():
        parts = TR.chunk_mesh(i, j, 0); grp = f"TR_{i}_{j}"; ct = 0
        for mname, m in sorted(parts.items()):
            if mname not in mats: mats[mname] = material_fn(mname, L["materials"][mname])
            textured(m, mats[mname]); scene.add_geometry(m, node_name=f"{grp}_{mname[4:]}", geom_name=f"{grp}_{mname[4:]}"); ct += len(m.faces)
        tris += ct; chunks.append(dict(id=grp, ij=[i, j], bounds=TR.chunk_bounds(i, j), hash=TR.chunk_hash(i, j), materials=sorted(parts), triangles_lod0=ct))
    mid_info = None
    if T.get("zones", {}).get("middle", {}).get("enabled", True):
        ring, mid_info = middle_ring(TR, L); mt = 0
        for (sct, mname), m in sorted(ring.items()):
            textured(m, None); node = f"TRM_{sct}"; scene.add_geometry(m, node_name=node, geom_name=node); mt += len(m.faces)
        tris += mt; mid_info["nodes"] = sorted({f"TRM_{a}" for a, b in ring}); mid_info["note"] = "MIDDLE zone: no collision, not playable, fogged"
    water = []
    for fid, m in water_meshes(TR).items():
        mname = T.get("water_material", "water")
        if mname not in mats: mats[mname] = material_fn(mname, L["materials"][mname])
        from build_level import uv_world
        mm, uv = uv_world(m, L["materials"][mname].get("tile_m", 4.0)); mm.visual = trimesh.visual.TextureVisuals(uv=uv, material=mats[mname])
        node = f"TW_{fid}"; scene.add_geometry(mm, node_name=node, geom_name=node); tris += len(mm.faces)
        b = m.bounds; water.append(dict(node=node, feature=fid, y=round(float(b[1][1]), 3), bounds=[round(float(v), 2) for v in (b[0][0], b[0][2], b[1][0], b[1][2])]))
    return tris, TR, dict(chunks=chunks, water=water, middle=mid_info)


# ------------------------------------------------------------------ MIDDLE zone: simplified continuation (no collision, not playable)
def middle_radius(TR):
    Z = TR.T.get("zones", {}).get("middle", {}); r0 = math.hypot(TR.x1 - TR.x0, TR.z1 - TR.z0) / 2
    return float(Z.get("radius", max(r0 * 2.6, 380.0))), r0


def ring_height(TR, X, Z, d, R_out, r0):
    """Same terrain function, plus a rise towards the far mountains (starts 20 m out: identical at the near edge)."""
    M = TR.T.get("zones", {}).get("middle", {}); nz = Perlin(_sid(TR.seed, "middle"))
    rise = M.get("rise", 32.0) * smooth(20.0, (R_out - r0) * 0.8, d) ** 1.2 * (0.35 + 0.9 * nz.ridged(X / 70.0, Z / 70.0, 4))
    for f in TR.features:  # river valleys and roads stay low as they run out to the horizon
        if f["type"] in ("river", "road", "street", "path"):
            dl, _, _, _ = poly_query(f["points"], X, Z); w = f.get("width", 8)
            rise = rise * smooth(w + 6, w * 2 + 70, dl)
    return TR.height(X, Z) + rise


def middle_ring(TR, L=None):
    """{(sector, material): mesh} ring from the near grid's outer edge (same vertices -> no crack, same normals -> no
    seam) to the middle radius, coarser outwards, morphing from the rectangle to a circle, outer rim skirted down."""
    G = TR.grid(); H = G["H"]; nz_, nx_ = H.shape; R_out, r0 = middle_radius(TR); c = TR.cell
    rr = [(0, j) for j in range(nx_ - 1)] + [(i, nx_ - 1) for i in range(nz_ - 1)] + [(nz_ - 1, j) for j in range(nx_ - 1, 0, -1)] + [(i, 0) for i in range(nz_ - 1, 0, -1)]
    rr = np.array(rr); P0 = np.c_[G["X"][rr[:, 0], rr[:, 1]], G["Z"][rr[:, 0], rr[:, 1]]]; n0 = len(P0); prm = np.arange(n0) / n0
    cen = np.array([(TR.x0 + TR.x1) / 2, (TR.z0 + TR.z1) / 2]); rel = P0 - cen; dist0 = np.linalg.norm(rel, axis=1); dirs = rel / dist0[:, None]
    span = R_out - r0; ds = [0.0]; d = c * 3
    while d < span: ds.append(d); d *= 1.55
    ds.append(span + (dist0.max() - dist0.min()))
    idxs, Vs, Ns = [], [], []
    for k, dk in enumerate(ds):
        step = 1 if k < 2 else min(2 ** (k - 1), max(1, n0 // 48))
        idx = np.arange(0, n0, step); t = smooth(0, 1, dk / (span * 0.6)) if k else 0.0
        rad = dist0[idx] * (1 - t) + r0 * t + dk; Q = cen + dirs[idx] * rad[:, None]; dd = np.maximum(0, rad - dist0[idx])
        if k == 0: y = H[rr[idx, 0], rr[idx, 1]]; N = G["N"][rr[idx, 0], rr[idx, 1]]
        else:
            y = ring_height(TR, Q[:, 0], Q[:, 1], dd, R_out, r0); e = c
            yx = ring_height(TR, Q[:, 0] + e, Q[:, 1], dd, R_out, r0) - ring_height(TR, Q[:, 0] - e, Q[:, 1], dd, R_out, r0)
            yz = ring_height(TR, Q[:, 0], Q[:, 1] + e, dd, R_out, r0) - ring_height(TR, Q[:, 0], Q[:, 1] - e, dd, R_out, r0)
            N = np.c_[-yx / (2 * e), np.ones(len(idx)), -yz / (2 * e)]; N /= np.linalg.norm(N, axis=1, keepdims=True)
        idxs.append(idx); Vs.append(np.c_[Q[:, 0], y, Q[:, 1]]); Ns.append(N)
    last = Vs[-1].copy(); last[:, 1] -= 40.0; Vs.append(last); Ns.append(Ns[-1]); idxs.append(idxs[-1])  # skirt down: never an open edge against the sky
    off = np.cumsum([0] + [len(v) for v in Vs])[:-1]; V = np.vstack(Vs); N = np.vstack(Ns); F = []; nsk = 0
    for k in range(len(Vs) - 1):
        ia, ib = idxs[k], idxs[k + 1]; f = stitch(list(off[k] + np.arange(len(ia))), list(prm[ia]), list(off[k + 1] + np.arange(len(ib))), list(prm[ib]))
        F += f; nsk = len(f)
    F = np.array(F); skirt = np.arange(len(F)) >= len(F) - nsk; tri = V[F]
    fn = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    flip = (fn[:, 1] < 0) & ~skirt
    cc = tri.mean(1)[:, [0, 2]] - cen; flip |= skirt & (np.einsum("ij,ij->i", fn[:, [0, 2]], cc) < 0)  # skirt faces outward
    F[flip] = F[flip][:, ::-1]; fn[flip] *= -1
    cenp = V[F].mean(1); col = TR.vertex_colors(V, N, L)
    rock = next((k for k, r in enumerate(TR.rules) if r["material"] == "rock"), None)
    ang = (np.degrees(np.arctan2(cenp[:, 2] - cen[1], cenp[:, 0] - cen[0])) + 360) % 360; sector = (ang // 45).astype(int) % 8
    out = {}
    for sct in range(8):  # vertex-coloured (1 material, 1 draw call per sector); colours match the near layers' average albedo
        sel = F[sector == sct]
        if not len(sel): continue
        used, inv = np.unique(sel.ravel(), return_inverse=True)
        m = trimesh.Trimesh(V[used], inv.reshape(-1, 3), vertex_normals=N[used], process=False); m.metadata["vertex_colors"] = col[used]
        out[(sct, "ter_far")] = m
    return out, dict(radius=R_out, near_half_diagonal=round(r0, 1), loops=len(Vs), triangles=int(len(F)), shading="vertex colour (ter_far)")


def write_info(level_dir, L, TR, tinfo):
    """terrain.json: derived metadata (chunks + hashes, LOD ranges, features, layers, water, instancing) for Godot + tools."""
    T = L["terrain"]; prev = {}
    p = os.path.join(level_dir, "terrain.json")
    if os.path.exists(p):
        try: prev = {c["id"]: c["hash"] for c in json.load(open(p)).get("chunks", [])}
        except Exception: prev = {}
    changed = [c["id"] for c in tinfo["chunks"] if prev.get(c["id"]) != c["hash"]]
    info = dict(generated_by="image-to-level Stage 9 (pipeline/terrain.py)", note="Derived from level.json['terrain'] - edit that, not this file.",
                extent=[TR.x0, TR.z0, TR.x1, TR.z1], cell=TR.cell, chunk_cells=TR.C, chunk_m=TR.C * TR.cell, grid=[TR.ncx, TR.ncz],
                lod=lod_settings(T), features=[dict(id=f["id"], type=f["type"], bbox=TR.bbox(f)) for f in TR.features],
                layers=[dict(id=r["id"], material="ter_" + r["material"]) for r in TR.rules], boundary=T.get("boundary"),
                chunks_rebuilt_since_last_build=changed if prev else "all (first build)", **tinfo)
    json.dump(info, open(p, "w"), indent=1)
    return info


def lod_settings(T):
    r = T.get("lod", {}).get("ranges", [60, 120]); return dict(ranges=r, levels=3, note="LOD k samples every 2^k vertices inside a chunk; borders stay full-res (crack-free)")


def map_image(TR, L):
    """Top-down colour map of the detailed terrain (material layer colour x hill shade, water tinted)."""
    G = TR.grid(); H, N = G["H"], G["N"]; P = np.c_[G["X"].ravel(), H.ravel(), G["Z"].ravel()]
    lay = TR.classify(P, N.reshape(-1, 3), {k: v.ravel() for k, v in G["M"].items()}, G["W"].ravel())
    cols = np.array([L["materials"].get("ter_" + r["material"], {}).get("color", [0.5, 0.5, 0.5]) for r in TR.rules])[lay].reshape(H.shape + (3,))
    shade = np.clip(0.55 + 0.6 * (N[..., 0] * -0.5 + N[..., 1] * 0.7 + N[..., 2] * -0.5), 0.3, 1.25)
    img = cols * shade[..., None]; wet = H < G["W"]; img[wet] = img[wet] * 0.35 + np.array([0.2, 0.35, 0.45]) * 0.65
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def is_terrain_node(n):
    return n.startswith(("TR_", "TRM_"))


def describe(L, level_dir=None):
    TR = Terrain(L["terrain"], level_dir)
    return dict(extent=[TR.x0, TR.z0, TR.x1, TR.z1], chunks=f"{TR.ncx}x{TR.ncz} of {TR.C * TR.cell:g} m", cell=TR.cell,
                features=[f"{f['id']}:{f['type']}" for f in TR.features], layers=[r["id"] + "->" + r["material"] for r in TR.rules],
                hashes={f"TR_{i}_{j}": TR.chunk_hash(i, j) for i, j in TR.chunk_ids()})


if __name__ == "__main__":
    d = sys.argv[1]; print(json.dumps(describe(json.load(open(os.path.join(d, "level.json"))), d), indent=1))
