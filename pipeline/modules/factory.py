"""Factory-hall dressing (Stage 16): slime vats, hanging claws, upper galleries, blast doors.

  {"id": "Vat_N1", "kind": "vat", "position": [18, -45], "size": [8, 20, 8]}            # stands in the slime
  {"id": "Claw_1", "kind": "claw", "position": [24, -8], "length": 9}                    # hangs from the ceiling
  {"id": "Gallery_N", "kind": "gallery", "from": [-14, -54.5], "to": [14, -54.5], "y": 16}  # balcony along a wall
  {"id": "Door_N", "kind": "blast_door", "position": [0, 7, -55.7], "facing": "south", "size": [6, 7, 0.6]}

Built for small files: few parts, 10-sided cylinders, existing material roles only (the vat glass reuses the hazard
slime material - no new texture), visual-only parts without colliders, "mobile": {"static": true} so they merge into
the static cells (no extra draw calls). Vat glass keeps a solid collider (not a hazard area: touching a vat is safe).
"""
import math
from modules import structure
from architecture import local as A_local, local


@structure("vat", pad=False)
def vat(ctx, s, x, y, z, yaw):
    """Slime vat: plinth, red-lit bands, glowing slime glass section, dark upper body with a banner, rimmed cap."""
    n = s["id"]; D, H, _ = s.get("size", [8, 20, 8]); st = dict(mobile={"static": True}); seg = int(s.get("sections", 10))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); y0 = -1.0  # plinth reaches into the slime: no visible gap at its foot
    gh = H * 0.5; base = 3.0; uh = max(1.5, H - base - 1.0 - gh - 1.0 - 0.8)
    ctx.add(n + "_Plinth", "cylinder", [0, y0, 0], [D + 1.2, base - y0, D + 1.2], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_BandLow", "cylinder", [0, base, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    ctx.add(n + "_Glass", "cylinder", [0, base + 0.9, 0], [D, gh + 0.2, D], s.get("material", "glass"), g, sections=seg, collision=True, double_sided=True, tube=True, **st)  # see-through: blobs rise inside; ends sunk 10 cm into the bands (no shared planes)
    ctx.add(n + "_BandMid", "cylinder", [0, base + 1.0 + gh, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    yu = base + 2.0 + gh
    ctx.add(n + "_Body", "cylinder", [0, yu, 0], [D + 0.3, uh, D + 0.3], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_Cap", "cylinder", [0, yu + uh, 0], [D + 0.9, 0.8, D + 0.9], "trim", g, sections=seg, collision=False, **st)
    if s.get("banner", True) and uh > 3:  # banner on the side facing the hall centre
        bw = min(3.0, D * 0.4); r = (D + 0.3) / 2 * math.cos(math.pi / seg) + 0.05
        ctx.add(n + "_Banner", "panel", [0, yu + uh * 0.08, r], [bw, uh * 0.8, 0], "accent", g, collision=False, outline=False, **st)


@structure("claw", pad=False)
def claw(ctx, s, x, y, z, yaw):
    """Crane claw on an overhead runway (Stage 31): an I-beam rail runs wall to wall through the claw along world x
    ("rail_yaw" turns it; claws on the same line share one rail), hung from the roof on hangers, under the ceiling ducts; a trolley rides
    it and the hoist chains hang from the trolley to the block with its red light and three prongs. "rail": false
    (or no ceiling) = the old chain straight from the ceiling / "y"."""
    n = s["id"]; top = float(s.get("y", getattr(ctx, "ceiling_y", 20.0))); L = float(s.get("length", 9.0)); yb = top - L
    st = dict(collision=False, mobile={"static": True}); g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw, 0])
    rail = s.get("rail", True) and getattr(ctx, "ceiling_y", None) is not None and "y" not in s
    if rail:
        ry = top - float(s.get("rail_drop", 4.9)); yb = min(yb, ry - 2.5)  # rail bottom; the claw head stays where it was (or lower)
        ryaw = float(s.get("rail_yaw", 0.0))  # runways follow the room grid (world x by default), whatever the claw's own turn
        _crane_rail(ctx, x, z, ryaw, ry, top)
        tg = ctx.add(n + "_Trolley", "group", [x, 0, z], rot=[0, ryaw, 0], collision=False)
        ctx.add(n + "_Trolley_Body", "box", [0, ry - 0.75, 0], [1.8, 0.75, 1.3], "machine", tg, **st)  # hangs under the rail's bottom flange
        for k_ in (-1, 1): ctx.add(f"{n}_Trolley_Side_{k_ + 1}", "box", [0, ry - 0.2, k_ * 0.48], [1.5, 1.0, 0.14], "frame", tg, outline=False, **st)  # wheel plates either side of the web
        ctop = ry - 0.7  # chains reach 5 cm into the trolley (attached, not just touching)
    else: ctop = top
    for k, o in enumerate((-0.18, 0.18)):  # two chain strands
        ctx.add(f"{n}_Chain_{k + 1}", "box", [o, yb, 0], [0.14, ctop - yb, 0.3], "frame", g, outline=False, **st)
    ctx.add(n + "_Block", "frustum", [0, yb - 1.5, 0], [1.9, 1.5, 1.9], "structure_b", g, sections=6, bottom_scale=0.55, **st)  # hoist housing, wide on top (Stage 33)
    hc = (0, yb - 1.5, 0)  # lights lie on the housing's flats (it tapers)
    face_light(ctx, n + "_Light", g, hc, 6, 0.95, 0.95 * 0.55, 1.5, 60, 0.55, 0.95, 0.36, st)
    for i, th in enumerate((180, 300)): face_light(ctx, f"{n}_Strip_{i + 1}", g, hc, 6, 0.95, 0.95 * 0.55, 1.5, th, 0.2, 1.3, 0.14, st)
    ctx.add(n + "_Collar", "cylinder", [0, yb - 1.85, 0], [0.75, 0.4, 0.75], "machine", g, sections=8, **st)
    claw_fingers(ctx, n, g, 0, yb - 1.84, 0, 1.7, st)


def _rooms(ctx):
    """[(x0, z0, x1, z1)] inner rectangles of the arena and its annexes."""
    out = []
    for a in [ctx.spec.get("arena") or {}] + list(ctx.spec.get("annexes") or []):
        if not a.get("size"): continue
        (cx, cz), (w, d) = a.get("center", [0, 0]), a["size"]; out.append((cx - w / 2, cz - d / 2, cx + w / 2, cz + d / 2))
    return out


def _rail_clear_ends(ctx, x, z, ux, uz, ry, t0, t1, reach=8.0, gap=2.0):
    """Pull each runway end back (up to `reach` m) until the beam's swept box (0.8 m tall, 0.7 m wide, +-0.2 m) is
    clear of wall-mounted things at that end - window screens, TVs, fans, vents, machines, emblems, galleries."""
    import re, numpy as _np
    from anchors import world_matrices
    W, _ = world_matrices({"objects": ctx.objects}); pat = re.compile(r"(_Screen|_Back|_M\d\d(Monitor|Fan|Vent|Machine|Emblem|Door)|Gallery|_SillLight|Mouth)")
    boxes = []
    for o in ctx.objects:
        if o["type"] in ("group", "band") or not o.get("size") or not pat.search(o["name"]): continue
        w_, h_, d_ = o["size"]; C = _np.array([[sx * w_ / 2, yy, sz * d_ / 2, 1] for sx in (-1, 1) for yy in (0, h_) for sz in (-1, 1)]) @ W[o["name"]].T
        lo, hi = C[:, :3].min(0), C[:, :3].max(0)
        if lo[1] < ry + 1.0 and hi[1] > ry - 0.4: boxes.append((lo, hi))
    def hit(ta, tb):
        a = _np.array([x + ux * ta, ry - 0.4, z + uz * ta]); b = _np.array([x + ux * tb, ry + 1.0, z + uz * tb]); lo = _np.minimum(a, b); hi = _np.maximum(a, b)
        lo[[0, 2]] -= _np.abs([uz, ux]) * 0.55; hi[[0, 2]] += _np.abs([uz, ux]) * 0.55
        return [bb for bb in boxes if (_np.minimum(hi, bb[1]) - _np.maximum(lo, bb[0]) > 0).all()]
    stops = [False, False]
    ts = []  # claws hanging on this line: a blocked end stops 5 m past the last one (not just short of the wall)
    for c in ctx.spec.get("structures", []):
        if c.get("kind") != "claw" or c.get("rail") is False: continue
        px, pz = c["position"][0], c["position"][-1]; t = (px - x) * ux + (pz - z) * uz
        if abs((px - x) * uz - (pz - z) * ux) < 0.5: ts.append(t)
    for k_ in (0, 1):
        for _ in range(int(reach / 0.25)):
            ta, tb = (t0 - gap, t0 + 0.05) if k_ == 0 else (t1 - 0.05, t1 + gap)  # the end + the gap in front of it (toward the wall)
            if not hit(ta, tb): break
            if k_ == 0: t0 += 0.25
            else: t1 -= 0.25
            stops[k_] = True
        if stops[k_] and ts:
            if k_ == 0: t0 = max(t0, min(min(ts) - 5.0, t1 - 4.0))
            else: t1 = min(t1, max(max(ts) + 5.0, t0 + 4.0))
    return t0, t1, stops


def _crane_rail(ctx, x, z, yaw, ry, top, step=11.0):
    """Overhead runway through (x, z) along local x of yaw, wall to wall of the room it is in (once per line)."""
    ux, uz = A_local(1, 0, yaw); room = next((r for r in _rooms(ctx) if r[0] < x < r[2] and r[1] < z < r[3]), None)
    ts = []
    if room:
        for k, (p, u, lo, hi) in enumerate(((x, ux, room[0], room[2]), (z, uz, room[1], room[3]))):
            if abs(u) > 1e-6: ts += sorted([(lo - p) / u, (hi - p) / u])
    t0, t1 = (max(ts[0::2]), min(ts[1::2])) if ts else (-15.0, 15.0)
    t0, t1 = t0 + 0.13, t1 - 0.13  # ends stop just short of the wall faces (wall fans / glow rings sit a few cm proud)
    t0, t1, stops = _rail_clear_ends(ctx, x, z, ux, uz, ry, t0, t1)  # Stage 38: never into a screen / TV / fan / vent on the wall
    cx_, cz_ = x + ux * (t0 + t1) / 2, z + uz * (t0 + t1) / 2; Lr = t1 - t0
    key = (round(cx_, 1), round(cz_, 1), round(yaw % 180, 1), round(ry, 2)); done = getattr(ctx, "crane_rails", set())
    if key in done: return None
    done.add(key); ctx.crane_rails = done; n = f"CraneRail_{len(done):02d}"; st = dict(collision=False, mobile={"static": True})
    g = ctx.add(n, "group", [cx_, 0, cz_], rot=[0, yaw, 0])
    ctx.add(n + "_Beam", "ibeam", [0, ry, 0], [Lr, 0.8, 0.7], "frame", g, **st)
    ctx.add(n + "_Stripe", "box", [0, ry + 0.28, 0], [Lr - 0.4, 0.24, 0.74], "stripe", g, outline=False, **st)  # hazard band on the web
    for e, on in ((-1, stops[0]), (1, stops[1])):  # end stop block where the runway was cut short of something on the wall
        if on: ctx.add(f"{n}_EndStop_{e + 1}", "box", [e * (Lr / 2 - 0.3), ry - 0.15, 0], [0.7, 1.1, 1.0], "structure_b", g, **st)  # 5 cm past the beam end
    m = max(2, int(round(Lr / step)))
    for i in range(m + 1):  # hanger rods up into the roof (they carry it; the ends stop short of the walls)
        hx = -Lr / 2 + 0.6 + (Lr - 1.2) * i / m
        ctx.add(f"{n}_Hanger_{i:02d}", "box", [hx, ry + 0.8, 0], [0.3, top - ry - 0.8 + 0.1, 0.3], "frame", g, outline=False, **st)
    return g


@structure("gallery", pad=False)
def gallery(ctx, s, x, y, z, yaw):
    """Upper balcony along a wall (visual tier, out of reach): deck ledge, railing on the hall side, red light strip
    on its front edge, struts down to the wall. from/to = the line it runs along, y = deck height, width (default 3)."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); w = float(s.get("width", 3.0))
    c = (ctx.spec.get("arena") or {}).get("center", [0, 0]); sx, sz = A_local(1, 0, yaw)
    side = 1 if (c[0] - x) * sx + (c[1] - z) * sz > 0 else -1  # local x side that faces the hall
    st = dict(collision=False, mobile={"static": True}); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Deck", "box", [0, -0.4, 0], [w, 0.4, L], "grate", g, **st)
    ctx.add(n + "_Edge", "box", [side * (w / 2 + 0.05), -0.32, 0], [0.12, 0.2, L - 0.6], "glow", g, outline=False, **st)
    ctx.add(n + "_Rail", "railing", [side * (w / 2 - 0.1), 0, 0], [L, 1.1, 0.08], "rail", g, [0, 90, 0], post_spacing=3.0, **st)
    k = max(2, int(L / 8))
    for i in range(k):
        zz = -L / 2 + L * (i + 0.5) / k
        ctx.add(f"{n}_Strut_{i + 1:02d}", "box", [-side * (w / 2 - 0.3), -2.8, zz], [0.4, 2.4, 0.4], "frame", g, **st)


@structure("blast_door", pad=False)
def blast_door(ctx, s, x, y, z, yaw):
    """Blast door set against a wall (local +z faces the room): heavy frame, two leaves with a hazard stripe, red warning
    light above. Closed (default): lit seam, solid. "open": true: the leaves stand slid aside, the doorway shows a dark
    corridor (void panel) and, with "target", a level_exit trigger stands in the doorway (level.json "exits")."""
    n = s["id"]; W, H, D = s.get("size", [6, 7, 0.6]); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    op = bool(s.get("open")); fw = 0.8
    if op:  # frame as three bars round the opening + the dark corridor beyond
        for k, sd in enumerate((-1, 1)): ctx.add(f"{n}_Jamb_{k + 1}", "box", [sd * (W / 2 + fw / 2), 0, 0], [fw, H + 1.0, D], "structure_b", g, **st)
        ctx.add(n + "_Head", "box", [0, H, 0], [W, 1.0, D], "structure_b", g, **st)
        roles = ctx.spec.get("materials", {}).get("roles", {}); atl = (roles.get("accent") or {}).get("atlas") or {}
        if s.get("target"): ctx.add(n + "_Dark", "panel", [0, 0.02, -D / 2 + 0.05], [W, H, 0], "accent" if "void" in atl else "void", g, uv_region="void", collision=False, outline=False, **st)
    else: ctx.add(n + "_Frame", "box", [0, 0, 0], [W + 1.6, H + 1.0, D], "structure_b", g, **st)
    for k, sd in enumerate((-1, 1)):
        lx = sd * (W * 0.75 + fw + 0.1) if op else sd * (W / 4 + 0.02)  # open: slid aside along the wall
        ctx.add(f"{n}_Leaf_{k + 1}", "box", [lx, 0, D / 2 + 0.12], [W / 2 - 0.08, H, 0.24], "wall", g, collision=op, **st)
        ctx.add(f"{n}_Stripe_{k + 1}", "box", [lx, 0.6, D / 2 + 0.25], [W / 2 - 0.3, 0.8, 0.04], "stripe", g, collision=False, outline=False, **st)
    if not op: ctx.add(n + "_Seam", "box", [0, 0.3, D / 2 + 0.26], [0.12, H - 0.6, 0.04], "glow", g, collision=False, outline=False, **st)
    ctx.add(n + "_Warning", "box", [0, H + 0.2, D / 2 + 0.1], [1.4, 0.4, 0.2], "glow", g, collision=False, outline=False, **st)
    if op and s.get("target"):
        fx, fz = A_local(0, D / 2 + 0.9, yaw); r = min(W / 2 - 0.3, 2.5)
        ctx.exits.append(dict(id=n + "_Exit", type="level_exit", target=s["target"], shape="cylinder", center=[round(x + fx, 3), round(y + 1.6, 3), round(z + fz, 3)],
                              radius=round(r, 3), height=3.0, note="walking through the open door loads the next level (Construct Error: handle in the level_exit trigger)"))
        ctx.notes.append(f"{n}: open exit door -> {s['target']}")
    else: ctx.notes.append(f"{n}: {'open' if op else 'sealed'} blast door ({W} x {H} m)")


@structure("conveyor", pad=False)
def conveyor(ctx, s, x, y, z, yaw):
    """Assembly-line conveyor (from/to at deck height y): belt with lit edge, side frames, end rollers, legs to the deck;
    "parcels" crates ride on it. 0.9 m high: low cover. Local +z runs along the belt."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); w = float(s.get("width", 2.0)); h = 0.9
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    ctx.add(n + "_Bed", "box", [0, 0, 0], [w, h - 0.15, L], "structure_b", g, **st)
    ctx.add(n + "_Belt", "box", [0, h - 0.15, 0], [w - 0.3, 0.12, L - 0.2], "grate", g, collision=False, **st)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Side_{k + 1}", "box", [sd * (w / 2 - 0.06), h - 0.2, 0], [0.16, 0.35, L - 0.04], "frame", g, collision=False, **st)  # 2 cm proud of the bed
        ctx.add(f"{n}_Edge_{k + 1}", "box", [sd * (w / 2 + 0.01), h - 0.45, 0], [0.04, 0.1, L - 0.6], "glow", g, collision=False, outline=False, **st)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Roller_{k + 1}", "cylinder", [0, h - 0.5, sd * (L / 2 - 0.1)], [0.5, w, 0.5], "machine", g, [0, 0, 90], sections=8, collision=False, **st)
    import random as _r
    rg = _r.Random(n); k = 0
    for zz in [(-L / 2 + 1.2 + i * 2.6) for i in range(int((L - 2) / 2.6))]:
        if rg.random() < float(s.get("parcels", 0.4)):
            k += 1; sz = rg.choice((0.7, 0.8, 0.9)); ctx.add(f"{n}_Parcel_{k:02d}", "box", [rg.uniform(-0.2, 0.2), h - 0.03, zz], [sz, sz * 0.8, sz], "accent", g, [0, rg.uniform(-20, 20), 0],
                                                                  collision=False, **st)


@structure("robot_arm", pad=False)
def robot_arm(ctx, s, x, y, z, yaw):
    """Industrial robot arm on a deck (Stage 33, from the user's reference): tapered base and turret, shoulder and elbow
    joints with glowing red discs, angular tapered links with red light strips on both sides, a spike on the elbow,
    sagging hose cables, a tapered wrist housing with a red diamond light and a three-finger claw with lit fingers.
    Pose "pose" deg [shoulder, elbow] (default from the id so neighbours differ). Solid base, visual arm."""
    n = s["id"]; sc = float(s.get("scale", 1.0)); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    vis = dict(collision=False, **st)
    import random as _r
    rg = _r.Random(n); sh, el = s.get("pose", [rg.uniform(20, 55), rg.uniform(40, 100)])
    if s.get("pedestal"):  # sunk 1.2 m deeper than asked: it stands IN what is below (liquid / deck), never on its surface
        pd = float(s["pedestal"]) + 1.2; ctx.add(n + "_Pedestal", "cylinder", [0, -pd, 0], [1.3 * sc, pd, 1.3 * sc], "structure_b", g, sections=10, **st)
    sh, el = _clear_pose(ctx, n, (x, y, z), yaw, sc, sh, el)
    ctx.add(n + "_Base", "frustum", [0, 0, 0], [1.9 * sc, 0.6 * sc, 1.9 * sc], "structure_b", g, sections=8, bottom_scale=1.25, **st)
    ctx.add(n + "_Turret", "frustum", [0, 0.6 * sc, 0], [1.2 * sc, 1.0 * sc, 1.2 * sc], "structure_b", g, sections=8, bottom_scale=1.2, **vis)
    face_light(ctx, n + "_TurretLight", g, (0, 0.6 * sc, 0), 8, 0.6 * sc, 0.72 * sc, 1.0 * sc, 90, 0.15 * sc, 0.85 * sc, 0.14 * sc, vis)
    py = 1.6 * sc; W1, l1 = 0.62 * sc, 2.7 * sc; a1 = math.radians(sh)
    def link(nm, base, ang, L, W, top):  # tapered angular link (wide at the joint it starts from) + red strips on both sides
        ctx.add(nm, "frustum", base, [W, L, W * 0.8], "structure_b", g, [ang, 0, 0], bottom_scale=1.0 / top, **vis)
        dy, dz = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        hw = lambda t: W / 2 * (1 / top + (1 - 1 / top) * t)  # half-width along the link (it tapers to W at the end)
        h0, h1 = hw(0.78), hw(0.18)  # the strip spans 0.18 .. 0.78 of the length: its thickness covers the taper
        for sd in (-1, 1):
            ctx.add(f"{nm}_Strip_{sd + 1}", "box", [sd * (h0 + h1) / 2, base[1] + dy * L * 0.18, base[2] + dz * L * 0.18], [h1 - h0 + 0.05, L * 0.6, 0.14 * sc], "glow", g,
                    [ang, 0, 0], outline=False, **vis)
    def joint(nm, cy, cz, r, W):  # axle along x + a glowing red disc on both ends
        ctx.add(nm, "cylinder", [W / 2, cy, cz], [2 * r, W, 2 * r], "structure_b", g, [0, 0, 90], sections=10, **vis)
        ctx.add(nm + "_Disc", "cylinder", [W / 2 + 0.05, cy, cz], [1.2 * r, W + 0.1, 1.2 * r], "glow", g, [0, 0, 90], sections=10, outline=False, **vis)
    joint(n + "_Shoulder", py, 0, 0.5 * sc, 0.95 * sc)
    link(n + "_Link1", [0, py, 0], sh, l1, W1, 0.78)
    ey, ez = py + l1 * math.cos(a1), l1 * math.sin(a1); a2 = a1 + math.radians(el); l2 = 2.2 * sc
    joint(n + "_Elbow", ey, ez, 0.42 * sc, 0.8 * sc)
    bk = a1 - math.pi / 2  # spike on the back of the elbow, pointing away from link 1
    tip = (ey + 0.9 * sc * math.cos(bk) * -1, ez + 0.9 * sc * math.sin(bk) * -1)
    ctx.add(n + "_Spike", "frustum", [0, tip[0], tip[1]], [0.36 * sc, 0.9 * sc, 0.36 * sc], "structure_b", g, [math.degrees(bk), 0, 0], sections=4, bottom_scale=0.05, **vis)
    link(n + "_Link2", [0, ey, ez], math.degrees(a2), l2, 0.5 * sc, 0.75)
    wy, wz = ey + l2 * math.cos(a2), ez + l2 * math.sin(a2)
    hh = 0.95 * sc  # wrist housing hangs under the end of link 2, wide on top
    ctx.add(n + "_Wrist", "frustum", [0, wy - hh + 0.1 * sc, wz], [0.95 * sc, hh, 0.95 * sc], "structure_b", g, sections=6, bottom_scale=0.55, **vis)
    wc = (0, wy - hh + 0.1 * sc, wz)  # lights lie on the wrist housing's flats
    face_light(ctx, n + "_Light", g, wc, 6, 0.475 * sc, 0.475 * sc * 0.55, hh, 60, hh * 0.45, hh * 0.75, 0.2 * sc, vis)
    for i, th in enumerate((0, 180)): face_light(ctx, f"{n}_WristStrip_{i + 1}", g, wc, 6, 0.475 * sc, 0.475 * sc * 0.55, hh, th, hh * 0.15, hh * 0.85, 0.1 * sc, vis)
    cyl = wy - hh + 0.1 * sc
    ctx.add(n + "_Collar", "cylinder", [0, cyl - 0.25 * sc, wz], [0.45 * sc, 0.28 * sc, 0.45 * sc], "machine", g, sections=8, **vis)
    claw_fingers(ctx, n, g, 0, cyl - 0.24 * sc, wz, sc, vis)
    for k, sd in enumerate((-1, 1)):  # hose cables: link 1 side -> wrist, sagging
        p0 = (sd * 0.3 * sc, py + math.cos(a1) * l1 * 0.45, math.sin(a1) * l1 * 0.45); p1 = (sd * 0.25 * sc, wy - 0.2 * sc, wz - 0.3 * sc)
        cable(ctx, f"{n}_Hose_{k + 1}", g, p0, p1, 0.6 * sc, 0.1 * sc, vis)


def face_light(ctx, nm, g, c, n, r_top, r_bot, H, theta, t0, t1, width, vis, mat="glow"):
    """Stage 33: a light strip lying ON flat `theta` (deg, from +x toward +z) of an n-gon frustum (circumradius r_bot at
    its base c = (x, y, z), r_top at height H): tilted with the face, half its thickness sunk in -> never floating."""
    ca = math.cos(math.pi / n); a = lambda t: ca * (r_bot + (r_top - r_bot) * t / H)
    tilt = math.atan2(a(H) - a(0), H); th = math.radians(theta)
    return ctx.add(nm, "box", [c[0] + a(t0) * math.cos(th), c[1] + t0, c[2] + a(t0) * math.sin(th)], [width, (t1 - t0) / math.cos(tilt), 0.06], mat, g,
                   [math.degrees(tilt), 90 - theta, 0], outline=False, **vis)


def _R(rot):
    from trimesh.transformations import euler_matrix
    return euler_matrix(*[math.radians(v) for v in rot], "sxyz")[:3, :3]


def _arm_points(sh, el, sc):
    """Sample points (local x, y, z; radius) of a robot arm in pose (sh, el): links, wrist, claw fingers, hoses."""
    a1 = math.radians(sh); l1 = 2.7 * sc; py = 1.6 * sc; ey, ez = py + l1 * math.cos(a1), l1 * math.sin(a1)
    a2 = a1 + math.radians(el); l2 = 2.2 * sc; wy, wz = ey + l2 * math.cos(a2), ez + l2 * math.sin(a2); P = []
    for t in (0.35, 0.65, 1.0): P.append((0, py + (ey - py) * t, ez * t, 0.45 * sc))
    for t in (0.33, 0.66, 1.0): P.append((0, ey + (wy - ey) * t, ez + (wz - ez) * t, 0.35 * sc))
    cy = wy - 0.95 * sc + 0.1 * sc - 0.24 * sc
    P.append((0, wy - 0.5 * sc, wz, 0.5 * sc)); P.append((0, cy, wz, 0.3 * sc))
    for k in range(3):  # knuckles and finger tips
        f = math.radians(120 * k); ox, oz = math.sin(f), math.cos(f); o1 = 0.16 * sc + 0.85 * sc * math.sin(math.radians(38))
        ky = cy - 0.85 * sc * math.cos(math.radians(38)); P.append((ox * o1, ky, wz + oz * o1, 0.18 * sc))
        o2 = o1 - 1.0 * sc * math.sin(math.radians(24)); P.append((ox * o2, ky - 1.0 * sc * math.cos(math.radians(24)), wz + oz * o2, 0.08 * sc))
    for t in (0.5,):  # hose sag (0.6 sc) half way between link 1 and the wrist
        P.append((0.3 * sc, (py + math.cos(a1) * l1 * 0.45 + wy) / 2 - 0.6 * sc, (math.sin(a1) * l1 * 0.45 + wz) / 2, 0.12 * sc))
    return P


def _clear_pose(ctx, n, pos, yaw, sc, sh, el, margin=0.25):
    """Stage 34: the pose closest to (sh, el) whose links, wrist, claw and hoses keep `margin` m clear of every other
    object already in the level (conveyor beds, parcels, decks, walls ...) - no arm glitching into things."""
    import numpy as _np
    from anchors import world_matrices
    W, by = world_matrices({"objects": ctx.objects}); boxes = []
    for o in ctx.objects:
        if o["type"] in ("group", "panel", "stream", "band", "boundary") or not o.get("size") or o["name"].startswith(n + "_") or o["name"] == n: continue
        if o["name"] in getattr(ctx, "hazards", []): continue
        M = W[o["name"]]; w, h, d = o["size"]; C = _np.array([[sx * w / 2, yy, sz * d / 2, 1] for sx in (-1, 1) for yy in (0, h) for sz in (-1, 1)]) @ M.T
        lo, hi = C[:, :3].min(0), C[:, :3].max(0)
        if _np.linalg.norm((lo + hi) / 2 - _np.array(pos)) < 12: boxes.append((lo, hi))
    def hits(a, b):
        for lx, ly, lz, r in _arm_points(a, b, sc):
            wx, wz = local(lx, lz, yaw); q = _np.array([pos[0] + wx, pos[1] + ly, pos[2] + wz]); rr = r + margin
            if any(_np.all(q > lo - rr) and _np.all(q < hi + rr) for lo, hi in boxes): return True
        return False
    if not hits(sh, el): return sh, el
    for d in range(1, 30):  # widen the search step by step: open the elbow (lifts the claw), lean less / more
        for a, b in ((sh, el - 4 * d), (sh - 3 * d, el), (sh - 3 * d, el - 4 * d), (sh + 3 * d, el - 4 * d), (sh, el + 4 * d)):
            if 5 <= a <= 75 and 10 <= b <= 140 and not hits(a, b):
                ctx.notes.append(f"{n}: pose {sh:.0f}/{el:.0f} -> {a:.0f}/{b:.0f} (clear of the objects around it)"); return a, b
    ctx.notes.append(f"{n}: no clear pose found near {sh:.0f}/{el:.0f}"); return sh, el


def claw_fingers(ctx, n, g, cx, cy, cz, sc, vis, open_deg=38):
    """Three-finger claw under (cx, cy, cz) in group g (Stage 33): each finger an upper segment angled outwards, a
    knuckle, and a tapered tip curling back in to a point; red inlays sit on the fingers' outer faces (computed from
    each segment's own rotation, half sunk in)."""
    import numpy as _np
    for k in range(3):
        ph = 120 * k; f = math.radians(ph); ox, oz = math.sin(f), math.cos(f); rr = 0.16 * sc
        t1, l1 = math.radians(open_deg), 0.85 * sc; B = _np.array([cx + ox * rr, cy, cz + oz * rr]); r1 = [180 - open_deg, ph, 0]
        ctx.add(f"{n}_Finger_{k + 1}", "box", B.tolist(), [0.24 * sc, l1, 0.2 * sc], "structure_b", g, r1, **vis)
        R1 = _R(r1); d1 = R1 @ [0, 1, 0]; out1 = -(R1 @ [0, 0, 1])  # local -z faces outwards / up
        E = B + d1 * l1
        ctx.add(f"{n}_Finger_{k + 1}_Knuckle", "box", (E - [0, 0.13 * sc, 0]).tolist(), [0.28 * sc, 0.26 * sc, 0.26 * sc], "machine", g, [0, ph, 0], **vis)
        t2 = -24; l2 = 1.0 * sc; r2 = [-t2, ph, 0]; R2 = _R(r2); d2 = R2 @ [0, 1, 0]  # tip: base at the point, axis back up to the knuckle
        T = E - d2 * l2
        ctx.add(f"{n}_Finger_{k + 1}_Tip", "frustum", T.tolist(), [0.24 * sc, l2 + 0.06 * sc, 0.2 * sc], "structure_b", g, r2, bottom_scale=0.2, **vis)
        out2 = R2 @ [0, 0, 1]
        if out2 @ [ox, 0, oz] < 0: out2 = -out2
        P = B + d1 * l1 * 0.15 + out1 * 0.1 * sc  # upper inlay on the outer face (box: constant half-thickness 0.1 sc)
        ctx.add(f"{n}_Finger_{k + 1}_Lit2", "box", P.tolist(), [0.07 * sc, l1 * 0.6, 0.06], "glow", g, r1, outline=False, **vis)
        h0, h1 = 0.1 * sc * (0.2 + 0.8 * 0.45), 0.1 * sc * (0.2 + 0.8 * 0.95)  # tip tapers: thickness spans the taper
        P2 = T + d2 * l2 * 0.45 + out2 * ((h0 + h1) / 2)
        ctx.add(f"{n}_Finger_{k + 1}_Lit", "box", P2.tolist(), [0.07 * sc, l2 * 0.5, h1 - h0 + 0.05], "glow", g, r2, outline=False, **vis)


def cable(ctx, nm, g, p0, p1, sag, r, vis, segs=4):
    """Sagging hose between two points (in g's frame): segs thin boxes along a parabola."""
    import numpy as _np
    pts = [(p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t - sag * 4 * t * (1 - t), p0[2] + (p1[2] - p0[2]) * t) for t in _np.linspace(0, 1, segs + 1)]
    for j, (pa, pb) in enumerate(zip(pts, pts[1:])):
        dx, dy, dz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]; sl = math.sqrt(dx * dx + dy * dy + dz * dz) or 1e-3
        yw = math.degrees(math.atan2(dx, dz)); pt = math.degrees(math.asin(max(-1, min(1, dy / sl))))
        ctx.add(f"{nm}_{j + 1}", "box", [(pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 - r / 2, (pa[2] + pb[2]) / 2], [2 * r, 2 * r, sl + 0.06], "frame", g, [-pt, yw, 0],
                outline=False, **vis)


@structure("lattice", pad=False)
def lattice(ctx, s, x, y, z, yaw):
    """Maintenance-shaft frame: open lattice tower (corner posts, cross rings every 4 m, diagonal braces on two faces),
    a lit ladder strip and a hanging service cage near the top. size [w, h, d]; visual only (the platforms inside are
    ordinary platforms + stairs)."""
    n = s["id"]; w, h, d = s.get("size", [10, 20, 10]); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(collision=False, mobile={"static": True})
    for i, (px, pz) in enumerate(((-1, -1), (1, -1), (1, 1), (-1, 1))):
        ctx.add(f"{n}_Post_{i + 1}", "box", [px * w / 2, 0, pz * d / 2], [0.5, h, 0.5], "frame", g, **st)
    for k in range(1, int(h // 4) + 1):
        yy = min(h - 0.6, k * 4.0)
        for j, (px, pz, ww, dd) in enumerate(((0, -d / 2, w - 0.3, 0.3), (0, d / 2, w - 0.3, 0.3), (-w / 2, 0, 0.3, d - 0.3), (w / 2, 0, 0.3, d - 0.3))):  # ends inside the posts
            ctx.add(f"{n}_Ring_{k:02d}_{j + 1}", "box", [px, yy, pz], [ww, 0.3, dd], "structure_b", g, **st)
    for k in range(int(h // 4)):  # braces on the two side faces, alternating
        sd = 1 if k % 2 else -1; L = math.hypot(d, 4.0); ang = math.degrees(math.atan2(d, 4.0)) * sd
        for px in (-w / 2, w / 2): ctx.add(f"{n}_Brace_{k + 1:02d}_{'W' if px < 0 else 'E'}", "box", [px, k * 4.0 + 2.0 - L / 2 * 0.0, 0], [0.18, L, 0.18], "frame", g, [ang, 0, 0], **st)
    ctx.add(n + "_Ladder", "box", [w / 2 - 0.3, 0.5, d / 2 + 0.05], [0.5, h - 1.0, 0.08], "glow", g, outline=False, **st)
    ctx.add(n + "_Cage", "box", [-w / 4, h - 4.5, 0], [2.4, 2.6, 2.4], "grate", g, **st)
    ctx.add(n + "_CageLight", "box", [-w / 4, h - 1.9, 0], [0.6, 0.3, 0.6], "glow", g, outline=False, **st)
    ctx.add(n + "_Cable", "box", [-w / 4, h - 1.9, 0], [0.12, 1.9, 0.12], "frame", g, outline=False, **st)


@structure("conduit", pad=False)
def conduit(ctx, s, x, y, z, yaw):
    """Waste conduit: ribbed half-tunnel over a walkway (from/to at walkway height y): arch ribs every "step" m with red
    light bars, a spine pipe along the top and a slime channel down one side. Visual only (the walkway is a platform)."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); w = float(s.get("width", 9.0)); h = float(s.get("height", 7.0))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(collision=False, mobile={"static": True}); step = float(s.get("step", 6.0)); k = 0
    zz = -L / 2 + step / 2
    while zz < L / 2:
        k += 1; ctx.add(f"{n}_Rib_{k:02d}", "arch", [0, 0, zz], [w, h, 0.8], "structure_b", g, opening=(w - 1.6) / w, opening_h=(h - 1.0) / h, **st)
        ctx.add(f"{n}_RibLight_{k:02d}", "box", [0, h - 1.15, zz + 0.42], [w * 0.5, 0.18, 0.06], "glow", g, outline=False, **st)
        zz += step
    ctx.add(n + "_Spine", "cylinder", [0, h + 0.6, -L / 2], [1.2, L, 1.2], "pipe", g, [90, 0, 0], sections=8, **st)
    side = float(s.get("channel_side", 0))
    if side: ctx.add(n + "_Channel", "box", [side * (w / 2 + 1.2), -0.6, 0], [2.0, 0.3, L], s.get("material", "hazard"), g, **st)



@structure("column", pad=False)
def column(ctx, s, x, y, z, yaw):
    """Reactor column from the slime to the ceiling (or "height"): plinth, glowing slime-glass sections at irregular
    heights between dark banded drums, a flared capital into the roof, red lights on some bands. "radius" (2.5).
    Drums, neck and capital are rings (Stage 34): the glass pipe's bore runs on through them up into the roof."""
    n = s["id"]; r = float(s.get("radius", 2.5)); top = float(s.get("height", getattr(ctx, "ceiling_y", 24.0)))
    import random as _r
    rg = _r.Random(n); g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True}); sec = int(s.get("sections", 8))
    ctx.add(n + "_Plinth", "cylinder", [0, -0.5, 0], [2 * r * 1.35, 4.5, 2 * r * 1.35], "structure_b", g, sections=sec, hole=round(r * 0.8, 3), hole_res=16, **st)  # the pipe reaches down into the slime
    yy, k = 4.0, 0; planes = [-0.5, 4.0, 3.9]  # horizontal faces of the column (barrels keep clear of them at rest)
    while yy < top - 4:
        k += 1; planes += [yy - 0.1, yy, yy + 0.1]
        if k % 2:  # glass section
            hh = min(rg.uniform(3, 7), top - 4 - yy); ctx.add(f"{n}_Glass_{k:02d}", "cylinder", [0, yy - 0.1, 0], [2 * r, hh + 0.2, 2 * r], s.get("material", "glass"), g, sections=sec, collision=True, double_sided=True, tube=True, outline=False, **st)
        else:
            hh = min(rg.uniform(1.0, 3.5), top - 4 - yy); ctx.add(f"{n}_Drum_{k:02d}", "cylinder", [0, yy, 0], [2 * r * 1.12, hh, 2 * r * 1.12], "structure_b" if k % 4 else "trim", g, sections=sec,
                                                                    hole=round(r * 0.8, 3), hole_res=16, **st)  # Stage 34: a ring - the liquid runs on through it
            if rg.random() < 0.6 and hh > 0.6:  # set into the drum (centre on the flat face's plane: never floating off a corner)
                ctx.add(f"{n}_Red_{k:02d}", "box", [0, yy + hh / 2 - 0.15, r * 1.12 * math.cos(math.pi / sec)], [0.6, 0.3, 0.3], "glow", g, collision=False, outline=False, **st)
        yy += hh; planes += [yy - 0.1, yy, yy + 0.1]
    ctx.add(n + "_Neck", "cylinder", [0, yy, 0], [2 * r * 1.05, top - 2.5 - yy, 2 * r * 1.05], "structure_b", g, sections=sec, hole=round(r * 0.8, 3), hole_res=16, **st)
    ctx.add(n + "_Capital", "frustum", [0, top - 2.5, 0], [2 * r * 2.0, 2.5, 2 * r * 2.0], "structure_b", g, sections=sec, bottom_scale=0.55, hole=round(r * 0.8, 3), hole_res=16,
            collision=False, **st)  # the pipe carries on up into the roof
    if s.get("barrels", True): tube_barrels(ctx, n, g, r, top, rg, planes + [top - 2.5])


TUBE_SPACING, TUBE_SPEED = 7.0, 9.0  # every column's barrels share one loop (one moving mobile group, one effect)


def tube_barrels(ctx, n, g, r, top, rg, planes=()):
    """Stage 43: toxic barrels shooting up a column's bore (effect "tube_travel": every target moves up by
    (t * speed) mod spacing, then snaps back - the train looks endless). The lowest barrel starts hidden inside the plinth
    (below the glass), the top one leaves out of sight inside the capital / roof. Slime-green body, three dark hoops;
    visual only, mobile group "Tube_Barrels" (2 draw calls for all of them)."""
    rb = round(min(r * 0.5, 1.3), 3); h = round(rb * 1.7, 2); S = TUBE_SPACING
    mv = dict(collision=False, outline=False, travel=True, mobile={"group": "Tube_Barrels"})
    HO = (0.06, 0.47, 0.88)
    def train(y0):
        ys = [y0]
        while ys[-1] + S < top - 2.5: ys.append(ys[-1] + S)
        return ys
    def faces(y): return [y, y + h] + [y + h * f - 0.09 + d for f in HO for d in (0.0, 0.18)]
    y0 = rg.uniform(0.3, 3.0 - h)  # inside the plinth, under the glass (3.9)
    for i in range(41):  # slide the whole train (spacing stays exact) until no barrel face is level with a column face at rest
        y = round(y0 + 0.037 * ((i + 1) // 2) * (1 if i % 2 else -1), 3)
        if all(abs(a - b) > 0.03 for yk in train(y) for a in faces(yk) for b in planes): break
    k = 0
    while True:
        k += 1; b = f"{n}_Barrel_{k}"
        ctx.add(b, "cylinder", [0, y, 0], [2 * rb, h, 2 * rb], "hazard", g, sections=10, **mv)
        for j, f in enumerate(HO):  # hoops proud of the body by 6 cm, never level with its ends
            ctx.add(f"{b}_Hoop_{j + 1}", "cylinder", [0, round(y + h * f - 0.09, 3), 0], [2 * rb + 0.12, 0.18, 2 * rb + 0.12], "frame", g, sections=10, **mv)
        if y + S >= top - 2.5: break  # this one leaves the hall inside the capital
        y += S


@structure("rock_face", pad=False)
def rock_face(ctx, s, x, y, z, yaw):
    """Raw cave rock the factory was built into (from/to along a wall, "height", "depth"): a few jagged cliff slabs
    of different heights and depths, buried in the slime. Visual only."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); H = float(s.get("height", 20)); D = float(s.get("depth", 5))
    import random as _r
    rg = _r.Random(n); g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw - 90, 0]); u = -L / 2; k = 0
    while u < L / 2 - 1:
        k += 1; sw = min(rg.uniform(8, 16), L / 2 - u); hh = H * rg.uniform(0.6, 1.0); dd = D * rg.uniform(0.6, 1.0)
        ctx.add(f"{n}_Slab_{k:02d}", "cliff", [u + sw / 2, 0, 0], [sw + 1.5, hh, dd], s.get("material", "rock"), g, seed=rg.randrange(1 << 20), step=3.5,
                collision=False, mobile={"static": True})
        u += sw
