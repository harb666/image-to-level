"""Stage 171: the security laser gate's sign atlas (the user's concept): one 1024 x 1024 image holding
  - "sign"  (top band, 1024 x 300): RESTRICTED AREA / LASER SECURITY GATE, red glowing text on dark metal, warning
            triangles either side, a red border;
  - "warn"  (300 x 300 below it, left): a laser-hazard warning plate - a glowing red triangle with the laser symbol.
Writes levels/assembly_ascent/references/laser_gate_atlas.png. UV rects (v up) are in ATLAS for the material.

    python3 pipeline/make_gate_art.py [out.png]
"""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024; SIGN_H = 300; WARN = (0, 340, 300, 640)  # px rects in the image
ATLAS = {"sign": [0.0, round(1 - SIGN_H / S, 4), 1.0, 1.0], "warn": [0.0, round(1 - WARN[3] / S, 4), round(WARN[2] / S, 4), round(1 - WARN[1] / S, 4)]}
RED, HOT, DIM = (255, 58, 40), (255, 150, 120), (150, 30, 25)
FB = next((p for p in ("/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(p)), None)
FM = next((p for p in ("/usr/share/fonts/opentype/inter/Inter-SemiBold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") if os.path.exists(p)), FB)


def triangle(d, cx, cy, r, w, col, fill=None):
    P = [(cx, cy - r), (cx + r * math.cos(math.radians(30)), cy + r / 2), (cx - r * math.cos(math.radians(30)), cy + r / 2)]
    if fill: d.polygon(P, fill=fill)
    d.line(P + [P[0]], fill=col, width=w, joint="curve")


def glow(layer, rad, k=1.6):
    a = np.asarray(layer, float); b = np.asarray(layer.filter(ImageFilter.GaussianBlur(rad)), float)
    return np.clip(a + b * k, 0, 255)


def main(out):
    img = np.zeros((S, S, 3), float) + (14, 10, 14)
    # --- the sign: dark brushed plate, red frame, glowing text, triangles
    y_ = np.linspace(0, 1, SIGN_H)[:, None]; x_ = np.linspace(0, 1, S)[None, :]
    plate = 18 + 10 * (1 - np.abs(y_ - 0.5) * 2) + 4 * np.sin(x_ * 900 + y_ * 40)
    img[:SIGN_H] = np.stack([plate * 1.15, plate * 0.8, plate * 0.85], -1)
    L = Image.new("RGB", (S, SIGN_H), (0, 0, 0)); d = ImageDraw.Draw(L)
    d.rounded_rectangle([14, 14, S - 14, SIGN_H - 14], radius=18, outline=RED, width=7)
    d.rounded_rectangle([30, 30, S - 30, SIGN_H - 30], radius=12, outline=DIM, width=2)
    fb = ImageFont.truetype(FB, 76) if FB else ImageFont.load_default(); fm = ImageFont.truetype(FM, 36) if FM else fb
    t1, t2 = "RESTRICTED AREA", "LASER SECURITY GATE"
    w1 = d.textlength(t1, font=fb); d.text(((S - w1) / 2, 62), t1, font=fb, fill=RED)
    w2 = d.textlength(t2, font=fm); d.text(((S - w2) / 2, 196), t2, font=fm, fill=(255, 110, 90))
    d.line([(200, 176), (S - 200, 176)], fill=DIM, width=3)
    for cx in (118, S - 118):
        triangle(d, cx, 160, 66, 9, RED); d.line([(cx, 128), (cx, 170)], fill=RED, width=10); d.ellipse([cx - 6, 180, cx + 6, 192], fill=RED)
    img[:SIGN_H] = np.clip(img[:SIGN_H] + glow(L, 5, 0.9), 0, 255)
    # --- the laser-hazard plate
    x0, y0, x1, y1 = WARN; n = x1 - x0
    img[y0:y1, x0:x1] = (22, 14, 16)
    W_ = Image.new("RGB", (n, n), (0, 0, 0)); d = ImageDraw.Draw(W_); c = n / 2
    d.rounded_rectangle([6, 6, n - 6, n - 6], radius=16, outline=DIM, width=4)
    triangle(d, c, c + 18, 118, 12, RED, fill=(60, 8, 8))
    cy = c + 34; d.ellipse([c - 16, cy - 16, c + 16, cy + 16], fill=RED)
    for k in range(12):  # the laser starburst
        a = math.radians(30 * k); r0, r1 = 24, 40 if k % 2 else 52
        d.line([(c + r0 * math.cos(a), cy + r0 * math.sin(a)), (c + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=RED, width=4)
    d.line([(c, cy), (c + 92, cy)], fill=(255, 110, 90), width=6)  # the beam leaving it
    img[y0:y1, x0:x1] = np.clip(img[y0:y1, x0:x1] + glow(W_, 4, 0.9), 0, 255)
    Image.fromarray(img.astype(np.uint8)).convert("RGBA").save(out)
    return out


if __name__ == "__main__":
    print(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "levels", "assembly_ascent", "references", "laser_gate_atlas.png")), ATLAS)
