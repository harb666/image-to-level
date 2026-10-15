"""Stage 66: robot-arm motion programs - the arm moves like a real machine, only through its joints.

A program is one cycle (period P = parcel spacing / belt speed) of segments [t_start, t_end, mode, A, B]. A and B are
claw-tip targets:
  {"k": "belt", "e": e, "h": h}   fixed point on the belt line: station tip + axis * e + up * h
  {"k": "track", "h": h}          the parcel itself: e = v * tau (conveyor tracking - the claw rides along with it)
  {"k": "bin", "h": h}            over / in the bin: bin tip + up * h
Within a segment the weight w = smootherstep(phase) (zero speed AND acceleration at both ends: jerk-limited servo
moves, no bounce). "lin" blends the Cartesian targets and solves the joints each frame (straight approaches, tracking:
blending into a moving target ends exactly at its speed); "joint" blends the joint angles of the two targets
(coordinated transfers, e.g. belt -> bin). Holds are segments with A == B.
Joints from the target by inverse kinematics: turret yaw faces the wrist, shoulder / elbow from the two-link solution
(elbow up), wrist = -(shoulder + elbow) offsets so the claw always hangs level. Twist and fingers have their own
keyed tracks (smootherstep too); the twist adds `twist_cycle` deg every cycle (the claw is 3-fold symmetric).
The runtimes (godot_fx/apply_effects.gd, viewer.html) implement exactly this file's `pose`."""
import math


def smoother(x):
    x = min(1.0, max(0.0, x)); return x * x * x * (x * (6 * x - 15) + 10)


def program(task, v, drop, bin_h=None):
    """Segments + tracks for one arm. drop: how far the claw tip goes below its rest height over the parcel; bin_h: tip
    height change for the bin pick (negative = down into it). Times in s relative to the parcel being under the arm."""
    B = lambda e, h=0.0: {"k": "belt", "e": round(e, 4), "h": round(h, 4)}
    T = lambda h=0.0: {"k": "track", "h": round(h, 4)}
    N = lambda h=0.0: {"k": "bin", "h": round(h, 4)}
    if task == "add":
        s0 = -2.2; ready = B(v * s0)
        segs = [[s0, -1.4, "lin", ready, T()],  # accelerate along with the parcel (ends at belt speed)
                [-1.4, -0.7, "lin", T(), T(-drop)],  # straight down onto it, still tracking
                [-0.7, 0.2, "lin", T(-drop), T(-drop)],  # set the canister in: twist, let go
                [0.2, 0.9, "lin", T(-drop), T()],  # straight up
                [0.9, 1.6, "lin", T(), B(v * 1.6)],  # brake to a stop over the belt
                [1.6, 2.8, "joint", B(v * 1.6), N()],  # swing over to the bin
                [2.8, 3.4, "lin", N(), N(bin_h)],  # straight down into it
                [3.4, 3.75, "lin", N(bin_h), N(bin_h)],  # grip the next canister
                [3.75, 4.35, "lin", N(bin_h), N()],  # straight up
                [4.35, 5.55, "joint", N(), ready],  # swing back over the belt, upstream of the next parcel
                [5.55, s0, "lin", ready, ready]]  # wait for it (wraps to the next cycle)
        return dict(start=s0, segs=segs, twist=[[-0.6, -0.1, 0.0, 120.0]], twist_cycle=120.0,
                    fingers=[[0.0, 0.25, -5.0, 16.0], [3.4, 3.65, 16.0, -5.0]], fingers_start=-5.0, held_hidden=[0.0, 3.55], scan=None)
    s0 = -2.4; ready = B(v * s0)
    segs = [[s0, -1.6, "lin", ready, T()], [-1.6, -1.0, "lin", T(), T(-drop)], [-1.0, 1.0, "lin", T(-drop), T(-drop)],  # ride along, scan
            [1.0, 1.6, "lin", T(-drop), T()], [1.6, 2.3, "lin", T(), B(v * 2.3)], [2.3, 3.6, "joint", B(v * 2.3), ready], [3.6, s0, "lin", ready, ready]]
    return dict(start=s0, segs=segs, twist=[[-0.95, -0.35, 0.0, 35.0], [-0.35, 0.35, 35.0, -35.0], [0.35, 0.95, -35.0, 0.0]], twist_cycle=0.0,
                fingers=[], fingers_start=6.0, held_hidden=None, scan=[-1.0, 1.0])


