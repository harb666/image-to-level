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
    base = float(s.get("base", 3.0)); gh = H * 0.5 + (3.0 - base); uh = max(1.5, H - base - 1.0 - gh - 1.0 - 0.8)  # Stage 73: "base" = plinth height (a low one gives the glass its height)
    ctx.add(n + "_Plinth", "cylinder", [0, y0, 0], [D + 1.2, base - y0, D + 1.2], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_BandLow", "cylinder", [0, base, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    ctx.add(n + "_Glass", "cylinder", [0, base + 0.9, 0], [D, gh + 0.2, D], s.get("material", "glass"), g, sections=seg, collision=True, double_sided=True, tube=True,
            bubble_range=[0.78, round(gh - 0.75, 3)], **st)  # see-through: bubbles rise inside (nozzle tops -> under the hood); ends sunk 10 cm into the bands
    ctx.add(n + "_BandMid", "cylinder", [0, base + 1.0 + gh, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    _vat_insides(ctx, n, g, D, base + 1.0, base + 1.0 + gh, seg, st)
    yu = base + 2.0 + gh
    ctx.add(n + "_Body", "cylinder", [0, yu, 0], [D + 0.3, uh, D + 0.3], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_Cap", "cylinder", [0, yu + uh, 0], [D + 0.9, 0.8, D + 0.9], "trim", g, sections=seg, collision=False, **st)
    if s.get("banner", True) and uh > 3:  # banner on the side facing the hall centre
        bw = min(3.0, D * 0.4); r = (D + 0.3) / 2 * math.cos(math.pi / seg) + 0.05
        ctx.add(n + "_Banner", "panel", [0, yu + uh * 0.08, r], [bw, uh * 0.8, 0], "accent", g, collision=False, outline=False, **st)


def _vat_insides(ctx, n, g, D, yb, yt, seg, st):
    """Stage 48: what the glass shows at its ends. Bottom: a machined diffuser drum with a perforated grate, a red-lit ring
    and six bubble nozzles round a centre one (the bubbles start at their tops). Top: a funnel hood hanging from the band
    with a vent grate where the bubbles end. Visual only; every face a few cm off its neighbours."""
    v = dict(collision=False, **st); w = dict(v, outline=False)
    ctx.add(n + "_Diffuser", "cylinder", [0, yb - 0.03, 0], [D * 0.86, 0.38, D * 0.86], "machine", g, sections=seg, **v)
    ctx.add(n + "_DiffuserRing", "cylinder", [0, yb + 0.32, 0], [D * 0.8, 0.07, D * 0.8], "glow", g, sections=seg, hole=round(D * 0.4 * math.cos(math.pi / seg) - 0.08, 3), hole_res=seg, **w)
    ctx.add(n + "_DiffuserGrate", "cylinder", [0, yb + 0.31, 0], [D * 0.7, 0.09, D * 0.7], "grate", g, sections=seg, **w)
    for k in range(7):  # nozzles: six on a ring (radius 0.22 D) + the centre one
        a = math.radians(60 * k); r = 0.0 if k == 6 else D * 0.22
        ctx.add(f"{n}_Nozzle_{k + 1}", "frustum", [math.cos(a) * r, yb + 0.36, math.sin(a) * r], [0.18, 0.32, 0.18], "frame", g, sections=6, bottom_scale=1.7, **w)  # tapered spout
    ctx.add(n + "_Hood", "frustum", [0, yt - 0.75, 0], [D * 0.88, 0.78, D * 0.88], "machine", g, sections=seg, bottom_scale=0.6, **v)
    ctx.add(n + "_HoodGrate", "cylinder", [0, yt - 0.79, 0], [D * 0.88 * 0.6 - 0.12, 0.07, D * 0.88 * 0.6 - 0.12], "grate", g, sections=seg, **w)
    for k in range(4):  # ribs down the hood's sloped face
        a = math.radians(45 + 90 * k); r = D * 0.44 * 0.8
        ctx.add(f"{n}_HoodRib_{k + 1}", "box", [math.cos(a) * r, yt - 0.7, math.sin(a) * r], [0.12, 0.68, D * 0.18], "frame", g, [0, -math.degrees(a) + 90, 0], **w)


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
    portal = bool(s.get("portal")) and op  # Stage 59: armoured alien portal round an open doorway (user reference)
    if op:  # frame as three bars round the opening + the dark corridor beyond
        for k, sd in enumerate((-1, 1)): ctx.add(f"{n}_Jamb_{k + 1}", "box", [sd * (W / 2 + fw / 2), 0, 0], [fw, H + 1.0, D], "structure_b", g, **st)
        ctx.add(n + "_Head", "box", [0, H, 0], [W, 1.0, D], "structure_b", g, **st)
        roles = ctx.spec.get("materials", {}).get("roles", {}); atl = (roles.get("accent") or {}).get("atlas") or {}
        if s.get("target"): ctx.add(n + "_Dark", "panel", [0, 0.02, -D / 2 + 0.05], [W, H, 0], "accent" if "void" in atl else "void", g, uv_region="void", collision=False, outline=False, **st)
    else: ctx.add(n + "_Frame", "box", [0, 0, 0], [W + 1.6, H + 1.0, D], "structure_b", g, **st)
    if portal: _portal(ctx, n, g, W, H, s, x, y, z, yaw)
    for k, sd in enumerate(() if portal else (-1, 1)):
        lx = sd * (W * 0.75 + fw + 0.1) if op else sd * (W / 4 + 0.02)  # open: slid aside along the wall
        ctx.add(f"{n}_Leaf_{k + 1}", "box", [lx, 0, D / 2 + 0.12], [W / 2 - 0.08, H, 0.24], "wall", g, collision=op, **st)
        ctx.add(f"{n}_Stripe_{k + 1}", "box", [lx, 0.6, D / 2 + 0.25], [W / 2 - 0.3, 0.8, 0.04], "stripe", g, collision=False, outline=False, **st)
    if not op: ctx.add(n + "_Seam", "box", [0, 0.3, D / 2 + 0.26], [0.12, H - 0.6, 0.04], "glow", g, collision=False, outline=False, **st)
    if not portal: ctx.add(n + "_Warning", "box", [0, H + 0.2, D / 2 + 0.1], [1.4, 0.4, 0.2], "glow", g, collision=False, outline=False, **st)
    if op and s.get("target"):
        fx, fz = A_local(0, D / 2 + 0.9, yaw); r = min(W / 2 - 0.3, 2.5)
        ctx.exits.append(dict(id=n + "_Exit", type="level_exit", target=s["target"], shape="cylinder", center=[round(x + fx, 3), round(y + 1.6, 3), round(z + fz, 3)],
                              radius=round(r, 3), height=3.0, note="walking through the open door loads the next level (Construct Error: handle in the level_exit trigger)"))
        ctx.notes.append(f"{n}: open exit door -> {s['target']}")
    else: ctx.notes.append(f"{n}: {'open' if op else 'sealed'} blast door ({W} x {H} m)")


def _portal(ctx, n, g, W, H, s, x, y, z, yaw):
    """Stage 59: the user's doorway reference, sized to the opening (W x H, door floor at the group origin, local +z
    into the room, wall face at z = -0.3): an armoured pillar each side - a pointed back plate, a front plate, slanted
    red light panels, a side fin with a light slit and a red strip on the jamb - a header with angled corners, two
    recessed panels and an inverted red trapezoid light, a red lamp hanging under it, hazard-striped plates low on the
    wall. All convex "prism" plates (outline in the door plane); visual only. Max height H + 3.4 (fits under a gallery).
    "laser_gate": {...} also closes the doorway with red laser beams (see _laser_gate)."""
    st = dict(collision=False, mobile={"static": True}); w2 = W / 2; F = lambda pts, sd: [[sd * px, py] for px, py in pts]
    P = lambda nm, pts, z0, dep, mat, sd=1: ctx.add(nm, "prism", [0, 0, z0], [3, 3, dep], mat, g, poly=F(pts, sd), **(dict(st, outline=False) if mat == "glow" else st))
    k = H / 6.0  # the reference proportions were drawn for a 6 m door
    Y = lambda v: round(v * k, 3); X = lambda v: round(w2 + v, 3)  # x measured out from the jamb, y scaled with the door
    for i, sd in enumerate((-1, 1)):
        side = "LR"[i]
        P(f"{n}_Pillar_{side}", [(X(0.1), 0), (X(3.2), 0), (X(3.6), Y(1.0)), (X(3.6), Y(7.6)), (X(2.1), Y(9.3)), (X(0.1), Y(8.2))], -0.5, 1.6, "structure_b", sd)
        P(f"{n}_Plate_{side}", [(X(0.35), Y(0.35)), (X(2.9), Y(0.35)), (X(3.25), Y(1.15)), (X(3.25), Y(7.35)), (X(2.0), Y(8.75)), (X(0.35), Y(7.85))], 1.05, 0.25, "frame", sd)
        for j, pts in enumerate(([(X(0.9), Y(3.6)), (X(2.6), Y(4.1)), (X(2.6), Y(6.9)), (X(0.9), Y(6.3))],
                                 [(X(0.9), Y(0.9)), (X(2.6), Y(0.9)), (X(2.6), Y(3.0)), (X(0.9), Y(3.35))],
                                 [(X(1.3), Y(7.2)), (X(2.5), Y(7.5)), (X(2.0), Y(8.4))])):
            P(f"{n}_Panel_{side}{j + 1}", pts, 1.27, 0.08, "glow", sd)
        P(f"{n}_Fin_{side}", [(X(3.6), Y(0.5)), (X(4.9), Y(1.3)), (X(4.9), Y(5.9)), (X(3.6), Y(6.9))], -0.5, 1.0, "structure_b", sd)
        P(f"{n}_FinLight_{side}", [(X(3.95), Y(1.9)), (X(4.55), Y(2.25)), (X(4.55), Y(5.3)), (X(3.95), Y(5.75))], 0.47, 0.08, "glow", sd)
        ctx.add(f"{n}_JambLight_{side}", "box", [sd * (w2 + 0.08), Y(0.8), 0.45], [0.06, Y(4.4), 0.6], "glow", g, collision=False, outline=False, mobile={"static": True})
        sx = sd * (w2 + 6.4)  # hazard-striped plate low on the wall beside the pillar
        ctx.add(f"{n}_StripePlate_{side}", "box", [sx, 1.0, -0.3], [3.2, 1.1, 0.12], "frame", g, collision=False, outline=False, mobile={"static": True})
        ctx.add(f"{n}_StripeBand_{side}", "box", [sx, 1.15, -0.2], [2.8, 0.8, 0.04], "stripe", g, collision=False, outline=False, mobile={"static": True})
    hw = w2 + 1.0
    P(n + "_Header", [(-w2 - 0.1, Y(5.96)), (w2 + 0.1, Y(5.96)), (hw, Y(6.9)), (hw, Y(8.6)), (hw - 0.8, Y(9.35)), (-hw + 0.8, Y(9.35)), (-hw, Y(8.6)), (-hw, Y(6.9))],
      -0.5, 1.3, "structure_b")
    for sd in (-1, 1):
        P(f"{n}_Recess_{'LR'[sd > 0]}", [(2.9, Y(6.6)), (w2 - 0.5, Y(6.6)), (w2 - 0.5, Y(8.7)), (2.9, Y(8.7))], 0.77, 0.1, "frame", sd)
    P(n + "_TrapFrame", [(-1.8, Y(6.35)), (1.8, Y(6.35)), (2.5, Y(8.95)), (-2.5, Y(8.95))], 0.77, 0.14, "frame")
    P(n + "_TrapLight", [(-1.25, Y(6.8)), (1.25, Y(6.8)), (1.85, Y(8.6)), (-1.85, Y(8.6))], 0.88, 0.07, "glow")
    ctx.add(n + "_LampStem", "box", [0, Y(5.96) - 0.71, 0.45], [0.3, 0.76, 0.3], "frame", g, collision=False, outline=False, mobile={"static": True})
    ctx.add(n + "_LampHousing", "box", [0, Y(5.96) - 1.16, 0.45], [1.6, 0.5, 0.7], "frame", g, collision=False, mobile={"static": True})
    ctx.add(n + "_LampLight", "box", [0, Y(5.96) - 1.04, 0.79], [1.1, 0.26, 0.06], "glow", g, collision=False, outline=False, mobile={"static": True})
    hx, hz = A_local(0, 0.6, yaw)
    ctx.portals = getattr(ctx, "portals", []) + [dict(id=n, center=[x + hx, y, z + hz], half=[hw + 4.0, Y(9.35) + 0.1, 2.5], yaw=yaw)]
    if s.get("laser_gate"): _laser_gate(ctx, n, g, W, H, s["laser_gate"], x, y, z, yaw)


def _laser_gate(ctx, n, g, W, H, lg, x, y, z, yaw):
    """Stage 59: the doorway starts closed by a laser gate - horizontal red beams from jamb to jamb plus emitter strips,
    role "laser", own mobile group (so the game can hide it). Visual only in the level (navigation treats the doorway as
    open); level.json "gates" tells the game to put a blocker there and to open it when lg["opens_on"] is met (e.g. the
    waves of an encounter are cleared) - apply_mobile.gd: open_gate(id) / signal gate_opened."""
    gid = lg.get("id", n + "_Laser"); mv = dict(collision=False, outline=False, mobile={"group": gid}); nb = int(lg.get("beams", 7)); w2 = W / 2
    top = min(H - 0.4, 5.8)
    for i in range(nb):
        yb = round(0.45 + (top - 0.45) * i / max(1, nb - 1), 3)
        ctx.add(f"{gid}_Beam_{i + 1}", "cylinder", [-w2 - 0.05, yb, 0.0], [0.09, W + 0.1, 0.09], ctx.role("laser"), g, [0, 0, -90], sections=6, **mv)
    for sd in (-1, 1):
        ctx.add(f"{gid}_Emitter_{'LR'[sd > 0]}", "box", [sd * (w2 - 0.01), 0.25, 0.0], [0.08, top, 0.22], ctx.role("laser"), g, **mv)
    bx, bz = A_local(0, 0.0, yaw)
    ctx.gates = getattr(ctx, "gates", []) + [dict(
        id=gid, group=gid, door=n, center=[round(x + bx, 3), round(y + top / 2 + 0.2, 3), round(z + bz, 3)], size=[round(W, 3), round(top + 0.4, 3), 0.6], yaw_deg=round(yaw, 2),
        closed_at_start=True, opens_on=lg.get("opens_on", {"type": "waves_cleared", "encounter": lg.get("encounter")}),
        note="Construct Error: a StaticBody3D blocker stands here while closed (apply_mobile.gd); call open_gate(id) when the "
             "encounter's last wave is cleared - the beams fade out, the blocker goes, signal gate_opened(id).")]


@structure("conveyor", pad=False)
def conveyor(ctx, s, x, y, z, yaw):
    """Assembly-line conveyor (from/to at deck height y): belt with lit edge, side frames, end rollers, legs to the deck;
    "parcels" crates ride on it. 0.9 m high: low cover. Local +z runs along the belt."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); w = float(s.get("width", 2.0)); h = 0.9
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    ctx.add(n + "_Bed", "box", [0, 0, 0], [w, h - 0.15, L], "structure_b", g, **st)
    ctx.add(n + "_Belt", "box", [0, h - 0.15, 0], [w - 0.3, 0.12, L - 0.2], "belt" if s.get("working") else "grate", g, collision=False, **st)  # Stage 68: a working belt has its own material (it scrolls)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Side_{k + 1}", "box", [sd * (w / 2 - 0.06), h - 0.2, 0], [0.16, 0.35, L - 0.04], "frame", g, collision=False, **st)  # 2 cm proud of the bed
        ctx.add(f"{n}_Edge_{k + 1}", "box", [sd * (w / 2 + 0.01), h - 0.45, 0], [0.04, 0.1, L - 0.6], "glow", g, collision=False, outline=False, **st)
    rs = 1 if float(s.get("roller_side", -1)) > 0 else -1  # Stage 60: which local side (x) the end rollers stick out of the bed (+1 / -1)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Roller_{k + 1}", "cylinder", [0, h - 0.5, sd * (L / 2 - 0.1)], [0.5, w, 0.5], "machine", g, [0, 0, -90 * rs], sections=8, collision=False, **st)
    if s.get("working"): return _assembly_line(ctx, s, n, g, L, w, h, x, y, z, yaw)
    import random as _r
    rg = _r.Random(n); k = 0
    for zz in [(-L / 2 + 1.2 + i * 2.6) for i in range(int((L - 2) / 2.6))]:
        if rg.random() < float(s.get("parcels", 0.4)):
            k += 1; sz = rg.choice((0.7, 0.8, 0.9)); ctx.add(f"{n}_Parcel_{k:02d}", "box", [rg.uniform(-0.2, 0.2), h - 0.03, zz], [sz, sz * 0.8, sz], "accent", g, [0, rg.uniform(-20, 20), 0],
                                                                  collision=False, **st)


def _assembly_line(ctx, s, n, g, L, w, h, x, y, z, yaw):
    """Stage 61: a working assembly line. Intake machine over the start of the belt, output machine over its end (each a
    housing with a dark mouth, rubber curtain strips, hazard-striped frame, status light; hopper on the intake, vent stack
    on the output). Identical parcels ride the belt at a fixed spacing (mobile group "<id>_Parcels", effect
    "assembly_line": it slides them along by (t * speed) mod spacing - a new parcel comes out of the intake mouth as the
    last one goes into the output, both hidden inside the housings). Per station (working["stations"]: arm, task
    "add" | "inspect", "at" m from the start) every parcel carries the station's part - a glowing canister on top (add)
    or a yellow approval light on its side (inspect) - in its own group. Each part carries its parcel's number in its UVs
    (u shifted by 10 per parcel), so the shader shows the whole part at once the moment its parcel's centre reaches the
    station's arm - when the arm's canister lets go (see robot_arm "task"). Local +z runs from -> to."""
    W_ = s["working"]; st = dict(mobile={"static": True}); v = float(W_.get("speed", 1.0)); mL = float(W_.get("machine", 2.6))
    hz = h - 0.03  # parcel base (belt top)
    for e_, zc, sg in (("In", -L / 2 + mL / 2, 1), ("Out", L / 2 - mL / 2, -1)):  # sg: the side the mouth faces (+z for the intake)
        m_ = f"{n}_{e_}"; fz = zc + sg * mL / 2  # mouth face
        ctx.add(m_ + "_Housing", "box", [0, -0.03, zc - sg * 0.05], [w + 0.56, 2.33, mL + 0.1], "machine", g, **st)  # 3 cm into the deck, 10 cm past the bed end: no shared faces
        ctx.add(m_ + "_Roof", "box", [0, 2.3, zc], [w + 0.8, 0.22, mL + 0.3], "structure_b", g, collision=False, **st)
        roles = ctx.spec.get("materials", {}).get("roles", {}); atl = (roles.get("accent") or {}).get("atlas") or {}
        ctx.add(m_ + "_Mouth", "panel", [0, hz - 0.05, fz + sg * 0.02], [w - 0.1, 1.05, 0], "accent" if "void" in atl else "void", g, [0, 0 if sg > 0 else 180, 0],
                uv_region="void", collision=False, outline=False, **st)
        for j in range(7):  # rubber curtain strips hanging in the mouth (the parcels push through them)
            cx = -(w - 0.3) / 2 + (w - 0.3) * (j + 0.5) / 7
            ctx.add(f"{m_}_Strip_{j + 1}", "box", [cx, hz + 0.25, fz + sg * 0.07], [(w - 0.3) / 7 - 0.03, 0.75, 0.025], "frame", g, collision=False, outline=False, **st)
        for k_, (ox, oy, sx, sy) in enumerate(((0, hz + 1.03, w + 0.3, 0.2), (-(w / 2 + 0.05), hz - 0.05, 0.2, 1.08), (w / 2 + 0.05, hz - 0.05, 0.2, 1.08))):
            ctx.add(f"{m_}_Frame_{k_ + 1}", "box", [ox, oy, fz + sg * 0.06], [sx, sy, 0.1], "stripe", g, collision=False, outline=False, **st)
        lamp = ctx.role("glow_yellow") if e_ == "In" else "glow"
        ctx.add(m_ + "_Lamp", "box", [0, hz + 1.38, fz + sg * 0.05], [0.9, 0.22, 0.08], lamp, g, collision=False, outline=False, **st)
        for sd in (-1, 1):  # side vents
            ctx.add(f"{m_}_Vent_{'LR'[sd > 0]}", "box", [sd * (w / 2 + 0.3), 0.9, zc], [0.06, 0.9, mL * 0.6], "frame", g, collision=False, outline=False, **st)
        if e_ == "In":  # hopper feeding the intake, glowing slime in it
            ctx.add(m_ + "_Hopper", "frustum", [0, 2.5, zc], [w + 0.6, 1.1, mL - 0.4], "structure_b", g, sections=4, bottom_scale=0.55, collision=False, **st)
            ctx.add(m_ + "_HopperFill", "box", [0, 3.48, zc], [w + 0.2, 0.06, mL - 0.8], ctx.role("fall") if "fall" in roles else "glow", g, collision=False, outline=False, **st)
        else:  # vent stack with a red ring
            ctx.add(m_ + "_Stack", "cylinder", [0.35, 2.5, zc], [0.7, 1.6, 0.7], "structure_b", g, sections=8, collision=False, **st)
            ctx.add(m_ + "_StackRing", "cylinder", [0.35, 3.3, zc], [0.82, 0.18, 0.82], "glow", g, sections=8, collision=False, outline=False, **st)
    s0, s1 = mL / 2, L - mL / 2; N = max(2, int(round((s1 - s0) / float(W_.get("spacing", 2.6))))); S = (s1 - s0) / N
    PS = 0.8; mv = dict(collision=False, mobile={"group": n + "_Parcels"})
    for i in range(N):
        ctx.add(f"{n}_Parcel_{i + 1:02d}", "box", [0, hz, -L / 2 + s0 + i * S], [PS, PS * 0.8, PS], "accent", g, **mv)
    stations = []
    for k_, stn in enumerate(W_.get("stations", [])):
        ig = f"{n}_Item{k_ + 1}"
        for i in range(N):
            zp = -L / 2 + s0 + i * S; it = dict(collision=False, outline=False, uv_shift=10 * (i + 1), mobile={"group": ig})  # parcel number in the UVs (10 per parcel)
            if stn["task"] == "add":  # glowing canister set into the lid (base 2 cm under it)
                ctx.add(f"{ig}_{i + 1:02d}", "cylinder", [0, hz + PS * 0.8 - 0.02, zp], [0.5, 0.5, 0.5], ctx.role("fall") if "fall" in ctx.spec.get("materials", {}).get("roles", {}) else "glow", g, sections=8, **it)
            else:  # approval light on both sides of the parcel (1 cm proud)
                for sd in (-1, 1):
                    ctx.add(f"{ig}_{i + 1:02d}_{'LR'[sd > 0]}", "box", [sd * (PS / 2 + 0.005), hz + PS * 0.55, zp], [0.02, 0.12, PS * 0.7], ctx.role("glow_yellow"), g, **it)
        stations.append(dict(stn, group=ig))
    ux, uz = math.sin(math.radians(yaw)), math.cos(math.radians(yaw)); ax_, az_ = x - ux * L / 2, z - uz * L / 2
    ctx.assembly = getattr(ctx, "assembly", {}); ctx.assembly[n] = dict(start=[round(ax_, 3), round(y, 3), round(az_, 3)], axis=[round(ux, 5), 0.0, round(uz, 5)], speed=v,
                                                                      spacing=round(S, 4), s0=round(s0, 3), parcels=N, stations=stations, top=round(y + hz + PS * 0.8, 3))
    ctx.notes.append(f"{n}: working assembly line - {N} parcels {S:.2f} m apart at {v} m/s, {len(stations)} station(s)")


@structure("robot_arm", pad=False)
def robot_arm(ctx, s, x, y, z, yaw):
    """Industrial robot arm on a deck (Stage 33, from the user's reference): tapered base and turret, shoulder and elbow
    joints with glowing red discs, angular tapered links with red light strips on both sides, a spike on the elbow,
    sagging hose cables, a tapered wrist housing with a red diamond light and a three-finger claw with lit fingers.
    Pose "pose" deg [shoulder, elbow] (default from the id so neighbours differ). Solid base, visual arm."""
    n = s["id"]; sc = float(s.get("scale", 1.0)); st = dict(mobile={"static": True})
    rch = s.get("reach")  # Stage 61: [x, y, z] world point the claw tips rest at (the arm turns to face it, pose solved)
    if rch: yaw = math.degrees(math.atan2(rch[0] - x, rch[2] - z))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    task = s.get("task") if rch else None  # "add" | "inspect": the upper arm moves (own mobile group) - effect "assembly_line"
    vis = dict(collision=False, **(dict(mobile={"group": n + "_Upper"}) if task else st))
    import random as _r
    rg = _r.Random(n); sh, el = s.get("pose", [rg.uniform(20, 55), rg.uniform(40, 100)])
    if s.get("pedestal"):  # sunk 1.2 m deeper than asked: it stands IN what is below (liquid / deck), never on its surface
        pd = float(s["pedestal"]) + 1.2; ctx.add(n + "_Pedestal", "cylinder", [0, -pd, 0], [1.3 * sc, pd, 1.3 * sc], "structure_b", g, sections=10, **st)
    if rch:  # two-link IK, elbow up: wrist joint = claw tips + 2.674 sc (the claw hangs straight down under it)
        l1, l2, py_ = 2.7 * sc, 2.2 * sc, 1.6 * sc; dz = math.hypot(rch[0] - x, rch[2] - z); dy = rch[1] + 2.674 * sc - y - py_
        D = min(math.hypot(dz, dy), l1 + l2 - 0.01); phi = math.atan2(dz, dy); al = math.acos((l1 * l1 + D * D - l2 * l2) / (2 * l1 * D))
        a1 = phi - al; ey_, ez_ = l1 * math.cos(a1), l1 * math.sin(a1); a2 = math.atan2(dz - ez_, dy - ey_)
        sh, el = math.degrees(a1), math.degrees(a2 - a1)
        if math.hypot(dz, dy) > l1 + l2: ctx.notes.append(f"{n}: reach point out of range ({math.hypot(dz, dy):.2f} > {l1 + l2:.2f} m) - arm fully stretched")
    else: sh, el = _clear_pose(ctx, n, (x, y, z), yaw, sc, sh, el)
    ctx.add(n + "_Base", "frustum", [0, 0, 0], [1.9 * sc, 0.6 * sc, 1.9 * sc], "structure_b", g, sections=8, bottom_scale=1.25, **st)
    vst = dict(collision=False, **(dict(mobile={"group": n + "_Upper"}) if task else st))  # Stage 65: a working arm's turret turns with it
    ctx.add(n + "_Turret", "frustum", [0, 0.6 * sc, 0], [1.2 * sc, 1.0 * sc, 1.2 * sc], "structure_b", g, sections=8, bottom_scale=1.2, **vst)
    face_light(ctx, n + "_TurretLight", g, (0, 0.6 * sc, 0), 8, 0.6 * sc, 0.72 * sc, 1.0 * sc, 90, 0.15 * sc, 0.85 * sc, 0.14 * sc, vst)
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
    for k, sd in enumerate((-1, 1) if not task else ()):  # hose cables: link 1 side -> wrist, sagging (Stage 67: not on working arms - a cable across a moving joint would stretch)
        p0 = (sd * 0.3 * sc, py + math.cos(a1) * l1 * 0.45, math.sin(a1) * l1 * 0.45); p1 = (sd * 0.25 * sc, wy - 0.2 * sc, wz - 0.3 * sc)
        cable(ctx, f"{n}_Hose_{k + 1}", g, p0, p1, 0.6 * sc, 0.1 * sc, vis)
    if task:  # Stage 61/63: what the moving arm carries (rotates with it; the effect shows / hides it in time with the parcels)
        tip = cyl - 0.24 * sc - 1.58 * sc; ctx.assembly_arms = getattr(ctx, "assembly_arms", {}); roles = ctx.spec.get("materials", {}).get("roles", {})
        fall = ctx.role("fall") if "fall" in roles else "glow"; tipw = [x + math.sin(math.radians(yaw)) * wz, y + tip, z + math.cos(math.radians(yaw)) * wz]
        extra = {}
        if task == "add":  # a canister held between the finger tips (radius 0.26: the tips touch it)
            ctx.add(n + "_Held", "cylinder", [0, tip + 0.01, wz], [0.52, 0.5, 0.52], fall, g, sections=8, collision=False, outline=False, mobile={"group": n + "_Held"})
            # Stage 63: the bin it takes them from - beside the arm, the same reach away, turned "bin_yaw" deg about the base
            psi = math.radians(float(s.get("bin_yaw", 90))); rx, rz = tipw[0] - x, tipw[2] - z
            bx, bz = x + rx * math.cos(psi) + rz * math.sin(psi), z - rx * math.sin(psi) + rz * math.cos(psi)
            bt = float(s.get("bin_top", rch[1] - 0.5)); bst = dict(mobile={"static": True}); bg = ctx.add(n + "_Bin", "group", [round(bx, 3), 0, round(bz, 3)])
            ctx.add(n + "_Bin_Body", "cylinder", [0, bt - 1.1, 0], [1.6, 1.1, 1.6], "structure_b", bg, sections=10, hole=0.62, hole_res=10, **bst)
            ctx.add(n + "_Bin_Rim", "cylinder", [0, bt - 0.04, 0], [1.72, 0.12, 1.72], "glow", bg, sections=10, hole=0.66, hole_res=10, collision=False, outline=False, **bst)
            ctx.add(n + "_Bin_Band", "cylinder", [0, bt - 0.62, 0], [1.66, 0.3, 1.66], "stripe", bg, sections=10, hole=0.7, hole_res=10, collision=False, outline=False, **bst)
            ctx.add(n + "_Bin_Void", "cylinder", [0, bt - 1.09, 0], [1.26, 0.05, 1.26], "accent" if "void" in ((roles.get("accent") or {}).get("atlas") or {}) else "void", bg,
                    sections=10, uv_region="void", collision=False, outline=False, **bst)  # black floor deep inside: reads bottomless
            for k_ in range(5):  # canisters waiting in it (tops well under the claw's reach)
                a_ = math.radians(72 * k_ + 18); rr_ = 0.0 if k_ == 4 else 0.36
                ctx.add(f"{n}_Bin_Can_{k_ + 1}", "cylinder", [math.cos(a_) * rr_, bt - 1.06 - 0.01 * (k_ % 2), math.sin(a_) * rr_], [0.34 if k_ < 4 else 0.46, 0.48, 0.34 if k_ < 4 else 0.46],
                        fall, bg, sections=8, collision=False, outline=False, **bst)
            ped = (bt - 1.1) + 1.4  # down into the slime
            ctx.add(n + "_Bin_Post", "cylinder", [0, bt - 1.1 - ped, 0], [0.7, ped + 0.03, 0.7], "structure_b", bg, sections=8, **bst)
            extra = dict(bin_yaw=round(float(s.get("bin_yaw", 90)), 3), bin_top=round(bt, 3))
        else:  # scanner: a yellow lens under the wrist, a scan beam, and a laser frame that sweeps up and down the parcel
            ctx.add(n + "_Lens", "cylinder", [0, cyl - 0.36 * sc, wz], [0.36 * sc, 0.13 * sc, 0.36 * sc], ctx.role("glow_yellow"), g, sections=8, collision=False, outline=False,
                    mobile={"group": n + "_Upper"})
            ctx.add(n + "_Scan", "frustum", [0, tip + 1.56 * sc, wz], [0.95, 1.56 * sc + 0.42, 0.95], ctx.role("scan"), g, [180, 0, 0], sections=4, bottom_scale=0.12,
                    collision=False, outline=False, double_sided=True, mobile={"group": n + "_Scan"})
            ry = float(s.get("ring_base", rch[1] - 0.9 - 0.62))  # parcel base on the belt
            rg_ = ctx.add(n + "_Ring", "group", [round(tipw[0], 3), 0, round(tipw[2], 3)], rot=[0, yaw, 0])
            for k_, (ox, oz, sx, sz) in enumerate(((0, 0.55, 1.16, 0.05), (0, -0.55, 1.16, 0.05), (0.55, 0, 0.05, 1.06), (-0.55, 0, 0.05, 1.06))):
                ctx.add(f"{n}_Ring_{k_ + 1}", "box", [ox, ry + 0.04, oz], [sx, 0.05, sz], ctx.role("glow_yellow"), rg_, collision=False, outline=False, mobile={"group": n + "_Ring"})
            extra = dict(ring=[n + "_Ring"], ring_travel=0.6)
        for o in ctx.objects:  # the moving arm in 3 materials (hull, lights, ink): fewer draw calls
            if (o.get("mobile") or {}).get("group") == n + "_Upper" and o.get("material") in ("machine", "frame"): o["material"] = "structure_b"
        # Stage 65: a skeleton - turret yaw, shoulder, elbow, wrist pitch, claw twist, 3 fingers - every part skinned to one joint
        cy_, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        Wp = lambda lx, ly, lz: [round(x + lx * cy_ + lz * sy_, 4), round(y + ly, 4), round(z - lx * sy_ + lz * cy_, 4)]
        Wv = lambda lx, lz: [round(lx * cy_ + lz * sy_, 5), 0.0, round(-lx * sy_ + lz * cy_, 5)]
        J = lambda k: f"{n}_J{k}"; hx = Wv(1, 0); up = [0.0, 1.0, 0.0]; cyf = cyl - 0.24 * sc
        joints = [dict(name=J("Yaw"), parent=None, pivot=Wp(0, 0.6 * sc, 0), axis=up), dict(name=J("Shoulder"), parent=J("Yaw"), pivot=Wp(0, py, 0), axis=hx),
                  dict(name=J("Elbow"), parent=J("Shoulder"), pivot=Wp(0, ey, ez), axis=hx), dict(name=J("Wrist"), parent=J("Elbow"), pivot=Wp(0, wy, wz), axis=hx),
                  dict(name=J("Twist"), parent=J("Wrist"), pivot=Wp(0, wy, wz), axis=up)]
        for k in range(3):  # each finger hinges at its root on the collar, about the tangent (+ = opens outwards)
            f = math.radians(120 * k); ox, oz = math.sin(f), math.cos(f)
            joints.append(dict(name=J(f"Finger{k + 1}"), parent=J("Twist"), pivot=Wp(ox * 0.16 * sc, cyf, wz + oz * 0.16 * sc), axis=Wv(-oz, ox)))
        part = (("Turret", "Yaw"), ("Shoulder", "Shoulder"), ("Link1", "Shoulder"), ("Elbow", "Elbow"), ("Spike", "Elbow"), ("Link2", "Elbow"), ("Wrist", "Wrist"),
                ("Light", "Wrist"), ("Collar", "Twist"), ("Lens", "Twist"), ("Held", "Twist"), ("Scan", "Twist"), ("Finger_1", "Finger1"), ("Finger_2", "Finger2"), ("Finger_3", "Finger3"))
        grp = [n + "_Upper"] + ([n + "_Held"] if task == "add" else [n + "_Scan"])
        for o in ctx.objects:
            if (o.get("mobile") or {}).get("group") not in grp: continue
            sfx = o["name"][len(n) + 1:]
            o["mobile"] = dict(o["mobile"], joint=J(next(j for p_, j in part if sfx.startswith(p_))))  # every part rigid on one joint (own dict: the parts share one)
        ctx.skeletons = getattr(ctx, "skeletons", {}); ctx.skeletons[n] = dict(groups=grp, joints=joints)
        rig = dict(joints=joints, l1=round(l1, 4), l2=round(l2, 4), a1=round(a1, 6), a2=round(a2, 6), wrist=[0.0, round(wy - py, 4), round(wz, 4)], yaw0=round(math.radians(yaw), 6), seed=round(_r.Random(n + "rig").random(), 4))
        ctx.assembly_arms[n] = dict(task=task, rig=rig, pivot=[round(x, 3), round(y + py, 3), round(z, 3)], hinge=[round(v_, 5) for v_ in (math.cos(math.radians(yaw)), 0.0, -math.sin(math.radians(yaw)))],
                                    tip=[round(v_, 3) for v_ in tipw], groups=[n + "_Upper"], held=[n + "_Held"] if task == "add" else [],
                                    scan=[n + "_Scan"] if task == "inspect" else [], **extra)


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
    out = s.get("spine_out")  # Stage 58: "to" / "from" - the spine runs on past that end, turns down and sinks into the slime
    ext = float(s.get("spine_ext", 6.0)) if out else 0.0; z0 = -L / 2 - (ext if out == "from" else 0.0)
    ctx.add(n + "_Spine", "cylinder", [0, h + 0.6, z0], [1.2, L + ext, 1.2], "pipe", g, [90, 0, 0], sections=8, **st)
    if out:
        ze = (L / 2 + ext) if out == "to" else (-L / 2 - ext); yb = float(s.get("spine_drop_y", 0.2)) - y  # bottom below the liquid surface: it vanishes into it
        ctx.add(n + "_SpineJoint", "box", [0, h + 0.6 - 0.84, ze], [1.68, 1.68, 1.68], "frame", g, **st)  # corner block (like pipe-run junctions)
        ctx.add(n + "_SpineDrop", "cylinder", [0, yb, ze], [1.2, h + 0.6 - yb, 1.2], "pipe", g, sections=8, **st)  # top ends inside the block; corroded at the slime line
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
    yy, k = 4.0, 0
    while yy < top - 4:
        k += 1
        if k % 2:  # glass section
            hh = min(rg.uniform(3, 7), top - 4 - yy); ctx.add(f"{n}_Glass_{k:02d}", "cylinder", [0, yy - 0.1, 0], [2 * r, hh + 0.2, 2 * r], s.get("material", "glass"), g, sections=sec, collision=True, double_sided=True, tube=True, outline=False,
                                                              bubbles=False, **st)  # Stage 49: pods, not bubbles, in the columns
        else:
            hh = min(rg.uniform(1.0, 3.5), top - 4 - yy); ctx.add(f"{n}_Drum_{k:02d}", "cylinder", [0, yy, 0], [2 * r * 1.12, hh, 2 * r * 1.12], "structure_b" if k % 4 else "trim", g, sections=sec,
                                                                    hole=round(r * 0.8, 3), hole_res=16, **st)  # Stage 34: a ring - the liquid runs on through it
            if rg.random() < 0.6 and hh > 0.6:  # set into the drum (centre on the flat face's plane: never floating off a corner)
                ctx.add(f"{n}_Red_{k:02d}", "box", [0, yy + hh / 2 - 0.15, r * 1.12 * math.cos(math.pi / sec)], [0.6, 0.3, 0.3], "glow", g, collision=False, outline=False, **st)
        yy += hh
    ctx.add(n + "_Neck", "cylinder", [0, yy, 0], [2 * r * 1.05, top - 2.5 - yy, 2 * r * 1.05], "structure_b", g, sections=sec, hole=round(r * 0.8, 3), hole_res=16, **st)
    ctx.add(n + "_Capital", "frustum", [0, top - 2.5, 0], [2 * r * 2.0, 2.5, 2 * r * 2.0], "structure_b", g, sections=sec, bottom_scale=0.55, hole=round(r * 0.8, 3), hole_res=16,
            collision=False, **st)  # the pipe carries on up into the roof
    if s.get("pods", s.get("barrels", True)): tube_pod(ctx, n, g, r, top, rg)


POD_SPEED = 28.0  # m/s up the bore (Stage 49)


def tube_pod(ctx, n, g, r, top, rg):
    """Stage 49: one capsule pod (the ceiling lamp-pod model - frame cap and base, clear shell, three cage bars - but full
    of glowing slime) launched up the column's bore every few seconds (effect "tube_pods", category "launch"): it waits
    hidden in the plinth, shoots up at POD_SPEED and vanishes into the capital / roof. Each column has its own period and
    phase (never in step). Own mobile group "<id>_Pod" (frame / glass_clear / hazard nodes) so it moves on its own."""
    rp = round(min(r * 0.5, 1.3), 3); h = round(rp * 2.0, 3); bot = round(3.85 - h - 0.35, 3)  # pod top (cap) 15 cm under the plinth top: hidden at rest
    mv = dict(collision=False, outline=False, launch=True, mobile={"group": n + "_Pod"}); nm = n + "_Pod"
    ctx.add(nm + "_Cap", "cylinder", [0, bot + h - 0.1, 0], [2 * rp + 0.3, 0.45, 2 * rp + 0.3], "frame", g, sections=6, **mv)
    ctx.add(nm + "_Shell", "cylinder", [0, bot + 0.2, 0], [2 * rp, h - 0.25, 2 * rp], ctx.role("glass_clear"), g, sections=6, double_sided=True, **mv)
    ctx.add(nm + "_Fluid", "cylinder", [0, bot + 0.27, 0], [2 * rp - 0.24, h - 0.42, 2 * rp - 0.24], "hazard", g, sections=6, **mv)  # the green inside
    ctx.add(nm + "_Base", "cylinder", [0, bot, 0], [2 * rp + 0.2, 0.3, 2 * rp + 0.2], "frame", g, sections=6, **mv)
    for b in range(3):  # cage posts on the outside corners
        a_ = math.radians(120 * b); ctx.add(f"{nm}_Bar_{b + 1}", "box", [math.cos(a_) * (rp + 0.04), bot + 0.2, -math.sin(a_) * (rp + 0.04)], [0.14, h - 0.25, 0.14], "frame", g, [0, 120 * b, 0], **mv)
    period = round(rg.uniform(2.6, 6.2), 2)
    ctx.launches = getattr(ctx, "launches", []) + [dict(group=nm, period=period, phase=round(rg.uniform(0, period), 2), travel=round(top - 2.4 - bot, 2))]


@structure("rock_face", pad=False)
def rock_face(ctx, s, x, y, z, yaw):
    """Raw cave rock the factory was built into (from/to along a wall, "height", "depth"): a few jagged cliff slabs
    of different heights and depths, buried in the slime. Visual only."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; L = math.hypot(bx - ax, bz - az); H = float(s.get("height", 20)); D = float(s.get("depth", 5))
    import random as _r
    rg = _r.Random(n); g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw - 90, 0]); u = -L / 2; k = 0; slabs = []
    while u < L / 2 - 1:
        k += 1; sw = min(rg.uniform(8, 16), L / 2 - u); hh = H * rg.uniform(0.6, 1.0); dd = D * rg.uniform(0.6, 1.0)
        ctx.add(f"{n}_Slab_{k:02d}", "cliff", [u + sw / 2, 0, 0], [sw + 1.5, hh, dd], s.get("material", "rock"), g, seed=rg.randrange(1 << 20), step=3.5,
                collision=False, mobile={"static": True})
        slabs.append((u, u + sw, dd, hh)); u += sw
    if s.get("industrial"): _rock_industry(ctx, s, n, g, x, z, yaw - 90, L, H, D, slabs, rg)


def _rock_industry(ctx, s, n, g, x, z, gy, L, H, D, slabs, rg):
    """Stage 56 (user reference): the factory dug into the rock. Taller pointed spires in front of the slabs; slime
    trickling out of small pipe spouts set into the rock (real pours: streams, splashes, ripples); metal ledges on
    brackets with red light slits; two glass tube tanks (bubbling slime, red band, cap, elbow pipe into the rock)
    standing in the pool. Local frame of the rock group: x along the face, +z towards the room."""
    from architecture import pipe as _pipe, local as _loc
    st = dict(mobile={"static": True}); mat = s.get("material", "rock")
    front = lambda u_: next((dd / 2 for a, b, dd, _ in slabs if a <= u_ <= b), D / 2)
    top = lambda u_: next((hh for a, b, _, hh in slabs if a <= u_ <= b), H)
    used = []
    def pick(margin, lo=-L / 2 + 3, hi=L / 2 - 3):
        for _ in range(40):
            u_ = rg.uniform(lo, hi)
            if all(abs(u_ - v) > margin for v in used): used.append(u_); return u_
        return None
    for i in range(int(s.get("spires", 4))):  # pointed spires a little in front of the slabs
        u_ = rg.uniform(-L / 2 + 3, L / 2 - 3); sd = D * rg.uniform(0.35, 0.5)
        ctx.add(f"{n}_Spire_{i + 1}", "cliff", [u_, 0, front(u_) - sd / 2 + rg.uniform(0.4, 1.0)], [rg.uniform(3.0, 5.5), H * rg.uniform(0.95, 1.15), sd], mat, g,
                seed=rg.randrange(1 << 20), step=2.5, collision=False, **st)
    for i in range(int(s.get("tanks", 2))):  # glass tube tanks standing in the pool, piped into the rock
        u_ = pick(5.0)
        if u_ is None: break
        tg = ctx.add(f"{n}_Tank{i + 1}", "group", [u_, 0, front(u_) + 2.2], parent=g)
        ctx.add(f"{n}_Tank{i + 1}_Plinth", "cylinder", [0, -0.5, 0], [2.2, 3.0, 2.2], "frame", tg, sections=8, **st)
        for j, y0 in enumerate((2.4, 6.2)):
            ctx.add(f"{n}_Tank{i + 1}_Glass_{j + 1}", "cylinder", [0, y0, 0], [1.6, 3.2, 1.6], "glass", tg, sections=8, collision=True, double_sided=True, tube=True, outline=False, **st)
        ctx.add(f"{n}_Tank{i + 1}_Band", "cylinder", [0, 5.5, 0], [2.0, 0.8, 2.0], "trim", tg, sections=8, collision=False, **st)
        ctx.add(f"{n}_Tank{i + 1}_Cap", "cylinder", [0, 9.3, 0], [2.1, 0.9, 2.1], "frame", tg, sections=8, collision=False, **st)
        ctx.add(f"{n}_Tank{i + 1}_Elbow", "cylinder", [0, 9.75, 0], [0.7, 4.2, 0.7], "pipe", tg, [-90, 0, 0], sections=8, collision=False, **st)  # back into the rock
    for i in range(int(s.get("ledges", 3))):  # metal ledges on brackets, red light slit along the front
        u_ = pick(3.5)
        if u_ is None: break
        f_ = front(u_); y_ = rg.uniform(6.0, min(13.0, top(u_) - 4.0))
        ctx.add(f"{n}_Ledge_{i + 1}", "box", [u_, y_, f_ + 0.5], [3.6, 0.35, 2.4], "frame", g, collision=False, **st)
        ctx.add(f"{n}_Ledge_{i + 1}_Light", "box", [u_, y_ + 0.09, f_ + 1.72], [2.6, 0.16, 0.06], "glow", g, collision=False, outline=False, **st)
        for k_, sd_ in enumerate((-1, 1)):
            ctx.add(f"{n}_Ledge_{i + 1}_Bracket_{k_ + 1}", "box", [u_ + sd_ * 1.4, y_ - 1.37, f_ + 0.2], [0.3, 1.4, 1.6], "frame", g, collision=False, outline=False, **st)
    for i in range(int(s.get("spouts", 5))):  # slime trickling out of pipe spouts set into the rock (real pours)
        u_ = pick(2.5)
        if u_ is None: break
        f_ = front(u_); y_ = round(rg.uniform(3.5, min(14.0, top(u_) - 3.0)), 2); bx, bz = _loc(u_, f_ - 1.2, gy); nx, nz = _loc(0, 1, gy)
        _pipe(ctx, dict(id=f"{n}_Spout_{i + 1}", position=[round(x + bx, 3), y_, round(z + bz, 3)], yaw=round(math.degrees(math.atan2(nx, nz)), 2), outlet="circle",
                        radius=round(rg.uniform(0.3, 0.45), 2), length=2.4, pour=True, fitting=False, mount=False), getattr(ctx, "floor_y", 0.0), {})  # base buried in the rock


@structure("wall_fans", pad=False)
def wall_fans(ctx, s, x, y, z, yaw):
    """Stage 68: big fans set into a wall face, a louvred vent under each. Place the group ON the wall face, local +z out
    of it ("yaw"); "fans": [[x, y, radius], ...] in the group's frame (y = height of the fan centre above the group);
    "rpm" (default random 14 - 34 per fan, own direction). Each rotor is its own node and spins (effect "spin")."""
    import architecture as A
    n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    for i, (fx, fy, R) in enumerate(s.get("fans", [])):
        nm = f"{n}_Fan_{i + 1}"; A.fan_unit(ctx, nm, g, (fx, fy, 0.0), R, float(s.get("depth", 1.0)), wall=True, rpm=s.get("rpm"), seed=A._h(nm), st=st)
        if s.get("vents", True):  # under the housing ring (R + 0.6) and its clamps
            vh = float(s.get("vent_height", 1.8)); vw = 2 * R * 0.95
            A.louvred_vent(ctx, f"{n}_Vent_{i + 1}", g, fx, fy - R - 1.0 - vh, vw, vh, 0.0, st)


@structure("crusher", pad=False)
def crusher(ctx, s, x, y, z, yaw):
    """Stage 72: industrial crusher the player has to cross: a hydraulic column rises out of the pool to a pad ("top",
    square "pad" m, hazard-striped edge, walkable), a ram housing hangs from the ceiling ("ceiling" = underside y) and
    the ram (press head + rod, own mobile group "<id>_Ram") slams down onto the pad every "period" s (effect "crusher"):
    whatever stands on the pad then dies (kill box). Rest gap between head and pad = "travel" m (head clear of a player)."""
    n = s["id"]; top = float(s.get("top", 8.0)); ceil = float(s["ceiling"]); P = float(s.get("pad", 3.2)); R = float(s.get("radius", 1.0))
    up = float(s.get("travel", 5.4)); hh = 0.8; Lr = up + 1.2; st = dict(mobile={"static": True}); vs = dict(collision=False, **st)
    g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw, 0]); ram = dict(collision=False, mobile={"group": n + "_Ram"})
    # base: flared foot in the slime, banded hydraulic column, brace under the pad
    ctx.add(n + "_Foot", "frustum", [0, 0, 0], [2.2 * R, 1.8, 2.2 * R], "structure_b", g, sections=12, bottom_scale=1.45, **st)
    ctx.add(n + "_Column", "cylinder", [0, 1.7, 0], [2 * R, top - 1.6 - 1.7 + 0.05, 2 * R], "pipe", g, sections=12, **st)
    for k, by_ in enumerate((2.6, 4.2)): ctx.add(f"{n}_Rib_{k + 1}", "cylinder", [0, by_, 0], [2 * R + 0.24, 0.3, 2 * R + 0.24], "structure_b", g, sections=12, outline=False, **vs)
    ctx.add(n + "_Brace", "frustum", [0, top - 1.6, 0], [P - 0.2, 1.0, P - 0.2], "structure_b", g, sections=4, bottom_scale=0.45, **st)
    ctx.add(n + "_Pad", "box", [0, top - 0.6, 0], [P, 0.6, P], "structure_b", g, **st)
    for k, (ox, oz, sx, sz) in enumerate(((0, P / 2 - 0.17, P - 0.04, 0.3), (0, -P / 2 + 0.17, P - 0.04, 0.3), (P / 2 - 0.17, 0, 0.3, P - 0.64), (-P / 2 + 0.17, 0, 0.3, P - 0.64))):
        ctx.add(f"{n}_Pad_Stripe_{k + 1}", "box", [ox, top - 0.02, oz], [sx, 0.04, sz], "stripe", g, outline=False, **vs)  # hazard-striped rim (2 cm proud, 2 cm in from the edges)
    for k, sd in enumerate((-1, 1)): ctx.add(f"{n}_Pad_Lamp_{k + 1}", "box", [sd * (P / 2 + 0.03), top - 0.35, 0], [0.06, 0.18, P * 0.6], "glow", g, outline=False, **vs)
    # ceiling housing: mounting plate, cylinder with bands, warning lamps on its lip
    hb = top + hh + Lr - 0.3  # housing bottom: the rod stays 30 cm inside it at full stroke
    ctx.add(n + "_Mount", "box", [0, ceil - 0.42, 0], [2 * R + 1.6, 0.44, 2 * R + 1.6], "structure_b", g, **vs)  # 2 cm into the ceiling
    ctx.add(n + "_Housing", "cylinder", [0, hb, 0], [2.5 * R, ceil - 0.4 - hb + 0.02, 2.5 * R], "machine", g, sections=12, **vs)
    for k, by_ in enumerate((hb + 0.25, (hb + ceil) / 2)): ctx.add(f"{n}_Housing_Rib_{k + 1}", "cylinder", [0, round(by_, 3), 0], [2.5 * R + 0.24, 0.3, 2.5 * R + 0.24], "structure_b", g, sections=12, outline=False, **vs)
    for k in range(4):
        a = math.radians(45 + 90 * k); ctx.add(f"{n}_Warn_{k + 1}", "box", [math.cos(a) * (1.25 * R + 0.02), hb + 0.75, math.sin(a) * (1.25 * R + 0.02)], [0.3, 0.3, 0.3], ctx.role("laser"), g,
                                                [0, -math.degrees(a), 0], outline=False, **dict(vs, mobile={"group": n + "_Warn"}))
    # the ram (moves): press head with striped sides, rod, collar
    hy = top + up
    ctx.add(n + "_Head", "box", [0, hy, 0], [P - 0.2, hh, P - 0.2], "machine", g, **ram)
    for k, (ox, oz, sx, sz) in enumerate(((0, (P - 0.2) / 2 + 0.01, P - 0.2, 0.04), (0, -(P - 0.2) / 2 - 0.01, P - 0.2, 0.04), ((P - 0.2) / 2 + 0.01, 0, 0.04, P - 0.2), (-(P - 0.2) / 2 - 0.01, 0, 0.04, P - 0.2))):
        ctx.add(f"{n}_Head_Stripe_{k + 1}", "box", [ox, hy + 0.15, oz], [sx, 0.5, sz], "stripe", g, outline=False, **ram)
    ctx.add(n + "_Rod", "cylinder", [0, hy + hh - 0.05, 0], [0.9, Lr + 0.05, 0.9], "rail", g, sections=12, **ram)
    ctx.add(n + "_Collar", "cylinder", [0, hy + hh - 0.02, 0], [1.5, 0.35, 1.5], "structure_b", g, sections=12, **ram)
    a = math.radians(yaw); hx, hz = abs(math.cos(a)) * P / 2 + abs(math.sin(a)) * P / 2, abs(math.sin(a)) * P / 2 + abs(math.cos(a)) * P / 2
    ctx.crushers = getattr(ctx, "crushers", []) + [dict(id=n, group=n + "_Ram", warn_group=n + "_Warn", travel=up, period=float(s.get("period", 4.5)), phase=float(s.get("phase", 0.0)),
                                                        warn=0.7, down=0.22, hold=0.45, rise=1.2,
                                                        kill=[[round(x - hx + 0.05, 3), top, round(z - hz + 0.05, 3)], [round(x + hx - 0.05, 3), round(top + 2.0, 3), round(z + hz - 0.05, 3)]])]
    ctx.walkable.append(dict(name=n + "_Pad", min=[round(x - hx, 3), round(z - hz, 3)], max=[round(x + hx, 3), round(z + hz, 3)], y=top))
    for pl in ctx.spec.get("platforms", []):  # Stage 75: where players land from / take off for the pad - kept clear of cover crates
        if pl.get("shape", "rect") != "rect" or abs(float(pl.get("top", 0)) - top) > 2.5: continue
        (cx, cz), (w, d) = pl["center"], pl["size"]; lx, lz = min(max(x, cx - w / 2 + 1.0), cx + w / 2 - 1.0), min(max(z, cz - d / 2 + 1.0), cz + d / 2 - 1.0)
        if max(abs(lx - x) - hx, abs(lz - z) - hz) <= ctx.G["player"]["jump_distance"] + 1.0: ctx.landings.append((round(lx, 3), round(lz, 3), 2.5))


