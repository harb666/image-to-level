"""Stage 168: the showcase monitor's picture - an exploded wireframe "dissection scan" of the vat specimen, drawn from
her real mesh (assets/characters/specimen/cyber_girl.glb, bind pose): the body split into parts by the bone that drives
each face (head, hair, torso, upper arms, forearms + hands, thighs, shins + feet), pushed apart, every edge drawn as
glowing cyan wire on a dark blueprint grid, with dashed joint lines, callout labels and readouts; one arm flagged in the
Construct Error pink. Writes levels/assembly_ascent/references/specimen_schematic.png (opaque RGBA, ~2.2:1).

    python3 pipeline/make_specimen_schematic.py [out.png]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import specimen as S

W, H, SS = 2200, 1000, 2  # final size, supersampling
CYAN, TEAL, PINK, GRID, BG = (70, 215, 255), (90, 170, 255), (255, 70, 200), (18, 52, 78), (5, 14, 26)  # (TEAL: the hair - her blue)
FONT = next((p for p in ("/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
             if os.path.exists(p)), None)

# part: (bones whose prefix drives it, exploded offset in metres (x is mirrored by side), label)
PARTS = {
    "head": (("Neck", "Head", "HeadTop", "LeftEye", "RightEye"), (0.0, 0.34), "CRANIAL UNIT"),
    "hair": ((), (0.0, 1.05), "NEURAL FIBRE ARRAY"),
    "torso": (("Hips", "Spine", "LeftShoulder", "RightShoulder"), (0.0, 0.0), "THORAX CORE"),
    "upperarm": (("Arm",), (0.22, 0.04), "SERVO ARM"),
    "forearm": (("ForeArm", "Hand"), (0.46, 0.06), "MANIPULATOR"),
    "thigh": (("UpLeg",), (0.08, -0.16), "HIP ACTUATOR"),
    "shin": (("Leg", "Foot", "Toe"), (0.14, -0.38), "LOCOMOTOR"),
}


def part_of(bone, prim):
    if prim == "Hair": return "hair"
    b = bone.replace("mixamorig:", "")
    side = "L" if b.startswith("Left") else "R" if b.startswith("Right") else ""
    core = b[4:] if side == "L" else b[5:] if side == "R" else b
    if b.startswith(("LeftShoulder", "RightShoulder")): return "torso"
    if core.startswith("Hand") or core.startswith("ForeArm"): return "forearm" + side
    if core.startswith("Arm"): return "upperarm" + side
    if core.startswith("UpLeg"): return "thigh" + side
    if core.startswith(("Leg", "Foot", "Toe")): return "shin" + side
    if b.startswith(("Neck", "Head", "LeftEye", "RightEye")) or "Eye" in b: return "head"
    return "torso"


def load():
    J, BIN = S.read_glb(os.path.join(ROOT, "assets", "characters", "specimen", "cyber_girl.glb"))
    joints = [J["nodes"][j]["name"] for j in J["skins"][0]["joints"]]; out = []
    for p in J["meshes"][0]["primitives"]:
        nm = p["extras"]["part"]
        if nm == "Cables": continue
        P = S.accessor(J, BIN, p["attributes"]["POSITION"]); F = S.accessor(J, BIN, p["indices"]).reshape(-1, 3)  # (wires: a simplified copy per part, below)
        Jn = S.accessor(J, BIN, p["attributes"]["JOINTS_0"]); Wt = S.accessor(J, BIN, p["attributes"]["WEIGHTS_0"])
        dom = Jn[np.arange(len(Jn)), np.argmax(Wt, 1)]  # each vertex's strongest bone
        lab = np.array([part_of(joints[int(dom[f[0]])], nm) for f in F])  # a face goes with its first corner's bone
        out.append((P, F, lab))
    return out


def main(out_path):
    prims = load()
    pieces = {}  # part -> list of (P, faces)
    for P, F, lab in prims:
        for k in np.unique(lab): pieces.setdefault(k, []).append((P, F[lab == k]))
    # exploded offsets (side from the part's centroid: her left is +x, facing +z)
    off = {}
    for k, lst in pieces.items():
        base = k.rstrip("LR") if k[-1] in "LR" and k[:-1] in PARTS else k
        ox, oy = PARTS[base][1]; cx = np.mean(np.concatenate([P[np.unique(F)] for P, F in lst])[:, 0])
        off[k] = np.array([np.sign(cx) * ox if ox else 0.0, oy])
    # projection (front, orthographic): fit the exploded figure into the left 60% of the picture
    pts = np.concatenate([P[np.unique(F)][:, :2] + off[k] for k, lst in pieces.items() for P, F in lst])
    lo, hi = pts.min(0), pts.max(0); box = (60 * SS, 175 * SS, 1150 * SS, (H - 80) * SS)
    sc = min((box[2] - box[0]) / (hi[0] - lo[0]), (box[3] - box[1]) / (hi[1] - lo[1]))
    ctr = np.array([(box[0] + box[2]) / 2, (box[1] + box[3]) / 2]); mid = (lo + hi) / 2
    to_px = lambda q: np.stack([ctr[0] + (q[..., 0] - mid[0]) * sc, ctr[1] - (q[..., 1] - mid[1]) * sc], -1)

    img = Image.new("RGB", (W * SS, H * SS), BG); d = ImageDraw.Draw(img)
    for gx in range(0, W * SS, 40 * SS): d.line([(gx, 0), (gx, H * SS)], fill=GRID if gx % (200 * SS) else (28, 78, 110), width=SS)
    for gy in range(0, H * SS, 40 * SS): d.line([(0, gy), (W * SS, gy)], fill=GRID if gy % (200 * SS) else (28, 78, 110), width=SS)
    glow = Image.new("RGB", img.size, (0, 0, 0)); dg = ImageDraw.Draw(glow); wire = Image.new("RGB", img.size, (0, 0, 0)); dw = ImageDraw.Draw(wire)
    flag = "forearmR"  # the "damaged" limb, flagged pink
    cents = {}
    for k, lst in pieces.items():
        col = TEAL if k == "hair" else PINK if k == flag else CYAN
        for P, F in lst:
            Q = to_px(P[:, :2] + off[k])
            for f in F:  # faint silhouette fill (depth), then the wire
                dg.polygon([tuple(Q[i]) for i in f], fill=tuple(int(c * 0.10) for c in col))
            try:  # Stage 178 (HD): wire a simplified copy (~1/4 of the faces) - distinct lines, not a haze
                import fast_simplification
                Vd, Fd = fast_simplification.simplify(P[:, :3].astype(np.float32), F.astype(np.int32), target_reduction=0.8 if k != "hair" else 0.9)
                Qd = to_px(np.asarray(Vd)[:, :2] + off[k])
            except Exception: Vd, Fd, Qd = P, F, Q
            E = np.sort(np.concatenate([Fd[:, [0, 1]], Fd[:, [1, 2]], Fd[:, [2, 0]]]), 1); E = np.unique(E, axis=0)
            for a, b in E: dw.line([tuple(Qd[a]), tuple(Qd[b])], fill=tuple(int(c * (0.5 if k == "hair" else 0.8)) for c in col), width=2 * SS)
            sil = Image.new("L", img.size, 0); ds = ImageDraw.Draw(sil)
            for f in F: ds.polygon([tuple(Q[i]) for i in f], fill=255)
            edge = np.asarray(sil.filter(ImageFilter.MaxFilter(5)), float) - np.asarray(sil.filter(ImageFilter.MinFilter(5)), float)  # the part's outline, bright
            ow = np.asarray(wire, float); ow = np.maximum(ow, (edge[..., None] / 255.0) * np.array(col)[None, None]); wire = Image.fromarray(ow.astype(np.uint8)); dw = ImageDraw.Draw(wire)
        allp = np.concatenate([P[np.unique(F)][:, :2] for P, F in lst]) + off[k]; cents[k] = to_px(allp.mean(0));
    halo = wire.filter(ImageFilter.GaussianBlur(4 * SS))
    img = Image.fromarray(np.clip(np.asarray(img, int) + np.asarray(glow, int) + np.asarray(wire, int) * 1.25 + np.asarray(halo, int) * 1.3, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    f_big = ImageFont.truetype(FONT, 64 * SS) if FONT else ImageFont.load_default(); f_mid = ImageFont.truetype(FONT, 38 * SS) if FONT else f_big  # Stage 178: legible on the wall
    f_sm = ImageFont.truetype(FONT, 27 * SS) if FONT else f_big
    # dashed joint lines between each limb part and what it was cut from
    links = [("head", "torso"), ("hair", "head")] + [(f"{a}{s}", f"{b}{s}" if b != "torso" else "torso") for s in "LR" for a, b in
                                                     (("upperarm", "torso"), ("forearm", "upperarm"), ("thigh", "torso"), ("shin", "thigh"))]
    for a, b in links:
        if a in cents and b in cents:
            p0, p1 = cents[a], cents[b]; n_ = int(np.hypot(*(p1 - p0)) // (18 * SS))
            for t in range(0, n_, 2): d.line([tuple(p0 + (p1 - p0) * t / n_), tuple(p0 + (p1 - p0) * (t + 1) / n_)], fill=(90, 160, 200), width=2 * SS)
    # callouts: a leader line from each part to a label in the right-hand column
    rows = sorted([k for k in ("hair", "head", "torso", "upperarmL", "upperarmR", "forearmL", "forearmR", "thighL", "thighR", "shinL", "shinR") if k in cents], key=lambda k: (cents[k][1], -cents[k][0]))  # top to bottom: leaders cross less
    x_lab = 1330 * SS
    for i, k in enumerate(rows):
        base = k[:-1] if k[-1] in "LR" and k[:-1] in PARTS else k; side = (" L" if k.endswith("L") else " R") if k != base else ""
        y_lab = (160 + i * 72) * SS; col = PINK if k == flag else TEAL if k == "hair" else CYAN; c = cents[k]
        d.line([tuple(c), (x_lab - 40 * SS, y_lab + 20 * SS), (x_lab - 10 * SS, y_lab + 20 * SS)], fill=col, width=2 * SS)
        d.ellipse([c[0] - 5 * SS, c[1] - 5 * SS, c[0] + 5 * SS, c[1] + 5 * SS], outline=col, width=2 * SS)
        d.text((x_lab, y_lab), f"{i + 1:02d} {PARTS[base][2]}{side}", font=f_mid, fill=col)
        st = "FAULT - SEVERED" if k == flag else ["NOMINAL", "STABLE", "NOMINAL", "SYNC 98%", "SYNC 97%"][i % 5]
        d.text((x_lab + 530 * SS, y_lab + 8 * SS), st, font=f_sm, fill=(255, 120, 215) if k == flag else (110, 170, 200))
    # header / footer readouts
    d.text((50 * SS, 22 * SS), "SPECIMEN 07 // DISSECTION SCAN", font=f_big, fill=CYAN)
    d.text((54 * SS, 100 * SS), "CONTAINMENT VAT 01  ::  STATUS: AGITATED", font=f_sm, fill=(130, 200, 235))
    d.text((1500 * SS, 26 * SS), "INTEGRITY 63%", font=f_mid, fill=(255, 110, 210)); d.rectangle([1500 * SS, 82 * SS, 2150 * SS, 108 * SS], outline=CYAN, width=3 * SS)
    d.rectangle([1506 * SS, 88 * SS, int((1506 + 638 * 0.63) * SS), 102 * SS], fill=(255, 90, 200))
    d.text((54 * SS, (H - 56) * SS), f"MESH {sum(len(F) for lst in pieces.values() for _, F in lst)} POLY  ::  {len(pieces)} SEGMENTS  ::  SCAN 0x07F3", font=f_sm, fill=(90, 150, 190))
    for x0, y0, sx, sy in ((14, 14, 1, 1), (W - 14, 14, -1, 1), (14, H - 14, 1, -1), (W - 14, H - 14, -1, -1)):  # corner brackets
        d.line([(x0 * SS, y0 * SS), ((x0 + sx * 70) * SS, y0 * SS)], fill=CYAN, width=3 * SS); d.line([(x0 * SS, y0 * SS), (x0 * SS, (y0 + sy * 70) * SS)], fill=CYAN, width=3 * SS)
    img = img.resize((W, H), Image.LANCZOS)
    a = np.asarray(img, float); yy = np.arange(H)[:, None, None]
    r = np.hypot(np.linspace(-1, 1, W)[None, :], np.linspace(-1, 1, H)[:, None]); a *= (1 - 0.2 * np.clip(r - 0.8, 0, 1))[..., None]  # light vignette (Stage 178: no scanlines - they moire when the texture shrinks)
    full = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)); full.convert("RGBA").save(out_path)
    for t, box_ in (("_L", (0, 0, W // 2, H)), ("_R", (W // 2, 0, W, H))):  # Stage 178: halves for the screen's 2-row atlas (twice the pixels across)
        full.crop(box_).save(out_path[:-4] + t + ".png")
    return out_path


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "levels", "assembly_ascent", "references", "specimen_schematic.png")))
