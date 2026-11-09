"""Stage 97: Assembly Ascent (Construct Error map 3) pieces - from the level 3 concept: saw blades on swinging robot
arms, hazard-striped stepping pillars on truss legs, conveyor ramps running against the climb over a spike pit, a
free-standing laser gate and signs (grin / exit / arrow / gear emblem from one sign atlas).

Moving / deadly parts write level.json lists the runtimes read (apply_effects.gd / apply_mobile.gd / viewer.html):
  "saws"   swinging arm + spinning blade (kill near the blade)      effect "saw"
  "belts"  a ramp surface that carries whoever stands on it        effect "belt" (chevrons slide along it)
  "kills"  static kill boxes (spikes)                              collision.json "kills" -> hazard areas
"""
import math
from modules import structure
from architecture import local as A_local


def _W(x, y, z, yaw):  # local (lx, ly, lz) of a group at (x, y, z) turned yaw -> world
    def f(lx, ly, lz):
        dx, dz = A_local(lx, lz, yaw); return [round(x + dx, 4), round(y + ly, 4), round(z + dz, 4)]
    return f


def _yaw_to(dx, dz): return math.degrees(math.atan2(dx, dz))


def _spikes(ctx, n, cx, cz, y, w, d, yaw, mat, length=0.7, pitch=0.7, mobile=None, up=True):
    """A bed of pyramid spikes on a w x d patch (local x / z), base at y (tips at y + length, or below when up=False)."""
    nx, nz = max(1, int(w / pitch)), max(1, int(d / pitch)); k = 0
    kw = dict(collision=False, outline=False, mobile=mobile or {"static": True})
    for i in range(nx):
        for j in range(nz):
            lx = -w / 2 + (i + 0.5) * w / nx; lz = -d / 2 + (j + 0.5) * d / nz; dx, dz = A_local(lx, lz, yaw); k += 1
            if up: ctx.add(f"{n}_{k:02d}", "frustum", [cx + dx, y, cz + dz], [pitch * 0.8, length, pitch * 0.8], mat, sections=4, bottom_scale=1.0 / 40, rot=[180, yaw, 0], **dict(kw, mobile=kw["mobile"]))
            else: ctx.add(f"{n}_{k:02d}", "frustum", [cx + dx, y - length, cz + dz], [pitch * 0.8, length, pitch * 0.8], mat, sections=4, bottom_scale=1.0 / 40, rot=[0, yaw, 0], **kw)
    return k


def _slot_walkways(ctx, C, A, reach, gap=0.9):
    """Stage 99: cut a slot through every walkway a saw blade chops across - the blade's plane (point C, horizontal
    normal A) splits the long boxes of any connector group (deck, girders, side cladding, light strips) under C,
    leaving a `gap` m slot the blade passes through (narrower than the player: walked straight over). The near piece
    keeps the original name and its end_a; the far piece "<name>_b" takes end_b, so the connection / support relations
    follow the piece that really owns them. Returns the names of the groups cut."""
    by = {o["name"]: o for o in ctx.objects}; cut = []
    groups = {o["parent"] for o in ctx.objects if o.get("connector") and o.get("parent") and o["type"] == "box"}
    for gname in sorted(groups):
        g = by.get(gname)
        if not g or g["type"] != "group": continue
        gx, gz, gy = g["position"][0], g["position"][2], g["rotation"][1]; a = math.radians(gy)
        wx, wz = C[0] - gx, C[2] - gz; lx, lz = wx * math.cos(a) - wz * math.sin(a), wx * math.sin(a) + wz * math.cos(a)  # C in the group's frame
        nx, nz = A[0] * math.cos(a) - A[2] * math.sin(a), A[0] * math.sin(a) + A[2] * math.cos(a)                        # the plane normal too
        kids = [o for o in ctx.objects if o.get("parent") == gname and o["type"] == "box" and o.get("size") and o["size"][2] > 1.0
                and abs(o["rotation"][1]) < 1e-6 and abs(o["rotation"][2]) < 1e-6]
        def cut_at(o):
            p = math.radians(-o["rotation"][0]); u = (0.0, math.sin(p), math.cos(p)); nu = nz * u[2]
            if abs(nu) < 0.3: return None  # the plane runs along this box: no clean cut
            tt = (nx * (lx - o["position"][0]) + nz * (lz - o["position"][2])) / nu
            return (tt, u) if abs(tt) < o["size"][2] / 2 - 0.05 else None
        decks = [o for o in kids if o.get("connector") and cut_at(o) and abs(lx - o["position"][0]) < o["size"][0] / 2 + 1.0 and abs(C[1] - o["position"][1]) < reach]
        if not decks: continue
        for o in list(kids):
            c = cut_at(o)
            if c is None: continue
            (tt, u), (px, py, pz), L, nm = c, o["position"], o["size"][2], o["name"]
            La, Lb = tt - gap / 2 + L / 2, L / 2 - tt - gap / 2; cA, cB = (-L / 2 + tt - gap / 2) / 2, (tt + gap / 2 + L / 2) / 2; zcut = pz + tt * u[2]
            o2 = dict(o, name=nm + "_b", position=[round(px + cB * u[0], 3), round(py + cB * u[1], 3), round(pz + cB * u[2], 3)], size=[o["size"][0], o["size"][1], round(Lb, 3)])
            ctx.names.add(o2["name"]); ctx.objects.append(o2)
            o.update(position=[round(px + cA * u[0], 3), round(py + cA * u[1], 3), round(pz + cA * u[2], 3)], size=[o["size"][0], o["size"][1], round(La, 3)])
            for r in ctx.relations:  # the far end and anything resting under the far piece move with it
                if r.get("a") == nm and r.get("a_anchor") == "end_b": r["a"] = o2["name"]
                if r.get("b") == nm and r.get("b_anchor") == "end_b": r["b"] = o2["name"]
                if r["type"] == "supported_by" and r.get("a") == nm:
                    sup = by.get(r["b"]) or {}; sp = sup.get("position")
                    if sp is not None and sup.get("parent") == gname and sp[2] > zcut: r["a"] = o2["name"]
            if o.get("connector"):  # Stage 100: hazard stripes on both lips of the opening (on the deck top, 3 cm proud)
                th_ = o["size"][1]; nrm = (0.0, u[2], -u[1])
                for k_, (q, s_) in enumerate(((o, 1), (o2, -1))):
                    off = s_ * (q["size"][2] / 2 - 0.22); b_ = q["position"]
                    ctx.add(f"{nm}_SlotEdge_{len(cut) + 1}{'ab'[k_]}", "box", [b_[0] + u[0] * off + nrm[0] * th_, b_[1] + u[1] * off + nrm[1] * th_, b_[2] + u[2] * off + nrm[2] * th_],
                            [o["size"][0] - 0.2, 0.03, 0.4], ctx.role("stripe"), gname, o["rotation"], collision=False, outline=False, mobile={"static": True})
        for th_n in (gname + "_Threshold_Lo", gname + "_Threshold_Hi"):  # Stage 100: the caution stripes move from the bridge ends to the openings
            q = by.get(th_n)
            if q in ctx.objects: ctx.objects.remove(q); ctx.names.discard(th_n)
        cut.append(gname)
    return cut


