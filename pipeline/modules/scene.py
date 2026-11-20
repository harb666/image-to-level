"""Stage 191: scenecore / Y2K emo-rave structures for the scene_rave experiment level - a platform style with print
sides, a neon checker cap, a glowing edge and chrome studs; a DJ stage; floating giant icons; holographic
butterflies; kandi-bead railings; rainbow light ribbons; cartoon skull statues; studded candy columns; glitch TVs.
Everything moving goes through the "swing" effect (ctx.swings) or "spin" (turntables, the spiral disc)."""
import math
import numpy as np
from modules import structure
import architecture as A
from architecture import local, footprint_edge
from trimesh.transformations import euler_from_matrix

KANDI = ["kandi_pink", "kandi_cyan", "kandi_green", "kandi_violet", "kandi_orange"]
GLOWS = ["glow_pink", "glow_cyan", "glow_green", "glow_violet", "glow_orange"]


def _rot_from(xv, yv):
    """Euler (deg, sxyz) of the rotation taking local x -> xv and local y -> yv (orthonormalised)."""
    xv = np.asarray(xv, float); xv /= np.linalg.norm(xv); yv = np.asarray(yv, float); yv = yv - xv * (yv @ xv); yv /= np.linalg.norm(yv)
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = xv, yv, np.cross(xv, yv)
    return [round(math.degrees(q), 4) for q in euler_from_matrix(M, "sxyz")]


def _swing(ctx, **kw):
    ctx.swings = getattr(ctx, "swings", []) + [kw]


# ------------------------------------------------------------------ platform style
def scene_plinth(ctx, p, base_y, centre):
    """A platform dressed for the rave: sides in a print ("side": zebra / leopard role), a neon checker cap
    ("material"), a glowing edge band under the cap's lip ("edge" glow role) and a row of chrome studs on every face."""
    n, (cx, cz), (w, d), top = p["id"], p["center"], p["size"], p["top"]; shape = p.get("shape", "rect")
    g = ctx.add(n, "group", [cx, 0, cz]); h = max(0.3, top - 0.45 - base_y)
    A._solid(ctx, n + "_Base", g, shape, w, h, d, base_y, p.get("side", "structure"))
    ctx.floor_of[n] = A._solid(ctx, n + "_Cap", g, shape, w, 0.45, d, top - 0.45, p.get("material", "deck"), 0.3, vkey=f"floor@{top:.2f}"); p["_plate"] = 0.3
    if h > 0.9:
        A._solid(ctx, n + "_Edge", g, shape, w, 0.14, d, top - 0.62, p.get("edge", "trim"), 0.18)  # neon band just under the lip
        if ctx.detail >= 1 and shape == "rect" and h > 1.6:  # chrome studs along every face
            ys = top - 1.05
            for ax, L_, off in (("x", w, d / 2 + 0.03), ("x", w, -d / 2 - 0.03), ("z", d, w / 2 + 0.03), ("z", d, -w / 2 - 0.03)):
                k_n = max(2, int(L_ / 1.4))
                for k in range(k_n):
                    t = -L_ / 2 + (k + 0.5) * L_ / k_n
                    pos = [t, ys, off] if ax == "x" else [off, ys, t]; rot = [90, 0, 0] if ax == "x" else [0, 0, 90]
                    ctx.add(f"{n}_Stud_{ax}{'pn'[off < 0]}{k + 1:02d}", "cylinder", pos, [0.22, 0.08, 0.22], "stud", g, rot, sections=6, collision=False, outline=False, mobile={"static": True})
    A._cover(ctx, p, g, top, p.get("side", "structure"))
    ctx.walkable.append(A._walk_rect(p, top))


A.PLATFORM_STYLES["scene"] = scene_plinth


