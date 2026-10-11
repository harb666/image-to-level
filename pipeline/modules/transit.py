"""Level transit structures: elevator shaft (exit to the next level).

  {"id": "Elevator", "kind": "elevator_shaft", "on": "Hub", "radius": 5.5, "target": "next_level"}

Cuts a real round hole through the platform it stands on (floor plate, trim, body, underframe -> hollow rings with
concave colliders), lines it with a shaft (wall, pilasters with light strips, light rings; "bottom": "void" (default) = the lower
walls fade into pure black with no floor in sight - reads bottomless; "glow" = lit red floor), dresses the
rim ("dressing": "minimal" (default): plain lip, two insignia plates, one outer light ring; "full": striped lip,
ring of light panels, four insignia plates, radial strips, inner light ring) and registers a level_exit trigger
volume inside the shaft (level.json "exits" -> collision.json triggers -> Godot Area3D; the preview shows the exit).
Must sit at the centre of its platform (offset [0, 0]); works on any platform style / shape (sky_pylon: the shaft ends where
the underframe meets the column; solid platforms: `depth` m deep, default 10, never below 0.3 m above the base or the
arena floor; the base is split).
"""
import math
from modules import structure
from architecture import local as A_local


@structure("elevator_shaft", pad=False)
def elevator_shaft(ctx, s, x, y, z, yaw):
    """Elevator shaft through a platform: open shaft, lit rim, exit trigger to the next level."""
    n = s["id"]; on = s.get("on"); R = float(s.get("radius", 5.5)); T = 0.4; top = y
    by = {o["name"]: o for o in ctx.objects}
    plat = by.get(on)
    if plat is None or abs(plat["position"][0] - x) > 0.05 or abs(plat["position"][2] - z) > 0.05:
        ctx.notes.append(f"{n}: elevator_shaft needs to sit at the centre of its platform (on + offset [0, 0]) - skipped"); return
    under, base = by.get(f"{on}_Underframe"), by.get(f"{on}_Base")
    yb = under["position"][1] if under else max(top - float(s.get("depth", 10.0)), (base["position"][1] + 0.3) if base else -1e9)  # sky_pylon: where the
    yb = max(yb, getattr(ctx, "floor_y", -1e9) + 0.3)  # underframe meets the column; solid: above the ground. Never below an arena floor / hazard liquid
    for part in ("_Floor", "_Cap", "_Trim", "_Body", "_Underframe", "_Base", "_Plinth"):  # real hole through every slab above the shaft floor
        o = by.get(on + part)
        if o is None or o["position"][1] + o["size"][1] <= yb + 0.01: continue
        if o["position"][1] < yb - 0.01:  # reaches below the shaft floor (solid base): keep the lower part solid, hole the upper part
            lo = o["position"][1]; h = o["size"][1]; up = {k: v for k, v in o.items() if k not in ("name", "type", "position", "size", "material", "parent", "rotation", "gen", "source")}
            sc = 1.0
            if o["type"] == "frustum":  # split a tapered block: width at the cut, each half keeps the same slope
                k = o.get("bottom_scale", 0.5); sc = k + (1 - k) * (yb - lo) / h; up["bottom_scale"] = round(sc, 4); o["bottom_scale"] = round(k / sc, 4)
            ctx.add(on + part + "Upper", o["type"], [o["position"][0], yb, o["position"][2]], [o["size"][0], lo + h - yb, o["size"][2]], None,
                    o.get("parent"), o.get("rotation", (0, 0, 0)), **up, material=o.get("material"), hole=R + T, collision_mesh=True)
            o["size"] = [round(o["size"][0] * sc, 3), round(yb - lo, 3), round(o["size"][2] * sc, 3)]
        else: o["hole"] = R + T; o["collision_mesh"] = True
    g = ctx.add(n, "group", [x, 0, z]); depth = top - yb; seg = 24
    ctx.add(n + "_Liner", "cylinder", [0, yb, 0], [2 * (R + T), depth, 2 * (R + T)], "structure_b", g, sections=seg, hole=R, collision_mesh=True, outline=False)  # outer face hidden in the deck
    void = s.get("bottom", "void") != "glow"  # "void": walls fade into pure black, no floor in sight (reads bottomless)
    fade = 0.7 if void else 0.0  # lower part of the shaft hidden by the dark sleeve
    if not void: ctx.add(n + "_GlowFloor", "cylinder", [0, yb, 0], [2 * R, 0.12, 2 * R], "glow", g, sections=seg)  # the lift glow far below
    for i in range(8):  # pilasters around the wall, light strips on every other one (above the dark part)
        a = 2 * math.pi * (i + 0.5) / 8; ca, sa = math.cos(a), math.sin(a); r = R - 0.22
        ctx.add(f"{n}_Pilaster_{i + 1}", "box", [ca * r, yb, sa * r], [0.9, depth - 0.25, 0.5], "structure_b", g, [0, -math.degrees(a) + 90, 0], bevel=0)
        if i % 2 == 0:
            y0 = yb + max(0.6, depth * fade - 0.3); y1 = top - 1.0
            if s.get("dressing", "minimal") != "full": y0, y1 = y0 + (0.0, 0.5, 0.15, 0.8)[i // 2], y1 - (0.3, 0.0, 0.6, 0.15)[i // 2]  # uneven lengths
            ctx.add(f"{n}_Strip_{i + 1}", "box", [ca * (r - 0.3), y0, sa * (r - 0.3)], [0.22, y1 - y0, 0.08], "glow", g, [0, -math.degrees(a) + 90, 0], mobile={"static": True})
    minimal = s.get("dressing", "minimal") != "full"
    for j, f in enumerate(() if minimal else (0.85,) if void else (0.25, 0.65)):  # light rings set into the wall
        ctx.add(f"{n}_LightRing_{j + 1}", "cylinder", [0, yb + depth * f, 0], [2 * R + 0.02, 0.3, 2 * R + 0.02], "glow", g, sections=16, hole=R - 0.15)
    if void:  # dark sleeve in front of the lower wall + black bottom: wall colour at its top edge fading to black (atlas "void" cell)
        roles = ctx.spec.get("materials", {}).get("roles", {}); atl = (roles.get("accent") or {}).get("atlas") or {}
        ctx.add(n + "_Void", "panel", [0, yb + 0.12, 0], [2 * (R - 0.62), depth * fade - 0.1, 0], "accent" if "void" in atl else "void", g,
                cut="sleeve", uv_region="void", collision=False, outline=False, mobile={"static": True})
    if s.get("dressing", "minimal") == "full":  # ring of light panels, 4 insignia plates, radial strips, striped lip
        ctx.add(n + "_Rim", "cylinder", [0, top, 0], [2 * (R + 1.0), 0.14, 2 * (R + 1.0)], "trim", g, sections=seg, hole=R)
        for i in range(16):
            a = 2 * math.pi * i / 16; ca, sa = math.cos(a), math.sin(a); r = R + 2.3
            if i % 4 == 2:
                yw = -math.degrees(a) - 90; ex, ez = A_local(0, 1.1 - 0.75, yw)
                ctx.add(f"{n}_Emblem_{i // 4 + 1}", "panel", [ca * r + ex, top + 0.03, sa * r + ez], [1.3, 2.2, 0], "accent", g, [-90, yw, 0], outline=False, mobile={"static": True})
            else:
                ctx.add(f"{n}_Panel_{i + 1:02d}", "box", [ca * r, top, sa * r], [1.6, 0.05, 0.75], "glow", g, [0, -math.degrees(a) + 90, 0], outline=False, mobile={"static": True})
        for i in range(4):
            a = 2 * math.pi * (i + 0.5) / 4; ca, sa = math.cos(a), math.sin(a); r = R + 6.0
            ctx.add(f"{n}_Radial_{i + 1}", "box", [ca * r, top, sa * r], [0.55, 0.04, 3.6], "glow", g, [0, -math.degrees(a) + 90, 0], outline=False)
    else:  # "minimal": plain hull lip, two insignia plates (not symmetric), nothing repeating round the hole
        ctx.add(n + "_Rim", "cylinder", [0, top, 0], [2 * (R + 0.8), 0.14, 2 * (R + 0.8)], "structure_b", g, sections=seg, hole=R)
        for k, deg in enumerate((38.0, 196.0)):
            # plate lies flat along the radius, centred at R + 2.1: spans R + 1.0 .. R + 3.2, clear of the lip (R + 0.8) and
            # fully inside the outer light ring (R + 3.5), so the ring never runs across the emblem
            a = math.radians(deg); r = R + 2.1; yw = -deg - 90; ex, ez = A_local(0, 1.1, yw)
            ctx.add(f"{n}_Emblem_{k + 1}", "panel", [math.cos(a) * r + ex, top + 0.03, math.sin(a) * r + ez], [1.3, 2.2, 0], "accent", g, [-90, yw, 0], outline=False, mobile={"static": True})
    ctx.add(n + "_OuterRing", "cylinder", [0, top, 0], [2 * (R + 3.75), 0.04, 2 * (R + 3.75)], "glow", g, sections=32, hole=R + 3.5, outline=False)
    lo = yb + 0.5; hi = top - 1.2
    ctx.exits.append(dict(id=n + "_Exit", type="level_exit", target=s.get("target", "next_level"), shape="cylinder",
                          center=[round(x, 3), round((lo + hi) / 2, 3), round(z, 3)], radius=round(R - 0.3, 3), height=round(hi - lo, 3),
                          note="entering the shaft below the floor loads the next level (Construct Error: handle in the level_exit trigger)"))
    ctx.notes.append(f"{n}: elevator shaft r {R} m, {depth:.1f} m deep through {on}; exit trigger -> {s.get('target', 'next_level')}")
