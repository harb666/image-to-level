"""Stage 152: the specimen in the showcase vat - a Construct Error character prepared for a glass tank.

Reads a Mixamo-rigged character GLB (assets/characters/source/cyber_girl_source.glb) and writes a light, re-rigged,
animated copy:

  - hair split from the body (colour + distance from the body's bone segments): its own primitive, weighted to two
    new hair bone chains (one per twin tail, rooted at the hair ties) + Head for the scalp - no arm / leg influence,
    so the hair is free of her body motion (still rooted at the head; its flow is baked animation, not physics)
  - body and hair decimated separately (fast_simplification), UVs re-projected per face corner from the closest
    original face, skin weights from the closest original vertex, smooth normals recomputed
  - a FloatRoot node between the armature and Hips (the runtimes bob it), a static WireAnchor bone, and cables from the
    tank cap down to her back, skinned in a gradient anchor -> spine (they stretch as she floats)
  - clips authored here with FK + analytic two-bone IK against the vat glass: "panic" (palms on the glass, sliding,
    head searching, kicking) and "bang" (fists pounding the glass) - hair waves phase-lagged down each chain;
    every joint checked against anatomical limits (tests/test_stage152.py)
  - base colour texture resized (embedded in <out>.glb for Godot; <out>_preview.glb has no images + <out>.jpg for the
    sandboxed preview, like Stage 113's player)

  python3 pipeline/specimen.py <source.glb> <out_prefix> [--config levels/<lvl>/scene_spec.json]
"""
import io, json, math, struct, sys
import numpy as np

# ------------------------------------------------------------------ glTF I/O
CT = {5126: (np.float32, 4), 5123: (np.uint16, 2), 5121: (np.uint8, 1), 5125: (np.uint32, 4)}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    b = open(path, "rb").read(); n = struct.unpack("<I", b[12:16])[0]; J = json.loads(b[20:20 + n]); o = 20 + n
    bl = struct.unpack("<I", b[o:o + 4])[0]; return J, b[o + 8:o + 8 + bl]


def accessor(J, BIN, i):
    a = J["accessors"][i]; v = J["bufferViews"][a["bufferView"]]; dt, sz = CT[a["componentType"]]; nc = NC[a["type"]]
    st = v.get("byteStride", sz * nc); off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    if st == sz * nc: out = np.frombuffer(BIN, dt, a["count"] * nc, off).reshape(a["count"], nc).copy()
    else:
        raw = np.frombuffer(BIN, np.uint8, st * (a["count"] - 1) + sz * nc, off).copy()
        out = np.lib.stride_tricks.as_strided(raw.view(np.uint8), (a["count"], nc * sz), (st, 1)).copy().view(dt).reshape(a["count"], nc)
    if a.get("normalized") and dt != np.float32: out = out.astype(np.float32) / np.iinfo(dt).max
    return out


def image_bytes(J, BIN, i):
    v = J["bufferViews"][J["images"][i]["bufferView"]]; return BIN[v.get("byteOffset", 0):v.get("byteOffset", 0) + v["byteLength"]]


class GLBWriter:
    def __init__(self): self.J = dict(asset=dict(version="2.0", generator="image-to-level specimen.py"), buffers=[dict(byteLength=0)], bufferViews=[], accessors=[]); self.blob = bytearray()

    def view(self, data, target=None):
        while len(self.blob) % 4: self.blob.append(0)
        v = dict(buffer=0, byteOffset=len(self.blob), byteLength=len(data))
        if target: v["target"] = target
        self.blob += data; self.J["bufferViews"].append(v); return len(self.J["bufferViews"]) - 1

    def acc(self, arr, type_, ctype, target=None, normalized=False, minmax=False):
        arr = np.ascontiguousarray(arr); a = dict(bufferView=self.view(arr.tobytes(), target), componentType=ctype, count=int(arr.shape[0]), type=type_)
        if normalized: a["normalized"] = True
        if minmax: a["min"] = arr.reshape(arr.shape[0], -1).min(0).tolist(); a["max"] = arr.reshape(arr.shape[0], -1).max(0).tolist()
        self.J["accessors"].append(a); return len(self.J["accessors"]) - 1

    def write(self, path):
        while len(self.blob) % 4: self.blob.append(0)
        self.J["buffers"][0]["byteLength"] = len(self.blob)
        js = json.dumps(self.J, separators=(",", ":")).encode(); js += b" " * (-len(js) % 4)
        glb = struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(self.blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(self.blob), 0x004E4942) + bytes(self.blob)
        open(path, "wb").write(glb); return len(glb)


# ------------------------------------------------------------------ quaternions (x, y, z, w) like glTF
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx, aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def qinv(q): return np.array([-q[0], -q[1], -q[2], q[3]]) / np.dot(q, q)
def qnorm(q): q = np.asarray(q, float); return q / np.linalg.norm(q)


def qaxis(axis, ang):
    axis = np.asarray(axis, float); n = np.linalg.norm(axis)
    if n < 1e-12 or abs(ang) < 1e-12: return np.array([0.0, 0.0, 0.0, 1.0])
    s = math.sin(ang / 2); return np.array([*(axis / n * s), math.cos(ang / 2)])


def qrot(q, v):
    u = np.array(q[:3]); w = q[3]; v = np.asarray(v, float); return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def qbetween(a, b):
    """Shortest-arc rotation taking direction a to direction b."""
    a = np.asarray(a, float) / np.linalg.norm(a); b = np.asarray(b, float) / np.linalg.norm(b); c = np.cross(a, b); d = float(np.dot(a, b))
    if d < -0.999999:
        ax = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0]); return qaxis(ax, math.pi)
    return qnorm([*c, 1 + d])


def qangle(q): q = qnorm(q); return 2 * math.acos(min(1.0, abs(q[3])))


def qslerp(a, b, t):
    a, b = qnorm(a), qnorm(b); d = float(np.dot(a, b))
    if d < 0: b, d = -b, -d
    if d > 0.9995: return qnorm(a + (b - a) * t)
    th = math.acos(d); return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / math.sin(th)