@structure("saw_arm", pad=False)
def saw_arm(ctx, s, x, y, z, yaw):
    """Stage 97/102: a big circular saw on a jointed yellow robot arm HANGING FROM THE CEILING beside a walkway. A ceiling
    plate and a drop column carry the shoulder housing ("shoulder_height", "side" of the walkway, "mount_offset" m out);
    an upper arm and a forearm (hydraulic pistons along their sides, dark joint caps with glowing rings) reach down to a
    wrist motor with a hazard-edged guard over the blade; the blade ("blade" m, a flange with bolts and a hex nut,
    glowing rings) spins on its arbor. All hinges are parallel to "axis_yaw" (along the walkway): the shoulder, elbow
    and wrist each pivot, the outer joints lagging (amp / elbow_amp / wrist_amp, elbow_lag / wrist_lag), so the arm
    whips the blade down across the walkway through the slot it cuts ("slot" m). At angle 0 (the pose built here) the
    blade's centre is over "aim" ([x, z]) at "height". level.json "saws": joints + spin group; the blade kills."""
    n = s["id"]; D = float(s.get("blade", 4.4)); R = D / 2; ax_, az_ = s["aim"]; yc = float(s["height"]); ceil = float(s.get("ceiling", 34.5))
    ay = float(s.get("axis_yaw", 0.0)); A = [round(math.sin(math.radians(ay)), 4), 0.0, round(math.cos(math.radians(ay)), 4)]
    side = 1.0 if float(s.get("side", 1)) > 0 else -1.0; hy = ay + 90.0; H = [math.sin(math.radians(hy)), 0.0, math.cos(math.radians(hy))]  # in-plane horizontal
    arm, gl, stripe = ctx.role("arm_yellow"), ctx.role("glow"), ctx.role("stripe")
    ga, gf, gw, gb = n + "_Arm", n + "_Fore", n + "_Wrist", n + "_Blade"
    K = lambda g, **kw: dict(collision=False, mobile={"group": g} if g else {"static": True}, **kw)
    add = lambda P, Q: [P[0] + Q[0], P[1] + Q[1], P[2] + Q[2]]; mul = lambda P, k: [P[0] * k, P[1] * k, P[2] * k]
    C = [ax_, yc, az_]; sh = float(s.get("shoulder_height", 22.0)); mo = float(s.get("mount_offset", 4.6))
    P0 = add([ax_, sh, az_], mul(H, -side * mo))                       # shoulder: above, beside the walkway
    W = add(add(C, [0, 1.7, 0]), mul(H, -side * 0.9))                  # wrist: just above the blade, towards the mount
    E = add(mul(add(P0, W), 0.5), mul(H, -side * float(s.get("bend", 2.6))))  # elbow bent outwards
    def seg(name, a, b, wd, th, mat, g, **kw):  # a box from a to b in the arm's plane (local x along the hinge axis)
        d = [b[i] - a[i] for i in range(3)]; L = math.dist(a, b); sH = d[0] * H[0] + d[2] * H[2]; pitch = math.degrees(math.atan2(d[1], sH))
        m = mul(add(a, b), 0.5); nrm = [-math.sin(math.radians(pitch)) * H[0], math.cos(math.radians(pitch)), -math.sin(math.radians(pitch)) * H[2]]
        ctx.add(name, "box", add(m, mul(nrm, -th / 2)), [wd, th, L], mat, rot=[-pitch, hy, 0], bevel=False, **K(g, **kw))
    def rod(name, a, b, dia, mat, g, sections=8, **kw):  # a cylinder from a to b in the plane
        d = [b[i] - a[i] for i in range(3)]; sH = d[0] * H[0] + d[2] * H[2]; th = math.degrees(math.atan2(sH, d[1]))
        ctx.add(name, "cylinder", a, [dia, math.dist(a, b), dia], mat, rot=[th, hy, 0], sections=sections, **K(g, **kw))
    def axle(name, P, dia, ln, mat, g, off=0.0, sections=12, **kw):  # a cylinder along the hinge axis centred on P (+ off along it)
        ctx.add(name, "cylinder", add(P, mul(A, off - ln / 2)), [dia, ln, dia], mat, rot=[90, ay, 0], sections=sections, **K(g, **kw))
    # --- ceiling mount (static)
    top = [P0[0], ceil, P0[2]]
    ctx.add(n + "_Plate", "box", [P0[0], ceil - 0.35, P0[2]], [3.4, 0.37, 3.4], "machine", rot=[0, hy, 0], **K(None))
    ys_ = [P0[1] + 1.1, P0[1] + 2.65, ceil - 1.35, ceil - 0.33]  # the column in three lengths, a striped band over each joint
    for k_ in range(3): rod(f"{n}_Column_{k_ + 1}", [P0[0], ys_[k_], P0[2]], [P0[0], ys_[k_ + 1], P0[2]], 1.4, "machine", None, sections=10)
    for k_, yy in enumerate((ys_[2], ys_[1])):
        ctx.add(f"{n}_ColBand_{k_ + 1}", "cylinder", [P0[0], yy - 0.25, P0[2]], [1.7, 0.5, 1.7], stripe, sections=10, **K(None, outline=False))
    ctx.add(n + "_ColGlow", "cylinder", [P0[0], P0[1] + 3.3, P0[2]], [1.6, 0.16, 1.6], gl, sections=10, **K(None, outline=False))
    for sd in (-1, 1):  # yoke cheeks either side of the shoulder housing
        q = add(P0, mul(A, sd * 1.45)); seg(f"{n}_Cheek_{'LR'[sd > 0]}", [q[0], P0[1] + 1.4, q[2]], [q[0], P0[1] - 0.5, q[2]], 0.3, 1.5, arm, None)
    axle(n + "_Shoulder", P0, 2.3, 2.6, "machine", None)
    for sd in (-1, 1): axle(f"{n}_ShoulderGlow_{'LR'[sd > 0]}", P0, 1.3, 0.06, gl, None, off=sd * 1.33, outline=False)
    # --- upper arm (shoulder joint) and forearm (elbow joint): beams with hydraulic pistons
    for nm, a, b, wd, th, g in (("Upper", P0, E, 1.05, 1.1, ga), ("Fore", E, W, 0.85, 0.9, gf)):
        seg(f"{n}_{nm}", a, b, wd, th, arm, g)
        d = [b[i] - a[i] for i in range(3)]; L = math.dist(a, b); u = mul(d, 1 / L)
        for sd in (-1, 1):  # a piston on each side: cylinder body then a chrome rod
            o = mul(A, sd * (wd / 2 + 0.22)); p1 = add(add(a, o), mul(u, L * 0.18)); p2 = add(add(a, o), mul(u, L * 0.55)); p3 = add(add(a, o), mul(u, L * 0.85))
            rod(f"{n}_{nm}Piston_{'LR'[sd > 0]}", p1, p2, 0.36, "machine", g); rod(f"{n}_{nm}Rod_{'LR'[sd > 0]}", p2, p3, 0.18, "machine", g, sections=6, outline=False)
    axle(n + "_Elbow", E, 1.6, 1.5, "machine", gf)
    # --- wrist: motor housing, a bracket down to the arbor, a guard over the blade (does not spin)
    axle(n + "_Wrist", W, 1.5, 1.3, "machine", gw)
    Cb = add(C, mul(A, -0.42)); Wb = add(W, mul(A, -0.42)); seg(n + "_Bracket", Wb, Cb, 0.42, 0.7, arm, gw)
    axle(n + "_Arbor", C, 0.5, 0.95, "machine", gw, off=-0.42, sections=8)
    uw = [W[i] - C[i] for i in range(3)]; Lw = math.dist(W, C); uw = mul(uw, 1 / Lw); v = [A[1] * uw[2] - A[2] * uw[1], A[2] * uw[0] - A[0] * uw[2], A[0] * uw[1] - A[1] * uw[0]]
    Rg = R + 0.22; pts = [add(C, add(mul(uw, Rg * math.cos(math.radians(th_))), mul(v, Rg * math.sin(math.radians(th_))))) for th_ in range(-80, 81, 20)]
    for k_ in range(len(pts) - 1):  # the guard hood: an arc of plates over the top of the blade, a striped lip
        seg(f"{n}_Guard_{k_ + 1}", pts[k_], pts[k_ + 1], 0.62, 0.18, arm, gw)
        seg(f"{n}_GuardLip_{k_ + 1}", add(pts[k_], mul(A, 0.33)), add(pts[k_ + 1], mul(A, 0.33)), 0.05, 0.18, stripe, gw, outline=False)
    # --- the blade (spins): disc, flange, glowing rings, bolts, hex nut - all concentric (each moving link keeps to 2-3 materials: draw calls)
    mb = K(gb, outline=False)
    ctx.add(n + "_Saw", "saw_blade", C, [D, 0.12, D], ctx.role("blade"), rot=[90, ay, 0], teeth=int(s.get("teeth", 36)), **mb)
    axle(n + "_Flange", C, D * 0.34, 0.3, "machine", gb, outline=False)
    for sd in (-1, 1): axle(f"{n}_BladeGlow_{'LR'[sd > 0]}", C, D * 0.42, 0.02, gl, gb, off=sd * 0.072, outline=False)
    axle(n + "_Nut", C, 0.42, 0.2, "machine", gb, off=0.25, sections=6, outline=False)
    for k_ in range(6):
        aa = math.radians(60 * k_); q = add(C, add(mul(uw, D * 0.12 * math.cos(aa)), mul(v, D * 0.12 * math.sin(aa))))
        axle(f"{n}_Bolt_{k_ + 1}", q, 0.13, 0.1, ctx.role("blade"), gb, off=0.2, sections=6, outline=False)
    slots = _slot_walkways(ctx, C, A, R + 2.0, float(s.get("slot", 0.9))) if s.get("slot", 0.9) else []  # Stage 99: a slot through the walkway it chops across
    amp = float(s.get("amp", 30.0)); J = [dict(group=ga, pivot=[round(v_, 3) for v_ in P0], amp=amp, lag=0.0),  # shoulder, elbow, wrist - each pivots,
         dict(group=gf, pivot=[round(v_, 3) for v_ in E], amp=float(s.get("elbow_amp", amp * 0.8)), lag=float(s.get("elbow_lag", 0.9))),  # the outer joints lagging behind
         dict(group=gw, pivot=[round(v_, 3) for v_ in W], amp=float(s.get("wrist_amp", amp * 0.7)), lag=float(s.get("wrist_lag", 1.7)))]  # (follow-through: it whips)
    ctx.saws = getattr(ctx, "saws", []) + [dict(id=n, arm=ga, blade=gb, spin=gb, joints=J, slots=slots, slot=float(s.get("slot", 0.9)), pivot=[round(v_, 3) for v_ in P0], axis=A, amp=amp,
                                               period=float(s.get("period", 3.2)), phase=float(s.get("phase", 0.0)), center=[round(v_, 3) for v_ in C], radius=round(R, 3), rpm=float(s.get("rpm", 240.0)),
                                               note="joint k turns its group and every later one about axis through its own pivot by amp_k sin(2 pi (t + phase) / period - lag_k) degrees; the spin group also turns rpm about the axis through the blade centre; kill within radius of the blade centre and 0.7 m of its plane (normal = axis)")]
    ctx.notes.append(f"{n}: ceiling saw {D:.1f} m, jointed arm (shoulder {amp:.0f} deg) across [{ax_}, {az_}]")