# ------------------------------------------------------------------ the DJ stage
@structure("dj_stage", pad=False)
def dj_stage(ctx, s, x, y, z, yaw):
    """A rave DJ stage on its platform ("on"), facing local +z: the booth (glitch-screen front, two turntables whose
    holo labels spin, a mixer of glowing knobs), speaker stacks with neon woofers, a zebra truss arch with spotlights
    and sweeping laser fans (swing), a giant psychedelic spiral disc spinning behind the booth in a neon ring, and
    neon word signs ("signs": [[word cell, x, y], ...] on the "signs" atlas)."""
    n = s["id"]; W_ = float(s.get("width", 26.0)); D_ = float(s.get("depth", 10.0)); st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    P = lambda lx, ly, lz: (lambda q: [x + q[0], y + ly, z + q[1]])(local(lx, lz, yaw))
    # booth
    bz = 0.6; ctx.add(n + "_Booth", "box", P(0, 0, bz), [7.0, 1.15, 2.0], "machine", rot=[0, yaw, 0], **st)
    ctx.add(n + "_BoothScreen", "panel", P(0, 0.12, bz + 1.02), [6.6, 0.9, 0], "glitch", rot=[0, yaw, 0], **vs)
    ctx.add(n + "_BoothTop", "box", P(0, 1.15, bz), [7.3, 0.1, 2.2], "frame", rot=[0, yaw, 0], **vs)
    for k, sx in enumerate((-2.1, 2.1)):  # turntables
        ctx.add(f"{n}_Deck_{k + 1}", "box", P(sx, 1.25, bz), [1.8, 0.12, 1.6], "frame", rot=[0, yaw, 0], **vs)
        ctx.add(f"{n}_Platter_{k + 1}", "cylinder", P(sx - 0.1, 1.37, bz), [1.3, 0.06, 1.3], "jet_black", rot=[0, yaw, 0], sections=16, **vs)
        ctx.add(f"{n}_Label_{k + 1}", "cylinder", P(sx - 0.1, 1.43, bz), [0.9, 0.02, 0.9], "holo", rot=[0, yaw, 0], sections=16, spin=33.0 * (1 if k else -1),
                collision=False, outline=False, mobile={"merge": False})
        ctx.add(f"{n}_Arm_{k + 1}", "box", P(sx + 0.62, 1.37, bz - 0.2), [0.08, 0.06, 0.95], "stud", rot=[0, yaw + 25, 0], **vs)
    ctx.add(n + "_Mixer", "box", P(0, 1.25, bz), [1.3, 0.16, 1.5], "jet_black", rot=[0, yaw, 0], **vs)
    for i in range(3):
        for j in range(4):
            ctx.add(f"{n}_Knob_{i}{j}", "cylinder", P(-0.4 + i * 0.4, 1.41, bz - 0.5 + j * 0.33), [0.16, 0.08, 0.16], GLOWS[(i + j) % 5], rot=[0, yaw, 0], sections=6, **vs)
    # speaker stacks
    for k, sx in enumerate((-(W_ / 2 - 2.0), W_ / 2 - 2.0)):
        for lv in range(3):
            ctx.add(f"{n}_Speaker_{k + 1}{lv + 1}", "box", P(sx, lv * 1.75, -0.5), [2.6, 1.7, 1.8], "jet_black" if lv % 2 else "structure", rot=[0, yaw, 0], **st)
            for c_ in (-0.62, 0.62):
                q = P(sx + c_, lv * 1.75 + 0.85, 0.42)
                ctx.add(f"{n}_Woofer_{k + 1}{lv + 1}{'ab'[c_ > 0]}", "cylinder", q, [1.0, 0.12, 1.0], "jet_black", rot=[90, yaw, 0], sections=12, **vs)
                ctx.add(f"{n}_Cone_{k + 1}{lv + 1}{'ab'[c_ > 0]}", "cylinder", P(sx + c_, lv * 1.75 + 0.85, 0.5), [0.42, 0.06, 0.42], GLOWS[(k + lv) % 5], rot=[90, yaw, 0], sections=12, **vs)
    # truss arch with spotlights + lasers
    Ht = float(s.get("truss_h", 9.0)); tx = W_ / 2 - 0.5
    for k, sx in enumerate((-tx, tx)):
        ctx.add(f"{n}_Truss_{k + 1}", "box", P(sx, 0, -2.5), [0.7, Ht, 0.7], "zebra_pink", rot=[0, yaw, 0], **st)
    ctx.add(n + "_TrussBeam", "box", P(0, Ht, -2.5), [2 * tx + 0.7, 0.8, 0.8], "zebra_pink", rot=[0, yaw, 0], **st)
    ctx.add(n + "_TrussGlow", "box", P(0, Ht - 0.1, -2.05), [2 * tx + 0.5, 0.12, 0.06], "glow_cyan", rot=[0, yaw, 0], **vs)
    for k in range(6):
        sx = -tx + 2.0 + k * (2 * tx - 4.0) / 5
        ctx.add(f"{n}_Spot_{k + 1}", "cylinder", P(sx, Ht - 0.95, -2.3), [0.6, 0.85, 0.6], "jet_black", rot=[0, yaw, 0], sections=8, **vs)
        ctx.add(f"{n}_SpotLens_{k + 1}", "cylinder", P(sx, Ht - 1.0, -2.3), [0.5, 0.06, 0.5], GLOWS[k % 5], rot=[0, yaw, 0], sections=8, **vs)
    for f_, sx in enumerate((-tx * 0.5, tx * 0.5)):  # laser fans, sweeping
        g_ = f"{n}_Laser_{f_ + 1}"; o_ = P(sx, Ht - 0.6, -2.0); L_ = float(s.get("laser_len", 18.0))
        for b in range(5):
            ang = -30 + b * 15; dirv = np.array([math.sin(math.radians(ang)) * 0.9, -0.28, 0.9]); dirv /= np.linalg.norm(dirv)
            dx_, dz_ = local(dirv[0], dirv[2], yaw); dw = np.array([dx_, dirv[1], dz_]); c_ = np.array(o_) + dw * L_ / 2
            ctx.add(f"{g_}_Beam_{b + 1}", "box", list(c_ - [0, 0.025, 0]), [0.05, 0.05, L_], ["glow_green", "glow_pink"][f_],
                    rot=_rot_from(np.cross([0, 1, 0], dw) if abs(dw[1]) < 0.99 else [1, 0, 0], np.cross(dw, np.cross([0, 1, 0], dw))), collision=False, outline=False, mobile={"group": g_})
        _swing(ctx, id=g_, group=g_, pivot=[round(v, 3) for v in o_], axis=[0, 1, 0], amp=28.0, period=5.0 + f_, phase=1.3 * f_)
    # spiral disc behind the booth, in a neon ring
    R_ = float(s.get("disc", 9.0)) / 2; dc = P(0, 1.3 + R_, -D_ / 2 + 0.6)
    ctx.add(n + "_SpiralBack", "cylinder", P(0, 1.3 + R_, -D_ / 2 + 0.25), [2 * R_ + 1.2, 0.4, 2 * R_ + 1.2], "frame", rot=[90, yaw, 0], sections=24, **st)
    ctx.add(n + "_SpiralRing", "cylinder", P(0, 1.3 + R_, -D_ / 2 + 0.42), [2 * R_ + 0.9, 0.12, 2 * R_ + 0.9], "glow_pink", rot=[90, yaw, 0], sections=24, collision=False, outline=False,
            hole=R_, hole_res=24, mobile={"static": True})
    ctx.add(n + "_Spiral", "cylinder", dc, [2 * R_, 0.06, 2 * R_], "spiral", rot=[90, yaw, 0], sections=24, spin=-9.0, collision=False, outline=False, mobile={"merge": False})
    # neon word signs
    for k, (cell, lx, ly, sz) in enumerate(s.get("signs", [])):
        q = P(lx, ly, -D_ / 2 + 0.335)  # on the backing board's face
        ctx.add(f"{n}_SignBack_{k + 1}", "box", P(lx, ly - 0.15, -D_ / 2 + 0.2), [sz + 0.3, sz + 0.3, 0.25], "jet_black", rot=[0, yaw, 0], **vs)
        ctx.add(f"{n}_SignPole_{k + 1}", "cylinder", P(lx, 0.0, -D_ / 2 + 0.05), [0.22, ly - 0.1, 0.22], "frame", sections=6, collision=False, outline=True, mobile={"static": True})  # holds it up
        ctx.add(f"{n}_Sign_{k + 1}", "panel", q, [sz, sz, 0], "signs", rot=[0, yaw, 0], uv_region=cell, **vs)
    ctx.notes.append(f"{n}: DJ stage - booth, turntables, speaker stacks, truss with spotlights + 2 sweeping laser fans, spinning spiral disc, {len(s.get('signs', []))} neon signs")