def mat_trs(t, r, s):
    x, y, z, w = r; R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)], [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    M = np.eye(4); M[:3, :3] = R * np.asarray(s, float)[None, :]; M[:3, 3] = t; return M


# ------------------------------------------------------------------ skeleton
class Skeleton:
    """Nodes by name with rest TRS, parent links and FK. Poses are {name: local rotation quaternion}, plus an optional
    {name: local translation}."""
    def __init__(self, nodes):
        self.nodes = nodes  # list of dict(name, t, r, s, parent)
        self.idx = {n["name"]: i for i, n in enumerate(nodes)}
        self.order = []; seen = set()
        def visit(i):
            if i in seen: return
            p = nodes[i]["parent"]
            if p is not None: visit(p)
            seen.add(i); self.order.append(i)
        for i in range(len(nodes)): visit(i)

    def add(self, name, parent, t, r=(0, 0, 0, 1), s=(1, 1, 1)):
        self.nodes.append(dict(name=name, t=np.asarray(t, float), r=qnorm(r), s=np.asarray(s, float), parent=self.idx[parent] if parent else None))
        self.idx[name] = len(self.nodes) - 1; self.order.append(len(self.nodes) - 1); return self.idx[name]

    def reparent(self, name, parent):
        self.nodes[self.idx[name]]["parent"] = self.idx[parent]; self.order = []; seen = set()
        def visit(i):
            if i in seen: return
            p = self.nodes[i]["parent"]
            if p is not None: visit(p)
            seen.add(i); self.order.append(i)
        for i in range(len(self.nodes)): visit(i)

    def fk(self, rot=None, trans=None):
        """World matrices (4x4) and world rotations (quaternions, ignoring scale) for a pose."""
        rot = rot or {}; trans = trans or {}; Wm = [None] * len(self.nodes); Wq = [None] * len(self.nodes)
        for i in self.order:
            n = self.nodes[i]; r = rot.get(n["name"], n["r"]); t = trans.get(n["name"], n["t"]); L = mat_trs(t, r, n["s"])
            p = n["parent"]
            if p is None: Wm[i], Wq[i] = L, qnorm(r)
            else: Wm[i], Wq[i] = Wm[p] @ L, qnorm(qmul(Wq[p], r))
        return Wm, Wq

    def pos(self, Wm, name): return Wm[self.idx[name]][:3, 3].copy()


def load_skeleton(J):
    parent = {c: i for i, n in enumerate(J["nodes"]) for c in n.get("children", [])}
    nodes = [dict(name=n.get("name", f"n{i}"), t=np.asarray(n.get("translation", [0, 0, 0]), float), r=qnorm(n.get("rotation", [0, 0, 0, 1])),
                  s=np.asarray(n.get("scale", [1, 1, 1]), float), parent=parent.get(i)) for i, n in enumerate(J["nodes"])]
    return Skeleton(nodes)


# ------------------------------------------------------------------ hair segmentation
def _seg_dist(P, a, b):
    ab = b - a; t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1); return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def hair_mask(P, col, sk, Wm):
    """Vertices of the hair: hair-coloured (cyan-blue-violet, saturated) AND clear of the body's limbs / torso (bone
    segments with radii) - the suit's cyan stripes sit on the body, the hair hangs off it. Scalp hair (above the neck,
    hair coloured) counts too."""
    import colorsys
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in col])
    hairc = (hsv[:, 1] > 0.3) & (hsv[:, 0] > 0.45) & (hsv[:, 0] < 0.8) & (hsv[:, 2] > 0.3)
    p = lambda n: sk.pos(Wm, "mixamorig:" + n)
    body = np.full(len(P), 1e9)
    segs = [("Hips", "Spine2", 0.21), ("Spine2", "Neck", 0.17), ("LeftUpLeg", "RightUpLeg", 0.22)]  # torso + pelvis (the skirt)
    for sd in ("Left", "Right"):
        segs += [(sd + "Shoulder", sd + "Arm", 0.14), (sd + "Arm", sd + "ForeArm", 0.085), (sd + "ForeArm", sd + "Hand", 0.075), (sd + "Hand", sd + "HandMiddle4", 0.07),
                 (sd + "UpLeg", sd + "Leg", 0.12), (sd + "Leg", sd + "Foot", 0.1), (sd + "Foot", sd + "Toe_End", 0.1)]
    near = np.zeros(len(P), bool)
    for a, b, r in segs:
        arm = a.endswith(("Arm", "Shoulder")) or a.endswith("ForeArm")  # (hands keep their full radius: cyan accents on them are not hair)
        rr = np.where(hairc, 0.055, r) if arm else r  # hair strands brushing the T-posed arms are hair (the arm's own surface is white / grey)
        near |= _seg_dist(P, p(a), p(b)) < rr
    head_c = (p("Head") + p("HeadTop_End")) / 2
    scalp = np.linalg.norm(P - head_c, axis=1) < 0.2
    hanging = ~near & ~scalp & (P[:, 1] > 0.35)  # the tails: everything hanging clear of the body (whatever its shade)
    return (hanging | (hairc & scalp)) & ((np.abs(P[:, 0]) < 0.68) | (P[:, 1] > 1.45)), head_c  # the tails never reach the T-posed hands


# ------------------------------------------------------------------ decimation with UV / attribute transfer
def decimate_part(P, UV, F, keep):
    """Simplify one part (faces F into the original vertex arrays) to ~keep of its faces. Returns (V, Fn, UVc, src):
    welded new vertices, faces, per-face-corner UVs (barycentric on the closest original face: no smearing across UV
    seams) and, per new vertex, the closest original vertex (for skin weights)."""
    import fast_simplification
    from scipy.spatial import cKDTree
    used = np.unique(F); key = np.round(P[used], 5); uq, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    remap = np.full(len(P), -1); remap[used] = inv; Fw = remap[F]; Fw = Fw[(Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])]
    if keep < 0.999: V, Fn = fast_simplification.simplify(uq.astype(np.float32), Fw.astype(np.int32), target_reduction=1.0 - keep)
    else: V, Fn = uq, Fw
    tri = P[F]; cen = tri.mean(1); tree = cKDTree(cen)
    _, fi = tree.query(V[Fn].mean(1)); UVc = np.zeros((len(Fn), 3, 2))
    for k in range(3):  # barycentric of each new corner in its closest original face (clamped: stays in that face's UV island)
        A, B, C = tri[fi, 0], tri[fi, 1], tri[fi, 2]; q = V[Fn[:, k]]; v0, v1, v2 = B - A, C - A, q - A
        d00, d01, d11 = (v0 * v0).sum(1), (v0 * v1).sum(1), (v1 * v1).sum(1); d20, d21 = (v2 * v0).sum(1), (v2 * v1).sum(1); den = d00 * d11 - d01 * d01 + 1e-20
        b1 = (d11 * d20 - d01 * d21) / den; b2 = (d00 * d21 - d01 * d20) / den; b0 = 1 - b1 - b2
        bc = np.clip(np.stack([b0, b1, b2], 1), -0.25, 1.25); bc /= bc.sum(1, keepdims=True)
        UVc[:, k] = (UV[F[fi]] * bc[:, :, None]).sum(1)
    _, src = cKDTree(P[used]).query(V); return np.asarray(V, float), np.asarray(Fn), UVc, used[src]


def smooth_normals(V, F):
    n = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); N = np.zeros_like(V)
    for k in range(3): np.add.at(N, F[:, k], n)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)