@structure("spinner", pad=False)
def spinner(ctx, s, x, y, z, yaw):
    """Stage 98: the spinner deck (on a round / octagonal platform whose top is position y, deck radius "radius"): a
    central tower (machine base with a glowing ring, a glowing core in a glass shell, a cap with four pipes curling out
    and down) and a rotor of "arms" hazard-striped bars at shin height ending in spiked balls, sweeping round the deck
    at "rpm". A bar is low enough to jump over; the balls are not. Four hovering pads with pink thrusters sit off the
    deck on the diagonals ("pads": diameter, "bridge": catwalk length), each joined by a grate catwalk. level.json
    "sweepers": the runtimes turn the rotor and kill whoever a bar or a ball hits (effect "sweeper")."""
    n = s["id"]; R = float(s.get("radius", 11.0)); T = y; st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    gl = ctx.role("glow"); stripe = ctx.role("stripe"); W = _W(x, 0, z, yaw)
    if s.get("floor") and s.get("floor_material"):  # Stage 105: the deck the maces sweep gets its own (scraped) surface
        for o in ctx.objects:
            if o["name"] == s["floor"] + "_Floor": o["material"] = ctx.role(s["floor_material"])
    # --- tower (static)
    ctx.add(n + "_HubBase", "cylinder", [x, T, z], [3.9, 1.0, 3.9], "machine", sections=12, **st)
    ctx.add(n + "_HubRing", "cylinder", [x, T + 0.62, z], [4.0, 0.22, 4.0], gl, sections=12, **vs)
    ctx.add(n + "_Neck", "cylinder", [x, T + 1.0, z], [2.5, 1.05, 2.5], "structure_b", sections=12, **st)
    ctx.add(n + "_Core", "cylinder", [x, T + 2.0, z], [1.5, 2.9, 1.5], gl, sections=10, **dict(st, outline=False))
    ctx.add(n + "_Glass", "cylinder", [x, T + 2.0, z], [2.3, 2.9, 2.3], ctx.role("glass_clear"), sections=10, double_sided=True, outline=False, collision=False, **st)
    for k, yy in enumerate((T + 2.0, T + 4.75)): ctx.add(f"{n}_Band_{k + 1}", "cylinder", [x, yy - 0.12, z], [2.65, 0.3, 2.65], "machine", sections=12, **dict(st, outline=False))
    pr = s.get("press")
    if pr:  # Stage 103: an anvil for the ceiling press - a lower cap, a hazard rim and the red strike plate it slams onto
        ctx.add(n + "_Cap", "cylinder", [x, T + 4.9, z], [3.0, 0.7, 3.0], "machine", sections=12, **st)
        ctx.add(n + "_CapRim", "cylinder", [x, T + 5.2, z], [3.2, 0.3, 3.2], stripe, sections=12, **dict(vs, outline=False))
        ctx.add(n + "_Strike", "cylinder", [x, T + 5.6, z], [1.9, 0.4, 1.9], gl, sections=10, **dict(vs, outline=False))
    else:
        ctx.add(n + "_Cap", "cylinder", [x, T + 4.9, z], [3.0, 0.9, 3.0], "machine", sections=12, **st)
    for k in range(4):  # pipes: up out of the cap (out of its side under a press), across, down into a valve box
        a = yaw + 45 + 90 * k; P0 = _W(x, 0, z, a)
        if pr:
            ctx.add(f"{n}_PipeOut_{k + 1}", "cylinder", P0(0, T + 5.3, 1.4), [0.5, 1.9, 0.5], "pipe", rot=[90, a, 0], sections=8, **vs)
            ctx.add(f"{n}_PipeBand_{k + 1}", "cylinder", P0(0, T + 5.3, 2.2), [0.62, 0.3, 0.62], gl, rot=[90, a, 0], sections=8, **vs)
            ctx.add(f"{n}_PipeDown_{k + 1}", "cylinder", P0(0, T + 5.1, 3.3), [0.5, 0.45, 0.5], "pipe", sections=8, **vs)
        else:
            ctx.add(f"{n}_PipeUp_{k + 1}", "cylinder", P0(0, T + 5.7, 0.9), [0.5, 1.0, 0.5], "pipe", sections=8, **vs)
            q = P0(0, T + 6.45, 0.9); ctx.add(f"{n}_PipeOut_{k + 1}", "cylinder", q, [0.5, 2.4, 0.5], "pipe", rot=[90, a, 0], sections=8, **vs)
            ctx.add(f"{n}_PipeBand_{k + 1}", "cylinder", P0(0, T + 6.45, 2.1), [0.62, 0.3, 0.62], gl, rot=[90, a, 0], sections=8, **vs)
            ctx.add(f"{n}_PipeDown_{k + 1}", "cylinder", P0(0, T + 5.1, 3.3), [0.5, 1.6, 0.5], "pipe", sections=8, **vs)
        ctx.add(f"{n}_Valve_{k + 1}", "box", P0(0, T + 4.2, 3.3), [0.9, 0.9, 0.9], "machine", rot=[0, a, 0], **vs)
    # --- rotor (moves): collar + arms + spiked balls
    gr = n + "_Rotor"; mr = dict(collision=False, mobile={"group": gr}); arms = [float(v) for v in s.get("arms", [0, 90, 180, 270])]
    by = float(s.get("bar_y", 0.72)); bh = float(s.get("bar_half", 0.22)); r0 = 1.3; br = float(s.get("ball", 1.36)) / 2; r1 = R - 0.4 - br; bly = by  # Stage 104: maces ON the poles' axis
    rc = br * 0.66; mace = ctx.role("mace"); nl = dict(mr, outline=False); pole_mat = ctx.role(s.get("pole_material", "stripe"))
    ctx.add(gr + "_Collar", "cylinder", [x, T + by - 0.35, z], [3.0, 0.7, 3.0], "machine", sections=12, **mr)
    for k, a0 in enumerate(arms):  # Stage 104 (concept art): a round striped pole out of a socket in the hub, a flanged coupling into a gunmetal mace
        a = yaw + a0; P0 = _W(x, 0, z, a); K_ = lambda nm, sh, r, sz, mat, kw=mr, sec=8: ctx.add(f"{gr}_{nm}_{k + 1}", sh, P0(0, T + by, r), sz, mat, rot=[90, a, 0], sections=sec, **kw)
        ctx.add(f"{gr}_Arm_{k + 1}", "pole", P0(0, T + by, r0), [2 * bh, r1 - r0, 2 * bh], pole_mat, rot=[90, a, 0], sections=10, uv_len=1.6, **mr)  # Stage 106: wound hazard stripes
        K_("Root", "cylinder", 1.8, [0.66, 0.55, 0.66], "machine")
        K_("Socket", "cylinder", r1 - rc - 0.32, [0.54, 0.44, 0.54], "machine")
        K_("Flange", "cylinder", r1 - rc - 0.32, [0.72, 0.09, 0.72], "machine", nl)
        K_("Band", "cylinder", r1 - 0.08, [2 * rc + 0.08, 0.16, 2 * rc + 0.08], "machine", nl, 12)
        K_("Seam", "cylinder", r1 - 0.03, [2 * rc + 0.1, 0.06, 2 * rc + 0.1], gl, nl, 12)
        c = P0(0, T + by, r1)
        ctx.add(f"{gr}_Ball_{k + 1}", "mace", c, [2 * br] * 3, mace, rot=[0, a, 0], **nl)
        ctx.add(f"{gr}_Tips_{k + 1}", "mace_tips", c, [2 * br] * 3, gl, rot=[0, a, 0], **nl)
    drive = _press(ctx, n, x, T, z, yaw, pr, gl, stripe) if pr else None
    ctx.sweepers = getattr(ctx, "sweepers", []) + [dict(id=n, group=gr, center=[round(x, 3), round(T, 3), round(z, 3)], rpm=float(drive["peak_rpm"] if drive else s.get("rpm", 6.0)), phase=float(s.get("phase", 0.0)), **({"drive": drive} if drive else {}),
                                                       arms=[round(yaw + a, 2) for a in arms], r0=r0, r1=round(r1, 3), bar_y=by, bar_half=bh, ball_r=round(br, 3), ball_y=round(bly, 3),
                                                       note="angle(t) = arm + rpm * 6 * t deg (level yaw convention: direction (sin, cos)); a bar kills a body it overlaps (jump over it), a ball kills within ball_r")]
    # --- hovering pads on the diagonals + grate catwalks
    pd = float(s.get("pads", 8.0)); bl = float(s.get("bridge", 3.5)); Dp = R + bl + pd / 2; ctx.spinner_pads = getattr(ctx, "spinner_pads", {})
    lift = s.get("lift_pad") or {}; ctx.lifts = getattr(ctx, "lifts", [])
    for k in range(4):
        a = yaw + 45 + 90 * k; P0 = _W(x, 0, z, a); c = P0(0, 0, Dp); pre = f"{n}_Pad_{k + 1}"; ctx.spinner_pads[f"{n}_{k + 1}"] = [c[0], T, c[2]]
        pr8 = [0, yaw + 22.5, 0]  # Stage 108: octagon flats (not corners) face the bridge and the four bearings
        ps, pv = st, vs; fl_ = pre + "_Flame"; flo = s.get("float_pads"); bob_ = None
        if flo: bob_ = dict(bob=[float(flo.get("amp", 0.28)), round(float(flo.get("period", 2.4)) + 0.27 * k, 3)], phase=round(0.9 * k, 3), tilt=float(flo.get("tilt", 2.2)), yaw=float(flo.get("yaw", 2.0)), flame=fl_, flame_y=round(T - 3.7, 3))
        floating = bool(flo) and int(lift.get("pad", 0)) != k + 1
        if floating:  # Stage 123: a floating pad - bobs and sways like the jet screen; ONE skinned rig for all of them (a bone per pad + per flame); colliders move with it (runtimes)
            rg = n + "_FloatRig"; jn, fj = pre + "_FJ", pre + "_FF"
            if not getattr(ctx, "_float_joints", None): ctx._float_joints = [dict(name=n + "_FRoot", parent=None, pivot=[round(x, 3), round(T, 3), round(z, 3)], axis=[0.0, 1.0, 0.0])]
            ctx._float_joints += [dict(name=jn, parent=n + "_FRoot", pivot=[round(c[0], 3), round(T, 3), round(c[2], 3)], axis=[0.0, 1.0, 0.0]),
                                  dict(name=fj, parent=jn, pivot=[round(c[0], 3), round(T - 3.7, 3), round(c[2], 3)], axis=[0.0, 1.0, 0.0])]
            ps = dict(mobile={"group": rg, "joint": jn}, floater=rg); pv = dict(ps, collision=False, outline=False)
            ctx._float_pads = getattr(ctx, "_float_pads", []) + [dict(joint=jn, flame_joint=fj, center=[round(c[0], 3), round(T, 3), round(c[2], 3)], deck_radius=round(pd / 2, 3), **bob_)]
        if int(lift.get("pad", 0)) == k + 1:  # Stage 108: this pad is a lift - its parts ride one group (runtime: "lifts"); the deck's collider is the runtime's
            lg = pre + "_Lift"; ps = dict(mobile={"group": lg}, lift=lg); pv = dict(ps, collision=False, outline=False)
            top = float(lift["top"]); bm = P0(0, T, (R + Dp - pd / 2) / 2)
            ctx.lifts.append(dict(id=lg, group=lg, center=[round(c[0], 3), round(T, 3), round(c[2], 3)], radius=round(pd / 2 * math.cos(math.pi / 8) - 0.3, 3), deck_radius=round(pd / 2, 3),
                                  bottom=round(T, 3), top=top, travel=round(top - T, 3), duration=float(lift.get("duration", 3.6)), wait=float(lift.get("wait", 0.8)),
                                  calls=[dict(at="bottom", center=[round(v, 3) for v in bm], radius=float(lift.get("call_radius", 3.2)))], links=[], **(bob_ or {}),
                                  note="stand on it 'wait' s -> it travels (smoothstep, 'duration' s) to the other end; a player in a call zone brings it to that end when it is empty; carries whoever stands on it"))
        ctx.add(pre + "_Deck", "cylinder", [c[0], T - 0.6, c[2]], [pd, 0.6, pd], "deck", sections=8, rot=pr8, **ps)
        ctx.add(pre + "_Rim", "cylinder", [c[0], T - 0.95, c[2]], [pd + 0.16, 0.42, pd + 0.16], stripe, sections=8, rot=pr8, **pv)
        ctx.add(pre + "_Hull", "frustum", [c[0], T - 3.0, c[2]], [pd - 0.4, 2.05, pd - 0.4], "structure_b", sections=8, bottom_scale=0.42, rot=pr8, **ps)
        ctx.add(pre + "_GlowBand", "frustum", [c[0], T - 2.1, c[2]], [pd * 0.8, 0.35, pd * 0.8], gl, sections=8, bottom_scale=0.92, rot=pr8, **pv)
        ctx.add(pre + "_Thruster", "cylinder", [c[0], T - 3.7, c[2]], [1.4, 0.75, 1.4], "machine", sections=8, rot=pr8, **pv)
        if flo and floating: ctx.add(pre + "_Jet", "frustum", [c[0], T - 4.7, c[2]], [1.1, 1.0, 1.1], gl, sections=8, bottom_scale=0.15, rot=pr8, collision=False, outline=False, mobile={"group": rg, "joint": fj})  # flickers (its bone)
        elif flo: ctx.add(pre + "_Jet", "frustum", [c[0], T - 4.7, c[2]], [1.1, 1.0, 1.1], gl, sections=8, bottom_scale=0.15, rot=pr8, collision=False, outline=False, mobile={"group": fl_})  # (the lift pad's flame: its own group)
        else: ctx.add(pre + "_Jet", "frustum", [c[0], T - 4.7, c[2]], [1.1, 1.0, 1.1], gl, sections=8, bottom_scale=0.15, rot=pr8, **pv)
        gap_ = float(flo.get("gap", 0.15)) if flo else None  # Stage 124: floating pads keep a small gap - the bridge stops short of the pad's flat instead of tucking under it
        q0 = P0(0, 0, R - 0.5); q1 = P0(0, 0, Dp - pd / 2 * math.cos(math.pi / 8) - gap_ if flo else Dp - pd / 2 + 0.6); m = [(q0[i] + q1[i]) / 2 for i in range(3)]; L = math.dist(q0, q1)
        ctx.add(pre + "_Bridge", "box", [m[0], T - 0.33, m[2]], [2.6, 0.3, L], "grate", rot=[0, a, 0], **st)  # 3 cm under the decks: no shared faces
        # Stage 106: the side rails run edge to edge - from the deck's edge (its octagon's flat on this bearing) to the
        # pad's facing flat - with a post at each end where they meet the decks
        e0 = float(s.get("deck_apothem", R)) - 0.05; e1 = Dp - pd / 2 * math.cos(math.pi / 8) + (-gap_ - 0.02 if flo else 0.05); Lr = e1 - e0
        for sd in (-1, 1):
            for nm, rr, ln, wd, hh in (("BridgeRail", (e0 + e1) / 2, Lr, 0.08, 0.7), ("BridgePost0", e0 + 0.09, 0.18, 0.18, 0.9), ("BridgePost1", e1 - 0.09, 0.18, 0.18, 0.9)):
                c_ = P0(sd * 1.38, 0, rr); ctx.add(f"{pre}_{nm}_{'LR'[sd > 0]}", "box", [c_[0], T - 0.03, c_[2]], [wd, hh, ln], "rail", rot=[0, a, 0], **dict(st, outline=False))
        ctx.landings.append((round(c[0], 3), round(c[2], 3), pd / 2))
    if getattr(ctx, "_float_pads", None):  # Stage 123: the floating pads' rig + record
        rg = n + "_FloatRig"; ctx.skeletons = getattr(ctx, "skeletons", {}); ctx.skeletons[n + "_Float"] = dict(groups=[rg], joints=ctx._float_joints, kind="float")
        ctx.floaters = getattr(ctx, "floaters", []) + [dict(id=rg, group=rg, skeleton=n + "_Float", pads=ctx._float_pads,
                                                            note="per pad: joint offset (0, amp sin(2 pi (t + phase) / period), 0), yaw +-yaw, tilt +-tilt (about the deck centre); flame_joint scale y flickers")]
        ctx._float_pads, ctx._float_joints = [], []
    for k in range(8):  # lamp posts round the rim, between the catwalks
        a = yaw + 22.5 + 45 * k
        if s.get("ramp_yaw") is not None and abs(((a - float(s["ramp_yaw"]) + 180) % 360) - 180) < 30: continue
        P0 = _W(x, 0, z, a); q = P0(0, 0, float(s.get("post_r", R - 0.55)))  # Stage 104: out on the deck's corners, clear of the maces' sweep
        ctx.add(f"{n}_Post_{k + 1}", "box", [q[0], T, q[2]], [0.45, 1.1, 0.45], "machine", rot=[0, a, 0], **st)
        ctx.add(f"{n}_PostLamp_{k + 1}", "box", [q[0], T + 1.1, q[2]], [0.5, 0.35, 0.5], gl, rot=[0, a, 0], **vs)
    ctx.notes.append(f"{n}: spinner, {len(arms)} arms " + (f"driven by a ceiling press (peak {drive['peak_rpm']} rpm, still {drive['still']:.1f} s per {drive['period']} s)" if drive else f"at {s.get('rpm', 6.0)} rpm") + ", 4 hovering pads")