# ------------------------------------------------------------------ floating giant icons
def _skull(ctx, nm, c, r, yaw, mv, bow="glow_pink"):
    """A chunky cartoon skull (centre c, radius r) with black eye sockets, glowing pupils, teeth and a bow."""
    P = lambda lx, ly, lz: (lambda q: [c[0] + q[0], c[1] + ly, c[2] + q[1]])(local(lx, lz, yaw))
    ctx.add(nm + "_Cranium", "dome", P(0, -r * 0.15, 0), [2 * r, 1.25 * r, 2 * r], "bone", rot=[0, yaw, 0], sections=16, **mv)
    ctx.add(nm + "_Face", "cylinder", P(0, -r * 0.55, 0), [2 * r * 0.98, r * 0.45, 2 * r * 0.98], "bone", rot=[0, yaw, 0], sections=16, **mv)
    ctx.add(nm + "_Jaw", "box", P(0, -r * 0.95, r * 0.15), [r * 1.15, r * 0.45, r * 1.2], "bone", rot=[0, yaw, 0], **mv)
    for sd in (-1, 1):
        ctx.add(f"{nm}_Eye{'LR'[sd > 0]}", "cylinder", P(sd * r * 0.4, -r * 0.05, r * 0.86), [r * 0.62, 0.08 * r, r * 0.62], "jet_black", rot=[90, yaw, 0], sections=12, **mv)
        ctx.add(f"{nm}_Pupil{'LR'[sd > 0]}", "cylinder", P(sd * r * 0.4, -r * 0.05, r * 0.92), [r * 0.22, 0.04 * r, r * 0.22], "glow_cyan", rot=[90, yaw, 0], sections=8, **mv)
    ctx.add(nm + "_Nose", "box", P(0, -r * 0.42, r * 0.92), [r * 0.22, r * 0.2, 0.06 * r], "jet_black", rot=[0, yaw, 0], **mv)
    for k in range(4):
        ctx.add(f"{nm}_Tooth_{k + 1}", "box", P(-r * 0.36 + k * r * 0.24, -r * 0.95, r * 0.76), [r * 0.16, r * 0.26, r * 0.06], "jet_black", rot=[0, yaw, 0], **mv)
    bw = dict(mv, intentional=list(set((mv.get("intentional") or []) + ["floating"])))  # (the bow sits on the dome's curve)
    for sd in (-1, 1):  # a bow on top, tilted
        ctx.add(f"{nm}_Bow{'LR'[sd > 0]}", "sticker3d", P(r * 0.45 + sd * r * 0.38, r * 0.78, 0), [r * 0.75, r * 0.6, r * 0.28], bow, rot=[0, yaw, -90 * sd], icon="diamond2d", **bw)
    ctx.add(nm + "_BowKnot", "cylinder", P(r * 0.45, r * 1.05, 0), [r * 0.3, r * 0.3, r * 0.3], bow, rot=[90, yaw, 0], sections=8, **bw)


