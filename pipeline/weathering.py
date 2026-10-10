"""Weathering decals (Stage 13): green slime leaking from SOME structures, chosen at random but reproducibly.

  spec "leaks": {"chance": 0.4, "material": "accent", "seed": 0, "kinds": ["tower", "building"], "max_drips": 3}

Per chosen structure: runs of slime down one or two faces (from under the cap / under a strap band / from a side
conduit), sometimes a puddle where a run reaches the floor. Decals are flat cut panels (shapes.cut_panel "drip" /
"blob") a few cm in front of the face: visual only (collision false, ignored by navigation and colliders), static
for the mobile merge. With an atlas material (alien_cartoon "accent": banner + "drip" / "puddle" cells) they add
no material and no draw call. They keep clear of the banners so emblems stay readable.
"""
import hashlib, math
import numpy as np

DEFAULTS = dict(chance=0.4, material="slime", seed=0, kinds=["tower", "building"], max_drips=3)


def _rng(*key):
    return np.random.default_rng(int(hashlib.sha1("|".join(map(str, key)).encode()).hexdigest()[:8], 16))


def _rot(x, z, yaw):
    a = math.radians(yaw); return x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)


def leaks(ctx, spec):
    cfg = dict(DEFAULTS, **(spec.get("leaks") or {}))
    if not spec.get("leaks") or cfg["chance"] <= 0: return 0
    by = {o["name"]: o for o in ctx.objects}; mat = cfg["material"]; n_dec = 0
    for s in spec.get("structures", []):
        if s.get("kind") not in cfg["kinds"] or s["id"] not in by or by[s["id"]]["type"] != "group": continue
        rng = _rng(cfg["seed"], s["id"])
        if rng.random() >= cfg["chance"]: continue
        ctx.element = (s["id"], s.get("source", "visible")); g = s["id"]; w, h, d = s.get("size", [4, 8, 4]); dec = s.get("decor") or []
        tower = s["kind"] == "tower"
        floor = max(0.6, min(1.2, h * 0.06)) if (tower and "hazard" in dec and h > 4) else 0.05  # plinth top (drips end above it)
        bw = min(2.6, w * 0.4) if (tower and "banners" in dec) else 0.0
        faces = [(0, d / 2, 0, w), (w / 2, 0, 90, d), (0, -d / 2, 180, w), (-w / 2, 0, 270, d)]
        if not tower: faces = faces[1:]  # buildings: windows + door on the front, slime on sides / back
        pick = rng.choice(len(faces), size=min(len(faces), 1 + int(rng.random() < 0.45)), replace=False)
        k_tot = 0
        for fi in pick:
            px, pz, fy, fw = faces[fi]; lim = fw / 2 - 0.45
            spans = [(-lim, -bw / 2 - 0.12), (bw / 2 + 0.12, lim)] if bw else [(-lim, lim)]
            spans = [sp for sp in spans if sp[1] - sp[0] > 0.35]
            if not spans: continue
            tops = [h] + ([h * f for f in (0.42, 0.7)] if tower and "bands" in dec and h > 6 else [])
            for j in range(int(rng.integers(1, cfg["max_drips"] + 1))):
                if k_tot >= cfg["max_drips"] + 1: break
                a, b = spans[int(rng.integers(len(spans)))]; dw = float(min(b - a, rng.uniform(0.6, 1.3)))
                cx = float(rng.uniform(a + dw / 2, b - dw / 2)); top = float(tops[int(rng.integers(len(tops)))])
                L = float(min(top - floor - 0.05, rng.uniform(0.25, 0.65) * h))
                if L < 0.8: continue
                ox, oz = _rot(cx, 0.05, fy); k_tot += 1; n_dec += 1
                ctx.add(f"{g}_Leak_{k_tot:02d}", "panel", [px + ox, top - L, pz + oz], [round(dw, 2), round(L, 2), 0], mat, g, [0, fy, 0],
                        cut="drip", seed=int(rng.integers(1 << 30)), uv_region="drip", collision=False, outline=False, mobile={"static": True})
                if top - L <= floor + 0.6 and rng.random() < 0.7:  # reached the floor: a puddle spreading in front of the face
                    _puddle(ctx, g, mat, rng, px, pz, fy, cx, (0.25 if floor > 0.1 else 0.0) + 0.05, f"{g}_Puddle_{k_tot:02d}"); n_dec += 1
        if tower and "pipes" in dec and h > 6 and rng.random() < 0.5:  # a side conduit leaking from its top joint
            k = 1 if rng.random() < 0.5 else 3; px, pz, fy, fw = faces[k]; sd = -1 if rng.random() < 0.5 else 1
            L = float(rng.uniform(0.3, 0.8) * h * 0.92); top = h * 0.92 - 0.2; ox, oz = _rot(sd * fw * 0.18, 0.35, fy); k_tot += 1; n_dec += 1
            ctx.add(f"{g}_Leak_{k_tot:02d}", "panel", [px + ox, max(floor, top - L), pz + oz], [0.26, round(min(L, top - floor), 2), 0], mat, g, [0, fy, 0],
                    cut="drip", seed=int(rng.integers(1 << 30)), uv_region="drip", collision=False, outline=False, mobile={"static": True})
            if top - L <= floor + 0.6: _puddle(ctx, g, mat, rng, px, pz, fy, sd * fw * 0.18, 0.5, f"{g}_Puddle_{k_tot:02d}"); n_dec += 1
    ctx.element = None
    if n_dec: ctx.notes.append(f"leaks: {n_dec} slime decals (visual only) on structures picked with chance {cfg['chance']}")
    return n_dec


def _puddle(ctx, g, mat, rng, px, pz, fy, cx, out, name):
    """Flat slime puddle on the floor of the structure's group (y 0.04), centred `out` m + its half depth in front of the
    face, under the drip at lateral offset cx."""
    pw, pd = float(rng.uniform(1.0, 2.2)), float(rng.uniform(0.7, 1.4))
    ox, oz = _rot(cx, out + pd / 2, fy); cx_, cz_ = px + ox, pz + oz
    sx, sz = _rot(0, pd / 2, fy)  # blob centre: local (0, h/2) -> after rotation [-90, fy, 0] at Ry(fy)(0, 0, -h/2) = -(sx, sz)
    ctx.add(name, "panel", [cx_ + sx, 0.04, cz_ + sz], [round(pw, 2), round(pd, 2), 0], mat, g, [-90, fy, 0],
            cut="blob", seed=int(rng.integers(1 << 30)), uv_region="puddle", collision=False, outline=False, mobile={"static": True})