def unweld_uv(V, F, UVc, N, JW, tol=0.012):
    """Vertices per (welded vertex, UV island): the corner UVs of one vertex closer than `tol` are merged (averaged) -
    split only at real seams."""
    J_, W_ = JW; corners = {}
    for f in range(len(F)):
        for k in range(3): corners.setdefault(int(F[f, k]), []).append((f, k))
    outV, outN, outUV, outJ, outW, outF = [], [], [], [], [], np.zeros_like(F)
    for v, cs in corners.items():
        groups = []  # [uv_sum, n, [(f, k)...]]
        for f, k in cs:
            uv = UVc[f, k]
            for g in groups:
                if np.abs(g[0] / g[1] - uv).max() < tol: g[0] = g[0] + uv; g[1] += 1; g[2].append((f, k)); break
            else: groups.append([uv.copy(), 1, [(f, k)]])
        for g in groups:
            i = len(outV); outV.append(V[v]); outN.append(N[v]); outUV.append(g[0] / g[1]); outJ.append(J_[v]); outW.append(W_[v])
            for f, k in g[2]: outF[f, k] = i
    return np.array(outV, np.float32), np.array(outN, np.float32), np.array(outUV, np.float32), np.array(outJ), np.array(outW, np.float32), outF


def top4(ji, wi):
    """Keep the 4 largest influences per vertex, renormalised."""
    o = np.argsort(-wi, axis=1)[:, :4]; J_ = np.take_along_axis(ji, o, 1); W_ = np.take_along_axis(wi, o, 1); W_ /= W_.sum(1, keepdims=True) + 1e-12; return J_, W_


def _islands_to_hair(P, F, fh, dch, max_faces=400, near=0.25):
    """Small disconnected islands of BODY faces lying on a tail's line are stray strands: they go to the hair."""
    import scipy.sparse as sp, scipy.sparse.csgraph as cg
    key = np.round(P, 5); _, inv = np.unique(key, axis=0, return_inverse=True); inv = inv.ravel()
    bf = np.flatnonzero(~fh); Fb = inv[F[bf]]; E_ = np.r_[Fb[:, [0, 1]], Fb[:, [1, 2]], Fb[:, [2, 0]]]
    n = inv.max() + 1; A = sp.coo_matrix((np.ones(len(E_)), (E_[:, 0], E_[:, 1])), shape=(n, n)); _, lab = cg.connected_components(A, directed=False)
    fl = lab[Fb[:, 0]]; cnt = np.bincount(fl); fh = fh.copy(); moved = 0
    dv = np.full(n, 9.0); np.minimum.at(dv, inv, dch)
    for c in np.unique(fl):
        if cnt[c] > max_faces: continue
        sel = bf[fl == c]; vs = np.unique(inv[F[sel]])
        if np.median(dv[vs]) < near: fh[sel] = True; moved += len(sel)
    return fh


# ------------------------------------------------------------------ rig additions
HAIR_BONES = 5


def hair_chains(P, hair, sk, Wm, head_c):
    """Per tail (L = +x, R = -x): joint positions down its centreline (HAIR_BONES + 1 points from the tie to the tip)."""
    out = {}
    for side, sg in (("L", 1.0), ("R", -1.0)):
        sel = hair & (P[:, 0] * sg > 0.12) & (np.linalg.norm(P - head_c, axis=1) > 0.16)
        Q = P[sel]; top, bot = Q[:, 1].max() - 0.04, Q[:, 1].min() + 0.06
        ys = np.linspace(top, bot, HAIR_BONES + 1); pts = []
        for y in ys:
            band = Q[np.abs(Q[:, 1] - y) < 0.06]; pts.append([band[:, 0].mean(), y, band[:, 2].mean()])
        out[side] = np.array(pts)
    return out


def hair_weights(P, chains, head_c, bone_index, head_bone):
    """Scalp: Head. Tails: blend between neighbouring chain bones by height (bone centres at the segment midpoints);
    the top half-segment blends into Head."""
    ji = np.zeros((len(P), 4), int); wi = np.zeros((len(P), 4)); ji[:, 0] = head_bone; wi[:, 0] = 1.0
    for side, sg in (("L", 1.0), ("R", -1.0)):
        C = chains[side]; ys = C[:, 1]; sel = (P[:, 0] * sg > 0.1) & (P[:, 1] < ys[0] + 0.08) & (np.linalg.norm(P - head_c, axis=1) > 0.15)
        s = np.interp(-P[sel, 1], -ys, np.arange(len(ys), dtype=float))  # 0 at the tie .. HAIR_BONES at the tip
        c = np.clip(s - 0.5, -1.0, HAIR_BONES - 1.0); k0 = np.floor(c).astype(int); f = c - k0  # between bone centres k0 and k0+1 (-1 = Head)
        b0 = np.where(k0 < 0, head_bone, [bone_index[f"Hair{side}_{max(k, 0) + 1}"] for k in k0]); b1 = np.array([bone_index[f"Hair{side}_{min(k + 1, HAIR_BONES - 1) + 1}"] for k in k0])
        ji[sel] = 0; wi[sel] = 0; ji[sel, 0] = b0; wi[sel, 0] = 1 - f; ji[sel, 1] = b1; wi[sel, 1] = f
    return ji, wi


def add_bone_along(sk, name, parent, p0, p1, Wm, Wq):
    """A bone at world p0 (rest) whose local +Y points to p1 (Mixamo convention), parented to `parent`."""
    pi = sk.idx[parent]; wq = qbetween([0, 1, 0], np.asarray(p1) - np.asarray(p0)); lq = qnorm(qmul(qinv(Wq[pi]), wq))
    lt = (np.linalg.inv(Wm[pi]) @ np.r_[p0, 1.0])[:3]; sk.add(name, parent, lt, lq); return sk.idx[name]


