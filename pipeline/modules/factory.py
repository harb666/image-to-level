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
    """Sealed blast door set against a wall (local +z faces the hall): heavy frame, two leaves with a hazard stripe and
    a lit seam, red warning light above. A later exit can open here; today it is closed (solid)."""
    n = s["id"]; W, H, D = s.get("size", [6, 7, 0.6]); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    ctx.add(n + "_Frame", "box", [0, 0, 0], [W + 1.6, H + 1.0, D], "structure_b", g, **st)
    for k, sd in enumerate((-1, 1)):
        ctx.add(f"{n}_Leaf_{k + 1}", "box", [sd * (W / 4 + 0.02), 0, D / 2 + 0.12], [W / 2 - 0.08, H, 0.24], "wall", g, collision=False, **st)
        ctx.add(f"{n}_Stripe_{k + 1}", "box", [sd * (W / 4 + 0.02), 0.6, D / 2 + 0.25], [W / 2 - 0.3, 0.8, 0.04], "stripe", g, collision=False, outline=False, **st)
    ctx.add(n + "_Seam", "box", [0, 0.3, D / 2 + 0.26], [0.12, H - 0.6, 0.04], "glow", g, collision=False, outline=False, **st)
    ctx.add(n + "_Warning", "box", [0, H + 0.2, D / 2 + 0.1], [1.4, 0.4, 0.2], "glow", g, collision=False, outline=False, **st)
    ctx.notes.append(f"{n}: sealed blast door ({W} x {H} m) - candidate exit to the next part")
