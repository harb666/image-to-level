"""Procedural 360° sky panoramas (equirectangular, CPU/numpy, seamless).

Every pixel is computed from its 3D view direction, so the image wraps seamlessly at the left/right edge and has no
pole pinching: clouds are projected onto a virtual cloud plane (natural perspective towards the horizon), haze bands
and horizon glows use direction-based 3D noise. Output is an sRGB JPEG usable as:
  - three.js scene.background (EquirectangularReflectionMapping)  - Godot 4 PanoramaSkyMaterial.panorama
Panorama convention (three.js): column u -> azimuth atan2(dir.z, dir.x); top row = straight up.
Level azimuths (sun, glows, factories) use 0° = north (-z), 90° = east (+x).

An external panorama can replace the procedural one: environment.sky.image = "path/to/pano.jpg" (2:1 equirect).
"""
import numpy as np
from PIL import Image

PRESETS = {
    # colours are sRGB 0..1; elevation/azimuth in degrees
    "industrial_smog": dict(zenith=[0.04, 0.06, 0.045], upper=[0.1, 0.15, 0.09], horizon=[0.36, 0.48, 0.2], below=[0.12, 0.16, 0.09],
                            clouds=dict(coverage=0.62, scale=1.0, dark=[0.08, 0.11, 0.07], lit=[0.36, 0.46, 0.22], layers=2, wisps=0.35),
                            smog=dict(strength=0.6, color=[0.42, 0.55, 0.22], height_deg=10),
                            sun=dict(azimuth_deg=215, elevation_deg=9, color=[0.95, 1.0, 0.65], size_deg=1.6, glow=0.5),
                            light=dict(sun_energy=2.2, sun_color=[0.95, 1.0, 0.85], ambient_energy=1.5, exposure=1.0)),
    "sunset": dict(zenith=[0.08, 0.1, 0.25], upper=[0.3, 0.25, 0.45], horizon=[1.0, 0.55, 0.28], below=[0.3, 0.2, 0.18],
                   clouds=dict(coverage=0.45, scale=1.0, dark=[0.3, 0.18, 0.25], lit=[1.0, 0.6, 0.35], layers=2, wisps=0.5),
                   smog=dict(strength=0.25, color=[0.9, 0.5, 0.35], height_deg=6),
                   sun=dict(azimuth_deg=270, elevation_deg=4, color=[1.0, 0.7, 0.4], size_deg=2.2, glow=1.0),
                   light=dict(sun_energy=2.2, sun_color=[1.0, 0.7, 0.45], ambient_energy=0.8, exposure=1.0)),
    "sunrise": dict(zenith=[0.18, 0.28, 0.5], upper=[0.55, 0.55, 0.7], horizon=[1.0, 0.75, 0.6], below=[0.35, 0.3, 0.3],
                    clouds=dict(coverage=0.35, scale=1.2, dark=[0.45, 0.4, 0.5], lit=[1.0, 0.8, 0.7], layers=2, wisps=0.6),
                    smog=dict(strength=0.2, color=[0.95, 0.8, 0.7], height_deg=5),
                    sun=dict(azimuth_deg=90, elevation_deg=6, color=[1.0, 0.85, 0.6], size_deg=2.0, glow=0.9),
                    light=dict(sun_energy=2.4, sun_color=[1.0, 0.85, 0.7], ambient_energy=1.0, exposure=1.0)),
    "night": dict(zenith=[0.005, 0.01, 0.03], upper=[0.02, 0.03, 0.07], horizon=[0.07, 0.09, 0.15], below=[0.03, 0.035, 0.05],
                  clouds=dict(coverage=0.3, scale=1.0, dark=[0.02, 0.025, 0.04], lit=[0.12, 0.14, 0.2], layers=1, wisps=0.3),
                  smog=dict(strength=0.2, color=[0.1, 0.12, 0.2], height_deg=6),
                  sun=dict(azimuth_deg=140, elevation_deg=35, color=[0.85, 0.9, 1.0], size_deg=1.8, glow=0.25), stars=0.8,
                  light=dict(sun_energy=0.35, sun_color=[0.6, 0.7, 1.0], ambient_energy=0.35, exposure=1.2)),
    "overcast": dict(zenith=[0.42, 0.44, 0.46], upper=[0.55, 0.57, 0.58], horizon=[0.7, 0.71, 0.7], below=[0.35, 0.36, 0.36],
                     clouds=dict(coverage=0.92, scale=0.8, dark=[0.38, 0.4, 0.42], lit=[0.72, 0.73, 0.74], layers=2, wisps=0.2),
                     smog=dict(strength=0.3, color=[0.7, 0.71, 0.7], height_deg=12),
                     sun=dict(azimuth_deg=180, elevation_deg=40, color=[1, 1, 1], size_deg=3, glow=0.15),
                     light=dict(sun_energy=0.9, sun_color=[0.95, 0.95, 1.0], ambient_energy=1.4, exposure=1.0)),
    "alien": dict(zenith=[0.06, 0.02, 0.12], upper=[0.25, 0.08, 0.35], horizon=[0.15, 0.6, 0.6], below=[0.08, 0.15, 0.18],
                  clouds=dict(coverage=0.5, scale=1.3, dark=[0.15, 0.05, 0.2], lit=[0.6, 0.3, 0.7], layers=2, wisps=0.6),
                  smog=dict(strength=0.4, color=[0.2, 0.7, 0.65], height_deg=8),
                  sun=dict(azimuth_deg=120, elevation_deg=20, color=[0.7, 1.0, 0.95], size_deg=1.2, glow=0.7),
                  planet=dict(azimuth_deg=300, elevation_deg=32, size_deg=14, color=[0.55, 0.35, 0.7], ring=True),
                  light=dict(sun_energy=1.5, sun_color=[0.7, 1.0, 0.95], ambient_energy=0.9, exposure=1.0)),
    "clear_day": dict(zenith=[0.12, 0.3, 0.7], upper=[0.35, 0.55, 0.85], horizon=[0.75, 0.85, 0.95], below=[0.4, 0.42, 0.45],
                      clouds=dict(coverage=0.3, scale=1.0, dark=[0.6, 0.65, 0.75], lit=[1, 1, 1], layers=2, wisps=0.4),
                      smog=dict(strength=0.15, color=[0.8, 0.85, 0.9], height_deg=5),
                      sun=dict(azimuth_deg=160, elevation_deg=55, color=[1, 0.98, 0.9], size_deg=1.5, glow=0.6),
                      light=dict(sun_energy=3.0, sun_color=[1.0, 0.97, 0.9], ambient_energy=1.2, exposure=1.0)),
}