def press_profile(D, t):
    """Stage 103: the press-driven spinner, shared by the runtimes (viewer.html, apply_effects.gd) and the checks.
    u = (t + phase) mod period: the ram slams down over "slam" s (accelerating), holds "hold" s, then rises over "rise"
    s (eased); the rotor spins up over "spin_up" s from the impact, holds "peak" deg/s while the ram is down, then coasts
    to a stop over "spin_down" s from the release - each cycle turns it a whole number of turns ("turns"), so it always
    stops in the same pose. Returns (ram offset (<= 0, m), rotor angle (deg))."""
    P, sl, ho, ri, su, sd, w = (float(D[k]) for k in ("period", "slam", "hold", "rise", "spin_up", "spin_down", "peak"))
    tp = t + float(D.get("phase", 0.0)); k = math.floor(tp / P); u = tp - k * P; tr = float(D["travel"])
    if u < sl: off = -tr * (u / sl) ** 2
    elif u < sl + ho: off = -tr
    elif u < sl + ho + ri: f = (u - sl - ho) / ri; off = -tr * (1 - f * f * (3 - 2 * f))
    else: off = 0.0
    d = u - sl
    if d <= 0: th = 0.0
    elif d < su: th = w * d * d / (2 * su)
    elif d < ho: th = w * (d - su / 2)
    elif d < ho + sd: e = d - ho; th = w * (ho - su / 2) + w * (e - e * e / (2 * sd))
    else: th = w * (ho - su / 2 + sd / 2)
    return off, k * 360.0 * float(D["turns"]) + th


def _press(ctx, n, x, T, z, yaw, pr, gl, stripe):
    """Stage 103: a giant telescoping hydraulic press hung from the ceiling over the spinner tower: a ceiling plate and
    an octagonal crown (glowing ring, hazard band), a barrel with hydraulic lines and gusset braces, a middle stage
    (moves half the stroke) and an inner stage carrying the head - an octagonal block with a tapered top, a hazard
    skirt, four guide sleeves running on four guide columns down from the crown, and a striker with a glowing ring that
    lands on the tower's red strike plate. Returns the drive record (level.json sweepers[].drive)."""
    C = float(pr.get("ceiling", 34.5)); yc = T + 6.0  # the strike plate's top
    st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    gm, gr_ = n + "_PressMid", n + "_Ram"; mm = dict(collision=False, mobile={"group": gm}); mr = dict(collision=False, mobile={"group": gr_})
    cyl = lambda nm, y0, h, dia, mat, kw, sec=10: ctx.add(nm, "cylinder", [x, y0, z], [dia, h, dia], mat, sections=sec, **kw)
    # --- static: ceiling plate, crown, barrel, braces, hydraulic lines, guide columns
    paint = ctx.role("arm_yellow")  # Stage 104: worn yellow paint on the press's rings (the hazard chevrons stay on the decks)
    cyl(n + "_PressPlate", C - 0.5, 0.5, 9.0, "machine", st, 8); cyl(n + "_PressPlateRim", C - 0.75, 0.3, 9.2, paint, vs, 8)
    cyl(n + "_Crown", C - 3.3, 2.8, 7.2, "structure_b", st, 8); cyl(n + "_CrownGlow", C - 2.3, 0.3, 7.3, gl, vs, 8)
    cyl(n + "_CrownBand", C - 3.45, 0.55, 7.4, paint, vs, 8)
    for k, (y0, y1) in enumerate(((C - 7.0, C - 5.12), (C - 5.12, C - 4.21), (C - 4.21, C - 3.25))): cyl(f"{n}_Barrel_{k + 1}", y0, y1 - y0, 3.6, "machine", st, 12)  # joins under the band / gauge rings
    cyl(n + "_BarrelBand", C - 5.3, 0.35, 3.9, "machine", vs, 12); cyl(n + "_Gland", C - 7.3, 0.55, 4.0, "machine", vs, 12)
    cyl(n + "_GaugeGlow", C - 4.3, 0.18, 3.7, gl, vs, 12)
    for k in range(4):
        a = yaw + 45 + 90 * k; P0 = _W(x, 0, z, a)
        lo, hi = P0(0, C - 6.6, 1.85), P0(0, C - 3.3, 3.3); th = math.degrees(math.atan2(1.45, 3.3))  # gusset brace: barrel -> crown rim
        ctx.add(f"{n}_Brace_{k + 1}", "cylinder", lo, [0.55, math.hypot(1.45, 3.3), 0.55], "machine", rot=[th, a, 0], sections=6, **vs)
        ctx.add(f"{n}_HydLine_{k + 1}", "cylinder", P0(0, C - 6.9, 1.9), [0.24, 3.65, 0.24], "pipe", sections=6, **vs)
    travel = round((C - 15.45) - yc, 3)  # the striker's lower face at rest (C - 15.45) -> the strike plate
    for k in range(4):  # guide columns the head's sleeves run on, a stop collar at the foot
        P0 = _W(x, 0, z, yaw + 90 * k); q = P0(0, 0, 2.75)
        ctx.add(f"{n}_Guide_{k + 1}", "cylinder", [q[0], yc + 0.1, q[2]], [0.42, C - 3.3 - yc - 0.1, 0.42], "pipe", sections=8, **vs)
        ctx.add(f"{n}_GuideStop_{k + 1}", "cylinder", [q[0], yc - 0.0, q[2]], [0.8, 0.4, 0.8], "machine", sections=8, **vs)
    # --- middle stage (half the stroke)
    cyl(n + "_StageMid", C - 10.2, 6.7, 3.0, "pipe", mm, 12); cyl(n + "_StageMidRing", C - 10.4, 0.4, 3.35, "pipe", mm, 12)
    # --- inner stage + head (the full stroke)
    cyl(n + "_StageIn", C - 13.3, 6.8, 2.3, "machine", mr, 12)
    cyl(n + "_Head", C - 14.9, 1.6, 6.4, "machine", mr, 8)
    ctx.add(n + "_HeadTaper", "frustum", [x, C - 13.3, z], [2.9, 0.7, 2.9], "machine", sections=8, bottom_scale=6.0 / 2.9, **mr)
    cyl(n + "_Skirt", C - 14.85, 0.45, 6.6, paint, dict(mr, outline=False), 8)
    cyl(n + "_Striker", C - 15.45, 0.25, 2.2, "machine", mr, 10); cyl(n + "_StrikerNeck", C - 15.2, 0.3, 1.9, "machine", mr, 10)
    cyl(n + "_StrikerGlow", C - 15.28, 0.16, 2.45, gl, dict(mr, outline=False), 10)
    for k in range(4):
        P0 = _W(x, 0, z, yaw + 90 * k); q = P0(0, 0, 2.75)
        ctx.add(f"{n}_Sleeve_{k + 1}", "cylinder", [q[0], C - 15.0, q[2]], [0.95, 1.9, 0.95], "machine", sections=8, **mr)
        P1 = _W(x, 0, z, yaw + 45 + 90 * k); q = P1(0, 0, 3.05)  # warning lamps on the head's diagonals (blink before the slam)
        ctx.add(f"{n}_RamLamp_{k + 1}", "box", [q[0], C - 14.2, q[2]], [0.7, 0.45, 0.35], gl, rot=[0, yaw + 45 + 90 * k, 0], **dict(mr, outline=False))
    P_, sl, ho, ri = float(pr.get("period", 9.5)), float(pr.get("slam", 0.35)), float(pr.get("hold", 2.4)), float(pr.get("rise", 1.8))
    su, sd, turns = float(pr.get("spin_up", 0.35)), float(pr.get("spin_down", 3.0)), float(pr.get("turns", 4))
    w = 360.0 * turns / (ho - su / 2 + sd / 2)
    # Stage 105: steam nozzles - jets of steam shoot out of them (level.json drive.jets: [[pos, dir], ...] per set)
    def jet(a, r, y, dy):  # nozzle tip at radius r, height y on bearing a; direction outward, tipped dy
        P0 = _W(x, 0, z, a); p_ = P0(0, y, r); h = math.sqrt(max(0.0, 1 - dy * dy)); q = P0(0, 0, 1.0); o = P0(0, 0, 0.0)
        return [[round(v, 3) for v in p_], [round((q[0] - o[0]) * h, 3), round(dy, 3), round((q[2] - o[2]) * h, 3)]]
    gland, head, crown = [], [], []
    for k in range(4):
        a = yaw + 22.5 + 90 * k; P0 = _W(x, 0, z, a)
        ctx.add(f"{n}_GlandNozzle_{k + 1}", "cylinder", P0(0, C - 7.0, 1.9), [0.28, 0.5, 0.28], "pipe", rot=[90, a, 0], sections=6, **vs)
        ctx.add(f"{n}_GlandValve_{k + 1}", "box", P0(0, C - 7.18, 2.12), [0.42, 0.36, 0.3], "machine", rot=[0, a, 0], **vs)
        gland.append(jet(a, 2.42, C - 7.0, -0.32))
        ctx.add(f"{n}_HeadNozzle_{k + 1}", "cylinder", P0(0, C - 14.0, 3.0), [0.3, 0.6, 0.3], "machine", rot=[90, a, 0], sections=6, **mr)
        head.append(jet(a, 3.62, C - 14.0 - travel, 0.18))
        a2 = yaw + 67.5 + 90 * k; P2 = _W(x, 0, z, a2)
        ctx.add(f"{n}_CrownVent_{k + 1}", "cylinder", P2(0, C - 3.85, 3.0), [0.34, 0.55, 0.34], "pipe", sections=6, **vs)
        crown.append(jet(a2, 3.0, C - 3.9, -0.88))
    return dict(press=gr_, stages=[{"group": gm, "frac": 0.5}, {"group": gr_, "frac": 1.0}], lamps=f"{gr_}__{gl}", travel=travel, period=P_, slam=sl, hold=ho, rise=ri,
                spin_up=su, spin_down=sd, turns=turns, peak=round(w, 3), peak_rpm=round(w / 6.0, 2), warn=float(pr.get("warn", 1.2)), phase=float(pr.get("phase", 0.0)),
                still=round(P_ - sl - ho - sd, 2), shake=float(pr.get("shake", 28.0)), jets=dict(gland=gland, head=head, crown=crown),
                note="press_profile(): u = (t + phase) mod period; ram offset -travel (u/slam)^2, held, eased back over rise; each stage moves offset * frac; "
                     "rotor angle = whole-turn cycles + spin-up / peak / coast-down from the impact; the head's glow blinks for 'warn' s before each slam; "
                     "camera shake within 'shake' m on impact")