@structure("float_decor", pad=False)
def float_decor(ctx, s, x, y, z, yaw):
    """Giant icons floating over the rave, each turning slowly and bobbing (its own swing group): "items" [{icon:
    heart / star / bolt / diamond2d (sticker3d) | gem | skull, at [x, y, z], size, material, spin deg/s, bob m}]."""
    n = s["id"]
    for k, it in enumerate(s["items"]):
        g = f"{n}_{k + 1:02d}"; ic = it["icon"]; sz = float(it.get("size", 3.0)); c = it["at"]; mat = it.get("material", "glow_pink")
        mv = dict(collision=False, outline=it.get("outline", True), mobile={"group": g}, intentional=["floating"])
        if ic == "skull": _skull(ctx, g, c, sz / 2, float(it.get("yaw", 0.0)), mv, bow=it.get("bow", "glow_pink")); cy = c[1]
        elif ic == "gem": ctx.add(g + "_Gem", "gem", [c[0], c[1] - sz * 0.6, c[2]], [sz, sz * 1.2, sz], mat, **mv); cy = c[1]
        else:
            ctx.add(g + "_Icon", "sticker3d", [c[0], c[1] - sz / 2, c[2]], [sz, sz, sz * 0.22], mat, rot=[0, float(it.get("yaw", 0.0)), float(it.get("tilt", 0.0))], icon=ic, **mv)
            if it.get("rim"):  # a white die-cut border behind it (the sticker look)
                bz_ = local(0, -sz * 0.2, float(it.get("yaw", 0.0)))  # behind the icon (no shared faces)
                ctx.add(g + "_Rim", "sticker3d", [c[0] + bz_[0], c[1] - sz * 0.55, c[2] + bz_[1]], [sz * 1.1, sz * 1.1, sz * 0.12], "bone", rot=[0, float(it.get("yaw", 0.0)), float(it.get("tilt", 0.0))], icon=ic, **dict(mv, outline=False))
            cy = c[1]
        _swing(ctx, id=g, group=g, pivot=[c[0], cy, c[2]], axis=[0, 1, 0], spin=float(it.get("spin", 12.0)), amp=0.0, period=1.0,
               bob=float(it.get("bob", 0.5)), bob_period=float(it.get("bob_period", 3.2 + 0.37 * k)), phase=round(0.71 * k, 3))
    ctx.notes.append(f"{n}: {len(s['items'])} floating giant icons")