def resolve(cfg):
    """Preset + per-level overrides (shallow-merged per sub-dict)."""
    p = {k: (dict(v) if isinstance(v, dict) else v) for k, v in PRESETS[cfg.get("preset", "industrial_smog")].items()}
    for k, v in cfg.items():
        if isinstance(v, dict) and isinstance(p.get(k), dict): p[k].update(v)
        elif k != "preset": p[k] = v
    return p


# ---------------------------------------------------------------- direction-based value noise (seamless by construction)
def _hash3(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 1274126177 + seed * 144665) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)


def vnoise3(x, y, z, seed=0):
    xi, yi, zi = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64), np.floor(z).astype(np.int64)
    fx, fy, fz = x - xi, y - yi, z - zi
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fx if dx else 1 - fx) * (fy if dy else 1 - fy) * (fz if dz else 1 - fz)
                out = out + w * _hash3(xi + dx, yi + dy, zi + dz, seed)
    return out


def fbm3(x, y, z, seed=0, octaves=5, gain=0.5):
    tot, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        tot = tot + amp * vnoise3(x * 2 ** o, y * 2 ** o, z * 2 ** o, seed + o * 17); norm += amp; amp *= gain
    return tot / norm


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1); return t * t * (3 - 2 * t)


def _dir(az_deg, el_deg):
    """Level azimuth (0=north/-z, 90=east/+x) + elevation -> unit vector."""
    a, e = np.radians(az_deg), np.radians(el_deg)
    return np.array([np.cos(e) * np.sin(a), np.sin(e), -np.cos(e) * np.cos(a)])


def _mix(a, b, t):
    return a + (b - a) * t[..., None]


