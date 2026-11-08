"""Original sign art for Assembly Ascent (drawn from simple shapes): grin face, exit pictogram, arrow, gear emblem."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter
S = 512; out = sys.argv[1]
BG = (24, 10, 34); MAG = (255, 70, 230); MAG2 = (190, 40, 175); GRN = (120, 255, 90); DARK = (40, 18, 52)
def canvas(): im = Image.new("RGB", (S, S), BG); d = ImageDraw.Draw(im); d.rectangle([10, 10, S - 11, S - 11], outline=(70, 30, 90), width=10); return im, d
def glow(im, layer):  # add a soft glow under the drawn layer
    g = layer.filter(ImageFilter.GaussianBlur(14)); im.paste(Image.blend(im, Image.new("RGB", (S, S), (0, 0, 0)), 0), (0, 0))
    base = Image.composite(g.convert("RGB"), im, g.split()[3].point(lambda v: int(v * 0.7))); return Image.composite(layer.convert("RGB"), base, layer.split()[3])
def grin_face(d, cx, cy, r, col):  # angry slanted eyes + jagged toothy grin
    for sd in (-1, 1):
        ex = cx + sd * r * 0.42
        d.polygon([(ex - sd * r * 0.30, cy - r * 0.62), (ex + sd * r * 0.30, cy - r * 0.34), (ex - sd * r * 0.22, cy - r * 0.22)], fill=col)
    top, bot = cy + r * 0.12, cy + r * 0.55; L, Rr = cx - r * 0.72, cx + r * 0.72
    mouth = [(L, top - r * 0.05)]; n = 7
    for i in range(n + 1): mouth.append((L + (Rr - L) * i / n, top + (r * 0.10 if i % 2 else 0)))
    mouth += [(Rr, top - r * 0.05), (cx + r * 0.45, bot), (cx, bot + r * 0.08), (cx - r * 0.45, bot)]
    d.polygon(mouth, fill=col)
    for i in range(1, 6):  # teeth gaps
        x = L + (Rr - L) * i / 6; d.line([(x, top + r * 0.08), (x + r * 0.02, top + r * 0.3)], fill=BG, width=max(2, int(r * 0.05)))
def cell_grin():
    im, _ = canvas(); lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); grin_face(d, S / 2, S / 2 - 20, 200, MAG + (255,)); return glow(im, lay)
def cell_exit():
    im, d0 = canvas(); d0.rectangle([40, 40, S - 41, S - 41], fill=(10, 40, 14)); lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); c = GRN + (255,)
    d.rectangle([300, 110, 420, 400], outline=c, width=14)  # doorway
    d.ellipse([170, 105, 230, 165], fill=c)  # head
    def limb(a, b, w=30): d.line([a, b], fill=c, width=w); d.ellipse([b[0] - w / 2, b[1] - w / 2, b[0] + w / 2, b[1] + w / 2], fill=c)
    limb((195, 180), (170, 290), 38)           # torso leaning forward
    limb((190, 200), (250, 235)); limb((250, 235), (285, 205))   # front arm
    limb((185, 205), (135, 245)); limb((135, 245), (105, 225))   # back arm
    limb((170, 290), (225, 340)); limb((225, 340), (215, 405))   # front leg
    limb((170, 290), (125, 345)); limb((125, 345), (75, 360))    # back leg
    d.polygon([(330, 255), (395, 255), (395, 230), (440, 275), (395, 320), (395, 295), (330, 295)], fill=c)  # arrow into the door
    return glow(im, lay)
def cell_arrow():
    im, _ = canvas(); lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.polygon([(80, 200), (300, 200), (300, 120), (440, 256), (300, 392), (300, 312), (80, 312)], fill=MAG + (255,)); return glow(im, lay)
def cell_gear():
    im = Image.new("RGB", (S, S), DARK); lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); c = MAG2 + (255,); cx = cy = S / 2
    n = 10; pts = []
    for k in range(n * 4):
        a = 2 * math.pi * k / (n * 4) - math.pi / 2; r = 235 if (k % 4) in (1, 2) else 190; pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    d.polygon(pts, fill=c); d.ellipse([cx - 150, cy - 150, cx + 150, cy + 150], fill=DARK + (255,))
    grin_face(d, cx, cy - 5, 120, c); return glow(im, lay)
atlas = Image.new("RGB", (2 * S, 2 * S))
for (cx, cy), f in (((0, 0), cell_grin), ((S, 0), cell_exit), ((0, S), cell_arrow), ((S, S), cell_gear)): atlas.paste(f(), (cx, cy))
atlas.save(out); print(out)