# ------------------------------------------------------------------ holographic butterflies
@structure("butterflies", pad=False)
def butterflies(ctx, s, x, y, z, yaw):
    """Holographic butterflies circling "center" [x, y, z] at "radius" (each its own radius / height / speed),
    flapping: per butterfly a body group and two wing groups (swing: the circle + a hinge flap applied first)."""
    n = s["id"]; C = s["center"]; cnt = int(s.get("count", 6)); rg = np.random.default_rng(int(s.get("seed", 5))); ws = float(s.get("wing", 1.3))
    for k in range(cnt):
        R = float(s.get("radius", 14.0)) * (0.7 + 0.6 * rg.random()); th = 2 * math.pi * k / cnt + rg.random() * 0.4; hy = C[1] + rg.uniform(-2.5, 2.5)
        B = np.array([C[0] + R * math.cos(th), hy, C[2] + R * math.sin(th)]); sp = float(s.get("speed", 14.0)) * (0.7 + 0.6 * rg.random()) * (1 if k % 2 else -1)
        hd = np.array([-math.sin(th), 0, math.cos(th)]) * (1 if sp > 0 else -1)  # heading (along the circle, the way it flies)
        side = np.cross(hd, [0, 1, 0]); side /= np.linalg.norm(side); g0 = f"{n}_{k + 1}"; per = 0.55 + 0.25 * rg.random(); ph = round(rg.random() * 3, 3)
        orbit = dict(pivot=[C[0], C[1], C[2]], axis=[0, 1, 0], spin=round(sp, 3), amp=0.0, period=1.0, bob=0.6, bob_period=round(2.4 + rg.random(), 3), phase=ph)
        mvb = dict(collision=False, outline=True, mobile={"group": g0 + "_Body"}, intentional=["floating"])
        ctx.add(g0 + "_Body", "cylinder", list(B - hd * ws * 0.45 - [0, 0.07, 0]), [0.14, ws * 0.9, 0.14], "jet_black", rot=_rot_from(side, hd), sections=6, **mvb)
        _swing(ctx, id=g0 + "_Body", group=g0 + "_Body", **orbit)
        for sd in (-1, 1):  # wings lying flat, hinged along the body
            gw = f"{g0}_Wing{'LR'[sd > 0]}"; xv = side * sd; rot = _rot_from(xv, hd)
            Rm = np.array([xv / np.linalg.norm(xv), hd, np.cross(xv / np.linalg.norm(xv), hd)]).T
            pos = B - Rm @ np.array([-ws / 2, ws / 2, 0.0])
            ctx.add(gw, "sticker3d", list(pos), [ws, ws, 0.04], s.get("material", "holo"), rot=rot, icon="wing", collision=False, outline=True, mobile={"group": gw}, intentional=["floating"])
            _swing(ctx, id=gw, group=gw, **orbit, pre=dict(pivot=[round(v, 3) for v in B], axis=[round(v, 4) for v in hd], amp=38.0 * sd, period=round(per, 3), phase=ph))
    ctx.notes.append(f"{n}: {cnt} holographic butterflies circling, flapping")