@structure("exit_hall", pad=False)
def exit_hall(ctx, s, x, y, z, yaw):
    """Stage 77: the level's way out - an arched doorway cut through the wall (group on the wall's room face at floor
    y, local +z into the room, local -z through the wall: "wall" m thick) into a short hallway ("length" m) that fades
    to pure black like the elevator shafts: walls, floor and ceiling carry the "void" fade (wall colour at the door end
    -> black over the far part), the end wall is black. Walking into the dark is the level exit ("target").
    Doorway "width" x "height"."""
    import architecture as A
    n = s["id"]; T = float(s.get("wall", 4.0)); Lh = float(s.get("length", 14.0))
    W = float(s.get("width", 6.0)); H = float(s.get("height", 7.0)); r0 = W / 2 - 0.7; spring = H - 0.8 - r0; Wi = W + 0.4; Hc = H + 1.0
    st = dict(mobile={"static": True}); vs = dict(collision=False, **st); gy = ctx.role("glow_yellow"); red = ctx.role("laser")
    hs = dict(outline=False, bevel=False, **st)  # the hall's shell: plain (no ink shell / bevel - smaller mobile GLB)
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); a = math.radians(yaw)
    Wp = lambda lx, ly, lz: [x + lx * math.cos(a) + lz * math.sin(a), y + ly, z - lx * math.sin(a) + lz * math.cos(a)]
    pts = [Wp(sx * (W / 2 - 0.05), sy, sz) for sx in (-1, 1) for sy in (-0.3, H - 0.05) for sz in (0.3, -T - 0.05)]  # (5 cm inside the frame: it bites into the wall, no flush faces)
    ctx.cuts = getattr(ctx, "cuts", []) + [dict(min=[min(p[i] for p in pts) for i in range(3)], max=[max(p[i] for p in pts) for i in range(3)], keep=n, floor=y)]
    # the doorway: an arched frame filling the cut, dressed on the room face
    ctx.add(n + "_Arch", "round_arch", [0, 0, -T / 2], [W, H, T + 0.1], "frame", g, opening=round(2 * r0 / W, 4), opening_h=round((spring + r0) / H, 4), segments=10)
    A.arch_dressing(ctx, n + "_Mouth", g, r0, spring, 0.0, H + 0.8, look=dict(stone="machine", pilaster="machine", depth=0.45, halo=0.24))  # stands out from the wall
    ctx.add(n + "_Sill", "box", [0, -0.3, -T / 2 + 0.1], [W - 0.1, 0.3, T + 0.3], "deck", g, bevel=False, **st)  # the doorway floor, through the wall
    if s.get("laser_gate"): _laser_gate(ctx, n, g, 2 * r0 + 0.2, H, s["laser_gate"], x, y, z, yaw)  # Stage 80: beams across the arch until e.g. a terminal opens it
    # the hallway: floor, walls, ceiling, end wall
    z0, ze = -T, -T - Lh; zm = (z0 + ze) / 2
    ctx.add(n + "_Floor", "box", [0, -0.6, zm], [Wi, 0.6, Lh], "deck", g, **hs)
    for k, sd in enumerate((-1, 1)): ctx.add(f"{n}_Wall_{k + 1}", "box", [sd * (Wi / 2 + 0.5), -0.6, zm], [1.0, Hc + 1.5, Lh], "wall", g, **hs)
    ctx.add(n + "_Ceiling", "box", [0, Hc, zm], [Wi + 1.8, 0.8, Lh], "structure_b", g, **hs)
    ctx.add(n + "_EndWall", "box", [0, -0.6, ze - 0.5], [Wi + 2.0, Hc + 1.5, 1.0], "wall", g, **hs)
    # the endless dark: "void" fade panels (panel v: 0 far end, black over its lower 45% .. 1 wall colour towards the door)
    P = round(Lh * 0.85, 3); vd = dict(cut="rect", uv_region="void", outline=False, **vs)
    for nm, pos, rot, wd in ((n + "_Fade_Floor", [0, 0.02, ze + 0.02], [90, 0, 180], Wi), (n + "_Fade_Ceiling", [0, Hc - 0.02, ze + 0.02], [90, 0, 0], Wi),
                             (n + "_Fade_1", [-Wi / 2 + 0.02, Hc / 2, ze + 0.02], [90, 0, 90], Hc), (n + "_Fade_2", [Wi / 2 - 0.02, Hc / 2, ze + 0.02], [90, 0, -90], Hc)):
        ctx.add(nm, "panel", pos, [wd, P, 0], "accent", g, rot, **vd)
    ctx.add(n + "_Fade_End", "panel", [0, 0.0, ze + 0.03], [Wi, round(Hc / 0.44, 3), 0], "accent", g, **vd)  # its black part covers the whole end
    # ribs + lamps and red floor-edge strips, in the lit part only (the dark part stays pure black)
    zb = ze + P * 0.5; k = 0; zr = z0 - 1.6
    while zr > zb + 0.5:
        k += 1
        for sd in (-1, 1): ctx.add(f"{n}_Rib_{k}_Post_{sd + 2}", "box", [sd * (Wi / 2 - 0.2), 0.0, zr], [0.4, Hc, 0.5], "structure_b", g, outline=False, **vs)
        ctx.add(f"{n}_Rib_{k}_Beam", "box", [0, Hc - 0.45, zr], [Wi, 0.45, 0.5], "structure_b", g, outline=False, **vs)
        ctx.add(f"{n}_Rib_{k}_Lamp", "box", [0, Hc - 0.57, zr], [0.9, 0.12, 0.3], gy, g, outline=False, **vs)
        zr -= 3.2
    for k, sd in enumerate((-1, 1)): ctx.add(f"{n}_Guide_{k + 1}", "box", [sd * (Wi / 2 - 0.03), 2.4, (z0 + zb) / 2], [0.06, 0.08, z0 - zb], red, g, outline=False, **vs)  # red guide strips on the walls
    ex, ey, ez = Wp(0, 2.0, ze + 2.5)
    ctx.exits.append(dict(id=n + "_Exit", type="level_exit", target=s.get("target", "next_level"), shape="cylinder", center=[round(ex, 3), round(ey, 3), round(ez, 3)],
                          radius=round(Wi / 2 - 0.3, 3), height=4.0, note="walking into the black at the end of the exit hallway loads the next level (Construct Error: handle in the level_exit trigger)"))
    c0, c1 = Wp(-Wi / 2, 0, z0), Wp(Wi / 2, 0, ze)
    ctx.walkable.append(dict(name=n + "_Floor", min=[round(min(c0[0], c1[0]), 3), round(min(c0[2], c1[2]), 3)], max=[round(max(c0[0], c1[0]), 3), round(max(c0[2], c1[2]), 3)], y=y))
    fx_, _, fz_ = Wp(0, 0, ze - 1.0); ctx.add(n + "_Far", "group", [round(fx_, 3), 0, round(fz_, 3)])  # (root marker: the level bounds reach the hall's end)
    ctx.notes.append(f"{n}: exit hallway {Lh:.0f} m fading to black -> {s.get('target')}")