@structure("overlook", pad=False)
def overlook(ctx, s, x, y, z, yaw):
    """Stage 108: a corner observation balcony high over the hall ("rect" [x0, z0, x1, z1] against two walls, deck top
    "top"), carried by columns down into the liquid ("columns" [[x, z], ...]) and diagonal braces off the walls
    ("braces" [[x, z, dir_x, dir_z], ...]: wall point, out along dir). Pink railings on its open edges, viewing
    binoculars ("viewers" [[x, z, yaw], ...]). A grate gantry ("gantry": {"lift": <lift id>, "width", "supports": [x...]})
    runs from the deck's west edge to where that lift pad stops at the top; a call post with a lamp at its end calls the
    lift (calls + nav link appended to level.json lifts)."""
    n = s["id"]; x0, z0, x1, z1 = (float(v) for v in s["rect"]); top = float(s["top"]); st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    stripe, gl, lamp = ctx.role("stripe"), ctx.role("glow"), ctx.role("glow_yellow"); cx, cz = (x0 + x1) / 2, (z0 + z1) / 2; W_, D_ = x1 - x0, z1 - z0
    ctx.add(n + "_Deck", "box", [cx, top - 0.6, cz], [W_, 0.6, D_], "deck", **st)
    ctx.add(n + "_EdgeW", "box", [x0 - 0.04, top - 0.55, cz], [0.08, 0.5, D_], stripe, **vs)
    ctx.add(n + "_EdgeN", "box", [cx, top - 0.55, z0 - 0.04], [W_ + 0.16, 0.5, 0.08], stripe, **vs)
    gy = top - 0.6 - 0.7  # girders under the deck
    cols = [[float(a), float(b)] for a, b in s.get("columns", [])]
    for k, zz in enumerate(sorted({round(c[1], 3) for c in cols})): ctx.add(f"{n}_GirderX_{k + 1}", "box", [cx, gy, zz], [W_ - 0.1, 0.7, 0.45], "frame", bevel=False, **vs)
    for k, xx in enumerate(sorted({round(c[0], 3) for c in cols})): ctx.add(f"{n}_GirderZ_{k + 1}", "box", [xx, gy, cz], [0.45, 0.7, D_ - 0.1], "frame", bevel=False, **vs)
    liq = float(s.get("liquid", 0.0))
    for k, (px, pz) in enumerate(cols):  # columns: footing in the liquid, shaft in two lengths joined under a hazard band
        ctx.add(f"{n}_Foot_{k + 1}", "frustum", [px, liq, pz], [1.0, 1.4, 1.0], "structure_b", bottom_scale=1.6, **st)
        ctx.add(f"{n}_Column_{k + 1}", "box", [px, liq + 1.4, pz], [0.9, gy - 1.6 - liq - 1.4, 0.9], "structure_b", **st)
        ctx.add(f"{n}_ColumnTop_{k + 1}", "box", [px, gy - 1.6, pz], [0.9, 1.6, 0.9], "structure_b", **st)
        ctx.add(f"{n}_ColumnBand_{k + 1}", "box", [px, gy - 1.85, pz], [1.0, 0.5, 1.0], stripe, **vs)
        ctx.add(f"{n}_ColumnLamp_{k + 1}", "box", [px, gy - 0.12, pz], [0.98, 0.2, 0.98], gl, **vs)  # glowing collar where it meets the girders
    for k, (wx, wz, dx, dz) in enumerate(s.get("braces", [])):  # wall braces: from the wall up and out to the girders
        ly, hy, out = top - 4.6, gy, 3.6; a = math.degrees(math.atan2(dx, dz)); th = math.degrees(math.atan2(out, hy - ly))
        ctx.add(f"{n}_Brace_{k + 1}", "cylinder", [wx, ly, wz], [0.34, math.hypot(out, hy - ly), 0.34], "frame", rot=[th, a, 0], sections=6, **vs)
        ctx.add(f"{n}_BraceFoot_{k + 1}", "box", [wx, ly - 0.35, wz], [0.6 if abs(dz) > 0.5 else 0.24, 0.7, 0.24 if abs(dz) > 0.5 else 0.6], "machine", **vs)
    # railings on the open edges (gap where the gantry arrives)
    G = s.get("gantry") or {}; gw = float(G.get("width", 3.0)); lf = next((l_ for l_ in getattr(ctx, "lifts", []) if l_["id"] == G.get("lift")), None)
    gz = lf["center"][2] if lf else None
    def rail_run(nm, a_, b_, fixed, along_x):
        L_ = b_ - a_
        if L_ < 0.4: return
        m_ = (a_ + b_) / 2; P = (lambda u: [u, top, fixed]) if along_x else (lambda u: [fixed, top, u])
        sz = (lambda l, w, h: [l, h, w]) if along_x else (lambda l, w, h: [w, h, l])
        for hh, nm2 in ((0.55, "Low"), (1.25, "High")):  # top rail above a jump: nobody hops it
            q = P(m_); ctx.add(f"{n}_{nm}_{nm2}", "box", [q[0], top + hh - 0.04, q[2]], sz(L_, 0.08, 0.08), "rail", bevel=False, **dict(st, outline=False))
        npost = max(2, int(L_ / 2.4) + 1)
        for k in range(npost):
            q = P(a_ + 0.06 + (L_ - 0.12) * k / (npost - 1)); ctx.add(f"{n}_{nm}_Post_{k + 1}", "box", [q[0], top, q[2]], [0.12, 1.32, 0.12], "rail", bevel=False, **dict(st, outline=False))
    if gz is not None:
        rail_run("RailW1", z0, gz - gw / 2, x0 + 0.1, False); rail_run("RailW2", gz + gw / 2, z1, x0 + 0.1, False)
    else: rail_run("RailW", z0, z1, x0 + 0.1, False)
    if "N" not in s.get("open_edges", []): rail_run("RailN", x0, x1, z0 + 0.1, True)  # Stage 109: "open" edges (e.g. onto a rising arena) get no railing
    for k, (vx, vz, vyaw) in enumerate(s.get("viewers", [])):  # coin-op binoculars on a post
        W = _W(vx, 0, vz, vyaw)
        ctx.add(f"{n}_Viewer_{k + 1}_Post", "cylinder", [vx, top, vz], [0.22, 1.05, 0.22], "machine", sections=8, **st)
        ctx.add(f"{n}_Viewer_{k + 1}_Head", "box", [vx, top + 1.05, vz], [0.62, 0.42, 0.45], "machine", rot=[0, vyaw, 0], **vs)
        for sd in (-1, 1):
            q = W(sd * 0.15, top + 1.27, 0.2); ctx.add(f"{n}_Viewer_{k + 1}_Eye{'LR'[sd > 0]}", "cylinder", q, [0.17, 0.3, 0.17], lamp, rot=[90, vyaw, 0], sections=8, **vs)
        q = W(0, top + 1.32, -0.24); ctx.add(f"{n}_Viewer_{k + 1}_Lamp", "box", q, [0.2, 0.08, 0.06], gl, rot=[0, vyaw, 0], **vs)
    ctx.walkable.append(dict(name=n + "_Deck", min=[round(x0, 3), round(z0, 3)], max=[round(x1, 3), round(z1, 3)], y=top))
    # Stage 117/118: wall TVs moved up here ("move_units": wall units whose TV parts leave the walls) and "wall_screens"
    # [[x, z, yaw, width], ...]: built into the wall above the deck at (x, z) on its face, facing straight out (yaw):
    # the moulded TV flush in a heavy machine surround with a glowing inner trim, a hazard ledge, a header with status
    # lamps, speaker columns with glow strips and conduits up the wall; raised "screen_lift" so heads clear it)
    mv = tuple(s.get("move_units", []))
    if mv:
        drop = {o["name"] for o in ctx.objects if any(o["name"].startswith(u + "_") and o["name"][len(u) + 1:].split("_")[0] in ("Body", "Screen", "Arm", "Cable") for u in mv)}
        ctx.objects[:] = [o for o in ctx.objects if o["name"] not in drop]; ctx.names -= drop
    from architecture import screen_slot
    for k, sc in enumerate(s.get("wall_screens", [])):  # Stage 118: built into the wall - flush, framed, facing straight out
        sx, sz, sy, tw = float(sc[0]), float(sc[1]), float(sc[2]), float(sc[3]) if len(sc) > 3 else 4.6
        W = _W(sx, 0, sz, sy); pre = f"{n}_WallScreen_{k + 1}"; bf, cf, depth = 0.07, 0.2, 0.4; W_ = tw / (1 - 2 * bf); H_ = W_ * 0.8; th = H_ * (1 - cf - bf * 1.33) * 0.98
        y0 = top + float(s.get("screen_lift", 2.2)); yy = y0 + H_ * cf; z0 = 0.03; fr = 0.42  # back 3 cm off the wall face; surround band
        def part(nm, lx, ly, lz, size, mat, **kw):  # lz: the part's BACK face (boxes are centred in depth; tv_body starts at its back)
            if kw.get("shape", "box") == "box": lz = lz + size[2] / 2
            q = W(lx, ly, lz); ctx.add(f"{pre}_{nm}", kw.pop("shape", "box"), q, size, mat, rot=[0, sy, 0], **dict(dict(collision=False, outline=False, **st), **kw))
        part("Body", 0, y0, z0, [W_, H_, depth], "tv_casing", shape="tv_body", border=bf, chin=cf, outline=True)
        reg, sid = screen_slot(ctx, "screen", "a" if k % 2 == 0 else "b")
        part("Glass", 0, yy + H_ * 0.003, z0 + depth - 0.10, [W_ * (1 - 2 * bf) * 0.995, th, 0], "screen", shape="panel", uv_region=reg, uv_shift=sid)
        for nm, lx, ly, w_, h_ in (("FrameT", 0, y0 + H_, W_ + 2 * fr, fr), ("FrameB", 0, y0 - fr, W_ + 2 * fr, fr), ("FrameL", -(W_ + fr) / 2, y0, fr, H_), ("FrameR", (W_ + fr) / 2, y0, fr, H_)):
            part(nm, lx, ly, z0, [w_, h_, 0.3], "machine", outline=True)  # heavy surround
        for nm, lx, ly, w_, h_ in (("TrimT", 0, y0 + H_ - 0.02, W_ + 0.12, 0.08), ("TrimB", 0, y0 - 0.06, W_ + 0.12, 0.08), ("TrimL", -(W_ + 0.06) / 2, y0, 0.08, H_), ("TrimR", (W_ + 0.06) / 2, y0, 0.08, H_)):
            part(nm, lx, ly, z0 + 0.3, [w_, h_, 0.05], gl)  # thin glowing inner trim, proud of the surround
        part("Ledge", 0, y0 - fr - 0.24, z0, [W_ + 2 * fr + 0.3, 0.24, 0.5], stripe)
        part("Header", 0, y0 + H_ + fr, z0, [W_ * 0.62, 0.55, 0.36], "machine", outline=True)
        for j, lx in enumerate((-0.9, -0.3, 0.3, 0.9)):
            part(f"HeaderLamp_{j + 1}", lx * W_ * 0.25, y0 + H_ + fr + 0.18, z0 + 0.34, [0.22, 0.18, 0.06], gl if j % 2 == 0 else ctx.role("glow_yellow"))
        for sd in (-1, 1):  # speaker columns with a glow strip, conduits up the wall
            cx_ = sd * (W_ / 2 + fr + 0.42); part(f"Speaker{'LR'[sd > 0]}", cx_, y0 - fr, z0, [0.7, H_ + 2 * fr, 0.34], "machine", outline=True)
            part(f"SpeakerGlow{'LR'[sd > 0]}", cx_, y0 + 0.2, z0 + 0.32, [0.12, H_ - 0.4, 0.05], gl)
            part(f"Conduit{'LR'[sd > 0]}", sd * W_ * 0.22, y0 + H_ + fr + 0.55, z0 + 0.12, [0.18, 2.6, 0.18], "pipe", shape="cylinder", sections=6)
    if lf:  # the gantry: along x from the deck's west edge to the lift pad's flat at the top
        ex = lf["center"][0] + lf["deck_radius"] * math.cos(math.pi / 8) + (0.15 if lf.get("bob") else 0.05); L_ = x0 - ex; mx = (x0 + ex) / 2  # Stage 124: room for a floating lift pad to bob
        ctx.add(n + "_Gantry", "box", [(ex + x0 - 0.02) / 2, top - 0.3, gz], [x0 - 0.02 - ex, 0.3, gw], "grate", **st)  # ends 2 cm short of the deck: no shared faces
        for sd in (-1, 1):
            ctx.add(f"{n}_Stringer_{'LR'[sd > 0]}", "box", [mx, top - 0.85, gz + sd * (gw / 2 - 0.15)], [L_ + 0.1, 0.55, 0.3], "frame", bevel=False, **vs)
            for hh, nm2 in ((0.55, "Low"), (1.25, "High")): ctx.add(f"{n}_GRail{nm2}_{'LR'[sd > 0]}", "box", [mx + 0.15, top + hh - 0.04, gz + sd * (gw / 2 - 0.06)], [L_ - 0.3, 0.08, 0.08], "rail", bevel=False, **dict(st, outline=False))
            for k in range(7):
                ctx.add(f"{n}_GPost_{'LR'[sd > 0]}_{k + 1}", "box", [ex + 0.35 + (L_ - 0.45) * k / 6, top, gz + sd * (gw / 2 - 0.06)], [0.12, 1.32, 0.12], "rail", bevel=False, **dict(st, outline=False))
        ctx.add(n + "_GantryThreshold", "box", [ex + 0.4, top, gz], [0.7, 0.03, gw - 0.3], stripe, **vs)
        for k, sx in enumerate(G.get("supports", [])):  # trestles under the gantry
            sx = float(sx); ctx.add(f"{n}_GFoot_{k + 1}", "frustum", [sx, liq, gz], [0.9, 1.2, 0.9], "structure_b", bottom_scale=1.6, **st)
            ctx.add(f"{n}_GLeg_{k + 1}", "box", [sx, liq + 1.2, gz], [0.75, top - 1.15 - liq - 1.2, 0.75], "structure_b", **st)
            ctx.add(f"{n}_GCross_{k + 1}", "box", [sx, top - 1.15, gz], [0.5, 0.3, gw + 0.2], "frame", bevel=False, **vs)
        cp = [ex + 1.1, top, gz + gw / 2 - 0.3]  # call post with a lamp, inside the rail near the gantry's end
        ctx.add(n + "_CallPost", "box", cp, [0.3, 1.35, 0.3], "machine", **st)
        ctx.add(n + "_CallLamp", "box", [cp[0], top + 1.35, cp[2]], [0.36, 0.3, 0.36], lamp, **vs)
        lf["calls"].append(dict(at="top", center=[round(ex + 1.6, 3), top, round(gz, 3)], radius=float(G.get("call_radius", 3.0))))
        lf["links"].append(dict(bottom=lf["center"], top=[round(ex + 1.0, 3), top, round(gz, 3)]))
        ctx.walkable.append(dict(name=n + "_Gantry", min=[round(ex, 3), round(gz - gw / 2, 3)], max=[round(x0, 3), round(gz + gw / 2, 3)], y=top))
    ctx.notes.append(f"{n}: corner overlook {W_:.1f} x {D_:.1f} m at {top} m" + (f", gantry {L_:.1f} m to lift {lf['id']}" if lf else ""))