# ------------------------------------------------------------------ kandi bead railings
@structure("kandi_rail", pad=False)
def kandi_rail(ctx, s, x, y, z, yaw):
    """A railing of kandi: black posts with glowing caps along "points" [[x, z], ...] at height "y" (deck top), two
    strands of pony beads (5 neon colours, a white letter cube every 9th bead) sagging between the posts."""
    n = s["id"]; Y = float(s["y"]); pts = [np.array(p_, float) for p_ in s["points"]]; st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    posts = []
    for a_, b_ in zip(pts, pts[1:]):
        L_ = np.linalg.norm(b_ - a_); k_n = max(1, int(math.ceil(L_ / float(s.get("post_step", 3.5)))))
        posts += [a_ + (b_ - a_) * k / k_n for k in range(k_n)]
    posts.append(pts[-1])
    for k, p_ in enumerate(posts):
        ctx.add(f"{n}_Post_{k + 1:02d}", "cylinder", [p_[0], Y, p_[1]], [0.14, 1.15, 0.14], "frame", sections=6, collision=True, outline=False, **st)
        ctx.add(f"{n}_Cap_{k + 1:02d}", "cylinder", [p_[0], Y + 1.15, p_[1]], [0.2, 0.12, 0.2], GLOWS[k % 5], sections=6, **vs)
    bi = 0
    for k, (a_, b_) in enumerate(zip(posts, posts[1:])):
        L_ = float(np.linalg.norm(b_ - a_)); nb = max(2, int(L_ / 0.2))
        for hy, sag in ((1.08, 0.22), (0.62, 0.16)):
            for j in range(nb):
                t = (j + 0.5) / nb; q = a_ + (b_ - a_) * t; yy = Y + hy - sag * 4 * t * (1 - t)
                dv = np.array([b_[0] - a_[0], -sag * 4 * (1 - 2 * t), b_[1] - a_[1]]); dv /= np.linalg.norm(dv); bi += 1
                if bi % 9 == 0: ctx.add(f"{n}_Cube_{bi:04d}", "box", [q[0], yy - 0.085, q[1]], [0.17, 0.17, 0.17], "bone", rot=[0, math.degrees(math.atan2(dv[0], dv[2])), 0], **vs)
                else: ctx.add(f"{n}_Bead_{bi:04d}", "cylinder", [q[0], yy, q[1]], [0.17, 0.14, 0.17], KANDI[bi % 5], rot=_rot_from(np.cross(dv, [0, 1, 0]) if abs(dv[1]) < 0.99 else [1, 0, 0], dv), sections=6, **vs)
    ctx.notes.append(f"{n}: kandi railing, {len(posts)} posts, {bi} beads")


# ------------------------------------------------------------------ rainbow light ribbons
@structure("ribbons", pad=False)
def ribbons(ctx, s, x, y, z, yaw):
    """Rainbow light trails swooping through the air: "paths" [[[x, y, z], ...], ...] (world), "width" m; material
    "rainbow" scrolled along its length (effect liquid_flow, flow_uv [1, 0])."""
    n = s["id"]; names = []
    for k, path in enumerate(s["paths"]):
        nm = f"{n}_{k + 1}"; names.append(nm)
        ctx.add(nm, "ribbon", [0, 0, 0], [float(s.get("width", 1.6)), 0.05, 0.05], s.get("material", "rainbow"), path=path, tile=float(s.get("tile", 6.0)), subdiv=10,
                double_sided=True, collision=False, outline=False, mobile={"static": True}, intentional=["floating"])
    ctx.ribbon_flows = getattr(ctx, "ribbon_flows", []) + [dict(id=n, targets=names, speed=float(s.get("speed", 6.0)))]
    ctx.notes.append(f"{n}: {len(names)} rainbow light ribbons")


