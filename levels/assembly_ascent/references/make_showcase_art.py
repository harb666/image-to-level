"""Stage 135: original art for the Construct Error showcase (redrawn from the user's concept image, simple shapes + a
bundled font): the mouse-skull logo, the CONSTRUCT ERROR_ banner, tall X banners, logo monitors, the floor logo
(cut-out) and the mascot silhouette inside the specimen tank (cut-out).

  python3 make_showcase_art.py <out_dir>   ->  ce_atlas.png (2048 x 2048), ce_floor_logo.png, ce_tank_mascot.png
Atlas regions (u0, v0, u1, v1; v up) are printed and must match scene_spec.json materials.roles.ce_signs.atlas."""
import math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
PINK = (236, 64, 160); HOT = (255, 70, 190); LIGHT = (250, 170, 225); PLUM = (44, 18, 46); DEEP = (26, 10, 30); GRN = (120, 255, 90)
rng = np.random.default_rng(135)
FONT = next((f for f in ("/usr/share/fonts/opentype/inter/InterDisplay-Black.otf", "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf") if os.path.exists(f)), None)


def grunge(size, base, amt=18, seed=0):
    """Cloth / painted-metal backdrop: base colour with soft blotches and fine speckle."""
    w, h = size; r = np.random.default_rng(seed)
    low = Image.fromarray((r.random((h // 32 + 2, w // 32 + 2)) * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    n = (np.asarray(low, float) / 255 - 0.5) * 2 * amt + (r.random((h, w)) - 0.5) * amt * 0.5
    a = np.clip(np.asarray(base, float)[None, None] + n[..., None], 0, 255).astype(np.uint8); return Image.fromarray(a, "RGB")


def brush_line(d, p, q, w, col, jitter=0.12, seed=0):
    """A painted stroke: a few offset lines of varying width (dry-brush edges)."""
    r = np.random.default_rng(seed)
    for k in range(5):
        o = (r.random(2) - 0.5) * w * jitter * 2; ww = int(w * (0.55 + 0.45 * r.random()))
        d.line([(p[0] + o[0], p[1] + o[1]), (q[0] + o[0], q[1] + o[1])], fill=col, width=max(2, ww))


def logo(d, cx, cy, s, col, back, slash=HOT, lw=None):
    """The mouse-skull mascot (concept image): two round ears, a squarish skull with X eyes, a toothy grin, a pink slash.
    s = overall height in px."""
    lw = lw or max(3, int(s * 0.055)); u = s / 100.0; P = lambda x, y: (cx + x * u, cy + y * u)
    for ex in (-27, 25):  # ears: rings behind the head
        d.ellipse([P(ex - 20, -50), P(ex + 20, -10)], outline=col, width=lw)
    head = [P(-34, -22), P(30, -26), P(38, -18), P(36, 22), P(24, 30), P(-26, 32), P(-38, 22), P(-40, -14)]
    d.polygon(head, fill=back); d.line(head + [head[0]], fill=col, width=lw, joint="curve")
    for ex in (-17, 15):  # X eyes
        d.line([P(ex - 8, -10), P(ex + 8, 4)], fill=col, width=lw); d.line([P(ex - 8, 4), P(ex + 8, -10)], fill=col, width=lw)
    d.rectangle([P(-25, 9), P(25, 28)], fill=back, outline=col, width=max(2, int(lw * 0.7)))  # grin: a row of square teeth
    for tx in range(-15, 25, 10): d.line([P(tx, 9), P(tx, 28)], fill=col, width=max(2, int(lw * 0.45)))
    brush_line(d, P(10, -6), P(46, -54), lw * 1.6, slash, seed=int(cx) % 97)  # the diagonal slash through the right ear


def glow_layer(base, layer, radius=10, strength=0.8):
    """Composite an RGBA drawing over base with a soft glow round it."""
    g = layer.filter(ImageFilter.GaussianBlur(radius)); ga = g.split()[3].point(lambda v: int(v * strength))
    out = Image.composite(g.convert("RGB"), base, ga); return Image.composite(layer.convert("RGB"), out, layer.split()[3])


def banner(w=2048, h=820):
    im = grunge((w, h), PLUM, 16, 1); d = ImageDraw.Draw(im)
    for k in range(9):  # faint dry-brush streaks across the cloth
        y = rng.uniform(0, h); brush_line(d, (rng.uniform(-100, w * 0.3), y), (rng.uniform(w * 0.6, w + 100), y + rng.uniform(-90, 90)), rng.uniform(8, 22), (70, 28, 70), seed=k)
    d.rectangle([14, 14, w - 15, h - 15], outline=(96, 36, 100), width=12)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    logo(dl, 420, 430, 560, PINK + (255,), PLUM + (255,), HOT + (255,))
    if FONT:  # CONSTRUCT (light) over ERROR_ (hot pink, bigger), condensed
        def text(s_, size, col, y):
            f = ImageFont.truetype(FONT, size); bb = dl.textbbox((0, 0), s_, font=f); tw, th = bb[2] - bb[0], bb[3] - bb[1]
            t = Image.new("RGBA", (tw + 20, th + 40), (0, 0, 0, 0)); ImageDraw.Draw(t).text((10 - bb[0], 10 - bb[1]), s_, font=f, fill=col)
            t = t.resize((int(t.width * 0.82), t.height), Image.LANCZOS); lay.alpha_composite(t, (760, y))
        text("CONSTRUCT", 210, LIGHT + (255,), 190); text("ERROR_", 300, HOT + (255,), 410)
    return glow_layer(im, lay, 12, 0.55)


def x_banner(w=512, h=1024):
    im = grunge((w, h), PLUM, 16, 2); d = ImageDraw.Draw(im); d.rectangle([10, 10, w - 11, h - 11], outline=(96, 36, 100), width=10)
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    brush_line(dl, (90, 230), (420, 640), 92, HOT + (255,), seed=3); brush_line(dl, (420, 230), (90, 640), 92, HOT + (255,), seed=4)
    for k in range(5): dl.polygon([(60 + k * 80, 900), (100 + k * 80, 900), (150 + k * 80, 780), (110 + k * 80, 780)], fill=PINK + (255,))  # //// at the foot
    return glow_layer(im, lay, 10, 0.5)


def monitor(w=512, h=512):
    im = Image.new("RGB", (w, h), DEEP); d = ImageDraw.Draw(im)
    for y in range(0, h, 6): d.line([(0, y), (w, y)], fill=(34, 14, 40))  # scanlines
    lay = Image.new("RGBA", (w, h), (0, 0, 0, 0)); logo(ImageDraw.Draw(lay), w / 2, h / 2 + 30, 340, HOT + (255,), DEEP + (255,), LIGHT + (255,))
    im = glow_layer(im, lay, 14, 0.9); ImageDraw.Draw(im).rectangle([6, 6, w - 7, h - 7], outline=(80, 30, 90), width=12); return im


def floor_logo(S=1024):
    """Cut-out floor paint: the logo in faded pink brush, transparent round it."""
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    logo(d, S / 2, S / 2 + 40, S * 0.78, (210, 70, 160, 235), (0, 0, 0, 0), (240, 90, 190, 235), lw=int(S * 0.045))
    a = np.asarray(lay, float); wear = np.random.default_rng(7).random(a.shape[:2]) ** 3  # scuffed paint
    a[..., 3] *= np.clip(1.0 - wear * 0.9, 0, 1); return Image.fromarray(a.astype(np.uint8), "RGBA")


def tank_mascot(S=512):
    """Cut-out silhouette floating in the specimen tank: the mascot's head on a small body, dark."""
    lay = Image.new("RGBA", (S, S * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); c = (20, 30, 18, 255)
    logo(d, S / 2, S * 0.62, S * 0.78, c, c, c, lw=int(S * 0.05))
    d.rounded_rectangle([S * 0.33, S * 0.86, S * 0.67, S * 1.42], 40, fill=c)  # torso
    for sx in (-1, 1):
        d.line([(S / 2 + sx * S * 0.15, S * 0.95), (S / 2 + sx * S * 0.34, S * 1.25)], fill=c, width=int(S * 0.08))   # arms out
        d.line([(S / 2 + sx * S * 0.09, S * 1.38), (S / 2 + sx * S * 0.14, S * 1.82)], fill=c, width=int(S * 0.09))  # legs
    return lay


def drop_emblem(S=480):
    """Stage 140: the pump / pillar emblem (concept image): a magenta plate, a white slime droplet with a little face,
    pink drips running off the bottom of the plate."""
    im = Image.new("RGB", (S, S), (150, 20, 110)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, S - 1, S - 1], outline=(70, 10, 52), width=18); d.rectangle([26, 26, S - 27, S - 27], outline=(220, 70, 170), width=6)
    for k, (x, ln) in enumerate(((0.3, 0.16), (0.5, 0.1), (0.68, 0.2))):  # drips from the lower edge
        d.rounded_rectangle([S * x - 9, S * 0.82, S * x + 9, S * (0.82 + ln)], 9, fill=(236, 90, 190))
    cx, cy, R = S / 2, S * 0.56, S * 0.25; lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    dl.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(250, 245, 250, 255)); dl.polygon([(cx - R * 0.72, cy - R * 0.7), (cx, cy - R * 2.05), (cx + R * 0.72, cy - R * 0.7)], fill=(250, 245, 250, 255))
    for ex in (-0.36, 0.36): dl.ellipse([cx + ex * R - R * 0.14, cy - R * 0.2, cx + ex * R + R * 0.14, cy + R * 0.14], fill=(150, 20, 110, 255))  # eyes
    dl.arc([cx - R * 0.3, cy + R * 0.1, cx + R * 0.3, cy + R * 0.5], 200, 340, fill=(150, 20, 110, 255), width=10)  # a little frown
    return glow_layer(im, lay, 10, 0.6)


def frown_face(S=1024, col=PINK, dark=(16, 8, 20)):
    """Stage 137: the mini boss's chest plate face (redrawn from a render of it): a slightly wide dark oval with a lighter
    rim, two X eyes and a downturned mouth - a cut-out floor decal (transparent round the oval)."""
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); cx, cy = S / 2, S / 2; rx, ry = S * 0.46, S * 0.38
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=dark + (255,), outline=(90, 34, 96, 255), width=int(S * 0.018))
    lw = int(S * 0.05); c = col + (255,)
    for ex in (-0.19, 0.19):  # X eyes (upper half; the panel's top lies away from the bridge)
        x0, y0 = cx + ex * S - S * 0.07, cy - S * 0.15; x1, y1 = x0 + S * 0.14, y0 + S * 0.14
        brush_line(d, (x0, y0), (x1, y1), lw, c, jitter=0.05, seed=int(ex * 100) + 51); brush_line(d, (x0, y1), (x1, y0), lw, c, jitter=0.05, seed=int(ex * 100) + 52)
    d.arc([cx - S * 0.2, cy + S * 0.09, cx + S * 0.2, cy + S * 0.36], 200, 340, fill=c, width=lw)  # the frown: the top of an ellipse (curving down at both ends)
    return lay


if __name__ == "__main__":
    A = Image.new("RGB", (2048, 2048), DEEP)
    A.paste(banner(), (0, 0)); A.paste(x_banner(), (0, 840)); A.paste(monitor(), (520, 840)); A.paste(monitor(), (1040, 840))
    A.paste(drop_emblem(), (1560, 840))  # Stage 140 (free space: the other cells are unchanged)
    A.save(os.path.join(OUT, "ce_atlas.png"))
    reg = lambda x0, y0, x1, y1: [round(x0 / 2048, 4), round(1 - y1 / 2048, 4), round(x1 / 2048, 4), round(1 - y0 / 2048, 4)]
    print({"banner": reg(0, 0, 2048, 820), "xban": reg(0, 840, 512, 1864), "screen": reg(520, 840, 1032, 1352), "drop": reg(1560, 840, 2040, 1320)})
    frown_face().save(os.path.join(OUT, "ce_frown_face.png"))
    floor_logo().save(os.path.join(OUT, "ce_floor_logo.png")); tank_mascot().save(os.path.join(OUT, "ce_tank_mascot.png"))