GOOFS = [dict(peek=1.1, wig=9.0, hz=1.6, tilt=2.5, dir=30.0), dict(peek=0.7, wig=14.0, hz=2.4, tilt=4.0, dir=120.0),  # Stage 110: per-platform personalities
         dict(peek=1.4, wig=7.0, hz=1.2, tilt=3.5, dir=250.0), dict(peek=0.9, wig=12.0, hz=2.0, tilt=4.5, dir=330.0)]


def goofy_pose(pd, tk, rise_s, liq):
    """Stage 110: the "goofy" rise of an emerge-rig platform (reference for viewer.html / apply_effects.gd), tk seconds
    after its turn: it EMERGES until its top peeks 0.9 m out of the liquid (0.45 s, ease-out), LOOKS AROUND (wiggles
    about its vertical axis, bobbing, "peek" s), DUCKS 0.6 m (0.22 s), LAUNCHES past its rest height (back-out ease over
    rise_s, thinning as it shoots up), then SETTLES: squashes wide on landing and jiggles, bobs, and sways about a
    tilted axis ("dir") - all decaying. Returns (y offset, yaw deg, tilt deg, xz scale, colliders live)."""
    g = pd["goof"]; rise = pd["rise"]; top = pd["center"][1]; a, b, c, d = 0.45, g["peek"], 0.22, rise_s; offp = liq + 0.9 - top
    if tk < 0: return (-rise, 0.0, 0.0, 1.0, False)
    if tk < a: u = tk / a; return (-rise + (offp + rise) * (1 - (1 - u) ** 3), 0.0, 0.0, 1.0, False)
    tb = tk - a
    if tb < b: return (offp + 0.12 * math.sin(2 * math.pi * 1.5 * tb), g["wig"] * math.sin(2 * math.pi * g["hz"] * tb) * math.sin(math.pi * tb / b), 0.0, 1.0, False)
    tc = tb - b
    if tc < c: return (offp - 0.6 * math.sin(math.pi / 2 * tc / c), 0.0, 0.0, 1.0, False)
    td = tc - c
    if td < d:
        u = td / d; c1 = 1.9; e = 1 + (c1 + 1) * (u - 1) ** 3 + c1 * (u - 1) ** 2
        return ((offp - 0.6) * (1 - e), 0.0, 0.0, 1 - 0.12 * math.sin(math.pi * u), u >= 0.8)
    te = td - d
    if te > 4.0: return (0.0, 0.0, 0.0, 1.0, True)
    return (0.3 * math.sin(9 * te) * math.exp(-3.5 * te), 0.0, g["tilt"] * math.exp(-2.6 * te) * math.sin(7.5 * te), 1 + 0.16 * math.exp(-4 * te) * math.cos(13 * te), True)


def rust_grow(pd, tk, rise_s):
    """Stage 112: how far (0..1) the green rust has crept up a goofy riser's column: from "delay" s after it starts to
    settle, over "grow" s (smoothstep). Mirrored in viewer.html / apply_effects.gd."""
    r = pd.get("rust")
    if not r or tk < 0: return 0.0
    f = min(1.0, max(0.0, (tk - (0.45 + pd["goof"]["peek"] + 0.22 + rise_s) - r["delay"]) / r["grow"])); return f * f * (3 - 2 * f)


@structure("rising_arena", pad=False)
def rising_arena(ctx, s, x, y, z, yaw):
    """Stage 109/110: a battle arena that surges up out of the liquid (the "emerge" rig of rising_pads: one bone per
    platform + one per surge ring; Godot apply_effects.gd / viewer.html play it, colliders live once up). Square
    platforms: a big deck ("center" [x, z], "deck_size" m, top "top") on a square column and a tapered bowl with a glowing
    band and rim, and "satellites" [[bearing, size, slide], ...] against its sides (slid along them). Nothing stands on
    them (yet). They rise in order ("stagger", "rise_s") when a player comes within "trigger_radius" of "trigger";
    "style": "goofy" (default) gives each its own personality (GOOFS; goofy_pose)."""
    n = s["id"]; (cx, cz) = s["center"]; D = float(s.get("deck_size", 14.0)); top = float(s["top"]); liq = float(s.get("liquid", 1.0))
    gl = ctx.role("glow"); grp = n + "_Rig"; nc = dict(collision=False, outline=False); style = s.get("style", "goofy")
    joints = [dict(name=n + "_JRoot", parent=None, pivot=[round(cx, 3), round(liq, 3), round(cz, 3)], axis=[0.0, 1.0, 0.0])]; pads = []
    def platform(k, px, pz, d, rot, name=None, cap_mat="deck"):
        jn, rn = f"{n}_J{k}", f"{n}_R{k}"; pj, rj = dict(group=grp, joint=jn), dict(group=grp, joint=rn); pre = name or f"{n}_{'Deck' if k == 1 else f'Pad_{k - 1}'}"
        joints.append(dict(name=jn, parent=n + "_JRoot", pivot=[round(px, 3), round(liq, 3), round(pz, 3)], axis=[0.0, 1.0, 0.0]))
        joints.append(dict(name=rn, parent=n + "_JRoot", pivot=[round(px, 3), round(liq + 0.03, 3), round(pz, 3)], axis=[0.0, 1.0, 0.0]))
        r4 = [0, rot, 0]
        cd = d * 0.36; ctx.add(pre + "_Column", "cylinder", [px, 0.0, pz], [cd, top - 2.4, cd], "structure_b", sections=12, mobile=pj, **nc)  # Stage 112: round supports
        if style == "goofy" and s.get("rust", True):  # Stage 112: green rust creeping up from the slime line once it has settled (its own bone, scaled up)
            un = f"{n}_U{k}"; hb = float(s.get("rust_height", 1.8)); hs = hb / 0.89; y0 = liq + hb - hs
            joints.append(dict(name=un, parent=jn, pivot=[round(px, 3), round(y0, 3), round(pz, 3)], axis=[0.0, 1.0, 0.0]))
            ctx.add(pre + "_Rust", "pole", [px, y0, pz], [cd + 0.07, hs, cd + 0.07], ctx.role("corrosion"), sections=12, uv_mode="band", uv_len=float(s.get("rust_tile", 4.0)),
                    mobile=dict(group=grp, joint=un), **nc)
        ctx.add(pre + "_Bowl", "frustum", [px, top - 2.6, pz], [d - 0.6, 2.0, d - 0.6], "structure_b", bottom_scale=0.42, rot=r4, mobile=pj, **nc)
        ctx.add(pre + "_Band", "frustum", [px, top - 1.05, pz], [d - 0.4, 0.4, d - 0.4], gl, bottom_scale=0.94, rot=r4, mobile=pj, **nc)
        ctx.add(pre + "_Cap", "box", [px, top - 0.6, pz], [d, 0.6, d], cap_mat, rot=r4, mobile=pj)
        ctx.add(pre + "_Rim", "box", [px, top - 0.66, pz], [d + 0.16, 0.14, d + 0.16], gl, rot=r4, mobile=pj, **nc)
        ctx.add(pre + "_Surge", "cylinder", [px, liq + 0.03, pz], [d * 1.2, 0.04, d * 1.2], ctx.role("fall"), sections=8, mobile=rj, **nc)
        pd = dict(joint=jn, ring=rn, center=[round(px, 3), round(top, 3), round(pz, 3)], size=d, rise=round(top - liq + 1.0, 3), colliders=[pre + "_Cap"])
        if style == "goofy": pd["goof"] = dict(GOOFS[(k - 1) % len(GOOFS)])
        if style == "goofy" and s.get("rust", True): pd["rust"] = dict(bone=f"{n}_U{k}", delay=float(s.get("rust_delay", 1.2)), grow=float(s.get("rust_grow", 2.5)))
        pads.append(pd); ctx.landings.append((round(px, 3), round(pz, 3), d / 2))
    G_ = s.get("grid")
    if G_:  # Stage 111: a symmetric grid of equal square tiles (gladiator floor), rising ring by ring from the centre
        N_, d, gap = int(G_.get("n", 5)), float(G_.get("tile", 4.0)), float(G_.get("gap", 0.2)); h = (N_ - 1) / 2; D = N_ * d + (N_ - 1) * gap
        ring_delay = [float(v) for v in G_.get("ring_delay", [0.0, 0.6, 1.3, 2.0])]; k = 0
        for i in range(N_):
            for j in range(N_):
                ox, oz = (j - h) * (d + gap), (i - h) * (d + gap); r = int(max(abs(i - h), abs(j - h))); par = int(abs(i - h) + abs(j - h)) % 2
                accent = (r == 0 or (abs(i - h) == h and abs(j - h) == h)) and G_.get("accent", True)  # the centre and the four corners: hull-plated (a symmetric pattern)
                k += 1; platform(k, cx + ox, cz + oz, d, 0.0, name=f"{n}_Tile_{i + 1}{j + 1}", cap_mat="structure_b" if accent else "deck")
                pd = pads[-1]; pd["delay"] = round(ring_delay[min(r, len(ring_delay) - 1)] + 0.12 * par, 3); pd["grid"] = [i, j]
                if "goof" in pd:  # symmetric personalities: by ring and parity; sway radial (outward from the centre)
                    g = dict(GOOFS[(r + 2 * par) % len(GOOFS)]); g["dir"] = round((math.degrees(math.atan2(oz, ox)) + 90.0) % 360, 2) if r else 0.0; pd["goof"] = g
    else:
        platform(1, cx, cz, D, 0.0)
        for k, sat in enumerate(s.get("satellites", [])):
            bear, d = float(sat[0]), float(sat[1]); sl = float(sat[2]) if len(sat) > 2 else 0.0
            q = _W(cx, 0, cz, bear)(sl, 0, D / 2 + d / 2 + 0.1); platform(k + 2, q[0], q[2], d, bear)
    tr = s.get("trigger") or [cx, top, cz]
    ctx.skeletons = getattr(ctx, "skeletons", {}); ctx.skeletons[n] = dict(groups=[grp], joints=joints, kind="emerge")
    ctx.risers = getattr(ctx, "risers", []) + [dict(id=n, group=grp, skeleton=n, pads=pads, trigger=dict(center=[float(v) for v in tr], radius=float(s.get("trigger_radius", 6.0))),
                                                     stagger=float(s.get("stagger", 0.45)), rise_s=float(s.get("rise_s", 0.75 if style == "goofy" else 2.6)), liquid=liq,
                                                     **({"style": "goofy"} if style == "goofy" else {}),
                                                     note="the arena starts under the liquid; its platforms surge up in order when a player enters the trigger sphere" + (" - goofy: see assembly.goofy_pose" if style == "goofy" else ""))]
    ctx.walkable.append(dict(name=n + "_Deck", min=[round(cx - D / 2, 3), round(cz - D / 2, 3)], max=[round(cx + D / 2, 3), round(cz + D / 2, 3)], y=top))
    ctx.notes.append(f"{n}: battle arena rising out of the liquid ({style}) - " + (f"{len(pads)} square tiles, {D:.1f} m across" if G_ else f"{D:.0f} m square deck + {len(pads) - 1} platforms") + f" at {top} m")


def _bez(a, b, c, d, u):
    m = 1 - u; return [m * m * m * a[i] + 3 * m * m * u * b[i] + 3 * m * u * u * c[i] + u * u * u * d[i] for i in range(3)]