# ------------------------------------------------------------------ statues, columns, TVs
@structure("skull_statue", pad=False)
def skull_statue(ctx, s, x, y, z, yaw):
    """A giant cartoon skull with a bow on a checker plinth (static)."""
    n = s["id"]; r = float(s.get("radius", 2.2)); st = dict(mobile={"static": True})
    ctx.add(n + "_Plinth", "box", [x, y, z], [r * 2.2, 1.2, r * 2.2], "deck_cyan", rot=[0, yaw, 0], **st)
    ctx.add(n + "_PlinthGlow", "box", [x, y + 1.2, z], [r * 2.3, 0.1, r * 2.3], "glow_cyan", rot=[0, yaw, 0], collision=False, outline=False, **st)
    _skull(ctx, n, [x, y + 1.3 + r * 1.2, z], r, yaw, dict(collision=True, outline=True, **st), bow=s.get("bow", "glow_pink"))


@structure("studded_column", pad=False)
def studded_column(ctx, s, x, y, z, yaw):
    """A candy column: zebra-pink shaft, chrome stud rings, a glowing crown and a spotlight on top."""
    n = s["id"]; H = float(s.get("height", 9.0)); r = float(s.get("radius", 0.7)); st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    ctx.add(n + "_Base", "cylinder", [x, y, z], [r * 3.0, 0.6, r * 3.0], "frame", sections=8, **st)
    ctx.add(n + "_Shaft", "pole", [x, y + 0.6, z], [2 * r, H - 1.2, 2 * r], s.get("material", "zebra_pink"), sections=8, uv_mode="band", uv_len=round(math.pi * 2 * r / 2, 3), **st)
    for k, hy in enumerate((1.6, H / 2, H - 1.8)):
        ctx.add(f"{n}_Ring_{k + 1}", "cylinder", [x, y + hy, z], [2 * r + 0.16, 0.22, 2 * r + 0.16], "jet_black", sections=8, **vs)
        for j in range(8):
            a = 2 * math.pi * (j + 0.5) / 8; ctx.add(f"{n}_Stud_{k + 1}{j + 1}", "cylinder", [x + (r + 0.1) * math.cos(a), y + hy + 0.11, z + (r + 0.1) * math.sin(a)], [0.14, 0.1, 0.14],
                                                       "stud", rot=_rot_from([-math.sin(a), 0, math.cos(a)], [math.cos(a), 0, math.sin(a)]), sections=6, **vs)
    ctx.add(n + "_Crown", "cylinder", [x, y + H - 0.6, z], [2 * r + 0.5, 0.6, 2 * r + 0.5], s.get("glow", "glow_cyan"), sections=8, **vs)
    ctx.add(n + "_Top", "cylinder", [x, y + H, z], [2 * r + 0.3, 0.25, 2 * r + 0.3], "frame", sections=8, **vs)


@structure("glitch_tv", pad=False)
def glitch_tv(ctx, s, x, y, z, yaw):
    """A chunky wall TV (black casing, neon bezel) showing the glitching retro-internet profile screen."""
    n = s["id"]; w, h = s.get("screen", [5.0, 3.6])[:2]; vs = dict(collision=False, outline=False, mobile={"static": True})
    P = lambda lx, ly, lz: (lambda q: [x + q[0], y + ly, z + q[1]])(local(lx, lz, yaw))
    ctx.add(n + "_Case", "box", P(0, 0, 0.4), [w + 0.6, h + 0.6, 0.8], "jet_black", rot=[0, yaw, 0], collision=False, outline=True, mobile={"static": True})
    ctx.add(n + "_Bezel", "box", P(0, 0.15, 0.82), [w + 0.2, h + 0.2, 0.06], s.get("bezel", "glow_pink"), rot=[0, yaw, 0], **vs)
    ctx.add(n + "_Screen", "panel", P(0, 0.3, 0.86), [w, h - 0.0, 0], "glitch", rot=[0, yaw, 0], **vs)