@structure("rising_pads", pad=False)
def rising_pads(ctx, s, x, y, z, yaw):
    """Stage 80: stepping-stone pads that rise out of the liquid - a jump route from "from" to "to" ([x, z], the two floor
    edges; EQUAL gaps between pads and to both floors, zig-zagging "zigzag" m to the sides), tops at "y" (+ "steps"
    height offsets, all within a jump). Each pad: a hexagonal column, an octagonal deck cap, a glowing rim, plus a glowing surge ring at the liquid surface.
    All pads are ONE skinned mesh per material (skeleton: one bone per pad + one per surge ring): memory and draw calls
    stay those of a single static prop. They start under the liquid ("liquid" y); when a player comes within
    "trigger_radius" of "trigger" ([x, y, z], default: before the first pad) they surge up one after another
    ("stagger" s apart, "rise_s" s each: fast, decelerating, a damped bob as they settle) while the surge ring bursts
    out and sinks back; a pad's collider is enabled once it is up (Godot: apply_effects.gd; preview: viewer.html).
    The colliders in collision.glb stand at the raised position (what the checks see)."""
    n = s["id"]; (ax, az), (bx, bz) = s["from"], s["to"]; N = int(s.get("count", 10)); D = float(s.get("pad_size", 2.8)); zz = float(s.get("zigzag", 1.2))
    liq = float(s.get("liquid", 1.0)); top0 = float(s.get("y", y)); steps = s.get("steps") or [0.0, 0.3, -0.2, 0.4, 0.0, -0.3, 0.3, 0.0, 0.4, 0.0]
    L = math.hypot(bx - ax, bz - az); ux, uz = (bx - ax) / L, (bz - az) / L; px, pz = -uz, ux; gap = (L - N * D) / (N + 1)
    grp = n + "_Rig"; st = dict(collision=False, outline=False); joints = [dict(name=n + "_JRoot", parent=None, pivot=[round(ax, 3), round(liq, 3), round(az, 3)], axis=[0.0, 1.0, 0.0])]
    rings, pads = [], []
    for k in range(N):
        e = gap * (k + 1) + D * (k + 0.5)  # equal gaps everywhere: first / last pad as far from the floors as from each other
        cx, cz = ax + ux * e + px * zz * (1 if k % 2 else -1), az + uz * e + pz * zz * (1 if k % 2 else -1)
        top = round(top0 + float(steps[k % len(steps)]) if 0 < k < N - 1 else top0, 3); jn, rn = f"{n}_J{k + 1}", f"{n}_R{k + 1}"
        joints.append(dict(name=jn, parent=n + "_JRoot", pivot=[round(cx, 3), round(liq, 3), round(cz, 3)], axis=[0.0, 1.0, 0.0])); rings.append(dict(name=rn, parent=n + "_JRoot", pivot=[round(cx, 3), round(liq + 0.03, 3), round(cz, 3)], axis=[0.0, 1.0, 0.0]))
        pj, rj = dict(group=grp, joint=jn), dict(group=grp, joint=rn); pre = f"{n}_Pad_{k + 1}"
        ctx.add(pre + "_Column", "cylinder", [cx, 0.0, cz], [D * 0.6, top - 0.4, D * 0.6], "structure_b", sections=6, mobile=pj, **st)
        ctx.add(pre + "_Cap", "cylinder", [cx, top - 0.4, cz], [D, 0.4, D], "deck", sections=8, mobile=pj)
        ctx.add(pre + "_Rim", "cylinder", [cx, top - 0.36, cz], [D + 0.14, 0.12, D + 0.14], ctx.role("glow"), sections=8, mobile=pj, **st)  # a disc: the cap hides its middle (32 tris, not a holed ring)
        ctx.add(pre + "_Surge", "cylinder", [cx, liq + 0.03, cz], [D * 1.25, 0.04, D * 1.25], "fall", sections=8, mobile=rj, **st)  # glowing slime burst on the surface
        pads.append(dict(joint=jn, ring=rn, center=[round(cx, 3), round(top, 3), round(cz, 3)], size=D, rise=round(top - liq + 1.0, 3), colliders=[pre + "_Cap"]))
        ctx.landings.append((round(cx, 3), round(cz, 3), D / 2))  # nothing of the cover / dressing passes stand on a pad
    tr = s.get("trigger") or [round(ax - ux * 1.0, 3), round(top0, 3), round(az - uz * 1.0, 3)]
    ctx.skeletons = getattr(ctx, "skeletons", {}); ctx.skeletons[n] = dict(groups=[grp], joints=joints + rings, kind="emerge")
    ctx.risers = getattr(ctx, "risers", []) + [dict(id=n, group=grp, skeleton=n, pads=pads, trigger=dict(center=tr, radius=float(s.get("trigger_radius", 7.0))),
                                                     stagger=float(s.get("stagger", 0.32)), rise_s=float(s.get("rise_s", 2.0)), liquid=liq,
                                                     note="pads start under the liquid; they surge up in order when a player enters the trigger sphere")]
    ctx.notes.append(f"{n}: {N} pads rising out of the liquid (one skinned mesh per material, {len(joints + rings)} bones)")


