"""Contact sheet of the material library: python3 pipeline/material_swatches.py out.png [levels/<name>/level.json]
Without a level.json: every PBR kind with a default colour. Columns: base colour | normal | ORM (R=AO G=rough B=metal) | emissive."""
import json, sys, numpy as np
from PIL import Image, ImageDraw
from materials import PBR, maps, _normal, _ao

DEMO = {"industrial_metal": [0.2, 0.22, 0.21], "painted_metal": [0.55, 0.12, 0.1], "damaged_metal": [0.3, 0.3, 0.28],
        "scifi_floor": [0.42, 0.42, 0.4], "grating": [0.32, 0.33, 0.31], "concrete": [0.5, 0.49, 0.46], "rock": [0.3, 0.29, 0.27],
        "sand": [0.7, 0.6, 0.45], "dirt": [0.38, 0.3, 0.22], "grass": [0.3, 0.45, 0.18], "toxic": [0.5, 1.0, 0.1],
        "glow": [0.55, 1.0, 0.2], "machinery_panel": [0.17, 0.18, 0.18], "trim_light": [0.14, 0.15, 0.15],
        "pipe": [0.19, 0.22, 0.21], "banner": [0.8, 0.1, 0.08]}
out = sys.argv[1]
mats = json.load(open(sys.argv[2]))["materials"] if len(sys.argv) > 2 else {k: {"type": k, "color": c} for k, c in DEMO.items()}
T = 160; rows = []
for name, m in mats.items():
    d = maps(m); r = lambda a: Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((T, T))
    orm = np.stack([_ao(d["h"]), d["rough"], d["metal"]], -1)
    em = d["alb"] * d["emit"][..., None] if d["emit"] is not None else np.zeros_like(d["alb"])
    row = Image.new("RGB", (T * 4 + 170, T), (20, 20, 20))
    for i, a in enumerate([d["alb"], _normal(d["h"], d["nstr"] or 0.01), orm, em]): row.paste(r(a), (170 + i * T, 0))
    ImageDraw.Draw(row).text((6, 8), f"{name}\n{d['kind']}\n{d['S']}px", fill=(230, 230, 230)); rows.append(row)
sheet = Image.new("RGB", (rows[0].width, T * len(rows)))
for i, r_ in enumerate(rows): sheet.paste(r_, (0, i * T))
sheet.save(out); print(out, len(rows), "materials")