def cable(p0, p1, r=0.018, rings=10, sides=6, sag=0.0):
    """Tube from p0 (her body) to p1 (the anchor): positions, faces, ring parameter t (0 at p0)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d); u = d / L
    a = np.cross(u, [1, 0, 0]) if abs(u[0]) < 0.9 else np.cross(u, [0, 0, 1]); a /= np.linalg.norm(a); b = np.cross(u, a); V, T = [], []
    for i in range(rings + 1):
        t = i / rings; c = p0 + d * t + np.array([0, -sag * 4 * t * (1 - t), 0])
        for k in range(sides): ang = 2 * math.pi * k / sides; V.append(c + r * (math.cos(ang) * a + math.sin(ang) * b)); T.append(t)
    F = []
    for i in range(rings):
        for k in range(sides):
            a0, a1, b0, b1 = i * sides + k, i * sides + (k + 1) % sides, (i + 1) * sides + k, (i + 1) * sides + (k + 1) % sides; F += [[a0, b0, a1], [a1, b0, b1]]
    return np.array(V), np.array(F), np.array(T)


# ------------------------------------------------------------------ build
DEFAULT = dict(keep_body=0.55, keep_hair=0.6, tex=1024, tex_q=84, vat_height=5.0, vat_offset=[0.0, 1.35, 1.0], glass_r=1.55)  # her feet 1.35 m above the vat floor: centred in the 5 m tank


def prepare(src, cfg=None):
    """Everything except the clips: skeleton (with the new nodes), the three primitives, the texture."""
    from PIL import Image
    cfg = dict(DEFAULT, **(cfg or {}))
    J, BIN = read_glb(src); sk = load_skeleton(J); Wm, Wq = sk.fk()
    pr = J["meshes"][0]["primitives"][0]; A = pr["attributes"]
    P = accessor(J, BIN, A["POSITION"]); UV = accessor(J, BIN, A["TEXCOORD_0"]); F = accessor(J, BIN, pr["indices"]).reshape(-1, 3).astype(int)
    JI = accessor(J, BIN, A["JOINTS_0"]).astype(int); WI = accessor(J, BIN, A["WEIGHTS_0"]).astype(float)
    tex_i = J["textures"][J["materials"][pr.get("material", 0)]["pbrMetallicRoughness"]["baseColorTexture"]["index"]]["source"]
    img = Image.open(io.BytesIO(image_bytes(J, BIN, tex_i))).convert("RGB"); im = np.asarray(img, float) / 255; H, W_ = im.shape[:2]
    col = im[np.clip((UV[:, 1] % 1) * H, 0, H - 1).astype(int), np.clip((UV[:, 0] % 1) * W_, 0, W_ - 1).astype(int)]
    hair, head_c = hair_mask(P, col, sk, Wm)
    ch0 = hair_chains(P, hair, sk, Wm, head_c); import colorsys  # tail strands brushing the hips / shoulders (inside those radii) that are hair-coloured and on a tail's line: hair too
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in col]); hairc = (hsv[:, 1] > 0.3) & (hsv[:, 0] > 0.45) & (hsv[:, 0] < 0.8) & (hsv[:, 2] > 0.3)
    dch = np.min([_seg_dist(P, C[k], C[k + 1]) for C in ch0.values() for k in range(len(C) - 1)], axis=0)
    hair = hair | (hairc & (dch < 0.14) & (np.abs(P[:, 0]) < 0.68)); fh = hair[F].sum(1) >= 2
    fh = _islands_to_hair(P, F, fh, dch)
    old_joints = [sk.nodes[j]["name"] for j in J["skins"][0]["joints"]]
    # -- rig additions: FloatRoot between the armature and Hips, WireAnchor, two hair chains under Head
    arm = sk.nodes[sk.nodes[sk.idx["mixamorig:Hips"]]["parent"]]["name"]
    sk.add("FloatRoot", arm, [0, 0, 0]); sk.reparent("mixamorig:Hips", "FloatRoot"); sk.add("WireAnchor", arm, [0, 0, 0])
    Wm, Wq = sk.fk(); chains = hair_chains(P, hair, sk, Wm, head_c)
    for side in ("L", "R"):
        C = chains[side]; parent = "mixamorig:Head"
        for k in range(HAIR_BONES):
            Wm, Wq = sk.fk(); add_bone_along(sk, f"Hair{side}_{k + 1}", parent, C[k], C[k + 1], Wm, Wq); parent = f"Hair{side}_{k + 1}"
    Wm, Wq = sk.fk()
    joints = old_joints + ["WireAnchor"] + [f"Hair{s}_{k + 1}" for s in "LR" for k in range(HAIR_BONES)]
    jx = {n: i for i, n in enumerate(joints)}; head_j = jx["mixamorig:Head"]
    parts = {}
    for name, FF, keep in (("Body", F[~fh], cfg["keep_body"]), ("Hair", F[fh], cfg["keep_hair"])):
        V, Fn, UVc, src_v = decimate_part(P, UV, FF, keep); N = smooth_normals(V, Fn)
        if name == "Hair":
            ji, wi = hair_weights(V, chains, head_c, jx, head_j)
        else:
            ji, wi = top4(JI[src_v], WI[src_v])  # (old joint indices = the same positions in the new list)
        vV, vN, vUV, vJ, vW, vF = unweld_uv(V, Fn, UVc, N, (ji, wi)); parts[name] = dict(P=vV, N=vN, UV=vUV, J=vJ, W=vW, F=vF)
    # -- cables: nape pair + crown jack, up to anchors under the tank cap (asset coords; vat centre at z = -vat_offset[2])
    top = float(cfg["vat_height"]) - float(cfg["vat_offset"][1]) + 0.05; vz = -float(cfg["vat_offset"][2]); CP, CF, CJ, CW = [], [], [], []  # the cables end 5 cm into the tank cap; CP, CF, CJ, CW = [], [], [], []
    att = [("mixamorig:Neck", [0.05, -0.085, 0.0], [0.28, top, vz - 0.55]), ("mixamorig:Neck", [-0.05, -0.085, 0.0], [-0.28, top, vz - 0.55]),
           ("mixamorig:HeadTop_End", [0.0, 0.0, -0.02], [0.0, top, vz - 0.15])]
    for bone, off, anchor in att:
        p0 = sk.pos(Wm, bone) + np.array([off[0], off[2], off[1]]); V, Fc, T = cable(p0, anchor, rings=12)
        s = T * T * (3 - 2 * T); b = len(CP) and sum(len(x) for x in CP)
        CP.append(V); CF.append(Fc + b); CJ.append(np.stack([np.full(len(V), jx[bone]), np.full(len(V), jx["WireAnchor"]), np.zeros(len(V), int), np.zeros(len(V), int)], 1))
        CW.append(np.stack([1 - s, s, np.zeros(len(V)), np.zeros(len(V))], 1))
    CPa = np.vstack(CP); CFa = np.vstack(CF); parts["Cables"] = dict(P=CPa.astype(np.float32), N=smooth_normals(CPa, CFa).astype(np.float32), UV=None, J=np.vstack(CJ), W=np.vstack(CW).astype(np.float32), F=CFa)
    s_ = int(cfg["tex"]); tex = img.resize((s_, s_), Image.LANCZOS); b = io.BytesIO(); tex.save(b, "JPEG", quality=int(cfg["tex_q"]))
    return dict(sk=sk, joints=joints, parts=parts, tex_jpg=b.getvalue(), chains=chains, cfg=cfg, hair_verts=int(hair.sum()), src_faces=len(F))


def write(prep, path, clips=None, embed_texture=True):
    sk, joints, parts = prep["sk"], prep["joints"], prep["parts"]; w = GLBWriter(); J = w.J
    keep = [i for i, n in enumerate(sk.nodes) if n["name"] != "output_unwrapped"]; nid = {o: k for k, o in enumerate(keep)}
    nodes = []
    for o in keep:
        n = sk.nodes[o]; d = dict(name=n["name"])
        if np.abs(n["t"]).max() > 1e-9: d["translation"] = [float(v) for v in n["t"]]
        if abs(n["r"][3] - 1) > 1e-9: d["rotation"] = [float(v) for v in n["r"]]
        if np.abs(n["s"] - 1).max() > 1e-6: d["scale"] = [float(v) for v in n["s"]]
        ch = [nid[c] for c, m in enumerate(sk.nodes) if m["parent"] == o and c in nid]
        if ch: d["children"] = ch
        nodes.append(d)
    root = next(k for k, o in enumerate(keep) if sk.nodes[o]["parent"] is None and sk.nodes[o]["name"] != "headfront" or sk.nodes[o]["name"] == "SmartRigArmature")
    mesh_node = len(nodes); nodes.append(dict(name="Specimen", mesh=0, skin=0)); nodes[root].setdefault("children", []).append(mesh_node)
    J["nodes"] = nodes; J["scenes"] = [dict(name="Scene", nodes=[root])]; J["scene"] = 0
    Wm, _ = sk.fk(); jn = [nid[sk.idx[n]] for n in joints]
    ibm = np.array([np.linalg.inv(Wm[sk.idx[n]]).T for n in joints], np.float32).reshape(-1, 16)
    J["skins"] = [dict(joints=jn, inverseBindMatrices=w.acc(ibm, "MAT4", 5126), skeleton=root)]
    mats = [dict(name="Specimen", doubleSided=True, pbrMetallicRoughness=dict(baseColorFactor=[1, 1, 1, 1], metallicFactor=0.15, roughnessFactor=0.55)),
            dict(name="Cable", pbrMetallicRoughness=dict(baseColorFactor=[0.08, 0.07, 0.1, 1], metallicFactor=0.3, roughnessFactor=0.5))]
    if embed_texture:
        J["images"] = [dict(bufferView=w.view(prep["tex_jpg"]), mimeType="image/jpeg", name="specimen_basecolor")]; J["samplers"] = [dict(magFilter=9729, minFilter=9987)]
        J["textures"] = [dict(source=0, sampler=0)]; mats[0]["pbrMetallicRoughness"]["baseColorTexture"] = dict(index=0)
    J["materials"] = mats; prims = []
    for name in ("Body", "Hair", "Cables"):
        p = parts[name]; at = dict(POSITION=w.acc(p["P"].astype(np.float32), "VEC3", 5126, 34962, minmax=True), NORMAL=w.acc(p["N"].astype(np.float32), "VEC3", 5126, 34962))
        if p["UV"] is not None: at["TEXCOORD_0"] = w.acc(p["UV"].astype(np.float32), "VEC2", 5126, 34962)
        W8 = np.round(p["W"] * 255).astype(int); W8[np.arange(len(W8)), W8.argmax(1)] += 255 - W8.sum(1)  # exact 255 sums
        at["JOINTS_0"] = w.acc(p["J"].astype(np.uint8), "VEC4", 5121, 34962); at["WEIGHTS_0"] = w.acc(W8.astype(np.uint8), "VEC4", 5121, 34962, normalized=True)
        prims.append(dict(attributes=at, indices=w.acc(p["F"].astype(np.uint16).reshape(-1), "SCALAR", 5123, 34963), material=0 if name != "Cables" else 1, extras=dict(part=name)))
    J["meshes"] = [dict(name="Specimen", primitives=prims)]
    if clips:
        J["animations"] = []
        for cname, (times, tracks) in clips.items():
            tin = w.acc(np.asarray(times, np.float32).reshape(-1, 1), "SCALAR", 5126, minmax=True); ch, sm = [], []
            for (node, prop), vals in tracks.items():
                sm.append(dict(input=tin, output=w.acc(np.asarray(vals, np.float32), "VEC4" if prop == "rotation" else "VEC3", 5126), interpolation="LINEAR"))
                ch.append(dict(sampler=len(sm) - 1, target=dict(node=nid[sk.idx[node]], path=prop)))
            J["animations"].append(dict(name=cname, channels=ch, samplers=sm))
    return w.write(path)


# ------------------------------------------------------------------ posing (FK + IK)
M = "mixamorig:"


def swing_twist(q, axis):
    """Split q = swing * twist, twist about `axis` (unit)."""
    q = qnorm(q); p = np.dot(q[:3], axis) * np.asarray(axis); tw = qnorm([*p, q[3]]) if np.linalg.norm([*p, q[3]]) > 1e-9 else np.array([0, 0, 0, 1.0])
    return qmul(q, qinv(tw)), tw


class Poser:
    """Builds one frame: rotations are set top-down; every helper works from the current (posed) parent."""
    def __init__(self, sk):
        self.sk = sk; self.rest_Wm, self.rest_Wq = sk.fk(); self.rot = {}; self.trans = {}; self._W = None

    def W(self):
        if self._W is None: self._W = self.sk.fk(self.rot, self.trans)
        return self._W

    def _set(self, name, lq): self.rot[name] = qnorm(lq); self._W = None
    def local(self, name): return self.rot.get(name, self.sk.nodes[self.sk.idx[name]]["r"])
    def pos(self, name): return self.sk.pos(self.W()[0], name)
    def wq(self, name): return self.W()[1][self.sk.idx[name]]
    def pwq(self, name):
        p = self.sk.nodes[self.sk.idx[name]]["parent"]; return self.W()[1][p]

    def rot_world(self, name, axis, ang):
        """Turn a bone by `ang` about a WORLD axis (through its own origin)."""
        if abs(ang) < 1e-9: return
        nw = qmul(qaxis(axis, ang), self.wq(name)); self._set(name, qmul(qinv(self.pwq(name)), nw))

    def rot_rest_axis(self, name, axis_world_rest, ang):
        """Turn about an axis fixed in the bone's REST frame (given as the world direction it has in the rest pose):
        anatomical axes (finger curl, knee hinge) that move with the bone."""
        a_loc = qrot(qinv(self.rest_Wq[self.sk.idx[name]]), axis_world_rest); self._set(name, qmul(self.local(name), qaxis(a_loc, ang)))

    def aim(self, name, target_dir):
        """Swing the bone so its +Y points along target_dir (minimal rotation from where its parent carries it)."""
        cur = qrot(self.wq(name), [0, 1, 0]); qs = qbetween(cur, target_dir); nw = qmul(qs, self.wq(name)); self._set(name, qmul(qinv(self.pwq(name)), nw))

    def twist_to(self, name, local_axis, target_world):
        """Turn the bone about its own +Y so that its `local_axis` points as close as possible to target_world."""
        q = self.wq(name); y = qrot(q, [0, 1, 0]); a = qrot(q, local_axis); t = np.asarray(target_world, float)
        a_p = a - y * np.dot(a, y); t_p = t - y * np.dot(t, y)
        if np.linalg.norm(a_p) < 1e-6 or np.linalg.norm(t_p) < 1e-6: return
        a_p /= np.linalg.norm(a_p); t_p /= np.linalg.norm(t_p); ang = math.atan2(np.dot(np.cross(a_p, t_p), y), np.dot(a_p, t_p))
        self.rot_world(name, y, ang)

    def arm_ik(self, side, wrist, pole, palm_out, fingers):
        """Two-bone IK: upper arm + forearm reach `wrist` with the elbow towards `pole`; the hand points `fingers` with its
        palm facing `palm_out`. The forearm takes the pronation / supination (twist), the wrist only bends."""
        A, F_, H = M + side + "Arm", M + side + "ForeArm", M + side + "Hand"
        S_ = self.pos(A); l1 = np.linalg.norm(self.sk.pos(self.rest_Wm, F_) - self.sk.pos(self.rest_Wm, A)); l2 = np.linalg.norm(self.sk.pos(self.rest_Wm, H) - self.sk.pos(self.rest_Wm, F_))
        T = np.asarray(wrist, float); d_ = T - S_; d = float(np.clip(np.linalg.norm(d_), abs(l1 - l2) + 1e-3, l1 + l2 - 1e-3)); u = d_ / np.linalg.norm(d_)
        a = (l1 * l1 - l2 * l2 + d * d) / (2 * d); h = math.sqrt(max(l1 * l1 - a * a, 0)); pv = np.asarray(pole, float) - u * np.dot(pole, u); pv /= np.linalg.norm(pv) + 1e-12
        E = S_ + u * a + pv * h; self.aim(A, E - S_); self.aim(F_, S_ + u * d - E)
        # hand: aim the fingers, then roll the palm; move the roll into the forearm (anatomy: pronation lives there)
        palm_loc = qrot(qinv(self.rest_Wq[self.sk.idx[H]]), [0, -1, 0]); self.aim(H, fingers); self.twist_to(H, palm_loc, palm_out)
        fq = self.wq(F_); hq = self.wq(H); rel = qmul(qinv(fq), hq); ax = np.array([0, 1.0, 0]); sw, tw = swing_twist(qmul(rel, qinv(qmul(qinv(self.rest_Wq[self.sk.idx[F_]]), self.rest_Wq[self.sk.idx[H]]))), ax)
        self._set(F_, qmul(self.local(F_), tw)); nw = hq; self._set(H, qmul(qinv(self.wq(F_)), nw))  # the hand keeps its world pose

    def curl(self, side, amount, thumb=None, spread=0.0):
        """Fingers curl towards the palm (amount in rad per joint), optional spread (abduction)."""
        h = self.sk.idx[M + side + "Hand"]; palm = qrot(self.rest_Wq[h], qrot(qinv(self.rest_Wq[h]), [0, -1, 0]))  # world palm normal at rest
        for k, f in enumerate(("Index", "Middle", "Ring", "Pinky")):
            for j in (1, 2, 3):
                b = M + side + "Hand" + f + str(j); bi = self.sk.idx[b]; d = qrot(self.rest_Wq[bi], [0, 1, 0]); ax = np.cross(d, palm)
                self.rot_rest_axis(b, ax, amount * (1.0 if j > 1 else 0.85))
                if j == 1 and spread: self.rot_rest_axis(b, palm, spread * (k - 1.5) / 1.5 * (1 if side == "Left" else -1))
        t_amt = amount * 0.5 if thumb is None else thumb
        for j in (1, 2, 3):
            b = M + side + "HandThumb" + str(j); bi = self.sk.idx[b]; d = qrot(self.rest_Wq[bi], [0, 1, 0]); ax = np.cross(d, palm); self.rot_rest_axis(b, ax, t_amt * (0.6 if j == 1 else 1.0))

    def leg(self, side, hip_flex, knee_flex, ankle, abduct=0.0):
        """Hip flexion (+ = thigh forward), abduction (+ = outward), knee flexion (shin back only), ankle (+ = toes down)."""
        sg = 1.0 if side == "Left" else -1.0
        self.rot_world(M + side + "UpLeg", [-1, 0, 0], hip_flex); self.rot_world(M + side + "UpLeg", [0, 0, 1], sg * abduct)
        self.rot_rest_axis(M + side + "Leg", [1, 0, 0], knee_flex); self.rot_rest_axis(M + side + "Foot", [1, 0, 0], ankle)

    def hair(self, t, amp=1.0, tempo=1.0, spread=0.1, back=0.28, periods=(3.0, 2.0)):
        """Underwater flow: phase-lagged waves down each chain (amplitude grows towards the tip), a little buoyancy
        (tails drift outwards / back). Periods divide the clip length (seamless loops)."""
        for side, sg in (("L", 1.0), ("R", -1.0)):
            for k in range(HAIR_BONES):
                b = f"Hair{side}_{k + 1}"; g = (k + 1) / HAIR_BONES; ph = k * 0.75 + (0.9 if side == "R" else 0.0)
                sway = amp * (0.05 + 0.08 * g) * math.sin(2 * math.pi * t / periods[0] * tempo - ph)
                fore = amp * (0.04 + 0.07 * g) * math.sin(2 * math.pi * t / periods[1] * tempo - ph * 1.3 + 0.7)
                self.rot_rest_axis(b, [0, 0, 1], sg * (spread * (1 if k == 0 else 0.35) + sway)); self.rot_rest_axis(b, [1, 0, 0], back * (1 if k == 0 else 0.3) + fore)  # (+ about X: the tail drifts back)

    def frame(self):
        """{name: local quaternion} for every animated node."""
        return {n: self.local(n) for n in self.rot}


# ------------------------------------------------------------------ clips
def _glass(cfg, theta, y, r=None):
    """Point on the vat glass (asset coords) at angle theta from her front (+ = towards +x), height y; outward normal."""
    R = float(r if r is not None else cfg["glass_r"]); oz = float(cfg["vat_offset"][2]); n = np.array([math.sin(theta), 0.0, math.cos(theta)])
    return np.array([R * n[0], y, -oz + R * n[2]]), n


def _body(P, t, lean, twist, side, hips_fwd, hips_up):
    P.trans[M + "Hips"] = P.sk.nodes[P.sk.idx[M + "Hips"]]["t"] + np.array([0.0, hips_up, hips_fwd]); P._W = None
    P.rot_world(M + "Hips", [1, 0, 0], lean * 0.4); P.rot_world(M + "Hips", [0, 1, 0], twist * 0.4)
    for b, f in (("Spine", 0.25), ("Spine1", 0.2), ("Spine2", 0.15)):
        P.rot_world(M + b, [1, 0, 0], lean * f); P.rot_world(M + b, [0, 1, 0], twist * f); P.rot_world(M + b, [0, 0, 1], side * f)


def _head(P, yaw, pitch, roll=0.0):
    for b, f in (("Neck", 0.4), ("Head", 0.6)):
        P.rot_world(M + b, [0, 1, 0], yaw * f); P.rot_world(M + b, [-1, 0, 0], pitch * f); P.rot_world(M + b, [0, 0, 1], roll * f)


def _shoulders(P, lift):
    P.rot_world(M + "LeftShoulder", [0, 0, 1], lift); P.rot_world(M + "RightShoulder", [0, 0, -1], lift)


def pose_panic(P, t, cfg):
    """Palms pressed to the glass and sliding, searching for a way out; kicking; hair flowing. Loop 6 s."""
    T = 2 * math.pi
    _body(P, t, lean=0.2 + 0.04 * math.sin(T * t / 3), twist=0.1 * math.sin(T * t / 3), side=0.05 * math.sin(T * t / 2), hips_fwd=0.07 + 0.02 * math.sin(T * t / 3), hips_up=0.03 * math.sin(T * t / 2))
    _head(P, yaw=0.5 * math.sin(T * t / 3 + 0.5) + 0.15 * math.sin(T * t / 1.5), pitch=0.12 + 0.12 * math.sin(T * t / 2 + 1.0), roll=0.06 * math.sin(T * t / 0.5))
    _shoulders(P, 0.18 + 0.05 * math.sin(T * t / 2))
    for side, sg, ph in (("Left", 1.0, 0.0), ("Right", -1.0, 1.7)):
        th = sg * (0.2 + 0.06 * math.sin(T * t / 3 + ph)); y = 1.52 + 0.09 * math.sin(T * t / 2 + ph * 1.5)
        ft = cfg.get("panic_tilt", 0.3); C, n = _glass(cfg, th, y, r=float(cfg["glass_r"]) - 0.035); tang = np.cross([0, 1, 0], n) * sg; f = np.array([0, 1.0, 0]) * 0.8 + tang * ft; f -= n * np.dot(f, n); f /= np.linalg.norm(f)
        pl = cfg.get("panic_pole", [0.6, -0.8, -0.2]); P.arm_ik(side, C - n * 0.03 - f * 0.075, pole=[sg * pl[0], pl[1], pl[2]], palm_out=n, fingers=f)
        P.curl(side, 0.1 + 0.12 * (0.5 + 0.5 * math.sin(T * t / 1.5 + ph)), thumb=0.15, spread=0.12)
    for side, ph in (("Left", 0.0), ("Right", math.pi)):
        k = math.sin(T * t / 2 + ph); P.leg(side, hip_flex=0.22 + 0.16 * k, knee_flex=0.5 + 0.3 * math.sin(T * t / 2 + ph - 1.2), ankle=0.45, abduct=0.06)
    P.hair(t, amp=1.0, periods=(3.0, 2.0))


def _strike(phi):
    """0 = fist on the glass, 1 = drawn back. Rests on the glass briefly, pulls back, accelerates in."""
    if phi < 0.1: return 0.0
    if phi < 0.55: u = (phi - 0.1) / 0.45; return u * u * (3 - 2 * u)
    u = (phi - 0.55) / 0.45; return 1 - u * u


def pose_bang(P, t, cfg):
    """Fists pounding the glass, alternating (L at 0.25 s, R at 0.75 s, every second), the body jolting with each blow;
    hair whipping. Loop 2 s."""
    T = 2 * math.pi; hits = [((t - h) % 1.0) for h in (0.25, 0.75)]; jolt = sum(math.exp(-((x if x < 0.5 else x - 1.0) / 0.06) ** 2) for x in hits)
    _body(P, t, lean=0.3 - 0.06 * jolt, twist=0.12 * math.sin(T * t / 1.0), side=0.05 * math.sin(T * t / 2), hips_fwd=0.1 - 0.015 * jolt, hips_up=0.02 * math.sin(T * t / 1.0))
    _head(P, yaw=0.12 * math.sin(T * t / 2), pitch=0.05 - 0.08 * jolt, roll=0.05 * math.sin(T * t / 0.5))
    _shoulders(P, 0.22)
    for side, sg, h in (("Left", 1.0, 0.25), ("Right", -1.0, 0.75)):
        s_ = _strike((t - h) % 1.0); th = sg * 0.24
        C, n = _glass(cfg, th, 1.55, r=float(cfg["glass_r"]) - 0.04); back = C - n * 0.24 + np.array([0, 0.1, 0])  # wind-up: drawn back, elbow bent (never locked overhead)
        med = np.array([-sg, 0.0, 0.0]); f = np.array([0, 0.85, 0]) + med * 0.35 - n * 0.15; f /= np.linalg.norm(f)  # hammer fist: knuckles up / in
        hit = C - n * 0.055 - f * 0.05; wrist = hit + (back - hit) * s_
        P.arm_ik(side, wrist, pole=[sg * 0.7, -0.7, -0.1], palm_out=med, fingers=f)  # the pinky edge of the fist strikes the glass
        P.curl(side, 1.25, thumb=0.6)
    for side, ph in (("Left", 0.0), ("Right", math.pi)):
        P.leg(side, hip_flex=0.3 + 0.12 * math.sin(T * t / 1.0 + ph), knee_flex=0.7 + 0.25 * math.sin(T * t / 1.0 + ph - 1.0), ankle=0.5, abduct=0.05)
    P.hair(t, amp=1.35, periods=(2.0, 1.0))


CLIPS = dict(panic=(pose_panic, 6.0, 20), bang=(pose_bang, 2.0, 30))


def make_clips(prep):
    sk, cfg = prep["sk"], prep["cfg"]; out = {}
    for name, (fn, dur, fps) in CLIPS.items():
        n = int(round(dur * fps)); times = [k / fps for k in range(n + 1)]; frames = []
        for t in times:
            P = Poser(sk); fn(P, t % dur if t < dur else 0.0, cfg); frames.append((P.frame(), dict(P.trans)))  # last key = first: seamless
        bones = sorted({b for f, _ in frames for b in f}); tracks = {}
        for b in bones:
            vals = [f.get(b, sk.nodes[sk.idx[b]]["r"]) for f, _ in frames]
            for k in range(1, len(vals)):  # keep neighbouring keys in the same hemisphere (no long-way-round slerps)
                if np.dot(vals[k], vals[k - 1]) < 0: vals[k] = -vals[k]
            tracks[(b, "rotation")] = np.array(vals)
        tb = sorted({b for _, tr in frames for b in tr})
        for b in tb: tracks[(b, "translation")] = np.array([tr.get(b, sk.nodes[sk.idx[b]]["t"]) for _, tr in frames])
        out[name] = (times, tracks)
    return out


def skin_part(prep, part, rot, trans=None):
    """Linear-blend skinning of one primitive for a pose (asset coords) - for checks and tests."""
    sk, joints = prep["sk"], prep["joints"]; rest, _ = sk.fk(); Wm, _ = sk.fk(rot, trans)
    S_ = np.array([Wm[sk.idx[n]] @ np.linalg.inv(rest[sk.idx[n]]) for n in joints]); p = prep["parts"][part]
    Ph = np.c_[p["P"], np.ones(len(p["P"]))]; out = np.zeros((len(Ph), 3))
    for k in range(4): out += p["W"][:, k:k + 1] * np.einsum("nij,nj->ni", S_[p["J"][:, k]], Ph)[:, :3]
    return out


def clip_report(prep, step=2):
    """Per clip: max distance from the vat axis of the body (hands excluded), hands, hair, cables; and the joint-angle
    extremes (elbow / knee flexion, wrist bend, forearm twist, neck + head yaw) over every `step`-th frame."""
    sk, cfg = prep["sk"], prep["cfg"]; oz = float(cfg["vat_offset"][2]); rep = {}
    hand_v = None
    for name, (fn, dur, fps) in CLIPS.items():
        n = int(round(dur * fps)); R = dict(body=0, hands=0, hair=0, cables=0, elbow=[180, 0], knee=[180, 0], wrist=0, twist=0, yaw=0, hair_min_y=9)
        for k in range(0, n, step):
            P = Poser(sk); fn(P, k / fps, cfg); rot, tr = P.frame(), dict(P.trans); Wm, Wq = P.W()
            for part in ("Body", "Hair", "Cables"):
                X = skin_part(prep, part, rot, tr); r = np.hypot(X[:, 0], X[:, 2] + oz)
                if part == "Body":
                    p = prep["parts"]["Body"]; jn = prep["joints"]; hb = np.array(["Hand" in jn[j] for j in p["J"][:, 0]])
                    R["body"] = max(R["body"], float(r[~hb].max())); R["hands"] = max(R["hands"], float(r[hb].max()))
                elif part == "Hair": R["hair"] = max(R["hair"], float(r.max())); R["hair_min_y"] = min(R["hair_min_y"], float(X[:, 1].min()))
                else: R["cables"] = max(R["cables"], float(r[X[:, 1] < 3.0].max()))
            for sd in ("Left", "Right"):
                pa = lambda b: sk.pos(Wm, M + sd + b); u1 = pa("ForeArm") - pa("Arm"); u2 = pa("Hand") - pa("ForeArm"); u3 = pa("HandMiddle1") - pa("Hand")
                ang = lambda a_, b_: math.degrees(math.acos(np.clip(np.dot(a_, b_) / np.linalg.norm(a_) / np.linalg.norm(b_), -1, 1)))
                e = ang(u1, u2); R["elbow"] = [min(R["elbow"][0], e), max(R["elbow"][1], e)]; R["wrist"] = max(R["wrist"], ang(u2, u3))
                k_ = ang(pa("Leg") - pa("UpLeg"), pa("Foot") - pa("Leg")); R["knee"] = [min(R["knee"][0], k_), max(R["knee"][1], k_)]
                if e > 15:  # pronation / supination: the palm's facing round the forearm vs neutral (thumb up: palm towards the elbow-hinge axis's medial side)
                    h = np.cross(u1, u2); h *= (1.0 if sd == "Left" else -1.0) / np.linalg.norm(h); hi = sk.idx[M + sd + "Hand"]
                    pn = qrot(Wq[hi], qrot(qinv(Poser(sk).rest_Wq[hi]), [0, -1, 0])); k_ = np.cross(u3, pn)  # the axis across the knuckles: wrist flexion / extension turns about it, pronation turns it
                    a_ = u2 / np.linalg.norm(u2); k_ = k_ - a_ * np.dot(k_, a_); kn = np.cross(a_, h)  # neutral: thumb up, palm towards the medial side of the elbow hinge
                    R["twist"] = max(R["twist"], ang(k_, kn))
            hq = Wq[sk.idx[M + "Head"]]; f = qrot(hq, qrot(qinv(Poser(sk).rest_Wq[sk.idx[M + "Head"]]), [0, 0, 1])); R["yaw"] = max(R["yaw"], abs(math.degrees(math.atan2(f[0], f[2]))))
        rep[name] = {k: (round(v, 3) if isinstance(v, float) else [round(x, 1) for x in v] if isinstance(v, list) else v) for k, v in R.items()}
    return rep


def build_asset(src, out, cfg=None, name="specimen"):
    """<out>.glb (texture embedded: Godot), <out>_preview.glb (no images: the sandboxed preview) + <out>.jpg, <out>.json."""
    prep = prepare(src, cfg); clips = make_clips(prep); rep = clip_report(prep, step=2)
    n_full = write(prep, out + ".glb", clips, embed_texture=True); n_prev = write(prep, out + "_preview.glb", clips, embed_texture=False)
    open(out + ".jpg", "wb").write(prep["tex_jpg"]); cfg = prep["cfg"]
    meta = dict(name=name, source=src, clips=dict(idle="panic", alert="bang"), float=dict(node="FloatRoot", amp=0.08, period=4.0),
                vat=dict(offset=cfg["vat_offset"], glass_r=cfg["glass_r"], note="asset origin = vat centre + (0, offset[1] above the vat floor, offset[2] towards her front); the clips' contacts assume it"),
                triangles={k: int(len(v["F"])) for k, v in prep["parts"].items()}, source_triangles=prep["src_faces"], bytes=dict(glb=n_full, preview_glb=n_prev, jpg=len(prep["tex_jpg"])),
                bones=len(prep["joints"]), checks=rep, texture=out.split("/")[-1] + ".jpg",
                note="Stage 152: hair split from the body (own primitive, two 5-bone chains + Head), FloatRoot (runtime bob), WireAnchor + cables; clips authored in pipeline/specimen.py")
    json.dump(meta, open(out + ".json", "w"), indent=1); return meta


if __name__ == "__main__":
    a = sys.argv[1:]; m = build_asset(a[0], a[1], name=a[1].split("/")[-1]); print(json.dumps({k: m[k] for k in ("triangles", "bytes", "bones", "checks")}, indent=1))