def jet_pose(J, phase, t):
    """Stage 119: pose of a jetpack screen (reference for viewer.html / apply_effects.gd). phase: "home" (t = clock),
    "fly" (t since it was triggered: double take, a swooping bezier flight with a barrel roll and a wobble, an
    overshoot that springs back), "wait" (t since arrival: bobbing in front of the player, the hatch opening), "press"
    (t since the button: cap pressed, a happy spin) and "back" (t since leaving: a high arc home). Returns
    (pos [x, y, z], yaw, pitch, roll (deg), hatch 0..1, cap press 0..1, flame scale)."""
    H, A, Tm = J["home"], J["arrive"], J["times"]; amp, per = J["bob"]
    bob = lambda tt: amp * math.sin(2 * math.pi * tt / per); fl = lambda tt, k=1.0: k * (1 + 0.18 * math.sin(tt * 31) + 0.1 * math.sin(tt * 17))
    if phase == "home": return ([H[0], H[1] + bob(t), H[2]], J["yaw0"] + 3 * math.sin(t * 0.7), 0.0, 2.5 * math.sin(2 * math.pi * t / (per * 1.7)), 0.0, 0.0, fl(t))
    if phase == "fly":
        tk, tf, ts = Tm["take"], Tm["fly"], Tm["settle"]
        if t < tk:  # double take: hops, spins round once
            u = t / tk; return ([H[0], H[1] + 1.4 * math.sin(math.pi * u), H[2]], J["yaw0"] + 360 * (u * u * (3 - 2 * u)), 0.0, 0.0, 0.0, 0.0, fl(t, 1.6))
        if t < tk + tf:
            u = (t - tk) / tf; e = u * u * (3 - 2 * u); P = _bez(H, J["ctrl1"], J["ctrl2"], A, e); Q = _bez(H, J["ctrl1"], J["ctrl2"], A, min(1, e + 0.02))
            dx, dz = Q[0] - P[0], Q[2] - P[2]; hd = math.degrees(math.atan2(dx, dz)) if abs(dx) + abs(dz) > 1e-6 else J["arrive_yaw"]
            w = 0.9 * math.sin(3 * math.pi * u) * math.sin(math.pi * u); P = [P[0] + w * math.cos(math.radians(hd)), P[1] + 0.5 * math.sin(5 * math.pi * u), P[2] - w * math.sin(math.radians(hd))]
            ky = min(1, max(0, (u - 0.75) / 0.25)); yaw = hd + (((J["arrive_yaw"] - hd + 180) % 360) - 180) * ky * ky * (3 - 2 * ky)
            roll = 360 * min(1, max(0, (u - 0.4) / 0.25)) if 0.4 <= u else 0.0; roll = roll * roll / 360 * (3 - 2 * roll / 360) if roll < 360 else 360.0
            return (P, yaw, -14 * math.sin(math.pi * u), roll % 360, 0.0, 0.0, fl(t, 1.8))
        s_ = t - tk - tf
        if s_ < ts:  # overshoots forward, springs back, wobbling
            f = math.radians(J["arrive_yaw"]); k = 1.6 * math.sin(7 * s_) * math.exp(-4 * s_)
            q = min(1.0, s_ / ts); ap = J.get("arrive_pitch", 0.0) * q * q * (3 - 2 * q)
            return ([A[0] + k * math.sin(f), A[1] + 0.4 * math.sin(9 * s_) * math.exp(-3 * s_), A[2] + k * math.cos(f)], J["arrive_yaw"] + 14 * math.sin(11 * s_) * math.exp(-3.5 * s_), ap,
                    10 * math.sin(8 * s_) * math.exp(-3 * s_), 0.0, 0.0, fl(t, 1.3))
        return jet_pose(J, "wait", s_ - ts)
    if phase == "wait":
        h = min(1, t / Tm["open"]); h = 1 + 2.2 * (h - 1) ** 3 + 1.2 * (h - 1) ** 2 if h < 1 else 1.0
        return ([A[0], A[1] + bob(t) * 0.5, A[2]], J["arrive_yaw"], J.get("arrive_pitch", 0.0), 1.5 * math.sin(2 * math.pi * t / per), h, 0.0, fl(t))
    if phase == "press":
        c = max(0.0, 1 - abs(t - 0.12) / 0.12) if t < 0.24 else 0.0; sp = min(1, max(0, (t - 0.3) / 0.8)); sp = sp * sp * (3 - 2 * sp)
        return ([A[0], A[1] + 0.6 * math.sin(math.pi * sp), A[2]], J["arrive_yaw"] + 360 * sp, J.get("arrive_pitch", 0.0), 0.0, 1.0, c, fl(t, 1.2))
    if phase == "back":  # hatch shuts, then a high arc home
        tb = Tm["back"]; h = max(0.0, 1 - t / 0.5); u = min(1, t / tb); e = u * u * (3 - 2 * u)
        P = _bez(A, [A[0], A[1] + 9, A[2]], [H[0], H[1] + 9, H[2]], H, e); yaw = J["arrive_yaw"] + (((J["yaw0"] - J["arrive_yaw"] + 180) % 360) - 180) * e
        return (P, yaw, -10 * math.sin(math.pi * u) + J.get("arrive_pitch", 0.0) * (1 - e), 0.0, h, 0.0, fl(t, 1.5))
    return jet_pose(J, "home", t)


@structure("jet_screen", pad=False)
def jet_screen(ctx, s, x, y, z, yaw):
    """Stage 119: a big grin screen ("cell" of the signs atlas, "size" [w, h]) on a jetpack, bobbing in the air at
    position (its centre) - back plate, frame, twin thrusters with flaring nozzles and flickering flames, fins, and a
    garage under the screen hiding a drawer with a BIG RED BUTTON. When a player reaches "trigger" (a walkable name,
    e.g. "Arena_Deck") it zooms over goofily to "arrive" ([x, z]; it hovers so the button is at hand height over
    "arrive_floor", facing "arrive_yaw"), and the drawer slides out: the button is a control terminal (radius 1.8) that
    opens "activates" (gate ids) - then it does a happy spin and jets home. level.json "jets" + "terminals"
    (requires: the screen has arrived); runtimes: viewer.html / apply_effects.gd (jet_pose)."""
    n = s["id"]; w_, h_ = (float(v) for v in s.get("size", [9, 6])[:2]); hw, hh = w_ / 2, h_ / 2; y0c = float(s.get("center_y", y + hh))
    gb, gf, gh, gc = n + "_Body", n + "_Flame", n + "_Hatch", n + "_Cap"; gl, stripe, lamp = ctx.role("glow"), ctx.role("stripe"), ctx.role("glow_yellow")
    W = _W(x, y0c, z, yaw); K = lambda g, **kw: dict(collision=False, mobile={"group": g}, **kw)
    def box(nm, lx, lyc, lz, sz, mat, g, **kw):  # centred (x, y, z) local box
        q = W(lx, lyc - sz[1] / 2, lz); ctx.add(f"{n}_{nm}", "box", q, sz, mat, rot=[0, yaw, 0], **K(g, **kw))
    def cyl(nm, lx, ly0, lz, dia, hgt, mat, g, sec=12, **kw):
        q = W(lx, ly0, lz); ctx.add(f"{n}_{nm}", "cylinder", q, [dia, hgt, dia], mat, sections=sec, **K(g, **kw))
    def fru(nm, lx, ly0, lz, dia, hgt, k, mat, g, **kw):
        q = W(lx, ly0, lz); ctx.add(f"{n}_{nm}", "frustum", q, [dia, hgt, dia], mat, sections=10, bottom_scale=k, **K(g, **kw))
    # --- screen: back plate, frame, the grin panel
    box("Back", 0, 0, -0.32, [w_ + 0.8, h_ + 0.8, 0.6], "machine", gb)
    for nm, lx, ly, sx, sy in (("FrameT", 0, hh + 0.075, w_ + 0.8, 0.35), ("FrameB", 0, -hh - 0.075, w_ + 0.8, 0.35), ("FrameL", -hw - 0.225, 0, 0.35, h_ + 0.15), ("FrameR", hw + 0.225, 0, 0.35, h_ + 0.15)):
        box(nm, lx, ly, 0.1, [sx, sy, 0.3], "machine", gb, outline=False)
    q = W(0, -hh, 0.03); ctx.add(n + "_Panel", "panel", q, [w_, h_, 0], ctx.role("signs"), rot=[0, yaw, 0], uv_region=s.get("cell_region", "a"), **K(gb, outline=False))
    box("GlowStrip", 0, -hh - 0.33, 0.27, [w_ * 0.8, 0.1, 0.06], gl, gb, outline=False)
    # --- jetpack: pack, twin thrusters, nozzles, fins, flames
    box("Pack", 0, -0.6, -1.25, [4.4, 3.0, 1.3], "machine", gb)
    for sd in (-1, 1):
        tx = sd * 1.75; tag = "LR"[sd > 0]
        cyl(f"Thruster{tag}", tx, -2.9, -1.35, 1.1, 3.5, "machine", gb)
        fru(f"ThrusterCap{tag}", tx, 0.6, -1.35, 0.7, 0.45, 1.6, "machine", gb)
        cyl(f"ThrusterBand{tag}", tx, -3.05, -1.35, 1.22, 0.3, stripe, gb, outline=False)
        fru(f"Nozzle{tag}", tx, -3.5, -1.35, 1.0, 0.6, 1.45, "machine", gb)
        cyl(f"NozzleGlow{tag}", tx, -3.53, -1.35, 1.25, 0.06, gl, gb, outline=False)
        box(f"Fin{tag}", tx + sd * 0.62, -2.0, -1.35, [0.14, 1.4, 0.9], "machine", gb)
        fru(f"Flame{tag}", tx, -5.15, -1.35, 0.95, 1.6, 0.12, lamp, gf, outline=False)
    # --- the garage under the screen, the drawer with the big red button
    box("Garage", 0, -hh - 0.9, -0.2, [3.4, 1.0, 1.6], "machine", gb)
    box("GarageLip", 0, -hh - 0.48, 0.66, [3.5, 0.16, 0.08], stripe, gb, outline=False)
    py = -hh - 0.95; box("Drawer", 0, py, -0.2, [2.8, 0.22, 1.8], "machine", gh)
    box("DrawerEdge", 0, py, 0.72, [2.86, 0.24, 0.1], stripe, gh, outline=False)
    cyl("ButtonBase", 0, py + 0.11, -0.2, 1.4, 0.25, "machine", gh)
    cyl("ButtonRing", 0, py + 0.11, -0.2, 1.62, 0.08, stripe, gh, outline=False)
    cyl("Button", 0, py + 0.36, -0.2, 1.1, 0.32, gl, gc, sec=16, outline=False)
    slide = float(s.get("slide", 1.9))
    if slide > 1.9:  # telescoping rails tie a long-reaching drawer back into its garage
        for sd in (-1, 1): box(f"DrawerRail{'LR'[sd > 0]}", sd * 1.25, py - 0.02, -0.2 - 0.9 - (slide - 0.6) / 2 + 0.05, [0.16, 0.14, slide - 0.6], "machine", gh, outline=False)
    cap_top = py + 0.68
    # --- where it goes, the terminal
    ax_, az_ = s["arrive"]; floor = float(s["arrive_floor"]); ay = float(s.get("arrive_yaw", 0.0)); reach = float(s.get("button_height", 1.35)); ap = float(s.get("arrive_pitch", 0.0))
    pr_ = math.radians(ap); by_ = cap_top * math.cos(pr_) - (-0.2 + slide) * math.sin(pr_); bz_ = cap_top * math.sin(pr_) + (-0.2 + slide) * math.cos(pr_)  # the button, tipped forward by the pitch
    acy = floor + reach - by_; bpos = [ax_ + bz_ * math.sin(math.radians(ay)), floor + reach, az_ + bz_ * math.cos(math.radians(ay))]
    trig = next((w for w in ctx.walkable if w["name"] == s["trigger_area"]), None)
    home = [round(x, 3), round(y0c, 3), round(z, 3)]; arrive = [round(ax_, 3), round(acy, 3), round(az_, 3)]
    J = dict(id=n, body=gb, flame=gf, hatch=gh, cap=gc, home=home, yaw0=float(yaw), arrive=arrive, arrive_yaw=ay, arrive_pitch=ap, flame_y=-3.55, slide=slide, press=0.14,
             ctrl1=[round(home[0], 3), round(home[1] + 5, 3), round(home[2] + 4, 3)], ctrl2=[round(arrive[0] + 12, 3), round(arrive[1] + 5, 3), round(arrive[2] - 12, 3)],
             times=dict(take=0.7, fly=3.3, settle=1.0, open=0.6, back=3.5), bob=[0.45, 2.2], button=n + "_Button",
             trigger=dict(name=s["trigger_area"], min=trig["min"], max=trig["max"], y=trig["y"]) if trig else None,
             note="assembly.jet_pose: home bob -> (player on trigger) fly -> wait (hatch opens; the button terminal goes live) -> press -> back home")
    ctx.jets = getattr(ctx, "jets", []) + [J]
    ctx.terminals = getattr(ctx, "terminals", []) + [dict(id=n + "_Button", center=[round(bpos[0], 3), round(floor, 3), round(bpos[2], 3)], radius=float(s.get("radius", 1.8)),
                                                           activates=list(s.get("activates", [])), requires=n, button=[round(v, 3) for v in bpos],
                                                           note="the big red button: live once the jet screen has arrived (level.json jets); using it opens the gates in 'activates'")]
    ctx.notes.append(f"{n}: jetpack grin screen bobbing at {home}; flies to {arrive} when a player reaches {s["trigger_area"]} - big red button opens {s.get('activates')}")


