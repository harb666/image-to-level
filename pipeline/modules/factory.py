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
from architecture import local as A_local


@structure("vat", pad=False)
def vat(ctx, s, x, y, z, yaw):
    """Slime vat: plinth, red-lit bands, glowing slime glass section, dark upper body with a banner, rimmed cap."""
    n = s["id"]; D, H, _ = s.get("size", [8, 20, 8]); st = dict(mobile={"static": True}); seg = int(s.get("sections", 10))
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); y0 = -1.0  # plinth reaches into the slime: no visible gap at its foot
    gh = H * 0.5; base = 3.0; uh = max(1.5, H - base - 1.0 - gh - 1.0 - 0.8)
    ctx.add(n + "_Plinth", "cylinder", [0, y0, 0], [D + 1.2, base - y0, D + 1.2], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_BandLow", "cylinder", [0, base, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    ctx.add(n + "_Glass", "cylinder", [0, base + 1.0, 0], [D, gh, D], s.get("material", "hazard"), g, sections=seg, collision=True, **st)
    ctx.add(n + "_BandMid", "cylinder", [0, base + 1.0 + gh, 0], [D + 0.6, 1.0, D + 0.6], "trim", g, sections=seg, collision=False, **st)
    yu = base + 2.0 + gh
    ctx.add(n + "_Body", "cylinder", [0, yu, 0], [D + 0.3, uh, D + 0.3], "structure_b", g, sections=seg, **st)
    ctx.add(n + "_Cap", "cylinder", [0, yu + uh, 0], [D + 0.9, 0.8, D + 0.9], "trim", g, sections=seg, collision=False, **st)
    if s.get("banner", True) and uh > 3:  # banner on the side facing the hall centre
        bw = min(3.0, D * 0.4); r = (D + 0.3) / 2 * math.cos(math.pi / seg) + 0.05
        ctx.add(n + "_Banner", "panel", [0, yu + uh * 0.08, r], [bw, uh * 0.8, 0], "accent", g, collision=False, outline=False, **st)


@structure("claw", pad=False)
def claw(ctx, s, x, y, z, yaw):
    """Crane claw hanging on a chain from the ceiling (or from "y" m): hoist block with a red light, three prongs."""
    n = s["id"]; top = float(s.get("y", getattr(ctx, "ceiling_y", 20.0))); L = float(s.get("length", 9.0)); yb = top - L
    st = dict(collision=False, mobile={"static": True}); g = ctx.add(n, "group", [x, 0, z], rot=[0, yaw, 0])
    for k, o in enumerate((-0.18, 0.18)):  # two chain strands
        ctx.add(f"{n}_Chain_{k + 1}", "box", [o, yb, 0], [0.14, L, 0.3], "frame", g, outline=False, **st)
    ctx.add(n + "_Block", "box", [0, yb - 1.3, 0], [1.6, 1.3, 1.6], "machine", g, **st)
    ctx.add(n + "_Light", "box", [0, yb - 0.9, 0.82], [0.5, 0.4, 0.06], "glow", g, outline=False, **st)
    for k in range(3):  # prongs angled outwards
        a = 2 * math.pi * k / 3; ca, sa = math.cos(a), math.sin(a)
        ctx.add(f"{n}_Prong_{k + 1}", "box", [ca * 0.55, yb - 3.1, sa * 0.55], [0.3, 1.9, 0.3], "structure_b", g, [math.degrees(sa) * -0.35, 0, math.degrees(ca) * 0.35], **st)


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
    """Industrial robot arm on a deck: turntable base, shoulder, two arm links in a pose ("pose" deg [shoulder, elbow],
    default from the id so neighbours differ), wrist with a claw and a red light. Solid base, visual arm."""
    n = s["id"]; sc = float(s.get("scale", 1.0)); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    import random as _r
    rg = _r.Random(n); sh, el = s.get("pose", [rg.uniform(20, 55), rg.uniform(40, 100)])
    if s.get("pedestal"): ctx.add(n + "_Pedestal", "cylinder", [0, -float(s["pedestal"]), 0], [1.3 * sc, float(s["pedestal"]), 1.3 * sc], "structure_b", g, sections=10, **st)
    ctx.add(n + "_Base", "cylinder", [0, 0, 0], [1.6 * sc, 0.6 * sc, 1.6 * sc], "structure_b", g, sections=10, **st)
    ctx.add(n + "_Turret", "cylinder", [0, 0.6 * sc, 0], [1.1 * sc, 0.8 * sc, 1.1 * sc], "machine", g, sections=10, collision=False, **st)
    a1 = math.radians(sh); l1 = 2.6 * sc; py = 1.4 * sc  # link 1 leans forward (+z) by sh from vertical
    ctx.add(n + "_Link1", "box", [0, py, 0], [0.5 * sc, l1, 0.5 * sc], "structure", g, [sh, 0, 0], collision=False, **st)
    ey, ez = py + l1 * math.cos(a1), l1 * math.sin(a1); a2 = a1 + math.radians(el); l2 = 2.0 * sc
    ctx.add(n + "_Elbow", "cylinder", [0.35 * sc, ey - 0.3 * sc, ez], [0.6 * sc, 0.7 * sc, 0.6 * sc], "machine", g, [0, 0, 90], sections=8, collision=False, **st)
    ctx.add(n + "_Link2", "box", [0, ey, ez], [0.4 * sc, l2, 0.4 * sc], "structure", g, [math.degrees(a2), 0, 0], collision=False, **st)
    wy, wz = ey + l2 * math.cos(a2), ez + l2 * math.sin(a2)
    ctx.add(n + "_Wrist", "box", [0, wy - 0.3 * sc, wz], [0.7 * sc, 0.6 * sc, 0.7 * sc], "machine", g, collision=False, **st)
    ctx.add(n + "_Light", "box", [0, wy - 0.15 * sc, wz + 0.36 * sc], [0.3 * sc, 0.2 * sc, 0.04], "glow", g, collision=False, outline=False, **st)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Finger_{k + 1}", "box", [sd * 0.22 * sc, wy - 1.0 * sc, wz], [0.14 * sc, 0.7 * sc, 0.2 * sc], "structure_b", g, [0, 0, sd * 12], collision=False, **st)


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

