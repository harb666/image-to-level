"""Original sign art for Assembly Ascent (drawn from simple shapes): grin face, exit pictogram, arrow, gear emblem."""
import math, sys
from PIL import Image, ImageDraw, ImageFilter
S = 512; out = sys.argv[1]
BG = (24, 10, 34); FACE = (232, 112, 244); PLUM = (46, 20, 52); BORDER = (150, 64, 182); MAG = (255, 70, 230); MAG2 = (190, 40, 175); GRN = (120, 255, 90); DARK = (40, 18, 52)
def canvas(): im = Image.new("RGB", (S, S), BG); d = ImageDraw.Draw(im); d.rectangle([10, 10, S - 11, S - 11], outline=(70, 30, 90), width=10); return im, d
def glow(im, layer):  # add a soft glow under the drawn layer
    g = layer.filter(ImageFilter.GaussianBlur(14)); im.paste(Image.blend(im, Image.new("RGB", (S, S), (0, 0, 0)), 0), (0, 0))
    base = Image.composite(g.convert("RGB"), im, g.split()[3].point(lambda v: int(v * 0.7))); return Image.composite(layer.convert("RGB"), base, layer.split()[3])
def grin_face(d, cx, cy, r, col, gap=None, sy=1.0, band=80):  # sy: vertical stretch (wide sign panels squash the square cell); band: mouth thickness  # the Construct Error grin (user's reference): wide flat triangle eyes, a wavy toothy band mouth with upturned tips
    gap = gap or BG; u = r / 225.0  # reference units: the face is 450 px wide, centred at (0, 0)
    P = lambda x, y: (cx + x * u, cy + y * u * sy)
    d.polygon([P(-212, -55), P(-37, -115), P(-62, -40)], fill=col)  # left eye: long top edge out to a sharp outer point
    d.polygon([P(212, -55), P(37, -118), P(60, -42)], fill=col)    # right eye (mirror, a touch different like hand-drawn)
    yt = lambda x: 46 + 13 * math.cos(2 * math.pi * (x + 112) / 150)  # top edge of the band (waves)
    xs = [x for x in range(-170, 171, 5)]
    top = [P(x, yt(x)) for x in xs]; bot = [P(x, yt(x) + band) for x in reversed(xs)]
    d.polygon([P(-222, 22)] + top + [P(226, 14)] + bot, fill=col)  # tips sweep up at both corners
    for x in (-152, -77, -2, 76, 148):  # teeth: thin dark separators across the band
        d.line([P(x, yt(x) + 2), P(x + 3, yt(x) + band - 2)], fill=gap, width=max(2, int(7 * u)))
def cell_grin():  # dark plum panel with a purple inset border (the reference sign)
    im = Image.new("RGB", (S, S), (18, 8, 24)); d0 = ImageDraw.Draw(im)
    d0.rectangle([8, 8, S - 9, S - 9], fill=PLUM, outline=(10, 4, 14), width=6); d0.rectangle([26, 26, S - 27, S - 27], outline=BORDER, width=9)
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); grin_face(d, S / 2, S / 2 - 6, 205, FACE + (255,), gap=PLUM, sy=1.4, band=88); return glow(im, lay)  # signs using it are ~3:2 wide
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
    grin_face(d, cx, cy + 4, 118, FACE + (255,), gap=DARK); return glow(im, lay)
atlas = Image.new("RGB", (2 * S, 2 * S))
for (cx, cy), f in (((0, 0), cell_grin), ((S, 0), cell_exit), ((0, S), cell_arrow), ((S, S), cell_gear)): atlas.paste(f(), (cx, cy))
atlas.save(out); print(out)
