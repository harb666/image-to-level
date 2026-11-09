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
    rc = br * 0.66; mace = ctx.role("mace"); nl = dict(mr, outline=False)
    ctx.add(gr + "_Collar", "cylinder", [x, T + by - 0.35, z], [3.0, 0.7, 3.0], "machine", sections=12, **mr)
    for k, a0 in enumerate(arms):  # Stage 104 (concept art): a round striped pole out of a socket in the hub, a flanged coupling into a gunmetal mace
        a = yaw + a0; P0 = _W(x, 0, z, a); K_ = lambda nm, sh, r, sz, mat, kw=mr, sec=8: ctx.add(f"{gr}_{nm}_{k + 1}", sh, P0(0, T + by, r), sz, mat, rot=[90, a, 0], sections=sec, **kw)
        K_("Arm", "cylinder", r0, [2 * bh, r1 - r0, 2 * bh], stripe)
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
    for k in range(4):
        a = yaw + 45 + 90 * k; P0 = _W(x, 0, z, a); c = P0(0, 0, Dp); pre = f"{n}_Pad_{k + 1}"; ctx.spinner_pads[f"{n}_{k + 1}"] = [c[0], T, c[2]]
        ctx.add(pre + "_Deck", "cylinder", [c[0], T - 0.6, c[2]], [pd, 0.6, pd], "deck", sections=8, **st)
        ctx.add(pre + "_Rim", "cylinder", [c[0], T - 0.95, c[2]], [pd + 0.16, 0.42, pd + 0.16], stripe, sections=8, **vs)
        ctx.add(pre + "_Hull", "frustum", [c[0], T - 3.0, c[2]], [pd - 0.4, 2.05, pd - 0.4], "structure_b", sections=8, bottom_scale=0.42, **st)
        ctx.add(pre + "_GlowBand", "frustum", [c[0], T - 2.1, c[2]], [pd * 0.8, 0.35, pd * 0.8], gl, sections=8, bottom_scale=0.92, **vs)
        ctx.add(pre + "_Thruster", "cylinder", [c[0], T - 3.7, c[2]], [1.4, 0.75, 1.4], "machine", sections=8, **vs)
        ctx.add(pre + "_Jet", "frustum", [c[0], T - 4.7, c[2]], [1.1, 1.0, 1.1], gl, sections=8, bottom_scale=0.15, **vs)
        q0 = P0(0, 0, R - 0.5); q1 = P0(0, 0, Dp - pd / 2 + 0.6); m = [(q0[i] + q1[i]) / 2 for i in range(3)]; L = math.dist(q0, q1)
        ctx.add(pre + "_Bridge", "box", [m[0], T - 0.33, m[2]], [2.6, 0.3, L], "grate", rot=[0, a, 0], **st)  # 3 cm under the decks: no shared faces
        for sd in (-1, 1):
            dx, dz = A_local(sd * 1.38, 0, a); ctx.add(f"{pre}_BridgeRail_{'LR'[sd > 0]}", "box", [m[0] + dx, T - 0.03, m[2] + dz], [0.08, 0.7, L - 1.4], "rail", rot=[0, a, 0], **dict(st, outline=False))
        ctx.landings.append((round(c[0], 3), round(c[2], 3), pd / 2))
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
    hb = C - 14.9 - travel  # the head's underside when pressed
    imp = [[round(v, 2) for v in _W(x, 0, z, yaw + 22.5 + 45 * k)(0, hb + 0.25, 3.45)] for k in range(8)]  # round the pressed head
    rel = [[round(v, 2) for v in _W(x, 0, z, yaw + 45 + 90 * k)(0, C - 7.35, 2.15)] for k in range(4)]  # out of the gland as it lets go
    return dict(press=gr_, stages=[{"group": gm, "frac": 0.5}, {"group": gr_, "frac": 1.0}], lamps=f"{gr_}__{gl}", travel=travel, period=P_, slam=sl, hold=ho, rise=ri,
                spin_up=su, spin_down=sd, turns=turns, peak=round(w, 3), peak_rpm=round(w / 6.0, 2), warn=float(pr.get("warn", 1.2)), phase=float(pr.get("phase", 0.0)),
                still=round(P_ - sl - ho - sd, 2), shake=float(pr.get("shake", 28.0)), steam_impact=imp, steam_release=rel,
                note="press_profile(): u = (t + phase) mod period; ram offset -travel (u/slam)^2, held, eased back over rise; each stage moves offset * frac; "
                     "rotor angle = whole-turn cycles + spin-up / peak / coast-down from the impact; the head's glow blinks for 'warn' s before each slam; "
                     "camera shake within 'shake' m on impact")


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
        ctx.add(n + "_Decal", "panel", [x + dx, y + 0.012, z + dz], [w, h, 0], ctx.role("signs"), rot=[-90, yaw, 0], uv_region=cell, **vs); return
    g = ctx.add(n, "group", [x, y, z], rot=[0, yaw, 0])
    ctx.add(n + "_Frame", "box", [0, -0.15, -0.12], [w + 0.3, h + 0.3, 0.22], "frame", g, **st)
    ctx.add(n + "_Panel", "panel", [0, 0, 0.0], [w, h, 0], ctx.role("signs"), g, uv_region=cell, **vs)
    if mount == "hanging":
        top = float(s.get("chain_to", y + 6)); L = top - (y + h + 0.15)
        for sd in (-1, 1): ctx.add(f"{n}_Chain_{'LR'[sd > 0]}", "box", [sd * w * 0.38, h + 0.15, -0.12], [0.08, L, 0.08], "frame", g, **vs)