@structure("pillar_path", pad=False)
def pillar_path(ctx, s, x, y, z, yaw):
    """Stepping pillars over the slime: "points" [[x, z, top], ...], square caps "pillar_size" m with a hazard-striped band
    round their edges on cross-braced truss legs down into the liquid. Every cap is walkable."""
    n = s["id"]; P_ = float(s.get("pillar_size", 3.8)); st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st)
    liq = float(s.get("liquid", 0.0)); stripe = ctx.role("stripe")
    for k, (px, pz, top) in enumerate(s["points"]):
        a = float(s.get("yaw", 0.0)) + (k * 7.0 if s.get("twist") else 0.0); W = _W(px, 0, pz, a); pre = f"{n}_{k + 1}"
        ctx.add(pre + "_Cap", "box", [px, top - 0.45, pz], [P_, 0.45, P_], "deck", rot=[0, a, 0], **st)
        for j, (lx, lz, sx, sz) in enumerate(((0, P_ / 2 + 0.03, P_ + 0.12, 0.06), (0, -P_ / 2 - 0.03, P_ + 0.12, 0.06), (P_ / 2 + 0.03, 0, 0.06, P_), (-P_ / 2 - 0.03, 0, 0.06, P_))):
            q = W(lx, 0, lz); ctx.add(f"{pre}_Band_{j + 1}", "box", [q[0], top - 0.5, q[2]], [sx, 0.48, sz], stripe, rot=[0, a, 0], **vs)
        h = top - 0.45 - liq; c = P_ / 2 - 0.25
        for j, (lx, lz) in enumerate(((c, c), (-c, c), (c, -c), (-c, -c))):
            q = W(lx, 0, lz); ctx.add(f"{pre}_Leg_{j + 1}", "box", [q[0], liq, q[2]], [0.3, h, 0.3], "frame", rot=[0, a, 0], bevel=False, **vs)
        bl = math.hypot(2 * c, h * 0.5); ang = math.degrees(math.atan2(h * 0.5, 2 * c))
        for j, (lx, lz, ry) in enumerate(((0, c, 0), (0, -c, 0), (c, 0, 90), (-c, 0, 90))):
            for hh, sg in ((0.25, 1), (0.75, -1)):
                q = W(lx, 0, lz); ctx.add(f"{pre}_Brace_{j + 1}{'ab'[hh > 0.5]}", "box", [q[0], liq + h * hh - 0.08, q[2]], [bl, 0.16, 0.16], "frame", rot=[0, a + ry, sg * ang], bevel=False, **vs)
        ctx.landings.append((round(px, 3), round(pz, 3), P_ / 2))
    ctx.notes.append(f"{n}: {len(s['points'])} striped pillars on truss legs")


@structure("belt_ramp", pad=False)
def belt_ramp(ctx, s, x, y, z, yaw):
    """A conveyor ramp from "foot" [x, y, z] up to "head" [x, y, z], "width" m: a belt deck with chevrons (they slide
    with the belt) between hazard-striped side frames on two trestles. The belt moves "speed" m/s along the ramp
    (negative = downhill, against a climbing player: level.json "belts" - whoever stands on it is carried). "pit": a gap
    "pit" m deep in front of the foot full of spikes (a static kill box): ridden down, you fall onto them."""
    n = s["id"]; (x0, y0, z0), (x1, y1, z1) = s["foot"], s["head"]; w = float(s.get("width", 4.0)); sp = float(s.get("speed", -2.5))
    Lh = math.hypot(x1 - x0, z1 - z0); L = math.hypot(Lh, y1 - y0); a = _yaw_to(x1 - x0, z1 - z0); pitch = math.degrees(math.atan2(y1 - y0, Lh))
    mx, my, mz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2; st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st); stripe = ctx.role("stripe")
    u = [(x1 - x0) / L, (y1 - y0) / L, (z1 - z0) / L]; th = 0.4
    ctx.add(n + "_Deck", "box", [mx, my - th, mz], [w, th, L], "belt", rot=[-pitch, a, 0], connector=True, **dict(st, approach="jump_foot") if s.get("pit") else st)  # deck top on the from -> to line
    for k, sd in enumerate((-1, 1)):
        dx, dz = A_local(sd * (w / 2 + 0.2), 0, a)
        ctx.add(f"{n}_Frame_{k + 1}", "box", [mx + dx, my - 0.75, mz + dz], [0.4, 1.0, L + 0.2], stripe, rot=[-pitch, a, 0], **st)  # side curbs 25 cm proud
    for k, f in enumerate((0.25, 0.75)):  # trestles into the slime
        px, py, pz = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, z0 + (z1 - z0) * f
        for sd in (-1, 1):
            dx, dz = A_local(sd * (w / 2 - 0.3), 0, a); ctx.add(f"{n}_Leg_{k + 1}{'LR'[sd > 0]}", "box", [px + dx, 0.0, pz + dz], [0.45, py - 0.6, 0.45], "frame", rot=[0, a, 0], bevel=False, **vs)
    gc = n + "_Chev"; mc = dict(collision=False, outline=False, mobile={"group": gc}); spacing = float(s.get("spacing", 2.6)); nc = max(1, int((L - 2.0 - spacing) / spacing) + 1)
    for k in range(nc):  # the runtimes shift them 0..-spacing along the belt (towards the foot when it runs downhill): from 1 m to L - 1 m
        f = (1.0 + spacing + k * spacing) / L; px, py, pz = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f + 0.015, z0 + (z1 - z0) * f
        for sd in (-1, 1):  # a chevron pointing uphill: two strips meeting on the centre line
            dx, dz = A_local(sd * w * 0.18, -0.35, a)
            ctx.add(f"{gc}_{k + 1:02d}{'LR'[sd > 0]}", "box", [px + dx, py, pz + dz], [w * 0.42, 0.03, 0.34], ctx.role("glow_yellow"), rot=[-pitch, a - sd * 40, 0], **mc)
    ctx.belts = getattr(ctx, "belts", []) + [dict(id=n, chevrons=gc, center=[round(mx, 3), round(my, 3), round(mz, 3)], axis=[round(v, 4) for v in u], length=round(L, 3), width=round(w, 3),
                                                 speed=sp, spacing=spacing, yaw=round(a, 2), pitch=round(pitch, 2),
                                                 note="a body standing on the deck (within width / length, feet within 0.4 m of it) moves speed * axis m/s")]
    if s.get("pit"):  # spike pit in front of the foot, across the belt's width
        pd = float(s["pit"]); gap = float(s.get("pit_len", 1.6)); fx, fz = x0 - u[0] / math.hypot(u[0], u[2]) * gap / 2, z0 - u[2] / math.hypot(u[0], u[2]) * gap / 2
        ctx.add(n + "_PitFloor", "box", [fx, y0 - pd - 0.3, fz], [w + 0.8, 0.3, gap], "structure_b", rot=[0, a, 0], **st)
        _spikes(ctx, n + "_PitSpike", fx, fz, y0 - pd, w, gap, a, ctx.role("spike"), length=0.8)
        K = dict(id=n + "_Pit", center=[round(fx, 3), round(y0 - pd + 0.5, 3), round(fz, 3)], size=[round(w, 3), 1.0, round(gap, 3)], yaw=round(a, 2), note="spikes")
        ctx.kills = getattr(ctx, "kills", []) + [K]; ctx.belts[-1]["kill"] = K  # (the preview reads it from the belt's effect)
    ctx.notes.append(f"{n}: conveyor ramp {L:.1f} m at {pitch:.0f} deg, belt {sp:+.1f} m/s" + (", spike pit at the foot" if s.get("pit") else ""))


@structure("laser_gate", pad=False)
def laser_gate(ctx, s, x, y, z, yaw):
    """A free-standing laser gate across a deck ("width" m, local x): two machine posts with red caps, the beams of
    factory._laser_gate between them (closed at start, level.json "gates", opens_on e.g. waves_cleared)."""
    from modules.factory import _laser_gate
    n = s["id"]; W = float(s.get("width", 5.0)); H = float(s.get("height", 5.0)); g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0]); st = dict(mobile={"static": True})
    for sd in (-1, 1):
        ctx.add(f"{n}_Post_{'LR'[sd > 0]}", "box", [sd * (W / 2 + 0.3), 0, 0], [0.55, H + 0.4, 0.7], "machine", g, **st)
        ctx.add(f"{n}_Cap_{'LR'[sd > 0]}", "box", [sd * (W / 2 + 0.3), H + 0.4, 0], [0.7, 0.25, 0.85], ctx.role("laser"), g, outline=False, collision=False, **st)
    _laser_gate(ctx, n, g, W, H, dict(s.get("laser_gate") or {}, id=s.get("gate_id", n + "_Laser"), opens_on=s.get("opens_on", {"type": "waves_cleared", "encounter": s.get("encounter")})), x, y, z, yaw)


@structure("sign", pad=False)
def sign(ctx, s, x, y, z, yaw):
    """A lit sign from the "signs" atlas ("cell": grin / exit / arrow / gear -> atlas a / b / c / d), "size" [w, h]:
    "mount" wall (a frame + panel facing local +z), hanging (two chains up to "chain_to" y) or floor (a decal lying on
    the deck, glowing paint)."""
    n = s["id"]; w, h = s.get("size", [4.0, 3.0, 0.2])[:2]; cell = {"grin": "a", "exit": "b", "arrow": "c", "gear": "d"}.get(s.get("cell", "grin"), "a")
    st = dict(mobile={"static": True}); vs = dict(collision=False, outline=False, **st); mount = s.get("mount", "wall")
    if mount == "floor":
        dx, dz = A_local(0, h / 2, yaw)  # a panel lying flat runs from its base along local +z: centre it
        if s.get("decal_material"):  # Stage 122: its own (cut-out) image - no background tile round the emblem
            ctx.add(n + "_Decal", "panel", [x + dx, y + 0.012, z + dz], [w, h, 0], ctx.role(s["decal_material"]), rot=[-90, yaw, 0], **vs); return
        ctx.add(n + "_Decal", "panel", [x + dx, y + 0.012, z + dz], [w, h, 0], ctx.role("signs"), rot=[-90, yaw, 0], uv_region=cell, **vs); return
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Frame", "box", [0, -0.15, -0.12], [w + 0.3, h + 0.3, 0.22], "frame", g, **st)
    ctx.add(n + "_Panel", "panel", [0, 0, 0.0], [w, h, 0], ctx.role("signs"), g, uv_region=cell, **vs)
    if mount == "hanging":
        top = float(s.get("chain_to", y + 6)); L = top - (y + h + 0.15)
        for sd in (-1, 1): ctx.add(f"{n}_Chain_{'LR'[sd > 0]}", "box", [sd * w * 0.38, h + 0.15, -0.12], [0.08, L, 0.08], "frame", g, **vs)