def _target(rig, q, tau, v):
    k = q["k"]
    if k == "bin": b = rig["bin"]; return [b[0], b[1] + q["h"], b[2]]
    e = v * tau if k == "track" else q["e"]; t0, ax = rig["tip"], rig["axis"]
    return [t0[0] + ax[0] * e, t0[1] + q["h"], t0[2] + ax[2] * e]


def ik(rig, p):
    """[yaw, shoulder, elbow] offsets from the rest pose for claw tip p (world)."""
    l1, l2 = rig["l1"], rig["l2"]; dx, dz = p[0] - rig["base"][0], p[2] - rig["base"][1]
    r = math.hypot(dx, dz); dy = p[1] + rig["claw"] - rig["py"]
    D = max(abs(l1 - l2) + 1e-3, min(math.hypot(r, dy), l1 + l2 - 1e-3))
    b1 = math.atan2(r, dy) - math.acos(max(-1.0, min(1.0, (l1 * l1 + D * D - l2 * l2) / (2 * l1 * D))))
    b2 = math.atan2(r - l1 * math.sin(b1), dy - l1 * math.cos(b1))
    yw = (math.atan2(dx, dz) - rig["yaw0"] + math.pi) % (2 * math.pi) - math.pi
    return [yw, b1 - rig["a1"], (b2 - b1) - (rig["a2"] - rig["a1"])]


def _keyed(keys, tau, v0):
    val = v0
    for a, b, f, t in keys:
        if tau >= b: val = t
        elif tau >= a: return f + (t - f) * smoother((tau - a) / (b - a))
    return val


def pose(rig, prog, v, period, t, t0):
    """Joint angles (rad) + flags at time t. t0: a time the parcel is under the arm."""
    s0 = prog["start"]; x = t - t0 - s0; n = math.floor(x / period); tau = x - n * period + s0
    for a, b, mode, A, B in prog["segs"]:
        b_ = b if b > a else b + period
        if a <= tau < b_ or (b <= a and tau < b):  # (the last segment wraps to the next cycle)
            tl = tau if tau >= a else tau + period; w = smoother((tl - a) / (b_ - a))
            if mode == "lin":
                pa, pb = _target(rig, A, tau, v), _target(rig, B, tau, v); J = ik(rig, [pa[i] + (pb[i] - pa[i]) * w for i in range(3)])
            else:
                ja, jb = ik(rig, _target(rig, A, tau, v)), ik(rig, _target(rig, B, tau, v)); J = [ja[i] + (jb[i] - ja[i]) * w for i in range(3)]
            break
    out = dict(yaw=J[0], shoulder=J[1], elbow=J[2], wrist=-(J[1] + J[2]),
               twist=math.radians(prog["twist_cycle"] * n + _keyed(prog["twist"], tau, 0.0)))
    f = math.radians(_keyed(prog["fingers"], tau, prog["fingers_start"]))
    for i in range(3): out[f"finger{i + 1}"] = f
    hh, sc = prog.get("held_hidden"), prog.get("scan")
    return out, dict(tau=tau, held=not (hh and hh[0] <= tau < hh[1]), scan=bool(sc and sc[0] <= tau < sc[1]))


def reach(rig, prog, v, period, samples=400):
    """Largest wrist distance from the shoulder over the cycle / (l1 + l2): near 1 the arm is nearly straight and small
    claw moves need big elbow swings (it looks like it is compressing); keep it under ~0.93."""
    best = 0.0; L = rig["l1"] + rig["l2"]
    for k in range(samples):
        tau = prog["start"] + period * k / samples
        for a, b, mode, A, B in prog["segs"]:
            b_ = b if b > a else b + period
            if a <= tau < b_:
                for q in (A, B):
                    p = _target(rig, q, tau, v); r = math.hypot(p[0] - rig["base"][0], p[2] - rig["base"][1])
                    best = max(best, math.hypot(r, p[1] + rig["claw"] - rig["py"]) / L)
    return best