@structure("control_terminal", pad=False)
def control_terminal(ctx, s, x, y, z, yaw):
    """Stage 80: a control console on a deck (local +z: the side the player stands at): plinth, slanted desk with a lit
    screen and a big glowing button, a beacon on a mast. level.json "terminals": the game puts an interaction area
    there ("radius") and, when the player uses it, opens the gates listed in "activates" (apply_mobile.gd:
    activate_terminal(id) -> open_gate for each, signal terminal_activated)."""
    n = s["id"]; g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    ctx.add(n + "_Plinth", "box", [0, 0, -0.1], [1.7, 1.0, 0.9], "machine", g, **st)
    ctx.add(n + "_Desk", "box", [0, 0.92, 0.0], [1.9, 0.14, 1.0], "structure_b", g, [-22, 0, 0], **st)
    from architecture import screen_slot
    scr, sid = screen_slot(ctx, "screen", "a")  # own picture variant + id (the screens' static / flicker differ)
    ctx.add(n + "_Screen", "panel", [0, 1.2, -0.48], [1.4, 0.78, 0], "screen", g, uv_region=scr, uv_shift=sid, **vs)  # upright monitor on the back panel, facing the player
    ctx.add(n + "_Bezel", "box", [0, 1.12, -0.52], [1.56, 0.94, 0.04], "frame", g, **vs)
    ctx.add(n + "_Keys", "box", [-0.15, 1.02, 0.02], [1.0, 0.04, 0.5], "glow_dim", g, [-22, 0, 0], **vs)
    ctx.add(n + "_Button", "cylinder", [0.62, 1.0, 0.32], [0.26, 0.1, 0.26], ctx.role("glow"), g, sections=8, **vs)
    ctx.add(n + "_Back", "box", [0, 0, -0.62], [1.8, 2.1, 0.22], "structure_b", g, **st)
    ctx.add(n + "_Mast", "cylinder", [0.7, 2.1, -0.62], [0.12, 0.9, 0.12], "frame", g, sections=6, collision=False, **st)
    ctx.add(n + "_Beacon", "cylinder", [0.7, 3.0, -0.62], [0.32, 0.3, 0.32], ctx.role("glow"), g, sections=8, **vs)
    ctx.add(n + "_Stripe", "box", [0, 0.0, 0.75], [1.9, 0.03, 0.6], "stripe", g, **vs)
    dx, dz = A_local(0, 0.9, yaw); fx, fz = x + dx, z + dz  # in front of the desk
    ctx.terminals = getattr(ctx, "terminals", []) + [dict(id=n, center=[round(fx, 3), round(y + 1.0, 3), round(fz, 3)], radius=float(s.get("radius", 1.8)), activates=list(s.get("activates", [])),
                                                           screen=n + "_Screen", note="use it (interact) within radius: opens the gates in 'activates'")]