def render(cfg, width=2048, glows=(), seed=7):
    """cfg: environment.sky dict (preset + overrides). glows: extra horizon glows [{azimuth_deg, color, width_deg, strength}].
    Returns (HxWx3 float sRGB image, info dict with horizon/ambient colours)."""
    p = resolve(cfg); W, H = width, width // 2
    u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
    a = (u - 0.5) * 2 * np.pi; el = (0.5 - v) * np.pi  # three.js equirect mapping
    A, E = np.meshgrid(a, el)
    dx, dy, dz = np.cos(E) * np.cos(A), np.sin(E), np.cos(E) * np.sin(A)
    s = np.sin(E)
    col = lambda k: np.array(p[k], float)
    # gradient: below -> horizon -> upper -> zenith
    up = _smooth(0.0, 0.35, s); top = _smooth(0.3, 1.0, s)
    img = _mix(_mix(col("horizon"), col("upper"), up), col("zenith"), top)
    img = np.where((s < 0)[..., None], _mix(col("horizon"), col("below"), _smooth(0, 0.25, -s)), img)
    # haze / smog band around the horizon, varying with azimuth
    sm = p.get("smog", {})
    if sm.get("strength", 0) > 0:
        band = np.exp(-(np.degrees(E) / sm.get("height_deg", 8)) ** 2); R = band[:, 0] > 1e-4  # noise only where visible
        var = 0.55 + 0.45 * fbm3(dx[R] * 2.5, dy[R] * 6, dz[R] * 2.5, seed + 3, 4)
        img[R] = _mix(img[R], np.array(sm["color"]), np.clip(band[R] * var * sm["strength"], 0, 1))
    # sun / moon (+ glow)
    sun = p["sun"]; sd = _dir(sun["azimuth_deg"], sun["elevation_deg"])
    ang = np.degrees(np.arccos(np.clip(dx * sd[0] + dy * sd[1] + dz * sd[2], -1, 1)))
    # clouds: perspective-projected cloud plane layers, lit from the sun side
    cl = p["clouds"]; cover = np.zeros((H, W))
    if cl.get("coverage", 0) > 0:
        R = s[:, 0] > 0.03  # clouds only above the horizon fade (rows below stay cloud-free) - halves the noise work
        sR = s[R]; t = 1.0 / np.maximum(sR, 0.12)  # cap the perspective squeeze near the horizon (no aliasing band)
        for layer in range(int(cl.get("layers", 2))):
            sc = cl.get("scale", 1.0) * (1.6 if layer else 0.9)
            px, pz = dx[R] * t * sc, dz[R] * t * sc * cl.get("stretch", 1.0)  # stretch > 1: long streaky (stylised) clouds
            n = fbm3(px * 0.9, pz * 0.9 * (1 + layer * 1.5), layer * 7.3, seed + 11 + layer, 5)
            if cl.get("angular"):  # stylised, angular cloud shapes: ridged noise folded into sharp crests
                n = n * (1 - cl["angular"]) + (1 - np.abs(2 * n - 1)) * cl["angular"] * 0.75 + cl["angular"] * 0.12
            thr = 1 - cl["coverage"] * (0.95 if layer == 0 else cl.get("wisps", 0.4))
            c = _smooth(thr - 0.02, thr + 0.22, n) * _smooth(0.03, 0.22, sR)  # fade into haze at the horizon
            n2 = fbm3((px + sd[0] * 0.25) * 0.9, (pz + sd[2] * 0.25) * 0.9 * (1 + layer * 1.5), layer * 7.3, seed + 11 + layer, 5)
            light = np.clip(0.55 + (n - n2) * 4, 0, 1) * (0.7 + 0.3 * np.exp(-ang[R] / 40))
            if cl.get("posterize"):  # flat cartoon cloud shading + hard cloud edges
                k = cl["posterize"]; light = np.round(light * (k - 1)) / (k - 1); c = _smooth(0.45, 0.55, c) * _smooth(0.03, 0.22, sR)
            ccol = _mix(np.array(cl["dark"]), np.array(cl["lit"]), light)
            img[R] = _mix(img[R], ccol, c * (0.95 if layer == 0 else 0.6)); cover[R] = np.maximum(cover[R], c)
    if p.get("stars", 0):
        st = (_hash3(np.floor(A * 900).astype(np.int64), np.floor(E * 900).astype(np.int64), 3, seed) > 0.9985) * _smooth(0.02, 0.2, s)
        img = img + (st * p["stars"] * (1 - cover))[..., None]
    pdisc = 0.0
    if p.get("planet"):
        pl = p["planet"]; pd = _dir(pl["azimuth_deg"], pl["elevation_deg"])
        pang = np.degrees(np.arccos(np.clip(dx * pd[0] + dy * pd[1] + dz * pd[2], -1, 1))); r = pl["size_deg"] / 2
        disc = _smooth(r, r * 0.97, pang); pdisc = disc; shade = np.clip(0.35 + 0.65 * (dx * sd[0] + dy * sd[1] + dz * sd[2] + 0.4), 0.15, 1)
        st = pl.get("stripes")
        if st:  # explicit horizontal stripes: hard-edged bands alternating colour / stripe colour (cartoon planet)
            ph = np.sin((dy - pd[1]) * st.get("frequency", 300)); band = _smooth(-0.15, 0.15, ph) * st.get("strength", 0.5)
            pc = _mix(np.array(pl["color"])[None, None] * np.ones_like(img), np.array(st.get("color", [1, 1, 1]))[None, None] * np.ones_like(img), band)
            img = _mix(img, pc * np.clip(shade, 0.6, 1)[..., None], disc * (1.0 if pl.get("over_clouds") else 1 - 0.5 * cover))
            if pl.get("over_clouds"): cover = np.where(disc > 0.5, 0.0, cover)  # nothing veils it; the sun glow below stays off it too
        else:
            bands = 0.85 + 0.15 * np.sin((dy - pd[1]) * 300)
            img = _mix(img, np.array(pl["color"])[None, None] * (shade * bands)[..., None], disc * (1 - 0.7 * cover))
        if pl.get("ring"):
            ringd = np.abs((dy - pd[1]) * 3 - (dx - pd[0]) * 0.6)
            ring = (ringd < 0.012) * (pang < r * 2.2) * (pang > r * 1.15)
            img = _mix(img, np.array(pl["color"]) * 1.3, ring * 0.6)
    disc = _smooth(sun["size_deg"], sun["size_deg"] * 0.8, ang) * (1 - 0.85 * cover)
    glow = sun.get("glow", 0.5) * (0.6 * np.exp(-ang / 6) + 0.4 * np.exp(-ang / 30)) * (1 - 0.5 * cover)
    if p.get("planet") and p["planet"].get("over_clouds"): glow = glow * (1 - 0.85 * pdisc); disc = disc * (1 - pdisc)  # planet in front of the sun
    img = img + (np.array(sun["color"])[None, None] * np.clip(disc + glow, 0, None)[..., None]) * (s > -0.05)[..., None]
    # industrial/city glows on the horizon (factories)
    for g in list(p.get("glows", [])) + list(glows):
        gd = np.degrees(np.angle(np.exp(1j * (np.arctan2(dx, -dz) - np.radians(g["azimuth_deg"])))))
        k = g.get("strength", 0.5) * np.exp(-(gd / g.get("width_deg", 12)) ** 2 - (np.degrees(E) / g.get("height_deg", 7)) ** 2)
        R = k.max(1) > 1e-5
        img[R] = img[R] + np.array(g["color"]) * (k[R] * (0.7 + 0.3 * fbm3(dx[R] * 4, dy[R] * 9, dz[R] * 4, seed + 5, 3)))[..., None]
    img = np.clip(img + (np.random.default_rng(seed).random((H, W, 1)) - 0.5) / 255, 0, 1)  # dither: no banding
    rows = lambda e0, e1: img[(np.degrees(el) >= e0) & (np.degrees(el) < e1)].reshape(-1, 3).mean(0)
    info = dict(horizon_rgb=rows(-1.5, 2.5).round(3).tolist(), upper_rgb=rows(20, 90).round(3).tolist(),
                below_rgb=rows(-30, -5).round(3).tolist(), sun=p["sun"], light=p.get("light", {}), preset=cfg.get("preset", "industrial_smog"))
    return img, info


def load_external(path, width):
    """Use an externally made 2:1 equirect panorama (resized to the quality width)."""
    im = Image.open(path).convert("RGB").resize((width, width // 2), Image.LANCZOS)
    a = np.asarray(im, float) / 255; H = a.shape[0]
    return a, dict(horizon_rgb=a[H // 2 - 4:H // 2 + 6].reshape(-1, 3).mean(0).round(3).tolist(),
                   upper_rgb=a[:H // 4].reshape(-1, 3).mean(0).round(3).tolist(), below_rgb=a[-H // 4:].reshape(-1, 3).mean(0).round(3).tolist())


if __name__ == "__main__":  # python3 pipeline/sky.py out_dir  -> one 1024px panorama per preset
    import os, sys, time
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    for name in PRESETS:
        t = time.time(); im, info = render({"preset": name}, 1024)
        Image.fromarray((im * 255).astype(np.uint8)).save(f"{out}/{name}.jpg", quality=85); print(name, f"{time.time() - t:.1f}s", info["horizon_rgb"])