@structure("turbine_fan", pad=False)
def turbine_fan(ctx, s, x, y, z, yaw):
    """Stage 82/85: a huge turbine fan at the mouth of an endless duct in a wall (group on the wall face at floor y; local
    +z out into the room). The wall ("wall" m thick) is cut behind it; the duct is a sleeve lined with the "void" fade
    (wall colour at the mouth -> pure black deep in: it reads endless, like the elevator shafts). In front: a steel
    trim frame with corner plates up to a deep housing ring sticking "depth" m out with heavy clamps and a solid plinth,
    a broad 6-bladed rotor (own node, turned by the wind effect - not the generic spin), guard bars. Its WIND (L.winds, effect "wind"): a cone along local +z ("length" m, radius growing "spread" m per m); a
    player in it is pushed along at "push" m/s (more than walking speed) and lifted "lift" m/s^2 while airborne, so a
    jump (or double jump) only carries them further out. With "stop_at" ([x, y, z]) it blows at full force until a
    player enters that sphere ("stop_radius"), then spins down over "spin_down" s and stays slow; without it, it
    cycles ("ramp" / "blast" / "calm" s). Collision: the frame, the housing (the duct can't be entered), the plinth."""
    n = s["id"]; D = float(s.get("diameter", 5.2)); R = D / 2; dep = float(s.get("depth", 1.4)); yc = R + float(s.get("lift_off", 1.2)); F = R + 1.0
    T = float(s.get("wall", 4.0)); Rh = (D + 0.9) / 2
    st = dict(mobile={"static": True}); vs = dict(collision=False, **st)
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); a = math.radians(yaw)
    Wp = lambda lx, ly, lz: [x + lx * math.cos(a) + lz * math.sin(a), y + ly, z - lx * math.sin(a) + lz * math.cos(a)]
    pts = [Wp(sx * (F - 0.1), sy, sz) for sx in (-1, 1) for sy in (yc - F + 0.1, yc + F - 0.1) for sz in (dep + 0.5, -T - 0.05)]  # through the wall
    ctx.cuts = getattr(ctx, "cuts", []) + [dict(min=[min(p[i] for p in pts) for i in range(3)], max=[max(p[i] for p in pts) for i in range(3)], keep=n, floor=y)]
    for k, (px, py, w, h) in enumerate(((0, yc + F - 0.45, 2 * F + 0.1, 0.45), (0, yc - F, 2 * F + 0.1, 0.45), (-F + 0.2, yc - F + 0.45, 0.45, 2 * F - 0.9), (F - 0.2, yc - F + 0.45, 0.45, 2 * F - 0.9))):
        ctx.add(f"{n}_Frame_{k + 1}", "box", [px, py, -0.02], [w, h, 0.4], "frame", g, bevel=False, outline=False, **st)  # plain dark steel frame round the cut
    ri = Rh * 0.95; ci = F - 0.3  # corner plates: frame corner -> housing ring (arc a little inside the ring's 12-gon)
    for k, (sx, sy) in enumerate(((1, 1), (-1, 1), (-1, -1), (1, -1))):
        arc = [[round(sx * ri * math.cos(t), 4), round(yc + sy * ri * math.sin(t), 4)] for t in [math.pi / 2 * q / 3 for q in range(3, -1, -1)]]
        poly = [[round(sx * ci, 4), round(yc, 4)], [round(sx * ci, 4), round(yc + sy * ci, 4)], [0.0, round(yc + sy * ci, 4)]] + arc
        if sx * sy < 0: poly = poly[::-1]  # same winding in every quadrant
        ctx.add(f"{n}_Corner_{k + 1}", "prism", [0, 0, 0.0], [2 * ci, 2 * ci, 0.3], "structure_b", g, poly=poly, outline=False, **st)
    ctx.add(n + "_Duct", "panel", [0, yc, 0.3 - (T + 0.2)], [2 * R + 0.06, T + 0.2, 0], "accent", g, [90, 0, 0], cut="sleeve12", uv_region="void", outline=False, **vs)  # endless black duct
    ctx.add(n + "_Housing", "cylinder", [0, yc, -0.05], [D + 0.9, dep + 0.35, D + 0.9], "machine", g, [90, 0, 0], sections=12, hole=R + 0.02, **st)
    hb = yc - Rh  # solid plinth under the housing: no low gap to crawl into
    ctx.add(n + "_Plinth", "box", [0, 0.0, 0.3 + dep / 2], [D + 0.4, hb + 0.25, dep - 0.1], "structure_b", g, bevel=False, outline=False, **st)
    for k in range(6):  # heavy clamps round the housing
        b = math.radians(30 + 60 * k); ca, sa = math.cos(b), math.sin(b)
        ctx.add(f"{n}_Clamp_{k + 1}", "box", [ca * (R + 0.55), yc + sa * (R + 0.55) - 0.35, 0.33 + (dep + 0.1) / 2], [0.9, 0.7, dep + 0.1], "frame", g, [0, 0, math.degrees(b) - 90], outline=False, **vs)  # in front of the cut
    ctx.add(n + "_Rotor", "fan_rotor", [0, yc, 0.3 + dep * 0.45], [D * 0.94, 0.5, D * 0.94], "frame", g, [90, 0, 0], blades=int(s.get("blades", 6)), sweep=30.0, solidity=0.62, detail="low", collision=False, outline=False,
            **dict(st, mobile={"merge": False}))  # own node: the wind effect turns it
    for k, o_ in enumerate((-R * 0.45, R * 0.45)):  # guard bars across the mouth
        ctx.add(f"{n}_Guard_{k + 1}", "box", [0, yc + o_ - 0.06, 0.3 + dep + 0.02], [2 * math.sqrt(R * R - o_ * o_) + 0.1, 0.12, 0.12], "frame", g, outline=False, **vs)
    ctx.add(n + "_GuardV", "box", [0, yc - R - 0.05, 0.3 + dep + 0.02], [0.12, D + 0.1, 0.12], "frame", g, outline=False, **vs)
    o = Wp(0, yc, 0.3 + dep); d = [math.sin(a), 0.0, math.cos(a)]  # local +z in the world
    w = dict(id=n, rotor=n + "_Rotor", origin=[round(v, 3) for v in o], dir=[round(v, 4) for v in d], radius=round(R + 0.3, 3),
             spread=float(s.get("spread", 0.22)), length=float(s.get("length", 18.0)), push=float(s.get("push", 9.0)), lift=float(s.get("lift", 16.0)),
             ramp=float(s.get("ramp", 1.0)), blast=float(s.get("blast", 3.0)), calm=float(s.get("calm", 2.5)), phase=float(s.get("phase", 0.0)),
             rpm=float(s.get("rpm", 160.0)), idle=0.12, note="force = push along dir (x strength), lift while airborne; inside the cone only")
    if s.get("stop_at"):  # Stage 85: full force until a player reaches this sphere, then it spins down for good
        w.update(trigger=dict(center=[float(v) for v in s["stop_at"]], radius=float(s.get("stop_radius", 4.0))), spin_down=float(s.get("spin_down", 4.0)), idle=0.06)
    ctx.winds = getattr(ctx, "winds", []) + [w]
    ctx.notes.append(f"{n}: turbine fan {D:.1f} m, wind {s.get('length', 18.0)} m cone, " + ("blows until a player reaches " + str(s["stop_at"]) if s.get("stop_at") else f"{s.get('blast', 3.0)} s blasts"))
